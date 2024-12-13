import re
from nltk.tokenize import RegexpTokenizer


def tokenize(sentence: str) -> list[str]:
    # 小文字化
    sentence = sentence.lower()
    # 下線符号の除去
    sentence = sentence.replace("_", "")
    # 単引用符の除去
    # print("*" * 50)
    # print(0, sentence)
    sentence = re.sub(r"(<?!\w)[‘'](.*?)['’]", r"\1", sentence)
    # print(1, sentence)
    sentence = re.sub(r"(.*?)['’](?!\w)", r"\1", sentence)
    # print(2, sentence)
    sentence = re.sub(r"(<?!\w)[‘'](.*?)", r"\1", sentence)
    # print(3, sentence)
    # print("*" * 50)
    sentence = re.sub(r"\[\d+\]", "", sentence)
    sentence = re.sub(r"\*\d+", "", sentence)

    tokenizer = RegexpTokenizer(r"[a-zA-Zâîûêôáíúéó0-9=-_'’]+")
    words = tokenizer.tokenize(sentence)

    def split_affixes(word: str) -> list[str]:
        if word.count("=") + word.count("-") >= 2:
            PREFIXES = [
                "ku",
                "k",
                "en",
                "in",
                "ci",
                "c",
                "un",
                "a",
                "i",
                "an",
                "e",
                "eci",
                "ec",
            ]
            prefix_group = f"((?:{'|'.join(PREFIXES)})=)?"

            SUFFIXES = ["an", "as"]
            suffix_group = f"(=(?:{'|'.join(SUFFIXES)}))?"

            PATTERN = re.compile(
                rf"{prefix_group}{prefix_group}([a-z/-]+){suffix_group}"
            )

            parts = PATTERN.match(word)

            if not parts:
                # print("regex: ", rf"{prefix_group}([a-z]+){suffix_group}")
                # raise ValueError(f"Cannot process affixes: {word}")
                return [word]

            return [p for p in parts.groups() if p]

        parts = re.split(r"([-=])", word)
        if len(parts) == 1:
            return [word]
        try:
            a, sep, b = parts
        except ValueError:
            # print("-" * 50)
            # print(parts)
            # print("-" * 50)
            return [word]
        if len(a) > len(b):
            return [a, sep + b]
        else:
            return [a + sep, b]

    words = [w.strip("‘’'?") for w in words]
    words = [split_affixes(w) for w in words]
    words = [w for word in words for w in word]
    return words
