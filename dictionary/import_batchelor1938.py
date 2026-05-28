"""Import Batchelor 1938 (4th edition) Ainu-English-Japanese Dictionary.

Source: 『アイヌ・英・和辭典 第四版』(John Batchelor), 1938 reprint,
        re-OCR'd via Chrome and supplied by the user.

The PDF has a clean text layer in 2-column layout. We use pdftotext
-bbox-layout to recover word coordinates, split each page on the
column midline, sort by Y per column, and reconstruct readable lines.
Entries begin with `Headword, カナ, ...` (Latin lemma, comma, katakana,
comma, POS, body). Multi-line entries are joined until the next
headword starts.

The 4th edition (Tokyo: Iwanami shoten, 1938; reprinted by Hokkaido
Publishing Co. / 國書刊行會) is the most comprehensive Batchelor
dictionary, ~14,000 headwords.
"""

from __future__ import annotations

import csv
import html
import re
import subprocess
from pathlib import Path


DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
FOLDER = DICT_ROOT / "1938_Batchelor_Ainu-English-Japanese-Dictionary-4ed"
PDF_PATH = FOLDER / "source.pdf"
RAW_TEXT_PATH = FOLDER / "raw.txt"
BBOX_PATH = FOLDER / "bbox.xml"

WORD_RE = re.compile(
    r'<word\s+xMin="(?P<xmin>[\d.]+)"\s+yMin="(?P<ymin>[\d.]+)"'
    r'\s+xMax="(?P<xmax>[\d.]+)"\s+yMax="(?P<ymax>[\d.]+)">(?P<text>[^<]+)</word>'
)
PAGE_RE = re.compile(r'<page\b[^>]*width="(?P<w>[\d.]+)"[^>]*height="(?P<h>[\d.]+)"[^>]*>')

# Empirical from page sampling: column gap around x=950 (in PDF pts on
# 1748-wide page). Header content above y=380, footer/page-number below
# y=2400.
COLUMN_SPLIT_X = 905.0  # column gap is around 900-925 on most pages
HEADER_Y_MAX = 380.0
FOOTER_Y_MIN = 2400.0
Y_TOLERANCE = 14.0  # vertical line clustering

# Headword pattern: leading-of-line Latin token starting with capital
# (single-letter "A," entries are valid), allowing internal lowercase /
# hyphen / apostrophe, followed by comma + katakana. The katakana
# follow-on is the discriminator that prevents body lines like "Thus,
# for..." from being mis-detected as new entries.
HEADWORD_RE = re.compile(
    r"^(?P<lemma>[A-Z][A-Za-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ'\-]*"
    r"(?:\s+[a-zà-ÿ'\-]+)?)\s*,\s*"
    r"(?P<rest>[ァ-ヴーㇰ-ㇿ・　].+)$"
)


def bbox_xml_path() -> Path:
    if not BBOX_PATH.exists() or BBOX_PATH.stat().st_size < 1_000_000:
        subprocess.run(
            ["pdftotext", "-bbox-layout", str(PDF_PATH), str(BBOX_PATH)],
            check=True,
        )
    return BBOX_PATH


def assemble_column(words: list[tuple[float, float, str]]) -> list[str]:
    """Cluster `(ymin, xmin, text)` tuples into reading-order lines."""
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


def render_text_per_page(xml: str) -> list[list[str]]:
    """Return list[page_idx -> list[line]]. Page 0 = first page in PDF."""
    page_chunks = re.split(r"(<page\b[^>]*>)", xml)
    pages: list[list[str]] = []
    for idx in range(1, len(page_chunks), 2):
        header = page_chunks[idx]
        body = page_chunks[idx + 1] if idx + 1 < len(page_chunks) else ""
        # Find next </page> close
        body = body.split("</page>", 1)[0]
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


def is_likely_headword_line(line: str) -> bool:
    return bool(HEADWORD_RE.match(line.strip()))


# Split a line on every embedded `Capital, カナ` headword. Useful when the
# bbox-layout extractor joins two adjacent column-end / column-start entries
# into a single line.
INLINE_HEADWORD_RE = re.compile(
    r"(?<=\s)(?=[A-Z][A-Za-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ'\-]*"
    r"(?:\s+[a-zà-ÿ'\-]+)?\s*,\s*[ァ-ヴーㇰ-ㇿ・　])"
)


def merge_lines_into_entries(all_lines: list[str]) -> list[str]:
    """Concatenate lines into entry blocks. A new entry begins at any line
    matching the HEADWORD_RE pattern (capitalized lemma + comma + katakana).
    Lines that don't look like headwords are appended to the current entry.
    Each line is also pre-split on inline `Capital, カナ` boundaries to
    catch cases where two entries got fused on the same OCR line."""
    entries: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            entries.append(" ".join(current).strip())
            current.clear()

    for line in all_lines:
        if not line.strip():
            continue
        # Pre-split inline headword boundaries.
        chunks = INLINE_HEADWORD_RE.split(line)
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            if is_likely_headword_line(chunk):
                flush()
                current.append(chunk)
            else:
                if current:
                    current.append(chunk)
    flush()
    return entries


# Parse fields from a joined entry string.
KATAKANA_RANGE = "　-ヿㇰ-ㇿ｡-ﾟ"  # CJK punct + katakana
ENTRY_FIELD_RE = re.compile(
    rf"^(?P<lemma>[A-Z][A-Za-z'\-]+(?:\s+[a-z'\-]+)?),\s*"
    rf"(?P<kana>[{KATAKANA_RANGE}][{KATAKANA_RANGE}、・…\.\s]*?)?\s*"
    rf"(?:,\s*(?P<rest>.+))?$",
    re.DOTALL,
)


def parse_entry(text: str) -> dict[str, str]:
    """Best-effort split into lemma / kana / body."""
    text = re.sub(r"\s+", " ", text).strip()
    m = HEADWORD_RE.match(text)
    if not m:
        return {"lemma": "", "kana": "", "body": text}
    lemma = m["lemma"].strip()
    rest = m["rest"]
    # Find leading katakana run as the kana field.
    kana_m = re.match(r"^\s*([{}][{}、・…\.\s]+)".format(KATAKANA_RANGE, KATAKANA_RANGE), rest)
    if kana_m:
        kana = kana_m.group(1).strip().rstrip(",;.")
        body = rest[kana_m.end():].lstrip(", ;:").strip()
    else:
        kana = ""
        body = rest.strip()
    return {"lemma": lemma, "kana": kana, "body": body}


def main() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    xml_path = bbox_xml_path()
    xml = xml_path.read_text(encoding="utf-8", errors="replace")
    pages = render_text_per_page(xml)

    # Save the linearised raw text for traceability.
    raw_chunks: list[str] = []
    all_lines: list[str] = []
    for idx, lines in enumerate(pages, start=1):
        raw_chunks.append(f"<!-- page {idx} -->\n" + "\n".join(lines))
        all_lines.extend(lines)
    RAW_TEXT_PATH.write_text("\n\n".join(raw_chunks) + "\n", encoding="utf-8")

    entries_blocks = merge_lines_into_entries(all_lines)
    rows = [parse_entry(block) for block in entries_blocks if block]
    rows = [r for r in rows if r["lemma"]]

    # Ainu has no /l/; replace `l → i` in lemmas as a best-effort OCR fix
    # (e.g. Kamul → Kamui). Original lemma stays for traceability.
    for row in rows:
        lemma = row["lemma"]
        row["lemma_normalized"] = lemma.replace("l", "i").replace("L", "I")

    out_path = FOLDER / "original.tsv"
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["lemma", "lemma_normalized", "kana", "body"],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    (FOLDER / "metadata.yaml").write_text(
        """type: dictionary
title: アイヌ・英・和辭典 第四版
title_en: An Ainu-English-Japanese Dictionary, 4th edition (Batchelor 1938)
author:
  en: Batchelor, John
  ja: バチェラー, ジョン
year: 1938
source: |
  User-supplied scan / Chrome-OCR PDF of the 4th edition of John Batchelor's
  Ainu-English-Japanese Dictionary (1938). 681 PDF pages with a two-column
  layout. The text layer is good enough that we can recover entry boundaries
  by clustering pdftotext -bbox-layout word coordinates per column (split at
  xMin = 905 pt on a 1748-pt page width), then joining Y-adjacent words into
  lines and splitting each line on inline `Capital, カナ` headword starts.
  Public domain (author died 1944; first edition 1889).
  source.pdf and bbox.xml are .gitignored due to size (100 MB and 50 MB); the
  importer regenerates bbox.xml from source.pdf and re-derives raw.txt /
  original.tsv on demand.
complements: |
  This 4th edition (Yokohama 1938) is the most complete Batchelor.
  Use 1905_Batchelor_Ainu-English-Japanese-Dictionary in parallel for the
  English→Ainu reverse vocabulary that the 1938 parse omits (an extraction
  of the 1938 back-matter lives in 1938_Batchelor_English-Ainu-Vocabulary-4ed).
caveats: |
  Roughly 14.5k entries parsed; Batchelor 1938 has ~14k headwords. The body
  text occasionally contains the trailing words of an adjacent entry where
  the OCR fused two visual lines together, and the running page header
  ("DICTIONARY") on each PDF page is filtered out by a y > 380 pt cutoff
  but the first few intro pages may still contain title-page artifacts.
  Ainu has no /l/ phoneme, so any lemma containing `l` is an upstream OCR
  error. `lemma_normalized` carries `l → i` substitution; the original
  `lemma` is preserved for traceability (e.g. `Kamul` → `Kamui`).
columns:
  lemma: head Ainu word as printed (may contain OCR-derived `l` typos)
  lemma_normalized: lemma with `l → i` substitution applied (Ainu has no /l/)
  kana: katakana transcription as printed
  body: remainder of the entry — Japanese gloss, part-of-speech tag, English
        definition, cross-references (Syn:, Same as ...), and example phrases.
        Joined onto a single line with whitespace collapsed.
""",
        encoding="utf-8",
    )
    print(
        f"wrote {len(rows)} Batchelor 1938 entries to {out_path} "
        f"(from {sum(len(p) for p in pages)} lines on {len(pages)} pages)"
    )


if __name__ == "__main__":
    main()
