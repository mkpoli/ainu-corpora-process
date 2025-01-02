from utils.accent import get_accent


def test_accent():
    assert get_accent("úsey") == 0
    assert get_accent("tané") == 1
    assert get_accent("konkane") == 0
    assert get_accent("kuni") == 1
