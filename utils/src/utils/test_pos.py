from utils.pos import get_pos


def test_pos():
    assert get_pos("ram") == ["n"]
    assert get_pos("us") == ["v"]


if __name__ == "__main__":
    test_pos()
