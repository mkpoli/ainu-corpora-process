"""Ingest Batchelor (1905) Ainu-English-Japanese Dictionary.

Source: archive.org djvu OCR of the 1905 edition, public domain.
URL: https://archive.org/details/anainuenglishja00batcgoog
DjVu text: https://archive.org/download/anainuenglishja00batcgoog/anainuenglishja00batcgoog_djvu.txt

The djvu text is messy turn-of-the-century OCR with broken kana, missing
punctuation, and frequent column-misordering. We do NOT try to produce
clean structured entries here — instead we save the raw djvu text and
extract a best-effort head/body TSV by looking for "^Lemma," or
"^Lemma. " patterns at the start of lines within the dictionary body.
Downstream consumers can re-OCR or hand-clean the rough parses.
"""

from __future__ import annotations

import csv
import re
import urllib.request
from pathlib import Path

DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
FOLDER = DICT_ROOT / "1905_Batchelor_Ainu-English-Japanese-Dictionary"

DJVU_URL = "https://archive.org/download/anainuenglishja00batcgoog/anainuenglishja00batcgoog_djvu.txt"

# The dictionary body proper starts at "AN AINU-ENGLISH-JAPANESE DICTIONARY"
# and ends before the JAPANESE-AINU or grammar sections.
BODY_START_RE = re.compile(r"AN\s+AINU-ENGLISH-JAPANESE", re.IGNORECASE)
BODY_END_RE = re.compile(r"JAPANESE-AINU\s+VOCABULARY|GRAMMAR\s+OF\s+THE\s+AINU", re.IGNORECASE)

# Heuristic: a Batchelor entry begins with an Ainu headword at the left
# margin. The headword is Latin-only (with hyphens / apostrophes), followed
# by a comma or period, then by Japanese katakana and an English gloss.
# Capital first letter; word boundary on the closing comma/period.
ENTRY_HEAD_RE = re.compile(
    r"^(?P<lemma>[A-Z][A-Za-z][A-Za-z'’\-]*)[,\.]\s+(?P<rest>.*)$"
)


def fetch_djvu() -> str:
    with urllib.request.urlopen(DJVU_URL, timeout=120) as response:
        return response.read().decode("utf-8", errors="replace")


def extract_body(text: str) -> str:
    m_start = BODY_START_RE.search(text)
    if not m_start:
        return text
    body = text[m_start.end():]
    m_end = BODY_END_RE.search(body)
    if m_end:
        body = body[: m_end.start()]
    return body


def parse(body: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    buffer: list[str] = []
    cur_lemma: str | None = None
    cur_rest: str | None = None

    def flush() -> None:
        nonlocal cur_lemma, cur_rest
        if cur_lemma is not None:
            body_text = (cur_rest or "") + " " + " ".join(buffer)
            rows.append({"lemma": cur_lemma, "body": re.sub(r"\s+", " ", body_text).strip()})
        buffer.clear()
        cur_lemma = None
        cur_rest = None

    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        # Skip page-break OCR junk like "AOQ -" or short headers.
        if re.fullmatch(r"[A-Z]{1,3}\s+[\-\=ーー]+\s*[A-Z]*\s*", line.strip()):
            continue
        m = ENTRY_HEAD_RE.match(line)
        if m:
            flush()
            cur_lemma = m["lemma"]
            cur_rest = m["rest"]
        else:
            if cur_lemma is not None:
                buffer.append(line.strip())
    flush()
    return rows


def main() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    raw = fetch_djvu()
    (FOLDER / "source.txt").write_text(raw, encoding="utf-8")
    body = extract_body(raw)
    (FOLDER / "body.txt").write_text(body, encoding="utf-8")
    rows = parse(body)

    tsv_path = FOLDER / "original.tsv"
    with tsv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(["lemma", "body"])
        for r in rows:
            writer.writerow([r["lemma"], r["body"]])

    metadata = """type: dictionary
title: An Ainu-English-Japanese Dictionary (including A Grammar of the Ainu Language)
title_en: An Ainu-English-Japanese Dictionary (Batchelor 1905)
author:
  en: Batchelor, John
  ja: バチェラー, ジョン
year: 1905
dialect:
  name: 北海道（沙流・幌別を中心）
  path: 北海道
parent:
  type: book
  title: An Ainu-English-Japanese Dictionary (including A Grammar of the Ainu Language)
  publisher: Methodist Publishing House, Tokyo
url: https://archive.org/details/anainuenglishja00batcgoog
license: public domain
source: |
  Plain-text djvu OCR from archive.org of the 1905 edition (the second of
  three editions Batchelor produced; 1889 and 1926 are the others). The OCR
  is turn-of-the-century quality and has substantial errors in both Latin
  and katakana columns; this importer extracts a best-effort lemma+body TSV
  but downstream consumers should re-OCR or hand-clean specific entries.
  source.txt holds the unmodified djvu dump; body.txt holds the body
  between the dictionary-start and JAPANESE-AINU/grammar sentinels.
columns:
  lemma:  head Ainu word (Latin) as detected at column-0 in djvu
  body:   the remainder of the entry concatenated (Japanese + English mixed)
"""
    (FOLDER / "metadata.yaml").write_text(metadata, encoding="utf-8")
    print(f"wrote {len(rows)} Batchelor 1905 entries (rough OCR) to {tsv_path}")


if __name__ == "__main__":
    main()
