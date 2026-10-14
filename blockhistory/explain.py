"""Plain-language notes for a finding, following the safety rules in docs/plan.md.

Rules: never say a property "is contaminated"; say what the map shows, the year, and that
this kind of business sometimes left contamination; always say it is historical use, not
a test result. Text is written from fixed templates, not by a model, so every sentence a
visitor reads has been reviewed once here.
"""

from __future__ import annotations

import re

# (category, pattern on label + use, why it matters). First match wins, so order matters:
# a "GASOL. ENG." in a coal yard is a fuel site before it is a coal site.
CATEGORIES = [
    (
        "fuel",
        r"FILL'?G|FILLING|GASOL|GAS(OLINE)? (STA|TK|STGE)|BULK OIL|OIL HO|OIL W\.? ?HO|OIL TK|FUEL",
        (
            "Filling stations and fuel storage often had buried gasoline tanks, which sometimes "
            "leaked petroleum into the soil and groundwater."
        ),
    ),
    (
        "dry cleaning",
        r"DRY CLEAN|CLEANING|DYE|BLEACH",
        (
            "Dry cleaners and dye works used solvents that can stay in soil and groundwater for "
            "decades."
        ),
    ),
    (
        "gas and coke works",
        r"COKE|BENZOL|TAR\b|NAPH|NAPTH|GASOMETER|GAS (PRODUCER|PUMPING|METER|WKS|WORKS|PLANT)|PURIF",
        (
            "Plants that made gas or coke from coal often left tar and other coal by-products in "
            "the ground."
        ),
    ),
    (
        "auto",
        r"AUTO|GARAGE|TRUCK|BATTERY|SERVICE",
        (
            "Auto repair shops and garages used oils and solvents and sometimes had fuel tanks; "
            "spills could reach the soil."
        ),
    ),
    (
        "metal",
        (
            r"FOUNDRY|CUPOLA|CASTING|SMELT|MELTING|BLAST FURN|PIG IRON|IRON W|STEEL W|TIN SH|"
            r"TIN FOIL|MACH|BL\.? ?SM|BLACKSMITH|WELD|PLATING|METAL|IRON"
        ),
        "Foundries and metal shops could leave metals such as lead, and foundry sand, in the soil.",
    ),
    (
        "chemicals, paint and printing",
        r"CHEM|SULPHUR|SULFUR|ACID|SOLVENT|PAINT|VARNISH|PRINT|PRTG|SIGN",
        (
            "Chemical, paint and printing businesses used solvents, inks and pigments, some of "
            "which contained lead."
        ),
    ),
    (
        "junk and wrecking",
        r"JUNK|WRECK|SCRAP",
        "Junk and wrecking yards could leave oil, battery acid and metals in the soil.",
    ),
    (
        "coal yard",
        r"COAL",
        "Coal yards could leave coal ash and cinders, which can contain metals.",
    ),
    (
        "lumber and woodworking",
        r"LUMBER|LBR|WOOD|SASH|PLANING|CARPR",
        "Lumber yards and woodworking shops sometimes used wood preservatives and finishes.",
    ),
    (
        "power and rail",
        r"ELEC|SUB-?STA|TRANSF|LOCOMOTIVE|ROUNDHOUSE|BOILER|BLR|ENG(INE)? (RM|HO)",
        (
            "Power equipment and rail shops sometimes used oils, including some that contained "
            "PCBs in later years."
        ),
    ),
]
OTHER = (
    "industrial",
    "Industrial sites sometimes handled fuels or chemicals; the map alone doesn't say which.",
)


def category(label: str, use: str = "", tanks: int = 0) -> tuple[str, str]:
    """(category, why it matters) from the label and use; drawn tanks make a site "fuel"
    only when nothing more specific matches."""
    text = f"{label} | {use}".upper()
    for name, pattern, why in CATEGORIES:
        if re.search(pattern, text):
            return name, why
    if tanks:
        return CATEGORIES[0][0], CATEGORIES[0][2]
    return OTHER


def explanation(finding: dict, year: str) -> str:
    """Two to four sentences for one finding, quoting the label as printed."""
    use = re.sub(r"\s*\(.*?\)", "", (finding.get("use") or "").split(";")[0]).strip()
    label = finding["label"].strip()
    tanks = finding.get("gasoline_tank_count", 0)
    name, why = category(label, finding.get("use", ""), tanks)
    seen = f"“{label}” ({use})" if use and use.lower() != label.lower() else f"“{label}”"
    parts = [f"The {year} Sanborn fire insurance map labels this site {seen}.", why]
    if tanks:
        parts.append(
            "The map also draws gasoline tanks here."
            if name == "fuel"
            else "The map also draws gasoline tanks here; buried tanks sometimes leaked "
            "petroleum into the soil."
        )
    parts.append("This is a historical use, not a test result.")
    return " ".join(parts)
