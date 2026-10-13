from blockhistory.map_reader.scoring import label_words, match_sheet, numbers


def _f(label, number=None):
    return {"label": label, "street_number": number}


def test_numbers_expand_short_ranges():
    assert numbers("6226-24") == {6226, 6224}
    assert numbers("7012 (lot)") == {7012}
    assert numbers(None) == set()


def test_abbreviations_and_spellings_match():
    assert label_words("BL. SM.") == ["BLACKSMITH"]
    assert label_words("NAPHTHALINE STGE") == label_words("NAPTHALINE STGE.")


def test_same_named_sites_need_one_finding_each():
    hand = [_f("FILL'G STA.", "6226-6224"), _f("FILL'G STA.", "6800"), _f("FILL'G STA.", "6930")]
    found = [_f("FILL'G STA.", "6800"), _f("FILL'G STA."), _f("FILL'G STA.", "6800")]
    # Address match first, then the unnumbered read takes a free site; the repeat of 6800
    # is a duplicate of 6800, so one site stays unfound.
    assert match_sheet(found, hand) == [1, 0, 1]


def test_most_shared_words_wins():
    hand = [_f("GAS PRODUCER HO."), _f("COOLING PONDS / GAS METER HO.")]
    assert match_sheet([_f("GAS METER HO.")], hand) == [1]


def test_contradicting_number_is_not_a_duplicate():
    hand = [_f("TIN SHOP", "7120")]
    assert match_sheet([_f("TIN SHOP", "7120"), _f("TIN SHOP", "5900")], hand) == [0, None]


def test_one_digit_misread_picks_the_right_station():
    # Sheet 57: the reader wrote 7902 for 7300-7302 and 2432 for 7432.
    hand = [_f("FILL'G STA.", "7300-7302"), _f("FILL'G STA.", "7432")]
    assert match_sheet([_f("FILLG STA CONC FL.", "2432"), _f("FILL'G STA.", "7902")], hand) == [
        1,
        0,
    ]
