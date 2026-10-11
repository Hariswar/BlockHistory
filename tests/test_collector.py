import itertools
import json

from PIL import Image

from blockhistory.collector import loc
from blockhistory.collector.tiling import _starts, tile_sheet

IIIF = "https://tile.loc.gov/image-services/iiif"
SERVICE = "service:gmd:gmd416m:g4164m:g4164rm:g4164rm_g048491948:04849_1948-0001a"
ITEM_JSON = {
    "item": {"date": "1948-06"},
    "resources": [
        {
            "files": [
                [
                    {
                        "mimetype": "image/jpeg",
                        "url": f"{IIIF}/{SERVICE}/full/pct:12.5/0/default.jpg",
                    },
                    {
                        "mimetype": "image/jp2",
                        "url": "https://x/04849_1948-0001a.jp2",
                        "width": 6450,
                        "height": 7650,
                    },
                ]
            ]
        }
    ],
}


def test_list_sheets_parses_item(monkeypatch):
    monkeypatch.setattr(loc, "_get_json", lambda url, params=None: ITEM_JSON)
    [sheet] = loc.list_sheets("sanborn04849_009")
    assert sheet.sheet_id == "04849_1948-0001a"
    assert sheet.sheet_number == 1
    assert sheet.edition_date == "1948-06"
    assert sheet.image_url(50) == f"{IIIF}/{SERVICE}/full/pct:50/0/default.jpg"
    assert sheet.image_url(100).endswith("/full/full/0/default.jpg")


def test_starts_cover_with_overlap():
    starts = _starts(3825, 1024, 896)
    assert starts[0] == 0 and starts[-1] == 3825 - 1024
    assert all(b - a <= 896 for a, b in itertools.pairwise(starts))
    assert _starts(500, 1024, 896) == [0]


def test_tile_sheet_writes_index(tmp_path):
    img = tmp_path / "sheet.jpg"
    Image.new("RGB", (2000, 1500), "white").save(img)
    paths = tile_sheet(img, tmp_path / "tiles")
    index = json.loads((tmp_path / "tiles" / "tiles.json").read_text())
    assert len(paths) == len(index["tiles"]) == 6  # 3 cols x 2 rows
    assert index["sheet_size"] == [2000, 1500]
    assert all(Image.open(p).size == (1024, 1024) for p in paths)
