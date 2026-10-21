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
    assert res == {"findings": [], "covered_by": [], "records": []}


def test_postgis_export_uses_geography(con, tmp_path):
    out = tmp_path / "load.sql"
    n, files = store.export_postgis_sql(con, out)
    assert n == 3 and [f.name for f in files] == ["load_1.sql"]
    sql = files[0].read_text()
    assert sql.index("DELETE FROM findings") < sql.index("INSERT INTO sheets")
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
    assert category("ST. LOUIS SULPHUR & CHEM. CO.", "chemical works")[0] == "chemicals"
    assert category("4E MISC STGE ACID TANK", "storage with acid tank")[0] == "chemicals"
    assert category("PAINT SHOP", "paint shop")[0] == "paint and printing"
    assert "chemicals" in explanation(
        {"label": "MONSANTO CHEMICAL CO.", "use": "chemical plant"}, "1938"
    ) and "inks" not in explanation(
        {"label": "MONSANTO CHEMICAL CO.", "use": "chemical plant"}, "1938"
    )


def test_tanks_at_a_non_fuel_site_get_their_own_sentence():
    text = explanation(
        {"label": "AUTO. REP.", "use": "auto repair", "gasoline_tank_count": 1}, "1938"
    )
    assert "Auto repair shops" in text and "buried tanks sometimes leaked" in text


def test_postgis_export_splits_into_parts_that_each_commit(con, tmp_path, monkeypatch):
    monkeypatch.setattr(store, "PART_BYTES", 400)
    n, files = store.export_postgis_sql(con, tmp_path / "load.sql")
    assert len(files) > 1
    texts = [f.read_text() for f in files]
    assert all(t.count("BEGIN;") == 1 and t.rstrip().endswith("COMMIT;") for t in texts)
    assert "DELETE FROM" in texts[0] and not any("DELETE FROM" in t for t in texts[1:])
    assert sum(t.count("INSERT INTO findings") for t in texts) == n


def test_misread_repeats_merge_but_facing_corners_stay_apart():
    near = 38.5450 + 20 / 111_320  # 20 m north
    rows = [
        _finding("MACH. SHOP", "machine shop", 38.5450, -90.2550),
        _finding("MACHI SHOP", "machine shop", near, -90.2550),  # misread repeat: merged
        _finding("FILL'G STA.", "filling station", 38.5460, -90.2550, tanks=2),
        _finding("FILL'G STA.", "filling station", 38.5460 + 20 / 111_320, -90.2550),
    ]
    sites = store.prepare_sites(rows)
    labels = sorted(f["label"] for f in sites)
    assert labels == ["FILL'G STA.", "FILL'G STA.", "MACH. SHOP"]


def test_low_confidence_guessed_dry_cleaner_is_not_shown():
    guess = _finding("DRY CLEANING", "dry cleaner", 38.5450, -90.2550) | {"confidence": "low"}
    printed = _finding("DRY CLEANG", "dry cleaner", 38.5470, -90.2550) | {"confidence": "low"}
    sure = _finding("DRY CLEANING", "dry cleaner", 38.5490, -90.2550)  # medium
    rel = {
        f["label"] + str(f["lat"]): f["relevance"]
        for f in store.prepare_sites([guess, printed, sure])
    }
    assert sorted(rel.values()) == ["high", "high", "low"]


def _record(name, lat, lon, release=True):
    return {
        "source": "Missouri DNR", "kind": "tank", "name": name, "address": "1 Main",
        "status": "No Further Action Letter Issued with Restriction",
        "status_plain": "a petroleum leak was cleaned up; limits on how the land is used remain",
        "release": release, "contaminants": "Petroleum constituents", "detail": None, "url": None,
        "lat": lat, "lon": lon, "located_by": "parcel",
    }  # fmt: skip


def test_records_are_returned_only_where_the_maps_cover(con, tmp_path):
    store.load_records(
        con, [_record("BROADWAY 66", 38.5451, -90.2550), _record("FAR", 38.60, -90.30)]
    )
    res = store.search(con, 38.5450, -90.2550)
    assert [r["name"] for r in res["records"]] == ["BROADWAY 66"]
    assert res["records"][0]["distance_m"] == 11 and res["records"][0]["release"] == 1
    assert store.search(con, 38.60, -90.30)["records"] == []  # not covered: nothing either way
    _, files = store.export_postgis_sql(con, tmp_path / "load.sql")
    sql = files[0].read_text()
    assert "DELETE FROM records" in sql and "INSERT INTO records" in sql and "TRUE" in sql


def test_ai_explanations_are_checked_and_framed(tmp_path, monkeypatch):
    from blockhistory import explain_ai

    f = explain_ai.facts({"label": "BENZOL PLANT", "use": "benzol plant"})
    ok = (
        "A benzol plant refined light oil from coke-oven gas into benzene and related "
        "solvents. Spilled solvents could soak into soil and sometimes reach groundwater."
    )
    assert explain_ai.check(ok, f) is None
    assert "contaminat" in explain_ai.check("The site is contaminated with benzene.", f)
    assert "you" in explain_ai.check("You may want to test the soil.", f).lower()
    assert "number" in explain_ai.check("It ran from 1890 on.", f)
    assert explain_ai.check("One. Two. Three.", f) == "more than 2 sentences"

    # A passing text replaces only the category sentence; the framing stays.
    monkeypatch.setattr(explain_ai, "ai_text", lambda finding, model=None: ok)
    text, source = explain_ai.explanation(
        {"label": "BENZOL PLANT", "use": "benzol plant", "gasoline_tank_count": 1}, "1938"
    )
    assert source == "ai" and ok in text
    assert text.startswith("The 1938 Sanborn fire insurance map labels this site “BENZOL PLANT”")
    assert text.endswith("This is a historical use, not a test result.")
    monkeypatch.setattr(explain_ai, "ai_text", lambda finding, model=None: None)
    assert (
        explain_ai.explanation({"label": "BENZOL PLANT", "use": "benzol plant"}, "1938")[1]
        == "template"
    )


def test_abbreviations_are_not_sentence_ends():
    from blockhistory import explain_ai

    f = explain_ai.facts({"label": "PAINT W. HO.", "use": "paint warehouse"})
    text = (
        "PAINT W. HO. likely means a paint warehouse, where paint products were stored. "
        "Such places often held solvents and pigments that could reach soil or groundwater."
    )
    assert explain_ai.check(text, f) is None
