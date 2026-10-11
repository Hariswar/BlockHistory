"""Send one map tile to the vision model and print what it extracted.

python scripts/read_tile.py data/tiles/rolla-mo/1948-06/04849_1948-0002/04849_1948-0002_r2_c1.jpg
"""

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from blockhistory.map_reader.extract import read_tile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tile", type=Path)
    args = parser.parse_args()

    load_dotenv()
    result = read_tile(args.tile)
    ext = result["extraction"]

    print(f"{args.tile.name}  model={result['model']}  cached={result['cached']}")
    print(f"tokens in/out: {result['usage']['input_tokens']}/{result['usage']['output_tokens']}")
    print(f"streets: {', '.join(ext['streets'])}\n")
    for b in ext["buildings"]:
        addr = " ".join(x for x in (b["street_number"], b["street_name"]) if x) or "?"
        flags = (" [G.T.]" if b["has_gasoline_tank"] else "") + (
            " [partial]" if b["partial"] else ""
        )
        print(
            f"  {addr:<18} {b['label']:<16} {b['use']:<20} {b['construction']:<14} "
            f"{b['confidence']}{flags}"
        )
    for key in ("other_features", "illegible_notes"):
        if ext[key]:
            print(f"\n{key}: {json.dumps(ext[key], indent=2)}")


if __name__ == "__main__":
    main()
