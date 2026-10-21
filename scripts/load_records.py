"""Load official environmental records (Missouri DNR tank and cleanup sites) into the database.

    python scripts/load_records.py            # Carondelet and Patch, from the cache if present
    python scripts/build_db.py carondelet 1950 --export   # then export as usual

Free: the DNR and City of St. Louis services are public. Downloads and address matches are
cached in data/cache/records/; delete that folder to refetch.
"""

import argparse
from collections import Counter

from blockhistory.db import store
from blockhistory.records import dnr

# Carondelet and Patch, with a margin (west, south, east, north).
CARONDELET = (-90.290, 38.525, -90.225, 38.575)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.parse_args()
    rows = dnr.records(CARONDELET)
    con = store.connect()
    n = store.load_records(con, rows)
    kinds = Counter(
        (r["kind"], "leak/contamination on record" if r["release"] else "no known leak")
        for r in rows
    )
    print(
        f"{n} records loaded: "
        + ", ".join(f"{k[0]} ({k[1]}) {v}" for k, v in sorted(kinds.items()))
    )
    print(f"placed on their parcel: {sum(r['located_by'] == 'parcel' for r in rows)} of {n}")


if __name__ == "__main__":
    main()
