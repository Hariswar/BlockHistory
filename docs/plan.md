# BlockHistory: Year-Long Build Plan

Oct 5, 2026

## Success after 12 months
- 3–5 cities fully covered, address-searchable
- Published accuracy number for the map-reading agents, backed by a hand-labeled test set
- Real users and at least one partner organization
- A public write-up of how it was built and what was learned

## Tech stack
| Layer | Choice |
|---|---|
| Agent code | Python + agent framework (Claude Agent SDK, LangGraph, or plain tool-calling loops) |
| Vision / LLM | Frontier vision model for map reading; small cheap model for routine text |
| Image processing | OpenCV, Pillow, rasterio |
| Geospatial | GDAL, PostGIS, GeoPandas |
| Database | PostgreSQL + PostGIS (Supabase or Neon free tier) |
| Job orchestration | Celery or Prefect |
| Frontend | Next.js + MapLibre GL |
| Hosting | Vercel (frontend) + small VM / Railway / Fly.io (agents) |
| Evals & tracing | Langfuse or logging table + labeled test set |

Budget: ~$20–60/month. Cache every model result so no tile is processed twice.

## Data sources
- Sanborn maps: Library of Congress (loc.gov JSON API)
- Historical city directories: local libraries / Internet Archive
- Contamination records: EPA Envirofacts / Cleanups in My Community, state LUST database
- Modern addresses/parcels: county open GIS parcel data
- Historical aerials (later): USGS EarthExplorer

## Phase 1 (Months 1–3): Foundation and first launch
Goal: public site to search addresses in one neighborhood, one map year.

| Week | Focus | Done when |
|---|---|---|
| 1 | Pick area (own city, 2+ map years, ~20–40 sheets) | List of sheet URLs for one neighborhood |
| 2 | Learn the map key; annotate 5 sheets | One-page cheat sheet |
| 3 | Download + tiling pipeline | 40 sheets downloaded and tiled automatically |
| 4–5 | Map-reading agent v1 | Labels extracted from 10 sheets, spot-checked |
| 6 | Ground-truth set: hand-label 3 sheets | Labeled JSON to score against |
| 7 | First accuracy score (precision/recall) | Baseline number |
| 8–9 | Georeferencing (QGIS manual, then automate) | Features have lat/lon |
| 10 | Load into PostGIS; 100 m query | Query returns results for a real address |
| 11 | Website v1: search, map, list with sheet links | Works locally |
| 12 | Launch + About & limitations page | Public URL, first 25 strangers |

## Phase 2 (Months 4–6): Accuracy and full agent pipeline
| Month | Focus | Done when |
|---|---|---|
| 4 | More map years + time slider | Users scrub earliest → latest |
| 4 | Verifier agent | Eval accuracy improves over baseline |
| 5 | Directory agent | Second evidence source per address |
| 5 | Cross-check agent (EPA + LUST) | Every flagged site has a confidence level |
| 6 | Explainer agent (follows safety rules) | Every summary links to sources |
| 6 | Eval suite: 15+ sheets, auto-run on changes | One command prints accuracy, cost, time per sheet |

Checkpoint: whole city searchable, published accuracy, known cost per sheet, blog post.

## Phase 3 (Months 7–9): Scale and grow users
| Month | Focus | Done when |
|---|---|---|
| 7 | Cities as config, not code | New city takes days, not weeks |
| 7–8 | Add 2–4 cities (varied regions) | Per-city accuracy score |
| 8 | Cost optimization (routing, caching, batching) | Before/after cost chart |
| 8 | Engagement: shareable pages, street history, satellite slider | People share links unprompted |
| 9 | Community corrections → review queue | First corrections from strangers |
| 9 | Outreach (library, historical society, university, gardens) | One org agrees to try/link |

## Phase 4 (Months 10–12): Polish, partnerships, packaging
| Month | Focus | Done when |
|---|---|---|
| 10 | Reliability: monitoring, alerts, weekly evals, status page | Runs a month untouched |
| 10 | Accessibility & mobile | Lighthouse a11y 90+ |
| 11 | Public accuracy dashboard | Anyone can see trustworthiness |
| 11 | Formal partnership + quote | Named org using BlockHistory |
| 12 | Technical write-up | Published and linked |
| 12 | Resume packaging: demo video, README, bullets | Explain from memory |

## Explainer agent rules
1. Never say a property "is contaminated." Say "historical records show a [use] here in [year], a type of business that sometimes left soil contamination."
2. Always cite the source sheet or directory page.
3. Always show a confidence level and say when a finding is unreviewed.
4. Always end with a practical next step (soil test, state environmental agency, local health department).
5. Separate "confirmed in an official contamination database" from "historical land use only."

Other safeguards: About & limitations page, not-an-ESA disclaimer, easy error reporting, no personal data about owners/residents, professor review of wording (~month 5).

## Risks and fallbacks
| Risk | Fallback |
|---|---|
| Faded/handwritten labels | Printed labels + color codes first; hard tiles to review queue |
| Georeferencing slow | Start with already-georeferenced Sanborn layers; manual GCPs for one area |
| Directories not digitized | Ship maps + EPA only |
| API costs grow | Cache, cheaper models for easy tiles, research credits |
| Few users | Partners + "interesting finds" posts |

## Metrics to track from month 1
Sheets processed · precision/recall · verifier accuracy gain · cost per sheet · cities & map years · monthly visitors/searches (Plausible/Umami) · user corrections · partner orgs

## First 7 days
- [x] Day 1: GitHub repo with README mission
- [x] Day 1: Progress log and decision log
- [ ] Day 2: Confirm your city has 2+ map years in the LoC Sanborn collection
- [ ] Day 3: Pick one neighborhood, save its sheet URLs
- [ ] Day 4: Read the Sanborn key; note symbols for gas stations, dry cleaners, factories
- [ ] Day 5: Manually annotate 2 sheets
- [ ] Day 6: Script to download one sheet via loc.gov API
- [ ] Day 7: Send one tile to a vision model; note what it got wrong
