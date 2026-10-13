"""Read whole sheets with Haiku through the Batch API (half price).

    python scripts/run_batch.py submit carondelet 1938 50 53 57 62 74 47 49 56 61 67
    python scripts/run_batch.py submit carondelet 1938 50 53 --tanks
    python scripts/run_batch.py status <batch_id>
    python scripts/run_batch.py collect <batch_id> [--wait]

Tiles already read (cached) are skipped, so re-submitting never pays twice. Collected
results land in the same cache read_tile.py uses; then run sheet_report.py.

--tanks runs the gas-tank second pass instead: it needs the first pass to be collected,
downloads the tiles with a fuel or vehicle finding at full resolution (4 crops each), and
counts tank circles there. evaluate.py and sheet_report.py use the counts when present.
"""

import argparse
import time
from pathlib import Path

from dotenv import load_dotenv

from blockhistory import costs
from blockhistory.map_reader import batch, tanks

ROOT = Path(__file__).resolve().parent.parent


def sheet_tiles(area: str, edition: str, sheets: list[int]) -> list[Path]:
    tiles = []
    for n in sheets:
        dirs = sorted((ROOT / "data" / "tiles" / area / edition).glob(f"*-{n:04d}*"))
        if not dirs:
            raise SystemExit(
                f"sheet {n}: no tiles under data/tiles/{area}/{edition} (tile it first)"
            )
        for d in dirs:
            tiles += sorted(d.glob("*.jpg"))
    return tiles


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("submit")
    s.add_argument("area")
    s.add_argument("edition")
    s.add_argument("sheets", nargs="+", type=int)
    s.add_argument("--model")
    s.add_argument("--effort")
    s.add_argument("--dry-run", action="store_true", help="show the estimate, send nothing")
    s.add_argument("--tanks", action="store_true", help="gas-tank second pass")
    for name in ("status", "collect"):
        c = sub.add_parser(name)
        c.add_argument("batch_id")
        if name == "collect":
            c.add_argument("--wait", action="store_true", help="poll until the batch ends")
    args = parser.parse_args()
    load_dotenv()

    if args.cmd == "submit":
        tiles = sheet_tiles(args.area, args.edition, args.sheets)
        reader = tanks if args.tanks else batch.extract
        model, effort = reader.resolve(args.model, args.effort)
        if args.tanks:
            picked = [
                t for d in sorted({t.parent for t in tiles}) for t in tanks.candidate_tiles(d)
            ]
            print(f"{len(picked)} of {len(tiles)} tiles have a fuel or vehicle finding")
            if args.dry_run:  # estimate without downloading the full-resolution crops
                est = batch.estimate_usd(4 * len(picked), model, reader)
                print(f"up to {4 * len(picked)} crops; {model}/{effort}; est. ${est:.3f}")
                return
            tiles = [c for t in picked for c in tanks.crops_for(t)]
        todo = [t for t in tiles if not reader.cache_path(t, model, effort).exists()]
        est = batch.estimate_usd(len(todo), model, reader)
        print(f"{len(tiles)} images, {len(todo)} not read yet; {model}/{effort}; est. ${est:.3f}")
        if args.dry_run:
            return
        m = batch.submit(tiles, model, effort, reader=reader)
        if m["batch_id"]:
            print(f"submitted batch {m['batch_id']}")
            print(f"next: python scripts/run_batch.py collect {m['batch_id']} --wait")
        else:
            print("nothing to send; every tile is already read")
        return

    if args.cmd == "status":
        b = batch.status(args.batch_id)
        print(b.processing_status, b.request_counts)
        return

    while True:
        b = batch.status(args.batch_id)
        if b.processing_status == "ended" or not args.wait:
            break
        c = b.request_counts
        print(f"{b.processing_status}: {c.processing} processing, {c.succeeded} done")
        time.sleep(30)
    if b.processing_status != "ended":
        print(f"still {b.processing_status}; run again later (or add --wait)")
        return
    summary = batch.collect(args.batch_id)
    print(
        f"saved {summary['saved']}, already saved {summary['already_saved']}, "
        f"failed {len(summary['failed'])}"
    )
    for cid, why in summary["failed"].items():
        print(f"  failed {cid}: {why}")
    print(
        f"this month ${costs.month_spend():.3f} of ${costs.monthly_cap():.2f}; "
        f"project ${costs.total_spend():.3f} of ${costs.total_cap():.2f}"
    )


if __name__ == "__main__":
    main()
