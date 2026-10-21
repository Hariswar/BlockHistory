"""Score the map reader against the hand labels in evals/labels/ (week 7 baseline).

    python scripts/evaluate.py carondelet 1938

Uses only cached results (no API calls, $0). For every sheet that has both hand labels
and read tiles, it reports:

- recall: hand-labeled sites the reader found anywhere on the sheet
- precision: findings flagged high/medium relevance that are a hand-labeled site
- gas tanks: tank sites where the reader put a tank on that site, exact counts, and
  tanks reported on sites with none
- the free Tesseract baseline: hand-labeled sites whose words OCR saw on the sheet
- cost per sheet, and precision of the high rows you ticked in evals/spotcheck/

Gas-tank second-pass counts (run_batch.py submit --tanks) are used when cached; add
--no-tank-pass to score the first pass alone.

Writes evals/reports/<date>-<area>-<edition>.md and a .json next to it.
"""

import argparse
import json
import re
from datetime import date
from pathlib import Path

from blockhistory.map_reader import tanks
from blockhistory.map_reader.relevance import relevance
from blockhistory.map_reader.scoring import is_found, label_words, match_sheet, tank_count
from blockhistory.map_reader.sheets import merge_sheet, ocr_words

ROOT = Path(__file__).resolve().parent.parent
LABELS = ROOT / "evals" / "labels"
SPOTCHECK = ROOT / "evals" / "spotcheck"
REPORTS = ROOT / "evals" / "reports"
FLAGGED = ("high", "medium")


def pct(a: int, b: int) -> str:
    return f"{a}/{b} ({100 * a / b:.0f}%)" if b else "—"


def spotcheck_ticks(sheet_id: str) -> tuple[int, int]:
    """(ok, wrong) ticks on high rows of a spot-check checklist."""
    path = SPOTCHECK / f"{sheet_id}.md"
    ok = wrong = 0
    if path.exists():
        for line in path.read_text().splitlines():
            m = re.match(r"\| \[(.)\] \| \[(.)\] \| high \|", line)
            if m:
                ok += m.group(1).lower() == "x"
                wrong += m.group(2).lower() == "x"
    return ok, wrong


def score_sheet(tile_dir: Path, labels: dict, tank_pass: bool = True) -> dict:
    merged = merge_sheet(tile_dir)
    findings = merged["findings"]
    tank_info = tanks.apply(findings, tile_dir) if tank_pass else {"tiles": 0, "usd": 0.0}
    for f in findings:  # recomputed, so relevance fixes apply without re-merging
        f["relevance"] = relevance(f["label"], f["use"])
    hand = labels["buildings"]
    match = match_sheet(findings, hand)

    found = {i for i in match if i is not None}
    flagged = [k for k, f in enumerate(findings) if f["relevance"] in FLAGGED]
    true_flags = [k for k in flagged if match[k] is not None]
    # A plant's parts (CUPOLA, SECTION 1) are often labeled on their own. Named in a site's
    # map_notes, they are a correct read of that site: right for precision, not recall.
    part_of = [
        k
        for k in flagged
        if match[k] is None
        and any(
            is_found(h.get("map_notes", ""), set(label_words(findings[k]["label"]))) for h in hand
        )
    ]
    seen: set[int] = set()
    duplicates = 0
    for k in true_flags:
        duplicates += match[k] in seen
        seen.add(match[k])
    out_of_scope = labels.get("out_of_scope_seen", [])
    false_flags = [
        {
            "label": findings[k]["label"],
            "relevance": findings[k]["relevance"],
            "address": findings[k]["street_number"],
            "out_of_scope": any(
                is_found(o.split(",")[0], set(label_words(findings[k]["label"])))
                for o in out_of_scope
            ),
        }
        for k in flagged
        if match[k] is None and k not in part_of
    ]

    tank_sites = [i for i, h in enumerate(hand) if tank_count(h) > 0]
    reported = {i: 0 for i in range(len(hand))}
    extra_tanks = []
    for k, f in enumerate(findings):
        n = f["gasoline_tank_count"]
        if not n:
            continue
        i = match[k]
        if i is None or tank_count(hand[i]) == 0:
            extra_tanks.append(f"{f['label']} x{n}")
        else:
            reported[i] = max(reported[i], n)
    tanks_hand = sum(tank_count(hand[i]) for i in tank_sites)

    ocr_seen: set[str] = set()
    for tile in tile_dir.glob("*.jpg"):
        ocr_seen |= ocr_words(tile)
    high = [i for i, h in enumerate(hand) if h["contamination_relevance"] == "high"]
    ok, wrong = spotcheck_ticks(merged["sheet_id"])
    return {
        "sheet": merged["sheet_id"],
        "status": labels.get("verification", {}).get("status", "unknown"),
        "tiles_read": merged["tiles_read"],
        "tiles_missing": len(merged["tiles_missing"]),
        "usd": merged["usd"] + tank_info["usd"],
        "tank_pass_tiles": tank_info["tiles"],
        "sites": len(hand),
        "found": len(found),
        "high_sites": len(high),
        "high_found": len(found & set(high)),
        "flagged": len(flagged),
        "flagged_true": len(true_flags) + len(part_of),
        "flagged_part_of": len(part_of),
        "duplicates": duplicates,
        "tank_sites": len(tank_sites),
        "tank_sites_found": sum(reported[i] > 0 for i in tank_sites),
        "tank_counts_exact": sum(reported[i] == tank_count(hand[i]) for i in tank_sites),
        "tanks_hand": tanks_hand,
        "tanks_reported_on_sites": sum(reported[i] for i in tank_sites),
        "extra_tanks": extra_tanks,
        "ocr_found": sum(is_found(h["label"], ocr_seen) for h in hand),
        "missed": [
            f"{h['label']} ({h['contamination_relevance']})"
            for i, h in enumerate(hand)
            if i not in found
        ],
        "tank_misses": [
            f"{hand[i]['label']} {hand[i]['street_number'] or ''}: map {tank_count(hand[i])}, "
            f"read {reported[i]}"
            for i in tank_sites
            if reported[i] != tank_count(hand[i])
        ],
        "false_flags": false_flags,
        "spotcheck_ok": ok,
        "spotcheck_wrong": wrong,
    }


def total(rows: list[dict]) -> dict:
    keys = [k for k, v in rows[0].items() if isinstance(v, (int, float)) and k != "status"]
    return {k: sum(r[k] for r in rows) for k in keys}


def summary_lines(name: str, rows: list[dict]) -> list[str]:
    t = total(rows)
    fp_scope = sum(f["out_of_scope"] for r in rows for f in r["false_flags"])
    ticks = t["spotcheck_ok"] + t["spotcheck_wrong"]
    return [
        f"### {name} ({len(rows)} sheets, {t['tiles_read']} tiles)",
        "",
        "| measure | Haiku 5.5 (low, batch) | Tesseract (free) |",
        "|---|---|---|",
        (
            f"| Recall: hand-labeled sites found | {pct(t['found'], t['sites'])} | "
            f"{pct(t['ocr_found'], t['sites'])} |"
        ),
        f"| Recall: high-relevance sites | {pct(t['high_found'], t['high_sites'])} | — |",
        (
            f"| Precision: high/medium flags that are a labeled site | "
            f"{pct(t['flagged_true'], t['flagged'])} | — |"
        ),
        f"| … of those, parts of a labeled plant (CUPOLA, SECTION 1) | {t['flagged_part_of']} | — |",
        f"| … of those, duplicate reads of a site | {t['duplicates']} | — |",
        f"| … wrong flags that are real but out of scope | {fp_scope} | — |",
        (
            f"| Gas-tank sites with a tank on the right site | "
            f"{pct(t['tank_sites_found'], t['tank_sites'])} | 0/{t['tank_sites']} |"
        ),
        (
            f"| Gas-tank sites with the exact count | {pct(t['tank_counts_exact'], t['tank_sites'])} "
            "| — |"
        ),
        (
            f"| Gas tanks: map vs read on those sites | {t['tanks_hand']} vs "
            f"{t['tanks_reported_on_sites']} | — |"
        ),
        (
            f"| Tanks reported on sites with none | {sum(len(r['extra_tanks']) for r in rows)} "
            "findings | — |"
        ),
        f"| Spot-checked high rows marked ok | {pct(t['spotcheck_ok'], ticks)} | — |",
        f"| Cost | ${t['usd']:.4f} total, ${t['usd'] / len(rows):.4f}/sheet | $0 |",
        "",
    ]


def score_edition(area: str, edition: str, tank_pass: bool = True) -> list[dict]:
    """score_sheet() for every sheet of the edition that has hand labels and read tiles."""
    tile_root = ROOT / "data" / "tiles" / area / edition
    rows = []
    for path in sorted(LABELS.glob("*.json")):
        tile_dir = tile_root / path.stem
        if path.stem.startswith("_") or not tile_dir.is_dir():
            continue
        if not any(tile_dir.glob("*.jpg")):
            continue
        r = score_sheet(tile_dir, json.loads(path.read_text()), tank_pass=tank_pass)
        if r["tiles_read"]:
            rows.append(r)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("area")
    parser.add_argument("edition")
    parser.add_argument("--no-tank-pass", action="store_true", help="first pass only")
    args = parser.parse_args()

    rows = score_edition(args.area, args.edition, tank_pass=not args.no_tank_pass)
    if not rows:
        raise SystemExit("no sheet has both hand labels and read tiles")

    verified = [r for r in rows if r["status"] == "human_verified"]
    draft = [r for r in rows if r["status"] != "human_verified"]
    lines = [
        f"# Map reader accuracy: {args.area} {args.edition}",
        "",
        f"Generated {date.today()} by `scripts/evaluate.py` from cached results ($0 to run).",
        (
            f"Gas-tank second pass: used on {sum(r['tank_pass_tiles'] for r in rows)} tiles."
            if not args.no_tank_pass
            else "Gas-tank second pass: off (first pass only)."
        ),
        "Sites are hand-labeled contamination-relevant uses (see each label file's `scope`).",
        "Draft label files have not been checked by a person yet, so their numbers can move.",
        "",
        "## Summary",
        "",
    ]
    if verified:
        lines += summary_lines("Human-verified labels", verified)
    if draft:
        lines += summary_lines("Draft labels (AI-assisted, unverified)", draft)
    lines += summary_lines("All labeled sheets", rows)
    lines += [
        "## Per sheet",
        "",
        (
            "| sheet | labels | recall | high recall | precision | dup. | tank sites | exact | "
            "OCR recall | $ |"
        ),
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['sheet'][-4:]} | {r['status'].replace('human_verified', 'verified')} | "
            f"{pct(r['found'], r['sites'])} | {pct(r['high_found'], r['high_sites'])} | "
            f"{pct(r['flagged_true'], r['flagged'])} | {r['duplicates']} | "
            f"{pct(r['tank_sites_found'], r['tank_sites'])} | "
            f"{pct(r['tank_counts_exact'], r['tank_sites'])} | "
            f"{pct(r['ocr_found'], r['sites'])} | {r['usd']:.4f} |"
        )
    lines += ["", "## Details", ""]
    for r in rows:
        lines += [f"### {r['sheet']}", ""]
        if r["missed"]:
            lines.append("- Missed: " + "; ".join(r["missed"]))
        if r["tank_misses"]:
            lines.append("- Tank counts off: " + "; ".join(r["tank_misses"]))
        if r["extra_tanks"]:
            lines.append("- Tanks on a site with none: " + "; ".join(r["extra_tanks"]))
        if r["false_flags"]:
            lines.append(
                "- Flags that are not a labeled site: "
                + "; ".join(
                    f"{f['label']} ({f['relevance']}{', out of scope' if f['out_of_scope'] else ''})"
                    for f in r["false_flags"]
                )
            )
        lines.append("")

    REPORTS.mkdir(parents=True, exist_ok=True)
    stem = f"{date.today()}-{args.area}-{args.edition}" + (
        "-first-pass" if args.no_tank_pass else ""
    )
    (REPORTS / f"{stem}.md").write_text("\n".join(lines))
    (REPORTS / f"{stem}.json").write_text(json.dumps(rows, indent=2) + "\n")
    print("\n".join(lines[: lines.index("## Per sheet")]))
    print(f"report: evals/reports/{stem}.md")


if __name__ == "__main__":
    main()
