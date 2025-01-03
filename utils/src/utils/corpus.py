from typing import TypedDict


class RawSentence(TypedDict):
    sentence: str
    words: list[str]
    translation: str
    lemmas: list[str]
    part_of_speech: list[list[str]]


class CorpusItem(TypedDict):
    translation: str
    sentence: str
    words: list[str]
    lemmas: list[list[str]]
    features: list[list[dict[str, str]]]
    part_of_speech: list[list[str]]
    glosses: list[list[str]]
    metadata: dict[str, str]
