from .lemmatize import lemmatize


def test_lemmatize():
    # Underscores
    assert lemmatize("w_a", "sconj") == ("wa", {"Valency": "0"})
    assert lemmatize("h_ine", "sconj") == ("hine", {"Valency": "0"})

    # Square brackets
    assert lemmatize("ne[y]", "cop") == ("ne", {"Valency": "+2"})
    assert lemmatize("awa[n]", "sconj") == ("awa", {"Valency": "0"})
    assert lemmatize("[u]", "intj") == ("u", {"Valency": "0"})

    # Apostrophes
    assert lemmatize("ne'ampe", "n") == ("neanpe", {"Valency": "-1"})
    assert lemmatize("inkar'", "vi") == ("inkar", {"Valency": "+1"})

    # Plurals
    assert lemmatize("oka", "vi") == ("an", {"Valency": "+1", "Number": "Plur"})
    assert lemmatize("okay", "vi") == ("an", {"Valency": "+1", "Number": "Plur"})

    # Possessives
    assert lemmatize("mat", "n") == ("mat", {"Valency": "-1"})
    assert lemmatize("maci", "n") == ("mat", {"Valency": "-1", "Possessed": "Yes"})
    assert lemmatize("macihi", "n") == ("mat", {"Valency": "-1", "Possessed": "Yes"})


# def test_hello():
#     # for row in possessives:
#     #     assert lemmatize(row[0]) == row[1]
