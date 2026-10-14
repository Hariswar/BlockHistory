import pytest

from blockhistory.db import corrections
from blockhistory.georef.transform import GCP, Affine


def _panels():
    # 0.1 m per pixel, north up, one panel covering the whole sheet.
    gcps = [GCP(x, y, 38.55 - y * 0.1 / 111_320, -90.25 + x * 0.1 / 87_000, "")
            for x, y in [(0, 0), (3000, 0), (0, 3800)]]  # fmt: skip
    return [("S-0001", None, Affine(gcps))]


def _f(label, px, **kw):
    return {"label": label, "use": "", "sheet_px": px, "gasoline_tank_count": 0, "tiles": []} | kw


FIX = {
    "hide": [{"sheet": 1, "label": "FILL'G STA.", "near": [100, 100]}],
    "set": [
        {
            "sheet": 1,
            "label": "PRINT SHOP",
            "near": [500, 500],
            "new_label": "PAINT SHOP",
            "use": "paint shop",
        },
        {"sheet": 1, "label": "GARAGE", "near": [900, 900], "sheet_px": [900, 600]},
    ],
    "add": [
        {
            "sheet": 1,
            "label": "MONSANTO CHEMICAL CO.",
            "use": "chemical plant",
            "sheet_px": [2000, 3000],
        }
    ],
}


def test_hide_set_and_add():
    found = [
        _f("FILL'G STA.", [110, 95]),  # the one to hide
        _f("FILL'G STA.", [1500, 1500]),  # same label far away: kept
        _f("PRINT SHOP", [505, 498]),
        _f("GARAGE", [900, 905]),
    ]
    out, problems = corrections.apply(found, FIX, 1, _panels())
    assert problems == []
    assert [f["label"] for f in out] == [
        "FILL'G STA.",
        "PAINT SHOP",
        "GARAGE",
        "MONSANTO CHEMICAL CO.",
    ]
    assert out[0]["sheet_px"] == [1500, 1500]
    assert out[1]["use"] == "paint shop"
    moved = out[2]
    assert moved["sheet_px"] == [900, 600] and moved["location_method"] == "hand-placed"
    assert moved["lat"] == pytest.approx(38.55 - 600 * 0.1 / 111_320)
    assert out[3]["location_method"] == "hand-placed" and out[3]["tiles"] == []


def test_unmatched_corrections_are_reported_not_ignored():
    out, problems = corrections.apply([_f("GARAGE", [0, 0])], FIX, 1, _panels())
    assert len(out) == 2  # the garage stays, the plant is added
    assert any("FILL'G STA." in p for p in problems) and any("PRINT SHOP" in p for p in problems)


def test_other_sheets_untouched():
    found = [_f("FILL'G STA.", [100, 100])]
    out, problems = corrections.apply(found, FIX, 2, _panels())
    assert out == found and problems == []
