"""Merge each sheet's tile results and write a spot-check checklist to evals/spotcheck/.

    python scripts/sheet_report.py carondelet 1938 50 53 57 62 74 47 49 56 61 67
    python scripts/sheet_report.py carondelet 1950 24 58 --as-shown

--as-shown lists what the website shows for a georeferenced sheet instead: hand corrections
applied, repeat reads merged, high and medium only. Its ticks match the database rows.

Sheets with hand labels in evals/labels/ also get a comparison: which hand-labeled sites
the reader found anywhere on the sheet, and whether gas tanks landed on the right site.
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from georef_sheet import load_panels, located_findings

from blockhistory.db import corrections, store
from blockhistory.map_reader import tanks
from blockhistory.map_reader.scoring import is_found, label_words, tank_count
from blockhistory.map_reader.sheets import merge_sheet

ROOT = Path(__file__).resolve().parent.parent
LABELS = ROOT / "evals" / "labels"
OUT = ROOT / "evals" / "spotcheck"


def compare(findings: list[dict], hand: list[dict]) -> dict:
    words = [set(label_words(f"{f['label']} {f['use']}")) for f in findings]
    all_words = set().union(*words) if words else set()
    missed = [h for h in hand if not is_found(h["label"], all_words)]
    tank_sites = [h for h in hand if tank_count(h) > 0]
    tank_found = [
        h
        for h in tank_sites
        if any(
            f["gasoline_tank_count"] and is_found(h["label"], w) for f, w in zip(findings, words)
        )
    ]
    return {"missed": missed, "tank_sites": tank_sites, "tank_found": tank_found}


def addr(f: dict) -> str:
    return " ".join(x for x in (f.get("street_number"), f.get("street_name")) if x) or "—"


def shown_sites(area: str, edition: str, sheet: int) -> list[dict]:
    """The sheet's sites as build_db.py stores them, high and medium only."""
    sid, located = located_findings(area, edition, sheet, use_ocr=True)
    panels = load_panels(area, edition, sid)
    located, _ = corrections.apply(located, corrections.load(area, edition), sheet, panels)
    sites = []
    for pid, _, _ in panels:
        sites += store.prepare_sites([f for f in located if f["panel"] == pid])
    return [f for f in sites if f["relevance"] in ("high", "medium")]


def write_report(area: str, edition: str, sheet: int, as_shown: bool = False) -> dict:
    tile_dir = next((ROOT / "data" / "tiles" / area / edition).glob(f"*-{sheet:04d}"))
    merged = merge_sheet(tile_dir)
    tank_info = tanks.apply(merged["findings"], tile_dir)  # no-op if the tank pass hasn't run
    merged["usd"] += tank_info["usd"]
    if as_shown:
        merged["findings"] = shown_sites(area, edition, sheet)
    order = {"high": 0, "medium": 1, "low": 2}
    merged["findings"].sort(
        key=lambda f: (order[f["relevance"]], -f["gasoline_tank_count"], f["label"])
    )
    sid = merged["sheet_id"]
    results_dir = ROOT / "data" / "results" / area / edition
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / f"{sid}.json").write_text(json.dumps(merged, indent=2) + "\n")

    f_all = merged["findings"]
    lines = [
        f"# Spot check: {sid} ({area}, {edition})",
        "",
        (
            f"Generated {date.today()} from {merged['tiles_read']} tiles"
            f" (${merged['usd']:.4f}). Map: data/sheets/{area}/{edition}/{sid}.jpg"
        ),
        "",
        "Tick **ok** if the finding is on the map as described, **wrong** if not. Check the",
        "high-relevance rows first. 'OCR' = Tesseract also saw the label's words (free check).",
        "",
    ]
    if merged["tiles_missing"]:
        lines += [f"**Not read yet:** {len(merged['tiles_missing'])} tiles", ""]

    hand_path = LABELS / f"{sid}.json"
    summary = {
        "sheet": sid,
        "findings": len(f_all),
        "high": sum(f["relevance"] == "high" for f in f_all),
        "usd": merged["usd"],
    }
    if hand_path.exists():
        hand = json.loads(hand_path.read_text())["buildings"]
        c = compare(f_all, hand)
        found = len(hand) - len(c["missed"])
        summary.update(
            hand=len(hand),
            found=found,
            tank_sites=len(c["tank_sites"]),
            tank_found=len(c["tank_found"]),
        )
        lines += [
            "## Against your hand labels",
            f"- Labels found anywhere on the sheet: **{found} / {len(hand)}**",
            (
                f"- Gas-tank sites with a tank on the right building: "
                f"**{len(c['tank_found'])} / {len(c['tank_sites'])}**"
            ),
        ]
        if c["missed"]:
            lines.append(
                "- Missed: "
                + "; ".join(f"{h['label']} ({h['contamination_relevance']})" for h in c["missed"])
            )
        missed_tanks = [h for h in c["tank_sites"] if h not in c["tank_found"]]
        if missed_tanks:
            lines.append(
                "- Tank sites without a tank: "
                + "; ".join(f"{h['label']} x{tank_count(h)}" for h in missed_tanks)
            )
        lines.append("")

    lines += [
        "## Findings",
        "",
        "| ok | wrong | relevance | label | use | address | G.T. | conf. | OCR | tiles |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for f in f_all:
        tiles = ", ".join(t.rsplit("_", 2)[1] + "_" + t.rsplit("_", 2)[2][:-4] for t in f["tiles"])
        lines.append(
            f"| [ ] | [ ] | {f['relevance']} | {f['label']} | {f['use']} | {addr(f)} | "
            f"{f['gasoline_tank_count'] or ''} | {f.get('confidence') or 'added by hand'} | "
            f"{'yes' if f.get('ocr_seen') else ''} | {tiles} |"
        )
    lines += ["", "## Notes", "", "- "]
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{sid}.md"
    if out.exists() and "[x]" in out.read_text().lower():
        out = OUT / f"{sid}.new.md"  # never overwrite a checklist you've started ticking
    out.write_text("\n".join(lines) + "\n")
    summary["report"] = str(out.relative_to(ROOT))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("area")
    parser.add_argument("edition")
    parser.add_argument("sheets", nargs="+", type=int)
    parser.add_argument("--as-shown", action="store_true", help="list what the website shows")
    args = parser.parse_args()

    print(
        f"{'sheet':<20} {'findings':>8} {'high':>5} {'hand found':>11} {'tank sites':>11} {'$':>8}"
    )
    for n in args.sheets:
        s = write_report(args.area, args.edition, n, args.as_shown)
        hand = f"{s['found']}/{s['hand']}" if "hand" in s else "—"
        tanks = f"{s['tank_found']}/{s['tank_sites']}" if "hand" in s else "—"
        print(
            f"{s['sheet']:<20} {s['findings']:>8} {s['high']:>5} {hand:>11} {tanks:>11} "
            f"{s['usd']:>8.4f}  {s['report']}"
        )


if __name__ == "__main__":
    main()
