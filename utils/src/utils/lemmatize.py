import regex as re
from utils.text import remove_accent
from .data.possessives import possessives
from .data.plurals import plurals

np_nm_patterns = {
    "neampe": "neanpe",
    "ampe": "anpe",
}

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


def clean_lemma(word: str) -> str:
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
    return word


def morphologize(word: str, lemma: str, pos: str) -> dict[str, str]:
    features = {}

    return features


def lemmatize(word: str, pos: str) -> tuple[str, frozenset[tuple[str, str]]]:
    if not word:
        return word, frozenset()

    word = clean_lemma(word)

    # | UPOS                | XPOS   | JAPANESE |
    # | ------------------- | ------ | -------- |
    # | VERB                | vi     | 自動詞   |
    # | VERB                | vt     | 他動詞   |
    # | VERB                | vd     | 複他動詞 |
    # | VERB                | vc     | 完全動詞 |
    # | VERB                | v      | 動詞     |
    # | AUX                 | auxv   | 助動詞   |
    # | AUX                 | cop    | 繋辞     |
    # | NOUN                | n      | 名詞     |
    # | NOUN                | nl     | 位置名詞 |
    # | NOUN                | nmlz   | 形式名詞 |
    # | PRON                | pron   | 代名詞   |
    # | PROPN               | propn  | 固有名詞 |
    # | DET                 | adn    | 連体詞   |
    # | ADV                 | adv    | 副詞     |
    # | CCONJ / SCONJ / ADV | cconj  | 接続詞   |
    # | POST                | post   | 助詞     |
    # | PART                | sfp    | 終助詞   |
    # | PART                | pers   | 人称接辞 |
    # | INTJ                | intj   | 間投詞   |
    # | SCONJ               | sconj  | 接続助詞 |
    # | SCONJ               | padv   | 後置副詞 |
    # | -                   | sfx    | 接尾辞   |
    # | -                   | pfx    | 接頭辞   |
    # | -                   | root   | 語根     |
    # | ADP                 | advp   | 副助詞   |
    # | ADP                 | postp  | 格助詞   |
    # | ADP                 | parti  | 助詞     |
    # | PRON / DET / NOUN   | int    | 疑問詞   |
    # | NUM                 | num    | 数詞     |
    # | PUNCT               | punct  | 記号     |
    # | -                   | colloc | 連語     |
    # | -                   | idiom  | 慣用句   |

    features: dict[str, str] = {}

    pos_2_valency = {
        "vi": "+1",
        "vt": "+2",
        "vd": "+3",
        "vc": "0",
        "v": None,
        "auxv": "0",
        "cop": f"+2",  # or 1?
        "n": "-1",
        "nl": "-1",
        "nmlz": "-1",
        "pron": "-1",
        "propn": "-1",
        "adn": "+1",  # or 0?
        "adv": "0",
        "cconj": "0",
        "post": "+1",
        "sfp": "0",
        "pers": None,
        "intj": "0",
        "sconj": "0",
        "padv": "+1",
        "sfx": None,
        "pfx": None,
        "root": "-1",
        "advp": "0",
        "parti": "0",
        "int": None,
        "num": None,
        "punct": None,
    }

    if pos and pos in pos_2_valency and pos_2_valency[pos] is not None:
        features["Valency"] = pos_2_valency[pos]

    # print(f"after valency {word=}, {features=}")

    if pos == "n":
        for lemma, short, long in possessives:
            if word == short or word == long:
                word = lemma
                features["Possessed"] = "Yes"

    if pos in ["v", "vi", "vt", "vd", "vc"]:
        for lemma, plural, valency in plurals:
            if word == lemma:
                features["Number"] = "Sing"
                features["Valency"] = str(valency)
                return lemma, frozenset(features.items())
            if word == plural:
                features["Number"] = "Plur"
                features["Valency"] = str(valency)
                return lemma, frozenset(features.items())

    # print(f"after plurals {word=}, {features=}")

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

    if word in PERS_SYSTEM:
        features = PERS_SYSTEM[word]

    # print(f"after pers system {word=}, {features=}")
    return word, frozenset(features.items())
