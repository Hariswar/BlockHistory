import pytest

from blockhistory.map_reader.relevance import relevance


@pytest.mark.parametrize(
    "label, use, expected",
    [
        ("FILL'G STA.", "filling station", "high"),
        ("ST. LOUIS SULPHUR & CHEM. CO.", "chemical works", "high"),
        ("PRTG. & BINDING", "printing and binding", "medium"),
        ("ST. LOUIS SHIP BUILDING & STEEL CO.", "shipyard", "medium"),
        # Found in the week 4-5 spot check: these were flagged high or medium.
        ("3-CARS", "auto house, 3 cars (footprint labeled A)", "low"),
        ("A. A-CARS", "auto house (garage) for 4 cars", "low"),
        ("3 CARS", "garage for three cars", "low"),
        ("5", "auto repair or garage", "low"),
        ("PRIV. GARAGE CAPY 12 CARS CONC. FL.", "private garage, 12 cars", "low"),
        ("FR. FOUND.", "frame foundry", "low"),
        # A truck garage is a fleet garage, not a home garage.
        ("PRIV. GARAGE", "private garage (capacity 10 trucks)", "high"),
    ],
)
def test_relevance(label, use, expected):
    assert relevance(label, use) == expected
