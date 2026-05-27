"""Ingest Vovin's Proto-Ainu reconstructions via the ABVD Swadesh database.

Source: Austronesian Basic Vocabulary Database (ABVD),
        https://abvd.eva.mpg.de/austronesian/language.php?id=828
Original: Vovin, Alexander. 1993. A Reconstruction of Proto-Ainu.
          Leiden: E. J. Brill. (Brill's Japanese Studies Library, vol. 4)

ABVD provides Vovin's reconstructions in a clean CSV: ~224 reconstructed
entries for 200+ Swadesh meanings with the original tonal annotation
(H/L), alternative forms, and loan/cognacy notes.
"""

from __future__ import annotations

import csv
import io
import urllib.request
from pathlib import Path

DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
FOLDER = DICT_ROOT / "1993_Vovin_Proto-Ainu-ABVD"
ABVD_URL = "https://abvd.eva.mpg.de/utils/save/?type=csv&section=austronesian&language=828"


def fetch_abvd() -> str:
    with urllib.request.urlopen(ABVD_URL, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def parse(text: str) -> list[dict[str, str]]:
    """ABVD CSV layout:
        line 1: bibliographic header
        line 2: latitude/longitude header
        line 3: lat/long values
        line 4: data header (id,word_id,word,item,annotation,loan,cognacy,pmpcognacy)
        line 5+: data rows
    """
    reader = csv.reader(io.StringIO(text))
    rows_iter = iter(reader)
    rows: list[dict[str, str]] = []
    columns: list[str] | None = None
    for raw in rows_iter:
        if raw and raw[0] == "id" and len(raw) > 3 and raw[3] == "item":
            columns = raw
            break
    if columns is None:
        raise ValueError("Could not locate data header in ABVD CSV")
    for raw in rows_iter:
        if len(raw) < len(columns):
            continue
        record = dict(zip(columns, raw))
        rows.append(record)
    return rows


def main() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    raw = fetch_abvd()
    (FOLDER / "source.csv").write_text(raw, encoding="utf-8")
    rows = parse(raw)

    out_columns = [
        "word_id",
        "concept_en",
        "reconstruction",
        "annotation",
        "loan",
        "cognacy",
    ]
    tsv_path = FOLDER / "original.tsv"
    with tsv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(out_columns)
        for r in rows:
            writer.writerow(
                [
                    r.get("word_id", ""),
                    r.get("word", ""),
                    r.get("item", ""),
                    r.get("annotation", "").replace("\n", " "),
                    r.get("loan", ""),
                    r.get("cognacy", ""),
                ]
            )

    metadata = """type: comparative-wordlist
title: A Reconstruction of Proto-Ainu (ABVD extract)
title_en: Vovin 1993 Proto-Ainu reconstructions (ABVD)
author:
  en: Vovin, Alexander
year: 1993
dialect:
  name: Proto-Ainu
  path: 祖アイヌ
parent:
  type: book
  title: A Reconstruction of Proto-Ainu
  publisher: 'E. J. Brill (Brill''s Japanese Studies Library, vol. 4)'
  isbn: 90-04-09905-0
url: https://abvd.eva.mpg.de/austronesian/language.php?id=828
license: ABVD distributes Swadesh-list extracts; original work © Brill 1993
source: |
  Andrew C. Hsiu's keyed-in Swadesh-list extraction of Vovin 1993, hosted by
  the Austronesian Basic Vocabulary Database (Max Planck Institute for
  Evolutionary Anthropology). Each row carries one Proto-Ainu reconstruction;
  many concepts have multiple alternative reconstructions encoded as separate
  rows sharing the same word_id. The annotation column preserves the H/L tonal
  marking and any alternative-form notes from Vovin's original entries.
columns:
  word_id:        ABVD concept number (shared across alternatives for the same gloss)
  concept_en:     English gloss
  reconstruction: Proto-Ainu reconstruction (Vovin's notation, e.g. *tE(=)k)
  annotation:    tonal marks (H/L) and Vovin's alternative-form notes
  loan:          loan-source flag (empty if not a loan)
  cognacy:       ABVD cognate-class flag
"""
    (FOLDER / "metadata.yaml").write_text(metadata, encoding="utf-8")
    print(f"wrote {len(rows)} Vovin 1993 reconstructions (via ABVD) to {tsv_path}")


if __name__ == "__main__":
    main()
