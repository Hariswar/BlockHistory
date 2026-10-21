import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_accuracy as C


def _m(found=10, sites=12, extra=1, shown=("1|A|1|1",), over=()):
    return {
        "rates": {"sites found": [found, sites]},
        "errors": {"tanks on sites with none": extra, "stale corrections": 0},
        "georef": {"over limit": list(over)},
        "shown": list(shown),
    }


def test_same_scores_pass():
    assert C.compare({"1938": _m()}, {"1938": _m()}) == []


def test_drops_new_listings_and_bad_georef_fail():
    base = {"1938": _m()}
    assert "fell" in C.compare({"1938": _m(found=9)}, base)[0]  # 75% vs 83%
    assert "rose" in C.compare({"1938": _m(extra=2)}, base)[0]
    assert "new since" in C.compare({"1938": _m(shown=("1|A|1|1", "1|CONC|2|2"))}, base)[0]
    assert "georeferencing" in C.compare({"1938": _m(over=["s 9.0 m"])}, base)[0]


def test_a_tiny_dip_within_tolerance_passes():
    base = {"1938": _m(found=100, sites=119)}
    assert C.compare({"1938": _m(found=100, sites=120)}, base) == []  # 84.0% vs 84.03%
