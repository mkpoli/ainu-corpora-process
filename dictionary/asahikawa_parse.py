"""Convert OCR output for the Asahikawa Ainu articles into TSV per article.

Reads:
  dictionary/output/asahikawa-ocr/vol{01,02,12,13}/page-*/ocr/openrouter_google_gemini-3-flash-preview.txt

Writes:
  ainu-dictionaries/1995_Uoi_Asahikawa-Ainu-Verbs-I/original.tsv (+ metadata.yaml + raw.txt)
  ainu-dictionaries/1996_Uoi_Asahikawa-Ainu-Verbs-II/...
  ainu-dictionaries/2006_Uoi_Asahikawa-Ainu-Nouns-I/...
  ainu-dictionaries/2007_Uoi_Asahikawa-Ainu-Nouns-II/...

Entry detection is simple: split on blank lines, treat the first whitespace-
delimited Latin token as the lemma. Heading-only paragraphs ("A", "B", "I", etc.)
and prose front-matter (Japanese-only) are filtered out. Everything else is
preserved as the entry body so downstream cleanup can refine the structure
without losing context.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from dictionary.asahikawa_normalize import normalize as normalize_lemma

ROOT = Path(__file__).resolve().parents[1]
OCR_ROOT = ROOT / "dictionary" / "output" / "asahikawa-ocr"
DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
OCR_MODEL_FILE = "openrouter_google_gemini-3-flash-preview.txt"

ARTICLES = [
    {
        "key": "vol01",
        "folder": "1995_Uoi_Asahikawa-Ainu-Verbs-I",
        "title": "旭川採集アイヌ語動詞語彙集Ⅰ",
        "title_en": "Asahikawa-collected Ainu verbs (part 1)",
        "year": 1995,
        "volume": 1,
        "pdf_pages": "17-31",
        "pdf_url": "https://www.city.asahikawa.hokkaido.jp/hakubutukan/kenkyuu/d056153_d/fil/kenkyu01.pdf",
        "kind": "verbs",
        # First half opens with a long grammatical preamble that contains lemma-
        # like examples (at, ot, sanke, ...). Skip until the first "A" header.
        "has_front_matter": True,
        "initial_section": None,
    },
    {
        "key": "vol02",
        "folder": "1996_Uoi_Asahikawa-Ainu-Verbs-II",
        "title": "旭川採集アイヌ語動詞語彙集Ⅱ",
        "title_en": "Asahikawa-collected Ainu verbs (part 2)",
        "year": 1996,
        "volume": 2,
        "pdf_pages": "2-19",
        "pdf_url": "https://www.city.asahikawa.hokkaido.jp/hakubutukan/kenkyuu/d056153_d/fil/kenkyu02.pdf",
        "kind": "verbs",
        # Continuation; opens mid-I section without a header.
        "has_front_matter": False,
        "initial_section": "I",
    },
    {
        "key": "vol12",
        "folder": "2006_Uoi_Asahikawa-Ainu-Nouns-I",
        "title": "旭川採集アイヌ語名詞集 (part 1)",
        "title_en": "Asahikawa-collected Ainu nouns (part 1)",
        "year": 2006,
        "volume": 12,
        "pdf_pages": "2-13",
        "pdf_url": "https://www.city.asahikawa.hokkaido.jp/hakubutukan/kenkyuu/d056153_d/fil/kenkyu12.pdf",
        "kind": "nouns",
        # Opens with a Japanese intro, then concept/possessive comparison list
        # that mimics entry shape. Skip until first "A" header. The Ainu noun
        # article ends on page 13 with the 凡例/references section; pages 14-21
        # belong to the next article (ニホンザリガニ ecology) and are excluded.
        "has_front_matter": True,
        "initial_section": None,
    },
    {
        "key": "vol13",
        "folder": "2007_Uoi_Asahikawa-Ainu-Nouns-II",
        "title": "旭川採集アイヌ語名詞集 (part 2)",
        "title_en": "Asahikawa-collected Ainu nouns (part 2)",
        "year": 2007,
        "volume": 13,
        "pdf_pages": "2-11",
        "pdf_url": "https://www.city.asahikawa.hokkaido.jp/hakubutukan/kenkyuu/d056153_d/fil/kenkyu13.pdf",
        "kind": "nouns",
        # Continuation; opens mid-C section without a header.
        "has_front_matter": False,
        "initial_section": "C",
    },
]

# A lemma is one or more lowercase Latin tokens (allowing internal apostrophe,
# hyphen, dot) at the start of a paragraph. The first non-Latin character marks
# the end of the headword.
LEMMA_RE = re.compile(
    r"^([A-Za-z][A-Za-z0-9À-ſ'’‘\.\-]*"
    r"(?:\s+[A-Za-z][A-Za-z0-9'’‘\-]+){0,3})"
    r"(?=[\s\.\,　《「〈【<\(]|$)"
)
# Section-letter heads like "A", "B", "i", "K" alone on a line.
SECTION_HEAD_RE = re.compile(r"^[A-Za-z]{1,2}$")
# Heuristic: a line starts a new entry if it begins with a lowercase-Latin
# headword (1-3 tokens) followed immediately by one of `.`, `<`, `〈`, `(`, `[`,
# or whitespace + a non-ASCII (Japanese) character. Sentence continuations in
# example glosses start uppercase or with Japanese, so this avoids false
# matches inside bodies.
ENTRY_START_RE = re.compile(
    r"^([a-z][a-z0-9'’‘\-]*(?:\s+[a-z][a-z0-9'’‘\-]+){0,3})\s*"
    r"(?:\.|<|〈|\[|\(|[ \t]+(?=[^\x00-\x7f]))"
)


def read_page_text(article_key: str, page: int) -> str:
    path = OCR_ROOT / article_key / f"page-{page:03d}" / "ocr" / OCR_MODEL_FILE
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def concat_pages(article_key: str, page_start: int, page_end: int) -> str:
    chunks = []
    for page in range(page_start, page_end + 1):
        text = read_page_text(article_key, page)
        if text:
            chunks.append(f"<!-- page {page} -->\n{text}")
    return "\n\n".join(chunks)


def split_entries(raw_text: str) -> list[str]:
    """Split OCR text into per-entry blocks.

    Many pages have blank lines between entries; some don't. So instead of
    splitting solely on blank lines, we also start a new block whenever a line
    looks like the start of an entry (lowercase Latin lemma followed by
    `.`/`<`/`〈`/`(`/Japanese). Section-letter heads ("A", "K") also force a
    block boundary so the section label propagates correctly.
    """
    paragraphs: list[str] = []
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            paragraphs.append("\n".join(buffer).strip())
            buffer.clear()

    for line in raw_text.splitlines():
        if line.startswith("<!-- page"):
            continue
        stripped = line.strip()
        if stripped == "":
            flush()
            continue
        if SECTION_HEAD_RE.fullmatch(stripped):
            flush()
            paragraphs.append(stripped)
            continue
        if ENTRY_START_RE.match(stripped):
            flush()
        buffer.append(line)
    flush()
    return paragraphs


def detect_lemma(paragraph: str) -> tuple[str, str] | None:
    """Return (lemma, body) if this paragraph looks like an entry; else None."""
    first_line = paragraph.splitlines()[0].lstrip()
    if SECTION_HEAD_RE.match(first_line):
        return None
    match = LEMMA_RE.match(first_line)
    if not match:
        return None
    lemma_raw = match.group(1)
    end = match.end()

    # Drop trailing dots that come from "lemma." style headings in nouns; the
    # period belongs to the body separator, not the lemma.
    lemma = lemma_raw.rstrip(".").strip()
    tokens = lemma.split()
    if not tokens or len(tokens) > 4:
        return None

    # Pathological case: the regex greedily glued a body cross-reference onto
    # the lemma, e.g. "ahup ahun(自)の主格複数形" where the real lemma is
    # "ahup" and "ahun(自)..." is the body. We detect this when the regex stops
    # immediately at "(" or "<" with no preceding whitespace AND the lemma has
    # more than one token: trim the last token off and re-anchor end.
    if len(tokens) > 1 and end < len(first_line) and first_line[end] in "(<":
        # The break char is glued onto the last token. Roll back one token.
        head = " ".join(tokens[:-1])
        # The boundary in the original line just after head must be a space.
        # Recompute end position from the start of first_line.
        roll_end = len(head)
        if (
            roll_end < len(first_line)
            and first_line[roll_end : roll_end + 1] == " "
        ):
            lemma = head
            # Move end to *after* the trailing space-then-token-prefix portion
            # so the body keeps the cross-reference intact: include the space.
            end = roll_end

    body_combined = (first_line[end:] + "\n" + "\n".join(paragraph.splitlines()[1:])).lstrip(" 　:.。,、\n")
    return lemma, body_combined.strip()


# Markers that close the dictionary section of an article. Anything after these
# (legend, references, postscript, dialect comparison tables) is not an entry.
END_OF_ENTRIES_MARKERS = (
    "凡例",
    "凡 例",
    "主要参考文献",
    "参考文献",
    "引用文献",
    "【付記】",
    "付記",
)


SOURCE_TAG_RE = re.compile(r"出所【[^】]+】")


def merge_continuations(paragraphs: list[str], kind: str) -> list[str]:
    """Merge wrap-broken paragraphs back into single entries.

    Asahikawa noun entries always end with `出所【NNN】`. If a paragraph that
    starts with a lemma-shaped line is missing that marker, the entry is
    continuing into the next paragraph; merge them. Verbs have no such marker,
    so we leave their paragraphs alone.
    """
    if kind != "nouns":
        return paragraphs
    merged: list[str] = []
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            merged.append("\n".join(buffer).strip())
            buffer.clear()

    for paragraph in paragraphs:
        first_line = paragraph.splitlines()[0].strip()
        if SECTION_HEAD_RE.fullmatch(first_line):
            flush()
            merged.append(paragraph)
            continue
        if not buffer:
            buffer.append(paragraph)
            continue
        # Decide whether this paragraph starts a new entry or continues the
        # previous one. A new entry must (a) start with a lemma-shaped line and
        # (b) come after a paragraph whose final 出所 marker has appeared.
        looks_like_entry = bool(LEMMA_RE.match(first_line)) and not SECTION_HEAD_RE.match(first_line)
        prev_complete = bool(SOURCE_TAG_RE.search("\n".join(buffer)))
        if looks_like_entry and prev_complete:
            flush()
            buffer.append(paragraph)
        else:
            buffer.append(paragraph)
    flush()
    return merged


def parse_article(article: dict) -> list[dict[str, str]]:
    raw = concat_pages(article["key"], *_pdf_pages_tuple(article["pdf_pages"]))
    entries: list[dict[str, str]] = []
    seen_signatures: set[tuple[str, str]] = set()
    in_entries = not bool(article.get("has_front_matter", False))
    current_section: str | None = article.get("initial_section")
    raw_paragraphs = split_entries(raw)
    paragraphs = merge_continuations(raw_paragraphs, article["kind"])
    for paragraph in paragraphs:
        first_line = paragraph.splitlines()[0].strip()
        # Markers like 凡例 / 引用文献 appear both in the intro (before entries)
        # and after entries (end-of-article). Only treat them as "stop" once
        # at least one entry has already been emitted.
        if entries and any(
            first_line.startswith(marker) for marker in END_OF_ENTRIES_MARKERS
        ):
            break
        if SECTION_HEAD_RE.fullmatch(first_line):
            current_section = first_line.upper()
            in_entries = True
            continue
        if not in_entries:
            continue
        detected = detect_lemma(paragraph)
        if detected is None:
            continue
        lemma, body = detected
        signature = (lemma, body)
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        entries.append(
            {
                "lemma": lemma,
                "body": body,
                "section": current_section or "",
            }
        )
    return entries


def _pdf_pages_tuple(spec: str) -> tuple[int, int]:
    start, end = spec.split("-")
    return int(start), int(end)


def write_outputs(article: dict, entries: list[dict[str, str]]) -> None:
    target_dir = DICT_ROOT / article["folder"]
    target_dir.mkdir(parents=True, exist_ok=True)

    raw_text = concat_pages(article["key"], *_pdf_pages_tuple(article["pdf_pages"]))
    (target_dir / "raw.txt").write_text(raw_text + "\n", encoding="utf-8")

    tsv_path = target_dir / "original.tsv"
    with tsv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(["lemma", "lemma_normalized", "section", "body"])
        for entry in entries:
            writer.writerow(
                [
                    entry["lemma"],
                    normalize_lemma(entry["lemma"]),
                    entry.get("section", ""),
                    entry["body"].replace("\n", " "),
                ]
            )

    metadata = f"""type: {article['kind']}
author:
  en: Uoi, Issan
  ja: 魚井, 一山
year: {article['year']}
dialect:
  name: 旭川
  path: 北海道/北東/石狩
title: {article['title']}
title_en: {article['title_en']}
parent:
  type: journal-article
  title: 旭川市博物館研究報告
  volume: {article['volume']}
  pages: {article['pdf_pages']}
  publisher: 旭川市博物館
url: {article['pdf_url']}
source: OCR of scanned PDF via openrouter/google/gemini-3-flash-preview
"""
    (target_dir / "metadata.yaml").write_text(metadata, encoding="utf-8")


def main() -> None:
    for article in ARTICLES:
        entries = parse_article(article)
        write_outputs(article, entries)
        print(f"{article['folder']}: {len(entries)} entries")


if __name__ == "__main__":
    main()
