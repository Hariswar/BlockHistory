"""Free first pass, part 1: Tesseract OCR on a map tile.

Sanborn labels run in every direction (along the building's long side, up streets), so the
tile is read at 0, 90 and 270 degrees and the words are pooled. Tesseract reads printed
labels like "DRY CLEANING" well and misses hand-lettered or faded ones; those tiles go on
to the vision model.

Needs the `tesseract` binary (brew install tesseract).
"""

from __future__ import annotations

import csv
import io
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

ROTATIONS = (0, 90, 270)
MIN_CONFIDENCE = 60  # Tesseract's 0-100 word confidence; below this is mostly map linework
# Map lettering is ~10 px tall in a 50%-scale tile; Tesseract wants ~30 px. Upscaling 3x and
# keeping only dark ink (dropping the pink/yellow/blue fills) took a test tile from
# 3 words (all noise) to ~7 real ones (WHOL., METAL, WALLS, DECK, PILASTD...).
UPSCALE = 3
INK_THRESHOLD = 120  # grayscale 0-255; darker pixels are kept as text


def _prepare(tile_path: Path) -> Image.Image:
    gray = Image.open(tile_path).convert("L")
    big = gray.resize((gray.width * UPSCALE, gray.height * UPSCALE), Image.Resampling.LANCZOS)
    return big.point(lambda p: 255 if p > INK_THRESHOLD else 0)


def _tesseract_tsv(image: Image.Image) -> list[dict]:
    with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
        image.save(tmp.name)
        # psm 11 = sparse text: find as much text as possible in no particular order,
        # which suits labels scattered over a drawing.
        out = subprocess.run(
            ["tesseract", tmp.name, "stdout", "--psm", "11", "tsv"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    return list(csv.DictReader(io.StringIO(out), delimiter="\t", quoting=csv.QUOTE_NONE))


def read_tile_ocr(tile_path: Path, min_confidence: int = MIN_CONFIDENCE) -> list[dict]:
    """Words found in the tile: [{text, confidence, rotation}], highest confidence first."""
    if shutil.which("tesseract") is None:
        raise RuntimeError("tesseract not found; install it with `brew install tesseract`")
    base = _prepare(tile_path)
    best: dict[str, dict] = {}
    for rotation in ROTATIONS:
        # PIL rotates counter-clockwise, so 90 makes text that runs upward read left-to-right.
        image = base.rotate(rotation, expand=True) if rotation else base
        for row in _tesseract_tsv(image):
            text = (row.get("text") or "").strip()
            conf = float(row.get("conf") or -1)
            # Short fragments are mostly linework read as letters ("AE", "PH"). Keep words
            # with 3+ letters; single-letter use codes (D, S, A) are left to the vision model.
            if conf < min_confidence or sum(c.isalpha() for c in text) < 3:
                continue
            key = text.upper()
            if key not in best or conf > best[key]["confidence"]:
                best[key] = {"text": text, "confidence": round(conf), "rotation": rotation}
    return sorted(best.values(), key=lambda w: -w["confidence"])


def read_tile_boxes(tile_path: Path, min_confidence: int = MIN_CONFIDENCE) -> list[dict]:
    """Like read_tile_ocr, but every word with its box in tile pixels: [{text, confidence,
    x, y, w, h}]. Boxes from the rotated reads are turned back to the tile's orientation."""
    if shutil.which("tesseract") is None:
        raise RuntimeError("tesseract not found; install it with `brew install tesseract`")
    base = _prepare(tile_path)
    bw, bh = base.size
    words = []
    for rotation in ROTATIONS:
        image = base.rotate(rotation, expand=True) if rotation else base
        for row in _tesseract_tsv(image):
            text = (row.get("text") or "").strip()
            conf = float(row.get("conf") or -1)
            if conf < min_confidence or sum(c.isalpha() for c in text) < 3:
                continue
            left, top = int(row["left"]), int(row["top"])
            w, h = int(row["width"]), int(row["height"])
            # Map the box's corners back: PIL's rotate(90) sends (x, y) to (y, W - x).
            if rotation == 90:
                x0, y0, x1, y1 = bw - (top + h), left, bw - top, left + w
            elif rotation == 270:
                x0, y0, x1, y1 = top, bh - (left + w), top + h, bh - left
            else:
                x0, y0, x1, y1 = left, top, left + w, top + h
            words.append(
                {
                    "text": text,
                    "confidence": round(conf),
                    "x": x0 / UPSCALE,
                    "y": y0 / UPSCALE,
                    "w": (x1 - x0) / UPSCALE,
                    "h": (y1 - y0) / UPSCALE,
                }
            )
    return words
