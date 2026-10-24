"""API spend tracking with hard spending caps.

The whole project has about $10 of paid API budget for the year (docs/budget.md). Every paid
model call is appended to a local ledger (data/spend.jsonl). Before each call,
`check_budget()` refuses to run if this month's spend has reached the monthly cap, or if all
spend to date has reached the project cap, so a runaway loop can't blow the budget. Cached
results cost nothing and are never logged.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

LEDGER = Path(__file__).resolve().parents[1] / "data" / "spend.jsonl"
DEFAULT_MONTHLY_CAP_USD = 3.0
DEFAULT_TOTAL_CAP_USD = 10.0

# USD per million tokens (input, output), standard rates for prompts under 100K tokens.
PRICES = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
}
BATCH_DISCOUNT = 0.5


class BudgetExceeded(RuntimeError):
    pass


def call_cost(model: str, input_tokens: int, output_tokens: int, batch: bool = False) -> float:
    in_price, out_price = PRICES[model]
    cost = (input_tokens * in_price + output_tokens * out_price) / 1_000_000
    return cost * BATCH_DISCOUNT if batch else cost


def monthly_cap() -> float:
    return float(os.environ.get("BLOCKHISTORY_MONTHLY_CAP_USD") or DEFAULT_MONTHLY_CAP_USD)


def total_cap() -> float:
    return float(os.environ.get("BLOCKHISTORY_TOTAL_CAP_USD") or DEFAULT_TOTAL_CAP_USD)


def _entries(ledger: Path | None) -> list[dict]:
    ledger = ledger or LEDGER
    if not ledger.exists():
        return []
    return [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]


def month_spend(ledger: Path | None = None, month: str | None = None) -> float:
    month = month or datetime.now(UTC).strftime("%Y-%m")
    return sum(e["usd"] for e in _entries(ledger) if e["at"].startswith(month))


def total_spend(ledger: Path | None = None) -> float:
    return sum(e["usd"] for e in _entries(ledger))


def check_budget(ledger: Path | None = None) -> None:
    spent, cap = total_spend(ledger), total_cap()
    if spent >= cap:
        raise BudgetExceeded(
            f"Spent ${spent:.2f} of the ${cap:.2f} project budget. "
            "Raise BLOCKHISTORY_TOTAL_CAP_USD in .env only if you have new credits."
        )
    spent, cap = month_spend(ledger), monthly_cap()
    if spent >= cap:
        raise BudgetExceeded(
            f"Spent ${spent:.2f} of the ${cap:.2f} monthly cap. "
            "Wait for next month or raise BLOCKHISTORY_MONTHLY_CAP_USD in .env."
        )


def record(
    model: str,
    input_tokens: int,
    output_tokens: int,
    what: str,
    batch: bool = False,
    ledger: Path | None = None,
) -> float:
    ledger = ledger or LEDGER
    usd = call_cost(model, input_tokens, output_tokens, batch)
    entry = {
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "batch": batch,
        "usd": round(usd, 6),
        "what": what,
    }
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return usd
