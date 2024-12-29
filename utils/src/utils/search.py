from typing import Generator, NamedTuple, TypedDict, cast


class Keyword(NamedTuple):
    word: str | None
    pos: str | None


class Word(NamedTuple):
    word: str
    poss: list[str]


class Sentence(TypedDict):
    book: str
    sentence: str
    words: list[str]
    part_of_speech: list[list[str]]
    translation: str


class SearchResult(Sentence):
    found_intervals: list[tuple[int, int]]


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


class Concordancer:
    corpus: list[Sentence]

    def __init__(self, corpus: list[Sentence]):
        self.corpus = corpus

    def search(
        self,
        keywords: list[Keyword],
        context_length: int = 1,
    ) -> Generator[SearchResult, None, None]:
        for i, sentence in enumerate(self.corpus):
            previous_contexts = (
                self.corpus[i - context_length : i] if i - context_length >= 0 else []
            )
            next_contexts = (
                self.corpus[i + 1 : i + context_length + 1]
                if i + context_length + 1 <= len(self.corpus)
                else []
            )
            previous_contexts = [
                context
                for context in previous_contexts
                if context["book"] == sentence["book"]
            ]
            previous_context_words = sum(
                len(context["words"]) for context in previous_contexts
            )
            next_contexts = [
                context
                for context in next_contexts
                if context["book"] == sentence["book"]
            ]
            extended_sentence = cast(
                Sentence,
                {
                    "book": sentence["book"],
                    "sentence": " ".join(
                        [context["sentence"] for context in previous_contexts]
                    )
                    + " "
                    + sentence["sentence"]
                    + " "
                    + " ".join([context["sentence"] for context in next_contexts]),
                    "words": [
                        *[
                            word
                            for context in previous_contexts
                            for word in context["words"]
                        ],
                        *sentence["words"],
                        *[
                            word
                            for context in next_contexts
                            for word in context["words"]
                        ],
                    ],
                    "part_of_speech": [
                        *[
                            pos
                            for context in previous_contexts
                            for pos in context["part_of_speech"]
                        ],
                        *sentence["part_of_speech"],
                        *[
                            pos
                            for context in next_contexts
                            for pos in context["part_of_speech"]
                        ],
                    ],
                    "translation": " ".join(
                        [context["translation"] for context in previous_contexts]
                    )
                    + " "
                    + sentence["translation"]
                    + " "
                    + " ".join([context["translation"] for context in next_contexts]),
                },
            )

            extended_words = [
                Word(word, pos)
                for word, pos in zip(
                    extended_sentence["words"], extended_sentence["part_of_speech"]
                )
            ]

            previous_contexts_words = sum(
                len(context["words"]) for context in previous_contexts
            )
            next_contexts_words = sum(
                len(context["words"]) for context in next_contexts
            )
            found = find(
                keywords,
                extended_words[
                    previous_contexts_words : len(extended_words) - next_contexts_words
                ],
            )

            found_intervals = [
                (f + previous_context_words, f + len(keywords) + previous_context_words)
                for f in found
            ]
            if found:
                yield SearchResult(
                    book=extended_sentence["book"],
                    sentence=extended_sentence["sentence"],
                    words=extended_sentence["words"],
                    part_of_speech=extended_sentence["part_of_speech"],
                    translation=extended_sentence["translation"],
                    found_intervals=found_intervals,
                )
