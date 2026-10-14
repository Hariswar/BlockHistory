# Free First-Pass Readers

**Status (Oct 12):** Day 7 showed the free vision model isn't usable as set up. Claude Haiku 5.5 is now the main reader (9 of 10 labels and 3 of 3 gas-tank sites on the test tiles, ~$0.001 per tile). Tesseract stays as a free cross-check. See `docs/decision-log.md`.

| Reader | Code | Runs on | Good at | Bad at |
|---|---|---|---|---|
| Tesseract OCR | `blockhistory/map_reader/ocr.py` | This laptop (`brew install tesseract`) | Printed business names on 1938 maps (FILL'G STA., BULK OIL, VINEGAR, WRECKING): 16 of 24 hand labels on 5 test tiles | **Never finds G.T. (gas tank) symbols**; misses short labels (TIN SHOP, OIL HO., CHEM. LAB), diagonal text, and 1903-style hand lettering (4 of 21 on The Hill); picks up the LoC stamp as text |
| Qwen2.5-VL via Ollama | `blockhistory/map_reader/free_vision.py` | Colab / Kaggle free GPU (`qwen2.5vl:7b`), or a laptop with 8 GB+ RAM (`qwen2.5vl:3b`) | Big printed company names (ice plant, vinegar works, wrecking co.): 3 of 10 hand labels on 3 test tiles | **Missed every filling station, bulk oil station and oil house; marked 1 of 3 gas-tank sites, wrongly.** Gets stuck repeating entries until the output limit (33–42 repeats per tile); uses block numbers as addresses; lists street names and use codes as buildings; 145–163 s per tile on a T4 |

Both use the same JSON schema and prompt as the paid reader (`extract.py`), so all three can be scored against the same hand labels.

## Run Tesseract (local, free)
```
.venv/bin/python scripts/free_read_tile.py data/tiles/carondelet/1938/04858_12_1938-0053/04858_12_1938-0053_r2_c1.jpg
```
It prints the words found and which hand-labeled buildings in that tile it found or missed.

## Run the vision model on Colab (free GPU)
1. Push the repo to GitHub (Colab clones it).
2. Open `notebooks/day7_free_vision_colab.ipynb` in Colab (File → Open notebook → GitHub, or upload it).
3. Runtime → Change runtime type → **T4 GPU**, then Runtime → Run all. It takes about 10 minutes, mostly the 6 GB model download.
4. The last cell downloads `free_vision_results.zip`. Unzip it into `data/cache/` on the laptop so the results are reused for free.

Kaggle notebooks work the same way (Settings → Accelerator → GPU T4; 30 free GPU hours a week).

## Run the vision model somewhere else
Point `OLLAMA_HOST` at any Ollama server and choose the model:
```
OLLAMA_HOST=http://localhost:11434 BLOCKHISTORY_FREE_MODEL=qwen2.5vl:3b \
  .venv/bin/python scripts/free_read_tile.py <tile> --vision
```
On this laptop, `qwen2.5vl:3b` needs about 3.2 GB of disk and runs slowly in 8 GB of RAM.
