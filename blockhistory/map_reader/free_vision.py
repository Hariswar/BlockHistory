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

import requests

from blockhistory.map_reader.extract import PROMPT_VERSION, SYSTEM_PROMPT, TileExtraction

# qwen2.5vl:3b fits in 8 GB of RAM; use qwen2.5vl:7b on a Colab/Kaggle GPU.
DEFAULT_MODEL = "qwen2.5vl:3b"
CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache" / "free_vision"


def _host() -> str:
    return os.environ.get("OLLAMA_HOST") or "http://localhost:11434"


def read_tile_free(tile_path: Path, model: str | None = None, timeout: int = 600) -> dict:
    """Extract buildings from one tile with a local/Colab model. Same shape as read_tile()."""
    model = model or os.environ.get("BLOCKHISTORY_FREE_MODEL") or DEFAULT_MODEL
    image_bytes = tile_path.read_bytes()
    key = hashlib.sha256(f"{model}|{PROMPT_VERSION}|".encode() + image_bytes).hexdigest()[:32]
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
            "options": {"temperature": 0},
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
    extraction = TileExtraction.model_validate_json(body["message"]["content"])
    result = {
        "tile": tile_path.name,
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "usage": {
            "input_tokens": body.get("prompt_eval_count", 0),
            "output_tokens": body.get("eval_count", 0),
        },
        "seconds": round(body.get("total_duration", 0) / 1e9, 1),
        "usd": 0.0,
        "extraction": extraction.model_dump(mode="json"),
    }
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(result, indent=2) + "\n")
    return {**result, "cached": False}
