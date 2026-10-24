"""One command for every accuracy number, compared with the saved baseline (Phase 2 eval suite).

    python scripts/check_accuracy.py            # print the scores; exit 1 if any got worse
    python scripts/check_accuracy.py --update   # accept the current scores as the new baseline

Run it after any change to the reader, the rules, the tank pass, the corrections or the
control points. It uses only cached results ($0) and checks, for 1938 and 1950:

- the reader against the hand-annotated answer keys (evals/labels/): sites found, high-
  concern sites found, flags that are real sites, tank sites, exact tank counts, and tanks
  put on sites that have none
- every shown listing on the scan-checked sheets: share right as read
  (scripts/shown_precision.py), and listings shown now that weren't when the baseline was
  saved: new and unchecked, so a rule change that lets junk through shows up here
- the hand corrections: every entry still matches a finding
- georeferencing: every panel's median leave-one-out error is under GEOREF_MAX_M
- cost per sheet (shown, never a failure)

A rate may not fall more than RATE_TOLERANCE below the baseline, a count of errors may not
rise, and a stale correction or a bad panel always fails. The baseline is
evals/baseline.json; commit it with the change that moved it.
"""

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate import score_edition
from georef_sheet import load_panels, located_findings, panel_files
from shown_precision import judged_sheets, score

from blockhistory.db import corrections
from blockhistory.georef.transform import leave_one_out, read_model, read_points

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "evals" / "baseline.json"
AREA = "carondelet"
# Years with hand-made answer keys; add one here when its keys exist.
EDITIONS = ("1908", "1938", "1950")
RATE_TOLERANCE = 0.01  # one percentage point
GEOREF_MAX_M = 8.0

# name -> (numerator key, denominator key) in evaluate.py's totals; higher is better
RATES = {
    "sites found": ("found", "sites"),
    "high-concern sites found": ("high_found", "high_sites"),
    "flags that are real sites": ("flagged_true", "flagged"),
    "tank sites found": ("tank_sites_found", "tank_sites"),
    "exact tank counts": ("tank_counts_exact", "tank_sites"),
}


def measure(edition: str) -> dict:
    rows = score_edition(AREA, edition)
    total = {k: sum(r[k] for r in rows) for k in rows[0] if isinstance(rows[0][k], (int, float))}
    out: dict = {
        "keys": f"{len(rows)} sheets, "
        + (
            "human-verified"
            if all(r["status"] == "human_verified" for r in rows)
            else "includes drafts"
        ),
        "rates": {name: [total[a], total[b]] for name, (a, b) in RATES.items() if total.get(b)},
        "errors": {"tanks on sites with none": sum(len(r["extra_tanks"]) for r in rows)},
        "usd_per_sheet": round(total["usd"] / len(rows), 4),
    }
    sheets = judged_sheets(AREA, edition)
    right, wrong = score(AREA, edition, sheets)
    if right or wrong:  # no fully scan-checked sheet yet: no rate
        out["rates"]["listings right as read"] = [len(right), len(right) + len(wrong)]
    out["shown"] = sorted(_key(f) for f in right + wrong)

    fixes = corrections.load(AREA, edition)
    stale = []
    for n in sheets:
        sid, found = located_findings(AREA, edition, n, use_ocr=True)
        _, problems = corrections.apply(found, fixes, n, load_panels(AREA, edition, sid))
        stale += [f"sheet {n}: {p}" for p in problems]
    out["errors"]["stale corrections"] = len(stale)
    out["stale"] = stale

    worst = []
    folder = ROOT / "config" / "georef" / AREA / edition
    sids = sorted({p.name.split(".")[0] for p in folder.glob("*.points")})
    for sid in sids:
        for path in panel_files(AREA, edition, sid):
            loo = leave_one_out(read_points(path), read_model(path))
            worst.append((median(loo), path.name.removesuffix(".points")))
    worst.sort(reverse=True)
    out["georef"] = {
        "panels": len(worst),
        "worst median m": round(worst[0][0], 1),
        "worst panel": worst[0][1],
        "over limit": [f"{n} ({m:.1f} m)" for m, n in worst if m > GEOREF_MAX_M],
    }
    return out


def _key(f: dict) -> str:
    """A shown listing, stable across rebuilds: sheet, label letters, rough position."""
    letters = "".join(c for c in f["label"].upper() if c.isalnum())
    x, y = f["sheet_px"]
    return f"{f['sheet']}|{letters}|{round(x / 40)}|{round(y / 40)}"


def _new_listings(m: dict, old: dict | None) -> list[str]:
    if not old or "shown" not in old:
        return []
    seen = set(old["shown"])
    return [k for k in m["shown"] if k not in seen]


def compare(now: dict, base: dict | None) -> list[str]:
    problems = []
    for ed, m in now.items():
        if m["georef"]["over limit"]:
            problems.append(
                f"{ed}: georeferencing over {GEOREF_MAX_M} m: {m['georef']['over limit']}"
            )
        if m["errors"]["stale corrections"]:
            problems.append(f"{ed}: {m['errors']['stale corrections']} corrections match nothing")
        old = (base or {}).get(ed)
        if not old:
            continue
        new = _new_listings(m, old)
        if new:
            problems.append(
                f"{ed}: {len(new)} shown listings are new since the baseline (check them on the"
                f" scan, then --update): {', '.join(new[:8])}"
            )
        for name, (a, b) in m["rates"].items():
            if name in old["rates"]:
                oa, ob = old["rates"][name]
                if b and ob and a / b < oa / ob - RATE_TOLERANCE:
                    problems.append(f"{ed}: {name} fell from {oa}/{ob} to {a}/{b}")
        for name, n in m["errors"].items():
            if n > old["errors"].get(name, n):
                problems.append(f"{ed}: {name} rose from {old['errors'][name]} to {n}")
    return problems


def show(now: dict, base: dict | None) -> None:
    for ed, m in now.items():
        old = (base or {}).get(ed, {})
        print(f"\n{ed}  (answer keys: {m['keys']})")
        for name, (a, b) in m["rates"].items():
            was = old.get("rates", {}).get(name)
            change = f"   baseline {was[0]}/{was[1]} ({was[0] / was[1]:.0%})" if was else ""
            print(f"  {name:28} {a:>4}/{b:<4} {a / b:6.1%}{change}")
        for name, n in m["errors"].items():
            was = old.get("errors", {}).get(name)
            print(f"  {name:28} {n:>4}{'' if was is None else f'        baseline {was}'}")
        new = _new_listings(m, old)
        print(f"  new listings since baseline  {len(new):>4}")
        g = m["georef"]
        print(
            f"  georeferencing               {g['panels']} panels, worst median {g['worst median m']} m ({g['worst panel']})"
        )
        print(f"  reading cost                 ${m['usd_per_sheet']:.4f} per sheet")
        for s in m["stale"]:
            print(f"    stale: {s}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--update", action="store_true", help="save these scores as the baseline")
    args = parser.parse_args()
    start = time.time()
    now = {ed: measure(ed) for ed in EDITIONS}
    base = json.loads(BASELINE.read_text())["editions"] if BASELINE.exists() else None
    show(now, base)
    problems = compare(now, base)
    print(f"\nchecked in {time.time() - start:.0f} s")
    if args.update:
        hard = [p for p in problems if "georeferencing" in p or "corrections match" in p]
        if hard:
            raise SystemExit("not saved: fix these first:\n  " + "\n  ".join(hard))
        clean = {ed: {k: v for k, v in m.items() if k != "stale"} for ed, m in now.items()}
        print(
            "Saving also marks every listing shown now as checked: run this only after the new"
            " ones were compared with the scans."
        )
        BASELINE.write_text(
            json.dumps({"date": str(date.today()), "editions": clean}, indent=1) + "\n"
        )
        print(f"baseline saved: {BASELINE.relative_to(ROOT)}")
        return
    if problems:
        print("WORSE THAN BASELINE:\n  " + "\n  ".join(problems))
        raise SystemExit(1)
    print("OK: nothing got worse" if base else "no baseline yet: run with --update to save one")


if __name__ == "__main__":
    main()
