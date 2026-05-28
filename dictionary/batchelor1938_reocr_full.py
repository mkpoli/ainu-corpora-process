"""Full Gemini re-OCR of Batchelor 1938 (681 pages).

Renders each page to PNG at 300 dpi, sends to openrouter/google/
gemini-3-flash-preview with an Ainu-aware TSV-output prompt, caches the
result per page, then merges into a single TSV. Idempotent — already
done pages are skipped.

Output paths:
  dictionary/output/batchelor1938-reocr/page-XXX/page.png
  dictionary/output/batchelor1938-reocr/page-XXX/gemini.tsv
  dictionary/output/batchelor1938-reocr/page-XXX/gemini.info
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dictionary.nakagawa_ocr_common import (
    ModelSpec,
    load_env_files,
    run_llm_ocr,
)

ROOT = Path(__file__).resolve().parents[1]
DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
SRC_FOLDER = DICT_ROOT / "1938_Batchelor_Ainu-English-Japanese-Dictionary-4ed"
PDF = SRC_FOLDER / "source.pdf"
OUTPUT_ROOT = ROOT / "dictionary" / "output" / "batchelor1938-reocr"
MODEL = "openrouter/google/gemini-3-flash-preview"

TOTAL_PAGES = 681

PROMPT = """You are performing OCR on a scanned page of John Batchelor's "An Ainu-English-Japanese Dictionary, 4th edition" (1938). The page has two columns. Each entry has this shape:

    Lemma, カナ, 日本語, pos. English definition. Syn: Other-lemma. ...

The lemma is a romanized Ainu word (Latin letters, may contain hyphens). The katakana follows in the same line. Japanese gloss is in mixed kanji + kana, often short. The POS abbreviations are: n., v.i., v.t., v., adj., adv., conj., pron., part., interj., prep. The body is in English with occasional Japanese phrases and example sentences in Ainu.

Output one entry per line, in this exact format, no extra commentary:

    LEMMA<TAB>カナ<TAB>BODY

Where:
- LEMMA: lemma exactly as printed in Latin, no quotes
- カナ: the katakana transcription (and any inline 日本語 gloss inside ・、 punctuation that the source places immediately after katakana)
- BODY: rest of the entry — POS, English definition, cross-refs, examples — joined with single spaces, kept on one line

Read the LEFT column top-to-bottom first, then the RIGHT column top-to-bottom. Do NOT interleave the columns. Skip the running page header ("DICTIONARY", "AINU-ENGLISH-JAPANESE", the alphabet-marker like "ABE" at the very top, and the page number).

Ainu has no /l/ phoneme. If a lemma appears to contain Latin `l`, it is almost certainly an `i` (e.g. "Kamul" → output "Kamui"). Correct such errors silently.

If a word appears OCR-corrupted (broken kana, garbled Latin), use your best guess and continue — do not refuse.

If this page contains only intro / preface / colophon text and no dictionary entries, output exactly the single token NO_ENTRIES on one line.
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
    candidates = list(out_dir.glob("page-*.png"))
    if not candidates:
        raise FileNotFoundError(f"pdftoppm produced no output for page {page}")
    if candidates[0] != out_png:
        candidates[0].rename(out_png)
    return out_png


def ocr_page(page: int) -> tuple[int, float | None, str]:
    """Return (page, cost, status). Skip if already cached."""
    out_dir = OUTPUT_ROOT / f"page-{page:03d}"
    tsv_path = out_dir / "gemini.tsv"
    info_path = out_dir / "gemini.info"
    if tsv_path.exists() and tsv_path.stat().st_size > 0:
        # Re-load cost from info if available.
        cost = None
        if info_path.exists():
            for line in info_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("response_cost="):
                    try:
                        cost = float(line.split("=", 1)[1])
                    except ValueError:
                        pass
        return page, cost, "cached"
    png = render_page(page)
    for attempt in range(3):
        try:
            result = run_llm_ocr(png, ModelSpec(id=MODEL), PROMPT)
            tsv_path.write_text(result.text, encoding="utf-8")
            info_path.write_text(
                f"prompt_tokens={result.usage.get('prompt_tokens')}\n"
                f"completion_tokens={result.usage.get('completion_tokens')}\n"
                f"response_cost={result.response_cost}\n",
                encoding="utf-8",
            )
            return page, result.response_cost, "ok"
        except Exception as exc:  # noqa: BLE001
            if attempt == 2:
                err_path = out_dir / "gemini.error"
                err_path.write_text(str(exc), encoding="utf-8")
                return page, None, f"failed: {exc.__class__.__name__}"
            time.sleep(2 ** attempt)
    return page, None, "failed"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=TOTAL_PAGES)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    load_env_files()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    pages = list(range(args.start, args.end + 1))
    done = 0
    failed: list[int] = []
    total_cost = 0.0
    new_calls = 0
    cached = 0
    start_t = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(ocr_page, p): p for p in pages}
        for fut in as_completed(futures):
            page, cost, status = fut.result()
            done += 1
            if status == "cached":
                cached += 1
            elif status == "ok":
                new_calls += 1
                if cost:
                    total_cost += cost
            else:
                failed.append(page)
            if done % 20 == 0 or done == len(pages):
                elapsed = time.time() - start_t
                rate = done / elapsed if elapsed > 0 else 0
                eta = (len(pages) - done) / rate if rate > 0 else 0
                print(
                    f"[{done}/{len(pages)}] cached={cached} new={new_calls} "
                    f"failed={len(failed)} cost=${total_cost:.3f} "
                    f"rate={rate:.1f}/s eta={int(eta)}s",
                    flush=True,
                )

    summary = {
        "total_pages": len(pages),
        "new_calls": new_calls,
        "cached": cached,
        "failed_pages": failed,
        "total_new_cost": total_cost,
    }
    (OUTPUT_ROOT / "run_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print("done:", json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
