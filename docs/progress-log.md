# Progress Log

One short entry per week: what got built, what got measured, what's next.

## Week 0: Rolla pilot (Oct 5–10, 2026)
Before the plan moved to St. Louis, the pipeline was built and tested on Rolla, MO (1924, 1933, and 1948 editions: 21 sheets, all downloaded and tiled). What carries over:
- The loc.gov client, downloader, and tiler.
- Two draft label files (`04849_1924-0002`, `04849_1948-0002`, 114 entries). These are car-era maps full of gas tanks, filling stations, and dry cleaners, so they're a useful second map style for the eval set.
- Lessons: the tiny notes ("G.T.S", "SOLVENT TK.") matter more than the big labels, and later editions are paste-ups that mix dates.

## Pilot 2: The Hill, 1903 (Oct 10, 2026)
Before Carondelet, The Hill (Vol. 10) was set up: 19 images downloaded and tiled, 5 sheets annotated (brickworks, clay mines). Dropped because only 1903 is scanned. The config and labels stay as a pre-car map style for the eval set. Tooling built during this pilot carries over: `area_config.py`, the $3/month + $10 project spending caps, retrying downloads, Tesseract and Ollama readers, the Colab notebook.

## Week 1 (Oct 5, 2026): pick the area
**Built**
- Plan revised for **Carondelet, St. Louis** (`docs/plan.md`).
- Confirmed on the LoC: Vol. 12 **1938** (`sanborn04858_022`, 77 images) and **1938–Jun 1950** (`sanborn04858_041`, 78 images) are both scanned. The 1950 scan has no sheet 11.
- Saved every sheet URL for both editions in `config/neighborhoods/carondelet.json`, with each sheet tagged as Carondelet (33), Patch (14) or west of Grand (27), from the 1938 key map.
- 1904 World's Fair test volume saved and downloaded (23 images, 420 tiles).
- Downloaded both Carondelet editions (155 images, ~150 MB) and tiled the 149 map sheets (key maps + sheets 1–74, minus 1950 sheet 11) into **2,980 tiles**. That is far past week 3's "40 sheets downloaded and tiled".

**Checked: does 1916 cover the same area?**
- **No.** In 1916, Vol. 12 was Dutchtown / Gravois / Morgan Ford; only sheets 47–50 touch Carondelet's west edge.
- **But 1908 Vol. 8 does.** Its key map shows riverfront Carondelet from Bates to the River Des Peres. The volume numbers moved between editions, and every 1938 sheet prints its 1908 equivalent ("(54-60-64-68 VOL. 8)" on sheet 50). That's the third map year for Phase 3.

## Week 2 (Oct 12, 2026): learn the maps
**Built**
- Cheat sheet rewritten from the **1938 Vol. 12 key** (`docs/sanborn-cheatsheet.md`): construction colors (C.B., asbestos-clad), the G.T. gasoline-tank symbol, fuel and chemical tank labels, map furniture (block numbers, previous-edition sheet references, old vs. current house numbers), and a contamination-relevance table.
- Annotated 5 Carondelet 1938 sheets (drafts, specific-use labels only, **80 entries, 10 with gas tanks**):

| Sheet | Area | Entries | Highlights |
|---|---|---|---|
| 74 | River Des Peres mouth | 21 | Laclede Gas Light Co. coke & by-products plant: gasometers, 65 coke ovens, tar/benzol/ammonia/naphthalene tanks |
| 50 | Riverfront north of Quincy | 24 | Blast furnace, 2 steel/iron foundries, tin-foil smelting, bulk oil station, 3 filling stations, coal yards |
| 53 | S. Broadway, Quincy–Robert | 16 | Filling station + battery service, tin shops, oil house, bulk oil station (above-ground tanks) |
| 57 | Patch, south of Robert | 11 | 2 filling stations (3 tanks each), 2 foundries, Lowell Bleachery & Dye Works, flooded quarry |
| 62 | Patch residential | 8 | Mostly houses; Chester Iron & Foundry, undertaker, tin shop |

**What annotating taught me**
- Carondelet 1938 has exactly what the project is for: **filling stations with G.T. tanks on Broadway**, two **bulk oil stations** by the tracks, and heavy industry (a coke/gas plant, foundries, smelting, dye works) a block from houses.
- The G.T. symbol is tiny (2–3 small circles at the curb). It's the most important thing to read and the easiest to miss.
- Each sheet says which 1908 Vol. 8 sheets cover the same ground, which makes linking map years much easier.
- North rotates sheet to sheet, and scales change (50 vs 100 ft per inch).

**Measured (Day 7, Tesseract only, $0)**
| Tile | Hand labels | Tesseract found | Missed |
|---|---|---|---|
| 0057 r1_c0 (2 filling stations, auto sales, coal) | 3 | 3 | — |
| 0053 r2_c1 (filling sta. + battery, tin shop, oil house) | 3 | 1 | TIN SHOP, OIL HO. |
| 0074 r2_c1 (coke plant core) | 10 | 6 | naphthalene, by-products bldg, machine shop, chem. lab |
| 0050 r3_c0 (gasoline storage, coal yard, filling sta.) | 3 | 2 | FILL'G STA. |
| 0050 r3_c2 (bulk oil, ice plant, vinegar, wrecking, foundry) | 5 | 4 | Semi-Steel Casting |
| **Total** | **24** | **16 (67%)** | |

**Day 7 notes: what each got wrong**
- *Tesseract*: much better on 1938 printed lettering than on 1903 hand lettering (16 of 24 vs 4 of 21). But it **never reports a G.T. symbol**, so it can't count gas tanks. It misses short labels (TIN SHOP, OIL HO.) and produces junk words from linework ("Fis", "LAT", "ayl"). A "found" match on a word like STA can be accidental, so the scoring is generous.
- *Vision model (Qwen2.5-VL 7B on a free Colab T4, Oct 12)*, 3 tiles from sheet 50:

| Tile | Hand labels | Tesseract found | Vision found | Gas-tank sites (hand / vision) |
|---|---|---|---|---|
| r3_c2 (bulk oil sta., ice plant, vinegar, wrecking, foundry) | 5 | 4 | 3 | 2 / 1 |
| r3_c0 (filling sta., gasoline storage, coal yard) | 3 | 2 | 1 | 1 / 0 |
| r1_c2 (oil house, locomotive house) | 2 | 0 | 0 | 0 / 0 |
| **Total** | **10** | **6** | **3** | **3 / 1** |

  What it got wrong:
  - **Missed every high-priority item**: the BULK OIL STA., both FILL'G STA., GASOL. & ALCOHOL STGE., and the OIL HO. It found only the big printed company names (ice plant, vinegar works, wrecking co., coal yard).
  - **Gas tanks**: 3 sites with 7 G.T. symbols on these tiles; it marked a tank on 1 building, and not one of the right ones.
  - **Repetition loop**: every reply hit the 4,096-token output limit. It listed the same buildings again and again (33 and 42 exact repeats on two tiles) instead of moving on.
  - **Wrong addresses**: it used **block numbers as street numbers** (3007, 3009, 2947, 2977 are city blocks) and put buildings on the wrong street.
  - **Junk entries**: a street name as a building ("ELOUGHBOROUGH AV."), bare use codes ("S", "2 P"), and a block number as a label ("2977").
  - **Slow**: 145–163 s per tile, partly because it kept generating repeats. At that speed, Carondelet's 2,980 tiles would take ~130 GPU hours, far beyond Colab's free sessions.
  - Scoring note: the first output said it "found" SEMI-STEEL CASTING; that was a matcher bug (the generic word "MFG" matched). Fixed; the table above is the corrected count.

  **Takeaway for week 4:** as set up, Qwen2.5-VL 7B is worse than Tesseract and can't be the free first pass for tanks.

- *Claude Haiku 5.5 (low effort, Oct 12)*, same 3 tiles, **$0.0035 total**:

| | Tesseract | Qwen2.5-VL 7B | **Haiku 5.5** |
|---|---|---|---|
| Hand labels found (of 10) | 6 | 3 | **9** |
| Gas-tank sites (of 3) | 0 | 0 (1 wrong) | **3** (+1 double count) |
| Cost | $0 | $0 | ~$0.001/tile |
| Time per tile | ~3 s | ~150 s | ~8 s |

  Right: both FILL'G STA. and the BULK OIL STA. with tanks, OIL HO., GASOL. & ALCOHOL STGE., LOCOMOTIVE HO., ice plant, vinegar works, wrecking co. It flagged 2947/2977 as lot numbers, not addresses.
  Wrong:
  - Missed SEMI-STEEL CASTING CO. (high priority).
  - Street names: gave S. Broadway house numbers to side streets ("6226 E. Bowen" is 6226 S. Broadway).
  - Marked a G.T. on the store next to a filling station (double count).
  - Misread abbreviations: FR. FOUND. as "frame foundry" (frame foundation), BR. CORE OVEN as "brass" (brick).
  - Listed a construction note ("CONC FL STEEL RF") as a building.
  - Lists every plain D/S/F too, which the hand labels exclude; filter before scoring.

  **Decision:** Haiku is the main reader. Both Carondelet editions (2,980 tiles) would cost ~$0.86 at batch prices. Week 4: fix the prompt (address = street the number faces; G.T. belongs to the building it's drawn beside; expand FR. = frame, BR. = brick; skip construction notes), try medium effort on the same tiles, then run 10 sheets through the Batch API.

**Spent:** $0.

**Still to do (you)**
- [ ] Apply for the GitHub Student Developer Pack and other free credits (Day 1).
- [x] Push the repo to GitHub, run the Colab notebook, and write the vision model's mistakes above.
- [ ] Spot-check the 5 Carondelet label drafts on the loc.gov full-resolution viewer; change `labeled_by` to your name.

**Next (week 3+)**
- Week 3 (download + tiling) is done. Start week 4: route tiles Tesseract → free vision model → Haiku only when unsure, and ask the vision model about G.T. symbols explicitly.

## Week 3–4 start (Oct 12, 2026): map-reading agent v1
- Prompt v1 (`blockhistory/map_reader/extract.py`): abbreviations, gas-tank placement and counts (`gasoline_tank_count`), block numbers aren't addresses, skip plain D/S/F/A.
- `scripts/compare_models.py` now scores gas tanks only when they're on the right building, reports extra (misplaced) tanks, and lists misses with `-v`. Shared matching rules in `blockhistory/map_reader/scoring.py`.

| Same 3 tiles, Haiku 5.5 | Labels | Tank sites | Extra tanks | $/tile |
|---|---|---|---|---|
| Prompt v0, low | 9/10 | 2/3 | 1 | $0.0012 |
| **Prompt v1, low** | **9/10** | **2/3** | **0** | **$0.0012** |
| Prompt v1, medium | 8/10 | 1/3 | 0 | $0.0022 |

- Still wrong: street names (side streets for S. Broadway numbers), the bulk oil station's tank count (2 vs 4), Semi-Steel Casting Co. missed. Streets will come from georeferencing (weeks 8–9).
- **Spent so far: ~$0.01.**
- Next: run 10 full sheets through the Batch API (~$0.10) and spot-check them (week 4–5 "done when").

## Weeks 4–5 (Oct 12, 2026): map-reading agent v1 on 10 sheets
**Built**
- `scripts/run_batch.py` + `blockhistory/map_reader/batch.py`: send tiles through the Batch API (half price), skip tiles already read, refuse batches that would pass the monthly cap, collect results into the same cache as single reads.
- `blockhistory/map_reader/sheets.py`: merge a sheet's 20 tiles into one list (joins duplicates from tile overlaps) with a free Tesseract cross-check per finding.
- `blockhistory/map_reader/relevance.py`: sorts findings high / medium / low from the cheat-sheet table (agrees with all 41 high-relevance hand labels).
- `scripts/sheet_report.py`: writes `evals/spotcheck/<sheet>.md` checklists, high relevance first, with a comparison to hand labels where they exist.
- How to run it all: `docs/pipeline.md`. Tests: 19, all passing.

**Ran:** Carondelet 1938 sheets 47, 49, 50, 53, 56, 57, 61, 62, 67, 74 (200 tiles) with Haiku 5.5, prompt v1, low effort. One batch, all 197 new tiles succeeded. **Cost $0.086** (~$0.0004/tile, ~$0.009/sheet). Project total: **$0.096**.

| Sheet | Findings | High | Hand labels found | Gas-tank sites |
|---|---|---|---|---|
| 50 riverfront | 137 | 22 | 26/27 | 5/7 |
| 53 Broadway | 67 | 4 | 16/17 | 1/1 |
| 57 Patch | 54 | 22 | 11/12 | 2/2 |
| 62 Patch residential | 33 | 7 | 4/5 | — |
| 74 coke plant | 57 | 17 | 26/27 | — |
| **Labeled total** | | | **83/88** | **8/10** |
| 47, 49, 56, 61, 67 (no hand labels) | 189 | 18 | — | — |

- Missed hand labels: PAINT'G, BLDG SUPPLY W. HO., STEEL STGE., POND (WATER FILLED QUARRY), STEEL PROCESSING TK. / AERATING TOWER.
- Missed tank sites: both single tanks at industrial yards (coal dealers' equipment yard, Semi-Steel Casting). **Every filling station and the bulk oil station got tanks.**
- New finds on unlabeled sheets: filling stations with 3 tanks on 47 and 61, ~10 auto-repair garages, an auto dealer with a tank on 56, a **dry cleaner** on 67 (520 E. Marceau; *wrong, see weeks 6–7*), paint spraying & benzol washing on 47.
- Caveats: "found" is word matching anywhere on the sheet, so it's generous, and there's no precision number yet (how many findings are wrong). That's what the spot-check and the week 7 eval measure.
- Fixed during the run: relevance marked "FR. FOUND." (frame on a foundation) as a foundry; iron works added as medium.

**Spot-check (you):** tick the checklists in `evals/spotcheck/`, high-relevance rows first. That is the "done when" for weeks 4–5.

## Weeks 6–7 (Oct 13, 2026): ground truth and first accuracy score
**Spot-check (weeks 4–5 "done when")**
- All 91 high-relevance rows on the 10 sheets are ticked: **83 ok, 8 wrong (91%)**. You checked sheet 47; I did a first pass on the other 9 by reading the map images, and ticked sheets 50, 53, 57, 62 and 74 against your checked labels. Notes are under each checklist.
- The 8 wrong: two labels cut by a tile edge (AUTO, AUTO R...), two misreads (S. CL. 2 is a construction note; IRNE REP. is FURNE REP., furniture), one company name read as a building (G. C. CO.), M. CARAG. (really M. CARPR., a carpenter), and **two made-up businesses**: AUTO TO REPAIRS on 57 and the **DRY CLEANING at 520 E Marceau on 67**, which I reported last week as a real find. 520 is a flat.

**Week 6: ground truth**
- New label drafts for sheets **47, 49, 56, 61 and 67** (30 sites, 11 gas tanks), same scope and format as your five. Drafted with AI help from the full-resolution images; **they need your check** before they count as hand labels (set `verification.status` to `human_verified`). With them, 10 sheets have labels (118 sites).
- Sheet 50's coal dealers' yard label now also names GASOL. ENG. and A. 18 TRUCKS (already in its notes). Your sheet 50 labels were missing a blacksmith (BL. SM.) at 107–111 E Soper; added with your OK.

**Week 7: first accuracy score** (`scripts/evaluate.py`, report in `evals/reports/2026-10-13-carondelet-1938.md`, $0 to run)

| On your 5 checked sheets (100 tiles) | Haiku 5.5, low, batch | Tesseract (free) |
|---|---|---|
| Recall: labeled sites found | 73/88 (83%) | 57/88 (65%) |
| Recall: high-relevance sites | 34/41 (83%) | — |
| Precision: high/medium flags that are a labeled site | 106/121 (88%) | — |
| Gas-tank sites with a tank on the right site | 6/10 (60%) | 0/10 |
| Gas-tank sites with the exact count | 4/10 (40%) | — |
| Gas tanks on those sites: map vs read | 25 vs 12 | — |
| Cost | $0.0092/sheet | $0 |

On the 5 draft sheets: recall 28/30, precision 36/41, tank sites 5/5 with exact counts (to be confirmed when you check the drafts). Qwen2.5-VL 7B (Day 7, 3 tiles only): 3/10 labels, 0/3 tank sites.

- **Gas tanks are the weak spot.** Names and uses are mostly right, but on the checked sheets the reader saw about half the drawn tanks, and missed all tanks at 3 of 10 tank sites (6532 and 6930 filling stations, Semi-Steel). This is below the ~80% revisit line set on Oct 12.
- Missed on purpose-heavy sheets: the coke plant's steel tank fields (74), the Johnston Tin Foil plant (50), the shipyard and contractor's yard (67).
- About 1 in 5 flags is a second read of a site already found (38 in all), mostly the same building seen from two tiles.

**Fixed along the way** (tests: 39, all passing)
- Merging: entries from the same tile are never joined (sheet 53's two tin shops), and tiles must share an edge, not just a corner (sheet 57's two coal yards). A numbered and an unnumbered read on edge-sharing tiles are now joined (sheets 49, 56, 61 had them twice).
- Relevance: "footprint"/"printed" no longer count as PRINT; "3 CARS"-style auto-house notes and private car garages are low; Sulphur & Chem. Co. is high; shipyards and contractor's yards are medium.

**Next:** check the 5 label drafts (and untick any first-pass tick you disagree with), then decide how to fix tank counts before reading the whole volume (see decision log).

## Week 7, continued (Oct 13, 2026): gas-tank second pass
**Built:** `blockhistory/map_reader/tanks.py` + `run_batch.py submit ... --tanks`. Tiles where the first pass found a fuel or vehicle site (50 of 200) are re-downloaded at full resolution (twice our tile detail; tank circles go from ~6 px to ~12 px), cut into 4 crops, and Haiku answers one question per crop: which gasoline-tank groups are here, how many circles, which building they serve. The counts go onto the first pass's findings; tanks naming a business the first pass missed become new findings.

**Ran:** 200 crops, one batch, **$0.038**. Project total **$0.134**.

| Your 5 checked sheets | First pass | + tank pass |
|---|---|---|
| Tank sites with a tank on the right site | 6/10 | **9/10** |
| Exact tank count | 4/10 | **7/10** |
| Tanks read on those sites (map: 25) | 12 | 25 |
| Tanks put on a site with none | 1 | 4 |
| Recall / precision (names) | 83% / 88% | 84% / 88% |

- The 25 of 25 hides two errors that cancel: the bulk oil station got 6 (map 4, it shares a lot and roof with the 6800 filling station) and the 6930 station got 2 (map 3). Semi-Steel's single tank is still missed.
- Remaining wrong tanks: 3 at USED AUTO SALES (the 7432 station's tanks, given to the next lot in one crop), 2 at a FOUNDRY, 1 each at GASOL. & ALCOHOL STGE. and the electric substation.
- Draft sheets: still 5/5 tank sites with exact counts.
- Cost on a whole edition: ~25% of tiles x 4 crops ≈ $0.0002 per crop, about $0.30 for 1938.
- Tests: 41, all passing.

**Label drafts verified (Oct 13).** You checked the drafts for sheets 47, 49, 56, 61 and 67; I then re-read every block of each sheet in 9 overlapping sections and confirmed every G.T. count on full-resolution crops. No in-scope site was missing and all 11 tank counts held. Fixes, all on 67: the sulphur plant's ORE W. HO. added; the grain elevator's BOILER HO. is in the inset (the 1930 building on the main map is storage); Eagle Iron Works is iron-clad, not fire-proof; the molasses tank moved to out-of-scope (different block). Construction and stories filled in for every entry. All 10 label files are now `human_verified` (118 sites, 36 gas tanks).

| All 10 verified sheets (200 tiles) | Haiku + tank pass | Tesseract |
|---|---|---|
| Recall: labeled sites | 102/118 (86%) | 67/118 (57%) |
| Recall: high-relevance | 47/53 (89%) | — |
| Precision: high/medium flags | 145/165 (88%) | — |
| Tank sites with a tank on the right site | 14/15 (93%) | 0/15 |
| Exact tank count | 12/15 (80%) | — |
| Tanks put on a site with none | 6 findings | — |
| Cost | $0.012/sheet | $0 |

One of the 6 wrong tanks is invented: the tank pass reported a G.T. at the 217 Upton auto repair (sheet 56); the full-resolution crop shows none.

## Weeks 8–9 start (Oct 13, 2026): whole 1938 volume read; first sheets georeferenced
**Whole volume (sheets 1–74, 1,480 tiles).** First pass $0.43, tank pass on the 243 tiles with a fuel or vehicle finding (972 full-resolution crops) $0.14, point pass on 338 tiles $0.04. No failures. **Project total $0.75 of $10.**
- Findings: 307 high, 188 medium, 1,763 low. 118 sites with gasoline tanks (285 tanks). Among the high/medium: ~94 filling-station reads, ~113 auto repair/garage/sales, 26 foundry, 17 dyeing/cleaning, 9 bulk oil/oil house. These are raw reads (about 1 in 8 flags is wrong and about 1 in 5 is a repeat read of a site, per the week 7 eval), not checked yet.

**Georeferencing** (`blockhistory/georef/`, `scripts/georef_sheet.py`)
- Control points are street intersections: found on the sheet by measuring the two block-edge lines of each street and taking the midpoint (checked by eye on a contact sheet), and located today from OpenStreetMap. Saved as QGIS `.points` files in `config/georef/`.
- Affine fit per sheet. Leave-one-out error: **sheet 56 median 1.3 m (worst 2.8 m), sheet 47 median 2.8 m (worst 7.5 m)**, 12 points each. Scale comes out at 0.333 ft per pixel, as 50 ft to the inch at 150 dpi should.
- **Point pass** (`points.py`): the reader's position words were up to half a tile off (27–55 m). Asking Haiku for each flagged building's pixel center put 13 of 15 checked sites within 4 m of where I measured them on the map (median 1.5 m, worst 16 m: a coal yard located at its shed).
- The Census geocoder turned out too rough to check against (46 m and 84 m off for two buildings I measured), so accuracy is checked against hand-measured map positions instead.
- Output: `data/results/carondelet/1938/<sheet>.geojson` with lat/lon, how each point was found, and an uncertainty in meters. Done for 47 and 56.
- Tests: 49, all passing.

**Next:** control points for the other 72 sheets. The 2 done by hand-checked measurement took a few minutes each; the plan is to automate it: predict where each intersection should be from already-georeferenced neighbors and the key map, refine with the edge measurement, and only review points whose error is over ~8 m.

## Weeks 10–11 (Oct 13–14, 2026): database and website v1
**Week 10: database and the 100 m query** (`blockhistory/db/`, `scripts/build_db.py`, `scripts/search_address.py`)
- Local SQLite for now (no Supabase account yet), with the same tables in `schema_postgis.sql` and a SQL export, so moving to Supabase is a paste.
- Sheets 47 and 56: 81 sites after merging repeat reads (89 findings before). Spot-check ticks carry over: 7 high sites checked ok, 3 checked wrong (hidden), the rest marked unreviewed.
- Each sheet's outline on today's map is stored, so a search can say "not covered yet" instead of "nothing here".
- **Done when met:** `search_address.py "7313 S Broadway"` returns the auto dealer with gas tanks (44 m) and an auto repair shop (63 m); "6601 S Broadway" returns the filling station (13 m); "4500 Shaw Ave" says no processed map covers it.

**Week 11: website v1, works locally** (`web/`: Next.js 16, MapLibre, OpenFreeMap tiles)
- Search box (Census geocoder, server side), map with the 100 m circle, the processed area outlined and numbered markers, and a list of past uses.
- Every listing follows the safety rules: quotes the label as printed, says what kind of business it was and why it can matter, "historical use, not a test result", a review badge ("checked by a person" / "not yet checked"), the reader's confidence, location precision, a close-up of the original map from the Library of Congress, a link to the sheet, and a "report it" link (GitHub issue).
- Three outcomes are worded differently: findings; covered but nothing flagged ("one year only, not a sign the soil is clean"); not covered yet.
- About & limits page: years covered, how it works, accuracy numbers, not-an-ESA, privacy (no data on residents; searches go to the Census geocoder).
- Checked in Chrome at desktop and phone width, light and dark: no console errors. Works without WebGL (the list still shows). Production build passes. Python tests: 54.

**Known limits:** only 2 sheets are on the map; Census address points can be 30–80 m off (the site says so); explanations come from templates, not the explainer agent planned for month 6.

**Next (week 12):** pick hosting (Vercel free) and the database (Supabase free), launch with the About page, and get the first 25 people to try it. More sheets need control points first.


**Supabase (Oct 14).** Schema and data loaded in the Supabase SQL editor; the site now reads Supabase when `web/.env.local` has the keys. New Supabase projects don't grant table access to the public role, so the schema now grants SELECT only (added to `schema_postgis.sql`). Checked: the four test addresses give the same results as the local file, all 81 sites are readable with the public key, and edits and deletes with it are refused.

## Weeks 8–9 finished (Oct 14, 2026): 17 sheets on the map
Georeferenced the busiest sheets, picked by flagged-site count, the careful way: every corner read by hand on a zoomed, gridded crop (block edges and water mains), then checked with leave-one-out error.

| Sheet | Points | Median error | Notes |
|---|---|---|---|
| 22 | 5 + 6 | 1.6 m / 2.6 m | two panels (Grand–Alaska, Alaska–Alabama) |
| 23 | 7 | 2.0 m | Fillmore jogs at Michigan: both crossings used |
| 24 | 9 | 0.8 m | |
| 44 | 8 | 1.6 m | Haven is two pieces at Virginia today |
| 49 | 12 | 1.5 m | |
| 50 | 6 + 7 | 0.5 m / 0.6 m | two strips along S. Broadway, similarity fit |
| 52 | 12 | 0.9 m | |
| 53 | 8 | 1.3 m | |
| 57 | 10 | 2.1 m | 100 ft to the inch |
| 58 | 7 | 3.4 m | inset left out (see decision log) |
| 59 | 9 | 1.9 m | |
| 60 | 8 | 1.7 m | |
| 62 | 11 | 2.1 m | worst 6.5 m at Steins & Vulcan by the tracks |
| 72 | 10 | 0.9 m | |
| 74 | 3 | 3.6 m | only 3 usable crossings; similarity fit, checked against the River des Peres |
| 47, 56 | 12 each | 2.8 m, 1.3 m | from before |

- **New in the code:** panels (`<sheet>.<panel>.points` with a pixel outline) and a no-shear similarity fit (`#MODEL similarity`). Tests: 57.
- **Checks far from the control points:** sheets 50 and 53 put the same water-main end on E. Quincy 0.2 m apart; sheet 74 puts the River des Peres channel and the rail crossing within ~5–10 m of where the map draws them, 400 m from its points.
- **Against the Census geocoder** on 46 hand-labeled addresses (sheets 49, 50, 53, 57, 62, 74): median 53 m, which is Census's own error. The few 200–990 m gaps were Census placing riverfront addresses that no longer exist, or the checker pairing a label with the wrong finding; none were placement errors.
- **Database:** 805 sites on 17 sheets (19 panel rows); 198 shown (high or medium), of which 72 were checked ok. `data/export/load_postgis.sql` is ready for Supabase (the schema didn't change).
- **Spot-check lists** written for the 9 new sheets without one: 84 high rows to tick.

**Next:** load the new export into Supabase, tick the new sheets' high rows, then launch (week 12).

## Listing cleanup (Oct 14, 2026)
A read-through of all 198 shown listings found three problems, now fixed:
- **Construction notes shown as uses (13 listings).** "(ASB. CL.)" (asbestos siding) was read as "asbestos cleaning" and flagged high; "CONC.", "CONC. FL.", "BR. 7ST.", "IR. CL.", "SC. GL." and similar were flagged too. A label made only of building-material words is now low (`construction_note()` in `relevance.py`), and a "4 cars garage" in the description no longer makes an undertaker's chapel a commercial garage. Eval: precision 88% -> **91%**, recall unchanged at 87%.
- **Repeat reads and plant parts as separate cards.** The website now groups the same kind of use within 40 m into one card, titled by its clearest read, listing the other printed labels ("Same kind of use, also printed within 40 m"). It says "checked" only if every part was checked, else "partly checked". Example: 6800 S Broadway's bulk oil station, filling station and oil house are one card.
- **Cut-off labels.** A label the reader marked as cut off or unclear is never a card's title when a clearer read is in the group; on its own, the card says to check the map image.

Shown listings: 185 (59 high unreviewed, 72 high checked, 54 medium), before grouping.

## Every unchecked listing checked against the scan (Oct 14, 2026)
All 113 shown listings that no one had checked (59 high, 54 medium) were compared with a full-resolution crop of the Library of Congress scan centered where the site places them. Fixes go in `config/corrections/carondelet-1938.json`, applied by `build_db.py` (`blockhistory/db/corrections.py`):
- **Hidden (15):** 3 not on the map (a "FILL'G STA." that was the street name FILLMORE, a low-confidence "DRY CLEANING" with no dry cleaner on the tile, a station placed in an empty yard on sheet 47), 2 private auto houses read as garages, 1 auto house read as auto repair, and 9 repeat reads of a site already listed.
- **Fixed (4):** "PRINT SHOP" and "PRINTS" are PAINT SHOP and PAINTS on the map; the gas tanks on the St. Louis Public Service substation belong to the station next door; a sheet 72 filling station moved 30 m to where it is printed.
- **Added (5): plant names the reader skipped** (it read their buildings but not the big lettering): Monsanto Chemical Co. (Carondelet Chemical Wks.), Johnston Tin Foil & Metal Co., Mississippi Valley Iron Co. pig iron plant, Laclede Gas Light Co. coke and by-products plant, St. Louis Ship Building & Steel Co. On the website a company name now titles its group's card.
- The construction-note rule also catches "…PLASTER PARTS".
- The other ~90 were right. About 8 are placed 10–30 m from their label (inside the 100 m search either way).
- These are machine-assisted checks, so the listings still say "not yet checked by a person".

Shown listings: 176. Production build of the website passes. Tests: 79.

## Week 12 (Oct 14, 2026): launched
- **Live at https://block-history.vercel.app/** (Vercel free tier, reading Supabase with the public key). Checked on the live site: searches inside and outside the covered area, the About page, Library of Congress map close-ups, desktop and phone (light and dark), no console errors, and neither Supabase value appears in the page or its scripts.
- Chemical plants now have their own explanation (they had shared the paint and printing sentence).
- **Analytics ready, off until an ID is set:** Umami Cloud (no cookies) counts visits and searches by outcome (found / nothing flagged / not covered / address not found). Search URLs carry the address, so query strings are excluded from page views and the address is never sent. The About page says so.
- **Left for Phase 1:** first 25 strangers. The README waits until the end of the project.

## Phase 1 done: 25 users (Oct 18, 2026)
Reached 25 people outside the project. Their feedback was about layout, so it was fixed before Phase 2:
- **"Expand the map, too much white space":** the map now fills the page width before a search and about 60% of it after, staying in view while the list scrolls; the summary moved beside the map so the map starts right under the search box; the heading area is tighter.
- **"Add a legend on the map":** a key in the map's top-left corner (often / sometimes linked, the searched address, the 100 m area, the covered area).
- **"About & limits is too long":** split into two tabs, **About** (what, how, accuracy as three stat tiles) and **Limits & privacy**. The disclaimer stays in the footer of every page.
Checked at desktop and phone width, light and dark, with no console errors; production build passes.

## Phase 2, month 4: the 1950 map (Oct 19, 2026)
- **Read the whole 1950 volume** (73 sheets, 1,460 tiles; sheet 11 isn't scanned), plus the tank and location passes on the 17 covered sheets. Cost **$0.58** (first pass $0.48, tanks $0.07, points $0.02). **Project total $1.34 of $10.**
- **Placed on the map without reading corners again:** `scripts/align_edition.py` aligns each 1950 scan to the 1938 one and carries the control points over. 17 sheets, median leave-one-out error 0.5–4.1 m, like 1938. Points that fell under a paste-over keep the whole-sheet prediction; checked by eye on sheets 57 and 72.
- **Checked all 189 shown 1950 listings against the scan.** 155 (82%) were right as read. Hidden: 5 reads of old print under a paste-over (a new kind of error: the building was replaced by 1950), 7 not on the map, 4 sprinkler or construction marks, 6 private garages or "found'n" notes, and 12 repeats or misplaced points. Corrected 3 and added 3 plant names (Monsanto, Laclede, the shipyard). The Mississippi Valley Iron Co. pig iron plant is gone by 1950: pasted over with a junk storage and a soap factory.
- **Website:** a 1938 / 1950 switch above the map. Each listing says whether the other year's map shows the same kind of use within 50 m ("Also on the 1950 map", "Not on the 1950 map", "New since the 1938 map"). Example: at 7313 S. Broadway the 1950 map adds a battery service at 7230 in a building that was a store in 1938, which is right on both scans.
- Shown: 176 sites (1938), 159 (1950). Recall for 1950 isn't measured yet: there are no hand labels for 1950.

## Whole area, both years, and raw accuracy over 87% (Oct 19, 2026)
- **Coverage:** all 46 Carondelet and Patch sheets georeferenced corner by corner for 1938 (1–7 m median leave-one-out error), and aligned for 1950 (no 1950 sheet 11 at the LoC). Sheet 58's inset placed (3 corners, similarity fit, checked against Idaho and Alabama today). Corners on streets realigned since 1938 were dropped (Bates St., parts of Michigan and Alabama Aves.).
- **Every shown listing on all 46 sheets, both years, checked against the scan.** Fixes in `config/corrections/carondelet-1938.json` and `-1950.json`; the checked sheets are listed in `config/corrections/checked.txt`.
- **Raw accuracy measured on every checked listing** (`scripts/shown_precision.py`): the AI plus the relevance rules, before any hand fix. It started at 84% (1938) / 82% (1950). The errors repeated, so rules were added: map markers (D, F, S, E, AS), car counts on non-garages, "FR. FOUND'N", more construction words, rear-address notes, the reader's "(illegible)", a guessed low-confidence "DRY CLEANING", and merging misread repeats of one site within 30 m. **Now 92% (1938) and 89% (1950).** The hand-label eval is unchanged (recall 103/119, high 47/53, precision 92%), so no real site was lost.
- **Address lookup:** City of St. Louis composite geocoder first (parcel when it can), Census as fallback. On 49 addresses, median distance to the building on the map 25 m vs 52 m for the Census.
- **Change notes:** "Also on the other map" now needs a shared label word; same kind of use only is "Similar use nearby".
- **1950 answer keys drafted** from the verified 1938 keys by comparing each site on the two scans (`evals/labels/04858_12_1950-*.json`, status draft). 26 sites marked gone, 10 renamed, 22 flagged `needs_human_check`. Sites new since 1938 are not in the drafts yet, so 1950 precision against them (78%) is too low by construction; recall 80/101 (79%) and tank sites 7/12 are the useful numbers until the keys are verified and swept for new sites.
- 1938 person-checked rows: 96 (was 99; three ticked rows were merged into a neighbouring site by the repeat rule).

## Phase 2: state tank and cleanup records (Oct 20, 2026)
- **152 Missouri DNR records** around Carondelet and Patch (106 tank facilities, 46 cleanup sites; 80 with a leak or contamination on record), 89 placed on their city parcel. 72 fall inside the mapped area; 38 of those are within 40 m of a past use on the maps.
- Examples that line up: Broadway 66 and a former service station (leaks, cleaned up) on the 1938 filling stations at 6520–6532 S. Broadway; the former Geldbach site at 6800 S. Broadway on the bulk oil station; J. W. Aluminum on the Johnston Tin Foil plant; Carondelet Coke on the Laclede coke ovens; ICL Performance Products (active cleanup) on the Monsanto plant; Nexeo on the Lowell Bleachery; a leak under investigation at 6101 Michigan on the 1938 gasoline filling station.
- Website: a "State record at about this spot" note on matching listings, a list of other state records within 100 m, and a plain "no record" note. About and Limits pages updated. Tests: 100.
