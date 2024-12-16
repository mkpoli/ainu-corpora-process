import regex
from ainconv import separate


def extrapolate_sakhalin_from_hokkaido(word: str) -> str:
    syllables = separate(word)

    def process_syllable(syllable: str) -> str:
        if not syllable:
            return syllable
        if not regex.match("[a-zA-Z]+", syllable):
            return syllable
        if len(syllable) <= 1:
            return syllable
        if syllable[-1] in ["p", "t", "k"]:
            return syllable[:-1] + "h" if syllable[-2] != "i" else syllable[:-1] + "s"
        elif syllable[-1] == "r":
            return syllable + syllable[-2]
        elif syllable[-1] == "m":
            return syllable[:-1] + "n"
        return syllable

    return "".join(process_syllable(syllable) for syllable in syllables)
