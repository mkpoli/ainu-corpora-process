from typing import NamedTuple


class Keyword(NamedTuple):
    word: str | None
    pos: str | None


class Word(NamedTuple):
    word: str
    poss: list[str]


def match_word(
    keyword: Keyword,
    word: Word,
) -> bool:
    return (
        # match word
        keyword.word is None
        or keyword.word == word.word
    ) and (
        # match pos
        keyword.pos is None
        or keyword.pos in word.poss
    )


def find(
    keywords: list[Keyword],
    words: list[Word],
    current_index: int = 0,
    start_index: int | None = None,
) -> list[int]:
    if not keywords:
        return [start_index if start_index is not None else current_index]

    if not words:
        return []

    results = []

    if start_index is None:
        if match_word(keywords[0], words[0]):
            results.extend(
                find(keywords[1:], words[1:], current_index + 1, current_index)
            )

        results.extend(find(keywords, words[1:], current_index + 1, None))
    else:
        if match_word(keywords[0], words[0]):
            results.extend(
                find(keywords[1:], words[1:], current_index + 1, start_index)
            )
        else:
            return []

    return results
