import re


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

        PATTERN = re.compile(rf"{prefix_group}{prefix_group}([a-z/-]+){suffix_group}")

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


def split_affixing_apostrophes(word: str) -> list[str]:
    if len(word) < 2:
        return [word]

    pattern = r"^(['’‘])?([^'’‘]*)(['’‘])?$"
    match = re.match(pattern, word)

    if not match:
        return [word]

    prefix, middle, suffix = match.groups()

    if prefix and suffix:
        return [prefix, middle, suffix]
    elif prefix:
        return [prefix, middle]
    elif suffix:
        return [middle, suffix]
    return [word]


def tokenize(sentence: str) -> list[str]:
    # 小文字化
    # sentence = sentence.lower()
    # 下線符号の除去
    # sentence = sentence.replace("_", "")
    # 単引用符の除去
    # print("*" * 50)
    # print(0, sentence)
    # sentence = re.sub(r"(<?!\w)[‘'](.*?)['’]", r"\1", sentence)
    # print(1, sentence)
    # sentence = re.sub(r"(.*?)['’](?!\w)", r"\1", sentence)
    # print(2, sentence)
    # sentence = re.sub(r"(<?!\w)[‘'](.*?)", r"\1", sentence)
    # print(3, sentence)
    # print("*" * 50)
    # sentence = re.sub(r"\[\d+\]", "", sentence)
    # sentence = re.sub(r"\*\d+", "", sentence)

    print("sentence: ", sentence)
    # tokenizer = RegexpTokenizer(
    #     r"(?:\.\.\.(\.\.\.)?)|[a-zA-Zâîûêôáíúéó=\-_'’]+|\d+|[<>\.,‘\"“”]"
    # )

    words = re.split(
        r"((?:\.\.\.(\.\.\.)?)|[a-zA-Zâîûêôáíúéó=\-_'’]+|\d+|[<>\.,‘\"“”])|\s+",
        sentence,
    )

    # words = tokenizer.tokenize(sentence)

    words = [w for w in words if w]

    print("words (1): ", words)

    words = [w for word in words for w in split_affixing_apostrophes(word)]
    print("words (2): ", words)

    words = [w for word in words for w in split_affixes(word)]
    print("words (3): ", words)

    words = [w for w in words if w]
    print("words (4): ", words)

    print("-" * 50)
    return words
