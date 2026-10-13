"""Read many tiles through the Message Batches API (half price; results within 24 h).

submit() sends every tile that isn't already cached and writes a manifest to
data/batches/<batch_id>.json. collect() fetches the results and stores each one in the
same cache as read_tile(), so everything downstream treats batch and single reads alike.
"""

from __future__ import annotations

import json
from pathlib import Path

import anthropic
from anthropic import transform_schema
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
from pydantic import ValidationError

from blockhistory import costs
from blockhistory.map_reader import extract

BATCH_DIR = Path(__file__).resolve().parents[2] / "data" / "batches"
# Measured on the Day 7 tiles with prompt v1 at low effort: ~3,900 input and ~1,700 output
# tokens per tile. Used only to refuse a batch that could break the budget.
EST_TOKENS_PER_TILE = (3_900, 2_500)


def estimate_usd(n_tiles: int, model: str) -> float:
    return n_tiles * costs.call_cost(model, *EST_TOKENS_PER_TILE, batch=True)


def _request(tile: Path, model: str, effort: str) -> Request:
    # custom_id must be <= 64 chars of [A-Za-z0-9_-]; tile stems are like 04858_12_1938-0050_r3_c2.
    return Request(
        custom_id=tile.stem,
        params=MessageCreateParamsNonStreaming(
            model=model,
            max_tokens=extract.MAX_TOKENS,
            system=extract.SYSTEM_PROMPT,
            messages=extract.messages_for(tile.read_bytes()),
            output_config={
                "effort": effort,
                "format": {
                    "type": "json_schema",
                    "schema": transform_schema(extract.TileExtraction),
                },
            },
        ),
    )


def submit(
    tiles: list[Path],
    model: str | None = None,
    effort: str | None = None,
    client: anthropic.Anthropic | None = None,
) -> dict:
    """Send uncached tiles as one batch. Returns the manifest (or a no-op summary)."""
    model, effort = extract.resolve(model, effort)
    todo = [t for t in tiles if not extract.cache_path(t, model, effort).exists()]
    if len({t.stem for t in todo}) != len(todo):
        raise ValueError("tile names must be unique within a batch")
    if not todo:
        return {"batch_id": None, "submitted": 0, "already_cached": len(tiles)}

    est = estimate_usd(len(todo), model)
    costs.check_budget()
    if costs.month_spend() + est > costs.monthly_cap():
        raise costs.BudgetExceeded(
            f"Batch of {len(todo)} tiles is estimated at ${est:.2f}; this month has "
            f"${costs.monthly_cap() - costs.month_spend():.2f} left. Send fewer tiles."
        )
    client = client or anthropic.Anthropic()
    batch = client.messages.batches.create(requests=[_request(t, model, effort) for t in todo])
    manifest = {
        "batch_id": batch.id,
        "model": model,
        "effort": effort,
        "prompt_version": extract.PROMPT_VERSION,
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
    if manifest["prompt_version"] != extract.PROMPT_VERSION:
        raise RuntimeError(
            f"Batch used prompt {manifest['prompt_version']} but the code is on "
            f"{extract.PROMPT_VERSION}; its results would be cached under the wrong version."
        )
    failed = manifest.setdefault("failed", {})
    summary = {"saved": 0, "already_saved": 0, "failed": failed}
    for item in client.messages.batches.results(batch_id):
        tile = Path(manifest["tiles"][item.custom_id])
        if extract.cache_path(tile, model, effort).exists() or item.custom_id in failed:
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
            extraction = extract.TileExtraction.model_validate_json(text)
        except (ValidationError, ValueError) as e:
            # Still billed, so still recorded.
            costs.record(model, *usage, what=f"{tile.name} (failed)", batch=True)
            failed[item.custom_id] = f"{msg.stop_reason}: {str(e)[:120]}"
            continue
        extract.save_result(tile, model, effort, msg.model, *usage, extraction, batch=True)
        summary["saved"] += 1
    (BATCH_DIR / f"{batch_id}.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return summary
