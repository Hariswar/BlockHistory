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
    r"BATTERY|CHEM(ICAL)? (WKS|WORKS|CO)|SOLVENT|ACID",
]
MEDIUM = [
    r"TIN SH|TIN SHOP|MACH(INE)? SH|BL\.? ?SM|BLACKSMITH|WELD|PLATING|METAL|IRON W(OR)?KS|STEEL W(OR)?KS",
    r"PAINT|PRINT|SIGN|PHOTO|VARNISH",
    r"COAL|JUNK|WRECK|SCRAP",
    r"LUMBER|WOODW|SASH|PLANING",
    r"ICE (PLANT|MFG)|AMMONIA|SUB(STATION)?\b|ELEC\.? SUB|TRANSF",
    r"BOILER|BLR|ENG(INE)? (RM|HO)|LOCOMOTIVE|ROUNDHOUSE|QUARRY|POND",
]


def relevance(label: str, use: str = "") -> str:
    # A bare "A" is a private auto house (a home garage), not a commercial garage.
    if re.fullmatch(r"\s*A\.?\s*", label):
        return "low"
    text = f" {label} | {use} ".upper().replace("PRIVATE GARAGE", "").replace("AUTO HOUSE", "")
    # "FR. FOUND." is a frame building on a foundation; readers sometimes call it a "frame
    # foundry" or add "(not a foundry)". Only a label that itself says FOUNDRY counts.
    if re.search(r"FOUND\b|FOUND'?N|FOUNDATION", label.upper()) and "FOUNDRY" not in label.upper():
        text = text.replace("FOUNDRY", "")
    if any(re.search(p, text) for p in HIGH):
        return "high"
    if any(re.search(p, text) for p in MEDIUM):
        return "medium"
    return "low"
