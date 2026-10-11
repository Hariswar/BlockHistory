"""Day 7: run one tile through the free readers and compare with the hand labels. Costs $0.

    python scripts/free_read_tile.py data/tiles/carondelet/1938/04858_12_1938-0050/04858_12_1938-0050_r3_c0.jpg
    python scripts/free_read_tile.py <tile> --vision     # also ask the Ollama vision model

Tesseract runs locally. --vision needs an Ollama server: on this laptop, or on a free
Colab GPU with OLLAMA_HOST set to its URL (docs/free-models.md).
"""

import argparse
import json
import re
from pathlib import Path

from dotenv import load_dotenv

from blockhistory.map_reader.ocr import read_tile_ocr

LABELS = Path("evals/labels")


def _norm(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def expected_labels(tile: Path) -> list[dict]:
    """Hand-labeled buildings whose position is this tile (empty if the sheet isn't labeled)."""
    sheet_id, row, col = tile.stem.rsplit("_", 2)
    path = LABELS / f"{sheet_id}.json"
    if not path.exists():
        return []
    doc = json.loads(path.read_text())
    return [b for b in doc["buildings"] if b["position"] == f"tile {row}_{col}"]


def label_words(label: str) -> list[str]:
    # 'GRINDING 1ST / DRYING 2 & 3RD' -> ['GRINDING', 'DRYING'] (words with 3+ letters)
    return [w for w in (_norm(t) for t in label.split()) if sum(c.isalpha() for c in w) >= 3]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tile", type=Path)
    parser.add_argument("--vision", action="store_true", help="also run the Ollama vision model")
    args = parser.parse_args()
    load_dotenv()

    expected = expected_labels(args.tile)
    words = read_tile_ocr(args.tile)
    found = {_norm(w["text"]) for w in words}

    print(f"== Tesseract: {len(words)} words")
    print("   " + ", ".join(f"{w['text']} ({w['confidence']})" for w in words))
    if expected:
        print(f"\n== Hand labels in this tile: {len(expected)}")
        for b in expected:
            ws = label_words(b["label"])
            # Exact word, or a 4+ letter fragment of it ("MACH" for "MACHS"); 3-letter
            # fragments like "LAY" matched too much by accident.
            hit = [w for w in ws if any(w == f or (len(f) >= 4 and f in w) for f in found)]
            mark = "found" if hit else "MISSED"
            print(f"   [{mark:6}] {b['label']}  ({b['contamination_relevance']})")

    if args.vision:
        from blockhistory.map_reader.free_vision import read_tile_free

        result = read_tile_free(args.tile)
        ext = result["extraction"]
        print(
            f"\n== Vision model {result['model']}: {len(ext['buildings'])} buildings, "
            f"{result.get('seconds', '?')} s, $0"
        )
        for b in ext["buildings"]:
            addr = " ".join(x for x in (b["street_number"], b["street_name"]) if x) or "?"
            print(f"   {b['label']:<28} {b['use']:<24} {addr:<20} {b['confidence']}")
        if ext["illegible_notes"]:
            print(f"   illegible: {ext['illegible_notes']}")


if __name__ == "__main__":
    main()
