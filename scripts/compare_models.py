"""Run the same labeled tiles through several models and compare accuracy against cost.

Rough scoring: the share of hand-labeled business labels and gas tanks (G.T.) in each tile
that the model also found. The full precision/recall eval comes in week 7.

    python scripts/compare_models.py                     # 3 default tiles, Haiku and Sonnet
    python scripts/compare_models.py --models claude-haiku-5-5 claude-sonnet-5-5
"""

import argparse
import json
import re
from pathlib import Path

from dotenv import load_dotenv

from blockhistory import costs
from blockhistory.map_reader.extract import read_tile

LABELS = Path("evals/labels")
TILES = Path("data/tiles")
TILES_PER_AREA = 1480  # Carondelet: 1938 + 1950 editions, 74 sheets each x 20 tiles
# Carondelet 1938 tiles with the high-priority finds: filling stations with G.T.S, a bulk
# oil station, an oil house, the Laclede Gas coke plant (tar, benzol, ammonia tanks).
DEFAULT_TILES = ["04858_12_1938-0050_r3_c2", "04858_12_1938-0050_r3_c0", "04858_12_1938-0050_r1_c2"]


def _norm(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def _expected(tile_name: str) -> list[dict]:
    sheet_id, row, col = tile_name.rsplit("_", 2)
    tile = f"{row}_{col}"
    doc = json.loads((LABELS / f"{sheet_id}.json").read_text())
    want = f"tile {tile}"
    return [b for b in doc["buildings"] if want in (b.get("position"), f"tile {b.get('tile')}")]


def _score(expected: list[dict], found: list[dict]) -> tuple[int, int, int, int]:
    found_labels = [_norm(b["label"]) for b in found]
    hits = sum(
        1
        for e in expected
        # Hand labels like "OFF. / LODGE HALL 2ND" match if any part was found.
        if any(
            part and any(part in f or f in part for f in found_labels if f)
            for part in (_norm(p) for p in e["label"].split("/"))
        )
    )
    gt_expected = sum(
        int(e.get("gasoline_tank_count", e.get("has_gasoline_tank", 0))) > 0 for e in expected
    )
    gt_found = min(gt_expected, sum(b["has_gasoline_tank"] for b in found))
    return hits, len(expected), gt_found, gt_expected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tiles", nargs="+", default=DEFAULT_TILES)
    parser.add_argument("--models", nargs="+", default=sorted(costs.PRICES))
    parser.add_argument("--effort", default="low")
    args = parser.parse_args()
    load_dotenv()

    print(f"{'model':<20} {'labels':>8} {'G.T.':>6} {'$/tile':>8} {'Area (batch)':>13}")
    for model in args.models:
        hits = total = gt_hits = gt_total = 0
        spent = 0.0
        for name in args.tiles:
            tile = next(TILES.glob(f"*/*/{name.rsplit('_', 2)[0]}/{name}.jpg"))
            result = read_tile(tile, model=model, effort=args.effort)
            # Cached runs report the original cost so the comparison stays fair.
            spent += result["usd"]
            h, t, gh, gt = _score(_expected(name), result["extraction"]["buildings"])
            hits, total, gt_hits, gt_total = hits + h, total + t, gt_hits + gh, gt_total + gt
        per_tile = spent / len(args.tiles)
        area = per_tile * TILES_PER_AREA * costs.BATCH_DISCOUNT
        print(
            f"{model:<20} {hits:>3}/{total:<4} {gt_hits:>2}/{gt_total:<3} "
            f"{per_tile:>8.4f} {area:>12.2f}"
        )
    print(
        f"\nThis month: ${costs.month_spend():.2f} of ${costs.monthly_cap():.2f}; "
        f"project: ${costs.total_spend():.2f} of ${costs.total_cap():.2f}"
    )


if __name__ == "__main__":
    main()
