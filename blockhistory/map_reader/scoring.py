"""Rough matching of reader output against hand labels (the full eval comes in week 7).

A hand label counts as found when a reader produced one of its significant words: the
same word, or a 4+ letter fragment of it ("MACH" for "MACHS"). Short fragments and
generic company words are ignored because they match by accident.
"""

from __future__ import annotations

import re

# Words in many company names, so matching on them alone proves nothing (the first Colab
# run "found" SEMI-STEEL CASTING CO. MFG. because the ice plant's name also had MFG).
GENERIC_WORDS = {"MFG", "THE", "AND", "SUPPLY", "BLDG", "STGE", "STA", "STEEL", "PLANT"}


def norm(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def label_words(label: str) -> list[str]:
    """'GRINDING 1ST / DRYING 2 & 3RD' -> ['GRINDING', 'DRYING'] (3+ letters, not generic)."""
    words = (norm(t) for t in label.split())
    return [w for w in words if sum(c.isalpha() for c in w) >= 3 and w not in GENERIC_WORDS]


def is_found(hand_label: str, found_words: set[str]) -> bool:
    return any(
        w == f or (len(f) >= 4 and f in w) for w in label_words(hand_label) for f in found_words
    )


def tank_count(entry: dict) -> int:
    """Gas tanks for one hand-label entry: newer files use gasoline_tank_count, older a bool."""
    return int(entry.get("gasoline_tank_count", entry.get("has_gasoline_tank", False)))
