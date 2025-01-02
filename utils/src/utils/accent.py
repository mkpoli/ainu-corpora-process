import regex
from ainconv import separate


def get_accent(word: str) -> int:
    """Calculate the accent of an Ainu word

    0+: the position of the accent
    -1: unknown

    """
    syllables = separate(word)
    print(syllables)
    if regex.search(r"[áéíóú]", word):
        return next(i for i, s in enumerate(syllables) if regex.search(r"[áéíóú]", s))
    else:
        first_syllable = syllables[0]

        if first_syllable[-1] in "aiueoáíúéó":
            return 1
        else:
            return 0
