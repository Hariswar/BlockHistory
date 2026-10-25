"""Check the live website against saved answers: pages, searches, map coverage and map images.

    python scripts/check_live.py                 # exit 1 if anything differs from evals/live.json
    python scripts/check_live.py --update        # save today's answers (after a data reload)
    python scripts/check_live.py --site http://localhost:3000

Run weekly by .github/workflows/weekly.yml. The data only changes when it is reloaded, so any
difference means something broke: the database was emptied or half-loaded, the city address
service changed, the Library of Congress image server moved, or a deploy failed. Free: a dozen
requests to the site and one to the Library of Congress.
"""

import argparse
import json
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parent.parent
SAVED = ROOT / "evals" / "live.json"
SITE = "https://block-history.vercel.app"
PAGES = ["/", "/streets", "/streets/south-broadway", "/about", "/accuracy", "/limits", "/status"]
# A filling station with state tank records; the example on the home page; a tin shop on all
# three maps; and an address outside the mapped area.
SEARCHES = ["6532 S Broadway", "7313 S Broadway", "6725 S Broadway", "1200 Market St"]
SLOW_S = 15


def get(site: str, path: str) -> requests.Response:
    return requests.get(site + path, timeout=30, headers={"User-Agent": "BlockHistory check"})


def answer(site: str, q: str) -> tuple[dict, list[str]]:
    """What a search shows, in the terms that would change if something broke, and its map crops."""
    r = get(site, f"/api/search?q={quote(q)}")
    r.raise_for_status()
    body = r.json()
    crops = [f["sourceCrop"] for f in body["findings"]]
    years = sorted({s["year"] for s in body["coveredBy"]})
    return {
        "located by": body["point"]["source"],
        "map years": years,
        "past uses": {y: sum(f["year"] == y for f in body["findings"]) for y in years},
        "uses": sorted({f"{f['year']} {f['title']}" for f in body["findings"]}),
        "state records": len(body["records"]),
    }, crops


def measure(site: str) -> tuple[dict, list[str]]:
    now: dict = {"pages": {}, "searches": {}}
    slow = []
    for p in PAGES:
        start = time.time()
        now["pages"][p] = get(site, p).status_code
        if time.time() - start > SLOW_S:
            slow.append(f"{p} took {time.time() - start:.0f} s")
    crops = []
    for q in SEARCHES:
        now["searches"][q], found = answer(site, q)
        crops += found
    sheets = get(site, "/api/coverage").json()["sheets"]
    now["map sections"] = dict(sorted(Counter(s["year"] for s in sheets).items()))
    now["bad input"] = get(site, "/api/search?q=x").status_code
    # One map crop from the Library of Congress, as a listing card loads it.
    img = requests.get(crops[0], timeout=60)
    now["map image"] = f"{img.status_code} {img.headers.get('content-type', '')}"
    return now, slow


def compare(now: dict, saved: dict) -> list[str]:
    problems = []
    for key in ("pages", "searches"):
        for name, want in saved[key].items():
            got = now[key].get(name)
            if got != want:
                problems.append(f"{name}: expected {json.dumps(want)}, got {json.dumps(got)}")
    for key in ("map sections", "bad input", "map image"):
        if now[key] != saved[key]:
            problems.append(f"{key}: expected {saved[key]}, got {now[key]}")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--site", default=SITE)
    parser.add_argument("--update", action="store_true", help="save these answers as expected")
    args = parser.parse_args()
    now, slow = measure(args.site.rstrip("/"))
    for p, code in now["pages"].items():
        print(f"  {code}  {p}")
    for q, a in now["searches"].items():
        counts = ", ".join(f"{y}: {n}" for y, n in a["past uses"].items()) or "outside the maps"
        print(f"  {q:18} {a['located by']:7} {counts}; {a['state records']} state records")
    print(f"  map sections {now['map sections']}; map image {now['map image']}")
    for s in slow:
        print(f"  slow: {s}")
    if args.update:
        SAVED.write_text(json.dumps({"date": str(date.today()), **now}, indent=1) + "\n")
        print(f"saved: {SAVED.relative_to(ROOT)}")
        return
    if not SAVED.exists():
        raise SystemExit("no saved answers yet: run with --update")
    problems = compare(now, json.loads(SAVED.read_text()))
    if problems:
        print("DIFFERENT FROM evals/live.json:\n  " + "\n  ".join(problems))
        sys.exit(1)
    print("OK: the live site gives the saved answers")


if __name__ == "__main__":
    main()
