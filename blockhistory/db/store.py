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
from blockhistory.georef.transform import M_PER_DEG, Affine, leave_one_out, read_points
from blockhistory.map_reader.relevance import relevance
from blockhistory.map_reader.scoring import label_words, norm

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "blockhistory.sqlite"
SHOWN = ("high", "medium")  # relevance levels the website lists
DUPLICATE_M = 15  # same label within this distance on one sheet = one site

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
"""


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
    rank = {"point pass": 0, "ocr": 1, "tile overlap": 2, "position words": 3, "tile center": 4}
    kept: list[dict] = []
    for f in sorted(findings, key=lambda f: rank.get(f["location_method"], 9)):
        words = set(label_words(f["label"]))
        same = next(
            (
                k
                for k in kept
                if words & set(label_words(k["label"]))
                and _distance_m(f["lat"], f["lon"], k["lat"], k["lon"]) < DUPLICATE_M
            ),
            None,
        )
        if same is None:
            kept.append(f)
        else:
            same["gasoline_tank_count"] = max(same["gasoline_tank_count"], f["gasoline_tank_count"])
            same["street_number"] = same.get("street_number") or f.get("street_number")
    return kept


def load_sheet(
    con: sqlite3.Connection, area: str, edition: str, sheet_id: str, findings: list[dict]
) -> int:
    """Replace one sheet's rows. `findings` are located (lat/lon) merged findings."""
    meta = json.loads((ROOT / "data" / "sheets" / area / edition / f"{sheet_id}.json").read_text())
    gcps = read_points(ROOT / "config" / "georef" / area / edition / f"{sheet_id}.points")
    t = Affine(gcps)
    loo = sorted(leave_one_out(gcps))
    index = json.loads(
        (ROOT / "data" / "tiles" / area / edition / sheet_id / "tiles.json").read_text()
    )
    w, h = index["sheet_size"]
    ring = [t.to_latlon(x, y) for x, y in ((0, 0), (w, 0), (w, h), (0, h), (0, 0))]
    con.execute("DELETE FROM findings WHERE sheet_id = ?", (sheet_id,))
    con.execute(
        "INSERT OR REPLACE INTO sheets VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            sheet_id,
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
    for f in _dedupe(findings):
        f["relevance"] = relevance(f["label"], f["use"])
        if f["gasoline_tank_count"] and f["relevance"] == "low":
            f["relevance"] = "high"  # a drawn gasoline tank always matters
        status = marks.get((norm(f["label"]), _tiles_key(f["tiles"])), "unreviewed")
        cat, _ = category(f["label"], f["use"], f["gasoline_tank_count"])
        con.execute(
            "INSERT INTO findings (sheet_id, edition, label, use, street_number, relevance, category,"
            " explanation, gasoline_tank_count, reader_confidence, review_status, lat, lon,"
            " location_method, location_uncertainty_m, sheet_px, sheet_py)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                sheet_id,
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
    return {"findings": out, "covered_by": covering}


def export_postgis_sql(con: sqlite3.Connection, out: Path) -> int:
    """All rows as INSERTs for schema_postgis.sql (paste into Supabase's SQL editor)."""

    def lit(v):
        if v is None:
            return "NULL"
        if isinstance(v, (int, float)):
            return repr(v)
        return "'" + str(v).replace("'", "''") + "'"

    lines = [
        "-- BlockHistory data. Run after blockhistory/db/schema_postgis.sql.",
        "SET search_path = public, extensions;",
        "BEGIN;",
        "DELETE FROM findings; DELETE FROM sheets;",
    ]
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
    lines.append("COMMIT;")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    return n
