import regex as re
from utils.text import remove_accent
from .data.possessives import possessives
from .data.plurals import plurals

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
    word = re.sub(r"^'|'$", "", word)  # remove ' at the beginning and end
    word = re.sub(r"_", "", word)  # remove underscores
    word = re.sub(r"^\[(.*?)\]$", r"\1", word)  # remove square brackets
    word = re.sub(r"\[.*?\]", "", word)  # remove square brackets

    for pattern, replacement in np_nm_patterns.items():
        word = re.sub(pattern, replacement, word)
    for pattern, replacement in sorted(
        plural_patterns.items(), key=lambda x: len(x[0]), reverse=True
    ):
        word = re.sub(pattern, replacement, word)

    if not word:
        return word, {}

    for lemma, short, long in possessives:
        if word == short or word == long:
            return lemma, {
                "Possessed": "Yes",
            }

    for lemma, plural, valency in plurals:
        if word == lemma:
            return lemma, {
                "Number": "Sing",
                "Valency": str(valency),
            }
        if word == plural:
            return lemma, {
                "Number": "Plur",
                "Valency": str(valency),
            }

    # ku= 1.sg.Nom
    # en= 1.sg.Acc
    # ci= 1.pl.excl.Erg
    # =as 1.pl.excl.Intr
    # un= 1.pl.excl.Acc
    # e= 1.pl.Dir
    # eci= 1.pl.Dir
    # ∅ 3.sg/pl.Dir
    # a= 4.pl.Erg
    # an= 4.pl.Erg
    # =an 4.pl.Inr
    # i= 4.pl.Acc

    PERS_SYSTEM = {
        # 4th person plural / 1st person plural inclusive / logographical transtive nominative
        "a=": {
            "Person": "4",
            "Number": "Plur",
            "Clusivity": "In",
            "Case": "Erg",
            "Valency": "-1",
        },
        # 4th person plural / 1st person plural inclusive / logographical intransitive ergative
        "an=": {
            "Person": "4",
            "Number": "Plur",
            "Clusivity": "In",
            "Case": "Erg",
            "Valency": "-1",
        },
        # 4th person plural / 1st person plural inclusive / logographical int
        "=an": {
            "Person": "4",
            "Number": "Plur",
            "Clusivity": "In",
            "Case": "Nom",
            "Valency": "-1",
        },
        "i=": {
            "Person": "4",
            "Number": "Plur",
            "Clusivity": "In",
            "Case": "Acc",
            "Valency": "-1",
        },
        "ku=": {
            "Person": "1",
            "Number": "Sing",
            "Case": "Nom",
            "Valency": "-1",
        },
        "en=": {
            "Person": "1",
            "Number": "Sing",
            "Case": "Acc",
            "Valency": "-1",
        },
        "ci=": {
            "Person": "1",
            "Number": "Sing",
            "Clusivity": "Ex",
            "Case": "Nom",
            "Valency": "-1",
        },
        "=as": {
            "Person": "1",
            "Number": "Plur",
            "Clusivity": "Ex",
            "Case": "Nom",
            "Valency": "-1",
        },
        "un=": {
            "Person": "1",
            "Number": "Plur",
            "Clusivity": "Ex",
            "Case": "Acc",
            "Valency": "-1",
        },
        "e=": {
            "Person": "2",
            "Number": "Sing",
            "Valency": "-1",
        },
        "eci=": {
            "Person": "2",
            "Number": "Plur",
            "Valency": "-1",
        },
    }

    for pattern, features in PERS_SYSTEM.items():
        if word == pattern:
            return word, features

    return word, {}
