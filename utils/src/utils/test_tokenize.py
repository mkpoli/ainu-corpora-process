from .tokenize import tokenize


def test_tokenize():
    TEST_CASES = [
        [
            "hioy’oy",
            ["hioy’oy"],
        ],
        [
            "aynu itak k=eyaypakasnu kor k=an!",
            ["aynu", "itak", "k=", "eyaypakasnu", "kor", "k=", "an", "!"],
        ],
        [
            "‘sine ancikar i=rewsire wa i=kore yan.’sekor hawean w_a a=rewsire kor oraun ene hawean h_i. an=an. an=uske. ruwe'",
            [
                "‘",
                "sine",
                "ancikar",
                "i=",
                "rewsire",
                "wa",
                "i=",
                "kore",
                "yan",
                ".",
                "’",
                "sekor",
                "hawean",
                "w_a",
                "a=",
                "rewsire",
                "kor",
                "oraun",
                "ene",
                "hawean",
                "h_i",
                ".",
                "an=",
                "an",
                ".",
                "an=",
                "uske",
                ".",
                "ruwe",
                "'",
            ],
        ],
        [
            '"Ekasi, ramusinne en=kore yan." sekor ku=ye kor kêtaidenwa ku=sanke wa k=eywanke a korka, néun ku=iki yakka kengai ne aan.',
            [
                '"',
                "Ekasi",
                ",",
                "ramusinne",
                "en=",
                "kore",
                "yan",
                ".",
                '"',
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
                ",",
                "néun",
                "ku=",
                "iki",
                "yakka",
                "kengai",
                "ne",
                "aan",
                ".",
            ],
        ],
        [
            "korka, katkemat'utar anakne uweyaykopuntek kor suke kor okay korka asinuma anakne suke ka=an ki somo ki no, soy peka omanan=an w_a inkar=an korka kuca okari (e)nep ka omanan ruwe ka isam no, siran w_a a=nukar korka inawcipa kes ta hemanta sirouri wa tumamaha anakne nuyna wa, sapa takupi sanke wa an pe an ruwe a=nukar wa kusu, a=hokuhu poro su ka kor wa arpa, kuca or_ ta kor wa arpa wa an pe ne kusu ne su a=atte w_a useykar=an wa *popse ... pop'useykar=an wa ne sapaha takup sanke wa an pe, sapaha a=kuta*3 akusu",
            [
                "korka",
                ",",
                "katkemat'utar",
                "anakne",
                "uweyaykopuntek",
                "kor",
                "suke",
                "kor",
                "okay",
                "korka",
                "asinuma",
                "anakne",
                "suke",
                "ka=",
                "an",
                "ki",
                "somo",
                "ki",
                "no",
                ",",
                "soy",
                "peka",
                "omanan",
                "=an",
                "w_a",
                "inkar",
                "=an",
                "korka",
                "kuca",
                "okari",
                "(",
                "e",
                ")",
                "nep",
                "ka",
                "omanan",
                "ruwe",
                "ka",
                "isam",
                "no",
                ",",
                "siran",
                "w_a",
                "a=",
                "nukar",
                "korka",
                "inawcipa",
                "kes",
                "ta",
                "hemanta",
                "sirouri",
                "wa",
                "tumamaha",
                "anakne",
                "nuyna",
                "wa",
                ",",
                "sapa",
                "takupi",
                "sanke",
                "wa",
                "an",
                "pe",
                "an",
                "ruwe",
                "a=",
                "nukar",
                "wa",
                "kusu",
                ",",
                "a=",
                "hokuhu",
                "poro",
                "su",
                "ka",
                "kor",
                "wa",
                "arpa",
                ",",
                "kuca",
                "or_",
                "ta",
                "kor",
                "wa",
                "arpa",
                "wa",
                "an",
                "pe",
                "ne",
                "kusu",
                "ne",
                "su",
                "a=",
                "atte",
                "w_a",
                "useykar",
                "=an",
                "wa",
                "*",
                "popse",
                "...",
                "pop'useykar",
                "=an",
                "wa",
                "ne",
                "sapaha",
                "takup",
                "sanke",
                "wa",
                "an",
                "pe",
                ",",
                "sapaha",
                "a=",
                "kuta",
                "*",
                "3",
                "akusu",
            ],
        ],
        [
            "a=sirkocotca p ne kusu an hine <ne>",
            ["a=", "sirkocotca", "p", "ne", "kusu", "an", "hine", "<", "ne", ">"],
        ],
    ]
    for text, expected in TEST_CASES:
        tokens = tokenize(text)
        # print(tokens)
        assert tokens == expected


if __name__ == "__main__":
    test_tokenize()
