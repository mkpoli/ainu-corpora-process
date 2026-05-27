"""Import Ainu numerals table from Omniglot.

Source: https://www.omniglot.com/language/numbers/ainu.htm
Author: Simon Ager
"""

from __future__ import annotations

import csv
import html
import re
import urllib.request
from pathlib import Path


DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
FOLDER = DICT_ROOT / "XXXX_Omniglot_Ainu-Numerals"
URL = "https://www.omniglot.com/language/numbers/ainu.htm"


def clean(text: str) -> str:
    text = re.sub(r"<br\s*/?>", " | ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def main() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(URL, timeout=30) as response:
        text = response.read().decode("utf-8", errors="replace")
    (FOLDER / "raw.html").write_text(text, encoding="utf-8")

    rows: list[tuple[str, str, str]] = []
    in_table = False
    current: list[str] = []
    for tr_block in re.split(r"<tr\b[^>]*>", text, flags=re.IGNORECASE)[1:]:
        cells = re.findall(r"<t[hd]\b[^>]*>(.*?)</t[hd]>", tr_block, flags=re.IGNORECASE | re.DOTALL)
        if not cells:
            continue
        cleaned = [clean(c) for c in cells]
        if cleaned[0].lower() in {"numeral", "number"}:
            in_table = True
            continue
        if not in_table:
            continue
        if len(cleaned) < 3:
            continue
        numeral, cardinal, ordinal = cleaned[0], cleaned[1], cleaned[2]
        if not numeral or not cardinal:
            continue
        rows.append((numeral, cardinal, ordinal))

    out = FOLDER / "original.tsv"
    with out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(["numeral", "cardinal", "ordinal"])
        writer.writerows(rows)

    (FOLDER / "metadata.yaml").write_text(
        """type: wordlist
title: Ainu numerals (Omniglot)
title_en: Ainu numerals — Omniglot
author:
  en: Ager, Simon
year: 2021
url: https://www.omniglot.com/language/numbers/ainu.htm
source: |
  Scraped from Omniglot's Ainu numbers page. Cardinal and ordinal forms in
  Latin and katakana for 1-10, decades 20-90, 100, 1,000 and 10,000.
columns:
  numeral: Arabic numeral / value
  cardinal: cardinal form (Latin / katakana with optional IPA pronunciation)
  ordinal: ordinal form (Latin / katakana)
""",
        encoding="utf-8",
    )
    print(f"wrote {len(rows)} Omniglot Ainu numeral rows to {out}")


if __name__ == "__main__":
    main()
