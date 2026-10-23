"""Write web/public/overlays/<area>.json: where each georeferenced map panel's scan lies on
the ground, for the website's old-map layer.

    python scripts/export_overlays.py carondelet      # also run by build_db.py --export

For every panel: the Library of Congress IIIF service, the panel's pixel box on the full-
resolution scan, the ground position of that box's four corners (the panel transforms are
affine, so four corners place the whole image exactly), and the panel outline as fractions
of the box (and, for the rest-of-sheet panel, the other panels' outlines as holes), which
the browser uses to cut the image so panels of one sheet don't overlap.
Free: no image is downloaded here.
"""

import argparse
import json
from pathlib import Path

from georef_sheet import load_panels

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "web" / "public" / "overlays"


def panels(area: str) -> list[dict]:
    out = []
    for folder in sorted((ROOT / "config" / "georef" / area).iterdir()):
        edition = folder.name
        for sid in sorted({p.name.split(".")[0] for p in folder.glob("*.points")}):
            meta = json.loads(
                (ROOT / "data" / "sheets" / area / edition / f"{sid}.json").read_text()
            )
            w, h = meta["width"] / 2, meta["height"] / 2  # outlines are on the 50% image
            scale = meta["width"] / w
            sheet = load_panels(area, edition, sid)
            for pid, outline, t in sheet:
                ring = outline or [(0, 0), (w, 0), (w, h), (0, h)]
                x0, y0 = min(x for x, _ in ring), min(y for _, y in ring)
                x1, y1 = max(x for x, _ in ring), max(y for _, y in ring)
                corners = [t.to_latlon(x, y) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
                out.append(
                    {
                        "id": pid,
                        "year": edition,
                        "service": meta["service"],
                        # x, y, w, h on the full-resolution scan
                        "region": [round(v * scale) for v in (x0, y0, x1 - x0, y1 - y0)],
                        # top-left, top-right, bottom-right, bottom-left as [lon, lat]
                        "corners": [[round(lon, 7), round(lat, 7)] for lat, lon in corners],
                        "clip": [
                            [round((x - x0) / (x1 - x0), 4), round((y - y0) / (y1 - y0), 4)]
                            for x, y in ring
                        ],
                        # A panel without an outline is the rest of the sheet: cut out the
                        # outlined panels, which have their own transforms.
                        "holes": [
                            [[round(x / w, 4), round(y / h, 4)] for x, y in other]
                            for _, other, _ in sheet
                            if outline is None and other
                        ],
                    }
                )
    return out


def write(area: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{area}.json"
    path.write_text(
        json.dumps({"area": area, "panels": panels(area)}, separators=(",", ":")) + "\n"
    )
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("area")
    path = write(parser.parse_args().area)
    data = json.loads(path.read_text())
    print(
        f"{len(data['panels'])} panels -> {path.relative_to(ROOT)} ({path.stat().st_size // 1000} KB)"
    )


if __name__ == "__main__":
    main()
