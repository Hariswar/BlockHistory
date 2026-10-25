# Reading 100-year-old fire insurance maps with a small AI budget

BlockHistory ([block-history.vercel.app](https://block-history.vercel.app)) answers one
question for an address in Carondelet, St. Louis: what stood near here that sometimes left
soil or groundwater contamination? The answer comes from Sanborn fire insurance maps for 1908,
1938 and 1950, read by Claude Haiku, placed on today's streets, checked against the scans, and
shown with the Missouri Department of Natural Resources' tank and cleanup records.

This is how it was built, what it cost, how accurate it is, and what didn't work.

## The problem

Sanborn maps drew American cities building by building for insurers: what each building was
made of, what it was used for, and where the gasoline tanks were buried. A filling station
from 1938 or a foundry from 1908 is exactly the kind of past use an environmental site
assessment looks for, but the maps are scanned images. The Library of Congress has them
online; nobody has them as data for a neighborhood.

Carondelet was chosen because it has all three: scanned maps from three years, a heavy
industrial riverfront (a coke plant, foundries, a smelter, bulk oil) and houses right next to
it. Earlier picks (Rolla, then The Hill) were dropped when their later maps turned out not to
be online ([decision log](decision-log.md)).

## Pipeline

```
LoC IIIF scans -> 1024 px tiles -> Haiku reads labels -> tank pass -> point pass
   -> merge across tiles -> relevance rules -> hand corrections -> place on today's streets
   -> SQLite / Supabase PostGIS -> Next.js site
```

**Collecting.** Sheets are downloaded through the Library of Congress IIIF server at 50% scale
(about 1 MB instead of 150 MB) and cut into 20 overlapping 1024 px tiles, so every label is
whole in at least one tile.

**Reading.** Each tile goes to Claude Haiku 5.5 through the Batch API with a structured-output
schema: printed label, plain-English use, house number, gasoline-tank count. Results are
cached by model, prompt version and image bytes, so nothing is ever paid for twice. On the
first test tiles Haiku found 9 of 10 hand-labeled sites; a free Qwen2.5-VL 7B found 3 and
Tesseract 6, so the free-first plan was dropped. Medium effort scored *worse* than low and
cost twice as much.

**Gas tanks.** The tank circles are about 6 px wide at 50% scale, and the first pass missed
most of them. Rather than a bigger model, tiles with a fuel or vehicle site (about 1 in 4) are
re-read at full resolution with a tanks-only question. That took tank sites found from 6/10 to
9/10 and exact counts from 4/10 to 7/10, for $0.04 on 10 sheets.

**Positions.** The reader's position words ("upper left") were off by 27–55 m. A second cheap
pass gives Haiku the tile and its list of labels and asks for each flagged building's pixel
center: 13 of 15 within 4 m.

**Merging and relevance.** Reads from neighbouring tiles are merged only across a shared tile
edge (two entries in one tile are two buildings). A keyword table decides relevance: high
(filling stations, garages, dry cleaners, foundries, gas works, chemical works), medium
(machine shops, paint, coal yards, lumber), or low. Most of the work was in what *isn't* a
use: construction notes ("CONC. FL.", "TIN CL."), map symbols, private auto houses ("3 CARS"),
and "FR. FOUND'N", a frame building on a foundation, which readers love to call a foundry.

**Corrections.** Wrong reads found by checking the scan go in a per-year corrections file
(hide, edit or add, each with a reason), matched by sheet, label and position. The tile cache
is never edited, so a re-read can't undo a fix, and a correction that stops matching anything
fails the accuracy check.

**Placing the maps.** Each sheet is fitted to today's streets with an affine (or similarity)
transform from street corners, checked by leave-one-out error. Three methods, one per year:

- *1938:* corners read by hand on zoomed, gridded crops (an automatic edge finder was right on
  only about 2 of 3).
- *1950:* the same printing plates with paste-over corrections, so each 1950 scan is aligned to
  its 1938 sheet (ORB features + RANSAC) and the 1938 corners are carried over.
- *1908:* drawn at twice the scale, where a click is ±15 px. Instead, each street's blank band
  is fitted as a line along its whole length and the lines are crossed (1–3 px). Corners are
  matched to OpenStreetMap intersections by consensus, so streets that moved since 1908
  (Fassen, Kansas, Caldwell, Water) get set aside instead of bending the fit.

Typical error is 2.0–2.8 m by year; the least precise sheet is 7.8 m.

**Explaining.** Each listing gets a short note. Code writes the opening (year, label as
printed), the tank sentence and "This is a historical use, not a test result"; Haiku writes
only the middle sentence about what that kind of business handled. Every AI sentence goes
through a checker: no claim that a site is contaminated, no health claims, no "you", nothing
about today, no numbers that aren't in the label, two sentences at most. Anything that fails
falls back to a reviewed template.

**State records.** Missouri DNR tank and cleanup records are shown beside the map. A record is
attached to a listing only when it is within 40 m and its kind fits, and its status is
reworded in plain language, never made stronger.

## Measuring it

Ten sheets per year were annotated by hand for 1938 and 1950, and two for 1908. `scripts/check_accuracy.py`
scores the reader against them, scores every shown listing against the scan checks, checks
that every correction still matches, and checks every sheet's placement, in about 15 seconds
from cache at $0. A pre-commit hook runs it, and it compares against a committed baseline
rather than fixed targets, so every change has to hold the line.

One lesson from building it: precision on the answer keys can't see junk that a looser rule
lets through elsewhere. Switching off the construction-note rule barely moved key precision,
but 30 new listings appeared. So the check also fails on any shown listing that wasn't in the
baseline, until someone has compared it with the scan.

| | 1938 | 1950 |
|---|---|---|
| Hand-marked sites found | 87% (103/119) | 80% (81/101) |
| Higher-concern sites found | 89% | 87% |
| Shown listings right as read (before fixes) | 92% (232/253) | 89% (213/238) |
| Gasoline-tank sites found | 14 of 15 | 8 of 8 |

The live numbers, including 1908, are on the [accuracy page](https://block-history.vercel.app/accuracy).
A weekly GitHub Action also runs saved searches against the live site, so a half-loaded
database or a changed address service shows up as an issue, and the
[status page](https://block-history.vercel.app/status) shows the result.

## Cost

The whole project's AI spend is under $2, against a $10 cap enforced in code (every call
checks a spend ledger and refuses to run past the monthly or total cap). Reading 1938 and 1950
cost $1.60; the same calls would have cost $3.18 without the Batch API and $63.51 with Sonnet
one call at a time ([cost.md](cost.md)). Hosting is free tiers: Vercel, Supabase, OpenFreeMap
base map, and map images loaded straight from the Library of Congress.

## The website

Next.js on Vercel, reading Supabase PostGIS through its REST API with the public key and
SELECT-only row-level security (a local SQLite file works the same way for development).
Addresses go through the City of St. Louis address service, usually landing on the parcel;
the US Census geocoder, the first choice, was 30–80 m off, which matters within a 100 m circle.
Each search shows the old map under the markers with a fade slider, compares each listing
with the map years on either side ("New since 1908", "Still on the 1950 map"), and links every
listing to its crop of the original scan. There are pages for 47 streets, share links with
generated previews, and a write-only queue where neighbors can add memories of what used to be
there; only the reviewer's wording is ever shown.

## What it can't do

- It isn't an environmental site assessment. A past use doesn't mean contamination today, and
  an empty result doesn't mean a lot is clean.
- Three snapshots only. A business that opened and closed between them doesn't show.
- The reader misses between 1 in 8 (1938) and 1 in 5 (1950) hand-marked sites, and misses
  outside the answer-key sheets can't be counted.

## What I'd do next

Another neighborhood: it's now a config file, control points and the usual runs, with no code
changes. Then city directories, to fill the years between the maps.
