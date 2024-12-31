import regex as re
from utils.text import remove_accent
from .data.possessives import possessives


np_nm_patterns = {
    "neampe": "neanpe",
    "ampe": "anpe",
}

plural_patterns = {"oka": "an", "okay": "an", "rok": "a"}

# class MorphoLogicalFeatures:
#     def __init__(self, name: str, value: str):
#         self.name = name
#         self.value = value

#     def __str__(self):
#         return f"{self.name}: {self.value}"

words_to_merge = {
    "haw'as": "hawas",  # TODO: háwas
    "haw'an": "hawan",  # TODO: háwan
    "sir'an": "siran",  # TODO: síran
    "sik'o": "siko",  # TODO: síko
    "cip'o": "cipo",  # TODO: cípo
}


def lemmatize(word: str) -> tuple[str, dict[str, str]]:
    word = remove_accent(word)  # TODO: keep accent distinctions
    # Apostrophes
    word = re.sub("’", "'", word)  # ’ -> '
    word = re.sub(r"(?<=[aiueo])'(?=[aiueo])", "", word)  # remove ' between vowels
    word = re.sub(r"^'", "", word)  # remove ' at the beginning
    word = re.sub(r"_", "", word)  # remove underscores
    word = re.sub(r"^\[(.*?)\]$", r"\1", word)  # remove square brackets
    word = re.sub(r"\[.*?\]", "", word)  # remove square brackets

    for pattern, replacement in np_nm_patterns.items():
        word = re.sub(pattern, replacement, word)
    for pattern, replacement in sorted(
        plural_patterns.items(), key=lambda x: len(x[0]), reverse=True
    ):
        word = re.sub(pattern, replacement, word)

    for lemma, short, long in possessives:
        if word and word == short or word == long:
            return lemma, {
                "Possessed": "Yes",
            }

    return word, {}
