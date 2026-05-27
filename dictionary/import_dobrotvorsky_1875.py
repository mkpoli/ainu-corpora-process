"""Import Dobrotvorsky 1875 Аинско-русскій словарь from RSL scan.

Source: https://rusneb.ru/catalog/000199_000009_003604991/
Author: М. М. Добротворскій (M. M. Dobrotvorsky)
Year: 1875

The PDF carries an OCR text layer in pre-1918 Russian orthography (ѣ, ъ, і).
The dictionary body uses numbered entries (1..~10930) interleaved with
sub-entries marked by an em-dash "—". We capture each numbered line as one
row, plus contiguous sub-entry lines until the next numbered line. Headword
parsing is best-effort — many entries have compound headwords and follow-on
sub-entries that share the previous lemma, so downstream consumers should
treat the raw body as authoritative.
"""

from __future__ import annotations

import csv
import re
import subprocess
import urllib.request
from pathlib import Path


DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
FOLDER = DICT_ROOT / "1875_Dobrotvorsky_Ainu-Russian-Dictionary"
PDF_PATH = FOLDER / "source.pdf"
RAW_TXT = FOLDER / "raw.txt"

PDF_URL = (
    "https://rusneb.ru/local/tools/exalead/getFiles.php"
    "?book_id=000199_000009_003604991&doc_type=pdf"
)

# Lines that look like "  10. headword. body" with a small or large id.
NUMBERED_RE = re.compile(r"^\s*(?P<id>\d{1,5})\.\s+(?P<rest>.+?)\s*$")
# Sub-entry continuation: an em-dash (or hyphen) at the start of the body,
# indicating the previous headword applies.
SUBENTRY_RE = re.compile(r"^\s*[—\-]+\s")


def fetch_pdf() -> None:
    if PDF_PATH.exists() and PDF_PATH.stat().st_size > 1_000_000:
        return
    PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(PDF_URL, timeout=300) as response, PDF_PATH.open("wb") as out:
        while True:
            chunk = response.read(1024 * 64)
            if not chunk:
                break
            out.write(chunk)


def pdf_to_text() -> None:
    if RAW_TXT.exists() and RAW_TXT.stat().st_size > 100_000:
        return
    subprocess.run(
        ["pdftotext", "-layout", str(PDF_PATH), str(RAW_TXT)],
        check=True,
    )


def extract_entries() -> list[dict[str, str]]:
    lines = RAW_TXT.read_text(encoding="utf-8", errors="replace").splitlines()
    # Determine dictionary body window. Entries start around the first
    # "А. ПЕРВАЯ БУКВА АЙНСКОЙ АЗБУКИ" header; the body proper ends before the
    # large appendices ("ПРИЛОЖЕНІЕ"). Use a generous window so we don't lose
    # entries to boundary noise.
    start = end = None
    for idx, line in enumerate(lines):
        if start is None and "АЗБУКИ" in line and "ПЕРВАЯ" in line:
            start = idx + 1
        if start is not None and "ПРИЛОЖЕНІЕ" in line and idx > start + 1000:
            end = idx
            break
    if start is None:
        start = 0
    if end is None:
        end = len(lines)

    entries: list[dict[str, str]] = []
    current_id: str | None = None
    current_lemma: str | None = None
    current_body: list[str] = []
    sub_index = 0

    def flush() -> None:
        nonlocal current_body, sub_index
        if current_id is not None and current_lemma is not None:
            entries.append(
                {
                    "id": current_id,
                    "lemma": current_lemma,
                    "body": re.sub(r"\s+", " ", " ".join(current_body)).strip(),
                    "sub_index": str(sub_index),
                }
            )
        current_body = []

    last_lemma_for_subs: str | None = None

    for raw_line in lines[start:end]:
        line = raw_line.rstrip()
        if not line.strip():
            continue
        m = NUMBERED_RE.match(line)
        if m:
            rest = m["rest"]
            # New numbered entry. May be sub-entry of the previous one if
            # rest starts with "—".
            flush()
            current_id = m["id"]
            sub_index = 0
            if rest.startswith("—") or rest.startswith("-"):
                # Numbered sub-entry that inherits the parent lemma.
                if last_lemma_for_subs:
                    current_lemma = last_lemma_for_subs
                    body_part = rest.lstrip("—- ").strip()
                else:
                    current_lemma = rest.strip()
                    body_part = ""
                sub_index += 1
            else:
                head_match = re.match(r"^(?P<lemma>[^\.]+?)\.\s*(?P<body>.*)$", rest)
                if head_match:
                    current_lemma = head_match["lemma"].strip()
                    last_lemma_for_subs = current_lemma
                    body_part = head_match["body"]
                else:
                    current_lemma = rest.strip()
                    last_lemma_for_subs = current_lemma
                    body_part = ""
            if body_part:
                current_body.append(body_part)
            continue
        if SUBENTRY_RE.match(line) and last_lemma_for_subs:
            # Unnumbered sub-entry under last lemma.
            flush()
            current_id = ""
            sub_index += 1
            current_lemma = last_lemma_for_subs
            current_body.append(line.strip())
            continue
        # Continuation of the running entry.
        current_body.append(line.strip())
    flush()
    return entries


def main() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    fetch_pdf()
    pdf_to_text()
    entries = extract_entries()

    out = FOLDER / "original.tsv"
    with out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(["id", "sub_index", "lemma", "body"])
        for row in entries:
            writer.writerow([row["id"], row["sub_index"], row["lemma"], row["body"]])

    (FOLDER / "metadata.yaml").write_text(
        """type: dictionary
title: Аинско-русскій словарь
title_en: Ainu-Russian Dictionary (Dobrotvorsky 1875)
author:
  en: Dobrotvorsky, Mikhail Mikhailovich
  ru: Добротворскій, М. М.
year: 1875
parent:
  type: book
  publisher: Казань, въ Университетской типографіи
url: https://rusneb.ru/catalog/000199_000009_003604991/
source: |
  PDF (661 pages, 38 MB) downloaded from the Russian National Electronic
  Library (NEB). pdftotext extracts a usable text layer in pre-1918 Russian
  orthography (ѣ, ъ, і, etc.). The original work is М. М. Добротворскій,
  Аинско-русскій словарь, Казань, въ Университетской типографіи, 1875.
  This importer captures numbered headword entries (~10,000+) plus their
  body text. Sub-entries marked by `—` inherit the previous lemma. OCR is
  imperfect for some letters; downstream consumers may want to clean the
  text further. The raw OCR text is preserved in raw.txt and the source
  PDF in source.pdf.
columns:
  id: numeric entry id as printed (may be empty for unnumbered sub-entries)
  sub_index: ordinal among sub-entries sharing the same parent lemma (0 = head)
  lemma: Ainu headword (best-effort extraction from the line)
  body: remainder of the entry text, lines joined and whitespace collapsed
""",
        encoding="utf-8",
    )
    print(f"wrote {len(entries)} Dobrotvorsky entries to {out}")


if __name__ == "__main__":
    main()
