"""Today's position of a street address, from the free US Census geocoder (no key).

Used only to check georeferencing: the Census interpolates along address ranges, so it is
itself off by 10-30 m, and Sanborn-era numbers can differ from today's.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "cache" / "geocode"
URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"


def geocode(address: str) -> tuple[float, float] | None:
    """(lat, lon) of the best match, or None. Cached, including misses."""
    path = CACHE_DIR / f"{hashlib.sha256(address.lower().encode()).hexdigest()[:16]}.json"
    if not path.exists():
        resp = requests.get(
            URL,
            params={"address": address, "benchmark": "Public_AR_Current", "format": "json"},
            timeout=60,
        )
        resp.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(resp.text)
    matches = json.loads(path.read_text())["result"]["addressMatches"]
    if not matches:
        return None
    c = matches[0]["coordinates"]
    return c["y"], c["x"]
