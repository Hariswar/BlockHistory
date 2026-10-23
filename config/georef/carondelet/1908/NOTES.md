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

## Renamed (use today's name)
- **Malt St** (1908) = **Mott St** (1938 sheet 47 prints Mott in the same place; fits to ~1 m).
- **Robert Av** west of Alabama (sheet 71): ~10 m further south today.
- **Grundy St**: gone. **Wilmington Rd** west of Alabama: partly gone.

## Sheets
Corners and options for every sheet are in `streets.txt`; re-place them all with
`scripts/place_sheets.py carondelet 1908`, and see each fit with `--report`.

Placed (Oct 23): 47–68 (50 in two panels) except the ones below, 71, 80. Median left-out
error 1–5 m on most; the weaker ones:
- **52** (5.6 m): only Bates and Dover usable (Fassen moved, Caldwell gone).
- **54** (5.0 m) and **68** (4.5 m): riverfront; Water St is gone, so few corners.
- **71** (0.9 m on its four corners): Robert Av is ~10 m further south today, so the
  Blow–Robert half is extrapolated and may be up to ~10 m off near Robert.

Not placed:
- 41–46: north of Bates, outside the 1938 coverage.
- 69: west of Grand, outside the 1938 coverage.
- 70: nearly empty land; Grand and Colorado "not open", only two usable corners.

Still to do: 72–79 and 81–106 (those inside the 1938 coverage).
