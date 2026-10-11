"""Cut a sheet image into overlapping square tiles small enough for a vision model.

Overlap keeps labels that straddle a tile edge fully visible in at least one tile;
the reader dedupes by position later.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image

# Sanborn sheets are ~6450x7650 at full res. Our default 50% download is ~3225x3825,
# which gives a 4x4 grid of 1024px tiles: big enough to read labels, small enough
# that the vision model doesn't downscale them.
TILE_SIZE = 1024
OVERLAP = 128


def _starts(length: int, size: int, step: int) -> list[int]:
    """Fewest evenly spaced offsets that cover `length` with at least size-step overlap."""
    if length <= size:
        return [0]
    n = math.ceil((length - size) / step) + 1
    return [round(i * (length - size) / (n - 1)) for i in range(n)]


def tile_sheet(
    image_path: Path, out_dir: Path, size: int = TILE_SIZE, overlap: int = OVERLAP
) -> list[Path]:
    """Write tiles as <sheet_id>_r<row>_c<col>.jpg plus a tiles.json index of pixel offsets."""
    out_dir.mkdir(parents=True, exist_ok=True)
    sheet_id = image_path.stem
    step = size - overlap
    paths, index = [], []
    with Image.open(image_path) as im:
        w, h = im.size
        for r, y in enumerate(_starts(h, size, step)):
            for c, x in enumerate(_starts(w, size, step)):
                path = out_dir / f"{sheet_id}_r{r}_c{c}.jpg"
                im.crop((x, y, min(x + size, w), min(y + size, h))).save(path, quality=90)
                paths.append(path)
                index.append({"tile": path.name, "row": r, "col": c, "x": x, "y": y})
    (out_dir / "tiles.json").write_text(
        json.dumps({"sheet_id": sheet_id, "sheet_size": [w, h], "tiles": index}, indent=2) + "\n"
    )
    return paths
