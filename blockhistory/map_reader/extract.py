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

# Main map reader (Day 7: Haiku found 9 of 10 hand labels and 3 of 3 gas-tank sites; the
# free vision model found 3 and 0). Haiku by default; Sonnet only for tiles Haiku is
# unsure about. Override in .env (BLOCKHISTORY_MODEL / BLOCKHISTORY_EFFORT).
DEFAULT_MODEL = "claude-haiku-5-5"
DEFAULT_EFFORT = "low"  # medium scored worse at ~2x cost on the Day 7 tiles
# Models that accept server-side refusal fallbacks (Haiku 5.5 has none).
FALLBACK_MODELS = {"claude-sonnet-5-5"}
# Bump whenever SYSTEM_PROMPT or the schema changes so the cache doesn't serve stale output.
PROMPT_VERSION = "v1"
CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache" / "map_reader"

SYSTEM_PROMPT = """\
You read crops of Sanborn fire insurance maps (US, 1880s-1950s) and transcribe what is \
printed on them. Your output feeds a tool that tells residents about past land uses that \
sometimes left soil contamination, so record only what is actually on the map and say \
when you are unsure.

How to read the map:
- Building color = construction: pink/red brick, yellow frame (wood), blue concrete block \
("C.B.") or concrete, gray iron or metal-clad, olive/brown fireproof. Brick with a yellow \
edge is brick veneer.
- Letters inside a footprint give the use: D dwelling, S store, F flat, A auto house \
(private garage). Longer labels name the business: "FILL'G STA.", "BULK OIL STA.", \
"OIL HO.", "DRY CLEANING", "AUTO REP'G", "TIN SHOP", "FOUNDRY", or a company name with a \
line like "MFG. STEEL CASTINGS".
- Small numbers in a footprint corner are stories (e.g. "2", "1B" = 1 story + basement).
- Common abbreviations: FR. = frame, BR. = brick, IR. = iron, CONC. = concrete, \
FOUND. = foundation, STGE = storage, W. HO. = warehouse, HO. = house, MFG. = \
manufacturing, GASOL. = gasoline, FILL'G STA. = filling station. "FR. FOUND." means a \
frame building on a foundation, not a foundry; "BR. CORE OVEN" is a brick core oven.
- Gasoline tanks: a small circle marked "G.T." (or "G.T.S" with 2-3 circles) is drawn at \
the curb or yard beside the building it serves, usually a filling station, garage or oil \
station. Count the circles and give the count to that one building only, never to its \
neighbors. Above-ground tanks are labeled in words ("IR. TANKS 8' ABV. GRD.").
- Addresses: house numbers are printed along the street edge of each lot, and belong to \
the street that edge faces. Follow the street line to find that street's name; it may be \
printed far from the building, and a nearby side street is usually not the right one. \
Numbers nearest the building are current; numbers in parentheses or further out are old.
- Not addresses: large bold numbers in the middle of a block (e.g. "3009") are city block \
numbers; circled numbers are ground elevations; big numbers at the sheet edge refer to \
other sheets.
- Thin pasted-over patches are later revisions; read the top layer.

Rules:
- List buildings and sites that have a specific use label (a business, factory, \
institution, yard, or tank). Do not list footprints marked only D, S, F, or A; do list \
any footprint with a G.T. symbol, whatever its label.
- A plant drawn as many labeled parts (boiler room, foundry, pattern shop) can be one \
entry per labeled part.
- Construction notes ("CONC. FL.", "STEEL RF.", "WOOD POSTS") describe a building; they \
are not buildings. Put them in that building's entry, not a new one.
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
    gasoline_tank_count: int = Field(
        description="Number of G.T. circles drawn for this building (0 if none)"
    )
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


# What batch.py needs from a reader: SCHEMA, SYSTEM_PROMPT, PROMPT_VERSION, MAX_TOKENS,
# EST_TOKENS, resolve(), cache_path(), messages_for() and save_result().
SCHEMA = TileExtraction
USER_TEXT = "Transcribe every labeled building in this tile."
MAX_TOKENS = 16000
# Measured on the Day 7 tiles with prompt v1 at low effort: ~3,900 input and ~1,700 output
# tokens per tile. Used only to refuse a batch that could break the budget.
EST_TOKENS = (3_900, 2_500)


def _cache_key(image_bytes: bytes, model: str, effort: str) -> str:
    h = hashlib.sha256()
    h.update(f"{model}|{effort}|{PROMPT_VERSION}|".encode())
    h.update(image_bytes)
    return h.hexdigest()[:32]


def resolve(model: str | None = None, effort: str | None = None) -> tuple[str, str]:
    """Model and effort from arguments, then .env, then defaults (read at call time)."""
    model = model or os.environ.get("BLOCKHISTORY_MODEL") or DEFAULT_MODEL
    effort = effort or os.environ.get("BLOCKHISTORY_EFFORT") or DEFAULT_EFFORT
    return model, effort


def cache_path(tile_path: Path, model: str, effort: str) -> Path:
    return CACHE_DIR / f"{_cache_key(tile_path.read_bytes(), model, effort)}.json"


def load_cached(
    tile_path: Path, model: str | None = None, effort: str | None = None
) -> dict | None:
    path = cache_path(tile_path, *resolve(model, effort))
    return {**json.loads(path.read_text()), "cached": True} if path.exists() else None


def messages_for(image_bytes: bytes) -> list[dict]:
    return [
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
                {"type": "text", "text": USER_TEXT},
            ],
        }
    ]


def save_result(
    tile_path: Path,
    model: str,
    effort: str,
    served_model: str,
    input_tokens: int,
    output_tokens: int,
    extraction: TileExtraction,
    batch: bool = False,
) -> dict:
    """Record the spend and cache one tile's result. Shared by single and batch reads."""
    usd = costs.record(model, input_tokens, output_tokens, what=tile_path.name, batch=batch)
    result = {
        "tile": tile_path.name,
        "model": served_model,
        "effort": effort,
        "prompt_version": PROMPT_VERSION,
        "batch": batch,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        "usd": round(usd, 6),
        "extraction": extraction.model_dump(mode="json"),
    }
    path = cache_path(tile_path, model, effort)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")
    return result


def read_tile(
    tile_path: Path,
    client: anthropic.Anthropic | None = None,
    model: str | None = None,
    effort: str | None = None,
) -> dict:
    """Extract buildings from one tile. Returns {extraction, usage, usd, model, cached}."""
    model, effort = resolve(model, effort)
    cached = load_cached(tile_path, model, effort)
    if cached:
        return cached

    costs.check_budget()
    client = client or anthropic.Anthropic()
    extra = {}
    if model in FALLBACK_MODELS:
        # On a safety-classifier false positive, let the API re-run on a fallback model.
        extra = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
    response = client.beta.messages.parse(
        model=model,
        max_tokens=MAX_TOKENS,
        output_config={"effort": effort},
        **extra,
        system=SYSTEM_PROMPT,
        messages=messages_for(tile_path.read_bytes()),
        output_format=TileExtraction,
    )
    if response.stop_reason == "refusal":
        costs.record(
            model, response.usage.input_tokens, response.usage.output_tokens, what=tile_path.name
        )
        raise RuntimeError(f"Model declined tile {tile_path.name}: {response.stop_details}")
    if response.parsed_output is None:
        costs.record(
            model, response.usage.input_tokens, response.usage.output_tokens, what=tile_path.name
        )
        raise RuntimeError(f"No parseable output for {tile_path.name} ({response.stop_reason})")

    result = save_result(
        tile_path,
        model,
        effort,
        response.model,
        response.usage.input_tokens,
        response.usage.output_tokens,
        response.parsed_output,
    )
    return {**result, "cached": False}
