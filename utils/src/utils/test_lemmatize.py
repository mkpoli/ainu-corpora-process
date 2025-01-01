from .lemmatize import lemmatize, normalize


def test_normalize():
    # Underscores
    assert normalize("w_a") == "wa"
    assert normalize("__hine") == "hine"
    assert normalize("h_ine") == "hine"

    # Square brackets
    assert normalize("ne[y]") == "ne"
    assert normalize("awa[n]") == "awa"
    assert normalize("[u]") == "u"

    # Apostrophes
    assert normalize("ne'ampe") == "neanpe"
    assert normalize("inkar'") == "inkar"
    assert normalize("’sekor") == "sekor"


def test_lemmatize():
    # Underscores
    assert lemmatize("w_a", "sconj") == ("wa", frozenset([("Valency", "0")]))
    assert lemmatize("h_ine", "sconj") == ("hine", frozenset([("Valency", "0")]))

    # Square brackets
    assert lemmatize("ne[y]", "cop") == ("ne", frozenset([("Valency", "+2")]))
    assert lemmatize("awa[n]", "sconj") == ("awa", frozenset([("Valency", "0")]))
    assert lemmatize("[u]", "intj") == ("u", frozenset([("Valency", "0")]))

    # Apostrophes
    assert lemmatize("ne'ampe", "n") == ("neanpe", frozenset([("Valency", "-1")]))
    assert lemmatize("inkar'", "vi") == ("inkar", frozenset([("Valency", "+1")]))

    # Plurals
    assert lemmatize("oka", "vi") == (
        "an",
        frozenset([("Valency", "+1"), ("Number", "Plur")]),
    )
    assert lemmatize("okay", "vi") == (
        "an",
        frozenset([("Valency", "+1"), ("Number", "Plur")]),
    )

    # Possessives
    assert lemmatize("mat", "n") == ("mat", frozenset([("Valency", "-1")]))
    assert lemmatize("maci", "n") == (
        "mat",
        frozenset([("Valency", "-1"), ("Possessed", "Yes")]),
    )
    assert lemmatize("macihi", "n") == (
        "mat",
        frozenset([("Valency", "-1"), ("Possessed", "Yes")]),
    )


# def test_hello():
#     # for row in possessives:
#     #     assert lemmatize(row[0]) == row[1]
