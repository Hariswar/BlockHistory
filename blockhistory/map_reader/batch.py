"""Read many tiles through the Message Batches API (half price; results within 24 h).

submit() sends every tile that isn't already cached and writes a manifest to
data/batches/<batch_id>.json. collect() fetches the results and stores each one in the
same cache as read_tile(), so everything downstream treats batch and single reads alike.
`reader` is the module that defines the prompt and schema: `extract` (the map reader,
the default), `tanks` (the gas-tank second pass) or `points` (pixel locations).
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import ModuleType

import anthropic
from anthropic import transform_schema
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
from pydantic import ValidationError

from blockhistory import costs
from blockhistory.map_reader import extract

BATCH_DIR = Path(__file__).resolve().parents[2] / "data" / "batches"


def estimate_usd(n_tiles: int, model: str, reader: ModuleType = extract) -> float:
    return n_tiles * costs.call_cost(model, *reader.EST_TOKENS, batch=True)


def _request(tile: Path, model: str, effort: str, reader: ModuleType = extract) -> Request:
    # custom_id must be <= 64 chars of [A-Za-z0-9_-]; tile stems are like 04858_12_1938-0050_r3_c2.
    return Request(
        custom_id=tile.stem,
        params=MessageCreateParamsNonStreaming(
            model=model,
            max_tokens=reader.MAX_TOKENS,
            system=reader.SYSTEM_PROMPT,
            # Readers whose prompt depends on the tile (points) build their own messages.
            messages=(
                reader.request_messages(tile)
                if hasattr(reader, "request_messages")
                else reader.messages_for(tile.read_bytes())
            ),
            output_config={
                "effort": effort,
                "format": {
                    "type": "json_schema",
                    "schema": transform_schema(reader.SCHEMA),
                },
            },
        ),
    )


def submit(
    tiles: list[Path],
    model: str | None = None,
    effort: str | None = None,
    client: anthropic.Anthropic | None = None,
    reader: ModuleType = extract,
) -> dict:
    """Send uncached tiles as one batch. Returns the manifest (or a no-op summary)."""
    model, effort = reader.resolve(model, effort)
    todo = [t for t in tiles if not reader.cache_path(t, model, effort).exists()]
    if len({t.stem for t in todo}) != len(todo):
        raise ValueError("tile names must be unique within a batch")
    if not todo:
        return {"batch_id": None, "submitted": 0, "already_cached": len(tiles)}

    est = estimate_usd(len(todo), model, reader)
    costs.check_budget()
    if costs.month_spend() + est > costs.monthly_cap():
        raise costs.BudgetExceeded(
            f"Batch of {len(todo)} tiles is estimated at ${est:.2f}; this month has "
            f"${costs.monthly_cap() - costs.month_spend():.2f} left. Send fewer tiles."
        )
    client = client or anthropic.Anthropic()
    batch = client.messages.batches.create(
        requests=[_request(t, model, effort, reader) for t in todo]
    )
    manifest = {
        "batch_id": batch.id,
        "reader": reader.__name__,
        "model": model,
        "effort": effort,
        "prompt_version": reader.PROMPT_VERSION,
        "estimated_usd": round(est, 4),
        "tiles": {t.stem: str(t) for t in todo},
        "submitted": len(todo),
        "already_cached": len(tiles) - len(todo),
    }
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    (BATCH_DIR / f"{batch.id}.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def status(batch_id: str, client: anthropic.Anthropic | None = None):
    client = client or anthropic.Anthropic()
    return client.messages.batches.retrieve(batch_id)


def collect(batch_id: str, client: anthropic.Anthropic | None = None) -> dict:
    """Store every finished result in the tile cache. Safe to run more than once."""
    client = client or anthropic.Anthropic()
    manifest = json.loads((BATCH_DIR / f"{batch_id}.json").read_text())
    model, effort = manifest["model"], manifest["effort"]
    reader = importlib.import_module(manifest.get("reader", extract.__name__))
    if manifest["prompt_version"] != reader.PROMPT_VERSION:
        raise RuntimeError(
            f"Batch used prompt {manifest['prompt_version']} but the code is on "
            f"{reader.PROMPT_VERSION}; its results would be cached under the wrong version."
        )
    failed = manifest.setdefault("failed", {})
    summary = {"saved": 0, "already_saved": 0, "failed": failed}
    for item in client.messages.batches.results(batch_id):
        tile = Path(manifest["tiles"][item.custom_id])
        if reader.cache_path(tile, model, effort).exists() or item.custom_id in failed:
            summary["already_saved"] += 1
            continue
        res = item.result
        if res.type != "succeeded":
            detail = getattr(getattr(res, "error", None), "type", "") or res.type
            failed[item.custom_id] = f"{res.type}: {detail}"
            continue
        msg = res.message
        usage = (msg.usage.input_tokens, msg.usage.output_tokens)
        text = next((b.text for b in msg.content if b.type == "text"), "")
        try:
            if msg.stop_reason == "refusal":
                raise ValueError(f"refusal: {msg.stop_details}")
            extraction = reader.SCHEMA.model_validate_json(text)
        except (ValidationError, ValueError) as e:
            # Still billed, so still recorded.
            costs.record(model, *usage, what=f"{tile.name} (failed)", batch=True)
            failed[item.custom_id] = f"{msg.stop_reason}: {str(e)[:120]}"
            continue
        reader.save_result(tile, model, effort, msg.model, *usage, extraction, batch=True)
        summary["saved"] += 1
    (BATCH_DIR / f"{batch_id}.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return summary
