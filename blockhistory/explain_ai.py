"""AI-written explanations of what a mapped business was, inside fixed safety framing.

The templates in explain.py give every fuel site the same sentence. This module asks Claude
Haiku (Batch API) for one or two sentences about the specific printed label ("BENZOL PLANT",
"PAINT SPRAYING & BENZOL WASHING", "CUPOLA") in plain words: what that kind of business or
structure did and why such places can matter for soil or groundwater. The model writes only
that middle part. explanation() wraps it in the same opening (the year and the label as
printed) and closing ("historical use, not a test result") as the templates, so the safety
rules don't depend on the model.

Every AI text is checked (check()) and the template is used instead when it fails: no
claims that a place is or was contaminated, no health effects, no "you", nothing about the
present day, no numbers that aren't in the facts, and a length limit. Results are cached by
the facts they were written from, so a rebuild never pays twice.

Items go through blockhistory.map_reader.batch as small JSON fact files (one per distinct
label), which stand in for the image tiles the other readers send.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from pydantic import BaseModel, Field

from blockhistory import costs
from blockhistory.explain import category
from blockhistory.explain import explanation as template_explanation

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "data" / "cache" / "explainer"
INPUT_DIR = ROOT / "data" / "cache" / "explainer_inputs"
DEFAULT_MODEL = "claude-haiku-5-5"
DEFAULT_EFFORT = "low"
PROMPT_VERSION = "e1"
MAX_TOKENS = 600
EST_TOKENS = (700, 120)
MAX_CHARS = 420

SYSTEM_PROMPT = """\
You write one short part of a note on a public website about past land uses. Neighbors \
type an address and see businesses printed on 1938 and 1950 Sanborn fire insurance maps \
of their block, with a note on why that kind of place can matter for soil or groundwater.

You get one map label as printed (often abbreviated, like "FILL'G STA." or "BL. SM."), a \
reader's guess at what it means, and a reviewed general sentence for its category. Write \
1 or 2 plain sentences (at most 60 words) that:
- say what this kind of business, room or structure was and did, decoding the label;
- say in general terms what materials such places handled and how they could reach soil \
or groundwater, using "could", "sometimes" or "often".

Rules (the website rejects text that breaks them):
- Describe the kind of place in general. Never say this site, this property or this \
building is or was contaminated, polluted, leaking or unsafe, and never describe health \
effects, illness or danger to people.
- Don't address the reader ("you"), give advice, or say anything about today or the present.
- No dates, years, numbers, names of people or companies, unless they appear in the label.
- Don't repeat the label or the year (the website shows them), and don't say "Sanborn".
- If the label is unclear, explain the reader's guess cautiously ("likely", "probably").
"""


class Explanation(BaseModel):
    text: str = Field(description="1-2 sentences, at most 60 words")


SCHEMA = Explanation

FORBIDDEN = re.compile(
    r"\b(contaminat\w*|pollut\w*|toxic\w*|poison\w*|danger\w*|unsafe|hazard\w*|cancer\w*|"
    r"carcinogen\w*|health|ill(ness)?|disease\w*|sick\w*|death|died|you|your|should|must|"
    r"today|currently|now|still|present-day|sanborn)\b",
    re.IGNORECASE,
)


def facts(finding: dict) -> dict:
    """What the explanation may be written from (and is cached by)."""
    name, why = category(finding["label"], finding.get("use", ""), 0)
    return {
        "label": finding["label"].strip(),
        "reader_guess": re.sub(r"\s*\(.*?\)", "", (finding.get("use") or "")).strip(),
        "category": name,
        "category_sentence": why,
    }


def _key(f: dict) -> str:
    return hashlib.sha256(json.dumps(f, sort_keys=True).encode()).hexdigest()[:32]


def input_file(finding: dict) -> Path:
    """The fact file the batch sends for this finding (written once)."""
    f = facts(finding)
    path = INPUT_DIR / f"{_key(f)}.json"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(f, indent=1) + "\n")
    return path


# --- the reader interface blockhistory/map_reader/batch.py expects ---


def resolve(model: str | None = None, effort: str | None = None) -> tuple[str, str]:
    return model or DEFAULT_MODEL, effort or DEFAULT_EFFORT


def cache_path(item: Path, model: str, effort: str) -> Path:
    h = hashlib.sha256(f"explain|{model}|{effort}|{PROMPT_VERSION}|".encode())
    h.update(item.read_bytes())
    return CACHE_DIR / f"{h.hexdigest()[:32]}.json"


def request_messages(item: Path) -> list[dict]:
    f = json.loads(item.read_text())
    return [
        {
            "role": "user",
            "content": (
                f"Label as printed: {f['label']}\n"
                f"Reader's guess at its meaning: {f['reader_guess'] or 'none'}\n"
                f"Reviewed category sentence: {f['category_sentence']}"
            ),
        }
    ]


def save_result(
    item: Path,
    model: str,
    effort: str,
    served_model: str,
    input_tokens: int,
    output_tokens: int,
    reading: Explanation,
    batch: bool = False,
) -> dict:
    usd = costs.record(model, input_tokens, output_tokens, what=f"explain {item.stem}", batch=batch)
    result = {
        "item": item.name,
        "model": served_model,
        "effort": effort,
        "prompt_version": PROMPT_VERSION,
        "batch": batch,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        "usd": round(usd, 6),
        "facts": json.loads(item.read_text()),
        "text": reading.text.strip(),
    }
    path = cache_path(item, model, effort)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")
    return result


# --- using the results ---


def check(text: str, f: dict) -> str | None:
    """Why the AI text can't be shown, or None if it passes."""
    t = " ".join(text.split())
    if not t:
        return "empty"
    if len(t) > MAX_CHARS:
        return "too long"
    # A sentence ends after a lowercase word; "W. HO." or "G.T.S." are abbreviations.
    if len(re.findall(r"[a-z]{2,}[.!?](\s|$)", t)) > 2:
        return "more than 2 sentences"
    if m := FORBIDDEN.search(t):
        return f"uses {m.group(0)!r}"
    allowed = set(re.findall(r"\d+", f["label"]))
    if extra := [n for n in re.findall(r"\d+", t) if n not in allowed]:
        return f"number not in the facts: {extra[0]}"
    if not t.endswith((".", "!")):
        return "unfinished sentence"
    return None


def ai_text(finding: dict, model: str | None = None) -> str | None:
    """The cached AI text for this finding if it passes check(), else None."""
    f = facts(finding)
    item = INPUT_DIR / f"{_key(f)}.json"
    if not item.exists():
        return None
    path = cache_path(item, *resolve(model))
    if not path.exists():
        return None
    text = " ".join(json.loads(path.read_text())["text"].split())
    return text if check(text, f) is None else None


def explanation(finding: dict, year: str) -> tuple[str, str]:
    """(text, source): the AI middle in the template's framing, or the template itself."""
    middle = ai_text(finding)
    template = template_explanation(finding, year)
    if middle is None:
        return template, "template"
    _, why = category(
        finding["label"], finding.get("use", ""), finding.get("gasoline_tank_count", 0)
    )
    # Swap the category sentence for the AI's; keep the opening, tank and closing sentences.
    return template.replace(why, middle, 1), "ai"
