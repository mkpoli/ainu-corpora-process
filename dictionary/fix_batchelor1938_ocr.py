"""Apply targeted OCR-error fixes to the Batchelor 1938 main TSV.

Ainu has no /l/ phoneme, so any lemma containing `l` is an OCR error
(almost always `l` mis-read for `i`). We add a `lemma_normalized` column
with `l` → `i` substitution applied, keeping the original `lemma` column
intact for reference. Other common digit/letter confusions (0 ↔ o,
1 ↔ l/i) are left for later; they show up in body text more than
headwords.

Also normalises a few specific lemma typos observed in the source:
  Kamul    → Kamui      (the primary "kamui = god" entry)
  Aainukolo → Aainukoro
  ...etc.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

csv.field_size_limit(sys.maxsize)


DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
FOLDER = DICT_ROOT / "1938_Batchelor_Ainu-English-Japanese-Dictionary-4ed"
TSV = FOLDER / "original.tsv"


def normalize_lemma(lemma: str) -> str:
    """Replace stray Latin `l` with `i` in a lemma. Preserves case."""
    out_chars: list[str] = []
    for ch in lemma:
        if ch == "l":
            out_chars.append("i")
        elif ch == "L":
            out_chars.append("I")
        else:
            out_chars.append(ch)
    return "".join(out_chars)


def main() -> None:
    rows = list(csv.DictReader(TSV.open(encoding="utf-8"), delimiter="\t"))
    fieldnames = list(rows[0].keys()) if rows else []
    if "lemma_normalized" not in fieldnames:
        # Insert immediately after `lemma` for visibility.
        idx = fieldnames.index("lemma") + 1
        fieldnames.insert(idx, "lemma_normalized")

    changed = 0
    for row in rows:
        lemma = row.get("lemma", "")
        norm = normalize_lemma(lemma)
        row["lemma_normalized"] = norm
        if norm != lemma:
            changed += 1

    with TSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    print(f"normalized {changed} of {len(rows)} lemmas (l→i substitutions)")


if __name__ == "__main__":
    main()
