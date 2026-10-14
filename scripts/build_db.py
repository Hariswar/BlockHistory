"""Load every georeferenced sheet's findings into the database (week 10).

    python scripts/build_db.py carondelet 1938            # -> data/blockhistory.sqlite
    python scripts/build_db.py carondelet 1938 --export   # + data/export/load_postgis.sql

A sheet is included when config/georef/<area>/<edition>/<sheet>.points exists. Re-running
replaces each sheet's rows. Free: uses only cached results (the first OCR read of a tile
runs Tesseract locally).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from georef_sheet import located_findings

from blockhistory.db import store

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("area")
    parser.add_argument("edition")
    parser.add_argument("--export", action="store_true", help="also write the PostGIS SQL")
    args = parser.parse_args()

    con = store.connect()
    points = sorted((ROOT / "config" / "georef" / args.area / args.edition).glob("*.points"))
    if not points:
        raise SystemExit("no georeferenced sheets yet (see scripts/georef_sheet.py)")
    for p in points:
        n = int(p.stem.rsplit("-", 1)[1])
        sid, findings = located_findings(args.area, args.edition, n, use_ocr=True)
        rows = store.load_sheet(con, args.area, args.edition, sid, findings)
        print(f"{sid}: {rows} sites ({len(findings)} findings before merging repeats)")
    shown = con.execute(
        "SELECT relevance, review_status, COUNT(*) FROM findings GROUP BY 1, 2 ORDER BY 1, 2"
    ).fetchall()
    for r in shown:
        print(f"  {r[0]:7} {r[1]:14} {r[2]}")
    print(f"database: {store.DB_PATH.relative_to(ROOT)}")
    if args.export:
        out = ROOT / "data" / "export" / "load_postgis.sql"
        n = store.export_postgis_sql(con, out)
        print(f"PostGIS export: {n} findings -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
