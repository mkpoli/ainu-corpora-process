"""Ingest the Ainu CSV from loanwordbank/wiktionary_cldf.

Source: https://github.com/loanwordbank/wiktionary_cldf
Path: raw2/ainu.csv
Layout: L2_orth, L2_ipa, L2_gloss, L2_etym (one Ainu lemma per row, with IPA
        pronunciation, English gloss, and an etymology note when available).
"""

from __future__ import annotations

import csv
import io
import urllib.request
from pathlib import Path


DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
FOLDER = DICT_ROOT / "XXXX_Loanwordbank_Wiktionary-Ainu"
URL = "https://raw.githubusercontent.com/loanwordbank/wiktionary_cldf/master/raw2/ainu.csv"


def main() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(URL, timeout=30) as response:
        raw = response.read().decode("utf-8", errors="replace")
    (FOLDER / "raw.csv").write_text(raw, encoding="utf-8")

    reader = csv.DictReader(io.StringIO(raw))
    rows: list[dict[str, str]] = []
    for record in reader:
        rows.append(
            {
                "lemma": (record.get("L2_orth") or "").strip(),
                "ipa": (record.get("L2_ipa") or "").strip(),
                "gloss_en": (record.get("L2_gloss") or "").strip(),
                "etymology": (record.get("L2_etym") or "").strip(),
            }
        )

    out = FOLDER / "original.tsv"
    with out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["lemma", "ipa", "gloss_en", "etymology"],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    (FOLDER / "metadata.yaml").write_text(
        """type: wordlist
title: Loanwordbank Wiktionary Ainu CSV
title_en: Loanwordbank Wiktionary-derived Ainu wordlist
author:
  en: Loanwordbank contributors / English Wiktionary
url: https://github.com/loanwordbank/wiktionary_cldf
license: CC BY-SA (per Wiktionary)
source: |
  Parsed extraction of the English Wiktionary's Ainu section by the
  loanwordbank project. Provides headword, IPA pronunciation, English gloss,
  and optional etymology note. Useful as a cross-check against the existing
  XXXX_English-Wiktionary entries.
columns:
  lemma: Ainu headword as in the Wiktionary page title
  ipa: IPA pronunciation (in brackets / slashes as printed)
  gloss_en: English gloss
  etymology: etymology note when present
""",
        encoding="utf-8",
    )
    print(f"wrote {len(rows)} Loanwordbank Ainu entries to {out}")


if __name__ == "__main__":
    main()
