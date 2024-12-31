from .lemmatize import lemmatize


def test_lemmatize():
    assert lemmatize("ne'ampe") == "neanpe"
    assert lemmatize("oka") == "an"
    assert lemmatize("okay") == "an"
