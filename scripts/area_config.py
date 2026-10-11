"""Save chosen sheets from one or more Sanborn volumes to config/neighborhoods/<slug>.json.

Big cities have dozens of volumes, so instead of listing a whole city (list_sheets.py),
pick the sheets that cover a neighborhood from each volume's key map.

python scripts/area_config.py the-hill --name "The Hill, St. Louis" \
    --item sanborn04858_013 --sheets 1 2 3 4 7 8 9 10 13 14 15 19 20 22 24 44
python scripts/area_config.py worlds-fair-1904 --name "1904 World's Fair" --item sanborn04858_002
"""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from blockhistory.collector.loc import list_sheets

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config" / "neighborhoods"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("slug")
    parser.add_argument("--name", required=True)
    parser.add_argument("--item", required=True, help="loc.gov item id, e.g. sanborn04858_013")
    parser.add_argument("--sheets", nargs="*", type=int, help="sheet numbers; default all")
    parser.add_argument(
        "--no-key", action="store_true", help="skip the volume's title/index/key-map pages"
    )
    args = parser.parse_args()

    sheets = list_sheets(args.item)
    chosen = [
        s
        for s in sheets
        if (args.sheets is None or s.sheet_number in args.sheets)
        # Keep title/index pages (no number) and the key map (sheet 0) for reference.
        or (not args.no_key and (s.sheet_number is None or s.sheet_number == 0))
    ]
    missing = sorted(set(args.sheets or []) - {s.sheet_number for s in chosen})
    if missing:
        parser.error(f"sheets not in {args.item}: {missing}")

    config_path = CONFIG_DIR / f"{args.slug}.json"
    config = json.loads(config_path.read_text()) if config_path.exists() else {"editions": []}
    config["name"] = args.name
    edition_date = sheets[0].edition_date
    config["editions"] = [e for e in config["editions"] if e["item_id"] != args.item]
    config["editions"].append(
        {
            "item_id": args.item,
            "date": edition_date,
            "url": sheets[0].item_url,
            "sheet_count": len(chosen),
            "sheets": [asdict(s) for s in chosen],
        }
    )
    config["editions"].sort(key=lambda e: e["date"])
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    print(f"{args.item} ({edition_date}): {len(chosen)} sheets -> {config_path}")


if __name__ == "__main__":
    main()
