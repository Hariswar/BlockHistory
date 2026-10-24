# What the AI reading cost, and what it would have cost

Computed on 2026-10-24 from `data/spend.jsonl` (every API call is logged with its tokens):
6,415 calls, 20.5 M input and 2.2 M output tokens, covering 1938 and 1950 (46 sheets each,
three passes: reading, gas tanks, points) and the explanations. Prices from `blockhistory/costs.py`.

| Setup | Cost for the same work | |
|---|---|---|
| Sonnet 5.5, one call at a time | $63.51 | ████████████████████████████████████████ |
| Sonnet 5.5, Batch API | $31.76 | ████████████████████ |
| Haiku 5.5, one call at a time | $3.18 | ██ |
| **Haiku 5.5, Batch API (what we did)** | **$1.60** | █ |

What brought it down:
- **Model:** Haiku with low effort, chosen after `scripts/compare_models.py` showed it read the
  test tiles nearly as well as Sonnet (`docs/decision-log.md`). 20× cheaper.
- **Batch API:** half price, results within hours. 2× cheaper.
- **Targeted passes:** the gas-tank pass only re-reads tiles with a fuel or vehicle site (about
  1 tile in 4); the points pass only tiles with flagged listings; explanations once per distinct
  label (295 labels for 475 listings).
- **Caching:** every result is cached by image and prompt version, so re-running the pipeline,
  the evaluations and the accuracy check costs $0; only changed prompts are re-read.

Per sheet: about **$0.012** to read a sheet (1938/1950), and an estimated $0.016 for the
larger-scale 1908 sheets (48 sheets, $0.79 estimated).
