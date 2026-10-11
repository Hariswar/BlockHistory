"""List a city's Sanborn editions and save every sheet URL to config/cities/<slug>.json.

python scripts/list_sheets.py --city rolla --state missouri --slug rolla-mo
"""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from blockhistory.collector.loc import list_sheets, search_editions

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config" / "cities"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--city", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--slug", required=True, help="config file name, e.g. rolla-mo")
    args = parser.parse_args()

    editions = search_editions(args.city, args.state)
    print(f"{len(editions)} editions for {args.city.title()}, {args.state.title()}")

    config_path = CONFIG_DIR / f"{args.slug}.json"
    config = json.loads(config_path.read_text()) if config_path.exists() else {}
    config.update({"city": args.city.title(), "state": args.state.title(), "editions": []})

    for ed in editions:
        sheets = list_sheets(ed.item_id)
        ed.sheet_count = len(sheets)
        print(f"  {ed.date}  {ed.item_id}  {len(sheets)} sheet images")
        config["editions"].append({**asdict(ed), "sheets": [asdict(s) for s in sheets]})

    config_path.write_text(json.dumps(config, indent=2) + "\n")
    print(f"Wrote {config_path}")


if __name__ == "__main__":
    main()
