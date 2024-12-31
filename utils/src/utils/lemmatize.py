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


def lemmatize(word: str) -> tuple[str, dict[str, str]]:
    # word = remove_accent(word)
    pattern_of_apostrophe_between_vowel_use_lookaahead_and_lookbehind = (
        r"(?<=[aiueo])'(?=[aiueo])"
    )
    word = re.sub(
        pattern_of_apostrophe_between_vowel_use_lookaahead_and_lookbehind, "", word
    )
    for pattern, replacement in np_nm_patterns.items():
        word = re.sub(pattern, replacement, word)
    for pattern, replacement in sorted(
        plural_patterns.items(), key=lambda x: len(x[0]), reverse=True
    ):
        word = re.sub(pattern, replacement, word)

    for lemma, short, long in possessives:
        if word == short or word == long:
            return lemma, {
                "Possessed": "Yes",
            }
    return word, {}
