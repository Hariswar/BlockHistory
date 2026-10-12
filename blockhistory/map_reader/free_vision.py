"""Free first pass, part 2: an open-source vision model served by Ollama.

Same prompt and JSON schema as the paid reader (extract.py), so outputs can be scored the
same way and only uncertain tiles get sent on to Haiku. Ollama can run on this laptop
(small models) or on a free Colab/Kaggle GPU (see docs/free-models.md); point OLLAMA_HOST
at whichever one is running. Costs nothing; results are cached like the paid reader's.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path

import pydantic_core
import requests
from pydantic import ValidationError

from blockhistory.map_reader.extract import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    Building,
    TileExtraction,
)

# qwen2.5vl:3b fits in 8 GB of RAM; use qwen2.5vl:7b on a Colab/Kaggle GPU.
DEFAULT_MODEL = "qwen2.5vl:3b"
CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache" / "free_vision"
# Bump when the Ollama options below change, so old cached results aren't reused.
READER_VERSION = "v1"
# Ollama's default context (2-4K tokens) is too small for a 1024px image plus the prompt
# plus a long JSON answer: on the first Colab run every reply was cut off mid-object at
# ~300 lines. 16K fits on a free T4 with the 7B model. The output cap stops runaway lists.
OLLAMA_OPTIONS = {"temperature": 0, "num_ctx": 16384, "num_predict": 4096}


def _salvage(content: str) -> tuple[TileExtraction, int]:
    """Parse a possibly cut-off JSON reply: keep complete buildings, drop exact repeats.

    Returns the extraction and how many duplicate buildings were removed. Small vision
    models sometimes list the same building over and over until they hit the token limit.
    """
    try:
        raw = pydantic_core.from_json(content, allow_partial=True)
    except ValueError:  # not JSON at all
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    buildings, seen, dupes = [], set(), 0
    for item in raw.get("buildings") or []:
        try:
            b = Building.model_validate(item)
        except ValidationError:
            continue  # the last, half-written entry
        key = b.model_dump_json()
        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        buildings.append(b)

    def strings(field: str) -> list[str]:
        return [x for x in raw.get(field) or [] if isinstance(x, str)]

    extraction = TileExtraction(
        streets=strings("streets"),
        buildings=buildings,
        other_features=strings("other_features"),
        illegible_notes=strings("illegible_notes"),
    )
    return extraction, dupes


def _host() -> str:
    return os.environ.get("OLLAMA_HOST") or "http://localhost:11434"


def read_tile_free(tile_path: Path, model: str | None = None, timeout: int = 600) -> dict:
    """Extract buildings from one tile with a local/Colab model. Same shape as read_tile()."""
    model = model or os.environ.get("BLOCKHISTORY_FREE_MODEL") or DEFAULT_MODEL
    image_bytes = tile_path.read_bytes()
    tag = f"{model}|{PROMPT_VERSION}|{READER_VERSION}|"
    key = hashlib.sha256(tag.encode() + image_bytes).hexdigest()[:32]
    cache_path = CACHE_DIR / f"{key}.json"
    if cache_path.exists():
        return {**json.loads(cache_path.read_text()), "cached": True}

    resp = requests.post(
        f"{_host()}/api/chat",
        json={
            "model": model,
            "stream": False,
            # Ollama constrains output to this JSON schema.
            "format": TileExtraction.model_json_schema(),
            "options": OLLAMA_OPTIONS,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": "Transcribe every labeled building in this tile.",
                    "images": [base64.standard_b64encode(image_bytes).decode()],
                },
            ],
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    body = resp.json()
    content = body["message"]["content"]
    try:
        TileExtraction.model_validate_json(content)
        truncated = False
    except ValidationError:
        truncated = True
    extraction, dupes = _salvage(content)
    result = {
        "tile": tile_path.name,
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "usage": {
            "input_tokens": body.get("prompt_eval_count", 0),
            "output_tokens": body.get("eval_count", 0),
        },
        "seconds": round(body.get("total_duration", 0) / 1e9, 1),
        # True when the reply wasn't valid JSON (usually cut off at num_predict) and only
        # the complete entries were kept. Count these as a reader failure in evals.
        "truncated": truncated,
        "done_reason": body.get("done_reason"),
        "duplicates_removed": dupes,
        "usd": 0.0,
        "extraction": extraction.model_dump(mode="json"),
    }
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(result, indent=2) + "\n")
    return {**result, "cached": False}
