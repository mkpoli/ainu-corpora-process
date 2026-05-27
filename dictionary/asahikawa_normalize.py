"""Normalize Asahikawa-style romanization to standard academic Ainu orthography.

The Asahikawa Uoi articles use a personal romanization derived from older
Japanese-Ainu conventions (Kindaichi-era). Differences from the now-standard
academic notation used by Hattori 1964 / Tamura / NINJAL include:

  Asahikawa     Standard
  ---------     --------
  ch  / Ch     →  c   / C       (affricate)
  sh  / Sh     →  s   / S       (palatal sibilant)
  tch / Tch    →  cc  / Cc      (geminated affricate)
  -ai / -ei / -oi / -ui   →   -ay / -ey / -oy / -uy   (syllable-coda glide)
  -au / -eu / -iu / -ou   →   -aw / -ew / -iw / -ow   (syllable-coda glide)
  b / d / g / z / j   →   p / t / k / s / c           (voicing not phonemic)

Conservative scope: applied to the *lemma* column only. We do not rewrite the
body, since the bodies contain the original author's example sentences plus
Japanese gloss text — leaving them as-is preserves the source faithfully and
lets researchers see the dialect transcription Uoi actually published.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")

ASAHIKAWA_FOLDERS = [
    "1995_Uoi_Asahikawa-Ainu-Verbs-I",
    "1996_Uoi_Asahikawa-Ainu-Verbs-II",
    "2006_Uoi_Asahikawa-Ainu-Nouns-I",
    "2007_Uoi_Asahikawa-Ainu-Nouns-II",
]

# Digraphs (longer first so e.g. "tch" never gets touched by the "ch" rule).
DIGRAPHS = [
    ("tch", "cc"),
    ("Tch", "Cc"),
    ("TCH", "CC"),
    ("ch", "c"),
    ("Ch", "C"),
    ("CH", "C"),
    ("sh", "s"),
    ("Sh", "S"),
    ("SH", "S"),
]

# Voiced ↔ voiceless consonant pairs. Ainu has no phonemic voicing distinction;
# Asahikawa transcription often writes the surface-voiced reflex.
VOICED_MAP = str.maketrans({
    "b": "p", "B": "P",
    "d": "t", "D": "T",
    "g": "k", "G": "K",
    "z": "s", "Z": "S",
    "j": "c", "J": "C",
})

# Coda glides: V[iu] at end of syllable → V[yw].
# In single-token Ainu lemmas the only place vowel + i/u survives finally or
# before another consonant is exactly the coda position.
CODA_I = re.compile(r"([aeou])i(?=$|[^aeiouAEIOU])")
CODA_U = re.compile(r"([aeio])u(?=$|[^aeiouAEIOU])")


def normalize(lemma: str) -> str:
    s = lemma
    for old, new in DIGRAPHS:
        s = s.replace(old, new)
    s = s.translate(VOICED_MAP)
    s = CODA_I.sub(r"\1y", s)
    s = CODA_U.sub(r"\1w", s)
    return s


def process_folder(folder: Path) -> tuple[int, int]:
    tsv_path = folder / "original.tsv"
    rows = list(csv.reader(tsv_path.open(encoding="utf-8"), delimiter="\t"))
    header, *data = rows
    if "lemma_normalized" in header:
        # Replace existing column rather than duplicate.
        idx = header.index("lemma_normalized")
    else:
        idx = None
    lemma_idx = header.index("lemma")
    out_rows: list[list[str]] = []
    new_header = list(header)
    if idx is None:
        new_header.insert(lemma_idx + 1, "lemma_normalized")
    out_rows.append(new_header)
    changed = 0
    for row in data:
        # Pad short rows.
        while len(row) < len(header):
            row.append("")
        lemma = row[lemma_idx]
        norm = normalize(lemma)
        if norm != lemma:
            changed += 1
        if idx is None:
            row = list(row)
            row.insert(lemma_idx + 1, norm)
        else:
            row[idx] = norm
        out_rows.append(row)
    with tsv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerows(out_rows)
    return len(data), changed


def main() -> None:
    for name in ASAHIKAWA_FOLDERS:
        folder = DICT_ROOT / name
        if not folder.exists():
            print(f"skip {name}: folder missing")
            continue
        total, changed = process_folder(folder)
        print(f"{name}: {total} rows, {changed} lemmas normalized")


if __name__ == "__main__":
    main()
