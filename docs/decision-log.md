# Decision Log

Format: **Date — Decision.** Chose X over Y because… (What would make us revisit?)

- **2026-10-10 — Python for the agent/pipeline code.** Python owns the geospatial (GDAL, GeoPandas, rasterio) and image (OpenCV, Pillow) libraries.
- **2026-10-10 — Study area is all of Rolla, MO, not one neighborhood.** Each Rolla edition is only 1–9 sheets, so the whole mapped town across 1924 + 1933 + 1948 is 21 sheets, inside the plan's 20–40 target. It's also local, so I can walk to sites to check them. (Revisit if Phase 2 needs more sheets per year than Rolla has; then add a bigger Missouri city like Springfield.)
- **2026-10-10 — 1948 is the Phase 1 map year.** It's the latest edition and covers the peak of the gas-station and dry-cleaner era. Caveat: it's the 1933 sheets with 1942–48 paste-over corrections, so a single sheet mixes dates.
- **2026-10-10 — Download through IIIF at 50% scale, not the master TIFF/JP2.** About 1 MB vs 150 MB per sheet, and labels are still legible in 1024px tiles at that scale. (Revisit if the eval shows misreads on small text; then try `--pct 100`.)
- **2026-10-10 — Tiles are 1024px with ≥128px overlap, evenly spaced.** 1024px stays under the vision model's downscale threshold. Overlap means every label is whole in at least one tile; duplicates get merged later by position.
- **2026-10-10 — The map reader uses structured outputs (Pydantic schema) and a disk cache keyed on model + prompt version + tile bytes.** The schema makes output scoreable against hand labels with no parsing heuristics. The cache enforces "never pay for the same tile twice." Bump `PROMPT_VERSION` on any prompt change.
- **2026-10-10 — Start with the plain Anthropic SDK, not an agent framework.** One tile in, JSON out is a single call, not an agent loop. Add a framework when the verifier/review-queue loop actually needs one (Phase 2).
