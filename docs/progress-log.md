# Progress Log

One short entry per week: what got built, what got measured, what's next.

## Week 1 (Oct 5, 2026)
**Built**
- Repo, progress log, decision log.
- Picked the study area: **Rolla, MO**. The LoC has 9 Sanborn editions (1884–1948); we're using 1924, 1933, and 1948 (21 sheet images). All sheet URLs are in `config/cities/rolla-mo.json`.
- `scripts/list_sheets.py` finds every edition and sheet through the loc.gov JSON API.
- `scripts/download_sheet.py` pulls sheets through the IIIF image service at 50% scale (~3225×3825 JPEG, about 1 MB each), instead of the 150 MB master TIFFs. The 1924 and 1948 editions are downloaded.
- `scripts/tile_sheet.py` cuts each sheet into 20 overlapping 1024px tiles (week 3 work, pulled forward because Day 7 needed a tile).
- Sanborn cheat sheet written from the key printed on Rolla's own 1933/1948 sheet 1.
- `scripts/read_tile.py` is map-reading agent v0. It sends one tile to the vision model and gets structured JSON back, cached on disk so no tile is paid for twice.

**Interesting finds already** (no model needed)
- 1948 key map: a **Bulk Oil Depot** by the Frisco tracks on the north side of town.
- 1948 sheet 2: a **dry cleaner** on E 7th St just off Pine (ref #57).
- 1924 index: **Standard Oil Co.** (sheet 6) and **Pierce Oil Co.** (sheet 7).

**Measured**
- Nothing yet. No API key was configured, so the Day 7 model run is still pending.

**Still to do from the week-1 checklist**
- [ ] Day 5: hand-annotate 2 sheets (suggest `04849_1948-0002` downtown, and `04849_1924-0002` for the same blocks 24 years earlier). Template is in `evals/labels/_template.json`; rules in `docs/labeling-guide.md`.
- [ ] Day 7: add `ANTHROPIC_API_KEY` to `.env`, run `read_tile.py` on `04849_1948-0002_r2_c1.jpg`, and write down what it got wrong below.

**Day 7 notes: what the model got wrong**
- _(fill in after the first run)_

**Next (week 2)**
- Annotate 5 sheets and fold surprises into the cheat sheet.
- Look at sheets 6–7 of 1924 for the oil company sites.
