"""Library of Congress Sanborn Maps client.

The loc.gov JSON API (append ``fo=json`` to any loc.gov URL) exposes each Sanborn
edition as an *item*; each item has one resource whose ``files`` are the sheets.
Images are served through IIIF, so we can ask for any scale without downloading the
150 MB master TIFFs.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

COLLECTION_URL = "https://www.loc.gov/collections/sanborn-maps/"
ITEM_URL = "https://www.loc.gov/item/{item_id}/"
IIIF_URL = "https://tile.loc.gov/image-services/iiif/{service}/full/{size}/0/default.jpg"
REGION_URL = "https://tile.loc.gov/image-services/iiif/{service}/{region}/full/0/default.jpg"

# loc.gov rate-limits aggressive clients; stay well under it.
REQUEST_DELAY_S = 1.0
USER_AGENT = "BlockHistory/0.0.1 (+https://github.com/Hariswar/BlockHistory)"

_session = requests.Session()
_session.headers["User-Agent"] = USER_AGENT
# tile.loc.gov returns 503/429 (and Cloudflare 52x) under load; back off 5, 10, 20, 40, 80 s before giving up.
_retry = Retry(
    total=5,
    backoff_factor=5,
    status_forcelist=(429, 500, 502, 503, 504, 520, 522, 524),
    respect_retry_after_header=True,
)
_session.mount("https://", HTTPAdapter(max_retries=_retry))


@dataclass
class Edition:
    item_id: str  # e.g. "sanborn04849_009"
    date: str  # e.g. "1948-06"
    title: str
    url: str
    sheet_count: int | None = None


@dataclass
class Sheet:
    sheet_id: str  # e.g. "04849_1948-0001a" (a/b suffixes are paste-over revisions)
    item_id: str
    edition_date: str
    sheet_number: int | None  # None for title and index pages ("-titl", "-ind1")
    service: str  # IIIF service id, used to build image URLs at any scale
    jp2_url: str
    width: int | None
    height: int | None
    item_url: str

    def image_url(self, pct: int = 50) -> str:
        size = "full" if pct >= 100 else f"pct:{pct}"
        return IIIF_URL.format(service=self.service, size=size)


def _get_json(url: str, params: dict | None = None) -> dict:
    params = {**(params or {}), "fo": "json"}
    resp = _session.get(url, params=params, timeout=60)
    resp.raise_for_status()
    time.sleep(REQUEST_DELAY_S)
    return resp.json()


def search_editions(city: str, state: str) -> list[Edition]:
    """All Sanborn editions for a city, oldest first."""
    data = _get_json(COLLECTION_URL, {"q": city, "c": 100, "at": "results"})
    editions = []
    for r in data["results"]:
        cities = [c.lower() for c in r.get("location_city", [])]
        states = [s.lower() for s in r.get("location_state", [])]
        if city.lower() not in cities or state.lower() not in states:
            continue
        item_id = r["id"].rstrip("/").rsplit("/", 1)[-1]
        editions.append(Edition(item_id=item_id, date=r["date"], title=r["title"], url=r["id"]))
    return sorted(editions, key=lambda e: e.date)


def list_sheets(item_id: str) -> list[Sheet]:
    """Every sheet image in one edition."""
    data = _get_json(ITEM_URL.format(item_id=item_id))
    date = data["item"]["date"]
    sheets = []
    for files in data["resources"][0]["files"]:
        jp2 = next(f for f in files if f["mimetype"] == "image/jp2")
        jpeg = next(f for f in files if f["mimetype"] == "image/jpeg")
        # ".../iiif/service:gmd:...:04849_1948-0001a/full/pct:12.5/0/default.jpg"
        service = jpeg["url"].split("/iiif/", 1)[1].split("/full/", 1)[0]
        sheet_id = service.rsplit(":", 1)[-1]
        # Rolla: "04849_1948-0001a"; St. Louis volumes: "04858_12_1916-0042", "..._1916-ind1".
        match = re.search(r"-(\d+)[a-z]?$", sheet_id)
        number = int(match.group(1)) if match else None
        sheets.append(
            Sheet(
                sheet_id=sheet_id,
                item_id=item_id,
                edition_date=date,
                sheet_number=number,
                service=service,
                jp2_url=jp2["url"],
                width=jp2.get("width"),
                height=jp2.get("height"),
                item_url=ITEM_URL.format(item_id=item_id),
            )
        )
    return sheets


def download_sheet(sheet: Sheet, out_dir: Path, pct: int = 50) -> Path:
    """Save a sheet JPEG plus a metadata sidecar. Skips sheets already on disk."""
    out_dir.mkdir(parents=True, exist_ok=True)
    img_path = out_dir / f"{sheet.sheet_id}.jpg"
    meta_path = out_dir / f"{sheet.sheet_id}.json"
    if img_path.exists() and meta_path.exists():
        return img_path

    img_path.write_bytes(_get_image(sheet.image_url(pct), sheet.sheet_id))
    meta = {**asdict(sheet), "downloaded_pct": pct, "image_url": sheet.image_url(pct)}
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return img_path


def download_region(service: str, box: tuple[int, int, int, int], out_path: Path) -> Path:
    """Save one full-resolution region (x, y, w, h in full-res pixels) of a sheet."""
    if not out_path.exists():
        x, y, w, h = box
        url = REGION_URL.format(service=service, region=f"{x},{y},{w},{h}")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(_get_image(url, out_path.name))
    return out_path


def _get_image(url: str, name: str) -> bytes:
    # The adapter retries refused requests; this loop also retries connections that drop
    # partway through the image body, which tile.loc.gov does under load.
    for attempt in range(4):
        try:
            resp = _session.get(url, timeout=300)
            resp.raise_for_status()
            break
        except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError):
            if attempt == 3:
                raise
            time.sleep(10 * 2**attempt)
    # A busy server sometimes answers 200 with an HTML error page instead of the image.
    if not resp.headers.get("content-type", "").startswith("image/"):
        raise RuntimeError(f"{name}: expected an image, got {resp.headers.get('content-type')}")
    time.sleep(REQUEST_DELAY_S)
    return resp.content
