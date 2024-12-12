from .search import match_word, Keyword, Word, find


def test_search():
    assert match_word(Keyword(None, None), Word("hemanta", ["noun"]))
    assert match_word(Keyword("hemanta", None), Word("hemanta", ["noun"]))
    assert match_word(Keyword(None, "noun"), Word("hemanta", ["noun"]))
    assert not match_word(Keyword("amam", None), Word("hemanta", ["noun"]))
    assert not match_word(Keyword(None, "verb"), Word("hemanta", ["noun"]))
    assert not match_word(Keyword("amam", "verb"), Word("hemanta", ["noun"]))


def test_find():
    assert find([], []) == [0]
    assert find([Keyword("wakka", "noun")], []) == []
    assert find([], [Word("wakka", ["noun"])]) == [0]
    assert find([Keyword("hemanta", None)], [Word("wakka", ["noun"])]) == []
    assert find([Keyword("hemanta", None)], [Word("hemanta", ["noun"])]) == [0]
    assert find([Keyword("hemanta", "noun")], [Word("hemanta", ["noun"])]) == [0]
    assert find([Keyword("hemanta", "verb")], [Word("hemanta", ["noun"])]) == []
    assert find(
        [Keyword("hemanta", None), Keyword("wakka", None)],
        [Word("hemanta", ["noun"]), Word("wakka", ["noun"])],
    ) == [0]
    assert (
        find(
            [Keyword("hemanta", None), Keyword("wakka", None)],
            [
                Word("hemanta", ["noun"]),
                Word("something", ["verb"]),
                Word("wakka", ["verb"]),
            ],
        )
        == []
    )
    assert find(
        [Keyword(None, "verb")],
        [
            Word("hemanta", ["verb"]),
            Word("wakka", ["verb"]),
            Word("other", ["noun"]),
            Word("wakka", ["verb"]),
        ],
    ) == [0, 1, 3]

    assert find(
        [Keyword("wakka", None), Keyword(None, "verb")],
        [
            Word("wakka", ["noun", "verb"]),
            Word("wakka", ["verb"]),
            Word("another", ["verb"]),
        ],
    ) == [0, 1]
    assert find(
        [
            Keyword("alpha", None),
            Keyword("beta", None),
            Keyword("gamma", None),
        ],
        [Word("alpha", ["noun"]), Word("beta", ["verb"]), Word("gamma", ["noun"])],
    ) == [0]
    assert find(
        [Keyword("wakka", "noun")],
        [
            Word("wakka", ["verb"]),
            Word("wakka", ["noun"]),
            Word("wakka", ["verb", "noun"]),
        ],
    ) == [1, 2]
    assert (
        find(
            [Keyword("wakka", "adjective")],
            [Word("wakka", ["noun", "verb"]), Word("another", ["adjective"])],
        )
        == []
    )
    assert find(
        [Keyword("exact", None)],
        [Word("exa", ["noun"]), Word("exact", ["noun"]), Word("exa", ["noun"])],
    ) == [1]

    assert find(
        [Keyword("foo", None)],
        [
            Word("foo", ["verb"]),
            Word("bar", ["noun"]),
            Word("foo", ["noun"]),
            Word("foo", ["verb"]),
        ],
    ) == [0, 2, 3]

    assert find(
        [Keyword(None, None), Keyword(None, None)],
        [
            Word("hemanta", ["verb"]),
            Word("wakka", ["noun"]),
            Word("another", ["adjective"]),
        ],
    ) == [0, 1]

    assert find(
        [Keyword(None, "noun"), Keyword(None, "noun")],
        [
            Word("alpha", ["noun"]),
            Word("beta", ["verb"]),
            Word("gamma", ["noun"]),
            Word("delta", ["noun"]),
        ],
    ) == [2]

    assert find([Keyword("alpha", None), Keyword("beta", None)], []) == []

    assert find(
        [Keyword("common", None)],
        [
            Word("common", ["noun"]),
            Word("common", ["verb"]),
            Word("common", ["adjective"]),
        ],
    ) == [0, 1, 2]

    assert (
        find(
            [Keyword("xyz", None), Keyword("123", None)],
            [Word("xyz", ["noun"]), Word("abc", ["noun"]), Word("123", ["noun"])],
        )
        == []
    )

    assert find(
        [Keyword("pewtanke", None)],
        [
            Word("menoko", ["noun"]),
            Word("pewtanke", ["verb"]),
            Word("haw", ["noun"]),
            Word("a=", ["prefix"]),
            Word("nu", ["verb"]),
            Word("wa", ["parti"]),
        ],
    ) == [1]
