"""Download Sanborn sheets listed in a config (run area_config.py or list_sheets.py first).

python scripts/download_sheet.py the-hill --edition 1903           # whole edition
python scripts/download_sheet.py the-hill 04858_10_1903-0009       # one sheet
"""

import argparse
import json
from pathlib import Path

from blockhistory.collector.loc import Sheet, download_sheet

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("city", help="config slug, e.g. the-hill or rolla-mo")
    parser.add_argument("sheet_ids", nargs="*")
    parser.add_argument("--edition", help="download every sheet in this edition date")
    parser.add_argument("--pct", type=int, default=50, help="IIIF scale (100 = full res)")
    args = parser.parse_args()

    # Neighborhood configs (area_config.py) first, then whole-city configs (list_sheets.py).
    paths = [ROOT / "config" / d / f"{args.city}.json" for d in ("neighborhoods", "cities")]
    config_path = next((p for p in paths if p.exists()), None)
    if config_path is None:
        parser.error(f"no config named {args.city}")
    config = json.loads(config_path.read_text())
    sheets = [Sheet(**s) for ed in config["editions"] for s in ed["sheets"]]
    if args.edition:
        sheets = [s for s in sheets if s.edition_date == args.edition]
    elif args.sheet_ids:
        sheets = [s for s in sheets if s.sheet_id in args.sheet_ids]
    else:
        parser.error("give sheet ids or --edition")
    if not sheets:
        parser.error("no matching sheets in config")

    for sheet in sheets:
        out_dir = ROOT / "data" / "sheets" / args.city / sheet.edition_date
        path = download_sheet(sheet, out_dir, pct=args.pct)
        print(f"{sheet.sheet_id} -> {path.relative_to(ROOT)} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
