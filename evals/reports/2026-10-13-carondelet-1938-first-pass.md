# Map reader accuracy: carondelet 1938

Generated 2026-10-13 by `scripts/evaluate.py` from cached results ($0 to run).
Gas-tank second pass: off (first pass only).
Sites are hand-labeled contamination-relevant uses (see each label file's `scope`).
Draft label files have not been checked by a person yet, so their numbers can move.

## Summary

### Human-verified labels (5 sheets, 100 tiles)

| measure | Haiku 5.5 (low, batch) | Tesseract (free) |
|---|---|---|
| Recall: hand-labeled sites found | 73/88 (83%) | 57/88 (65%) |
| Recall: high-relevance sites | 34/41 (83%) | — |
| Precision: high/medium flags that are a labeled site | 106/121 (88%) | — |
| … of those, parts of a labeled plant (CUPOLA, SECTION 1) | 21 | — |
| … of those, duplicate reads of a site | 29 | — |
| … wrong flags that are real but out of scope | 1 | — |
| Gas-tank sites with a tank on the right site | 6/10 (60%) | 0/10 |
| Gas-tank sites with the exact count | 4/10 (40%) | — |
| Gas tanks: map vs read on those sites | 25 vs 12 | — |
| Tanks reported on sites with none | 1 findings | — |
| Spot-checked high rows marked ok | 67/70 (96%) | — |
| Cost | $0.0462 total, $0.0092/sheet | $0 |

### Draft labels (Claude, unverified) (5 sheets, 100 tiles)

| measure | Haiku 5.5 (low, batch) | Tesseract (free) |
|---|---|---|
| Recall: hand-labeled sites found | 28/30 (93%) | 10/30 (33%) |
| Recall: high-relevance sites | 12/12 (100%) | — |
| Precision: high/medium flags that are a labeled site | 36/41 (88%) | — |
| … of those, parts of a labeled plant (CUPOLA, SECTION 1) | 2 | — |
| … of those, duplicate reads of a site | 9 | — |
| … wrong flags that are real but out of scope | 1 | — |
| Gas-tank sites with a tank on the right site | 5/5 (100%) | 0/5 |
| Gas-tank sites with the exact count | 5/5 (100%) | — |
| Gas tanks: map vs read on those sites | 11 vs 11 | — |
| Tanks reported on sites with none | 0 findings | — |
| Spot-checked high rows marked ok | 16/21 (76%) | — |
| Cost | $0.0392 total, $0.0078/sheet | $0 |

### All labeled sheets (10 sheets, 200 tiles)

| measure | Haiku 5.5 (low, batch) | Tesseract (free) |
|---|---|---|
| Recall: hand-labeled sites found | 101/118 (86%) | 67/118 (57%) |
| Recall: high-relevance sites | 46/53 (87%) | — |
| Precision: high/medium flags that are a labeled site | 142/162 (88%) | — |
| … of those, parts of a labeled plant (CUPOLA, SECTION 1) | 23 | — |
| … of those, duplicate reads of a site | 38 | — |
| … wrong flags that are real but out of scope | 2 | — |
| Gas-tank sites with a tank on the right site | 11/15 (73%) | 0/15 |
| Gas-tank sites with the exact count | 9/15 (60%) | — |
| Gas tanks: map vs read on those sites | 36 vs 23 | — |
| Tanks reported on sites with none | 1 findings | — |
| Spot-checked high rows marked ok | 83/91 (91%) | — |
| Cost | $0.0855 total, $0.0085/sheet | $0 |

## Per sheet

| sheet | labels | recall | high recall | precision | dup. | tank sites | exact | OCR recall | $ |
|---|---|---|---|---|---|---|---|---|---|
| 0047 | draft | 8/8 (100%) | 3/3 (100%) | 9/10 (90%) | 2 | 2/2 (100%) | 2/2 (100%) | 2/8 (25%) | 0.0077 |
| 0049 | draft | 5/5 (100%) | 2/2 (100%) | 5/6 (83%) | 1 | — | — | 1/5 (20%) | 0.0080 |
| 0050 | verified | 23/27 (85%) | 10/12 (83%) | 37/44 (84%) | 8 | 4/7 (57%) | 3/7 (43%) | 21/27 (78%) | 0.0129 |
| 0053 | verified | 14/17 (82%) | 3/3 (100%) | 13/17 (76%) | 4 | 1/1 (100%) | 1/1 (100%) | 4/17 (24%) | 0.0087 |
| 0056 | draft | 7/7 (100%) | 5/5 (100%) | 10/12 (83%) | 1 | 2/2 (100%) | 2/2 (100%) | 0/7 (0%) | 0.0090 |
| 0057 | verified | 10/12 (83%) | 5/5 (100%) | 25/26 (96%) | 7 | 1/2 (50%) | 0/2 (0%) | 7/12 (58%) | 0.0090 |
| 0061 | draft | 4/4 (100%) | 1/1 (100%) | 6/6 (100%) | 3 | 1/1 (100%) | 1/1 (100%) | 2/4 (50%) | 0.0065 |
| 0062 | verified | 4/5 (80%) | 1/1 (100%) | 6/8 (75%) | 2 | — | — | 2/5 (40%) | 0.0072 |
| 0067 | draft | 4/6 (67%) | 1/1 (100%) | 6/7 (86%) | 2 | — | — | 5/6 (83%) | 0.0081 |
| 0074 | verified | 22/27 (81%) | 15/20 (75%) | 25/26 (96%) | 8 | — | — | 23/27 (85%) | 0.0084 |

## Details

### 04858_12_1938-0047

- Flags that are not a labeled site: BR. 7ST. (medium)

### 04858_12_1938-0049

- Flags that are not a labeled site: S. CL. 2 (high)

### 04858_12_1938-0050

- Missed: PAINT'G (medium); THE JOHNSTON TIN FOIL & METAL CO. MFG. METAL FOIL (high); COAL YARD (medium); FILL'G STA. (high)
- Tank counts off: BULK OIL STA. / GASOL STGE TKS. 6800: map 4, read 2; SEMI-STEEL CASTING CO. MFG. CASTINGS 139: map 1, read 0; FILL'G STA. 6930: map 3, read 0; FILL'G STA. 6532: map 2, read 0
- Tanks on a site with none: GASOL. & ALCOHOL STGE. x1
- Flags that are not a labeled site: G. C. CO. (high); M. CARAG. (high); BL. SM. L. (medium); BLK. RM. (medium); BLR. RM. (medium); TRANSFER RM. (medium); WELDING EQUIPT. (medium)

### 04858_12_1938-0053

- Missed: WOODWK'G (low); PAINTS (medium); BLDG SUPPLY W. HO. (low)
- Flags that are not a labeled site: PRINT SHOP (medium); PRINTS (medium); STEEL C... METAL L... PLASTE... (medium); STEEL C... METAL L... PLASTER (medium)

### 04858_12_1938-0056

- Flags that are not a labeled site: IRNE REP. (high); METAL LATH & PLASTER PARTS (medium, out of scope)

### 04858_12_1938-0057

- Missed: IR. TANKS NOT USED (medium); POND (WATER FILLED QUARRY) (medium)
- Tank counts off: FILL'G STA. 7300-7302: map 4, read 0; FILL'G STA. 7432: map 3, read 2
- Flags that are not a labeled site: BLR RM. (medium)

### 04858_12_1938-0061


### 04858_12_1938-0062

- Missed: STEEL STGE. (low)
- Flags that are not a labeled site: BOILER RM. (medium, out of scope); WOODWK'G (medium)

### 04858_12_1938-0067

- Missed: CONTRACTOR'S YARD (medium); ST. LOUIS SHIP BUILDING & STEEL CO. / SHIP YARDS (medium)
- Flags that are not a labeled site: DRY CLEANING (high)

### 04858_12_1938-0074

- Missed: STEEL PROCESSING TK. / AERATING TOWER (high); STEEL AMMONIA LIQUOR TKS. / STEEL TAR SEPARATOR TK. / STEEL TAR TKS. / STEEL BENZOL WASHERS / STEEL COOL'G TOWERS / ACID STGE. TKS. (high); STEEL GAS COOLING TKS. / STEEL TAR TANKS IN CONC. PIT (high); STEEL BENZOL & SOLVENT TKS. (high); COAL PILE / COKE PILE (high)
- Flags that are not a labeled site: B.R. (medium)
