"""Help pick control points: a gridded preview of a sheet, and snapping to street crossings.

    # 1. Look at the sheet with a labeled pixel grid (50% image coordinates).
    python scripts/georef_preview.py grid carondelet 1908 80

    # 2. Snap rough intersection guesses to the center of the street crossing, and draw
    #    each one on a crop to check by eye. Prints the snapped "Name/Name@x,y" arguments
    #    for georef_sheet.py gcps.
    python scripts/georef_preview.py snap carondelet 1908 80 "Robert Av/Minnesota Av@590,375" ...

    # 3. Better on a regular grid: name each street with its rough position (H = runs
    #    across the sheet, at y; V = runs down, at x). The street's center line is measured
    #    every 40 px along it and fitted as a line; control points are where lines cross.
    #    "V:Idaho Av@2140/1973-3956" measures only from y 1973 to 3956 (one panel).
    python scripts/georef_preview.py lines carondelet 1908 80 "H:Robert Av@386" "V:Minnesota Av@572" ...

Snapping looks for the blank bands that streets make between blocks: within a window
around the guess, rows (and columns) with almost no ink or color are street, and the
crossing is the middle of the nearest horizontal and vertical band. It assumes the street
grid runs along the sheet edges, as on most Sanborn sheets; if no band is found the guess
is kept and marked "not snapped". Images go to data/georef_preview/ (free, no API calls).
"""

import argparse
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "georef_preview"
WINDOW = 260  # half-size of the snapping window, 50% pixels
BLANK = 0.04  # a street row/column has less than this share of marked pixels
MIN_BAND = 25  # narrowest street band accepted, 50% pixels


def sheet_image(area: str, edition: str, n: int) -> Path:
    return next((ROOT / "data" / "sheets" / area / edition).glob(f"*-{n:04d}.jpg"))


def marked(rgb: np.ndarray) -> np.ndarray:
    """Pixels that aren't paper: ink, building colors, text."""
    r, g, b = (rgb[..., i].astype(int) for i in range(3))
    gray = (r + g + b) / 3
    saturation = rgb.max(axis=2).astype(int) - rgb.min(axis=2).astype(int)
    paper = np.median(gray)
    return (gray < paper - 45) | (saturation > 60)


# Marked runs this thin between two blank ones count as street (a water pipe drawn down the
# middle). Off by default: it also merges streets with empty yards beside them. Turn it on
# per sheet with GEOREF_THIN=8 when a pipe line splits a street (1908 sheet 65).
THIN = int(os.environ.get("GEOREF_THIN", "0"))


def _band(profile: np.ndarray, center: int) -> tuple[int, int] | None:
    """The run of blank entries nearest to `center` that is at least MIN_BAND long. A thin
    marked run between two blank ones (a pipe line drawn down the street) counts as blank."""
    blank = profile < BLANK
    i = 0
    while i < len(blank):
        if not blank[i]:
            j = i
            while j < len(blank) and not blank[j]:
                j += 1
            if 0 < i and j < len(blank) and j - i <= THIN:
                blank[i:j] = True
            i = j
        else:
            i += 1
    runs, start = [], None
    for i, b in enumerate([*blank, False]):
        if b and start is None:
            start = i
        elif not b and start is not None:
            if i - start >= MIN_BAND:
                runs.append((start, i - 1))
            start = None
    if not runs:
        return None
    return min(
        runs,
        key=lambda r: 0 if r[0] <= center <= r[1] else min(abs(r[0] - center), abs(r[1] - center)),
    )


def snap(img: np.ndarray, x: int, y: int) -> tuple[int, int, bool]:
    h, w = img.shape[:2]
    x0, x1 = max(0, x - WINDOW), min(w, x + WINDOW)
    y0, y1 = max(0, y - WINDOW), min(h, y + WINDOW)
    m = marked(img[y0:y1, x0:x1])
    rows = _band(m.mean(axis=1), y - y0)
    cols = _band(m.mean(axis=0), x - x0)
    if rows is None or cols is None:
        return x, y, False
    return x0 + (cols[0] + cols[1]) // 2, y0 + (rows[0] + rows[1]) // 2, True


STRIP = 25  # half-width of each sample strip across a street, 50% pixels
STEP = 40  # distance between samples along a street
INLIER_PX = 6  # a sample this close to the fitted line counts
MAX_SLOPE = 0.2  # steepest street accepted (~11 degrees off the sheet edge)


def _street_line(
    img: np.ndarray, across: bool, pos: int, span: tuple[int, int] | None = None
) -> tuple[float, float, int, float]:
    """Fit a street's center line near `pos`: (a, b, samples, spread px), where for a street
    running across the sheet y = a + b*x, and for one running down x = a + b*y."""
    a = img if across else img.transpose(1, 0, 2)  # rows along the street's length
    length, depth = a.shape[1], a.shape[0]
    lo, hi = max(0, pos - WINDOW), min(depth, pos + WINDOW)
    t, c = [], []
    first, last = span or (0, length)
    for u in range(max(STRIP, first), min(length - STRIP, last), STEP):
        prof = marked(a[lo:hi, u - STRIP : u + STRIP]).mean(axis=1)
        band = _band(prof, pos - lo)
        # A band that fills the window is a crossing street or the margin: no edge to measure.
        if band is None or band[0] == 0 or band[1] == hi - lo - 1:
            continue
        t.append(u)
        c.append(lo + (band[0] + band[1]) / 2)
    t, c = np.array(t, float), np.array(c, float)
    if len(t) < 4:
        return float(pos), 0.0, len(t), float("nan")
    # Consensus fit: of many lines through two samples, keep the one most samples lie within
    # INLIER_PX of (labels, hydrants, pipes and missing blocks give stray samples).
    rng = np.random.default_rng(0)
    best = np.zeros(len(t), bool)
    for _ in range(400):
        i, j = rng.choice(len(t), 2, replace=False)
        if t[i] == t[j]:
            continue
        b = (c[j] - c[i]) / (t[j] - t[i])
        if abs(b) > MAX_SLOPE:  # streets run near the sheet edges
            continue
        inl = np.abs(c - (c[i] + b * (t - t[i]))) <= INLIER_PX
        if inl.sum() > best.sum():
            best = inl
    if best.sum() < 4:
        return float(pos), 0.0, int(best.sum()), float("nan")
    b, a0 = np.polyfit(t[best], c[best], 1)
    spread = float(np.std(c[best] - (a0 + b * t[best])))
    return float(a0), float(b), int(best.sum()), spread


def lines(area: str, edition: str, n: int, specs: list[str]) -> Path:
    im = Image.open(sheet_image(area, edition, n)).convert("RGB")
    arr = np.asarray(im)
    across, down = [], []
    for spec in specs:
        kind, rest = spec.split(":", 1)
        name, where = rest.rsplit("@", 1)
        # "@pos" or "@pos/from-to": measure only between from and to along the street
        # (one panel of a sheet drawn in two parts).
        pos, _, rng = where.partition("/")
        span = tuple(int(v) for v in rng.split("-")) if rng else None
        a0, b, k, spread = _street_line(arr, kind.upper() == "H", int(pos), span)
        (across if kind.upper() == "H" else down).append((name, a0, b))
        flag = "" if k >= 8 and spread <= 6 else "   <- weak: check"
        print(f"  {kind}:{name:28} {k:3} samples, spread {spread:4.1f} px{flag}")
    w, h = im.size
    k = 1400 / w
    small = im.resize((1400, round(h * k)))
    d = ImageDraw.Draw(small)
    for name, a0, b in across:
        d.line([(0, a0 * k), (w * k, (a0 + b * w) * k)], fill=(255, 0, 0), width=1)
    for name, a0, b in down:
        d.line([(a0 * k, 0), ((a0 + b * h) * k, h * k)], fill=(255, 0, 0), width=1)
    out = []
    for hn, ha, hb in across:
        for vn, va, vb in down:
            # y = ha + hb*x and x = va + vb*y
            y = (ha + hb * va) / (1 - hb * vb)
            x = va + vb * y
            if 0 <= x < w and 0 <= y < h:
                out.append(f'"{hn}/{vn}@{round(x)},{round(y)}"')
                d.ellipse(
                    (x * k - 5, y * k - 5, x * k + 5, y * k + 5), outline=(0, 0, 255), width=2
                )
    print(" ".join(out))
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{edition}-{n:04d}-lines.jpg"
    small.save(path, quality=85)
    return path


def grid(area: str, edition: str, n: int, width: int = 1400) -> Path:
    im = Image.open(sheet_image(area, edition, n)).convert("RGB")
    k = width / im.width
    small = im.resize((width, round(im.height * k)))
    d = ImageDraw.Draw(small)
    for v in range(0, max(im.size), 250):
        d.line([(v * k, 0), (v * k, small.height)], fill=(0, 120, 255), width=1)
        d.line([(0, v * k), (small.width, v * k)], fill=(0, 120, 255), width=1)
        if v % 500 == 0:
            d.text((v * k + 2, 2), str(v), fill=(0, 0, 255))
            d.text((2, v * k + 2), str(v), fill=(0, 0, 255))
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{edition}-{n:04d}-grid.jpg"
    small.save(path, quality=85)
    return path


def snap_points(area: str, edition: str, n: int, specs: list[str]) -> Path:
    im = Image.open(sheet_image(area, edition, n)).convert("RGB")
    arr = np.asarray(im)
    tiles = []
    for spec in specs:
        names, xy = spec.rsplit("@", 1)
        x, y = (int(float(v)) for v in xy.split(","))
        sx, sy, ok = snap(arr, x, y)
        print(f'"{names}@{sx},{sy}"' + ("" if ok else "   # not snapped"))
        R = 220
        crop = im.crop((sx - R, sy - R, sx + R, sy + R)).resize((300, 300))
        d = ImageDraw.Draw(crop)
        k = 300 / (2 * R)
        gx, gy = (x - sx + R) * k, (y - sy + R) * k
        d.ellipse((gx - 4, gy - 4, gx + 4, gy + 4), outline=(0, 0, 255), width=2)  # guess
        d.line((140, 150, 160, 150), fill=(255, 0, 0), width=2)  # snapped
        d.line((150, 140, 150, 160), fill=(255, 0, 0), width=2)
        d.text((3, 3), names[:40], fill=(0, 0, 255))
        tiles.append(crop)
    cols = 4
    sheet = Image.new("RGB", (cols * 300, ((len(tiles) + cols - 1) // cols) * 300), "white")
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * 300, (i // cols) * 300))
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{edition}-{n:04d}-snap.jpg"
    sheet.save(path, quality=85)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("grid")
    s = sub.add_parser("snap")
    ln = sub.add_parser("lines")
    for p in (g, s, ln):
        p.add_argument("area")
        p.add_argument("edition")
        p.add_argument("sheet", type=int)
    s.add_argument("points", nargs="+", help='"Street/Street@x,y" rough guesses')
    ln.add_argument("streets", nargs="+", help='"H:Street@y" or "V:Street@x"')
    args = parser.parse_args()
    if args.cmd == "grid":
        print(grid(args.area, args.edition, args.sheet))
    elif args.cmd == "snap":
        print(snap_points(args.area, args.edition, args.sheet, args.points))
    else:
        print(lines(args.area, args.edition, args.sheet, args.streets))


if __name__ == "__main__":
    main()
