"""An area's settings, from config/neighborhoods/<area>.json ("site" block).

A new neighborhood needs only that file (made with scripts/area_config.py, plus the "site"
block: display name, bounding box, map center, map years) and its control points; the
pipeline and the website read everything else from it.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@cache
def load(area: str) -> dict:
    return json.loads((ROOT / "config" / "neighborhoods" / f"{area}.json").read_text())


def site(area: str) -> dict:
    return load(area)["site"]


def years(area: str) -> list[str]:
    return site(area)["years"]


def bbox(area: str) -> tuple[float, float, float, float]:
    """(west, south, east, north), the order ArcGIS services take."""
    b = site(area)["bbox"]
    return (b["west"], b["south"], b["east"], b["north"])
