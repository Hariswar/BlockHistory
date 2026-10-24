"""Find past uses within 100 m of an address.

    python scripts/search_address.py "7313 S Broadway"
    python scripts/search_address.py "7313 S Broadway" --radius 150 --all

The address is located with the free US Census geocoder (St. Louis, MO is added), which
is approximate: 30-80 m off on the buildings checked so far.
"""

import argparse

from blockhistory.db import store
from blockhistory.georef.geocode import geocode


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("address")
    parser.add_argument("--radius", type=float, default=100, help="meters (default 100)")
    parser.add_argument("--all", action="store_true", help="include low-relevance findings")
    args = parser.parse_args()

    query = args.address if "," in args.address else f"{args.address}, St. Louis, MO"
    pos = geocode(query)
    if pos is None:
        raise SystemExit(f"Census geocoder found no match for {query!r}")
    levels = ("high", "medium", "low") if args.all else store.SHOWN
    res = store.search(store.connect(), *pos, radius_m=args.radius, levels=levels)
    print(f"{query} -> {pos[0]:.6f}, {pos[1]:.6f}")
    if not res["covered_by"]:
        print("No processed map covers this address yet, so there is nothing to report either way.")
        return
    sheets = ", ".join(f"{s['edition']} sheet {s['sheet_number']}" for s in res["covered_by"])
    print(f"Covered by: {sheets}. {len(res['findings'])} past uses within {args.radius:.0f} m:")
    for f in res["findings"]:
        tanks = "  [gasoline tanks]" if f["gasoline_tank_count"] else ""
        print(
            f"  {f['distance_m']:4} m  {f['relevance']:6} {f['label']} ({f['use']}){tanks}"
            f"  - {f['review_status'].replace('_', ' ')}"
        )


if __name__ == "__main__":
    main()
