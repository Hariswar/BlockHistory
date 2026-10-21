"""State environmental records from the Missouri DNR E-START map service (free, public).

Two layers matter for past land use:
- Underground Storage Tank Facilities (layer 3): registered petroleum tank sites, with the
  status of any leak and its cleanup.
- Hazardous Waste Program Cleanup Sites (layer 0): brownfield, Superfund and other cleanups.

Each record is placed at its address on its City of St. Louis parcel when the city geocoder
matches it (DNR's own points were a median 12 m from the parcel but sometimes 60-300 m off),
otherwise at DNR's point. Raw downloads are cached in data/cache/records/.

Tanks only had to be registered from 1986, so a 1938 filling station that closed earlier
usually has no record: "no record" is not evidence of anything.
"""

from __future__ import annotations

import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "cache" / "records"
SERVICE = "https://gis.dnr.mo.gov/host/rest/services/e_start/e_start/MapServer"
CITY_GEOCODER = (
    "https://maps6.stlouis-mo.gov/arcgis/rest/services/GEOCODERS/COMPOSITE_GEOCODE/"
    "GeocodeServer/findAddressCandidates"
)
LAYERS = {"tank": 3, "cleanup": 0}
PAGE = 1000

# DNR status -> (plain words for the site, whether a release/contamination is on record)
TANK_STATUS = {
    "Investigation/Corrective Action is Ongoing or Incomplete": (
        "a petroleum leak is under investigation or cleanup",
        True,
    ),
    "No Further Action Letter Issued with Restriction": (
        "a petroleum leak was cleaned up; limits on how the land is used remain",
        True,
    ),
    "No Further Action Letter Issued without Restriction": (
        "a petroleum leak was cleaned up with no remaining restrictions",
        True,
    ),
    "Facility Closed Prior to Implementation of 2004 Tanks RBCA": (
        "registered tanks were closed before 2004",
        False,
    ),
    "Administrative Closure": ("the state's tank file was closed administratively", False),
    "Operating UST Facilities with No Known Release": (
        "operating tanks with no known leak",
        False,
    ),
    "Other Reported Petroleum Facilities with No Known Release": (
        "a reported petroleum site with no known leak",
        False,
    ),
}
CLEANUP_STATUS = {
    "Active": "an environmental cleanup is active",
    "Long-Term Stewardship": "a cleanup was done; long-term controls remain on the land",
    "Completed": "an environmental cleanup was completed",
    "Brownfield Assessment": "the site was assessed as a brownfield",
    "Inactive VCP (Terminated/Withdrew)": "a voluntary cleanup was started and withdrawn",
    "Environmental Notice": "an environmental notice is recorded on the land",
}


def fetch(layer: int, bbox: tuple[float, float, float, float]) -> list[dict]:
    """GeoJSON features of a layer inside (west, south, east, north). Cached by layer+box."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"dnr_{layer}_{'_'.join(f'{v:.3f}' for v in bbox)}.geojson"
    if path.exists():
        return json.loads(path.read_text())["features"]
    feats, offset = [], 0
    while True:
        resp = requests.get(
            f"{SERVICE}/{layer}/query",
            params={
                "geometry": ",".join(str(v) for v in bbox),
                "geometryType": "esriGeometryEnvelope",
                "inSR": 4326,
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "*",
                "outSR": 4326,
                "f": "geojson",
                "resultOffset": offset,
                "resultRecordCount": PAGE,
            },
            timeout=120,
        )
        resp.raise_for_status()
        page = resp.json().get("features", [])
        feats += page
        if len(page) < PAGE:
            break
        offset += PAGE
    path.write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
    return feats


def _parcel_point(address: str, cache: dict) -> tuple[float, float] | None:
    """Lat/lon of the address on its city parcel (parcel matches only), cached."""
    key = address.upper().strip()
    if key not in cache:
        cache[key] = None
        if key[:1].isdigit():
            data = requests.get(
                CITY_GEOCODER,
                params={"Street": key, "outSR": 4326, "outFields": "Loc_name", "f": "json"},
                timeout=30,
            ).json()
            for c in data.get("candidates", []):
                if c["score"] >= 90 and c["attributes"].get("Loc_name") == "PARCEL_GEOCODE":
                    cache[key] = (c["location"]["y"], c["location"]["x"])
                    break
    return cache[key]


def records(bbox: tuple[float, float, float, float]) -> list[dict]:
    """Tank and cleanup records in the box, normalized and placed."""
    geo_path = CACHE / "parcel_points.json"
    geo = json.loads(geo_path.read_text()) if geo_path.exists() else {}
    geo = {k: tuple(v) if v else None for k, v in geo.items()}
    out = []
    for kind, layer in LAYERS.items():
        for f in fetch(layer, bbox):
            p = f["properties"]
            if not f.get("geometry"):
                continue
            if kind == "tank":
                status = (p.get("FACSTAT") or "").strip()
                plain, release = TANK_STATUS.get(status, (status.lower(), False))
                name, detail = p.get("FACNAME"), p.get("SUMMARY")
            else:
                status = (p.get("SITESTAT") or "").strip()
                plain, release = CLEANUP_STATUS.get(status, status.lower()), True
                name, detail = p.get("SITENAME"), p.get("CLEANUPSUM") or p.get("SITEHIST")
            address = " ".join((p.get("ADDRESS") or "").split())
            lon, lat = f["geometry"]["coordinates"][:2]
            parcel = _parcel_point(address, geo) if address else None
            out.append(
                {
                    "source": "Missouri DNR",
                    "kind": kind,
                    "name": " ".join((name or "").split()).strip(),
                    "address": address,
                    "status": status,
                    "status_plain": plain,
                    "release": release,
                    "contaminants": (p.get("CONTAMINS") or "").strip() or None,
                    "detail": (detail or "").strip()[:1200] or None,
                    "url": (p.get("URL") or "").strip() or None,
                    "lat": parcel[0] if parcel else lat,
                    "lon": parcel[1] if parcel else lon,
                    "located_by": "parcel" if parcel else "state point",
                }
            )
    geo_path.write_text(json.dumps(geo))
    return out
