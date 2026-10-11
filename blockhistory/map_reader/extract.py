"""Map-reading agent v0: send one tile to a vision model, get buildings back as JSON.

Every result is cached on disk keyed by (model, prompt version, tile bytes), so
re-running never pays twice for the same tile.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from enum import Enum
from pathlib import Path

import anthropic
from pydantic import BaseModel, Field

from blockhistory import costs

# This paid reader only sees tiles the free first pass (Tesseract + an open-source vision
# model) couldn't read. Haiku by default; Sonnet only for tiles Haiku is unsure about.
# Override in .env (BLOCKHISTORY_MODEL / BLOCKHISTORY_EFFORT); see docs/budget.md.
DEFAULT_MODEL = "claude-haiku-5-5"
DEFAULT_EFFORT = "medium"
# Models that accept server-side refusal fallbacks (Haiku 5.5 has none).
FALLBACK_MODELS = {"claude-sonnet-5-5"}
# Bump whenever SYSTEM_PROMPT or the schema changes so the cache doesn't serve stale output.
PROMPT_VERSION = "v0"
CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache" / "map_reader"

SYSTEM_PROMPT = """\
You read crops of Sanborn fire insurance maps (US, 1880s-1950s) and transcribe what is \
printed on them. Your output feeds a tool that warns residents about historical land uses \
that sometimes left soil contamination, so record only what is actually on the map and \
say when you are unsure.

How to read the map:
- Building color = construction: pink/red brick, yellow frame (wood), blue stone or \
concrete block ("C.B."), gray iron or metal-clad, brown fireproof. Brick with a yellow \
stripe is brick veneer.
- Letters inside a footprint give the use: D dwelling, S store, F flat, A auto house \
(private garage). Longer labels name the business ("DRUGS", "REST.", "FILL'G STA.", \
"DRY CLEANING", "AUTO REPAIRING", "TIN SHOP", "BULK OIL DEPOT").
- Small numbers in a footprint corner are stories (e.g. "2", "1B" = 1 story + basement).
- Street numbers run along the street edge of each lot; current numbers are printed \
outside, and older numbers sometimes appear in parentheses.
- A small circle labeled "G.T." is a gasoline tank (often underground). Oil tanks, \
pumps ("P"), and "GAS" also matter.
- Thin pasted-over patches are later revisions; read the top layer.

Rules:
- One entry per labeled building footprint. Skip unlabeled outbuildings unless they \
carry a use label or G.T./tank symbol.
- Copy label text verbatim, including abbreviations; put your expansion in `use`.
- Never invent an address. If no street number is legible for a building, leave it null.
- A building cut off by the tile edge is still listed; set `partial` true.
"""


class Construction(str, Enum):
    brick = "brick"
    brick_veneer = "brick_veneer"
    frame = "frame"
    stone = "stone"
    concrete_block = "concrete_block"
    metal = "metal"
    fireproof = "fireproof"
    unknown = "unknown"


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Building(BaseModel):
    label: str = Field(description="Use label exactly as printed, e.g. 'D', 'S', 'DRY CLEANING'")
    use: str = Field(description="Plain-English use, e.g. 'dwelling', 'store', 'dry cleaner'")
    street_number: str | None = Field(description="Street number as printed, or null")
    street_name: str | None = Field(description="Street the number fronts on, or null")
    construction: Construction
    stories: str | None = Field(description="Story marking as printed, e.g. '2', '1B', or null")
    has_gasoline_tank: bool = Field(description="A G.T. / gasoline or oil tank symbol is attached")
    partial: bool = Field(description="Footprint is cut off by the tile edge")
    confidence: Confidence
    position: str = Field(description="Rough location in the tile, e.g. 'top-left'")


class TileExtraction(BaseModel):
    streets: list[str] = Field(description="Street names visible in the tile")
    buildings: list[Building]
    other_features: list[str] = Field(
        description="Tanks, railroad spurs, yards, and other non-building items worth noting"
    )
    illegible_notes: list[str] = Field(description="Text you could see but not read confidently")


def _cache_key(image_bytes: bytes, model: str, effort: str) -> str:
    h = hashlib.sha256()
    h.update(f"{model}|{effort}|{PROMPT_VERSION}|".encode())
    h.update(image_bytes)
    return h.hexdigest()[:32]


def read_tile(
    tile_path: Path,
    client: anthropic.Anthropic | None = None,
    model: str | None = None,
    effort: str | None = None,
) -> dict:
    """Extract buildings from one tile. Returns {extraction, usage, usd, model, cached}."""
    # Read at call time so values from .env (loaded by the calling script) apply.
    model = model or os.environ.get("BLOCKHISTORY_MODEL") or DEFAULT_MODEL
    effort = effort or os.environ.get("BLOCKHISTORY_EFFORT") or DEFAULT_EFFORT
    image_bytes = tile_path.read_bytes()
    cache_path = CACHE_DIR / f"{_cache_key(image_bytes, model, effort)}.json"
    if cache_path.exists():
        return {**json.loads(cache_path.read_text()), "cached": True}

    costs.check_budget()
    client = client or anthropic.Anthropic()
    extra = {}
    if model in FALLBACK_MODELS:
        # On a safety-classifier false positive, let the API re-run on a fallback model.
        extra = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
    response = client.beta.messages.parse(
        model=model,
        max_tokens=16000,
        output_config={"effort": effort},
        **extra,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": base64.standard_b64encode(image_bytes).decode(),
                        },
                    },
                    {"type": "text", "text": "Transcribe every labeled building in this tile."},
                ],
            }
        ],
        output_format=TileExtraction,
    )
    usd = costs.record(
        model, response.usage.input_tokens, response.usage.output_tokens, what=tile_path.name
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Model declined tile {tile_path.name}: {response.stop_details}")
    if response.parsed_output is None:
        raise RuntimeError(f"No parseable output for {tile_path.name} ({response.stop_reason})")

    result = {
        "tile": tile_path.name,
        "model": response.model,
        "effort": effort,
        "prompt_version": PROMPT_VERSION,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
        "usd": round(usd, 6),
        "extraction": response.parsed_output.model_dump(mode="json"),
    }
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(result, indent=2) + "\n")
    return {**result, "cached": False}
