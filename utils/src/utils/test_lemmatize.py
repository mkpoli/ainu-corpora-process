from .lemmatize import lemmatize

from .data.possessives import possessives


def test_lemmatize():
    # Underscores
    assert lemmatize("w_a") == ("wa", {})
    assert lemmatize("h_ine") == ("hine", {})

    # Apostrophes
    assert lemmatize("ne'ampe") == ("neanpe", {})
    assert lemmatize("oka") == ("an", {})
    assert lemmatize("okay") == ("an", {})
    assert lemmatize("mat") == ("mat", {})
    assert lemmatize("maci") == ("mat", {"Possessed": "Yes"})
    assert lemmatize("macihi") == ("mat", {"Possessed": "Yes"})


# def test_hello():
#     # for row in possessives:
#     #     assert lemmatize(row[0]) == row[1]
