"""Georeference a later edition by aligning its scans to an already georeferenced edition.

    python scripts/align_edition.py carondelet 1938 1950 22 23 24 ...

The 1938-1950 volume is the 1938 sheets with paste-over corrections, so the streets are in
the same place on the paper; only the scan differs (framing, a little scale and rotation).
For each control point of the earlier edition, this finds the same spot on the later scan:

1. Whole-sheet match (ORB features + RANSAC, shift + scale + rotation) predicts where it is.
2. A patch around the point (the street corner) is searched for near that prediction
   (normalized cross-correlation). A weak match keeps the prediction and says so: a
   paste-over can cover a corner.

It writes config/georef/<area>/<later>/<sheet>.points with the same real-world positions,
panel outlines and fit model, and prints the leave-one-out error like georef_sheet.py fit.
Needs opencv-python (the "vision" extra).
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from georef_sheet import panel_id, report

from blockhistory.georef.transform import (
    GCP,
    read_model,
    read_outline,
    read_points,
    write_points,
)

ROOT = Path(__file__).resolve().parent.parent
PATCH = 90  # half-size of the corner patch, 50% image pixels (~9 m at 50 ft to the inch)
SEARCH = 60  # how far from the whole-sheet prediction to look
MIN_SCORE = 0.6  # weaker matches keep the prediction


def image(area: str, edition: str, sheet_id: str) -> np.ndarray:
    path = ROOT / "data" / "sheets" / area / edition / f"{sheet_id}.jpg"
    return cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)


def sheet_transform(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, int]:
    """2x3 matrix taking pixels of a to pixels of b, and the number of agreeing features."""
    orb = cv2.ORB_create(8000)
    ka, da = orb.detectAndCompute(a, None)
    kb, db = orb.detectAndCompute(b, None)
    matches = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(da, db)
    pa = np.float32([ka[m.queryIdx].pt for m in matches])
    pb = np.float32([kb[m.trainIdx].pt for m in matches])
    m, inliers = cv2.estimateAffinePartial2D(pa, pb, ransacReprojThreshold=4.0)
    return m, int(inliers.sum())


def apply(m: np.ndarray, x: float, y: float) -> tuple[float, float]:
    return float(m[0, 0] * x + m[0, 1] * y + m[0, 2]), float(m[1, 0] * x + m[1, 1] * y + m[1, 2])


def refine(a: np.ndarray, b: np.ndarray, pa: tuple, pb: tuple) -> tuple[tuple, float]:
    """Find a's patch around pa inside b near pb. Returns (point in b, match score)."""
    ax, ay = round(pa[0]), round(pa[1])
    bx, by = round(pb[0]), round(pb[1])
    tpl = a[max(0, ay - PATCH) : ay + PATCH, max(0, ax - PATCH) : ax + PATCH]
    r = PATCH + SEARCH
    win = b[max(0, by - r) : by + r, max(0, bx - r) : bx + r]
    if tpl.shape[0] < 2 * PATCH or tpl.shape[1] < 2 * PATCH or win.shape[0] <= tpl.shape[0]:
        return pb, 0.0  # too close to the sheet edge to compare
    if win.shape[1] <= tpl.shape[1]:
        return pb, 0.0
    res = cv2.matchTemplate(win, tpl, cv2.TM_CCOEFF_NORMED)
    _, score, _, (mx, my) = cv2.minMaxLoc(res)
    x = max(0, bx - r) + mx + (ax - max(0, ax - PATCH))
    y = max(0, by - r) + my + (ay - max(0, ay - PATCH))
    return (float(x), float(y)), float(score)


def align_sheet(area: str, earlier: str, later: str, n: int) -> None:
    folder = ROOT / "config" / "georef" / area / earlier
    files = sorted(folder.glob(f"*-{n:04d}.points")) + sorted(folder.glob(f"*-{n:04d}.*.points"))
    if not files:
        print(f"sheet {n}: no {earlier} control points")
        return
    sid_a = files[0].name.split(".")[0]
    sid_b = sid_a.replace(f"_{earlier}-", f"_{later}-")
    a, b = image(area, earlier, sid_a), image(area, later, sid_b)
    m, agree = sheet_transform(a, b)
    scale = float(np.hypot(m[0, 0], m[1, 0]))
    print(f"\n{sid_b}: whole-sheet match from {agree} features, scale {scale:.4f}")
    for path in files:
        out = ROOT / "config" / "georef" / area / later / path.name.replace(sid_a, sid_b)
        gcps, kept = read_points(path), []
        for g in gcps:
            predicted = apply(m, g.px, g.py)
            (x, y), score = refine(a, b, (g.px, g.py), predicted)
            moved = float(np.hypot(x - predicted[0], y - predicted[1]))
            if score < MIN_SCORE:
                x, y = predicted
                note = f"weak match ({score:.2f}): kept the whole-sheet prediction"
            else:
                note = f"match {score:.2f}, {moved:.0f} px from prediction"
            print(f"  {g.name:34} {note}")
            kept.append(GCP(round(x, 1), round(y, 1), g.lat, g.lon, g.name, g.enabled))
        outline = read_outline(path)
        if outline:
            outline = [tuple(round(v) for v in apply(m, x, y)) for x, y in outline]
        write_points(out, kept, outline, read_model(path))
        print(f"  -> {out.relative_to(ROOT)}  ({panel_id(out)})")
        report(kept, read_model(path))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("area")
    parser.add_argument("earlier")
    parser.add_argument("later")
    parser.add_argument("sheets", nargs="+", type=int)
    args = parser.parse_args()
    for n in args.sheets:
        align_sheet(args.area, args.earlier, args.later, n)


if __name__ == "__main__":
    main()
