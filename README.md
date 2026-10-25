# BlockHistory

**What stood on your block?** BlockHistory reads Sanborn fire insurance maps from 1908, 1938
and 1950 for Carondelet, St. Louis, and lists past uses near an address that sometimes left
soil or groundwater contamination: filling stations, garages, dry cleaners, foundries, a coke
plant.

**Live site:** [block-history.vercel.app](https://block-history.vercel.app) ·
[Accuracy](https://block-history.vercel.app/accuracy) ·
[Status](https://block-history.vercel.app/status) ·
[Technical write-up](docs/writeup.md)

BlockHistory is not an environmental site assessment. A past use doesn't mean the soil is
contaminated today, and an empty result doesn't mean it's clean.

## What it does

- Type an address: past uses within 100 m on each map year, with the old map drawn under
  today's streets, a crop of the original scan for every listing, and whether the map before
  and after shows it too.
- Missouri DNR tank and cleanup records nearby, in plain words.
- Pages for 47 streets, share links with previews, and a form for neighbors to add what they
  remember.

## How it works

1. Map scans come from the Library of Congress (IIIF) and are cut into overlapping tiles.
2. Claude Haiku 5.5 reads each tile's labels through the Batch API, with a second
   full-resolution pass for gasoline-tank symbols and a third for building positions.
3. Keyword rules rate each use; wrong reads found on the scans are fixed in a corrections file.
4. Each sheet is fitted to today's street corners (typical error 2–3 m).
5. The data goes to Supabase PostGIS; a Next.js site on Vercel serves the search.

The whole AI bill is under $2 (a $10 cap is enforced in code). Details in
[docs/writeup.md](docs/writeup.md) and [docs/cost.md](docs/cost.md).

## Accuracy

| | 1938 | 1950 |
|---|---|---|
| Hand-marked sites found | 87% | 80% |
| Shown listings right as read (before fixes) | 92% | 89% |
| Gasoline-tank sites found | 14 of 15 | 8 of 8 |

Measured on 10 hand-annotated sheets per year by `scripts/check_accuracy.py`, which runs
before every commit. All numbers, including 1908, are on the
[accuracy page](https://block-history.vercel.app/accuracy).

## Repository

| Path | What's there |
|---|---|
| `blockhistory/` | The pipeline: collecting (`collector/`), reading (`map_reader/`), placing (`georef/`), database (`db/`), state records (`records/`), explanations, cost caps |
| `scripts/` | Command-line steps, the accuracy check (`check_accuracy.py`) and the live check (`check_live.py`) |
| `config/` | Neighborhoods, control points, hand corrections |
| `evals/` | Answer keys, spot checks, the accuracy baseline, saved live answers |
| `web/` | The Next.js website |
| `docs/` | [Pipeline](docs/pipeline.md), [decisions](docs/decision-log.md), [progress](docs/progress-log.md), [plan](docs/plan.md), [cost](docs/cost.md) |

## Running it

```
python -m venv .venv && .venv/bin/pip install -e ".[dev,vision]"
.venv/bin/python -m pytest -q
git config core.hooksPath .githooks        # accuracy check before each commit
```

Reading new sheets needs an `ANTHROPIC_API_KEY` in `.env` (see `.env.example`); the full run
is in [docs/pipeline.md](docs/pipeline.md). The scans, tiles and model cache live in `data/`,
which isn't in git.

The website:

```
cd web && npm install && npm run dev
```

It reads `data/blockhistory.sqlite` (built by `scripts/build_db.py`), or Supabase when
`SUPABASE_URL` and `SUPABASE_ANON_KEY` are set in `web/.env.local`.

## Sources

Sanborn Map Company maps from the
[Library of Congress](https://www.loc.gov/collections/sanborn-maps/) · Missouri Department of
Natural Resources E-START · City of St. Louis address service · base map
[OpenFreeMap](https://openfreemap.org), © OpenStreetMap contributors.

MIT License.
