"""Import dictionary-like datasets already collected in ainu-corpora.

Sources:
- ainu-corpora/data.jsonl
  - トピック別 アイヌ語会話辞典 (NINJAL topical dictionary data)
  - アイヌ語鵡川方言日本語‐アイヌ語辞典 (Mukawa dialect dictionary)
- dictionary/output/tommy1949_aynudictionary.tsv
  - 富田隆 Aynu Online Dictionary parsed from the public HTML page

The source corpus rows are sentence-shaped JSONL, but these two collections are
lexical/topic dictionary data. We preserve the corpus identifiers and topic /
document labels for traceability.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AINU_PROJECTS = ROOT.parents[0]
CORPORA_JSONL = AINU_PROJECTS / "ainu-corpora" / "data.jsonl"
DICT_ROOT = AINU_PROJECTS / "ainu-dictionaries"
TOMITA_TSV = ROOT / "dictionary" / "output" / "tommy1949_aynudictionary.tsv"


TOPICAL_FOLDER = DICT_ROOT / "1898_Kanazawa_NINJAL-Topical-Ainu-Conversation-Dictionary"
MUKAWA_FOLDER = DICT_ROOT / "XXXX_Chiba_Mukawa-Dialect-Japanese-Ainu-Dictionary"
TOMITA_FOLDER = DICT_ROOT / "2021_Tomita_Aynu-Online-Dictionary"


def load_corpora_rows(collection: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with CORPORA_JSONL.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("collection_lv1") == collection:
                rows.append(row)
    return rows


def write_tsv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def import_topical() -> int:
    source_rows = load_corpora_rows("トピック別 アイヌ語会話辞典")
    rows = [
        {
            "id": row.get("id", ""),
            "lemma": row.get("text", ""),
            "translation": row.get("translation", ""),
            "topic": row.get("document", ""),
            "dialect": row.get("dialect", ""),
            "author": row.get("author", ""),
            "published_at": str(row.get("published_at") or ""),
            "uri": row.get("uri", ""),
        }
        for row in source_rows
    ]
    write_tsv(
        TOPICAL_FOLDER / "original.tsv",
        ["id", "lemma", "translation", "topic", "dialect", "author", "published_at", "uri"],
        rows,
    )
    (TOPICAL_FOLDER / "metadata.yaml").write_text(
        """type: topical-dictionary
title: トピック別 アイヌ語会話辞典
title_en: Topical Dictionary of Conversational Ainu
author:
  en: Kanazawa, Shozaburo
  ja: 金澤, 庄三郎
year: 1898
dialect:
  name: 沙流
  path: 北海道/南西/沙流
parent:
  type: database
  title: トピック別 アイヌ語会話辞典
  publisher: NINJAL
url: https://ainu.ninjal.ac.jp/topic/
source: |
  Rows copied from the local ainu-corpora aggregate (collection_lv1 =
  トピック別 アイヌ語会話辞典), preserving the original corpus id, topic label,
  author, dialect, and URI. The data is based on Kanazawa Shozaburo's 1898
  conversational Ainu material as presented by NINJAL.
columns:
  id: source row id in ainu-corpora
  lemma: Ainu entry / phrase
  translation: Japanese gloss or translation
  topic: topical section name
  dialect: dialect label from source corpus
  author: source author label
  published_at: publication year where known
  uri: source URL
""",
        encoding="utf-8",
    )
    return len(rows)


def import_mukawa() -> int:
    source_rows = load_corpora_rows("アイヌ語鵡川方言日本語‐アイヌ語辞典")
    rows = [
        {
            "id": row.get("id", ""),
            "lemma": row.get("text", ""),
            "translation": row.get("translation", ""),
            "source_speaker": row.get("document", ""),
            "author": row.get("author", ""),
            "dialect": row.get("dialect", ""),
            "uri": row.get("uri", ""),
        }
        for row in source_rows
    ]
    write_tsv(
        MUKAWA_FOLDER / "original.tsv",
        ["id", "lemma", "translation", "source_speaker", "author", "dialect", "uri"],
        rows,
    )
    (MUKAWA_FOLDER / "metadata.yaml").write_text(
        """type: japanese-ainu-dictionary
title: アイヌ語鵡川方言日本語‐アイヌ語辞典
title_en: Mukawa Dialect Japanese-Ainu Dictionary
author:
  en: Chiba, Nobue
  ja: 千葉, 伸恵
year: unknown
dialect:
  name: 鵡川
  path: 北海道/南西/鵡川
source: |
  Rows copied from the local ainu-corpora aggregate (collection_lv1 =
  アイヌ語鵡川方言日本語‐アイヌ語辞典). The corpus rows identify the source speaker
  document as either 新井田セイノ氏の言葉 or 吉村冬子氏の言葉.
columns:
  id: source row id in ainu-corpora
  lemma: Ainu entry / phrase
  translation: Japanese gloss or translation
  source_speaker: source speaker section in the corpus
  author: speaker / contributor label from corpus
  dialect: dialect label from source corpus
  uri: source URI where present
""",
        encoding="utf-8",
    )
    return len(rows)


def import_tomita() -> int:
    rows: list[dict[str, str]] = []
    with TOMITA_TSV.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            rows.append(
                {
                    "id": row.get("id", ""),
                    "lemma": row.get("lemma", ""),
                    "etymology": row.get("etymology", ""),
                    "explanation": row.get("explanation", ""),
                }
            )
    write_tsv(TOMITA_FOLDER / "original.tsv", ["id", "lemma", "etymology", "explanation"], rows)
    (TOMITA_FOLDER / "metadata.yaml").write_text(
        """type: online-dictionary
title: アイヌ語電子辞書
title_en: Aynu Online Dictionary
author:
  en: Tomita, Takashi
  ja: 富田, 隆
year: 2021
url: http://tommy1949.world.coocan.jp/aynudictionary.htm
source: |
  Parsed TSV copied from ainu-corpora-process/dictionary/output/
  tommy1949_aynudictionary.tsv. The source HTML says it was updated on
  2021-01-05 and contains 15,005 heading cells. This import preserves the
  parser's id, lemma, etymology, and explanation columns without further
  cleanup.
columns:
  id: parser row id
  lemma: headword or head phrase
  etymology: grammatical / etymological note column from source table
  explanation: Japanese explanation and examples
""",
        encoding="utf-8",
    )
    return len(rows)


def main() -> None:
    print(f"topical: {import_topical()} rows")
    print(f"mukawa: {import_mukawa()} rows")
    print(f"tomita: {import_tomita()} rows")


if __name__ == "__main__":
    main()
