import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dictionary import lookup_helper, batchelor_modern_match as v1
from dictionary import batchelor_modern_match_v2 as v2, batchelor_modern_match_v3 as v3
from dictionary.headwords import NAKAGAWA, nakagawa_lemma


class HeadwordTests(unittest.TestCase):
    def test_exact_lookup_keeps_original_heading(self):
        rows = [("nakagawa", "rur, -i", "海の潮", "rur"), ("nakagawa", "askepet, -i", "指", "askepet")]
        with patch.object(lookup_helper, "rows", return_value=rows):
            self.assertEqual(lookup_helper.lemma_lookup("rur"), [("nakagawa", "rur, -i", "海の潮")])
            self.assertEqual(lookup_helper.lemma_lookup("-i"), [])

    def test_matchers_index_the_word_and_keep_the_printed_heading(self):
        for module in [v2, v3]:
            source = module.Source("nakagawa")
            source.add("rur, -i", "ルㇽ", "海の潮", pos="名")
            source.add("ka,-si oyki", "", "面倒を見る", pos="連動")
            self.assertEqual(source.latn["rur"][0]["lemma"], "rur")
            self.assertEqual(source.latn["rur"][0]["printed_lemma"], "rur, -i")
            self.assertNotIn(module.norm_latn("-i"), source.latn)
            self.assertNotIn("ka", source.latn)
            if module is v3:
                self.assertIn("rur", source.lemma_set)
                for records in source.ja_index.values():
                    self.assertLessEqual(sum(r["lemma"] == "rur" for r in records), 1)

    def test_tsv_loaders_use_pos_to_preserve_fused_phrases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / NAKAGAWA
            directory.mkdir()
            path = directory / "nakagawa_terms.tsv"
            with path.open("w", newline="") as f:
                writer = csv.writer(f, delimiter="\t")
                writer.writerow(["kana", "latn", "pos", "definition"])
                writer.writerows([["ルㇽ", "rur, -i", "名", "海の潮"], ["", "kip, -iniwkes", "連動", "助ける"]])
            with patch.object(v1, "DICT_ROOT", root):
                index = v1.load_nakagawa()
                self.assertEqual(index["rur"][0]["printed_lemma"], "rur, -i")
                self.assertNotIn("kip", index)
            with patch.object(lookup_helper, "DICT_ROOT", root):
                loaded = lookup_helper.load_all()
                self.assertEqual(loaded[0][-1], "rur")
                self.assertEqual(loaded[1][-1], "kip, -iniwkes")

    def test_multiple_suffixes_and_numbered_headwords(self):
        for heading, expected in [("rep², -ke", "rep²"), ("kimuyka, -si, -ke", "kimuyka"), ("rapok, -i=ke", "rapok"), ("ka,-si oyki", "ka,-si oyki"), ("-kar³", "-kar³")]:
            self.assertEqual(nakagawa_lemma(heading), expected)


if __name__ == "__main__":
    unittest.main()
