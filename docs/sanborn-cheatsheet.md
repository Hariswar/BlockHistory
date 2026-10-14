# Sanborn Map Cheat Sheet

Built from the key printed on the **St. Louis Vol. 12 (1938) key map** (`04858_12_1938-0000`) and from annotating 5 Carondelet sheets (50, 53, 57, 62, 74). The 1938–1950 edition uses the same key; it's the 1938 sheets with paste-over corrections.

## Color codes (building construction)
| Color | Meaning | Notes |
|---|---|---|
| Pink / red | Brick | Most Broadway stores, foundries, kilns |
| Yellow | Frame (wood) | Most dwellings, sheds, coal yards |
| Pink with yellow edge `(VEN'D)` | Brick veneer | |
| Pink with `BRICK 1ST` | Brick first story, frame above | |
| Yellow with `FRAME, BRICK LINED` | Frame, brick lined | |
| Blue `(C.B.)` | Hollow concrete / cement block | 1920s–30s filling stations and garages |
| Blue `(CONC)` | Concrete | |
| Blue `(C.B. & BR. CONST'N)` | Mixed cement block and brick | |
| Gray | Iron building / metal clad | Tanks, steel foundry sheds, blast furnace |
| Olive / dark brown | Fireproof construction | Often with "BUILT 19xx" |
| Yellow with `(ASB. CL.)` | Frame covered with asbestos | Asbestos siding |
| X across the footprint | Stable | |
| `A` | Auto house or private garage | `A IN B'S'M'T` = garage in basement |
| `LOFT` | Tenant building, various manufacturers | |

## Letters and numbers on a footprint
| Mark | Meaning |
|---|---|
| D / F / S | Dwelling / flat / store |
| `2`, `2B`, `1½` in a corner | Stories (`B` = basement) |
| `●` / `x` / `○` in a corner | Composition / shingle / non-combustible (metal, slate, tile, **asbestos shingle**) roof |
| `8`, `12`, `16` along a wall | Wall thickness in inches |
| `|` `||` `|||` `||||` | Fire wall 6 / 12 / 18 / 36 inches above roof |
| `28'` | Height to roof |
| `CAP'Y 12 CARS`, `5 CARS` | Garage capacity |

## Symbols that matter most
| Symbol | Meaning | Why we care |
|---|---|---|
| **`G.T. ○`** | **Gasoline tank** | The key symbol. Usually small circles at the curb by a filling station; `G.T.S` with 2–3 circles means several tanks |
| `IR. GASOL. TK. ON GRD` / `IR. TANKS 8' ABV. GRD.` | Above-ground iron fuel tanks | High |
| `FUEL OIL TK.` | Fuel oil tank | High |
| `OIL HO.` / `OIL W. HO.` | Oil house / oil warehouse | High |
| `V.S.B.` | Vertical steam boiler | Coal ash |
| `I.E.P.` | Independent electric plant | Fuel, transformer oil |
| `GASOL. ENG.` | Gasoline engine | Medium |
| `AMMONIA TKS.` / `IR. ALCOHOL TK.` / `CALCIUM CHLORIDE TK.` | Process chemical tanks | Medium–high |
| `IR. CH.` / brick-chimney square / `CH. 70'` | Iron or brick chimney and height | Shows a boiler or furnace |
| `(W.T.)` | Water tank | |
| `(O.U.)` | Open under | |
| Paragraph under a company name | Insurance notes: watchman, heat, power, **fuel (coal, coke, gas, oil)** | Best evidence of what was burned on site |

## Map furniture (not buildings)
| Mark | Meaning |
|---|---|
| Big bold number in a block (`3012`) | City block number (matches modern block numbers, useful for georeferencing) |
| Large number at a sheet edge (`57`) | Adjoining sheet; `0` = not mapped |
| **`(54-60-64-68 VOL. 8)` under the sheet number** | **Matching sheets in the previous edition.** Vol. 12 1938 sheet 50 = Vol. 8 1908 sheets 54, 60, 64, 68 |
| Circled number at a corner (`(41')`) | Ground elevation |
| `6" W.P.` / `12" W.P. (PRIV.)` | Water pipe and size |
| Numbers along a street edge | Addresses; numbers **nearest the building** are current, ones **furthest away** are old numbering |
| `NOT OPENED` on a street | Platted but not built |
| `FR. FOUND.` | Frame building on a foundation (riverfront shacks) |

## Use labels and contamination relevance
| Label | Meaning | Relevance |
|---|---|---|
| **FILL'G STA. / F.S.** | Filling station | **High**: gasoline USTs |
| **BATTERY SERV.** | Battery service | **High**: lead |
| **BULK OIL STA. / GASOL STGE TKS** | Bulk petroleum terminal | **High** |
| **GARAGE / AUTO REP'G / USED AUTO SALES / A 18 TRUCKS** | Garages, auto repair, truck yards | High–medium: oil, solvents, tanks |
| **DRY CLEANING / CLEANING & PRESS'G** | Dry cleaner | **High**: PCE/TCE (none in the first 5 sheets; check the rest) |
| **GASOMETER / GAS PRODUCER HO. / COKE OVENS / TAR TKS / BENZOL / NAPTHALINE / PURIFIERS** | Manufactured gas / coke plant | **High**: coal tar, PAHs, benzene, cyanide |
| **FOUNDRY / CUPOLA / CORE OVENS / ELEC. MELTING FURN. / BLAST FURN. / PIG IRON** | Iron and steel foundries | **High**: metals, foundry sand, slag |
| **SMELTING & MELTING POTS / MFG. METAL FOIL** | Metal smelting | **High**: lead, tin |
| **BLEACHERY / DYE WORKS** | Textile bleaching and dyeing | **High**: dyes, solvents, chlorine |
| TIN SHOP / MACH. SHOP / BL. SM. | Metalworking | Medium |
| PAINTS / PAINT SHOP / SIGN PAINT'G | Paint store or shop | Medium: lead, solvents |
| WOODWK'G / SASH & DOOR FACTY | Woodworking | Medium: finishes |
| COAL / COAL YARD | Coal yard | Medium: PAHs, metals |
| JUNK YARD / WRECKING & SUPPLY | Salvage | Medium–high: metals, oils |
| ELEC. SUB. | Electric substation | Medium: transformer oil (PCBs) |
| ICE PLANT / ARTIFICIAL ICE | Ice plant | Medium: ammonia |
| POND (WATER FILLED QUARRY) | Flooded quarry | Medium: unknown fill |
| UNDERTAKER | Funeral home | Low |
| FLOUR MILL / FEED MILL / VINEGAR WKS | Food processing | Low |
| CEMENT ELEVATOR | Cement storage | Low |

## Carondelet 1938: what the first 5 sheets show
Full lists: `evals/labels/04858_12_1938-00{50,53,57,62,74}.json`.

| Sheet | Area | Highlights |
|---|---|---|
| 74 | River Des Peres mouth | **Laclede Gas Light Co. coke & by-products plant**: 3 gasometers, 65 coke ovens, tar / ammonia / benzol / naphthalene tanks, purifiers, coal & coke piles. The biggest contamination site in the sample |
| 50 | Riverfront, Dover to Quincy | **Mississippi Valley Iron Co.** blast furnace (idle), **St. Louis Steel Casting**, **Semi-Steel Casting**, **Johnston Tin Foil** (smelting, fuel oil tank), a **bulk oil station**, 3 filling stations, coal yards, a junk yard |
| 53 | S. Broadway, Quincy to Robert | Main street: **filling station + battery service** (2 G.T.S), 2 tin shops, paint store with **oil house**, coal yard, Baur Flour Mills, **bulk oil station** (above-ground tanks) by the tracks |
| 57 | South of Robert (Patch) | 2 filling stations (3 G.T.S each), used auto sales, **Western Foundry**, **Liberty Foundry**, **Lowell Bleachery & Dye Works**, flooded quarry |
| 62 | Patch residential | Mostly D/F/A. **Chester Iron & Foundry** (part idle), undertaker, tin shop, sign painting |

## Gotchas for the map-reading agent
- **G.T. symbols are tiny circles beside, not inside, the building**, often just `G.T.S ○○○` at the curb. Tesseract never finds them; the vision model must be asked about them explicitly.
- North rotates sheet to sheet (on sheets 50 and 57, north points to the upper left). Read street names, not directions.
- Big plants are drawn as many small labeled parts (`STEEL TAR TKS`, `PUMP RM.`); a whole plant can be one finding with many sub-labels.
- Insurance notes ("FUEL: COAL, COKE & GAS") are small paragraph text under the company name.
- Insets use their own scale, and some sheets switch scale (50 ft vs 100 ft per inch). Note this for georeferencing.
- 1950 sheets are paste-ups on the 1938 base, so one sheet mixes dates.
- Key maps use colors for sheet coverage, not construction. Don't extract buildings from them.

## Earlier pilots (other map styles, kept for the eval set)
- **The Hill, 1903** (Vol. 10): brickworks, kilns, clay mines; pre-car key. `evals/labels/04858_10_1903-*.json`.
- **Rolla, 1924 and 1948**: small-town car-era maps with filling stations, solvent tanks. `evals/labels/04849_*.json`.
