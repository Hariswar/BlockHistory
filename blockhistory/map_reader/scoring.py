"""Matching reader output against hand labels.

A hand label counts as found when a reader produced one of its significant words: the
same word, or a 4+ letter fragment of it ("MACH" for "MACHS"). Short fragments and
generic words are ignored because they match by accident. `match_sheet` then pairs each
finding with one hand-labeled site, using street numbers to tell same-named sites apart.
"""

from __future__ import annotations

import re

# Words in many company names, so matching on them alone proves nothing (the first Colab
# run "found" SEMI-STEEL CASTING CO. MFG. because the ice plant's name also had MFG).
# REP, SHOP, YARD, FOUND, ELEC and the rest were added in week 7: "FURNE REP." matched
# "AUTO REP.", and "FR. FOUND." (a frame building on a foundation) matched "FOUNDRY".
GENERIC_WORDS = {"MFG", "THE", "AND", "SUPPLY", "BLDG", "STGE", "STA", "STEEL", "PLANT"} | {
    "REP", "REPG", "SHOP", "YARD", "CONC", "NOT", "USED", "FACTY", "WORKS", "WKS", "FOUND",
    "ELEC",
}  # fmt: skip


def norm(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


# Abbreviations whose parts are too short to match on their own, and spelling variants.
SPELLINGS = [(r"\bBL\.?\s*SM\b\.?", "BLACKSMITH"), (r"NAPHTH", "NAPTH")]


def label_words(label: str) -> list[str]:
    """'GRINDING 1ST / DRYING 2 & 3RD' -> ['GRINDING', 'DRYING'] (3+ letters, not generic)."""
    label = label.upper()
    for pattern, repl in SPELLINGS:
        label = re.sub(pattern, repl, label)
    words = (norm(t) for t in label.split())
    return [w for w in words if sum(c.isalpha() for c in w) >= 3 and w not in GENERIC_WORDS]


def is_found(hand_label: str, found_words: set[str]) -> bool:
    return any(
        w == f or (len(f) >= 4 and f in w) for w in label_words(hand_label) for f in found_words
    )


def tank_count(entry: dict) -> int:
    """Gas tanks for one hand-label entry: newer files use gasoline_tank_count, older a bool."""
    return int(entry.get("gasoline_tank_count", entry.get("has_gasoline_tank", False)))


def numbers(text: str | None) -> set[int]:
    """'6226-24' -> {6226, 6224}; '7012 (lot)' -> {7012}; '6820-6830; 6900-6902' -> 4 numbers."""
    out: set[int] = set()
    for a, b in re.findall(r"(\d{2,})(?:\s*-\s*(\d+))?", text or ""):
        out.add(int(a))
        if b:
            out.add(int(a[: len(a) - len(b)] + b))
    return out


def same_address(finding: dict, hand: dict) -> bool | None:
    """True/False when both have street numbers; None when either is missing."""
    f, h = numbers(finding.get("street_number")), numbers(hand.get("street_number"))
    if not f or not h:
        return None
    return bool(f & h) or any(min(h) <= n <= max(h) for n in f)


def address_level(finding: dict, hand: dict) -> int:
    """3 same number, 2 one digit off (sheet 57: '2432' for 7432), 1 unknown, 0 different."""
    same = same_address(finding, hand)
    if same is None:
        return 1
    if same:
        return 3
    f, h = numbers(finding.get("street_number")), numbers(hand.get("street_number"))
    for a in map(str, f):
        for b in map(str, h):
            if len(a) == len(b) and sum(x != y for x, y in zip(a, b)) == 1:
                return 2
    return 0


def match_sheet(findings: list[dict], hand: list[dict]) -> list[int | None]:
    """Index of the hand entry each finding describes, or None.

    A finding can match a hand entry when one of the entry's words is in the finding's
    label (not its use: a reader that calls "FR. FOUND." a foundry must not score). Pairs
    are then taken best first, one finding per entry: a matching street number (or one a
    digit off, a common misread), then the
    most shared words ("GAS METER HO." is the gas meter house, not the gas producer house),
    then no contradicting number, then the larger share of the entry's words. So a sheet
    with four FILL'G STA. needs four filling-station findings to score four, and a finding
    never claims an entry that shares fewer words than its best one ("9 COKE OVENS" is a
    second read of the coke ovens, not the coke pile). Findings left over join their best
    entry as duplicates, unless their street number contradicts it.
    """
    words = [set(label_words(f["label"])) for f in findings]
    out: list[int | None] = [None] * len(findings)
    pairs = []
    for k, f in enumerate(findings):
        for i, h in enumerate(hand):
            if not is_found(h["label"], words[k]):
                continue
            hw = label_words(h["label"])
            n = sum(is_found(w, words[k]) for w in hw)
            address = address_level(f, h)
            pairs.append(((address if address >= 2 else 0, n, address, n / len(hw)), k, i))
    pairs.sort(key=lambda p: p[0], reverse=True)
    # A finding whose number matches some entry is that entry or a duplicate of it, never
    # a different site with a contradicting number. Other contradictions are allowed:
    # readers often give the side-street number (bulk oil station "100" for 6800).
    has_match = {k for (rank, *_), k, _ in pairs if rank}
    best = {}  # most words a finding shares with any entry
    for (_, n, _, _), k, _ in pairs:
        best[k] = max(best.get(k, 0), n)
    claimed: set[int] = set()
    for (_, n, address, _), k, i in pairs:  # one-to-one, best pairs first
        if (
            out[k] is None
            and i not in claimed
            and n == best[k]
            and not (address == 0 and k in has_match)
        ):
            out[k] = i
            claimed.add(i)
    for (_, _, address, _), k, i in pairs:  # leftovers: duplicates of a site already found
        if out[k] is None and address:
            out[k] = i
    return out
