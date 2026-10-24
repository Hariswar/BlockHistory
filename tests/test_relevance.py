import pytest

from blockhistory.map_reader.relevance import construction_note, relevance


@pytest.mark.parametrize(
    "label, use, expected",
    [
        ("FILL'G STA.", "filling station", "high"),
        ("ST. LOUIS SULPHUR & CHEM. CO.", "chemical works", "high"),
        ("PRTG. & BINDING", "printing and binding", "medium"),
        ("ST. LOUIS SHIP BUILDING & STEEL CO.", "shipyard", "medium"),
        # Not uses: these used to be flagged high or medium.
        ("3-CARS", "auto house, 3 cars (footprint labeled A)", "low"),
        ("A. A-CARS", "auto house (garage) for 4 cars", "low"),
        ("3 CARS", "garage for three cars", "low"),
        ("5", "auto repair or garage", "low"),
        ("PRIV. GARAGE CAPY 12 CARS CONC. FL.", "private garage, 12 cars", "low"),
        ("FR. FOUND.", "frame foundry", "low"),
        # A truck garage is a fleet garage, not a home garage.
        ("PRIV. GARAGE", "private garage (capacity 10 trucks)", "high"),
        # Construction notes read as uses.
        ("ASB. CL.", "asbestos clothing or cleaning-related note on dwelling", "low"),
        ("(ASB. CL.)", "asbestos cleaning (as printed)", "low"),
        ("CONC.", "concrete (construction note on garage footprint)", "low"),
        ("CONC. FL. 12' 8'", "concrete-floor building (part of filling station)", "low"),
        ("BR. 7ST.", "brick story-marking note on Junk building", "low"),
        ("IR. CL. 3", "iron clad building", "low"),
        ("SC. GL. 3'", "skylight/glass sign note", "low"),
        ("BR. IR. CDLS.", "brick and iron building, possibly castings", "low"),
        ("IR. POSTS METAL LATH & PLASTER PARTNS.", "iron posts; metal lath and plaster", "low"),
        ("STEEL C... METAL L... PLASTE...", "partially visible plant or shop", "low"),
        ("METAL LATH & PLASTER PARTS", "metal lath and plaster partitions", "low"),
        ("UNDERTAKER CHAPEL", "undertaker chapel with 4 cars garage, cinder block", "low"),
        ("3 CARS A.", "garage (3 cars, auto house)", "low"),
        # ...without hiding real uses that share those words.
        # Map markers, car counts, FR. FOUND'N.
        ("D'", "dwelling", "low"),
        ("AS", "automatic sprinkler", "low"),
        ("15 - CARS A.", "private garage", "low"),
        ("3 GARS.", "garage for three cars", "low"),
        ("MISCL. STGE-2 A.-1ST.-3 CARS", "storage with auto house", "low"),
        ("FR. FOUNDRY", "frame foundry", "low"),
        ("FR. FOUND. TIN SHOP", "tin shop", "medium"),
        ("SL.CI. 2N.Y.", "slate clad 2nd", "low"),
        ("FIRE PROOF CONST. CONC. FL. & RF. BR. WALLS", "fireproof construction", "low"),
        ("WOOD FL.", "construction note", "low"),
        ("R6016 LOUISIANA", "rear address", "low"),
        ("2 Sto.. O.S.Ex. (illegible)", "garage", "low"),
        ("STEEL JOIST CONSTR'N CONC. FL'S. & R.F.", "construction", "low"),
        ("E", "flat", "low"),
        # ...but real garages and plants stay.
        ("GARAGE CAP'Y. 20 CARS", "garage, capacity 20 cars", "high"),
        ("AUTO STGE. 1ST CAPY 16 CARS", "auto storage garage", "high"),
        ("FOUNDRY", "foundry", "high"),
        ("STEEL CASTING CO.", "steel foundry", "high"),
        ("METAL MIX", "metal melting plant", "high"),
        ("IRON WORKS", "structural iron works", "medium"),
        ("FILLG STA CONC FL", "filling station", "high"),
        ("GARAGE", "garage, capacity 20 cars", "high"),
    ],
)
def test_relevance(label, use, expected):
    assert relevance(label, use) == expected


def test_construction_note_needs_every_word_to_be_construction():
    assert construction_note("METAL LATH & PLASTER PARTS")
    assert not construction_note("AUTO PARTS")
    assert not construction_note("STEEL CASTING CO.")
