from .text import remove_accent


def test_remove_accent():
    assert remove_accent("néno") == "neno"
    assert remove_accent("côsi") == "cosi"
