# St. Louis Sanborn Sources

Checked 2026-10-10 against the Library of Congress Sanborn collection (loc.gov JSON API). Only items with images in the API ("View All Images" on the site) are scanned; many later editions are catalogued but not scanned.

## Carondelet (the study area)
Carondelet is far south St. Louis between the Mississippi and the River Des Peres. Today's boundaries: Eichelberger St (NE), the Mississippi (SE), the River Des Peres (SW), and S. Grand Blvd / I-55 (NW). Patch, south of Robert Ave, was part of the old town of Carondelet.

| Edition | LoC item | Images | Status |
|---|---|---|---|
| **Vol. 12, 1938** | `sanborn04858_022` | 77: title, index, key map, sheets 1–74 | **Scanned.** Phase 1 map year |
| **Vol. 12, 1938 – Jun 1950** | `sanborn04858_041` | 78: cover, title, 2 index pages, key map, sheets 1–74 **except 11** | **Scanned.** Phase 2 map year. Paste-up revisions on the 1938 base |
| Vol. 8, 1908 | `sanborn04858_011` | 123 | Scanned. **Covers the same riverfront Carondelet streets** (sheets ~47–106). A third, pre-car year |
| Vol. 12, 1916 | `sanborn04858_015` | 85 | Scanned but **does not match**. In 1916, Vol. 12 covered Dutchtown / Gravois / Morgan Ford; only sheets 47–50 touch Carondelet's west edge |

Saved in `config/neighborhoods/carondelet.json`, with every sheet tagged by area.

**The volume numbers moved between editions.** In 1908, riverfront Carondelet was Vol. 8 (which ran from Chippewa south to the River Des Peres). By 1938 it had been split: Vol. 8 kept Dutchtown / Marine Villa north of Bates, and Vol. 12 took Carondelet. Each 1938 sheet prints its 1908 equivalent under the sheet number, e.g. sheet 50 shows "(54-60-64-68 VOL. 8)", so the two years can be linked sheet by sheet.

### Which Vol. 12 sheets are Carondelet
From the 1938 key map (approximate; the Fire Limits line and the Missouri Pacific R.R. roughly follow S. Grand):

| Group | Sheets | Count |
|---|---|---|
| Carondelet (Bates to Robert, Grand to the river) | 9–14, 19–26, 42–56, 58, 59, 63, 68 | 33 |
| Patch (south of Robert, east of Alabama) | 57, 60–62, 64–67, 69–74 | 14 |
| West of Grand (Holly Hills, Boulevard Heights, Carondelet Park, cemeteries) | 1–8, 15–18, 27–41 | 27 |

All 74 sheets are in the budget (155 images across both editions). Process Carondelet and Patch first; the west-of-Grand sheets are mostly 1920s–30s houses and parkland.

## Test set: 1904 World's Fair volume
`sanborn04858_002`: "Insurance maps of Louisiana Purchase exposition", 23 images (title + key map + sheets 1–21). Saved in `config/neighborhoods/worlds-fair-1904.json`. A self-contained set with unusual labels (exhibition palaces, temporary buildings) for testing the reader.

## Why not The Hill
The Hill is in Vol. 10. Only its **1903** edition is scanned; the 1926 and 1926–1951 editions are catalogued but not scanned, which would leave The Hill with no car-era maps. Its config (`config/neighborhoods/the-hill.json`) and five labeled 1903 sheets are kept as a pre-car map style for the eval set.

## Other St. Louis volumes, for later neighborhoods
Scanned: Vols. 1–12 (1903–1916 editions); Vols. 8, 12, 20 (1938); Vols. 3–9, 12, 20 (1950–51 revisions). Not scanned: Vols. 1, 2 (1932, 1950); 10, 11, 13–17 (1924–1931 editions and their 1950 revisions).

Vol. 8 (1938, `sanborn04858_019`, 90 images), Dutchtown / Marine Villa just north of Carondelet, is the natural second neighborhood: same riverfront, same map years.

## Other sources (stretch goals)
- **City directories**: yearly St. Louis directories after ~1930 aren't on the Internet Archive. Gould's Red Book (business directory, possibly 1917) may be a free pre-1938 snapshot. Ask the St. Louis Public Library about criss-cross directories for key lots (Phase 3).
- **University of Missouri Digital Library** (digital.library.missouri.edu) also hosts St. Louis sheets. It blocks scripts with a CAPTCHA, so search it in a browser.
