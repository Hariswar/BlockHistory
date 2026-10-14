import json

import pytest

from blockhistory.db import store
from blockhistory.explain import category, explanation


def _finding(label, use, lat, lon, tanks=0, method="point pass"):
    return {
        "label": label,
        "use": use,
        "street_number": None,
        "gasoline_tank_count": tanks,
        "confidence": "medium",
        "lat": lat,
        "lon": lon,
        "location_method": method,
        "uncertainty_m": 10,
        "sheet_px": [0, 0],
        "tiles": ["S-0001_r0_c0.jpg"],
    }


@pytest.fixture
def con(tmp_path):
    con = store.connect(tmp_path / "t.sqlite")
    square = [[-90.26, 38.54], [-90.25, 38.54], [-90.25, 38.55], [-90.26, 38.55], [-90.26, 38.54]]
    con.execute(
        "INSERT INTO sheets VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("S-0001", "a", "1938", 1, "v", "", "svc", 0.1, 2.0, 1.0, json.dumps({"type": "Polygon", "coordinates": [square]})),
    )  # fmt: skip
    rows = [
        _finding("FILL'G STA.", "filling station", 38.5450, -90.2550, tanks=3),
        _finding("FILLG STA", "filling station", 38.54505, -90.2550, method="position words"),
        _finding("FOUNDRY", "foundry", 38.5458, -90.2550),  # ~90 m north
        _finding("A", "private garage", 38.5451, -90.2551),  # low: stored, not shown
    ]
    for f in store._dedupe(rows):
        con.execute(
            "INSERT INTO findings (sheet_id, label, use, relevance, gasoline_tank_count,"
            " review_status, lat, lon) VALUES ('S-0001',?,?,?,?,'unreviewed',?,?)",
            (f["label"], f["use"], "low" if f["label"] == "A" else "high", f["gasoline_tank_count"], f["lat"], f["lon"]),
        )  # fmt: skip
    return con


def test_search_finds_nearby_sites_and_merges_repeat_reads(con):
    res = store.search(con, 38.5450, -90.2550, radius_m=100)
    assert [f["label"] for f in res["findings"]] == ["FILL'G STA.", "FOUNDRY"]
    assert res["findings"][0]["gasoline_tank_count"] == 3
    assert 85 < res["findings"][1]["distance_m"] < 95
    assert [s["sheet_id"] for s in res["covered_by"]] == ["S-0001"]


def test_search_outside_any_sheet_says_not_covered(con):
    res = store.search(con, 38.60, -90.30)
    assert res == {"findings": [], "covered_by": []}


def test_postgis_export_uses_geography(con, tmp_path):
    out = tmp_path / "load.sql"
    assert store.export_postgis_sql(con, out) == 3
    sql = out.read_text()
    assert "ST_Point(-90.255, 38.545, 4326)::geography" in sql
    assert "FILL''G STA." in sql  # quotes escaped


def test_explanations_follow_the_safety_rules():
    text = explanation(
        {"label": "FILL'G STA.", "use": "filling station", "gasoline_tank_count": 2}, "1938"
    )
    assert text.startswith(
        "The 1938 Sanborn fire insurance map labels this site “FILL'G STA.” (filling station)."
    )
    assert "gasoline tanks" in text and "not a test result" in text
    assert "contaminated" not in text.lower()
    assert category("GASOL. ENG.", "gasoline engine house")[0] == "fuel"
    assert category("DRY CLEANING", "dry cleaner")[0] == "dry cleaning"
    assert category("AUTO. REP.", "auto repair")[0] == "auto"
    assert (
        category("ST. LOUIS SULPHUR & CHEM. CO.", "chemical works")[0]
        == "chemicals, paint and printing"
    )


def test_tanks_at_a_non_fuel_site_get_their_own_sentence():
    text = explanation(
        {"label": "AUTO. REP.", "use": "auto repair", "gasoline_tank_count": 1}, "1938"
    )
    assert "Auto repair shops" in text and "buried tanks sometimes leaked" in text
