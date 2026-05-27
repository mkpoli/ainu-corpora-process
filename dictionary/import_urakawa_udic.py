"""Scrape the private Urakawa Ainu dictionary HTML pages.

Source: http://city.hokkai.or.jp/~ayaedu/udic/udic0.html

The site presents category pages `udic1.html` ... `udic8.html`, each with a
two-column HTML table: Ainu (katakana) and Japanese. The underlying source is
the 1985 booklet `続浦河地方のアイヌ語` (Hidaka Board of Education / Hokkaido
Utari Association Urakawa branch), based on interviews with Urakawa Riu and
Toyama Saki.
"""

from __future__ import annotations

import csv
import html
import re
import urllib.request
from pathlib import Path


DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
FOLDER = DICT_ROOT / "1985_Urakawa_Private-Ainu-Dictionary"
BASE_URL = "http://city.hokkai.or.jp/~ayaedu/udic"

CATEGORIES = {
    1: "日常生活に関する用語",
    2: "天候に関する用語",
    3: "刀剣に関する用語",
    4: "用具・衣類・織物に関する用語",
    5: "動物・虫鳥・魚に関する用語",
    6: "食用・植物・酒に関する用語",
    7: "木・水・海に関する用語",
    8: "祝・祭り・葬・祈りに関する用語",
}


def fetch(page: int) -> str:
    url = f"{BASE_URL}/udic{page}.html"
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read().decode("shift_jis", errors="replace")


def clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def cell_items(td_html: str) -> list[str]:
    # Entries are in <P>...</P>; some malformed source cells omit a closing P,
    # so split on opening P tags and then strip any remaining tags.
    parts = re.split(r"<P[^>]*>", td_html, flags=re.IGNORECASE)
    items: list[str] = []
    for part in parts[1:]:
        item = clean_text(part.split("</P>", 1)[0])
        if item:
            items.append(item)
    return items


def parse_page(page: int, text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    # Match table data rows after the header. Each data row has two TD cells,
    # left = Ainu, right = Japanese, with aligned <P> items.
    for tr in re.findall(r"<TR>(.*?)</TR>", text, flags=re.IGNORECASE | re.DOTALL):
        cells = re.findall(r"<TD[^>]*>(.*?)</TD>", tr, flags=re.IGNORECASE | re.DOTALL)
        if len(cells) != 2:
            continue
        if "アイヌ語" in cells[0] and "日本語" in cells[1]:
            continue
        ainu_items = cell_items(cells[0])
        ja_items = cell_items(cells[1])
        for idx, (lemma, gloss) in enumerate(zip(ainu_items, ja_items), start=1):
            rows.append(
                {
                    "lemma_kana": lemma,
                    "gloss_ja": gloss,
                    "category": CATEGORIES[page],
                    "source_page": f"udic{page}.html",
                    "row_in_table": str(idx),
                }
            )
    return rows


def main() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    raw_dir = FOLDER / "raw"
    raw_dir.mkdir(exist_ok=True)
    for page in range(1, 9):
        text = fetch(page)
        (raw_dir / f"udic{page}.html").write_text(text, encoding="utf-8")
        rows.extend(parse_page(page, text))

    with (FOLDER / "original.tsv").open("w", encoding="utf-8", newline="") as fh:
        columns = ["lemma_kana", "gloss_ja", "category", "source_page", "row_in_table"]
        writer = csv.DictWriter(fh, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    (FOLDER / "metadata.yaml").write_text(
        """type: dictionary
title: ＜私家版＞浦河アイヌ語辞典
title_en: Private Urakawa Ainu Dictionary
author:
  en: unknown
  ja: 不明
year: 1985
dialect:
  name: 浦河
  path: 北海道/南西/日高/浦河
url: http://city.hokkai.or.jp/~ayaedu/udic/udic0.html
source: |
  Scraped from the private HTML dictionary hosted at city.hokkai.or.jp. The
  site says it reorganizes the 1985 booklet 『続浦河地方のアイヌ語』, published by
  北海道教育長日高教育局 and planned/edited by 北海道ウタリ協会浦河支部. The booklet is based
  on interviews with 浦河リウ (born 1921, Urakawa Anecha) and 遠山サキ (born
  1928). Entries are preserved as printed in katakana.
columns:
  lemma_kana: Ainu form in the site's katakana notation
  gloss_ja: Japanese gloss
  category: source category page heading
  source_page: source HTML page name
  row_in_table: order within the source table row pairing
""",
        encoding="utf-8",
    )
    print(f"wrote {len(rows)} Urakawa entries to {FOLDER / 'original.tsv'}")


if __name__ == "__main__":
    main()
