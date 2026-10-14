"""Sheet pixels <-> latitude/longitude from ground control points (GCPs).

A GCP pairs a pixel on the 50% sheet image (data/sheets/...) with the same spot today,
usually a street intersection. GCPs live in config/georef/<area>/<edition>/<sheet>.points
in QGIS's georeferencer format, so they can be made or fixed by hand in QGIS too.

The fit is affine (shift, scale, rotation, shear) in a local flat projection around the
sheet; one Sanborn sheet covers well under 2 km, so the flat-earth error is negligible.
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


def write_points(path: Path, gcps: list[GCP]) -> None:
    lines = ["#CRS: EPSG:4326"]
    lines += [f"#NAME {i} {g.name}" for i, g in enumerate(gcps) if g.name]
    lines.append(HEADER)
    lines += [
        f"{g.lon:.7f},{g.lat:.7f},{g.px:.1f},{-g.py:.1f},{int(g.enabled)},0,0,0" for g in gcps
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


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
    def __init__(self, gcps: list[GCP]):
        pts = [g for g in gcps if g.enabled]
        if len(pts) < 3:
            raise ValueError("need at least 3 enabled GCPs")
        self.lat0 = sum(g.lat for g in pts) / len(pts)
        self.lon0 = sum(g.lon for g in pts) / len(pts)
        self.kx = M_PER_DEG * math.cos(math.radians(self.lat0))
        xs = [(g.px, g.py, 1.0) for g in pts]
        ata = [[sum(x[i] * x[j] for x in xs) for j in range(3)] for i in range(3)]
        east = [(g.lon - self.lon0) * self.kx for g in pts]
        north = [(g.lat - self.lat0) * M_PER_DEG for g in pts]
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


def leave_one_out(gcps: list[GCP]) -> list[float]:
    """For each enabled GCP: error (m) when the transform is fit without it."""
    pts = [g for g in gcps if g.enabled]
    out = []
    for i, g in enumerate(pts):
        rest = pts[:i] + pts[i + 1 :]
        out.append(Affine(rest).error_m(g) if len(rest) >= 3 else float("nan"))
    return out
