# Running the Map Reader

How to turn downloaded Sanborn sheets into a spot-checkable list of findings. All commands run from the project root with the virtualenv's Python.

## 1. Get the sheets (free)
```
.venv/bin/python scripts/download_sheet.py carondelet --edition 1938
.venv/bin/python scripts/tile_sheet.py data/sheets/carondelet/1938/*-00*.jpg
```
Each sheet becomes 20 overlapping 1024 px tiles under `data/tiles/carondelet/1938/<sheet_id>/`.

## 2. Read the tiles with Haiku (paid, half price)
```
.venv/bin/python scripts/run_batch.py submit carondelet 1938 50 53 57 --dry-run   # estimate only
.venv/bin/python scripts/run_batch.py submit carondelet 1938 50 53 57
.venv/bin/python scripts/run_batch.py collect <batch_id> --wait
```
- Tiles already read are skipped, so resubmitting never pays twice.
- `submit` refuses a batch that would push this month past `BLOCKHISTORY_MONTHLY_CAP_USD`.
- About $0.0004 per tile at batch price (prompt v1, low effort): ~$0.009 per sheet (measured on 10 sheets).
- Results land in `data/cache/map_reader/`, the same cache `scripts/read_tile.py` uses for one-off tiles.

## 2b. Gas-tank second pass (batch, after step 2 is collected)
```
.venv/bin/python scripts/run_batch.py submit carondelet 1938 50 53 57 --tanks
.venv/bin/python scripts/run_batch.py collect <batch_id> --wait
```
- Picks tiles with a fuel or vehicle finding (about 1 in 4), downloads them at full resolution into `data/tiles_hires/`, and counts gas-tank circles in 4 crops per tile (~$0.0002 per crop).
- `--dry-run` prints the estimate without downloading.
- Steps 3 and 5 use the counts automatically when they are cached.

## 3. Merge sheets and write spot-check lists (free)
```
.venv/bin/python scripts/sheet_report.py carondelet 1938 50 53 57
```
For each sheet:
- `data/results/carondelet/1938/<sheet_id>.json`: merged findings (overlap duplicates joined, relevance, Tesseract cross-check).
- `evals/spotcheck/<sheet_id>.md`: a checklist, high-relevance findings first. If the sheet has hand labels, it also shows which labels and gas-tank sites were found.

A checklist you've started ticking is never overwritten; a rerun writes `<sheet_id>.new.md` instead.

## 4. Spot-check
Open the checklist next to the sheet image and tick **ok** or **wrong** for each row, starting with high relevance. Note anything the reader missed under "Notes".

## 5. Score accuracy (free)
```
.venv/bin/python scripts/evaluate.py carondelet 1938
```
Scores every sheet that has both a label file in `evals/labels/` and read tiles, using only the cache. Writes `evals/reports/<date>-carondelet-1938.md` (and `.json`):
- **Recall:** hand-labeled sites the reader found. A sheet with four filling stations needs four filling-station findings; street numbers decide which is which (one wrong digit still counts as the same number).
- **Precision:** findings rated high or medium that are a labeled site, or a named part of one (a CUPOLA of a labeled foundry). Duplicate reads of one site are counted separately.
- **Gas tanks:** sites where a tank landed on the right site, exact counts, and tanks put on sites with none.
- **Tesseract baseline:** labeled sites whose words OCR saw anywhere on the sheet (free).
- **Spot-check:** share of ticked high rows marked ok.

Add `--no-tank-pass` to score the first pass alone (report name ends in `-first-pass`).

Human-verified and draft label files are reported separately. A draft becomes verified when you check it and set `verification.status` to `human_verified`.

## 6. Georeference sheets and place findings (free, except the point pass)
```
# where each flagged finding is on its tile (~$0.0001 per tile, batch)
.venv/bin/python scripts/run_batch.py submit carondelet 1938 47 56 --points
.venv/bin/python scripts/run_batch.py collect <batch_id> --wait

# control points: street intersections on the 50% sheet image, located today in OpenStreetMap
.venv/bin/python scripts/georef_sheet.py gcps carondelet 1938 56 "Robert Av/Minnesota Av@467,325" ...
.venv/bin/python scripts/georef_sheet.py fit carondelet 1938 56        # error per point, in meters
.venv/bin/python scripts/georef_sheet.py locate carondelet 1938 47 56  # -> data/results/.../<sheet>.geojson
```
- Control points are saved in `config/georef/<area>/<edition>/<sheet>.points`, QGIS georeferencer format: open the sheet JPEG in QGIS's Georeferencer, load the file, add or move points, save. Commit these files; they are hand-checked data.
- Pick 6+ intersections spread over the sheet. `fit` prints each point's leave-one-out error (the transform refit without it); a point over ~8 m is probably mis-clicked or the street moved.
- A finding's location comes from the point pass when available, then a Tesseract word box, then the reader's position words, then the tile center. The GeoJSON records which, with a rough uncertainty in meters.
- Street names are matched to OpenStreetMap after dropping directions and suffixes; Sanborn spellings that differ go in `ALIASES` in `blockhistory/georef/osm.py` (KRAUS -> Krauss).
- **Reading a corner:** the street's center is the midpoint between the block edges on either side; the water-main lines (W.P.) run near the center and help on blank corners. Check every point on a zoomed crop: the automatic edge finder picks the wrong edge on about 1 corner in 3, especially where streets slope across the sheet. Skip corners where a street is "not opened", runs through a blank area, or has been realigned since 1938 (today's Idaho north of Tesson, Polk north of Courtois, Reilly at Catalan).
- **A street that jogs** has two OSM crossings with the same cross street (Fillmore at Michigan, Haven at Virginia). `gcps` refuses those; write the point with the right vertex (see sheets 23 and 44).
- **Two panels on one sheet** (an inset, or a strip from another part of town): give each panel its own file with `--panel <name> --outline ...`; a finding uses the panel whose outline contains it. A main panel can also take an outline that leaves out an inset not done yet (sheet 58); findings in no panel are left off the map.
- **`--similarity`** fits shift, one scale and rotation (no shear). Use it when every usable crossing is on one street (sheet 50's two strips along S. Broadway) or there are only 3–4 points in one corner (sheet 74). The scale it prints should match the sheet's printed scale: 0.333 ft/px at 50 ft to the inch, 0.667 at 100 ft.
- **Check far from the points** when a panel's points are bunched or in a line: compare a feature two sheets share (sheets 50 and 53 put the same water-main end 0.2 m apart), or one that hasn't moved (the River des Peres channel on sheet 74).

## 6b. A later edition of the same volume (free)
```
.venv/bin/python scripts/run_batch.py submit carondelet 1950 <sheets>          # first pass (~$0.0008/tile)
.venv/bin/python scripts/run_batch.py submit carondelet 1950 <sheets> --tanks  # then --points
.venv/bin/python scripts/align_edition.py carondelet 1938 1950 <sheets>        # control points
```
- The 1938–1950 volume is the 1938 plates with paste-over patches, so `align_edition.py` reuses the 1938 control points: it matches each whole scan, then finds each street corner's patch on the later scan. It prints a leave-one-out report like `fit`; a "weak match" kept the whole-sheet prediction (a corner under a paste-over), so look at those sheets.
- Needs OpenCV: `.venv/bin/python -m pip install "opencv-python>=4.9"` (the `vision` extra).
- 1950 has no sheet 11 at the Library of Congress. A batch over ~250 MB is refused; submit sheets in chunks of about 25.
- Paste-overs: the reader sometimes reads old print showing faintly through a patch. Check new findings against the scan and hide those in `config/corrections/<area>-1950.json`.

## 6c. Official records (free)
```
.venv/bin/python scripts/load_records.py      # Missouri DNR tank and cleanup sites -> records table
```
- `blockhistory/records/dnr.py` reads two public layers of the DNR E-START map service (tank facilities, hazardous-waste cleanup sites) for Carondelet and Patch, puts each on its City of St. Louis parcel when the address matches, and words its status plainly. Cached in `data/cache/records/`.
- Run it before `build_db.py --export`; the export carries the records. After a schema change, re-run `schema_postgis.sql` in Supabase first (it adds the `records` table and `records_near()`).

## 7. Build the database (free)
```
.venv/bin/python scripts/build_db.py carondelet 1938 [--export]
.venv/bin/python scripts/search_address.py "7313 S Broadway"
```
- Loads every sheet that has a `.points` file into `data/blockhistory.sqlite`: one row per site (repeat reads within 15 m merged), with relevance, a plain-language explanation, review status from the spot-check ticks (rows ticked **wrong** are kept but never shown), and the sheet's outline on today's map.
- `--export` also writes `data/export/load_postgis_1.sql`, `_2.sql`, ... for Supabase (each under 400 KB: the SQL editor refuses bigger queries).
- Hand fixes in `config/corrections/<area>-<edition>.json` are applied first: `hide` (not on the map, a repeat, a private garage), `set` (`new_label`, `use`, `gasoline_tank_count`, or `sheet_px` to move it) and `add` (a site the reader missed, such as a plant name printed across its buildings). Each entry names the sheet, the label as read and its position (`near`, 50% image pixels), plus a `why`. The build prints any entry that no longer matches.

**Supabase** (the site's database once keys are set):
1. Supabase dashboard → SQL Editor → paste and run `blockhistory/db/schema_postgis.sql` (once; safe to re-run). It turns on PostGIS, creates the tables with read-only row-level security, and the functions `findings_near(at_lat, at_lon, radius_m)`, `sheets_covering(at_lat, at_lon)` and `sheets_list()`.
2. Same place → paste and run `data/export/load_postgis_1.sql`, then `_2`, `_3`, ... in order, each in its own query. Part 1 clears the tables, so always start from part 1 and run every part after each `build_db.py --export`.
3. Project Settings → API → copy the Project URL and the **anon/publishable** key (never the service_role/secret key) into `web/.env.local`, following `web/.env.local.example`. That file is gitignored.
4. Restart `npm run dev`. With both values set the site reads Supabase; with them empty it reads the local SQLite file.

## 8. Run the website locally (free)
```
cd web
npm install        # once
npm run dev        # http://localhost:3000
```
- Reads Supabase when `web/.env.local` has `SUPABASE_URL` and `SUPABASE_ANON_KEY`; otherwise `../data/blockhistory.sqlite` (or `BLOCKHISTORY_DB`) with Node's built-in SQLite (Node 22.13+).
- Addresses go through the US Census geocoder (server side); the base map is OpenFreeMap (no key).
- Links like `http://localhost:3000/?q=7313+S+Broadway` open a search directly.

## Where the code is
| Step | Code |
|---|---|
| Prompt, schema, single-tile reads, cache | `blockhistory/map_reader/extract.py` |
| Batch submit / collect | `blockhistory/map_reader/batch.py` |
| Merge tiles into a sheet, OCR cross-check | `blockhistory/map_reader/sheets.py` |
| Relevance (high / medium / low) | `blockhistory/map_reader/relevance.py` |
| Matching against hand labels | `blockhistory/map_reader/scoring.py` |
| Gas-tank second pass | `blockhistory/map_reader/tanks.py` |
| Point pass (pixel location of each finding) | `blockhistory/map_reader/points.py` |
| Control points, transform, OSM streets, finding locations | `blockhistory/georef/` |
| Georeferencing commands | `scripts/georef_sheet.py` |
| Accuracy report | `scripts/evaluate.py` |
| Database, distance search, PostGIS export | `blockhistory/db/store.py`, `blockhistory/db/schema_postgis.sql` |
| Explanations shown on the site | `blockhistory/explain.py` |
| Website (Next.js + MapLibre) | `web/app/`, `web/components/`, `web/lib/` |
| Spend log and caps | `blockhistory/costs.py` |
