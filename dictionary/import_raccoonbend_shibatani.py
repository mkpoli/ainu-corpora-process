"""Import RaccoonBend's Shibatani-derived Ainu-English word list."""

from __future__ import annotations

import csv
import html
import re
import urllib.request
from pathlib import Path


DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
FOLDER = DICT_ROOT / "1990_Shibatani_RaccoonBend-Ainu-English-Wordlist"
URL = "https://www.raccoonbend.com/languages/ainuenglish.html"


def fetch() -> str:
    with urllib.request.urlopen(URL, timeout=30) as response:
        return response.read().decode("iso-8859-1", errors="replace")


def split_cell(cell: str) -> list[str]:
    cell = re.sub(r"<br\s*/?>", "\n", cell, flags=re.IGNORECASE)
    cell = re.sub(r"<[^>]+>", "", cell)
    cell = html.unescape(cell)
    return [re.sub(r"\s+", " ", line).strip() for line in cell.splitlines() if line.strip()]


def parse(text: str) -> list[dict[str, str]]:
    cells = re.findall(r"<td[^>]*>(.*?)</td>", text, flags=re.IGNORECASE | re.DOTALL)
    if len(cells) < 2:
        raise RuntimeError("Could not find the two list table cells")
    lemmas = split_cell(cells[0])
    meanings = split_cell(cells[1])
    rows = []
    for idx, (lemma, meaning) in enumerate(zip(lemmas, meanings), start=1):
        rows.append({"id": str(idx), "lemma": lemma, "meaning_en": meaning})
    return rows


def main() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    text = fetch()
    (FOLDER / "raw.html").write_text(text, encoding="utf-8")
    rows = parse(text)
    with (FOLDER / "original.tsv").open("w", encoding="utf-8", newline="") as fh:
        columns = ["id", "lemma", "meaning_en"]
        writer = csv.DictWriter(fh, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (FOLDER / "metadata.yaml").write_text(
        """type: wordlist
title: Ainu-English Word List
title_en: RaccoonBend Ainu-English Word List (from Shibatani 1990)
author:
  en: Wright, Mike
  ja: ライト, マイク
year: 1990
url: https://www.raccoonbend.com/languages/ainuenglish.html
source: |
  Scraped from RaccoonBend's Ainu-English Word List. The page states that the
  words and meanings were extracted from Masayoshi Shibatani, The Languages of
  Japan (Cambridge University Press, 1990), with hyphens omitted and with mixed
  classical/colloquial Ainu and mixed Sakhalin/Hokkaido dialect material.
columns:
  id: row order in the HTML list
  lemma: Ainu form as printed by RaccoonBend
  meaning_en: English gloss as printed by RaccoonBend
""",
        encoding="utf-8",
    )
    print(f"wrote {len(rows)} RaccoonBend/Shibatani entries to {FOLDER / 'original.tsv'}")


if __name__ == "__main__":
    main()
