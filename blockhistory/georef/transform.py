"""Sheet pixels <-> latitude/longitude from ground control points (GCPs).

A GCP pairs a pixel on the 50% sheet image (data/sheets/...) with the same spot today,
usually a street intersection. GCPs live in config/georef/<area>/<edition>/<sheet>.points
in QGIS's georeferencer format, so they can be made or fixed by hand in QGIS too.
A few sheets hold two separately drawn panels (an inset, or a strip from another part of
town); each panel gets its own file, <sheet>.<panel>.points, with an "#OUTLINE x,y x,y ..."
line: the panel's outline in sheet pixels. The main panel's file can have one too, to
leave out an inset that isn't georeferenced yet.

The fit is affine (shift, scale, rotation, shear) in a local flat projection around the
sheet; one Sanborn sheet covers well under 2 km, so the flat-earth error is negligible.
A "#MODEL similarity" line fits shift, one scale and rotation instead: Sanborn sheets are
drawn to scale with no shear (the affine fits agree to ~2%), and a similarity can be fit
from points along one street, as on a narrow panel where every crossing is on S. Broadway.
Leave-one-out error (refit without each point, measure how far off it lands) is the
honest accuracy number: plain residuals shrink as points are added even when they're bad.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

M_PER_DEG = 111_320.0
HEADER = "mapX,mapY,sourceX,sourceY,enable,dX,dY,residual"


@dataclass
class GCP:
    px: float  # column on the 50% sheet image
    py: float  # row (down is positive)
    lat: float
    lon: float
    name: str = ""
    enabled: bool = True


def read_points(path: Path) -> list[GCP]:
    """QGIS .points: mapX=lon, mapY=lat, sourceX=column, sourceY=-row. '#' lines are comments."""
    gcps, names = [], {}
    for line in path.read_text().splitlines():
        if line.startswith("#NAME "):  # our own comment: "#NAME <index> <name>"
            idx, name = line[6:].split(" ", 1)
            names[int(idx)] = name
        if not line.strip() or line.startswith(("#", "mapX")):
            continue
        f = line.split(",")
        gcps.append(
            GCP(
                px=float(f[2]),
                py=-float(f[3]),
                lat=float(f[1]),
                lon=float(f[0]),
                enabled=f[4] != "0",
            )
        )
    for i, g in enumerate(gcps):
        g.name = names.get(i, "")
    return gcps


Outline = list[tuple[float, float]]


def read_outline(path: Path) -> Outline | None:
    """The panel's outline in sheet pixels from an "#OUTLINE" line, or None (whole sheet)."""
    for line in path.read_text().splitlines():
        if line.startswith("#OUTLINE "):
            return [tuple(float(v) for v in xy.split(",")) for xy in line[9:].split()]
    return None


def parse_outline(text: str) -> Outline:
    """ "x,y x,y ..." -> [(x, y), ...]; "x0,y0,x1,y1" is a box."""
    nums = [float(v) for v in text.replace(" ", ",").split(",") if v]
    if len(nums) == 4 and " " not in text.strip():
        x0, y0, x1, y1 = nums
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return list(zip(nums[::2], nums[1::2]))


def in_outline(outline: Outline | None, px: float, py: float) -> bool:
    if outline is None:
        return True
    inside = False
    for (x1, y1), (x2, y2) in zip(outline, outline[1:] + outline[:1]):
        if (y1 > py) != (y2 > py) and px < x1 + (py - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def read_model(path: Path) -> str:
    """ "affine" (the default) or "similarity", from a "#MODEL" line."""
    for line in path.read_text().splitlines():
        if line.startswith("#MODEL "):
            return line[7:].strip()
    return "affine"


def write_points(
    path: Path, gcps: list[GCP], outline: Outline | None = None, model: str = "affine"
) -> None:
    lines = ["#CRS: EPSG:4326"]
    if model != "affine":
        lines.append(f"#MODEL {model}")
    if outline:
        lines.append("#OUTLINE " + " ".join(f"{x:g},{y:g}" for x, y in outline))
    lines += [f"#NAME {i} {g.name}" for i, g in enumerate(gcps) if g.name]
    lines.append(HEADER)
    lines += [
        f"{g.lon:.7f},{g.lat:.7f},{g.px:.1f},{-g.py:.1f},{int(g.enabled)},0,0,0" for g in gcps
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


MIN_POINTS = {"affine": 3, "similarity": 2}


def _similarity(pts: list[GCP], east: list[float], north: list[float]) -> tuple[list, list]:
    """Least-squares shift + scale + rotation. Pixel rows run down while north runs up, so
    the map is mirrored: east = a*px + b*py + c, north = b*px - a*py + d."""
    n = len(pts)
    mx, my = sum(g.px for g in pts) / n, sum(g.py for g in pts) / n
    me, mn = sum(east) / n, sum(north) / n
    xs = [(g.px - mx, g.py - my) for g in pts]
    es, ns = [v - me for v in east], [v - mn for v in north]
    s = sum(x * x + y * y for x, y in xs)
    a = sum(x * e - y * nn for (x, y), e, nn in zip(xs, es, ns)) / s
    b = sum(y * e + x * nn for (x, y), e, nn in zip(xs, es, ns)) / s
    return [a, b, me - a * mx - b * my], [b, -a, mn - b * mx + a * my]


def _solve3(a: list[list[float]], b: list[float]) -> list[float]:
    """Solve a 3x3 linear system by Gaussian elimination with partial pivoting."""
    m = [row[:] + [v] for row, v in zip(a, b)]
    for c in range(3):
        p = max(range(c, 3), key=lambda r: abs(m[r][c]))
        m[c], m[p] = m[p], m[c]
        if abs(m[c][c]) < 1e-12:
            raise ValueError("GCPs are collinear; add points off that line")
        for r in range(3):
            if r != c:
                k = m[r][c] / m[c][c]
                m[r] = [x - k * y for x, y in zip(m[r], m[c])]
    return [m[i][3] / m[i][i] for i in range(3)]


class Affine:
    def __init__(self, gcps: list[GCP], model: str = "affine"):
        pts = [g for g in gcps if g.enabled]
        if len(pts) < MIN_POINTS[model]:
            raise ValueError(f"need at least {MIN_POINTS[model]} enabled GCPs for {model}")
        self.model = model
        self.lat0 = sum(g.lat for g in pts) / len(pts)
        self.lon0 = sum(g.lon for g in pts) / len(pts)
        self.kx = M_PER_DEG * math.cos(math.radians(self.lat0))
        east = [(g.lon - self.lon0) * self.kx for g in pts]
        north = [(g.lat - self.lat0) * M_PER_DEG for g in pts]
        if model == "similarity":
            self.e, self.n = _similarity(pts, east, north)
        else:
            xs = [(g.px, g.py, 1.0) for g in pts]
            ata = [[sum(x[i] * x[j] for x in xs) for j in range(3)] for i in range(3)]
            self.e = _solve3(ata, [sum(x[i] * v for x, v in zip(xs, east)) for i in range(3)])
            self.n = _solve3(ata, [sum(x[i] * v for x, v in zip(xs, north)) for i in range(3)])
        self.gcps = pts

    def to_meters(self, px: float, py: float) -> tuple[float, float]:
        e, n = self.e, self.n
        return e[0] * px + e[1] * py + e[2], n[0] * px + n[1] * py + n[2]

    def to_latlon(self, px: float, py: float) -> tuple[float, float]:
        east, north = self.to_meters(px, py)
        return self.lat0 + north / M_PER_DEG, self.lon0 + east / self.kx

    def meters_per_pixel(self) -> float:
        return math.sqrt(abs(self.e[0] * self.n[1] - self.e[1] * self.n[0]))

    def error_m(self, g: GCP) -> float:
        lat, lon = self.to_latlon(g.px, g.py)
        return distance_m((lat, lon), (g.lat, g.lon))


def distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    kx = M_PER_DEG * math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot((a[0] - b[0]) * M_PER_DEG, (a[1] - b[1]) * kx)


def leave_one_out(gcps: list[GCP], model: str = "affine") -> list[float]:
    """For each enabled GCP: error (m) when the transform is fit without it."""
    pts = [g for g in gcps if g.enabled]
    out = []
    for i, g in enumerate(pts):
        rest = pts[:i] + pts[i + 1 :]
        ok = len(rest) >= MIN_POINTS[model]
        out.append(Affine(rest, model).error_m(g) if ok else float("nan"))
    return out
