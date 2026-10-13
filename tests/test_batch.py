import json
from types import SimpleNamespace

import pytest
from PIL import Image

from blockhistory import costs
from blockhistory.map_reader import batch, extract, sheets


def _extraction(label, tanks=0):
    return {
        "streets": [],
        "buildings": [
            {
                "label": label,
                "use": "filling station",
                "street_number": "7106",
                "street_name": "S Broadway",
                "construction": "brick",
                "stories": "1",
                "gasoline_tank_count": tanks,
                "partial": False,
                "confidence": "medium",
                "position": "left",
            }
        ],
        "other_features": [],
        "illegible_notes": [],
    }


class FakeBatches:
    def __init__(self, results):
        self.created = []
        self._results = results

    def create(self, requests):
        self.created.append(requests)
        return SimpleNamespace(id="msgbatch_test")

    def results(self, batch_id):
        return self._results


def _ok(custom_id, payload, stop="end_turn"):
    msg = SimpleNamespace(
        model="claude-haiku-5-5",
        stop_reason=stop,
        stop_details=None,
        usage=SimpleNamespace(input_tokens=4000, output_tokens=1000),
        content=[SimpleNamespace(type="text", text=payload)],
    )
    return SimpleNamespace(
        custom_id=custom_id, result=SimpleNamespace(type="succeeded", message=msg)
    )


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(costs, "LEDGER", tmp_path / "spend.jsonl")
    monkeypatch.setattr(extract, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(batch, "BATCH_DIR", tmp_path / "batches")
    monkeypatch.setattr(sheets, "OCR_CACHE", tmp_path / "ocr")
    for k in ("BLOCKHISTORY_MODEL", "BLOCKHISTORY_EFFORT", "BLOCKHISTORY_MONTHLY_CAP_USD"):
        monkeypatch.delenv(k, raising=False)
    tile_dir = tmp_path / "04858_12_1938-0053"
    tile_dir.mkdir()
    tiles = []
    for i, name in enumerate(["r0_c0", "r0_c1", "r1_c0"]):
        t = tile_dir / f"04858_12_1938-0053_{name}.jpg"
        Image.new("RGB", (32, 32), (i * 40, 0, 0)).save(t)  # distinct bytes per tile
        tiles.append(t)
    return tiles


def test_submit_skips_cached_and_builds_structured_requests(env):
    tiles = env
    extract.save_result(
        tiles[0],
        "claude-haiku-5-5",
        "low",
        "claude-haiku-5-5",
        1,
        1,
        extract.TileExtraction.model_validate(_extraction("X")),
    )
    fake = FakeBatches([])
    m = batch.submit(tiles, client=SimpleNamespace(messages=SimpleNamespace(batches=fake)))
    (reqs,) = fake.created
    assert m["submitted"] == 2 and m["already_cached"] == 1
    assert [r["custom_id"] for r in reqs] == [t.stem for t in tiles[1:]]
    params = reqs[0]["params"]
    assert params["model"] == "claude-haiku-5-5"
    assert params["output_config"]["effort"] == "low"
    assert params["output_config"]["format"]["type"] == "json_schema"
    assert "fallbacks" not in params  # not allowed on the Batch API


def test_submit_refuses_batch_over_monthly_cap(env, monkeypatch):
    monkeypatch.setenv("BLOCKHISTORY_MONTHLY_CAP_USD", "0.0001")
    with pytest.raises(costs.BudgetExceeded):
        batch.submit(env, client=SimpleNamespace(messages=SimpleNamespace(batches=FakeBatches([]))))


def test_collect_caches_results_once_and_bills_at_batch_price(env):
    tiles = env
    fake = FakeBatches(
        [
            _ok(tiles[0].stem, json.dumps(_extraction("FILL'G STA.", 2))),
            _ok(tiles[1].stem, json.dumps(_extraction("FILL'G STA.", 1))),
            _ok(tiles[2].stem, '{"streets": [', stop="max_tokens"),
        ]
    )
    client = SimpleNamespace(messages=SimpleNamespace(batches=fake))
    batch.submit(tiles, client=client)
    first = batch.collect("msgbatch_test", client=client)
    again = batch.collect("msgbatch_test", client=client)

    assert first["saved"] == 2 and list(first["failed"]) == [tiles[2].stem]
    assert again["saved"] == 0 and again["already_saved"] == 3
    # 3 billed results (incl. the failed one), each 4000 in / 1000 out at half price; none twice.
    assert costs.month_spend() == pytest.approx(
        3 * costs.call_cost("claude-haiku-5-5", 4000, 1000, batch=True)
    )
    cached = extract.load_cached(tiles[0])
    assert (
        cached["batch"] is True and cached["extraction"]["buildings"][0]["gasoline_tank_count"] == 2
    )


def test_merge_sheet_joins_overlap_duplicates(env, monkeypatch):
    tiles = env
    monkeypatch.setattr(sheets, "read_tile_ocr", lambda t: [{"text": "FILL'G", "confidence": 90}])
    for t, tanks in zip(tiles[:2], (2, 1)):
        extract.save_result(
            t,
            "claude-haiku-5-5",
            "low",
            "claude-haiku-5-5",
            1,
            1,
            extract.TileExtraction.model_validate(_extraction("FILL'G STA.", tanks)),
        )
    merged = sheets.merge_sheet(tiles[0].parent)
    (f,) = merged["findings"]  # r0_c0 and r0_c1 are neighbors, so one finding
    assert len(f["tiles"]) == 2 and f["gasoline_tank_count"] == 2
    assert f["relevance"] == "high" and f["ocr_seen"] is True
    assert merged["tiles_missing"] == [tiles[2].name]


@pytest.mark.parametrize("pair, expected", [((0, 1), 1), ((1, 2), 2)])
def test_merge_numbered_with_unnumbered_only_across_an_edge(env, monkeypatch, pair, expected):
    # r0_c0 / r0_c1 share an edge: same site, one read missed the number (sheets 49, 56, 61).
    # r0_c1 / r1_c0 are diagonal: kept apart, like sheet 47's two filling stations.
    tiles = env
    monkeypatch.setattr(sheets, "read_tile_ocr", lambda t: [])
    numbered = _extraction("FILL'G STA.", 3)
    unnumbered = _extraction("FILL'G STA.", 3)
    unnumbered["buildings"][0]["street_number"] = None
    for i, ext in zip(pair, (numbered, unnumbered)):
        extract.save_result(
            tiles[i],
            "claude-haiku-5-5",
            "low",
            "claude-haiku-5-5",
            1,
            1,
            extract.TileExtraction.model_validate(ext),
        )
    merged = sheets.merge_sheet(tiles[0].parent)
    assert len(merged["findings"]) == expected


def test_merge_keeps_two_same_label_entries_from_one_tile(env, monkeypatch):
    # Sheet 53: a TIN SHOP at 7120 and an unnumbered one behind it, read from one tile.
    tiles = env
    monkeypatch.setattr(sheets, "read_tile_ocr", lambda t: [])
    ext = _extraction("TIN SHOP")
    ext["buildings"].append({**ext["buildings"][0], "street_number": None})
    extract.save_result(
        tiles[0],
        "claude-haiku-5-5",
        "low",
        "claude-haiku-5-5",
        1,
        1,
        extract.TileExtraction.model_validate(ext),
    )
    assert len(sheets.merge_sheet(tiles[0].parent)["findings"]) == 2
