"""Re-OCR selected pages of Batchelor 1938 with Gemini and show diffs.

For each chosen page:
  1. Render to PNG with pdftoppm.
  2. Send to openrouter/google/gemini-3-flash-preview with an Ainu-aware prompt.
  3. Extract entries from the Gemini output using the same parser.
  4. Compare against the existing rows from the bbox-layout parse (rows that
     came from this page, identified by scanning raw.txt).
  5. Print a unified diff and a side-by-side count summary.

Output goes to dictionary/output/batchelor1938-reocr/page-XXX/.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import os
import re
import subprocess
import sys
from pathlib import Path

from dictionary.nakagawa_ocr_common import (
    ModelSpec,
    image_data_url,
    load_env_files,
    run_llm_ocr,
)

csv.field_size_limit(sys.maxsize)

ROOT = Path(__file__).resolve().parents[1]
DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
SRC_FOLDER = DICT_ROOT / "1938_Batchelor_Ainu-English-Japanese-Dictionary-4ed"
PDF = SRC_FOLDER / "source.pdf"
RAW = SRC_FOLDER / "raw.txt"
OUTPUT_ROOT = ROOT / "dictionary" / "output" / "batchelor1938-reocr"


PROMPT = """You are performing OCR on a scanned page of John Batchelor's
"An Ainu-English-Japanese Dictionary, 4th edition" (1938). The page has
two columns. Each entry has this shape:

    Lemma, カナ, 日本語, pos. English definition. Syn: Other-lemma. ...

The lemma is a romanized Ainu word (Latin letters, may contain hyphens).
The katakana follows in the same line. Japanese gloss is in mixed kanji
+ kana, often short. The POS abbreviations are: n., v.i., v.t., v.,
adj., adv., conj., pron., part., interj., prep. The body is in English
with occasional Japanese phrases and example sentences in Ainu.

Output one entry per line, in this exact format, no extra commentary:

    LEMMA<TAB>カナ<TAB>BODY

Where:
- LEMMA: lemma exactly as printed in Latin, no quotes
- カナ: the katakana transcription (and any inline 日本語 gloss inside ・、 punctuation that the source places immediately after katakana)
- BODY: rest of the entry — POS, English definition, cross-refs, examples — joined with single spaces, kept on one line

Read the LEFT column top-to-bottom first, then the RIGHT column top-to-bottom.
Do NOT interleave the columns. Skip the running page header (the word
"DICTIONARY" and the alphabet-marker like "ABE" at the very top, and the page
number).

If a word appears OCR-corrupted (broken kana, garbled Latin), use your best
guess and continue — do not refuse.
"""


def render_page(page: int, dpi: int = 300) -> Path:
    out_dir = OUTPUT_ROOT / f"page-{page:03d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_png = out_dir / "page.png"
    if out_png.exists() and out_png.stat().st_size > 100_000:
        return out_png
    subprocess.run(
        [
            "pdftoppm",
            "-f",
            str(page),
            "-l",
            str(page),
            "-r",
            str(dpi),
            "-png",
            str(PDF),
            str(out_dir / "page"),
        ],
        check=True,
    )
    # pdftoppm output filename varies by page count digits. Find the produced file.
    candidates = list(out_dir.glob("page-*.png"))
    if not candidates:
        raise FileNotFoundError(f"pdftoppm produced no output for page {page}")
    # Rename to predictable name.
    candidates[0].rename(out_png)
    return out_png


def gemini_ocr(image_path: Path) -> tuple[str, dict]:
    text_dir = image_path.parent
    out_txt = text_dir / "gemini.tsv"
    info_txt = text_dir / "gemini.info"
    if out_txt.exists():
        return out_txt.read_text(encoding="utf-8"), {}
    result = run_llm_ocr(
        image_path,
        ModelSpec(id="openrouter/google/gemini-3-flash-preview"),
        PROMPT,
    )
    out_txt.write_text(result.text, encoding="utf-8")
    info_txt.write_text(
        f"prompt_tokens={result.usage.get('prompt_tokens')}\n"
        f"completion_tokens={result.usage.get('completion_tokens')}\n"
        f"response_cost={result.response_cost}\n",
        encoding="utf-8",
    )
    return result.text, result.usage


def page_text_from_raw(page: int) -> str:
    text = RAW.read_text(encoding="utf-8")
    pattern = re.compile(rf"<!-- page {page} -->(.*?)(?=<!-- page \d+ -->|\Z)", re.DOTALL)
    m = pattern.search(text)
    return m.group(1).strip() if m else ""


def parse_gemini(text: str) -> list[tuple[str, str, str]]:
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        while len(parts) < 3:
            parts.append("")
        rows.append((parts[0].strip(), parts[1].strip(), " ".join(parts[2:]).strip()))
    return rows


def existing_rows_for_page(page: int) -> list[tuple[str, str, str, str]]:
    """Return (lemma, lemma_normalized, kana, body) for entries whose first
    body line appears in this page's raw.txt block. Heuristic: any lemma
    whose first body word appears in the page-window text."""
    page_block = page_text_from_raw(page)
    if not page_block:
        return []
    matches: list[tuple[str, str, str, str]] = []
    tsv_path = SRC_FOLDER / "original.tsv"
    with tsv_path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            lemma = row.get("lemma", "")
            if not lemma:
                continue
            # Match on lemma appearing near a comma at the start of a line in the page
            pattern = re.compile(rf"^\s*{re.escape(lemma)}\s*,", re.MULTILINE)
            if pattern.search(page_block):
                matches.append(
                    (
                        lemma,
                        row.get("lemma_normalized", ""),
                        row.get("kana", ""),
                        row.get("body", ""),
                    )
                )
    return matches


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pages", nargs="*", type=int, default=[100, 244, 514])
    args = parser.parse_args()
    load_env_files()

    for page in args.pages:
        print(f"\n===== page {page} =====")
        png = render_page(page)
        text, usage = gemini_ocr(png)
        gemini_entries = parse_gemini(text)
        existing = existing_rows_for_page(page)
        summary = (
            f"  gemini entries:  {len(gemini_entries)}\n"
            f"  current parse:   {len(existing)}\n"
        )
        if usage:
            cost = usage.get("response_cost")
            summary += f"  cost (Gemini):   ${cost:.4f}\n" if cost else ""
        print(summary)

        # Print first 6 lemmas from each side for eyeballing.
        print("  ~ first 6 lemmas: gemini  vs  current ~")
        for i in range(6):
            g_lem = gemini_entries[i][0] if i < len(gemini_entries) else ""
            e_lem = existing[i][0] if i < len(existing) else ""
            marker = "  " if g_lem == e_lem else " *"
            print(f"   {marker}  {g_lem:<25}  |  {e_lem}")

        # Write a comparison file with full sides.
        cmp_path = OUTPUT_ROOT / f"page-{page:03d}" / "diff.txt"
        with cmp_path.open("w", encoding="utf-8") as fh:
            fh.write("=== Gemini OCR ===\n")
            for lem, kana, body in gemini_entries:
                fh.write(f"{lem}\t{kana}\t{body}\n")
            fh.write("\n=== Current bbox-layout parse ===\n")
            for lem, norm, kana, body in existing:
                fh.write(f"{lem}\t{norm}\t{kana}\t{body}\n")
        print(f"  wrote {cmp_path}")


if __name__ == "__main__":
    main()
