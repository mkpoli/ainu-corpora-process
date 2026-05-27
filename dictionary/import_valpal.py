"""Ingest Bugaeva's Ainu (Southern Hokkaido) valency data from ValPaL.

Source: https://github.com/lexibank/valpal (CC BY 3.0)
Description: Hartmann et al.'s "Valency Patterns Leipzig" CLDF dataset.
The Ainu contribution is by Anna Bugaeva (Southern Hokkaido / Saru) and
covers ~80 verb meanings with their valency frames.

Each row corresponds to one verb meaning in ValPaL; the Form/Value column
gives the Ainu verb form. Coding-frame IDs are large opaque identifiers
that ValPaL uses internally; left as a column in the TSV for traceability.
"""

from __future__ import annotations

import csv
import io
import urllib.request
from pathlib import Path

DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
FOLDER = DICT_ROOT / "2013_Bugaeva_ValPaL-Ainu-Verbs"

FORMS_URL = "https://raw.githubusercontent.com/lexibank/valpal/master/cldf/forms.csv"
PARAMS_URL = "https://raw.githubusercontent.com/lexibank/valpal/master/cldf/parameters.csv"


def fetch_csv(url: str) -> list[dict]:
    with urllib.request.urlopen(url, timeout=120) as response:
        text = response.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def main() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    forms = fetch_csv(FORMS_URL)
    params = {row["ID"]: row for row in fetch_csv(PARAMS_URL)}

    rows: list[dict] = []
    for row in forms:
        if row["Language_ID"] != "ainu1240":
            continue
        p = params.get(row["Parameter_ID"], {})
        rows.append(
            {
                "lemma": row["Form"],
                "lemma_raw": row["Value"],
                "meaning_en": p.get("Name", row["Parameter_ID"]),
                "concepticon": p.get("Concepticon_Gloss", ""),
                "verb_type": row.get("verb_type", ""),
                "simplex_or_complex": row.get("simplex_or_complex", ""),
                "comment": row.get("Comment", ""),
                "coding_frame_id": row.get("Basic_Coding_Frame_ID", ""),
                "typical_context": p.get("typical_context", ""),
                "role_frame": p.get("role_frame", ""),
            }
        )

    columns = [
        "lemma",
        "lemma_raw",
        "meaning_en",
        "concepticon",
        "verb_type",
        "simplex_or_complex",
        "comment",
        "coding_frame_id",
        "typical_context",
        "role_frame",
    ]
    tsv_path = FOLDER / "original.tsv"
    with tsv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for r in rows:
            writer.writerow(
                {
                    c: (r.get(c, "") or "")
                    .replace("\n", " ")
                    .replace("\t", " ")
                    .replace("\r", " ")
                    for c in columns
                }
            )

    metadata = """type: valency-dataset
title: Ainu (Southern Hokkaido) — Valency Patterns Leipzig
title_en: ValPaL — Ainu (Southern Hokkaido)
author:
  en: Bugaeva, Anna
  ja: ブガエワ, アンナ
year: 2013
dialect:
  name: 沙流
  path: 北海道/南西/沙流
parent:
  type: chapter
  title: Valency Patterns Leipzig
  publisher: lexibank / clld (Hartmann et al.)
url: https://valpal.info/contributions/ainu1240
license: CC BY 3.0
source: |
  ~80 verb meanings with valency frames. Originally curated by Anna Bugaeva
  (2013). Fetched from lexibank/valpal master/cldf/forms.csv. Each row gives
  the Ainu lexicalization of a ValPaL verb meaning, plus the original
  meaning's role frame, typical context, and the upstream Basic Coding Frame
  ID for cross-reference.
columns:
  lemma:              cleaned form (CLDF Form column)
  lemma_raw:          original Value column (sometimes shows SG/PL alternation)
  meaning_en:         ValPaL meaning name in English
  concepticon:        Concepticon gloss
  verb_type:          ValPaL classification (where given)
  simplex_or_complex: Simplex / Complex (for derived forms)
  comment:            Bugaeva's commentary, often including morphological derivation
  coding_frame_id:    upstream ValPaL Basic_Coding_Frame_ID
  typical_context:    canonical sentence template for the meaning
  role_frame:         ValPaL role-frame template (e.g. 'S appears')
"""
    (FOLDER / "metadata.yaml").write_text(metadata, encoding="utf-8")
    print(f"wrote {len(rows)} Ainu valency entries to {tsv_path}")


if __name__ == "__main__":
    main()
