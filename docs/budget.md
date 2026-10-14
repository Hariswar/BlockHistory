# Budget: about $10 for the whole year

Earlier versions planned $20–60, then $5–10 per month. The plan is now **about $10 for the year**: free tools do most of the work, and a small paid API credit covers only the tiles they can't read.

## Hard caps (enforced in code)
`blockhistory/costs.py` logs every paid call to `data/spend.jsonl` and refuses to make a call once either cap is reached:

| Cap | Default | Setting in `.env` |
|---|---|---|
| Per month | $3 | `BLOCKHISTORY_MONTHLY_CAP_USD` |
| Whole project | $10 | `BLOCKHISTORY_TOTAL_CAP_USD` |

Only Haiku 5.5 and Sonnet 5.5 have prices in the code, so an Opus call fails outright instead of costing money. Cached results are free and never logged.

## Where the money goes
| Item | Plan | Cost |
|---|---|---|
| First-pass map reading | Tesseract (laptop) + Qwen2.5-VL on Colab/Kaggle free GPU | $0 |
| Hard tiles | Claude Haiku 5.5, Batch API (50% off) | most of the ~$10 |
| Tiles Haiku is unsure about | Claude Sonnet 5.5, occasionally | small |
| Database | Supabase free tier | $0 |
| Frontend + hosting | Next.js + MapLibre + OpenStreetMap on Vercel / Cloudflare Pages free | $0 |
| Analytics | Umami (free) | $0 |
| Domain | Optional, end of year | $0–10 |

## Per-tile and per-sheet estimates
A tile is about 1,400 image tokens + ~800 prompt tokens in, and ~3,000 tokens out. Prices per million tokens (checked 2026-10-10): Haiku 5.5 $0.10 in / $0.50 out, Sonnet 5.5 $2 / $10; the Batch API halves both.

| Model (batch) | $/tile | $/sheet if every tile (20) is paid | $/sheet if ~30% go to paid (plan) |
|---|---|---|---|
| Haiku 5.5 | ~$0.0009 | ~$0.017 | **~$0.005** |
| Sonnet 5.5 | ~$0.017 | ~$0.34 | **~$0.10** |

The plan's per-sheet figures assume the free first pass handles about 70% of tiles. **That's unmeasured until weeks 4–7.** Process 10 real sheets first and check actual cost in the API dashboard and `data/spend.jsonl`.

## What this buys
| Job | Tiles | Haiku, every tile | Plan estimate |
|---|---|---|---|
| 1904 World's Fair test volume (21 map sheets) | 420 | ~$0.36 | Under $1 |
| Carondelet 1938 (74 sheets) | 1,480 | ~$1.30 | — |
| Carondelet 1938 + 1950 (147 sheets) | 2,940 | ~$2.60 | ~$4–6 with some Sonnet |
| + 1908 Vol. 8 Carondelet sheets (~60) | +1,200 | +~$1.00 | Phase 3, if budget allows |
| Evals and prompt testing (mostly Haiku) | | | ~$2–5 |

Even with no free first pass at all, Haiku on every tile fits the budget. Sonnet on every tile would not: ~$0.34/sheet is $50 for Carondelet's 147 sheets.

## Cost-control rules (from the plan)
1. Verifier: uncertain tiles only, free model first.
2. Change detection: compare saved text results, never re-read images.
3. Explainer: Haiku via Batch, never Sonnet (~$1 for all of Carondelet).
4. Evals: mostly the free model or Haiku; Sonnet only occasionally.
5. No live chat on the website.
6. Any service that asks for a card gets a spending cap or billing alert right away.
7. Apply for the GitHub Student Developer Pack and other free credits early.
