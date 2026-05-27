"""Ingest the Ainu column from pannous/swadesh multi-language Swadesh list.

Source: https://github.com/pannous/swadesh/blob/master/ainu.tsv
This file is a comparison Swadesh table covering Ainu, Nivkh, Yukaghir,
Chukchi, Koryak, Aliutor, Kerek, Itelmen, Yupik — and a PIE column. We
extract just the (English meaning, Ainu form) pair for our collection.
"""

from __future__ import annotations

import csv
import io
import re
import urllib.request
from pathlib import Path

DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
FOLDER = DICT_ROOT / "XXXX_PannousSwadesh_Ainu-Swadesh"
URL = "https://raw.githubusercontent.com/pannous/swadesh/master/ainu.tsv"


def fetch() -> str:
    with urllib.request.urlopen(URL, timeout=60) as response:
        return response.read().decode("utf-8")


def main() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    raw = fetch()
    (FOLDER / "source.tsv").write_text(raw, encoding="utf-8")

    rows: list[dict[str, str]] = []
    for record in csv.DictReader(io.StringIO(raw), delimiter="\t"):
        # Header has trailing spaces; normalise. DictReader may yield list
        # values for fields beyond the header count (under restkey); cast
        # everything to a string defensively.
        record = {
            (k or "").strip(): (
                (" ".join(v).strip() if isinstance(v, list) else (v or "").strip())
            )
            for k, v in record.items()
        }
        # First column is the row number header "№"; skip pure-header echoes.
        num = record.get("№", "")
        if not num or not num.strip():
            continue
        en = record.get("English", "")
        ain = record.get("Ainu", "")
        if not en and not ain:
            continue
        rows.append({"num": num, "concept_en": en, "ain": ain})

    tsv_path = FOLDER / "original.tsv"
    with tsv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(["num", "concept_en", "ain"])
        for r in rows:
            writer.writerow([r["num"], r["concept_en"], r["ain"]])

    metadata = """type: comparative-wordlist
title: pannous/swadesh — Ainu column
title_en: Ainu Swadesh (pannous/swadesh GitHub TSV)
author:
  en: Pannous (compiler), various
year: ~2014
dialect:
  name: 北海道
  path: 北海道
parent:
  type: github-repo
  title: pannous/swadesh
  publisher: GitHub
url: https://github.com/pannous/swadesh
license: see upstream repository
source: |
  Multi-language Swadesh comparison TSV maintained by pannous on GitHub.
  Includes a single Ainu column alongside Nivkh, Yukaghir, Chukchi, Koryak,
  Aliutor, Kerek, Itelmen, Yupik, and a PIE column for comparative work.
  Ainu forms appear to be drawn from a mix of sources (Hattori, Tamura,
  Batchelor); the original repository does not document its citations.
columns:
  num:        Swadesh number from the upstream TSV
  concept_en: English meaning
  ain:        Ainu form(s) as printed in the source row (may be a comma-
              separated alternation, e.g. "ku-, kani")
"""
    (FOLDER / "metadata.yaml").write_text(metadata, encoding="utf-8")
    print(f"wrote {len(rows)} pannous-swadesh Ainu entries to {tsv_path}")


if __name__ == "__main__":
    main()
