# Sanborn Map Cheat Sheet

Built from the key printed on Rolla 1933/1948 sheet 1 (`04849_1948-0001a`, key revised 5-31)
plus the 1924 index. Older editions (pre-1910s) use the same color scheme with a simpler key.

## Color codes (building construction)
| Color | Meaning | Notes |
|---|---|---|
| Pink / red | Brick | Most of downtown Pine St |
| Pink with yellow stripe, "(VEN'D)" | Brick veneer | |
| Yellow | Frame (wood) | Most dwellings |
| Blue | Stone | |
| Blue with "C.B." | Hollow concrete / cement block | Common for 1920s–40s garages and filling stations |
| Gray | Iron building / metal-clad | Sheds, warehouses, tanks |
| Brown | Fireproof construction | |
| Pink with "(TILE)" | Tile building | |
| Blue with an X across | Stable (shown with CONC = concrete) | |

Colors on the **key map** (sheet 1) aren't construction; they just show which sheet covers which area.

## Use labels (inside the footprint)
| Abbrev. | Meaning | Contamination relevance |
|---|---|---|
| D | Dwelling | — |
| S | Store | Low (depends on the business) |
| F | Flat | — |
| A | Auto house (private garage) | Low; occasional private fuel tank |
| REST. | Restaurant | — |
| OFF. | Office | — |
| F.S. / FILL'G STA. / GAS & OIL | Filling station | **High**: petroleum, underground storage tanks |
| GARAGE / AUTO REP'G / AUTO SALES & SERV. | Auto repair / dealer | **High**: solvents, waste oil, often tanks |
| BULK OIL DEPOT / OIL HO. / OIL CO. (e.g. Standard Oil, Pierce Oil) | Bulk petroleum storage | **High**: large above-ground and underground tanks, usually by the railroad |
| DRY CLEANING / CLEANING & PRESS'G / DRY CLE'G | Dry cleaner | **High**: chlorinated solvents (PCE/TCE) in soil and groundwater |
| TIN SH. / PLUMB'G / BLK SM. (blacksmith) / MACH. SH. | Metal working | Medium: metals, oils |
| PAINT SH. / PRINT'G | Paint / printing | Medium: solvents, lead |
| PHOTO | Photo studio / lab | Medium: silver, developer chemicals |
| COAL / COAL YD. / COAL SHEDS | Coal storage | Medium: PAHs, metals |
| ELEC. LT. & WATER PL. / GAS WKS. | Power or manufactured-gas plant | **High**: coal tar, PAHs |
| CREAMERY / ICE PLANT | Food processing / refrigeration | Low–medium: ammonia, fuel |
| LUMBER / LUMBER SHED | Lumber yard | Low–medium: wood treatment chemicals |
| FEED / WHOL. GRO. | Feed store / wholesale grocery | Low |
| DRUGS | Drugstore | Low |

## Symbols
| Symbol | Meaning | Why we care |
|---|---|---|
| **○ G.T.** | **Gasoline tank** | **The single most important symbol for this project** |
| Number in a footprint corner (e.g. `2`, `1B`) | Stories (`B` = with basement, `2B` = 2 stories & basement) | |
| `x` in a corner | Shingle roof | |
| `●` in a corner | Composition roof | |
| `○` in a corner | Slate, tile, asbestos shingle, or metal roof | Asbestos indicator, low priority |
| Filled square with outline / `○` | Brick chimney / iron chimney | |
| ● V.S.B. | Vertical steam boiler | Fuel storage nearby |
| I.E.P. | Independent electric plant | Fuel, transformer oils |
| ● D.H. | Double hydrant | |
| `6" W. PIPE` | Water main and size | |
| Circled A.S. / N.S. | Automatic sprinklers / not sprinklered | |
| Circled F.A. | Fire alarm box | |
| `(O.U.)` | Open under | |
| Big circled number (e.g. **57**) | Reference number | |
| Number in the middle of a block | Block number | |
| Numbers along the street edge | Street addresses; numbers in parentheses are older numbering | **Needed for georeferencing** |
| `|` / `||` / `|||` marks on walls | Fire walls 6, 12, or 18 in. above roof | |
| Pasted-over patch (slightly different paper tone) | Later correction (1948 sheets are 1933 sheets with patches) | Read the top layer, but note the paste date |

## Rolla-specific things already spotted
| Where | What | Source |
|---|---|---|
| North edge, by the Frisco tracks | **BULK OIL DEPOT** | 1948 sheet 1a key map |
| E 7th St just east of Pine, ref #57 | **DRY CLE[ANING]** (label partly hidden) | 1948 sheet 2, tile r2_c1 |
| Index "Specials" | **Standard Oil Co.** (sheet 6), **Pierce Oil Co.** (sheet 7) | 1924 sheet 1 index |
| Index "Specials" | Elec. Light & Water Pl. (sheet 6), Rolla Creamery (sheet 6) | 1924 sheet 1 index |
| Pine St at 8th St, NE corner | Herrmann Lumber Co. | 1948 sheet 2 |
| Pine St at 6th St, SW block | Creamery & ice plant, F.B. Powell Lumber Co., coal | 1948 sheet 2 |
| North of town | Sinclair Pennant Tavern (Sinclair = oil brand; possible fuel station) | 1948 sheet 1a key map |

## Gotchas for the map-reading agent
- Labels are rotated to follow the building's long axis, so the model must read sideways text.
- Addresses sit *outside* the footprint along the street line, and current and old numbers are stacked.
- The 1948 edition is the 1933 sheets with paste-over corrections, so the same sheet mixes two dates.
- The key map on sheet 1 uses colors for sheet coverage, not construction. Don't extract buildings from it.
