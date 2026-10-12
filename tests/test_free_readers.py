import json as jsonlib
import shutil
from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw, ImageFont

from blockhistory.map_reader import free_vision, ocr


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")
def test_ocr_reads_horizontal_and_rotated_labels(tmp_path):
    tile = tmp_path / "tile.png"
    img = Image.new("RGB", (400, 400), (240, 235, 220))  # map-paper color
    font = ImageFont.load_default(size=14)
    ImageDraw.Draw(img).text((40, 60), "CLAY SHED", fill="black", font=font)
    # Text running bottom-to-top, as Sanborn labels along a long building often do.
    side = Image.new("RGB", (200, 30), (240, 235, 220))
    ImageDraw.Draw(side).text((10, 5), "KILNS", fill="black", font=font)
    img.paste(side.rotate(90, expand=True), (300, 150))
    img.save(tile)

    words = {w["text"].upper() for w in ocr.read_tile_ocr(tile)}
    assert {"CLAY", "SHED", "KILNS"} <= words


def test_free_vision_calls_ollama_and_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(free_vision, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setenv("OLLAMA_HOST", "http://colab.example:11434")
    tile = tmp_path / "tile.jpg"
    Image.new("RGB", (32, 32), "white").save(tile)
    content = {
        "streets": ["Macklind Ave"],
        "buildings": [
            {
                "label": "OIL HO.",
                "use": "oil house",
                "street_number": None,
                "street_name": None,
                "construction": "frame",
                "stories": "1",
                "gasoline_tank_count": 0,
                "partial": False,
                "confidence": "medium",
                "position": "center",
            }
        ],
        "other_features": [],
        "illegible_notes": [],
    }
    calls = []

    def fake_post(url, json, timeout):
        calls.append((url, json))
        body = {
            "message": {"content": jsonlib.dumps(content)},
            "prompt_eval_count": 900,
            "eval_count": 120,
            "total_duration": 4_200_000_000,
        }
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: body)

    monkeypatch.setattr(free_vision.requests, "post", fake_post)
    first = free_vision.read_tile_free(tile, model="qwen2.5vl:7b")
    again = free_vision.read_tile_free(tile, model="qwen2.5vl:7b")

    assert len(calls) == 1 and again["cached"] and not first["cached"]
    url, payload = calls[0]
    assert url == "http://colab.example:11434/api/chat"
    assert payload["model"] == "qwen2.5vl:7b" and payload["messages"][1]["images"]
    assert payload["format"]["properties"]["buildings"]  # constrained to the shared schema
    assert first["usd"] == 0.0 and first["seconds"] == 4.2
    assert first["extraction"]["buildings"][0]["label"] == "OIL HO."
    (cached_file,) = (tmp_path / "cache").glob("*.json")
    assert jsonlib.loads(cached_file.read_text())["model"] == "qwen2.5vl:7b"


def test_salvage_keeps_complete_buildings_from_cut_off_reply():
    b = {
        "label": "FILL'G STA.",
        "use": "filling station",
        "street_number": "6226",
        "street_name": "S Broadway",
        "construction": "brick",
        "stories": "1",
        "gasoline_tank_count": 2,
        "partial": False,
        "confidence": "high",
        "position": "bottom left",
    }
    other = {**b, "label": "COAL YARD", "use": "coal yard", "gasoline_tank_count": 0}
    whole = jsonlib.dumps({"streets": ["S Broadway"], "buildings": [b, b, other]})
    # Cut off mid-way through a fourth entry, like the first Colab run.
    cut = whole[:-2] + ', {"label": "JUNK YARD", "use": "junk", "has_gas'

    extraction, dupes = free_vision._salvage(cut)
    assert [x.label for x in extraction.buildings] == ["FILL'G STA.", "COAL YARD"]
    assert dupes == 1
    assert extraction.streets == ["S Broadway"]
    assert free_vision._salvage("not json at all {")[0].buildings == []
