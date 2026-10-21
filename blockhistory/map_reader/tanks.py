"""Gas-tank second pass: count G.T. circles at fuel and vehicle sites at full resolution.

The first pass names buildings well but misses about half the gasoline tanks (week 7:
12 of 25 on the checked sheets). Tank circles are a few pixels wide on our 50% tiles, so
this pass re-downloads only the tiles with a fuel or vehicle finding at full resolution,
splits each into four crops, and asks one narrow question: which tank groups are here,
how many circles each, and which building they serve. apply() then puts those counts on
the first pass's findings and adds tank sites the first pass missed.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from enum import Enum
from pathlib import Path

from PIL import Image
from pydantic import BaseModel, Field

from blockhistory import costs
from blockhistory.collector.loc import download_region
from blockhistory.map_reader import extract
from blockhistory.map_reader.relevance import relevance
from blockhistory.map_reader.scoring import address_level, is_found, label_words

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "cache" / "tank_reader"
DEFAULT_EFFORT = "low"
PROMPT_VERSION = "t2"  # t2: ignore faint print showing through paste-over patches
MAX_TOKENS = 4000
EST_TOKENS = (2_300, 600)  # per crop; only used for the budget check
CROP_OVERLAP = 128  # full-res pixels shared by neighboring crops of one tile
# A tile gets the second pass if the first pass found one of these there.
FUEL = re.compile(r"FILL|GAS|OIL|GARAGE|AUTO|TRUCK|BATTERY|SERV|TANK|TK", re.IGNORECASE)

SYSTEM_PROMPT = """\
You count gasoline tank symbols on full-resolution crops of 1930s-1950s Sanborn fire \
insurance maps. The counts tell residents where buried fuel tanks may have been, so \
count only what is drawn and say when you are unsure.

What counts as a gasoline tank:
- A small open circle (about the size of a printed letter O) next to the label "G.T." \
(one tank) or "G.T.S." (tanks; the label covers every circle in the group). Each circle \
is one tank. Count the circles, not the labels. Circles are usually at the curb, the \
sidewalk or a yard beside a filling station, garage, auto shop or oil station, often in \
a row of 2-4.
- Tanks labeled in words as gasoline: "GASOL. STGE. TKS.", "GASOL. TK.", \
"IR. GASOL. TK. ON GRD.". Count the circles drawn with them (or 1 if none is drawn).

What does not count:
- Solid black dots (fire hydrants) and the pipes that join them.
- Circled numbers (ground elevations), circled letters like "FA" (fire alarm boxes).
- Water tanks ("W.T."), and tanks labeled for oil, tar, benzol, ammonia, acid, water, \
grain or molasses. Gas holders ("GASOMETER") store coal gas, not gasoline.
- Letters O and the digit 0 in printed text; skylights and small squares.
- Faint, washed-out circles or labels showing through a pasted-on paper patch. Later map editions cover changed lots with printed patches (often a slightly different paper tone with a visible edge); the old symbols underneath can still show faintly. They are no longer on the map. Count only crisp, dark circles printed on top.

For each group of gasoline tanks give the printed tank label, the number of circles, and \
the site the tanks serve: copy that building's or yard's use label exactly as printed \
(e.g. "FILL'G STA.", "AUTO REP.", "BULK OIL STA.", or a company name) and its street \
number if one is printed. If the circles stand between buildings, pick the nearest one \
with a fuel or vehicle use. If there are no gasoline tanks in the crop, return no groups.
"""
USER_TEXT = "List every group of gasoline tank symbols in this crop."


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class TankGroup(BaseModel):
    tank_label: str = Field(description="Tank label as printed, e.g. 'G.T.S.', or '' if none")
    circles: int = Field(description="Number of tank circles in this group")
    site_label: str = Field(description="Use label of the building the tanks serve, as printed")
    site_street_number: str | None = Field(description="That building's street number, or null")
    partial: bool = Field(description="The group is cut off by the crop edge")
    confidence: Confidence


class TankReading(BaseModel):
    groups: list[TankGroup]


SCHEMA = TankReading


def resolve(model: str | None = None, effort: str | None = None) -> tuple[str, str]:
    """Same model as the map reader; this pass has its own effort default."""
    return extract.resolve(model, None)[0], effort or DEFAULT_EFFORT


def _cache_key(image_bytes: bytes, model: str, effort: str) -> str:
    h = hashlib.sha256()
    h.update(f"tanks|{model}|{effort}|{PROMPT_VERSION}|".encode())
    h.update(image_bytes)
    return h.hexdigest()[:32]


def cache_path(crop: Path, model: str, effort: str) -> Path:
    return CACHE_DIR / f"{_cache_key(crop.read_bytes(), model, effort)}.json"


def load_cached(crop: Path, model: str | None = None, effort: str | None = None) -> dict | None:
    path = cache_path(crop, *resolve(model, effort))
    return json.loads(path.read_text()) if path.exists() else None


def messages_for(image_bytes: bytes) -> list[dict]:
    data = base64.standard_b64encode(image_bytes).decode()
    return [
        {
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}},
                {"type": "text", "text": USER_TEXT},
            ],
        }
    ]  # fmt: skip


def save_result(
    crop: Path,
    model: str,
    effort: str,
    served_model: str,
    input_tokens: int,
    output_tokens: int,
    reading: TankReading,
    batch: bool = False,
) -> dict:
    usd = costs.record(model, input_tokens, output_tokens, what=f"tanks {crop.name}", batch=batch)
    result = {
        "crop": crop.name,
        "model": served_model,
        "effort": effort,
        "prompt_version": PROMPT_VERSION,
        "batch": batch,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        "usd": round(usd, 6),
        "reading": reading.model_dump(mode="json"),
    }
    path = cache_path(crop, model, effort)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")
    return result


def is_candidate(building: dict) -> bool:
    """A first-pass finding worth a tank check: any tanks, or a fuel/vehicle business."""
    if building.get("gasoline_tank_count"):
        return True
    text = f"{building['label']} {building['use']}"
    return bool(FUEL.search(text)) and relevance(building["label"], building["use"]) != "low"


def candidate_tiles(tile_dir: Path, model: str | None = None) -> list[Path]:
    """Tiles whose first-pass result has a fuel or vehicle finding."""
    out = []
    for tile in sorted(tile_dir.glob("*.jpg")):
        result = extract.load_cached(tile, model)
        if result and any(is_candidate(b) for b in result["extraction"]["buildings"]):
            out.append(tile)
    return out


def hires_dir(tile_dir: Path) -> Path:
    """data/tiles/<area>/<edition>/<sheet> -> data/tiles_hires/<area>/<edition>/<sheet>."""
    return ROOT / "data" / "tiles_hires" / _sheet_rel(tile_dir)


def _sheet_rel(tile_dir: Path) -> Path:
    return tile_dir.resolve().relative_to(ROOT / "data" / "tiles")


def crops_for(tile: Path) -> list[Path]:
    """The tile's area at full resolution, as four overlapping crops (downloads once)."""
    tile_dir = tile.parent
    out_dir = hires_dir(tile_dir)
    existing = sorted(out_dir.glob(f"{tile.stem}_q*.jpg"))
    if len(existing) == 4:
        return existing
    index = json.loads((tile_dir / "tiles.json").read_text())
    entry = next(t for t in index["tiles"] if t["tile"] == tile.name)
    rel = _sheet_rel(tile_dir)
    meta = json.loads((ROOT / "data" / "sheets" / rel.parent / f"{rel.name}.json").read_text())
    scale = meta["width"] / index["sheet_size"][0]
    with Image.open(tile) as im:
        w, h = im.size
    box = tuple(round(v * scale) for v in (entry["x"], entry["y"], w, h))
    region = download_region(meta["service"], box, out_dir / f"{tile.stem}_full.jpg")
    crops = []
    with Image.open(region) as im:
        fw, fh = im.size
        cw, ch = (fw + CROP_OVERLAP) // 2, (fh + CROP_OVERLAP) // 2
        for r, y in enumerate((0, fh - ch)):
            for c, x in enumerate((0, fw - cw)):
                path = out_dir / f"{tile.stem}_q{r}{c}.jpg"
                im.crop((x, y, x + cw, y + ch)).save(path, quality=90)
                crops.append(path)
    return crops


def _serves(group: dict, finding: dict) -> bool:
    site = group["site_label"] or ""
    named = is_found(finding["label"], set(label_words(site))) or is_found(
        site, set(label_words(finding["label"]))
    )
    number = {"street_number": group.get("site_street_number")}
    return named and address_level(number, finding) > 0


def _unnamed(site: str) -> bool:
    """No site, or only a plain footprint letter (D, S, F, A), which can't hold a tank."""
    return not label_words(site) or bool(re.fullmatch(r"\s*[DSFA]\.?\s*", site))


def _grid(tile: str) -> tuple[int, int]:
    """'..._r2_c3.jpg' -> (2, 3)."""
    m = re.search(r"_r(\d+)_c(\d+)\.jpg$", tile)
    return (int(m.group(1)), int(m.group(2))) if m else (-99, -99)


def _same_number(group: dict, finding: dict) -> bool:
    """Exactly the same house number, or one of them unknown (no misread tolerance)."""
    a, b = group.get("site_street_number"), finding.get("street_number")
    return not a or not b or a.split("-")[0].strip() == b.split("-")[0].strip()


def _near_tiles(tile: str, other: str) -> bool:
    (r1, c1), (r2, c2) = _grid(tile), _grid(other)
    return abs(r1 - r2) <= 1 and abs(c1 - c2) <= 1


def apply(findings: list[dict], tile_dir: Path, model: str | None = None) -> dict:
    """Put second-pass tank counts on a sheet's findings, in place.

    Each tank group goes to the finding on its tile that it names. A group that names no
    business ("" or "D.") goes to the tile's only fuel or vehicle finding if there is
    exactly one, and is dropped otherwise. A named group that matches nothing on its tile
    but names a finding on a neighbouring tile, street number included, is that finding's
    tanks seen across a tile edge, not a new site. A finding's count becomes the most circles any
    one crop of its tiles gives it (crops overlap, so counts are not added across crops),
    or the first pass's count if that is higher. Groups naming a business the first pass
    missed become new findings. Returns a summary.
    """
    readings: dict[str, list[tuple[str, list[dict]]]] = {}
    usd = 0.0
    for tile in sorted(tile_dir.glob("*.jpg")):
        for crop in sorted(hires_dir(tile_dir).glob(f"{tile.stem}_q*.jpg")):
            result = load_cached(crop, model)
            if result:
                readings.setdefault(tile.name, []).append((crop.name, result["reading"]["groups"]))
                usd += result["usd"]
    if not readings:
        return {"tiles": 0, "usd": 0.0, "changed": 0, "added": 0}

    counts: dict[int, list[int]] = {}  # finding index -> circles given by each crop
    orphans: list[tuple[str, dict]] = []
    for tile, crops in readings.items():
        here = [k for k, f in enumerate(findings) if tile in f["tiles"]]
        fuel = [k for k in here if is_candidate(findings[k])]
        for crop, groups in crops:
            per_crop: dict[int, int] = {k: 0 for k in here}
            for g in groups:
                if g["circles"] <= 0:
                    continue
                k = next((k for k in here if _serves(g, findings[k])), None)
                if k is None and _unnamed(g["site_label"] or "") and len(fuel) == 1:
                    k = fuel[0]
                if k is not None:
                    per_crop[k] += g["circles"]
                elif not _unnamed(g["site_label"] or ""):
                    orphans.append((tile, g))
            for k, n in per_crop.items():
                counts.setdefault(k, []).append(n)

    changed = 0
    for k, per_crop in counts.items():
        f = findings[k]
        f["tank_pass_count"] = max(per_crop)
        if f["tank_pass_count"] > f["gasoline_tank_count"]:
            f["gasoline_tank_count"] = f["tank_pass_count"]
            changed += 1

    added: list[dict] = []
    for tile, g in orphans:
        label = g["site_label"]
        # The same tanks seen from a neighbouring tile, under a slightly different name.
        near = [
            k
            for k, f in enumerate(findings)
            if any(_near_tiles(tile, t) for t in f["tiles"])
            and (
                is_found(f["label"], set(label_words(label)))
                or is_found(label, set(label_words(f["label"])))
            )
        ]

        same_place = [k for k in near if _serves(g, findings[k]) and _same_number(g, findings[k])]
        if same_place:
            f = findings[same_place[0]]
            f["tank_pass_count"] = max(f.get("tank_pass_count", 0), g["circles"])
            f["gasoline_tank_count"] = max(f["gasoline_tank_count"], g["circles"])
            continue
        same = next(
            (
                a
                for a in added
                if label_words(a["label"]) == label_words(label)
                and address_level({"street_number": g["site_street_number"]}, a) > 0
            ),
            None,
        )
        if same:
            same["gasoline_tank_count"] = max(same["gasoline_tank_count"], g["circles"])
            if tile not in same["tiles"]:
                same["tiles"].append(tile)
            continue
        added.append(
            {
                "label": label,
                "use": f"site with gasoline tanks ({g['tank_label'] or 'tank symbols'})",
                "street_number": g["site_street_number"],
                "street_name": None,
                "construction": "unknown",
                "stories": None,
                "gasoline_tank_count": g["circles"],
                "partial": g["partial"],
                "confidence": g["confidence"],
                "position": "from the tank pass",
                "tiles": [tile],
                "ocr_seen": None,
                "relevance": "high",
                "tank_pass_count": g["circles"],
                "source": "tank pass",
            }
        )
    findings.extend(added)
    return {"tiles": len(readings), "usd": round(usd, 6), "changed": changed, "added": len(added)}
