# Labeling Guide

`evals/labels/` holds hand-labeled sheets, the ground truth the map-reading agent is scored against.

- Copy `evals/labels/_template.json` to `evals/labels/<sheet_id>.json`.
- One entry per labeled building footprint. The fields match `Building` in
  `blockhistory/map_reader/extract.py`, so scoring is a direct comparison.
- Copy label text exactly as printed (`DRY CLE`, not `Dry cleaning`); put the expansion in `use`.
- `construction` is one of: brick, brick_veneer, frame, stone, concrete_block, metal, fireproof, unknown.
- Leave `street_number` null unless you can actually read it. Don't guess.
- `position` is the tile that holds the building (`tile r3_c1`); tiles are in `data/tiles/<area>/<edition>/<sheet_id>/`.
- `contamination_relevance` (high / medium / low) follows the use-label table in `docs/sanborn-cheatsheet.md`. It isn't something the model extracts; it's there to weight the eval toward the uses that matter (missing an OIL HO. is worse than missing a cow shed).
- Groups of identical footprints (a row of KILNs) can be one entry with the count in `notes`.
- Use the full-resolution viewer on loc.gov (the `item_url` in the sheet's metadata) to zoom.

Weeks 1–2: get a feel for the data (5 sheets, specific-use labels only). Week 6: the real ground-truth set (3 sheets, every building).

Labeled so far (drafts, need a human check against the loc.gov full-resolution viewer):
- **Carondelet 1938 (study area)**: `04858_12_1938-0050`, `-0053`, `-0057`, `-0062`, `-0074`
- The Hill 1903 (pre-car map style): `04858_10_1903-0009`, `-0014`, `-0015`, `-0020`, `-0044`
- Rolla pilot (small-town car era): `04849_1924-0002`, `04849_1948-0002`
