"""The findings database: build it from results, and query it by distance.

A local SQLite file for now (data/blockhistory.sqlite), with the same tables as
schema_postgis.sql so it can move to Supabase unchanged: `export_postgis_sql()` writes
the rows as one SQL file to paste into Supabase's SQL editor.

Only georeferenced sheets go in. Each sheet's footprint (its corners on today's map) is
stored too, so a search can tell "no findings near you" apart from "we haven't processed
the map for your block yet".
"""

from __future__ import annotations

import itertools
import json
import math
import re
import sqlite3
from pathlib import Path

from blockhistory.explain import category, explanation
from blockhistory.georef.transform import M_PER_DEG, Affine, leave_one_out
from blockhistory.map_reader.relevance import relevance
from blockhistory.map_reader.scoring import label_words, norm

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "blockhistory.sqlite"
SHOWN = ("high", "medium")  # relevance levels the website lists
DUPLICATE_M = 15  # same label within this distance on one sheet = one site
REPEAT_M = 30  # same kind of use with a similar label (a misread repeat) within this = one site

SCHEMA = """
CREATE TABLE IF NOT EXISTS sheets (
  sheet_id TEXT PRIMARY KEY,
  area TEXT, edition TEXT, sheet_number INTEGER, volume TEXT,
  loc_page_url TEXT,            -- the sheet on loc.gov
  iiif_service TEXT,            -- for image crops: tile.loc.gov/image-services/iiif/<service>/...
  scale_m_per_px REAL,          -- on the 50% image
  full_res_scale REAL,          -- full-resolution pixels per 50% image pixel (~2.0)
  georef_error_m REAL,          -- median leave-one-out error of the control points
  footprint TEXT                -- GeoJSON Polygon of the sheet's corners today
);
CREATE TABLE IF NOT EXISTS findings (
  id INTEGER PRIMARY KEY,
  sheet_id TEXT REFERENCES sheets(sheet_id),
  edition TEXT,
  label TEXT,                   -- as printed on the map
  use TEXT,                     -- plain English, from the reader
  street_number TEXT,
  relevance TEXT,               -- high / medium / low
  category TEXT,
  explanation TEXT,
  gasoline_tank_count INTEGER,
  reader_confidence TEXT,
  review_status TEXT,           -- unreviewed / checked_ok / checked_wrong
  lat REAL, lon REAL,
  location_method TEXT,
  location_uncertainty_m REAL,
  sheet_px INTEGER, sheet_py INTEGER
);
CREATE INDEX IF NOT EXISTS findings_latlon ON findings (lat, lon);
CREATE TABLE IF NOT EXISTS records (
  id INTEGER PRIMARY KEY,
  source TEXT,                  -- e.g. Missouri DNR
  kind TEXT,                    -- tank / cleanup
  name TEXT, address TEXT,
  status TEXT,                  -- as the agency words it
  status_plain TEXT,            -- plain words (blockhistory/records/dnr.py)
  release INTEGER,              -- 1 if a leak or contamination is on record
  contaminants TEXT,
  detail TEXT,
  url TEXT,
  lat REAL, lon REAL,
  located_by TEXT               -- parcel / state point
);
CREATE INDEX IF NOT EXISTS records_latlon ON records (lat, lon);
"""
RECORD_COLS = (
    "source", "kind", "name", "address", "status", "status_plain", "release", "contaminants",
    "detail", "url", "lat", "lon", "located_by",
)  # fmt: skip


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def _distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    kx = M_PER_DEG * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot((lat1 - lat2) * M_PER_DEG, (lon1 - lon2) * kx)


def _loc_page(area: str, sheet_id: str, service: str) -> str:
    """loc.gov page for the sheet: ?sp= is the image's place in the edition's file list."""
    config = json.loads((ROOT / "config" / "neighborhoods" / f"{area}.json").read_text())
    for ed in config["editions"]:
        ids = [s["sheet_id"] for s in ed["sheets"]]
        if sheet_id in ids:
            # service:gmd:...:g4164sm:g4164sm_g04858193812:<sheet> -> g4164sm.g4164sm_g04858193812
            group, resource = service.split(":")[-3:-1]
            return f"https://www.loc.gov/resource/{group}.{resource}/?sp={ids.index(sheet_id) + 1}"
    return ""


def review_marks(sheet_id: str) -> dict[tuple[str, str], str]:
    """(normalized label, tiles) -> checked_ok / checked_wrong, from the spot-check ticks."""
    path = ROOT / "evals" / "spotcheck" / f"{sheet_id}.md"
    marks = {}
    if path.exists():
        for line in path.read_text().splitlines():
            m = re.match(r"\| \[(.)\] \| \[(.)\] \| \w+ \| (.*?) \|.*\| ([^|]*) \|$", line)
            if m and "x" in (m.group(1) + m.group(2)).lower():
                status = "checked_ok" if m.group(1).lower() == "x" else "checked_wrong"
                marks[(norm(m.group(3)), m.group(4).strip())] = status
    return marks


def _tiles_key(tiles: list[str]) -> str:
    """Same format as the checklist's tiles column: 'r2_c2, r3_c2'."""
    return ", ".join(t.rsplit("_", 2)[1] + "_" + t.rsplit("_", 2)[2][:-4] for t in tiles)


def _dedupe(findings: list[dict]) -> list[dict]:
    """One row per site: same label words within DUPLICATE_M meters are one finding."""
    rank = {
        "hand-placed": -1,
        "point pass": 0,
        "ocr": 1,
        "tile overlap": 2,
        "position words": 3,
        "tile center": 4,
    }
    kept: list[dict] = []
    for f in sorted(findings, key=lambda f: rank.get(f["location_method"], 9)):
        same = next((k for k in kept if _repeat(f, k)), None)
        if same is None:
            kept.append(f)
        else:
            same["gasoline_tank_count"] = max(same["gasoline_tank_count"], f["gasoline_tank_count"])
            same["street_number"] = same.get("street_number") or f.get("street_number")
    return kept


def _repeat(f: dict, k: dict) -> bool:
    """Is f another read of the site k? Same label words within DUPLICATE_M, or a similar but
    different label of the same kind of use within REPEAT_M. Identical labels farther apart
    are separate sites (two filling stations on facing corners)."""
    d = _distance_m(f["lat"], f["lon"], k["lat"], k["lon"])
    words, other = set(label_words(f["label"])), set(label_words(k["label"]))
    if words & other and d < DUPLICATE_M:
        return True
    return (
        d < REPEAT_M
        and words != other
        and category(f["label"], f["use"], f["gasoline_tank_count"])[0]
        == category(k["label"], k["use"], k["gasoline_tank_count"])[0]
        and _similar_words(words, other)
    )


def _similar_words(a: set[str], b: set[str]) -> bool:
    """A shared word, or a misread of one: a prefix ("MACH" / "MACHINE", "MIX" / "MIXING") or
    up to two letters different in a longer word ("PRINTG" / "PAINTG", "VARNISHING" /
    "VARNISHG")."""
    for x in a:
        for y in b:
            if x == y or (min(len(x), len(y)) >= 3 and (x.startswith(y) or y.startswith(x))):
                return True
            if min(len(x), len(y)) >= 5 and _edits(x, y) <= 2:
                return True
    return False


def _edits(x: str, y: str) -> int:
    """Levenshtein distance."""
    row = list(range(len(y) + 1))
    for i, cx in enumerate(x, 1):
        prev, row[0] = row[0], i
        for j, cy in enumerate(y, 1):
            prev, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, prev + (cx != cy))
    return row[-1]


# The reader writes a clean "DRY CLEANING" when it guesses; the map prints "DRY CLEANG",
# "DRY CLG" and the like. At low confidence that full spelling was never on the map in any
# of the 10 checked cases, so it isn't shown.
GUESSED = re.compile(r"\s*DRY CLEANING\.?\s*")


def prepare_sites(findings: list[dict]) -> list[dict]:
    """One row per site (repeat reads merged), with its relevance: what load_sheet stores and
    what a spot-check list should show."""
    sites = _dedupe(findings)
    for f in sites:
        f["relevance"] = relevance(f["label"], f["use"])
        if f["gasoline_tank_count"] and f["relevance"] == "low":
            f["relevance"] = "high"  # a drawn gasoline tank always matters
        if f.get("confidence") == "low" and GUESSED.fullmatch(f["label"].upper()):
            f["relevance"] = "low"
    return sites


def clear_sheet(con: sqlite3.Connection, sheet_id: str) -> None:
    """Remove a sheet and all its panels (before reloading it)."""
    ids = [sheet_id, f"{sheet_id}.%"]
    con.execute("DELETE FROM findings WHERE sheet_id = ? OR sheet_id LIKE ?", ids)
    con.execute("DELETE FROM sheets WHERE sheet_id = ? OR sheet_id LIKE ?", ids)


def load_sheet(
    con: sqlite3.Connection,
    area: str,
    edition: str,
    panel_id: str,
    findings: list[dict],
    t: Affine,
    outline: list[tuple[float, float]] | None = None,
) -> int:
    """Replace one sheet's (or panel's) rows. `findings` are located merged findings; `t`
    is the panel's transform and `outline` its pixel outline (None = the whole sheet)."""
    sheet_id = panel_id.split(".")[0]
    meta = json.loads((ROOT / "data" / "sheets" / area / edition / f"{sheet_id}.json").read_text())
    loo = sorted(leave_one_out(t.gcps, t.model))
    index = json.loads(
        (ROOT / "data" / "tiles" / area / edition / sheet_id / "tiles.json").read_text()
    )
    w, h = index["sheet_size"]
    outline = outline or [(0, 0), (w, 0), (w, h), (0, h)]
    ring = [t.to_latlon(x, y) for x, y in [*outline, outline[0]]]
    con.execute("DELETE FROM findings WHERE sheet_id = ?", (panel_id,))
    con.execute(
        "INSERT OR REPLACE INTO sheets VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            panel_id,
            area,
            edition,
            meta.get("sheet_number"),
            "St. Louis Vol. 12",
            _loc_page(area, sheet_id, meta["service"]),
            meta["service"],
            t.meters_per_pixel(),
            meta["width"] / w,
            loo[len(loo) // 2],
            json.dumps({"type": "Polygon", "coordinates": [[[lon, lat] for lat, lon in ring]]}),
        ),
    )
    marks = review_marks(sheet_id)
    rows = 0
    for f in prepare_sites(findings):
        status = marks.get((norm(f["label"]), _tiles_key(f["tiles"])), "unreviewed")
        cat, _ = category(f["label"], f["use"], f["gasoline_tank_count"])
        con.execute(
            "INSERT INTO findings (sheet_id, edition, label, use, street_number, relevance, category,"
            " explanation, gasoline_tank_count, reader_confidence, review_status, lat, lon,"
            " location_method, location_uncertainty_m, sheet_px, sheet_py)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                panel_id,
                edition,
                f["label"],
                f["use"],
                f.get("street_number"),
                f["relevance"],
                cat,
                explanation(f, edition),
                f["gasoline_tank_count"],
                f.get("confidence"),
                status,
                f["lat"],
                f["lon"],
                f["location_method"],
                f["uncertainty_m"],
                f["sheet_px"][0],
                f["sheet_px"][1],
            ),
        )
        rows += 1
    con.commit()
    return rows


def _inside(lat: float, lon: float, polygon: dict) -> bool:
    ring = polygon["coordinates"][0]
    inside = False
    for (x1, y1), (x2, y2) in itertools.pairwise(ring):
        if (y1 > lat) != (y2 > lat) and lon < x1 + (lat - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def load_records(con: sqlite3.Connection, rows: list[dict]) -> int:
    """Replace every official record with `rows` (from blockhistory/records)."""
    con.execute("DELETE FROM records")
    marks = ", ".join("?" * len(RECORD_COLS))
    con.executemany(
        f"INSERT INTO records ({', '.join(RECORD_COLS)}) VALUES ({marks})",
        [tuple(int(r[c]) if c == "release" else r.get(c) for c in RECORD_COLS) for r in rows],
    )
    con.commit()
    return len(rows)


def records_near(con: sqlite3.Connection, lat: float, lon: float, radius_m: float) -> list[dict]:
    dlat = radius_m / M_PER_DEG
    dlon = radius_m / (M_PER_DEG * math.cos(math.radians(lat)))
    rows = con.execute(
        "SELECT * FROM records WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?",
        (lat - dlat, lat + dlat, lon - dlon, lon + dlon),
    ).fetchall()
    out = [
        {**dict(r), "distance_m": round(_distance_m(lat, lon, r["lat"], r["lon"]))} for r in rows
    ]
    return sorted((r for r in out if r["distance_m"] <= radius_m), key=lambda r: r["distance_m"])


def search(
    con: sqlite3.Connection, lat: float, lon: float, radius_m: float = 100, levels=SHOWN
) -> dict:
    """Findings within radius_m (nearest first) and the sheets that cover the point."""
    dlat = radius_m / M_PER_DEG
    dlon = radius_m / (M_PER_DEG * math.cos(math.radians(lat)))
    rows = con.execute(
        "SELECT f.*, s.loc_page_url, s.iiif_service, s.sheet_number FROM findings f"
        " JOIN sheets s USING (sheet_id)"
        " WHERE f.lat BETWEEN ? AND ? AND f.lon BETWEEN ? AND ? AND f.review_status != 'checked_wrong'",
        (lat - dlat, lat + dlat, lon - dlon, lon + dlon),
    ).fetchall()
    out = []
    for r in rows:
        d = _distance_m(lat, lon, r["lat"], r["lon"])
        if d <= radius_m and r["relevance"] in levels:
            out.append({**dict(r), "distance_m": round(d)})
    out.sort(key=lambda r: r["distance_m"])
    covering = [
        dict(s)
        for s in con.execute("SELECT * FROM sheets").fetchall()
        if _inside(lat, lon, json.loads(s["footprint"]))
    ]
    records = records_near(con, lat, lon, radius_m) if covering else []
    return {"findings": out, "covered_by": covering, "records": records}


PART_BYTES = 400_000  # Supabase's SQL editor refuses much larger queries


def export_postgis_sql(con: sqlite3.Connection, out: Path) -> tuple[int, list[Path]]:
    """All rows as INSERTs for schema_postgis.sql, split into files small enough for
    Supabase's SQL editor: <out stem>_1.sql (clears the tables, then loads), _2.sql, ...
    Run them in order. Returns (findings written, files)."""

    def lit(v):
        if v is None:
            return "NULL"
        if isinstance(v, (int, float)):
            return repr(v)
        return "'" + str(v).replace("'", "''") + "'"

    lines = ["DELETE FROM findings; DELETE FROM sheets; DELETE FROM records;"]
    for s in con.execute("SELECT * FROM sheets"):
        s = dict(s)
        fp = s.pop("footprint")
        cols = ", ".join(s) + ", footprint"
        vals = ", ".join(lit(v) for v in s.values()) + f", ST_GeomFromGeoJSON({lit(fp)})::geography"
        lines.append(f"INSERT INTO sheets ({cols}) VALUES ({vals});")
    n = 0
    for f in con.execute("SELECT * FROM findings"):
        f = dict(f)
        f.pop("id")
        lat, lon = f.pop("lat"), f.pop("lon")
        cols = ", ".join(f) + ", geom"
        vals = (
            ", ".join(lit(v) for v in f.values()) + f", ST_Point({lon!r}, {lat!r}, 4326)::geography"
        )
        lines.append(f"INSERT INTO findings ({cols}) VALUES ({vals});")
        n += 1
    for r in con.execute("SELECT * FROM records"):
        r = dict(r)
        r.pop("id")
        lat, lon = r.pop("lat"), r.pop("lon")
        r["release"] = bool(r["release"])
        cols = ", ".join(r) + ", geom"
        vals = (
            ", ".join(
                ("TRUE" if v else "FALSE") if k == "release" else lit(v) for k, v in r.items()
            )
            + f", ST_Point({lon!r}, {lat!r}, 4326)::geography"
        )
        lines.append(f"INSERT INTO records ({cols}) VALUES ({vals});")

    parts: list[list[str]] = [[]]
    size = 0
    for line in lines:
        if size + len(line) > PART_BYTES and parts[-1]:
            parts.append([])
            size = 0
        parts[-1].append(line)
        size += len(line) + 1
    out.parent.mkdir(parents=True, exist_ok=True)
    for old in out.parent.glob(f"{out.stem}*.sql"):
        old.unlink()  # a shorter export must not leave an old extra part behind
    files = []
    for i, body in enumerate(parts, 1):
        path = out.with_name(f"{out.stem}_{i}{out.suffix}")
        head = [
            f"-- BlockHistory data, part {i} of {len(parts)}. Run parts in order, after",
            "-- blockhistory/db/schema_postgis.sql. Part 1 clears the tables first.",
            "SET search_path = public, extensions;",
            "BEGIN;",
        ]
        path.write_text("\n".join([*head, *body, "COMMIT;"]) + "\n")
        files.append(path)
    return n, files
