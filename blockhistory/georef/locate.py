"""Where a finding is on its sheet, in pixels of the 50% sheet image.

Best first: the point pass (points.py: the model gives the building's pixel center on its
tile); a label word Tesseract read on the tile; the first pass's position words ("right
block, upper middle"), which pick a ninth of the tile but were wrong by up to half a tile
on sheet 56; the tile's center. Each point carries the method and a rough
uncertainty so the website can say how precise it is.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from blockhistory.map_reader import points
from blockhistory.map_reader.ocr import read_tile_boxes
from blockhistory.map_reader.scoring import label_words, norm

ROOT = Path(__file__).resolve().parents[2]
BOX_CACHE = ROOT / "data" / "cache" / "ocr_boxes"


def ocr_boxes(tile: Path) -> list[dict]:
    key = hashlib.sha256(tile.read_bytes()).hexdigest()[:32]
    path = BOX_CACHE / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text())
    boxes = read_tile_boxes(tile)
    BOX_CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(boxes))
    return boxes


def tile_offsets(tile_dir: Path) -> dict[str, tuple[int, int, int, int]]:
    """tile name -> (x, y, width, height) on the sheet image."""
    index = json.loads((tile_dir / "tiles.json").read_text())
    w, h = index["sheet_size"]
    out = {}
    for t in index["tiles"]:
        out[t["tile"]] = (t["x"], t["y"], min(1024, w - t["x"]), min(1024, h - t["y"]))
    return out


def _word_match(ocr_text: str, word: str) -> bool:
    t = norm(ocr_text)
    return t == word or (len(t) >= 4 and t in word)


def _fraction(position: str) -> tuple[float, float] | None:
    """'right block, upper middle' -> (0.8, 0.2); None if it names no direction."""
    words = set(re.findall(r"[a-z]+", position.lower()))
    fx = 0.2 if "left" in words else 0.8 if "right" in words else None
    fy = 0.2 if words & {"top", "upper"} else 0.8 if words & {"bottom", "lower"} else None
    if fx is None and fy is None and not words & {"center", "centre", "middle"}:
        return None
    return (0.5 if fx is None else fx), (0.5 if fy is None else fy)


def sheet_point(finding: dict, tile_dir: Path, use_ocr: bool = True) -> dict:
    """{px, py, method, uncertainty_px} for one merged finding."""
    offsets = tile_offsets(tile_dir)
    tiles = [t for t in finding["tiles"] if t in offsets]
    if not tiles:
        raise ValueError(f"finding {finding['label']!r} has no known tile")
    pts = []
    for tile in tiles:
        for p in points.tile_points(tile_dir / tile):
            same_label = norm(p["label"]) == norm(finding["label"])
            same_number = (p["street_number"] or None) == (finding.get("street_number") or None)
            if p["found"] and same_label and (same_number or len(tiles) > 1):
                x, y, _, _ = offsets[tile]
                pts.append((x + p["x"], y + p["y"]))
                break
    if pts:
        return {
            "px": sum(p[0] for p in pts) / len(pts),
            "py": sum(p[1] for p in pts) / len(pts),
            "method": "point pass",
            "uncertainty_px": 100,
        }
    if use_ocr:
        wanted = [w for w in label_words(finding["label"]) if len(w) >= 4]
        for tile in tiles:
            hits = [
                b
                for b in ocr_boxes(tile_dir / tile)
                if any(_word_match(b["text"], w) for w in wanted)
            ]
            if hits:
                b = max(hits, key=lambda b: b["confidence"])
                x, y, _, _ = offsets[tile]
                return {
                    "px": x + b["x"] + b["w"] / 2,
                    "py": y + b["y"] + b["h"] / 2,
                    "method": "ocr",
                    "uncertainty_px": 60,
                }
    # A building read on several tiles sits in their overlap: use that rectangle.
    rects = [offsets[t] for t in tiles]
    x0, y0 = max(r[0] for r in rects), max(r[1] for r in rects)
    x1, y1 = min(r[0] + r[2] for r in rects), min(r[1] + r[3] for r in rects)
    if x1 <= x0 or y1 <= y0:  # not overlapping (a merged chain): use the first tile
        x0, y0, w, h = rects[0]
        x1, y1 = x0 + w, y0 + h
    frac = _fraction(finding.get("position") or "")
    w, h = x1 - x0, y1 - y0
    fx, fy = frac or (0.5, 0.5)
    # In a 128 px overlap strip only the long side is unknown, and the first tile's words
    # still describe it (neighbors across a vertical edge share the same rows).
    fx, fy = (fx if w > 400 else 0.5), (fy if h > 400 else 0.5)
    if len(tiles) > 1:
        method, unc = "tile overlap", (0.25 if frac else 0.5) * max(w, h)
    elif frac:
        method, unc = "position words", 0.25 * max(w, h)
    else:
        method, unc = "tile center", 0.5 * max(w, h)
    return {"px": x0 + fx * w, "py": y0 + fy * h, "method": method, "uncertainty_px": unc}
