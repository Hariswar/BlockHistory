from PIL import Image

from blockhistory import costs
from blockhistory.map_reader import tanks


def _group(site, number, circles, label="G.T.S."):
    return tanks.TankGroup(
        tank_label=label,
        circles=circles,
        site_label=site,
        site_street_number=number,
        partial=False,
        confidence="high",
    )


def test_apply_takes_the_max_over_overlapping_crops_and_adds_missed_sites(tmp_path, monkeypatch):
    monkeypatch.setattr(tanks, "ROOT", tmp_path)
    monkeypatch.setattr(tanks, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(costs, "LEDGER", tmp_path / "spend.jsonl")
    tile_dir = tmp_path / "data" / "tiles" / "area" / "1938" / "S-0050"
    tile_dir.mkdir(parents=True)
    Image.new("RGB", (8, 8)).save(tile_dir / "S-0050_r0_c0.jpg")
    crops = tanks.hires_dir(tile_dir)
    crops.mkdir(parents=True)
    readings = {
        # The station sits in the overlap, so both crops see all 3 circles.
        "q00": [_group("FILL'G STA.", "6930", 3)],
        "q01": [_group("FILLG STA. CONC. FL.", None, 3), _group("AUTO REP.", "116", 1, "G.T.")],
        # No site named: goes to the tile's only fuel finding, so still 3 (max), not 5.
        "q10": [_group("", None, 2)],
    }
    for i, (q, groups) in enumerate(readings.items()):
        crop = crops / f"S-0050_r0_c0_{q}.jpg"
        Image.new("RGB", (8, 8), (i, 0, 0)).save(crop)
        tanks.save_result(
            crop, *tanks.resolve(), "claude-haiku-5-5", 1, 1, tanks.TankReading(groups=groups)
        )

    station = {
        "label": "FILL'G STA.",
        "use": "filling station",
        "street_number": "6930",
        "gasoline_tank_count": 0,
        "tiles": ["S-0050_r0_c0.jpg"],
    }
    findings = [station]
    summary = tanks.apply(findings, tile_dir)

    assert station["gasoline_tank_count"] == 3  # not 6: crops overlap
    (added,) = findings[1:]
    assert added["label"] == "AUTO REP." and added["gasoline_tank_count"] == 1
    assert summary["changed"] == 1 and summary["added"] == 1


def test_candidates_skip_private_garages():
    assert tanks.is_candidate({"label": "FILL'G STA.", "use": "filling station"})
    assert tanks.is_candidate({"label": "D", "use": "dwelling", "gasoline_tank_count": 1})
    assert not tanks.is_candidate({"label": "A 3 CARS", "use": "private garage for 3 cars"})


def test_tanks_seen_across_a_tile_edge_are_not_a_new_site(tmp_path, monkeypatch):
    monkeypatch.setattr(tanks, "ROOT", tmp_path)
    monkeypatch.setattr(tanks, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(costs, "LEDGER", tmp_path / "spend.jsonl")
    tile_dir = tmp_path / "data" / "tiles" / "area" / "1950" / "S-0057"
    tile_dir.mkdir(parents=True)
    for t in ("S-0057_r0_c0.jpg", "S-0057_r1_c0.jpg"):
        Image.new("RGB", (8, 8)).save(tile_dir / t)
    crops = tanks.hires_dir(tile_dir)
    crops.mkdir(parents=True)
    crop = crops / "S-0057_r0_c0_q10.jpg"
    Image.new("RGB", (8, 8), (9, 0, 0)).save(crop)
    groups = [
        # The used-car lot on the next tile, named a little differently: same tanks.
        _group("AUTO. SALES", None, 4, "IR. GASOL. TKS."),
        # A station with a different street number on the next tile: a separate site.
        _group("FILL'G STA.", "100", 2, "G.T."),
    ]
    tanks.save_result(
        crop, *tanks.resolve(), "claude-haiku-5-5", 1, 1, tanks.TankReading(groups=groups)
    )
    lot = {"label": "USED AUTO SALES", "use": "used car lot", "street_number": "7414",
           "gasoline_tank_count": 3, "tiles": ["S-0057_r1_c0.jpg"]}  # fmt: skip
    station = {"label": "FILL'G STA.", "use": "filling station", "street_number": "6800",
               "gasoline_tank_count": 1, "tiles": ["S-0057_r1_c0.jpg"]}  # fmt: skip
    findings = [lot, station]
    tanks.apply(findings, tile_dir)
    assert lot["gasoline_tank_count"] == 4  # folded in, max of the two views
    assert station["gasoline_tank_count"] == 1  # "100" is not "6800"
    assert [f["label"] for f in findings[2:]] == ["FILL'G STA."]  # the other station is new
