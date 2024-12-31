from .lemmatize import lemmatize


def test_lemmatize():
    # Underscores
    assert lemmatize("w_a") == ("wa", {})
    assert lemmatize("h_ine") == ("hine", {})

    # Square brackets
    assert lemmatize("ne[y]") == ("ne", {})
    assert lemmatize("awa[n]") == ("awa", {})
    assert lemmatize("[u]") == ("u", {})

    # Apostrophes
    assert lemmatize("ne'ampe") == ("neanpe", {})
    assert lemmatize("inkar'") == ("inkar", {})

    # Plurals
    assert lemmatize("oka") == ("an", {})
    assert lemmatize("okay") == ("an", {})

    # Possessives
    assert lemmatize("mat") == ("mat", {})
    assert lemmatize("maci") == ("mat", {"Possessed": "Yes"})
    assert lemmatize("macihi") == ("mat", {"Possessed": "Yes"})


# def test_hello():
#     # for row in possessives:
#     #     assert lemmatize(row[0]) == row[1]
