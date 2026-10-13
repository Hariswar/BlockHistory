"""Combine one sheet's tile results into a single list of findings.

Tiles overlap by >=128 px, so a building near a tile edge is often read twice. Entries
with the same label (and the same street number, when both have one) on neighboring
tiles are merged. Each finding also records whether Tesseract saw the label's words in
one of its tiles: a free, independent check that the label is really printed there.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from blockhistory.map_reader import extract
from blockhistory.map_reader.ocr import read_tile_ocr
from blockhistory.map_reader.relevance import relevance
from blockhistory.map_reader.scoring import label_words, norm

OCR_CACHE = Path(__file__).resolve().parents[2] / "data" / "cache" / "ocr"
CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}


def ocr_words(tile: Path) -> set[str]:
    """Tesseract words for a tile, cached by image hash."""
    key = hashlib.sha256(tile.read_bytes()).hexdigest()[:32]
    path = OCR_CACHE / f"{key}.json"
    if path.exists():
        return set(json.loads(path.read_text()))
    words = sorted({norm(w["text"]) for w in read_tile_ocr(tile)})
    OCR_CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(words))
    return set(words)


def _tile_rc(tile_name: str) -> tuple[int, int]:
    row, col = tile_name.rsplit("_", 2)[1:]
    return int(row[1:]), int(col[1:].split(".")[0])


def _same(a: dict, b: dict) -> bool:
    if norm(a["label"]) != norm(b["label"]):
        return False
    # Merge only when both have the same number or both have none. A numbered and an
    # unnumbered read of the same label can be two different sites (sheet 47 has two
    # FILL'G STA.: one at 6601, one unnumbered), and a lost site is worse than a duplicate.
    na, nb = a.get("street_number"), b.get("street_number")
    if bool(na) != bool(nb) or (na and nb and norm(na) != norm(nb)):
        return False
    return any(
        abs(r1 - r2) <= 1 and abs(c1 - c2) <= 1
        for r1, c1 in map(_tile_rc, a["tiles"])
        for r2, c2 in map(_tile_rc, b["tiles"])
    )


def merge_sheet(
    tile_dir: Path, model: str | None = None, effort: str | None = None, ocr: bool = True
) -> dict:
    """Findings for one sheet from its cached tile results. Tiles not read yet are listed."""
    tiles = sorted(tile_dir.glob("*.jpg"))
    findings: list[dict] = []
    missing, cost = [], 0.0
    for tile in tiles:
        result = extract.load_cached(tile, model, effort)
        if result is None:
            missing.append(tile.name)
            continue
        cost += result["usd"]
        seen = ocr_words(tile) if ocr else set()
        for b in result["extraction"]["buildings"]:
            entry = {**b, "tiles": [tile.name], "ocr_seen": None}
            if ocr:
                entry["ocr_seen"] = any(
                    w == f or (len(f) >= 4 and f in w)
                    for w in label_words(b["label"])
                    for f in seen
                )
            match = next((f for f in findings if _same(f, entry)), None)
            if match is None:
                findings.append(entry)
                continue
            match["tiles"].append(tile.name)
            match["gasoline_tank_count"] = max(
                match["gasoline_tank_count"], entry["gasoline_tank_count"]
            )
            match["street_number"] = match["street_number"] or entry["street_number"]
            match["partial"] = match["partial"] and entry["partial"]
            if CONFIDENCE_RANK[entry["confidence"]] > CONFIDENCE_RANK[match["confidence"]]:
                match["confidence"] = entry["confidence"]
            if ocr:
                match["ocr_seen"] = match["ocr_seen"] or entry["ocr_seen"]
    for f in findings:
        f["relevance"] = relevance(f["label"], f["use"])
    order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: (order[f["relevance"]], -f["gasoline_tank_count"], f["label"]))
    return {
        "sheet_id": tile_dir.name,
        "tiles_read": len(tiles) - len(missing),
        "tiles_missing": missing,
        "usd": round(cost, 6),
        "findings": findings,
    }
