# BlockHistory: Year-Long Build Plan

Oct 5, 2026 (revised Oct 10, 2026: Carondelet, St. Louis, about $10 for the year)

A free website where anyone types an address and sees what stood there over the last 100+ years, with a plain-language note on whether past uses (gas stations, dry cleaners, factories) are worth checking for soil or groundwater contamination.

Pitch: "I built a multi-agent system that reads century-old fire insurance maps to surface hidden pollution history under people's homes."

## Who it serves
- Families and renters who want to know what was on their land before it was a house
- Gardeners and parents (lead and petroleum in soil matter for vegetable beds and play areas)
- Homebuyers who can't afford a $2,000+ environmental report
- Local historians, teachers, and environmental justice groups

## Success after 12 months
- **Carondelet in St. Louis** fully covered across its online map years (1938 and 1950, plus 1908 Vol. 8 if time allows) and searchable by address, expanding as budget or free credits allow
- A published accuracy number for the map-reading agents, backed by a hand-labeled test set
- Real users and at least one partner organization (library, university, community group)
- A public write-up of how it was built and what was learned

**Starting neighborhood: Carondelet, St. Louis.** A historic river town in far south St. Louis, known for ironworks and boatbuilding (James Eads built Civil War ironclads there), with an industrial riverfront next to residential streets people live on today. Sanborn Vol. 12 covers it, with the 1938 (77 images) and 1938–1950 (78 images) editions both scanned, so the site can show change through the car era. The Hill was dropped because only its 1903 maps are online. A second neighborhood can be added later.

## Tech stack (about $10 for the whole year)
| Layer | Choice | Cost |
|---|---|---|
| Agent code | Python + plain tool-calling loops or a light agent framework | Free |
| First-pass map reading | Tesseract OCR for printed labels + a free open-source vision model (Qwen-VL or Llama Vision via Ollama) on Google Colab / Kaggle free GPUs | Free |
| Hard tiles only | Claude Haiku 5.5 via the Batch API (50% off); Sonnet 5.5 only for tiles Haiku is unsure about | ~$5–10 / year |
| Image processing | OpenCV, Pillow, rasterio | Free |
| Geospatial | GDAL, QGIS, PostGIS, GeoPandas | Free |
| Database | Supabase free tier (Postgres + PostGIS) | Free |
| Frontend | Next.js + MapLibre GL + OpenStreetMap tiles | Free |
| Hosting | Vercel or Cloudflare Pages free plan (`*.vercel.app`) | Free |
| Evals & tracking | Labeled test set + simple results table; Umami analytics | Free |

## Data sources (all public)
- Sanborn maps: Library of Congress (loc.gov JSON API); University of Missouri Digital Library also hosts St. Louis sheets. Only editions with images ("View All Images") are scanned; check before committing to an area
- Historical city directories (stretch goal): post-1930 St. Louis directories aren't on the Internet Archive; Gould's Red Book (possibly 1917) may be a free pre-1938 snapshot; ask the St. Louis Public Library
- Contamination records: EPA Envirofacts / Cleanups in My Community, Missouri DNR LUST database
- Modern addresses/parcels: City of St. Louis open GIS parcel data
- Historical aerials (later): USGS EarthExplorer

**What's online for Carondelet (checked 2026-10-10):** Vol. 12 1938 and 1938–1950 are scanned (sheet 11 is missing from the 1950 scan). The 1916 Vol. 12 does **not** cover Carondelet (it's Dutchtown), but **1908 Vol. 8 does**. See `docs/sources-st-louis.md`.

## Budget: about $10 for the year
| Item | Cost |
|---|---|
| 1904 World's Fair volume test run (23 sheets) | Under $1 |
| Carondelet (Vol. 12), 1938 and 1950 editions (155 images; ~275 with 1908 Vol. 8), mixed models | ~$4–6 |
| Eval and prompt testing (mostly Haiku) | ~$2–5 |
| Hosting, database, maps, data | $0 |
| Custom domain (optional, end of year) | $0–10 |

Estimates at batch prices (~$0.005/sheet Haiku 5.5, ~$0.10/sheet Sonnet 5.5). Process 10 real sheets first and check actual cost. Hard caps are enforced in code (`blockhistory/costs.py`): $3/month and $10 for the project. Cache every result. Apply early for the GitHub Student Developer Pack and other free credits. Details in `docs/budget.md`.

### Cost-control rules
1. Verifier agent: re-check only uncertain tiles, free model first.
2. Change-detection agent: compare saved text results, not images, so it costs almost nothing.
3. Explainer agent: Haiku 5.5 via Batch API, never Sonnet (~$1 for all of Carondelet).
4. Testing: most eval experiments on the free model or Haiku; Sonnet only occasionally.
5. No live chat: the website itself stays at $0 unless free credits arrive.
6. Free tiers: if a service asks for a credit card, set a spending cap or billing alert right away.

## Phase 1 (Months 1–3): Foundation and first launch
Goal: public site to search addresses in Carondelet and see past land uses from the 1938 map, with under $5 spent.

| Week | Focus | Done when |
|---|---|---|
| 1 | Pick the area: St. Louis; 1904 World's Fair volume (23 sheets) as test set; Carondelet from Vol. 12, 1938 + 1938–1950; check 1916 | List of sheet URLs for Carondelet |
| 2 | Learn the map key; annotate 5 sheets | One-page cheat sheet |
| 3 | Download + tiling pipeline | 40 sheets downloaded and tiled automatically |
| 4–5 | Map-reading agent v1: Haiku 5.5 (low effort) via the Batch API reads every tile; Tesseract cross-checks for free *(changed after Day 7: the free vision model found 3/10 labels and no tanks)* | Labels extracted from 10 sheets, spot-checked |
| 6 | Ground-truth set: hand-label 3 sheets fully | Labeled JSON to score against |
| 7 | First accuracy score: precision, recall, cost per sheet, free model vs Haiku | Baseline number |
| 8–9 | Georeferencing (QGIS manual, then automate) | Features have lat/lon |
| 10 | Load into PostGIS; 100 m query | Query returns results for a real address |
| 11 | Website v1: search, map, list with sheet links | Works locally |
| 12 | Launch + About & limitations page | Public URL, first 25 strangers |

Habits from week 1: public GitHub repo, weekly progress log, decision log.

## Phase 2 (Months 4–6): Accuracy and full agent pipeline
| Month | Focus | Done when |
|---|---|---|
| 4 | 1950 edition (and 1908 Vol. 8 if it matches) + time slider | Users scrub earliest → latest |
| 4 | Verifier agent (uncertain tiles only, free model first) → review queue | Eval accuracy improves over baseline |
| 5 | Change-detection agent: compare 1938 vs 1950 saved extractions per lot | Every lot has a "what changed here" summary |
| 5 | Cross-check agent (EPA + LUST; tank install dates cover the 1950s–70s): "confirmed record" / "historical use only" / "no record" | Every flagged site has a confidence level |
| 6 | Explainer agent on Haiku via Batch, follows safety rules, shows gaps ("1951–1975: no records") | Every summary links to sources |
| 6 | Eval suite: 15+ sheets, auto-run on changes | One command prints accuracy, cost, time per sheet |

Checkpoint: Carondelet searchable across 1938 and 1950, published accuracy, known cost per sheet, blog post.

## Phase 3 (Months 7–9): Deepen Carondelet and grow users
| Month | Focus | Done when |
|---|---|---|
| 7 | Neighborhoods as config, not code | New neighborhood takes days, not weeks |
| 7–8 | Deepen Carondelet: 1908 Vol. 8, more hand-checked labels, fix common errors; look up 10–20 key lots in library criss-cross directories | Per-map-year accuracy score |
| 8 | Cost optimization (routing, caching, batching) | Before/after cost chart |
| 8 | Engagement: shareable pages, street history, satellite slider | People share links unprompted |
| 9 | Community corrections → review queue ("Remember what used to be here?"); residents fill the 1950–80s gap | First corrections from strangers |
| 9 | Outreach: St. Louis Public Library, historical societies, St. Louis universities, community gardens | One org agrees to try/link |

## Phase 4 (Months 10–12): Polish, partnerships, packaging
| Month | Focus | Done when |
|---|---|---|
| 10 | Reliability: monitoring, alerts, weekly evals, status page | Runs a month untouched |
| 10 | Accessibility & mobile | Lighthouse a11y 90+ |
| 11 | Public accuracy dashboard (by neighborhood and map year) | Anyone can see trustworthiness |
| 11 | Formal partnership + quote | Named org using BlockHistory |
| 12 | Technical write-up | Published and linked |
| 12 | Resume packaging: demo video, README, bullets | Explain from memory |

## Explainer agent rules
1. Never say a property "is contaminated." Say "historical records show a [use] here in [year], a type of business that sometimes left soil contamination."
2. Always cite the source sheet or directory page.
3. Always show a confidence level and say when a finding is unreviewed.
4. Always end with a practical next step (soil test, state environmental agency, local health department).
5. Separate "confirmed in an official contamination database" from "historical land use only."

Other safeguards: About & limitations page stating which years are covered, not-an-ESA disclaimer, easy error reporting, no personal data about owners/residents, professor review of wording (~month 5).

## Risks and fallbacks
| Risk | Fallback |
|---|---|
| Faded/handwritten labels | Printed labels + color codes first; hard tiles to review queue |
| Georeferencing slow | Start where georeferenced Sanborn layers exist; manual GCPs for one area |
| History before 1938 or 1950–1980s is thin | Show gaps on the timeline; tank install dates; resident input; key lots by hand in library directories; Gould's Red Book and aerials as stretch goals |
| API costs grow | Hard caps in code, cache, cheaper models for easy tiles, research credits |
| Few users | Partners + "interesting finds" posts |

## Metrics to track from month 1
Sheets processed · precision/recall · verifier accuracy gain · cost per sheet · neighborhoods & map years · monthly visitors/searches (Umami) · user corrections · partner orgs

## First 7 days
- [x] Day 1: GitHub repo with README
- [x] Day 1: Progress log and decision log
- [ ] Day 1: Apply for the GitHub Student Developer Pack and other free credits *(you)*
- [x] Day 2: Browse the LoC St. Louis Sanborn volumes, starting with the 1904 World's Fair volume
- [x] Day 3: Save the sheet URLs for Vol. 12, 1938 and 1938–1950 (Carondelet)
- [x] Day 4: Read the Sanborn key; note symbols for gas stations, dry cleaners, factories
- [x] Day 5: Manually annotate 2 sheets *(5 drafts; need your check)*
- [x] Day 6: Script to download one sheet via loc.gov API
- [ ] Day 7: Run one tile through Tesseract and a free vision model; note what each got wrong. Don't spend money *(Tesseract done; vision model = Colab notebook)*
