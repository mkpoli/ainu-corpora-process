from typing import TypedDict


class RawSentence(TypedDict):
    sentence: str
    words: list[str]
    translation: str
    part_of_speech: list[list[str]]
