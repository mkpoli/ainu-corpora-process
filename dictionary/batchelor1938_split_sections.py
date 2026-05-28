"""Split the Batchelor 1938 re-OCR TSV into Ainu→Eng/Ja and English→Ainu.

Pages 1-581 are the main Ainu→English/Japanese dictionary; pages 582-680
are the English→Ainu reverse vocabulary. The Gemini re-OCR pass produced
both halves in a single TSV; split them so the main `original.tsv` only
contains Ainu headwords and the new
`1938_Batchelor_English-Ainu-Vocabulary-4ed/original.tsv` has the English
headwords (replacing the older bbox-parse version of the same back matter).
"""

from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

csv.field_size_limit(sys.maxsize)

DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
MAIN = DICT_ROOT / "1938_Batchelor_Ainu-English-Japanese-Dictionary-4ed"
ENG = DICT_ROOT / "1938_Batchelor_English-Ainu-Vocabulary-4ed"
MAIN_TSV = MAIN / "original.tsv"
MAIN_BACKUP = MAIN / "original.combined.tsv"

ENG_PAGE_START = 582  # inclusive


def main() -> None:
    if not MAIN_BACKUP.exists():
        shutil.copy2(MAIN_TSV, MAIN_BACKUP)

    with MAIN_BACKUP.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        fieldnames = list(reader.fieldnames or [])
        ainu_rows: list[dict[str, str]] = []
        eng_rows: list[dict[str, str]] = []
        for row in reader:
            page = int(row.get("page") or 0)
            if page >= ENG_PAGE_START:
                eng_rows.append(row)
            else:
                ainu_rows.append(row)

    # Overwrite the main TSV with just the Ainu-section rows.
    with MAIN_TSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(ainu_rows)

    # Write the English back-matter as a sibling dictionary. Drop the
    # `lemma_normalized` column (it normalizes English words pointlessly)
    # and keep lemma/kana/body/page; rename for clarity.
    ENG.mkdir(parents=True, exist_ok=True)
    eng_out = ENG / "original.tsv"
    eng_backup = ENG / "original.bbox.tsv"
    if eng_out.exists() and not eng_backup.exists():
        shutil.copy2(eng_out, eng_backup)
    eng_fieldnames = ["english_lemma", "ainu_kana", "ainu_translations", "page"]
    with eng_out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=eng_fieldnames, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for row in eng_rows:
            w.writerow(
                {
                    "english_lemma": row.get("lemma", ""),
                    "ainu_kana": row.get("kana", ""),
                    "ainu_translations": row.get("body", ""),
                    "page": row.get("page", ""),
                }
            )

    print(
        f"split: {len(ainu_rows)} Ainu-section rows → {MAIN_TSV}\n"
        f"       {len(eng_rows)} English-section rows → {eng_out}\n"
        f"backup: {MAIN_BACKUP}"
    )


if __name__ == "__main__":
    main()
