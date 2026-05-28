"""Extract the English-Ainu Vocabulary back-matter from Batchelor 1938.

Pages 582-680 of the PDF contain the reverse English→Ainu index. Each entry
looks like:

    Aback, adv. Mak; makta; oshmake; oshmaketa; oshmake un; mak un; ...
    Abandon, v.t. Oasere; ...

We re-use the column-aware bbox parser from the main importer, then detect
entries by leading-Capital-English-word + comma, with body containing
optional part-of-speech tag and one or more semicolon-separated Ainu
translations.

Writes to a sibling folder so the English-side index is searchable
independently of the main Ainu-headword dictionary.
"""

from __future__ import annotations

import csv
import html
import re
import subprocess
from pathlib import Path


DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
SRC_FOLDER = DICT_ROOT / "1938_Batchelor_Ainu-English-Japanese-Dictionary-4ed"
FOLDER = DICT_ROOT / "1938_Batchelor_English-Ainu-Vocabulary-4ed"
PDF_PATH = SRC_FOLDER / "source.pdf"
BBOX_PATH = SRC_FOLDER / "bbox.xml"

ENG_PAGE_START = 582
ENG_PAGE_END = 680

# English back-matter columns are narrower than the main dictionary's.
# Sample of page 582 shows left-column body extending to xMax≈820 and
# right-column entries starting at xMin≈900, so split at 860.
COLUMN_SPLIT_X = 860.0
HEADER_Y_MAX = 380.0
FOOTER_Y_MIN = 2400.0
Y_TOLERANCE = 14.0

WORD_RE = re.compile(
    r'<word\s+xMin="(?P<xmin>[\d.]+)"\s+yMin="(?P<ymin>[\d.]+)"'
    r'\s+xMax="(?P<xmax>[\d.]+)"\s+yMax="(?P<ymax>[\d.]+)">(?P<text>[^<]+)</word>'
)

# English-side entry: Capital + lowercase letters, optional hyphenation,
# possibly multi-word ("To run", "Up to"), then comma, then English POS
# abbreviation (n., v., v.t., v.i., adj., adv., a., conj., prep., int., pron.,
# part.) and the Ainu body. We don't require POS — many entries omit it.
HEADWORD_RE = re.compile(
    r"^(?P<lemma>[A-Z][A-Za-z'\-]+(?:\s+[a-zA-Z'\-]+){0,3})"
    r"\s*,\s*"
    r"(?:\(?(?P<pos>(?:n|v|vi|vt|v\.t|v\.i|adj|adv|a|conj|prep|int|pron|part|interj)\b\.?)?\)?\s*\.?\s*)?"
    r"(?P<body>.+)$",
    re.IGNORECASE,
)

# Inline-split: an English entry head is `Capital_word(s), pos. ...` where the
# trailing `; ...` Ainu translations rarely begin with a Capital-English-word
# pattern, so this is robust enough.
INLINE_HEADWORD_RE = re.compile(
    r"(?<=\s)(?=[A-Z][a-z][A-Za-z'\-]*(?:\s+[a-z'\-]+){0,3}\s*,\s*)"
)


def ensure_bbox_xml() -> Path:
    if not BBOX_PATH.exists() or BBOX_PATH.stat().st_size < 1_000_000:
        subprocess.run(
            ["pdftotext", "-bbox-layout", str(PDF_PATH), str(BBOX_PATH)],
            check=True,
        )
    return BBOX_PATH


def assemble_column(words: list[tuple[float, float, str]]) -> list[str]:
    if not words:
        return []
    words = sorted(words)
    lines: list[str] = []
    current: list[tuple[float, float, str]] = []
    cluster_y: float | None = None
    for ymin, xmin, txt in words:
        if cluster_y is None or ymin - cluster_y > Y_TOLERANCE:
            if current:
                lines.append(
                    " ".join(t for _, _, t in sorted(current, key=lambda x: x[1]))
                )
            current = [(ymin, xmin, txt)]
            cluster_y = ymin
        else:
            current.append((ymin, xmin, txt))
    if current:
        lines.append(" ".join(t for _, _, t in sorted(current, key=lambda x: x[1])))
    return lines


def render_text_per_page(xml: str, first_page: int, last_page: int) -> list[list[str]]:
    page_chunks = re.split(r"(<page\b[^>]*>)", xml)
    pages: list[list[str]] = []
    page_index = 0
    for idx in range(1, len(page_chunks), 2):
        page_index += 1
        body = page_chunks[idx + 1] if idx + 1 < len(page_chunks) else ""
        body = body.split("</page>", 1)[0]
        if page_index < first_page or page_index > last_page:
            continue
        left: list[tuple[float, float, str]] = []
        right: list[tuple[float, float, str]] = []
        for m in WORD_RE.finditer(body):
            ymin = float(m["ymin"])
            xmin = float(m["xmin"])
            if ymin < HEADER_Y_MAX or ymin > FOOTER_Y_MIN:
                continue
            tup = (ymin, xmin, html.unescape(m["text"]))
            if xmin < COLUMN_SPLIT_X:
                left.append(tup)
            else:
                right.append(tup)
        pages.append(assemble_column(left) + assemble_column(right))
    return pages


def is_headword_line(line: str) -> bool:
    return bool(HEADWORD_RE.match(line.strip()))


def merge_entries(all_lines: list[str]) -> list[str]:
    entries: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            entries.append(" ".join(current).strip())
            current.clear()

    for line in all_lines:
        if not line.strip():
            continue
        chunks = INLINE_HEADWORD_RE.split(line)
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            if is_headword_line(chunk):
                flush()
                current.append(chunk)
            elif current:
                current.append(chunk)
    flush()
    return entries


def parse_entry(text: str) -> dict[str, str] | None:
    text = re.sub(r"\s+", " ", text).strip()
    m = HEADWORD_RE.match(text)
    if not m:
        return None
    lemma = m["lemma"].strip().rstrip(",")
    pos = (m["pos"] or "").strip(". ")
    body = m["body"].strip()
    # Ainu translations are separated by semicolons. The first/leading
    # chunk may still contain a stray POS marker if the regex didn't catch
    # it; leave body as-is for fidelity.
    return {"lemma": lemma, "pos": pos, "ainu_translations": body}


def main() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    xml_path = ensure_bbox_xml()
    xml = xml_path.read_text(encoding="utf-8", errors="replace")
    pages = render_text_per_page(xml, ENG_PAGE_START, ENG_PAGE_END)

    raw_lines: list[str] = []
    all_lines: list[str] = []
    for idx, lines in enumerate(pages, start=ENG_PAGE_START):
        raw_lines.append(f"<!-- page {idx} -->\n" + "\n".join(lines))
        all_lines.extend(lines)
    (FOLDER / "raw.txt").write_text("\n\n".join(raw_lines) + "\n", encoding="utf-8")

    entries_blocks = merge_entries(all_lines)
    rows: list[dict[str, str]] = []
    for block in entries_blocks:
        parsed = parse_entry(block)
        if parsed and parsed["lemma"]:
            rows.append(parsed)

    out_path = FOLDER / "original.tsv"
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["lemma", "pos", "ainu_translations"],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    (FOLDER / "metadata.yaml").write_text(
        """type: dictionary
title: アイヌ・英・和辭典 第四版 — 英アイヌ語彙
title_en: An Ainu-English-Japanese Dictionary, 4th edition — English-Ainu Vocabulary back-matter
author:
  en: Batchelor, John
  ja: バチェラー, ジョン
year: 1938
source: |
  Extracted from the English-Ainu Vocabulary appendix of Batchelor's
  4th edition (pages 582-680 of the Chrome-OCR PDF). Same column-aware
  bbox parser as 1938_Batchelor_Ainu-English-Japanese-Dictionary-4ed but
  with English-side entry detection: `English_lemma, POS. Ainu1; Ainu2; ...`.
  Public domain (Batchelor died 1944).
caveats: |
  Some entries may include stray Japanese particles or fused-line noise
  similar to the main parse. POS detection is best-effort. The English
  lemma is the search key; ainu_translations preserves the original
  semicolon-separated list as printed.
columns:
  lemma: English headword as printed in the vocabulary
  pos: English part-of-speech abbreviation (n, v, v.t, v.i, adj, adv, ...)
  ainu_translations: semicolon-separated list of Ainu equivalents
""",
        encoding="utf-8",
    )
    print(
        f"wrote {len(rows)} English-Ainu entries to {out_path} "
        f"(from {sum(len(p) for p in pages)} lines on {len(pages)} pages)"
    )


if __name__ == "__main__":
    main()
