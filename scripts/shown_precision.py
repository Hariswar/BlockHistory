"""How many shown listings are right as read, judged by the scan checks.

    python scripts/shown_precision.py carondelet 1938 1950 [--sheets 9 10 ...] [--list wrong]

Every shown listing on a checked sheet has a judgment: a "hide" entry in
config/corrections/<area>-<edition>.json, or a spot-check tick of "wrong", means it was wrong
as read; anything else shown was right (a "set" entry fixes details of a real site). This
scores the reader plus the relevance rules before any hand correction, so a rule change can be
measured against every listing ever checked, not just the 10 hand-labeled sheets.
"""

import argparse
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from georef_sheet import load_panels, located_findings

from blockhistory.db import corrections, store
from blockhistory.map_reader.scoring import norm

ROOT = Path(__file__).resolve().parent.parent
SHOWN = ("high", "medium")


def judged_sheets(area: str, edition: str) -> list[int]:
    """Sheets whose shown listings were all checked: listed in config/corrections/checked.txt."""
    path = ROOT / "config" / "corrections" / "checked.txt"
    out = []
    for line in path.read_text().splitlines():
        parts = line.split("#")[0].split()
        if len(parts) >= 3 and parts[0] == area and parts[1] == edition:
            out += [int(n) for n in parts[2:]]
    return out


def score(area: str, edition: str, sheets: list[int]) -> tuple[list[dict], list[dict]]:
    fixes = corrections.load(area, edition)
    right, wrong = [], []
    for n in sheets:
        sid, located = located_findings(area, edition, n, use_ocr=True)
        panels = load_panels(area, edition, sid)
        hides = [e for e in fixes.get("hide", []) if e["sheet"] == n]
        for pid, _, _ in panels:
            marks = store.review_marks(pid)
            for f in store.prepare_sites([dict(f) for f in located if f["panel"] == pid]):
                if f["relevance"] not in SHOWN:
                    continue
                f["sheet"] = n
                hidden = any(
                    norm(e["label"]) == norm(f["label"])
                    and math.dist(e["near"], f["sheet_px"]) <= corrections.MATCH_PX
                    for e in hides
                )
                ticked = (
                    marks.get((norm(f["label"]), store._tiles_key(f["tiles"]))) == "checked_wrong"
                )
                if hidden or ticked:
                    f["why"] = next(
                        (e["why"] for e in hides if norm(e["label"]) == norm(f["label"])),
                        "ticked wrong",
                    )
                    wrong.append(f)
                else:
                    right.append(f)
    return right, wrong


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("area")
    parser.add_argument("editions", nargs="+")
    parser.add_argument("--sheets", nargs="*", type=int)
    parser.add_argument("--list", choices=["wrong", "right"])
    args = parser.parse_args()
    for ed in args.editions:
        sheets = args.sheets or judged_sheets(args.area, ed)
        right, wrong = score(args.area, ed, sheets)
        n = len(right) + len(wrong)
        print(f"{ed}: {len(right)}/{n} shown listings right as read ({len(right) / n:.0%}), "
              f"{len(sheets)} checked sheets")  # fmt: skip
        kinds = Counter(_kind(f["why"]) for f in wrong)
        print("  wrong:", ", ".join(f"{k} {v}" for k, v in kinds.most_common()))
        if args.list:
            for f in wrong if args.list == "wrong" else right:
                print(
                    f"    s{f['sheet']:<3} {f['relevance'][:3]} {f['label'][:40]:40} | {f.get('why', '')[:70]}"
                )


def _kind(why: str) -> str:
    w = why.lower()
    for key, words in [
        ("repeat", ("repeat",)),
        ("construction note", ("construction note", "found'n", "sl. cl", "br. 6")),
        ("private garage", ("private auto house", "private garage")),
        ("not a concern use", ("not a concern use", "school", "dwelling", "locker")),
        ("misplaced", ("placed on", "placed in")),
        ("old print under a patch", ("paste-over",)),
        (
            "not on the map",
            ("not on the map", "no dry cleaner", "no filling", "no gasoline", "no standard"),
        ),
    ]:
        if any(x in w for x in words):
            return key
    return "other"


if __name__ == "__main__":
    main()
