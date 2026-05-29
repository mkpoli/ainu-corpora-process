"""Quick lookup across all loaded Ainu dictionaries by Japanese / English
gloss or Ainu lemma. For interactive use while manually annotating the
remaining Batchelor 1938 unmatched entries.

Usage:
    uv run python -m dictionary.lookup_helper search "頰"
    uv run python -m dictionary.lookup_helper search "cheek"
    uv run python -m dictionary.lookup_helper lemma "notpuy"
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

csv.field_size_limit(sys.maxsize)

DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")

SOURCES = [
    ("kayano", "1996_Kayano_Kayanos-Ainu-Dictionary/kayano-entries.tsv", "lemma", "definition"),
    ("nakagawa", "1995_Nakagawa_Ainu-Chitose-Dialect-Dictionary/nakagawa_terms.tsv", "latn", "definition"),
    ("tamura", "1996_Tamura_Ainu-Saru-Dialect-Dictionary/original.tsv", "translit", "definition"),
    ("tomita", "2021_Tomita_Aynu-Online-Dictionary/original.tsv", "lemma", "explanation"),
    ("silja-AE", "2023_Silja_Ainu-English-Ainu-vocabulary-list/Ainu-English.tsv", "Ainu", "English"),
    ("silja-EA", "2023_Silja_Ainu-English-Ainu-vocabulary-list/English-Ainu.tsv", "Ainu", "English"),
    ("tane_an", None, None, None),  # CSV path, handled separately
    ("asahikawa_v1", "1995_Uoi_Asahikawa-Ainu-Verbs-I/original.tsv", "lemma_normalized", "body"),
    ("asahikawa_v2", "1996_Uoi_Asahikawa-Ainu-Verbs-II/original.tsv", "lemma_normalized", "body"),
    ("asahikawa_n1", "2006_Uoi_Asahikawa-Ainu-Nouns-I/original.tsv", "lemma_normalized", "body"),
    ("asahikawa_n2", "2007_Uoi_Asahikawa-Ainu-Nouns-II/original.tsv", "lemma_normalized", "body"),
    ("nel", "2020_NorthEuraLex_Hokkaido-Ainu/original.tsv", "lemma_raw", "concept_en"),
    ("enwikt", "XXXX_English-Wiktionary/wiktionary-en-entries.tsv", "lemma", "definition"),
    ("jawikt", "XXXX_Japanese-Wiktionary/wiktionary-entries.tsv", "lemma", "definition"),
    ("chiri_a", "1987_Chiri_Categorized-Ainu-Dictionary/chiri-animals-entries.tsv", "lemma", "definition"),
    ("chiri_p", "1987_Chiri_Categorized-Ainu-Dictionary/chiri-plants-entries.tsv", "lemma", "definition"),
    ("chiri_h1", "1987_Chiri_Categorized-Ainu-Dictionary/chiri-human-1-entries.tsv", "lemma", "definition"),
    ("chiri_h2", "1987_Chiri_Categorized-Ainu-Dictionary/chiri-human-2-entries.tsv", "lemma", "definition"),
    ("shibatani", "1990_Shibatani_RaccoonBend-Ainu-English-Wordlist/original.tsv", "lemma", "meaning_en"),
    ("lex_ru", "2024_LexiconsRu_Ainu-English-Ainu/original.tsv", "lemma", "meaning_en"),
    ("mukawa", "XXXX_Chiba_Mukawa-Dialect-Japanese-Ainu-Dictionary/original.tsv", "lemma", "translation"),
    ("kanazawa", "1898_Kanazawa_NINJAL-Topical-Ainu-Conversation-Dictionary/original.tsv", "lemma", "translation"),
    ("urakawa", "1985_Urakawa_Private-Ainu-Dictionary/original.tsv", "lemma_kana", "gloss_ja"),
    ("akulov", "2009_Akulov_Russian-Ainu-Dictionary/original.tsv", "ain", "rus_gloss"),
    ("ota", "2022_Ota_Japanese-Ainu_Dictionary/original.tsv", "title", "description"),
    ("loanwordbank", "XXXX_Loanwordbank_Wiktionary-Ainu/original.tsv", "lemma", "gloss_en"),
    ("td", "2009_TranslationDirectory_Wikipedia-Ainu-English/original.tsv", "lemma", "english"),
    ("bugaeva", "2013_Bugaeva_ValPaL-Ainu-Verbs/original.tsv", "lemma", "meaning_en"),
    ("bat1905", "1905_Batchelor_Ainu-English-Japanese-Dictionary/original.tsv", "lemma", "body"),
]


def load_all():
    rows = []
    for entry in SOURCES:
        if entry[1] is None:
            # tane_an CSV
            csv_path = DICT_ROOT / "2024_Tane_an_Aynuitak-kotupte_Itak-uoeroskip/ainu-glossary.csv"
            if csv_path.exists():
                with csv_path.open(encoding="utf-8") as fh:
                    for row in csv.DictReader(fh):
                        lem = (row.get("ainu") or row.get("Ainu") or "").strip()
                        defn = (row.get("japanese") or row.get("Japanese") or "").strip()
                        if lem:
                            rows.append(("tane_an", lem, defn))
            continue
        name, rel, lem_col, def_col = entry
        p = DICT_ROOT / rel
        if not p.exists():
            continue
        with p.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                lem = (row.get(lem_col) or "").strip()
                defn = (row.get(def_col) or "").strip()
                if lem or defn:
                    rows.append((name, lem, defn))
    return rows


_ROWS = None
def rows():
    global _ROWS
    if _ROWS is None:
        _ROWS = load_all()
    return _ROWS


def search(query: str, limit: int = 12, contains: bool = True) -> list[tuple[str, str, str]]:
    q = query.strip()
    out = []
    seen = set()
    for src, lem, defn in rows():
        if not q:
            continue
        if contains:
            hit = (q in lem) or (q in defn)
        else:
            hit = (lem == q)
        if hit:
            key = (src, lem)
            if key in seen:
                continue
            seen.add(key)
            out.append((src, lem, defn[:140]))
            if len(out) >= limit:
                break
    return out


def lemma_lookup(q: str, limit: int = 12) -> list[tuple[str, str, str]]:
    return search(q, limit=limit, contains=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("search", "lemma"))
    ap.add_argument("query", nargs="+")
    ap.add_argument("--limit", type=int, default=12)
    args = ap.parse_args()
    q = " ".join(args.query)
    func = lemma_lookup if args.mode == "lemma" else search
    results = func(q, limit=args.limit)
    if not results:
        print(f"(no hits for: {q})")
        return
    for src, lem, defn in results:
        print(f"{src:18}  {lem:30}  {defn}")


if __name__ == "__main__":
    main()
