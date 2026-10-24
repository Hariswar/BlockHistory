# 1908 Vol. 8 control points: notes

Points come from `scripts/georef_preview.py lines` (street center lines fitted from many
samples, crossed) and `scripts/georef_sheet.py gcps --skip-missing`. Scale is 50 ft to the
inch: about 0.33 ft (0.10 m) per pixel on the 50% image.

## Streets that moved or vanished since 1908 (don't use as control points)
- **Fassen St**: today's Fassen is ~8 m off the 1908 line (sheets 51, 52 fit 2–5 m better without it).
- **Kansas St** (Iron to Carondelet Park): roughly today's Holly Hills, but ~20 m further south on
  the 1908 map than Holly Hills is now (Iron–Kansas 142–151 m on the map, Iron–Holly Hills
  120–127 m today). Using it squeezes the sheet ~12%.
- **Caldwell St** (Bates–Dover): gone.
- **Soper St** east of Michigan (sheet 62): ~6 m off today.

Corners gone from today's map are taken from the placed 1938 sheets instead:
`config/georef/carondelet/known_points.txt` (Water St at Quincy–Robert, the coke-plant
riverfront at Upton/Koeln, the 1908 Polk St, the old river bend). They override OpenStreetMap.

## Renamed (use today's name)
- **Malt St** (1908) = **Mott St** (1938 sheet 47 prints Mott in the same place; fits to ~1 m).
- **Robert Av** west of Alabama (sheet 71): ~10 m further south today.
- **Grundy St**: gone. **Wilmington Rd** west of Alabama: partly gone.

## Sheets
Corners and options for every sheet are in `streets.txt`; re-place them all with
`scripts/place_sheets.py carondelet 1908`, and see each fit with `--report`.

Placed (Oct 23-24): 48 sheets (49 panels): 47-68, 71-74, 76-87, 89-93, 96-98, 100, 102.
Median left-out error 0.9-5 m on all but 52 (7.3 m) and 74 (6.4 m). Weaker ones:
- **52**: only Bates and Dover usable (Fassen moved, Caldwell gone).
- **54, 68, 74**: riverfront; Water St is gone, so few corners (74 uses Water St corners
  measured on the 1938 map).
- **71**: Robert Av is ~10 m further south today, so the Blow-Robert half is extrapolated.
- **77, 90**: three corners each, all near one edge; the far side is extrapolated.

Not placed:
- 41–46: north of Bates, outside the 1938 coverage.
- 69: west of Grand, outside the 1938 coverage.
- 70: nearly empty land; Grand and Colorado "not open", only two usable corners.
- 75: west of Grand, outside the 1938 coverage.
- 88: the old River Des Peres bend (channel moved in the 1920s-30s) with the Theo. Hiertz
  Metal Co. smelter. Only Poepping/Tennessee can be tied (from 1938 sheet 58, which shows the
  same smelting works); the street at the sheet's right edge is not Alaska (72 m from
  Tennessee, Alaska is ~110 m). The site is covered by the 1938 map and a state cleanup record.

- 94: empty blocks by the tracks; its streets are gone today east of Reilly.
- 95: Patch south of Davis was re-platted when the River Des Peres was moved; corners disagree by 25-50 m.
- 99, 101, 103, 105, 106: south of Catalan, outside the 1938 coverage (103 is the empty land
  where the Laclede coke plant was later built).
- 104: Polk and Van Buren there today are different streets.

Coverage check: 217 of the 252 shown 1938 listings fall on a placed 1908 sheet. The 35 that don't
are the coke plant (later), and the Phelan-Faust paint works and its neighbors on 1938 sheet 42
(empty land on 1908 sheet 70).
