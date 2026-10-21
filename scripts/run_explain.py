"""AI-written explanations for the shown listings (Claude Haiku, Batch API, half price).

    python scripts/run_explain.py submit            # one request per distinct label shown
    python scripts/run_explain.py collect <batch_id> [--wait]
    python scripts/run_explain.py apply             # put passing texts into the database
    python scripts/run_explain.py report            # how many passed, and why others didn't

Only high/medium listings get one. Texts that fail the safety checks in
blockhistory/explain_ai.py keep the reviewed template. build_db.py uses passing texts too.
"""

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

from blockhistory import costs, explain_ai
from blockhistory.db import store
from blockhistory.map_reader import batch

SHOWN = "relevance IN ('high', 'medium') AND review_status != 'checked_wrong'"


def shown_rows(con) -> list[dict]:
    return [dict(r) for r in con.execute(f"SELECT * FROM findings WHERE {SHOWN}")]


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("submit")
    c = sub.add_parser("collect")
    c.add_argument("batch_id")
    c.add_argument("--wait", action="store_true")
    sub.add_parser("apply")
    sub.add_parser("report")
    args = parser.parse_args()
    con = store.connect()

    if args.cmd == "submit":
        items = sorted({explain_ai.input_file(r) for r in shown_rows(con)})
        model, _ = explain_ai.resolve()
        print(
            f"{len(items)} distinct labels; est. ${batch.estimate_usd(len(items), model, explain_ai):.3f}"
        )
        m = batch.submit(items, reader=explain_ai)
        print(f"submitted {m.get('batch_id')} ({m['submitted']} new, {m['already_cached']} cached)")
    elif args.cmd == "collect":
        while args.wait and batch.status(args.batch_id).processing_status != "ended":
            time.sleep(30)
        print(batch.collect(args.batch_id))
        print(f"project ${costs.total_spend():.3f} of ${costs.total_cap():.2f}")
    elif args.cmd == "apply":
        n = Counter()
        for r in shown_rows(con):
            text, source = explain_ai.explanation(r, r["edition"])
            con.execute("UPDATE findings SET explanation = ? WHERE id = ?", (text, r["id"]))
            n[source] += 1
        con.commit()
        print(dict(n))
    else:
        why = Counter()
        for r in shown_rows(con):
            f = explain_ai.facts(r)
            item = explain_ai.INPUT_DIR / f"{explain_ai._key(f)}.json"
            path = explain_ai.cache_path(item, *explain_ai.resolve()) if item.exists() else None
            if not path or not path.exists():
                why["not written yet"] += 1
                continue
            problem = explain_ai.check(json.loads(path.read_text())["text"], f)
            why[problem.split(":")[0].split("'")[0].strip() if problem else "passes"] += 1
        print(dict(why))


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
