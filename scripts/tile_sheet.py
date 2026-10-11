"""Cut downloaded sheets into tiles under data/tiles/<city>/<edition>/<sheet_id>/.

python scripts/tile_sheet.py data/sheets/rolla-mo/1948-06/04849_1948-0002.jpg
python scripts/tile_sheet.py data/sheets/rolla-mo/1948-06/*.jpg
"""

import argparse
from pathlib import Path

from blockhistory.collector.tiling import tile_sheet

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sheets", nargs="+", type=Path)
    args = parser.parse_args()

    for sheet in args.sheets:
        sheet = sheet.resolve()
        # data/sheets/<city>/<edition>/<id>.jpg -> data/tiles/<city>/<edition>/<id>/
        city, edition = sheet.parent.parent.name, sheet.parent.name
        out_dir = ROOT / "data" / "tiles" / city / edition / sheet.stem
        tiles = tile_sheet(sheet, out_dir)
        print(f"{sheet.name}: {len(tiles)} tiles -> {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
