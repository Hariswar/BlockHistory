"""Day 7: run one tile through the free readers and compare with the hand labels. Costs $0.

    python scripts/free_read_tile.py data/tiles/carondelet/1938/04858_12_1938-0050/04858_12_1938-0050_r3_c0.jpg
    python scripts/free_read_tile.py <tile> --vision     # also ask the Ollama vision model

Tesseract runs locally. --vision needs an Ollama server: on this laptop, or on a free
Colab GPU with OLLAMA_HOST set to its URL (docs/free-models.md).
"""

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from blockhistory.map_reader.ocr import read_tile_ocr
from blockhistory.map_reader.scoring import is_found, label_words, norm, tank_count

LABELS = Path("evals/labels")


def expected_labels(tile: Path) -> list[dict]:
    """Hand-labeled buildings in this tile: `position` or an optional `tile` field names it.

    Entries positioned by city block ("block 3012") can't be matched to a tile.
    """
    sheet_id, row, col = tile.stem.rsplit("_", 2)
    path = LABELS / f"{sheet_id}.json"
    if not path.exists():
        return []
    doc = json.loads(path.read_text())
    want = f"tile {row}_{col}"
    return [b for b in doc["buildings"] if want in (b.get("position"), f"tile {b.get('tile')}")]


def report(expected: list[dict], found: set[str], gas_tanks: int | None = None) -> None:
    """Print which hand-labeled buildings a reader found, by matching label words."""
    for b in expected:
        mark = "found" if is_found(b["label"], found) else "MISSED"
        print(f"   [{mark:6}] {b['label']}  ({b['contamination_relevance']})")
    if gas_tanks is not None:
        sites = sum(tank_count(b) > 0 for b in expected)
        symbols = sum(tank_count(b) for b in expected)
        print(
            f"   gas tanks: hand labels have {sites} site(s) with {symbols} G.T. symbol(s); "
            f"reader marked {gas_tanks} building(s) with a tank"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tile", type=Path)
    parser.add_argument("--vision", action="store_true", help="also run the Ollama vision model")
    args = parser.parse_args()
    load_dotenv()

    expected = expected_labels(args.tile)
    words = read_tile_ocr(args.tile)
    found = {norm(w["text"]) for w in words}

    print(f"== Tesseract: {len(words)} words")
    print("   " + ", ".join(f"{w['text']} ({w['confidence']})" for w in words))
    if not expected:
        print(
            "\n(No hand labels with this tile's position. Labels positioned by block can't be"
            ' matched to a tile; add a "tile" field to compare.)'
        )
    if expected:
        print(f"\n== Hand labels in this tile: {len(expected)}")
        report(expected, found)

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
        if result.get("truncated"):
            print(
                f"   WARNING: reply was cut off ({result.get('done_reason')}); "
                "only complete entries kept"
            )
        if result.get("duplicates_removed"):
            print(f"   WARNING: removed {result['duplicates_removed']} repeated entries")
        if expected:
            print("\n== Vision model vs hand labels")
            vision_words = {
                w for b in ext["buildings"] for w in label_words(f"{b['label']} {b['use']}")
            }
            report(expected, vision_words, sum(b["has_gasoline_tank"] for b in ext["buildings"]))


if __name__ == "__main__":
    main()
