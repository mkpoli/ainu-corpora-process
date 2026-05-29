"""Apply manual_matches to modern_correspondence.tsv.

Reads the existing TSV, and for every row whose `match_modern_source`
is empty AND whose `batchelor_lemma` appears in MANUAL_MATCHES, fills in
the manual entry with match_kind="manual".
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from dictionary.batchelor1938_manual_matches import MANUAL_MATCHES

csv.field_size_limit(sys.maxsize)

DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
TSV = (
    DICT_ROOT
    / "1938_Batchelor_Ainu-English-Japanese-Dictionary-4ed"
    / "modern_correspondence.tsv"
)


def main() -> None:
    # Index by both exact lemma and trailing-comma-stripped form so we
    # match entries like "Nushiromare," from the TSV against "Nushiromare"
    # in the manual_matches table.
    manual_map: dict[str, tuple] = {}
    for row in MANUAL_MATCHES:
        manual_map[row[0]] = row
        manual_map[row[0].rstrip(",.; ")] = row

    with TSV.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    applied = 0
    for row in rows:
        if row.get("match_modern_source"):
            continue
        lemma = row.get("batchelor_lemma", "")
        key = manual_map.get(lemma) or manual_map.get(lemma.rstrip(",.; "))
        if key:
            _, mod_lemma, mod_source, mod_def, conf = key
            row["match_modern_lemma"] = mod_lemma
            row["match_modern_kana"] = ""
            row["match_modern_source"] = mod_source
            row["match_modern_definition"] = mod_def
            row["match_kind"] = "manual"
            row["confidence"] = f"{conf:.2f}"
            applied += 1

    with TSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    matched = sum(1 for r in rows if r.get("match_modern_source"))
    print(
        f"applied {applied} manual matches "
        f"({len(MANUAL_MATCHES)} entries in MANUAL_MATCHES); "
        f"total matched now {matched}/{len(rows)} "
        f"({100*matched/len(rows):.1f}%)"
    )


if __name__ == "__main__":
    main()
