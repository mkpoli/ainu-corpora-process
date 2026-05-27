"""Import TranslationDirectory's Ainu-English wordlist (Wikipedia-derived, GFDL).

Source: https://www.translationdirectory.com/dictionaries/dictionary036.php
Provenance note from the page itself:
  "Most of the content of this page was taken from the equivalent
   Japanese-language article, accessed March 27, 2006."
Under the GNU Free Documentation License (Wikipedia GFDL legacy).
"""

from __future__ import annotations

import csv
import html
import re
import urllib.request
from pathlib import Path


DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
FOLDER = DICT_ROOT / "2009_TranslationDirectory_Wikipedia-Ainu-English"
URL = "https://www.translationdirectory.com/dictionaries/dictionary036.php"

LI_RE = re.compile(r"<li>(.*?)</li>", re.IGNORECASE | re.DOTALL)
SECTION_RE = re.compile(r'<h3[^>]*>(?P<letter>[A-Z])\s*</h3>', re.IGNORECASE)
ENTRY_RE = re.compile(
    r"^\s*(?P<lemma>[A-Za-z][\w\-'’ ]*?)\s*(?:\((?P<kana>[^)]*)\))?\s*[-—–]\s*(?P<def>.+?)\s*$",
    re.DOTALL,
)


def fetch() -> str:
    with urllib.request.urlopen(URL, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def main() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    text = fetch()
    (FOLDER / "raw.html").write_text(text, encoding="utf-8")

    # Track which letter section each <li> belongs to by interleaving
    # SECTION_RE/LI_RE matches in source-order.
    events: list[tuple[int, str, str]] = []
    for m in SECTION_RE.finditer(text):
        events.append((m.start(), "section", m["letter"].upper()))
    for m in LI_RE.finditer(text):
        events.append((m.start(), "li", m.group(1)))
    events.sort()

    rows: list[dict[str, str]] = []
    current_section = ""
    for _, kind, value in events:
        if kind == "section":
            current_section = value
            continue
        cleaned = clean(value)
        if not cleaned:
            continue
        m = ENTRY_RE.match(cleaned)
        if not m:
            continue
        rows.append(
            {
                "lemma": m["lemma"].strip(),
                "kana": (m["kana"] or "").strip(),
                "definition_en": m["def"].strip(),
                "section": current_section,
            }
        )

    out = FOLDER / "original.tsv"
    with out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["section", "lemma", "kana", "definition_en"],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    (FOLDER / "metadata.yaml").write_text(
        """type: wordlist
title: Ainu-English Dictionary (Wikipedia-derived, TranslationDirectory mirror)
title_en: Ainu-English Dictionary (TranslationDirectory mirror of Wikipedia List of Ainu Terms)
author:
  en: Wikipedia contributors
date: 2009
url: https://www.translationdirectory.com/dictionaries/dictionary036.php
license: GFDL (Wikipedia legacy)
source: |
  Static HTML page hosted by TranslationDirectory.com mirroring an old
  Wikipedia "List of Ainu terms" article (accessed 2006-03-27, page-text
  date 2009-02). Single-column bullet list grouped by alphabet header.
  Approximately 200 entries plus indented sub-entries; nested sub-entries
  inherit the section letter of their parent header.
columns:
  section: alphabet letter the entry appears under
  lemma: Ainu form in romanization
  kana: katakana form when given in parentheses
  definition_en: English gloss / explanation as printed
""",
        encoding="utf-8",
    )
    print(f"wrote {len(rows)} TranslationDirectory Ainu-English entries to {out}")


if __name__ == "__main__":
    main()
