from .tokenize import tokenize


def test_tokenize():
    TEST_CASES = [
        [
            "aynu itak k=eyaypakasnu kor k=an!",
            ["aynu", "itak", "k=", "eyaypakasnu", "kor", "k=", "an"],
        ],
        [
            "‘sine ancikar i=rewsire wa i=kore yan.’sekor hawean w_a a=rewsire kor oraun ene hawean h_i. an=an. an=uske. ruwe'",
            [
                "sine",
                "ancikar",
                "i=",
                "rewsire",
                "wa",
                "i=",
                "kore",
                "yan",
                "sekor",
                "hawean",
                "wa",
                "a=",
                "rewsire",
                "kor",
                "oraun",
                "ene",
                "hawean",
                "hi",
                "an=",
                "an",
                "an=",
                "uske",
                "ruwe",
            ],
        ],
        [
            '"Ekasi, ramusinne en=kore yan." sekor ku=ye kor kêtaidenwa ku=sanke wa k=eywanke a korka, néun ku=iki yakka kengai ne aan.',
            [
                "ekasi",
                "ramusinne",
                "en=",
                "kore",
                "yan",
                "sekor",
                "ku=",
                "ye",
                "kor",
                "kêtaidenwa",
                "ku=",
                "sanke",
                "wa",
                "k=",
                "eywanke",
                "a",
                "korka",
                "néun",
                "ku=",
                "iki",
                "yakka",
                "kengai",
                "ne",
                "aan",
            ],
        ],
    ]
    for text, expected in TEST_CASES:
        tokens = tokenize(text)
        print(tokens)
        assert tokens == expected


if __name__ == "__main__":
    test_tokenize()
