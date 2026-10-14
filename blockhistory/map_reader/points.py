"""Point pass: where on its tile each flagged finding's building is, in pixels.

The first pass's position words ("center-right") were off by up to half a tile on sheet
56, 50+ m on the ground. This pass sends a tile back with the list of labels the first
pass found there and asks for the pixel center of each one's building. Only findings
rated high or medium, or with gas tanks, are asked about, so it runs on a minority of tiles.
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, Field

from blockhistory import costs
from blockhistory.map_reader import extract
from blockhistory.map_reader.relevance import relevance

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "cache" / "point_reader"
DEFAULT_EFFORT = "low"
PROMPT_VERSION = "p1"
MAX_TOKENS = 4000
EST_TOKENS = (1_900, 400)

SYSTEM_PROMPT = """\
You locate labeled buildings on a crop of a 1930s Sanborn fire insurance map. The image \
is 1024 pixels square unless stated otherwise; x runs 0 at the left edge to the right, y \
runs 0 at the top edge downward.

You get a numbered list of labels that were read from this crop. For each one, find the \
printed label and give the pixel center of the building or yard it describes (the \
footprint the words sit in or point to, not the words themselves when they are outside \
it). If a label appears more than once, use the street number to pick the right one. If \
you cannot find a label, set found to false and give your best guess.
"""


class Point(BaseModel):
    index: int = Field(description="The label's number in the list")
    x: int = Field(description="Pixel column of the building's center")
    y: int = Field(description="Pixel row of the building's center")
    found: bool = Field(description="The label was found on the image")


class PointReading(BaseModel):
    points: list[Point]


SCHEMA = PointReading


def wanted(building: dict) -> bool:
    return building.get("gasoline_tank_count", 0) > 0 or relevance(
        building["label"], building["use"]
    ) in ("high", "medium")


def labels_for(tile: Path, model: str | None = None) -> list[dict]:
    """The first pass's flagged findings on this tile, in its order."""
    result = extract.load_cached(tile, model)
    if not result:
        return []
    return [b for b in result["extraction"]["buildings"] if wanted(b)]


def _prompt(tile: Path) -> str:
    lines = []
    for i, b in enumerate(labels_for(tile)):
        num = f" (no. {b['street_number']})" if b.get("street_number") else ""
        lines.append(f"{i}. {b['label']}{num}: {b['use']}")
    return "Labels on this crop:\n" + "\n".join(lines)


def resolve(model: str | None = None, effort: str | None = None) -> tuple[str, str]:
    return extract.resolve(model, None)[0], effort or DEFAULT_EFFORT


def cache_path(tile: Path, model: str, effort: str) -> Path:
    h = hashlib.sha256()
    h.update(f"points|{model}|{effort}|{PROMPT_VERSION}|{_prompt(tile)}|".encode())
    h.update(tile.read_bytes())
    return CACHE_DIR / f"{h.hexdigest()[:32]}.json"


def load_cached(tile: Path, model: str | None = None, effort: str | None = None) -> dict | None:
    path = cache_path(tile, *resolve(model, effort))
    return json.loads(path.read_text()) if path.exists() else None


def request_messages(tile: Path) -> list[dict]:
    data = base64.standard_b64encode(tile.read_bytes()).decode()
    return [
        {
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}},
                {"type": "text", "text": _prompt(tile)},
            ],
        }
    ]  # fmt: skip


def save_result(
    tile: Path,
    model: str,
    effort: str,
    served_model: str,
    input_tokens: int,
    output_tokens: int,
    reading: PointReading,
    batch: bool = False,
) -> dict:
    usd = costs.record(model, input_tokens, output_tokens, what=f"points {tile.name}", batch=batch)
    result = {
        "tile": tile.name,
        "model": served_model,
        "effort": effort,
        "prompt_version": PROMPT_VERSION,
        "batch": batch,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        "usd": round(usd, 6),
        "labels": [b["label"] for b in labels_for(tile)],
        "reading": reading.model_dump(mode="json"),
    }
    path = cache_path(tile, model, effort)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")
    return result


def candidate_tiles(tile_dir: Path) -> list[Path]:
    return [t for t in sorted(tile_dir.glob("*.jpg")) if labels_for(t)]


def tile_points(tile: Path, model: str | None = None) -> list[dict]:
    """[{label, street_number, x, y, found}] for the tile, or [] if the pass hasn't run."""
    result = load_cached(tile, model)
    if not result:
        return []
    labels = labels_for(tile, model)
    out = []
    for p in result["reading"]["points"]:
        if 0 <= p["index"] < len(labels):
            b = labels[p["index"]]
            out.append({"label": b["label"], "street_number": b.get("street_number"), **p})
    return out
