"""Run the same labeled tiles through several models and compare accuracy against cost.

Rough scoring: the share of hand-labeled labels in each tile the model also found, and
how many gas-tank (G.T.) sites it put on the right building.

    python scripts/compare_models.py                     # 3 default tiles, Haiku and Sonnet
    python scripts/compare_models.py --models claude-haiku-5-5 --effort medium -v
"""

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from blockhistory import costs
from blockhistory.map_reader.extract import read_tile
from blockhistory.map_reader.scoring import is_found, label_words, tank_count

LABELS = Path("evals/labels")
TILES = Path("data/tiles")
TILES_PER_AREA = 1480  # Carondelet: 1938 + 1950 editions, 74 sheets each x 20 tiles
# Carondelet 1938 tiles with the high-priority finds: filling stations with G.T.S, a bulk
# oil station, an oil house, the Laclede Gas coke plant (tar, benzol, ammonia tanks).
DEFAULT_TILES = ["04858_12_1938-0050_r3_c2", "04858_12_1938-0050_r3_c0", "04858_12_1938-0050_r1_c2"]


def _expected(tile_name: str) -> list[dict]:
    sheet_id, row, col = tile_name.rsplit("_", 2)
    tile = f"{row}_{col}"
    doc = json.loads((LABELS / f"{sheet_id}.json").read_text())
    want = f"tile {tile}"
    return [b for b in doc["buildings"] if want in (b.get("position"), f"tile {b.get('tile')}")]


def _words(b: dict) -> set[str]:
    return set(label_words(f"{b['label']} {b['use']}"))


def _sheet_tank_sites(tile_name: str) -> list[dict]:
    sheet_id = tile_name.rsplit("_", 2)[0]
    doc = json.loads((LABELS / f"{sheet_id}.json").read_text())
    return [b for b in doc["buildings"] if tank_count(b) > 0]


def _score(expected: list[dict], found: list[dict], sheet_tank_sites: list[dict]) -> dict:
    """Labels found, and gas-tank sites found on the right building.

    A hand-labeled tank site counts as found only if a reader building with tanks matches
    its label. Reader buildings with tanks that match no hand-labeled tank site anywhere on
    the sheet are "extra" (tiles overlap, so a neighbor tile's site can appear here).
    """
    all_words = set().union(*map(_words, found)) if found else set()
    missed = [e["label"] for e in expected if not is_found(e["label"], all_words)]
    tank_sites = [e for e in expected if tank_count(e) > 0]
    tank_buildings = [b for b in found if b["gasoline_tank_count"] > 0]
    gt_hits = sum(any(is_found(e["label"], _words(b)) for b in tank_buildings) for e in tank_sites)
    extra = [
        b["label"]
        for b in tank_buildings
        if not any(is_found(e["label"], _words(b)) for e in sheet_tank_sites)
    ]
    return {
        "hits": len(expected) - len(missed),
        "total": len(expected),
        "gt_hits": gt_hits,
        "gt_total": len(tank_sites),
        "missed": missed,
        "extra_tanks": extra,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tiles", nargs="+", default=DEFAULT_TILES)
    parser.add_argument("--models", nargs="+", default=sorted(costs.PRICES))
    parser.add_argument("--effort", default="low")
    parser.add_argument("-v", "--verbose", action="store_true", help="list misses per tile")
    args = parser.parse_args()
    load_dotenv()

    print(
        f"{'model':<20} {'effort':<7} {'labels':>7} {'G.T. sites':>11} {'extra G.T.':>11} "
        f"{'$/tile':>8} {'Area (batch)':>13}"
    )
    for model in args.models:
        totals = {"hits": 0, "total": 0, "gt_hits": 0, "gt_total": 0, "extra": 0}
        notes = []
        spent = 0.0
        for name in args.tiles:
            tile = next(TILES.glob(f"*/*/{name.rsplit('_', 2)[0]}/{name}.jpg"))
            result = read_tile(tile, model=model, effort=args.effort)
            # Cached runs report the original cost so the comparison stays fair.
            spent += result["usd"]
            sc = _score(_expected(name), result["extraction"]["buildings"], _sheet_tank_sites(name))
            for k in ("hits", "total", "gt_hits", "gt_total"):
                totals[k] += sc[k]
            totals["extra"] += len(sc["extra_tanks"])
            notes.append(f"  {name}: missed {sc['missed']}; extra G.T. on {sc['extra_tanks']}")
        per_tile = spent / len(args.tiles)
        area = per_tile * TILES_PER_AREA * costs.BATCH_DISCOUNT
        labels = f"{totals['hits']}/{totals['total']}"
        sites = f"{totals['gt_hits']}/{totals['gt_total']}"
        print(
            f"{model:<20} {args.effort:<7} {labels:>7} {sites:>11} {totals['extra']:>11} "
            f"{per_tile:>8.4f} {area:>12.2f}"
        )
        if args.verbose:
            print("\n".join(notes))
    print(
        f"\nThis month: ${costs.month_spend():.2f} of ${costs.monthly_cap():.2f}; "
        f"project: ${costs.total_spend():.2f} of ${costs.total_cap():.2f}"
    )


if __name__ == "__main__":
    main()
