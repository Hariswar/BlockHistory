"""Contamination relevance of a map label, from the table in docs/sanborn-cheatsheet.md.

Keyword matching on the printed label and the reader's plain-English `use`. It decides
what a reviewer checks first; it is not a finding about any property.
"""

from __future__ import annotations

import re

HIGH = [
    r"FILL'?G|FILLING STA|F\.S\.|GAS(OL)?(INE)? (STA|STGE|TK)|GASOL",
    r"BULK OIL|OIL HO|OIL W\.? ?HO|OIL CO|FUEL OIL|OIL TK|OIL STA",
    r"GARAGE|AUTO REP|AUTO SALES|AUTO SERV|TRUCKS|USED AUTO",
    r"DRY CLEAN|CLEANING|DYE|BLEACH",
    r"FOUNDRY|CUPOLA|CASTING|BLAST FURN|PIG IRON|SMELT|MELTING",
    r"COKE|TAR |TAR$|BENZOL|NAPTHALINE|NAPHTHALENE|GASOMETER|GAS WKS|GAS PLANT|PURIF",
    r"GAS (PUMPING|PRODUCER|METER|PROCESSING)|TIN FOIL",
    r"BATTERY|CHEM(ICAL)?\.? (WKS|WORKS|CO)|SOLVENT|ACID|SULPHUR|SULFUR",
]
MEDIUM = [
    r"TIN SH|TIN SHOP|MACH(INE)? SH|BL\.? ?SM|BLACKSMITH|WELD|PLATING|METAL|IRON W(OR)?KS|STEEL W(OR)?KS",
    r"PAINT|\bPRINT(?!ED)|\bPRT'?G\b|\bSIGN\b|PHOTO|VARNISH",
    r"COAL|JUNK|WRECK|SCRAP",
    r"LUMBER|WOODW|SASH|PLANING",
    r"ICE (PLANT|MFG)|AMMONIA|SUB(STATION)?\b|ELEC\.? SUB|TRANSF",
    r"BOILER|BLR|ENG(INE)? (RM|HO)|LOCOMOTIVE|ROUNDHOUSE|QUARRY|POND",
    r"SHIP ?(BUILDING|YARD)|CONTRACTOR",
]
# Words that describe how a building is built, not what it was used for: "CONC. FL."
# (concrete floor), "BR. 7ST.", "IR. CL." (iron clad), "(ASB. CL.)" (asbestos siding),
# "SC. GL." (skylight glass), "IR. POSTS METAL LATH & PLASTER PARTNS.". A label made only of
# these (plus numbers, story counts and stray letters) is a construction note.
CONSTRUCTION = {
    "CONC", "CONCRETE", "FL", "FLR", "FLOOR", "BR", "BRK", "BRICK", "IR", "IRON", "CL", "CLAD",
    "ASB", "ASBESTOS", "SC", "GL", "GLASS", "POSTS", "POST", "LATH", "PLASTER", "PLASTE",
    "PARTNS", "PARTS", "PARTITIONS", "METAL", "STEEL", "COLS", "CDLS", "TRUSSES", "RF", "ROOF", "EARTH",
    "RAISED", "FR", "FRAME", "C", "B", "ST", "STS", "STORY", "STORIES", "ABV", "ABOVE", "HOLLOW",
    "TILE", "STONE", "SL", "CI", "FIRE", "PROOF", "FIREPROOF", "CONST", "CONSTN", "WALL", "WALLS",
    "WOOD", "BEAMS", "IST", "ISR", "JOIST", "JOISTS", "FLS", "CEILING", "CEILINGS", "CEILG", "SLAB",
    "EXCEPT", "EXPOSED", "APRON", "CURTAIN", "PILASTD", "PILASTERED", "CONSTR",
}  # fmt: skip
# "IST"/"ISR" are common misreads of "1ST"; "CI" of "CL".
# Map symbols and markers that readers sometimes report as uses: a lone dwelling (D), flat (F),
# store (S) or auto house (A) marker, and the automatic sprinkler symbol (AS).
MARKER = re.compile(r"\(?(A\.?\s?S|[DFSAE])[.'’)]*")
# A rear-address note pasted on a later edition ("R. 6016 LOUISIANA"), and the reader's own
# "(illegible)" for text it couldn't read: neither names a use.
ADDRESS_NOTE = re.compile(r"R\.?\s*\d+\s*[A-Z. ]*")
ILLEGIBLE = re.compile(r"ILLEGIBLE|UNREADABLE")
# A car count on a building that isn't a garage or auto business is a private auto house:
# "15 - CARS A.", "MISCL. STGE-2 A.-1ST.-3 CARS", "3 GARS." (a misread of CARS).
CAR_COUNT = re.compile(r"\b\d+\s*[-–]?\s*[CG]ARS?\b|\bA[.\-]?\s*[-–]?\s*\d*\s*CARS\b")
COMMERCIAL_GARAGE = re.compile(r"GARAGE|REP|SALES|SERV|FILL|TRUCK|AUTO STGE|CAP'?Y")
# "FR. FOUND'N" (a frame building on a foundation), often read as "FR. FOUNDRY".
FRAME_ON_FOUNDATION = re.compile(r"\bFR\.?\s*FOUND[A-Z'’]*\.?")


def construction_note(label: str) -> bool:
    words = re.findall(r"[A-Z]+", re.sub(r"\d+(ST|ND|RD|TH)\b", "", label.upper()))
    words = [w for w in words if len(w) > 1 or w in CONSTRUCTION]
    return bool(words) and all(w in CONSTRUCTION for w in words)


def relevance(label: str, use: str = "") -> str:
    # A bare "A" is a private auto house (a home garage), not a commercial garage.
    # So is a capacity note on one ("3 CARS", "A. 4-CARS", a bare "5").
    if re.fullmatch(r"\s*A\.?\s*", label) or re.fullmatch(
        r"(A\.?\s*)?(\w{1,2}[- ]?)?CARS?\.?(\s*A\.?)?|\d+", label.strip().upper()
    ):
        return "low"
    if (
        construction_note(label)
        or MARKER.fullmatch(label.strip().upper())
        or ADDRESS_NOTE.fullmatch(label.strip().upper())
        or ILLEGIBLE.search(label.upper())
    ):
        return "low"
    upper = label.upper()
    if CAR_COUNT.search(upper) and not COMMERCIAL_GARAGE.search(upper):
        return "low"
    if FRAME_ON_FOUNDATION.search(upper):
        upper = FRAME_ON_FOUNDATION.sub(" ", upper)
        use = re.sub(r"(?i)\bfoundry\b", "", use)
        if not re.search(r"[A-Z]{3}", upper):
            return "low"
    label = re.sub(r"PRIV(ATE|\.)? GARAGE", "", upper)
    text = f" {label} | {use} ".upper().replace("PRIVATE GARAGE", "").replace("AUTO HOUSE", "")
    # A capacity note in the description ("chapel with 4 cars garage") is a private garage.
    text = re.sub(r"\b\d+[- ]?CARS?\b( GARAGE)?", "", text)
    # "FR. FOUND." is a frame building on a foundation; readers sometimes call it a "frame
    # foundry" or add "(not a foundry)". Only a label that itself says FOUNDRY counts.
    if re.search(r"FOUND\b|FOUND'?N|FOUNDATION", label.upper()) and "FOUNDRY" not in label.upper():
        text = text.replace("FOUNDRY", "")
    if any(re.search(p, text) for p in HIGH):
        return "high"
    if any(re.search(p, text) for p in MEDIUM):
        return "medium"
    return "low"
