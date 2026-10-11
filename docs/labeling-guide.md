# Labeling Guide

`evals/labels/` holds hand-labeled sheets, the ground truth the map-reading agent is scored against.

- Copy `evals/labels/_template.json` to `evals/labels/<sheet_id>.json`.
- One entry per labeled building footprint. The fields match `Building` in
  `blockhistory/map_reader/extract.py`, so scoring is a direct comparison.
- Copy label text exactly as printed (`DRY CLE`, not `Dry cleaning`); put the expansion in `use`.
- `construction` is one of: brick, brick_veneer, frame, stone, concrete_block, metal, fireproof, unknown.
- Leave `street_number` null unless you can actually read it. Don't guess.
- Use the full-resolution viewer on loc.gov (the `item_url` in the sheet's metadata) to zoom.

Week 5 is for getting a feel (2 sheets, any depth). Week 6 is the real ground-truth set (3 sheets, every building).
