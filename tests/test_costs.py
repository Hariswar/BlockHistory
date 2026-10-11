import json
from types import SimpleNamespace

import pytest
from PIL import Image

from blockhistory import costs
from blockhistory.map_reader import extract


def test_call_cost_uses_per_million_prices():
    # 2,000 in + 3,000 out on Sonnet 5.5 = 0.004 + 0.03
    assert costs.call_cost("claude-sonnet-5-5", 2_000, 3_000) == pytest.approx(0.034)
    assert costs.call_cost("claude-haiku-5-5", 2_000, 3_000) == pytest.approx(0.0017)
    assert costs.call_cost("claude-sonnet-5-5", 2_000, 3_000, batch=True) == pytest.approx(0.017)
    with pytest.raises(KeyError):  # Opus isn't in the plan, so it has no price here
        costs.call_cost("claude-opus-5-5", 1, 1)


def test_monthly_cap_blocks_after_limit(tmp_path, monkeypatch):
    ledger = tmp_path / "spend.jsonl"
    monkeypatch.setenv("BLOCKHISTORY_MONTHLY_CAP_USD", "0.05")
    costs.check_budget(ledger)  # empty ledger is fine
    costs.record("claude-sonnet-5-5", 2_000, 3_000, what="t1", ledger=ledger)
    assert costs.month_spend(ledger) == pytest.approx(0.034)
    costs.check_budget(ledger)  # still under
    costs.record("claude-sonnet-5-5", 2_000, 3_000, what="t2", ledger=ledger)
    with pytest.raises(costs.BudgetExceeded, match="monthly"):
        costs.check_budget(ledger)


def test_project_cap_counts_every_month(tmp_path, monkeypatch):
    ledger = tmp_path / "spend.jsonl"
    old = {"at": "2026-01-15T00:00:00+00:00", "usd": 9.99, "model": "claude-haiku-5-5"}
    ledger.write_text(json.dumps(old) + "\n")
    assert costs.month_spend(ledger) == 0  # a past month doesn't count toward this month
    costs.check_budget(ledger)
    costs.record("claude-sonnet-5-5", 2_000, 3_000, what="t1", ledger=ledger)
    assert costs.total_spend(ledger) == pytest.approx(10.024)
    with pytest.raises(costs.BudgetExceeded, match="project budget"):
        costs.check_budget(ledger)


class FakeMessages:
    def __init__(self):
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            stop_reason="end_turn",
            stop_details=None,
            model=kwargs["model"],
            usage=SimpleNamespace(input_tokens=1_500, output_tokens=500),
            parsed_output=extract.TileExtraction(
                streets=[], buildings=[], other_features=[], illegible_notes=[]
            ),
        )


@pytest.fixture
def fake_env(tmp_path, monkeypatch):
    monkeypatch.setattr(costs, "LEDGER", tmp_path / "spend.jsonl")
    monkeypatch.setattr(extract, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.delenv("BLOCKHISTORY_MODEL", raising=False)
    tile = tmp_path / "tile.jpg"
    Image.new("RGB", (64, 64), "white").save(tile)
    messages = FakeMessages()
    client = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    return tile, client, messages


def test_read_tile_records_spend_and_caches(fake_env):
    tile, client, messages = fake_env
    first = extract.read_tile(tile, client=client, model="claude-haiku-5-5", effort="low")
    again = extract.read_tile(tile, client=client, model="claude-haiku-5-5", effort="low")
    assert len(messages.calls) == 1 and again["cached"] and not first["cached"]
    assert first["usd"] == pytest.approx(0.0004)  # 1,500 x $0.10 + 500 x $0.50 per M
    assert costs.month_spend() == pytest.approx(0.0004)
    # Haiku 5.5 has no server-side fallback, so none is requested.
    assert "fallbacks" not in messages.calls[0]


def test_read_tile_model_from_env_and_fallback_on_sonnet(fake_env, monkeypatch):
    tile, client, messages = fake_env
    monkeypatch.setenv("BLOCKHISTORY_MODEL", "claude-sonnet-5-5")
    extract.read_tile(tile, client=client)
    assert messages.calls[0]["model"] == "claude-sonnet-5-5"
    assert messages.calls[0]["fallbacks"] == "default"


def test_read_tile_refuses_when_over_budget(fake_env, monkeypatch):
    tile, client, messages = fake_env
    monkeypatch.setenv("BLOCKHISTORY_MONTHLY_CAP_USD", "0")
    with pytest.raises(costs.BudgetExceeded):
        extract.read_tile(tile, client=client)
    assert messages.calls == []


def test_blank_env_values_fall_back_to_defaults(fake_env, monkeypatch):
    tile, client, messages = fake_env
    # .env.example ships these blank.
    monkeypatch.setenv("BLOCKHISTORY_MODEL", "")
    monkeypatch.setenv("BLOCKHISTORY_EFFORT", "")
    monkeypatch.setenv("BLOCKHISTORY_MONTHLY_CAP_USD", "")
    assert costs.monthly_cap() == costs.DEFAULT_MONTHLY_CAP_USD
    result = extract.read_tile(tile, client=client)
    assert messages.calls[0]["model"] == extract.DEFAULT_MODEL
    assert result["effort"] == extract.DEFAULT_EFFORT
