"""Ingest NorthEuraLex 0.9 Hokkaido-Ainu lexicon as a new dictionary folder.

Source: https://github.com/lexibank/northeuralex
License: CC BY-SA 4.0

Joins forms.csv (Ainu rows) with parameters.csv to attach English glosses
and the Concepticon ID, then writes:
  2020_NorthEuraLex_Hokkaido-Ainu/original.tsv     (lemma, segments, value, concept_en, concept_de, concepticon)
  2020_NorthEuraLex_Hokkaido-Ainu/metadata.yaml
"""

from __future__ import annotations

import csv
import io
import urllib.request
from pathlib import Path

DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
FOLDER = DICT_ROOT / "2020_NorthEuraLex_Hokkaido-Ainu"

FORMS_URL = "https://raw.githubusercontent.com/lexibank/northeuralex/master/cldf/forms.csv"
PARAMS_URL = "https://raw.githubusercontent.com/lexibank/northeuralex/master/cldf/parameters.csv"


def fetch_csv(url: str) -> list[dict]:
    with urllib.request.urlopen(url, timeout=60) as response:
        text = response.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def main() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    forms = fetch_csv(FORMS_URL)
    params = {row["ID"]: row for row in fetch_csv(PARAMS_URL)}

    ainu_rows: list[dict] = []
    for row in forms:
        if row["Language_ID"] != "ain":
            continue
        p = params.get(row["Parameter_ID"], {})
        de_gloss = p.get("NorthEuralex_Gloss", "")
        de = de_gloss.split("::")[0] if de_gloss else ""
        ainu_rows.append(
            {
                "lemma": row["Form"],
                "lemma_raw": row["Value"],
                "segments": row["Segments"],
                "concept_id": row["Parameter_ID"],
                "concept_en": p.get("Name", ""),
                "concept_de": de,
                "concepticon": p.get("Concepticon_Gloss", ""),
                "source": row["Source"],
            }
        )

    tsv_path = FOLDER / "original.tsv"
    columns = [
        "lemma",
        "lemma_raw",
        "segments",
        "concept_en",
        "concept_de",
        "concepticon",
        "concept_id",
        "source",
    ]
    with tsv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=columns, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        for row in ainu_rows:
            writer.writerow({k: row.get(k, "") for k in columns})

    metadata = """type: comparative-wordlist
title: NorthEuraLex 0.9 — Hokkaido Ainu
title_en: NorthEuraLex 0.9 (Hokkaido Ainu subset)
author:
  en: Dellert, Johannes et al.
year: 2020
dialect:
  name: 北海道
  path: 北海道
title_original: 'NorthEuraLex: a wide-coverage lexical database of Northern Eurasia'
parent:
  type: journal-article
  title: Language Resources and Evaluation
  publisher: Springer
url: https://github.com/lexibank/northeuralex
license: CC BY-SA 4.0
source: |
  Sourced from lexibank/northeuralex master/cldf/forms.csv. Hokkaido Ainu
  (Glottocode ainu1240) is one of the 107 languages in this 1016-concept
  Northern-Eurasia lexicostatistical database. Underlying Ainu data is
  Hattori 1964 - derived.
columns:
  lemma:        Form column (CLDF) - cleaned IPA/Latin form
  lemma_raw:    Value column (CLDF) - original source spelling
  segments:     space-separated phonemic segmentation
  concept_en:   English concept name
  concept_de:   German concept name (NorthEuralex_Gloss)
  concepticon:  Concepticon gloss ID
  concept_id:   NorthEuraLex internal concept ID
  source:       upstream citation key
"""
    (FOLDER / "metadata.yaml").write_text(metadata, encoding="utf-8")
    print(f"wrote {len(ainu_rows)} Hokkaido Ainu entries to {tsv_path}")


if __name__ == "__main__":
    main()
