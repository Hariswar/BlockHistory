import math

import pytest

from blockhistory.georef import osm
from blockhistory.georef.locate import _fraction
from blockhistory.georef.transform import (
    GCP,
    Affine,
    distance_m,
    in_outline,
    leave_one_out,
    parse_outline,
    read_outline,
    read_points,
    write_points,
)

LAT0, LON0 = 38.55, -90.257
KX = 111_320 * math.cos(math.radians(LAT0))


def _sheet(px, py):
    """A made-up sheet: 0.1 m/px, rotated 30 degrees, like a Sanborn sheet."""
    a = math.radians(30)
    east = 0.1 * (px * math.cos(a) + py * math.sin(a))
    north = 0.1 * (px * math.sin(a) - py * math.cos(a))
    return LAT0 + north / 111_320, LON0 + east / KX


def _gcps():
    return [GCP(x, y, *_sheet(x, y), f"p{i}") for i, (x, y) in enumerate([(0, 0), (3000, 0), (0, 3800), (3000, 3800), (1500, 1900)])]  # fmt: skip


def test_affine_recovers_a_rotated_sheet():
    t = Affine(_gcps())
    assert t.meters_per_pixel() == pytest.approx(0.1, rel=1e-4)
    assert distance_m(t.to_latlon(1234, 567), _sheet(1234, 567)) < 0.01
    assert max(leave_one_out(_gcps())) < 0.01


def test_similarity_fits_points_along_one_street():
    # Four crossings on one straight street: too few for an affine, enough for a similarity.
    on_a_line = [GCP(1000, y, *_sheet(1000, y), f"p{y}") for y in (300, 1400, 2500, 3600)]
    t = Affine(on_a_line, "similarity")
    assert t.meters_per_pixel() == pytest.approx(0.1, rel=1e-4)
    assert distance_m(t.to_latlon(2500, 900), _sheet(2500, 900)) < 0.01  # off the street too
    assert max(leave_one_out(on_a_line, "similarity")) < 0.01
    with pytest.raises(ValueError):
        Affine(on_a_line)  # collinear


def test_leave_one_out_flags_a_bad_point():
    gcps = _gcps()
    gcps[4].lat += 20 / 111_320  # 20 m off
    loo = leave_one_out(gcps)
    assert loo.index(max(loo)) == 4 and max(loo) > 15


def test_points_file_round_trip(tmp_path):
    path = tmp_path / "s.points"
    write_points(path, _gcps())
    back = read_points(path)
    assert [g.name for g in back] == [g.name for g in _gcps()]
    assert back[3].py == pytest.approx(3800) and back[3].lat == pytest.approx(_gcps()[3].lat)
    assert "mapX,mapY,sourceX,sourceY" in path.read_text()  # QGIS can open it


def test_panel_outline_round_trip(tmp_path):
    path = tmp_path / "s.inset.points"
    box = parse_outline("2230,0,3201,3898")
    assert box == [(2230, 0), (3201, 0), (3201, 3898), (2230, 3898)]
    write_points(path, _gcps(), outline=box)
    assert read_outline(path) == box
    assert len(read_points(path)) == 5  # the outline is a comment to QGIS and to us
    write_points(path, _gcps())
    assert read_outline(path) is None


def test_l_shaped_outline_leaves_out_an_inset():
    # Whole sheet minus a bottom-left inset box (1185 wide, from y 2480 down).
    outline = parse_outline("0,0 3201,0 3201,3898 1185,3898 1185,2480 0,2480")
    assert in_outline(outline, 2000, 3000)  # main panel, beside the inset
    assert in_outline(outline, 500, 1000)  # main panel, above the inset
    assert not in_outline(outline, 776, 2721)  # inside the inset
    assert in_outline(None, 776, 2721)  # no outline = whole sheet


def test_street_names_match_osm_spelling():
    assert osm.norm_street("E. KRAUS") == osm.norm_street("East Krauss Street")
    assert osm.norm_street("S. Broadway") == osm.norm_street("South Broadway")
    assert osm.norm_street("Robert Av") == osm.norm_street("East Robert Avenue")


def test_intersection_merges_divided_road_vertices():
    streets = [
        {"name": "South Broadway", "coords": [(38.5, -90.25), (38.50002, -90.25)]},
        {"name": "Koeln Avenue", "coords": [(38.5, -90.25), (38.50002, -90.25), (38.51, -90.26)]},
    ]
    (point,) = osm.intersection("Koeln Av", "S. Broadway", streets)
    assert point == pytest.approx((38.50001, -90.25))


@pytest.mark.parametrize(
    "words, expected",
    [("top-left", (0.2, 0.2)), ("right block, upper middle", (0.8, 0.2)), ("center", (0.5, 0.5))],
)
def test_position_words(words, expected):
    assert _fraction(words) == expected
    assert _fraction("from the tank pass") is None
