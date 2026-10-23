"""Modern street intersections from OpenStreetMap, for ground control points.

One Overpass query fetches every named street in a bounding box (cached on disk), and
intersection() finds where two streets share a vertex. Map names and OSM names differ in
small ways ("KRAUS" is "Krauss Street", "S. BROADWAY" is "South Broadway"), so names are
compared after dropping directions and street types, with a short alias list.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "cache" / "osm"
SERVERS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
USER_AGENT = "BlockHistory/0.0.1 (+https://github.com/Hariswar/BlockHistory)"
# Carondelet and Patch, with a margin.
CARONDELET_BBOX = (38.535, -90.285, 38.600, -90.215)  # south, west, north, east
# Sanborn spelling -> today's (after normalizing).
ALIASES = {"kraus": "krauss"}
DROP = {"n", "s", "e", "w", "north", "south", "east", "west"} | {
    "st", "street", "av", "ave", "avenue", "blvd", "boulevard", "dr", "drive", "ct", "court",
    "pl", "place", "rd", "road",
}  # fmt: skip


def norm_street(name: str) -> str:
    words = [w for w in re.sub(r"[^a-z0-9 ]", " ", name.lower()).split() if w not in DROP]
    key = " ".join(words)
    return ALIASES.get(key, key)


def fetch_streets(bbox: tuple[float, float, float, float] = CARONDELET_BBOX) -> list[dict]:
    """Named OSM highways in the box: [{name, highway, coords: [(lat, lon), ...]}]. Cached."""
    box = ",".join(str(v) for v in bbox)
    query = f"[out:json][timeout:60];way[highway][name]({box});out tags geom;"
    path = CACHE_DIR / f"{hashlib.sha256(query.encode()).hexdigest()[:16]}.json"
    if not path.exists():
        last = None
        for url in SERVERS:  # the main server is often busy; fall back to a mirror
            try:
                resp = requests.post(
                    url, data={"data": query}, headers={"User-Agent": USER_AGENT}, timeout=120
                )
                resp.raise_for_status()
                data = resp.json()
                break
            except (requests.RequestException, ValueError) as e:
                last = e
        else:
            raise RuntimeError(f"Overpass failed on every server: {last}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
    data = json.loads(path.read_text())
    return [
        {
            "name": e["tags"]["name"],
            "highway": e["tags"].get("highway"),
            "coords": [(g["lat"], g["lon"]) for g in e["geometry"]],
        }
        for e in data["elements"]
        if e.get("geometry")
    ]


def meters(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat = math.radians((a[0] + b[0]) / 2)
    dy = (a[0] - b[0]) * 111_320
    dx = (a[1] - b[1]) * 111_320 * math.cos(lat)
    return math.hypot(dx, dy)


def intersection(street_a: str, street_b: str, streets: list[dict] | None = None) -> list[tuple]:
    """Points where the two streets share a vertex, merged within 40 m (divided roads)."""
    streets = streets if streets is not None else fetch_streets()
    ka, kb = norm_street(street_a), norm_street(street_b)
    pa = {c for s in streets if norm_street(s["name"]) == ka for c in s["coords"]}
    pb = {c for s in streets if norm_street(s["name"]) == kb for c in s["coords"]}
    groups: list[list[tuple]] = []
    for p in sorted(pa & pb):
        g = next((g for g in groups if meters(g[0], p) < 40), None)
        if g:
            g.append(p)
        else:
            groups.append([p])
    return [(sum(p[0] for p in g) / len(g), sum(p[1] for p in g) / len(g)) for g in groups]


# Streets a business faces; not paths, alleys, driveways or the interstate.
NOT_FRONTAGE = {
    "footway", "path", "cycleway", "steps", "pedestrian", "track", "bridleway", "proposed",
    "motorway", "motorway_link", "trunk_link", "primary_link", "secondary_link", "construction",
}  # fmt: skip
# Named service roads are often old streets now inside a plant (East Mott Street); keep those.
STREET_NAME = re.compile(r"\b(Street|Avenue|Boulevard|Place|Court|Road|Drive|Lane)$")
STREET_MAX_M = 80  # farther than this from any street: on no street page (big plant interiors)


def street_page_name(name: str) -> str:
    """One page per street: "East Krauss Street" and "Krauss Street" are the same street."""
    return re.sub(r"^(East|West) ", "", name)


def _to_segment_m(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    kx = 111_320 * math.cos(math.radians(p[0]))
    ax, ay = (a[1] - p[1]) * kx, (a[0] - p[0]) * 111_320
    bx, by = (b[1] - p[1]) * kx, (b[0] - p[0]) * 111_320
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / (dx * dx + dy * dy)))
    return math.hypot(ax + t * dx, ay + t * dy)


def nearest_street(
    lat: float, lon: float, printed: str | None = None, streets: list[dict] | None = None
) -> str | None:
    """Today's name of the street a mapped site faces: the nearest frontage street within
    STREET_MAX_M, or the street printed with its house number when that one is in range too
    (corner lots sit about as close to both streets)."""
    streets = streets if streets is not None else fetch_streets()
    best: dict[str, float] = {}
    for s in streets:
        if s["highway"] in NOT_FRONTAGE:
            continue
        if s["highway"] == "service" and not STREET_NAME.search(s["name"]):
            continue
        c = s["coords"]
        d = (
            min(_to_segment_m((lat, lon), c[i], c[i + 1]) for i in range(len(c) - 1))
            if len(c) > 1
            else 1e9
        )
        if d <= STREET_MAX_M and d < best.get(s["name"], 1e9):
            best[s["name"]] = d
    if not best:
        return None
    if printed and norm_street(printed):
        named = [n for n in best if norm_street(n) == norm_street(printed)]
        if named:
            return street_page_name(named[0])
    return street_page_name(min(best, key=best.get))
