"""Hand corrections to located findings, from config/corrections/<area>-<edition>.json.

Checking listings against the full-resolution scan turns up reads that are wrong (a street
name read as a business), repeats, misplaced points, misread labels, and plant names the
reader skipped. Fixing them in the tile results would be undone by the next read, so they
live in one reviewed file that the database build applies:

- "hide": drop the finding (not stored at all).
- "set": change fields: "new_label", "use", "gasoline_tank_count", or "sheet_px" (moves it).
- "add": a finding the reader missed, placed by hand.

A finding is matched by sheet number, printed label and the nearest position to "near" (50%
sheet image pixels, within MATCH_PX). Entries that match nothing are reported, so a re-read
that changes a label doesn't silently drop a fix.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from blockhistory.georef.transform import in_outline

ROOT = Path(__file__).resolve().parents[2]
MATCH_PX = 150
HAND_PLACED_M = 5  # a point placed by eye on the building


def load(area: str, edition: str) -> dict:
    path = ROOT / "config" / "corrections" / f"{area}-{edition}.json"
    return json.loads(path.read_text()) if path.exists() else {}


def _norm(label: str) -> str:
    return "".join(c for c in label.upper() if c.isalnum())


def _find(findings: list[dict], entry: dict) -> dict | None:
    same = [f for f in findings if _norm(f["label"]) == _norm(entry["label"])]
    near = [(math.dist(f["sheet_px"], entry["near"]), id(f), f) for f in same]
    near = [n for n in near if n[0] <= MATCH_PX]
    return min(near)[2] if near else None


def _place(f: dict, px: list[float], panels: list) -> bool:
    """Put f at sheet pixel px using the panel that contains it."""
    panel = next((p for p in panels if in_outline(p[1], px[0], px[1])), None)
    if panel is None:
        return False
    pid, _, t = panel
    f["panel"] = pid
    f["lat"], f["lon"] = (round(v, 7) for v in t.to_latlon(*px))
    f["sheet_px"] = [round(px[0]), round(px[1])]
    f["location_method"] = "hand-placed"
    f["uncertainty_m"] = HAND_PLACED_M
    return True


def apply(
    findings: list[dict], corrections: dict, sheet_number: int, panels: list
) -> tuple[list[dict], list[str]]:
    """Return (corrected findings, problems). `panels` is georef_sheet.load_panels()."""
    problems = []

    def mine(kind: str) -> list[dict]:
        return [e for e in corrections.get(kind, []) if e["sheet"] == sheet_number]

    hidden = set()
    for e in mine("hide"):
        f = _find(findings, e)
        if f is None:
            problems.append(f"hide: no match for {e['label']!r} near {e['near']}")
        else:
            hidden.add(id(f))
    out = [f for f in findings if id(f) not in hidden]
    for e in mine("set"):
        f = _find(out, e)
        if f is None:
            problems.append(f"set: no match for {e['label']!r} near {e['near']}")
            continue
        if "new_label" in e:
            f["label"] = e["new_label"]
        for key in ("use", "gasoline_tank_count"):
            if key in e:
                f[key] = e[key]
        if "sheet_px" in e and not _place(f, e["sheet_px"], panels):
            problems.append(f"set: {e['sheet_px']} is outside every panel")
    for e in mine("add"):
        f = {
            "label": e["label"],
            "use": e["use"],
            "street_number": e.get("street_number"),
            "gasoline_tank_count": e.get("gasoline_tank_count", 0),
            "confidence": None,
            "tiles": [],
        }
        if _place(f, e["sheet_px"], panels):
            out.append(f)
        else:
            problems.append(f"add: {e['label']!r} at {e['sheet_px']} is outside every panel")
    return out, problems
