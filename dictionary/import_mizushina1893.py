"""Ingest Mizushina 1893 Kuril Ainu meteorological wordlist.

Source: GitHub Gist https://gist.github.com/mkpoli/eea296bbc85e539c7bfdaf89d633cea7
Original: 水科七三郎『北海氣象鎖談（承前）』, 氣象集誌 vol.11 issue 9,
          1893-09 (published while surveying meteorology in Hokkaidō; the
          Kuril (Shikotan) wordlist comes from Mizushina's 1891-10 visit).
DOI: 10.2151/jmsj1882.11.9_394

The gist is a Markdown table with two side-by-side (Japanese gloss, Ainu
word) pairs per row, so each markdown row yields up to two TSV rows.
"""

from __future__ import annotations

import csv
import re
import urllib.request
from pathlib import Path

DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
FOLDER = DICT_ROOT / "1893_Mizushina_Kuril-Ainu-Meteorology"
GIST_URL = "https://gist.githubusercontent.com/mkpoli/eea296bbc85e539c7bfdaf89d633cea7/raw"


def fetch_gist() -> str:
    with urllib.request.urlopen(GIST_URL, timeout=60) as response:
        return response.read().decode("utf-8")


def parse(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    in_table = False
    for line in text.splitlines():
        # Skip until first table row.
        if not in_table:
            if line.startswith("| 譯語"):
                in_table = True
            continue
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        # Skip the column-delimiter row ("|---|---|...").
        if all(re.fullmatch(r"-+", c) for c in cells if c):
            continue
        # Expected layout: [jpn1, ain1, spacer, jpn2, ain2] (5 cells)
        if len(cells) < 5:
            continue
        for jpn, ain in [(cells[0], cells[1]), (cells[3], cells[4])]:
            if not jpn and not ain:
                continue
            if not ain:
                # Sometimes a meaning has no Ainu equivalent recorded; still keep it
                # so the wordlist's coverage is documented.
                rows.append({"jpn": jpn, "ain": ""})
            else:
                rows.append({"jpn": jpn, "ain": ain})
    return rows


def main() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    text = fetch_gist()
    (FOLDER / "source.md").write_text(text, encoding="utf-8")
    rows = parse(text)

    tsv_path = FOLDER / "original.tsv"
    with tsv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(["jpn", "ain"])
        for r in rows:
            writer.writerow([r["jpn"], r["ain"]])

    metadata = """type: wordlist
title: 北海氣象鎖談（承前）千島色丹アイヌ気象・計数語彙
title_en: Kuril Ainu meteorological & numeric wordlist (Mizushina 1893)
author:
  en: Mizushina, Shichisaburo
  ja: 水科, 七三郎
year: 1893
dialect:
  name: 千島 (色丹)
  path: 千島
parent:
  type: journal-article
  title: 氣象集誌
  publisher: 日本気象学会
  volume: 11
  issue: 9
  pages: 380-389
doi: 10.2151/jmsj1882.11.9_394
url: https://gist.github.com/mkpoli/eea296bbc85e539c7bfdaf89d633cea7
source: |
  Mizushina collected this on his 1891-10 visit to Shikotan island, where
  the Meiji government had relocated Northern-Kuril Ainu from Shumshu (占守)
  in 1884. The article frames the list against the Hokkaidō Ainu vocabulary
  he had published earlier (vol.10 no.9). The list covers meteorology,
  natural phenomena, calendar, and numerals.
columns:
  jpn:  Japanese gloss (譯語) as printed in the article
  ain:  Kuril Ainu form in katakana (土人語) as printed in the article
"""
    (FOLDER / "metadata.yaml").write_text(metadata, encoding="utf-8")
    print(f"wrote {len(rows)} Kuril Ainu (Mizushina 1893) entries to {tsv_path}")


if __name__ == "__main__":
    main()
