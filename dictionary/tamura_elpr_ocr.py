"""OCR pipeline for the Tamura Suzuko ELPR A2 Ainu materials volume.

Source: 文部科学省特定領域研究「環太平洋の『消滅に瀕した言語』にかんする緊急調査研究」
        北原次郎太・田村雅史・田村将人・丹菊逸治・田村すず子 編
        『アイヌ語 樺太・名寄・釧路方言の資料 — 田村すず子採録 藤山ハルさん・
         山田ハヨさん・北風磯吉さん・徹辺重次郎さんの口頭文芸・語彙・民族誌』
        (ELPR publication A2, 環北太平洋班)

The PDF is one 340-page volume mixing several content types:
  - interlinear glossed oral literature (numbered lines: katakana Ainu over Latin
    Ainu, paired with a Japanese translation column, plus footnotes) -> corpus
  - numbered Japanese->Ainu vocabulary lists (with acute pitch accents and
    apostrophes) -> dictionary
  - Ainu word indices (アイヌ語索引): 2-column concordance, lemma + line refs

A single faithful-transcription prompt covers all of these; the section-specific
structuring happens downstream at parse time. SECTIONS below records the routing
target and page ranges (printed page numbers; PDF page = printed + PAGE_OFFSET).

Outputs land under dictionary/output/tamura-elpr-ocr/page-{PPP}/ following the
same status / cost-report layout used by nakagawa_ocr_* and asahikawa_ocr.
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict
from pathlib import Path

from PIL import Image

from dictionary.nakagawa_ocr_common import (
    CropPadding,
    ModelSpec,
    OCRStatusFile,
    crop_image,
    detect_crop_box,
    ensure_dir,
    file_sha256,
    format_crop_box,
    load_env_files,
    log_progress,
    model_statuses,
    read_status_file,
    record_run_status,
    run_command,
    run_key,
    run_llm_ocr,
    sanitize_model_id,
    should_skip_run,
    string_sha256,
    write_cost_report,
    write_status_file,
    write_text,
)

ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "dictionary" / "input" / "tamura_elpr" / "アイヌ語樺太名寄釧路方言の資料.pdf"
OUTPUT_ROOT = ROOT / "dictionary" / "output" / "tamura-elpr-ocr"

TOTAL_PDF_PAGES = 340
# PDF (1-indexed) page = printed page + PAGE_OFFSET. Verified: PDF 10 = printed 3,
# PDF 17 = printed 10 (言い伝え1 title).
PAGE_OFFSET = 7

DEFAULT_DPI = 300
# User-requested model. gemini-3.5-flash on OpenRouter handles katakana + Latin +
# Japanese mixed pages well and is cheap (~$0.01/page).
DEFAULT_MODELS = [
    "openrouter/google/gemini-3.5-flash",
]

# Content begins at printed p2 (PDF 9); summary/back-matter runs to PDF 340.
DEFAULT_PAGE_START = 9
DEFAULT_PAGE_END = TOTAL_PDF_PAGES


def printed_to_pdf(p: int) -> int:
    return p + PAGE_OFFSET


# Section map for downstream routing. Page numbers are PRINTED page numbers.
# route: "corpus" (oral literature / songs), "dictionary" (vocabulary list),
# "index" (Ainu concordance index), "front" (front/section matter).
SECTIONS: list[dict[str, object]] = [
    # 第I編 樺太方言 — 藤山ハルさん の口頭文芸と歌 (Sakhalin / Fujiyama Haru)
    {"part": "I", "dialect": "Sakhalin", "speaker": "藤山ハル", "title": "言い伝え1 (ウチャシクマ1)", "printed": [10, 29], "route": "corpus"},
    {"part": "I", "dialect": "Sakhalin", "speaker": "藤山ハル", "title": "言い伝え2", "printed": [30, 39], "route": "corpus"},
    {"part": "I", "dialect": "Sakhalin", "speaker": "藤山ハル", "title": "言い伝え3", "printed": [40, 54], "route": "corpus"},
    {"part": "I", "dialect": "Sakhalin", "speaker": "藤山ハル", "title": "言い伝え4", "printed": [55, 104], "route": "corpus"},
    {"part": "I", "dialect": "Sakhalin", "speaker": "藤山ハル", "title": "言い伝え5", "printed": [105, 149], "route": "corpus"},
    {"part": "I", "dialect": "Sakhalin", "speaker": "藤山ハル", "title": "子守歌1・子守歌2・酒歌・子守歌3", "printed": [150, 170], "route": "corpus"},
    # 第II編 樺太方言 — 山田ハヨさん の語彙と口頭文芸 (Sakhalin / Yamada Hayo)
    {"part": "II", "dialect": "Sakhalin", "speaker": "山田ハヨ", "title": "山田ハヨさんの語彙と口頭文芸", "printed": [175, 192], "route": "dictionary"},
    {"part": "II", "dialect": "Sakhalin", "speaker": "山田ハヨ", "title": "アイヌ語索引", "printed": [193, 202], "route": "index"},
    # 第III編 名寄方言 — 北風磯吉さん の口頭文芸と語彙 (Nayoro / Kitakaze Isokichi)
    {"part": "III", "dialect": "Nayoro", "speaker": "北風磯吉", "title": "第1部 口頭文芸 (散文説話)", "printed": [208, 210], "route": "corpus"},
    {"part": "III", "dialect": "Nayoro", "speaker": "北風磯吉", "title": "第2部 語彙 002〜145", "printed": [211, 234], "route": "dictionary"},
    {"part": "III", "dialect": "Nayoro", "speaker": "北風磯吉", "title": "アイヌ語索引", "printed": [235, 239], "route": "index"},
    # 第IV編 釧路方言 — 徹辺重次郎さん の語彙と口頭文芸 (Kushiro / Tetsube Jujiro)
    {"part": "IV", "dialect": "Kushiro", "speaker": "徹辺重次郎", "title": "第1部 語彙1・語彙2", "printed": [250, 308], "route": "dictionary"},
    {"part": "IV", "dialect": "Kushiro", "speaker": "徹辺重次郎", "title": "第2部 言い伝え1・言い伝え2", "printed": [309, 314], "route": "corpus"},
    {"part": "IV", "dialect": "Kushiro", "speaker": "徹辺重次郎", "title": "アイヌ語索引", "printed": [315, 329], "route": "index"},
]


# The scans have a faint binding shadow on the inner margin and a green cast;
# content sits well inside the page. Crop lightly to drop header/footer page
# numbers and the gutter shadow.
DEFAULT_CROP = CropPadding(left=3.5, top=4.0, right=3.5, bottom=4.5)


OCR_PROMPT = """You are performing OCR on a scanned page from a Japanese-published Ainu language documentation volume (Tamura Suzuko's field recordings of Sakhalin, Nayoro and Kushiro Ainu).

Pages come in a few layouts; transcribe whichever you see FAITHFULLY in reading order:

1. Interlinear oral text. Numbered lines (1, 2, 3 …). Each item has, on the LEFT, an Ainu line written in KATAKANA, and directly BELOW it the SAME line in Latin transliteration; on the RIGHT, a Japanese translation. Output each item as: the number, then the katakana line, then the Latin line, then the Japanese translation. Keep the katakana line and Latin line on separate lines. Keep the Japanese translation on its own line after them.

2. Vocabulary list. Numbered entries (1., 2., 3. …) shaped: number, then (optionally) a Japanese gloss, then the Ainu word in Latin, then (optionally) a Japanese note. Keep them in column order as printed. A header like "3 ページ" may appear — keep it.

3. Ainu word index (アイヌ語索引). Two columns of: a Latin Ainu lemma followed by a list of reference numbers (e.g. "ahkas 22, 72"). Read the LEFT column fully top-to-bottom first, then the RIGHT column. Do not interleave columns. Single-letter section headers (A, C, E, H …) appear between groups — keep them.

General rules:
- Preserve ALL diacritics exactly: acute accents marking pitch (á é í ó ú), apostrophes ('), equals signs (=), hyphens, dots, parentheses, and quotation marks.
- Preserve superscript footnote markers (render as the bare number, e.g. enkusu24 -> enkusu^24) and transcribe any footnotes at the bottom of the page after a horizontal rule, prefixed by their marker.
- Ainu katakana uses small kana that are meaningful. Use the adjacent Latin line to disambiguate. Small kana: k->ㇰ, s->ㇱ, p->ㇷ゚, m->ㇺ; syllable-final r after a vowel: ar->ㇻ, ir->ㇼ, ur->ㇽ, er->ㇾ, or->ㇿ. Use small ッ for syllable-final t.
- Keep the page-number footer out (do not output the "— 60 —" style footer).
- Do NOT translate, normalize, summarize, or add commentary. Do NOT output Markdown. If a glyph is illegible, output [?].
"""


def render_page(pdf_path: Path, page: int, output_png: Path, dpi: int) -> None:
    prefix = output_png.with_suffix("")
    ensure_dir(output_png.parent)
    result = run_command(
        [
            "pdftoppm",
            "-f",
            str(page),
            "-l",
            str(page),
            "-r",
            str(dpi),
            "-png",
            str(pdf_path),
            str(prefix),
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"pdftoppm failed for page {page}")

    candidates = list(output_png.parent.glob(f"{prefix.name}-*.png"))
    if not candidates:
        raise FileNotFoundError(f"Expected rendered page not found for {pdf_path}:{page}")
    if len(candidates) > 1:
        match = [c for c in candidates if c.stem.endswith(str(page))]
        candidates = match or candidates
    shutil.move(candidates[0], output_png)


def build_image_hashes_local(pdf_path: Path, image_paths: dict[str, Path]) -> dict[str, str]:
    hashes = {"pdf": file_sha256(pdf_path)}
    for label, path in image_paths.items():
        hashes[label] = file_sha256(path)
    return hashes


def run_pages(
    *,
    pages: list[int],
    models: list[ModelSpec],
    dpi: int,
    crop: CropPadding,
    prompt: str,
    output_root: Path,
    keep_full_page_image: bool,
    skip_ocr: bool,
) -> None:
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF missing: {PDF_PATH}")

    ensure_dir(output_root)
    statuses = model_statuses(models)
    write_text(
        output_root / "backend_status.json",
        json.dumps([asdict(status) for status in statuses], ensure_ascii=False, indent=2),
    )
    available = {status.id: status.available for status in statuses}
    prompt_hash = string_sha256(prompt)

    for page in pages:
        log_progress(f"[page {page}] rendering")
        page_dir = output_root / f"page-{page:03d}"
        status_path = page_dir / "status.json"
        previous_status = read_status_file(status_path, crop)
        full_page_image = page_dir / "images" / "full_page.png"
        cropped_page_image = page_dir / "images" / "cropped_page.png"
        render_page(PDF_PATH, page, full_page_image, dpi)

        with Image.open(full_page_image) as rendered:
            rendered_size = rendered.size
            crop_box = detect_crop_box(rendered, crop)
        if crop_box is not None:
            log_progress(
                f"[page {page}] crop on {rendered_size[0]}x{rendered_size[1]}: {format_crop_box(crop_box)}"
            )
            crop_image(full_page_image, cropped_page_image, crop_box)
        else:
            ensure_dir(cropped_page_image.parent)
            shutil.copy2(full_page_image, cropped_page_image)

        image_paths = {"cropped_page_image": cropped_page_image}
        if keep_full_page_image:
            image_paths["full_page_image"] = full_page_image
        else:
            full_page_image.unlink(missing_ok=True)

        current_status = OCRStatusFile(
            page=page,
            dpi=dpi,
            crop_padding=crop,
            prompt_hash=prompt_hash,
            inputs=build_image_hashes_local(PDF_PATH, image_paths),
            runs={},
        )
        write_status_file(status_path, current_status)

        if skip_ocr:
            log_progress(f"[page {page}] skip_ocr enabled")
            continue

        for model in models:
            output_path = page_dir / "ocr" / f"{sanitize_model_id(model.id)}.txt"
            error_path = page_dir / "ocr" / f"{sanitize_model_id(model.id)}.error.txt"

            if not available.get(model.id, False):
                log_progress(f"[page {page}] unavailable {model.id}")
                record_run_status(
                    current_status,
                    model_id=model.id,
                    ok=False,
                    output_path=error_path,
                    error="model not configured",
                )
                write_text(error_path, "model not configured")
                write_status_file(status_path, current_status)
                continue

            if should_skip_run(
                previous_status,
                model_id=model.id,
                inputs=current_status.inputs,
                dpi=dpi,
                crop_padding=crop,
                prompt_hash=prompt_hash,
            ) and output_path.exists():
                log_progress(f"[page {page}] skipping {model.id} (cached)")
                cached = previous_status.runs[run_key(model.id)] if previous_status else {}
                record_run_status(
                    current_status,
                    model_id=model.id,
                    ok=True,
                    output_path=output_path,
                    usage=cached.get("usage"),
                    response_ms=cached.get("response_ms"),
                    response_cost=cached.get("response_cost"),
                )
                write_status_file(status_path, current_status)
                continue

            try:
                log_progress(f"[page {page}] running {model.id}")
                result = run_llm_ocr(cropped_page_image, model, prompt)
                write_text(output_path, result.text)
                record_run_status(
                    current_status,
                    model_id=model.id,
                    ok=True,
                    output_path=output_path,
                    usage=result.usage,
                    response_ms=result.response_ms,
                    response_cost=result.response_cost,
                )
            except Exception as exc:
                log_progress(f"[page {page}] failed {model.id}: {exc}")
                write_text(error_path, str(exc))
                record_run_status(
                    current_status,
                    model_id=model.id,
                    ok=False,
                    output_path=error_path,
                    error=str(exc),
                )
            write_status_file(status_path, current_status)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OCR the Tamura ELPR A2 volume (Sakhalin/Nayoro/Kushiro)."
    )
    parser.add_argument(
        "--pages",
        nargs="*",
        type=int,
        help="Specific PDF page numbers (1-indexed). Default: content range.",
    )
    parser.add_argument("--start", type=int, default=DEFAULT_PAGE_START)
    parser.add_argument("--end", type=int, default=DEFAULT_PAGE_END)
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI)
    parser.add_argument("--model", action="append", dest="models")
    parser.add_argument("--keep-full-page-image", action="store_true")
    parser.add_argument("--skip-ocr", action="store_true")
    return parser.parse_args()


def main() -> None:
    load_env_files()
    args = parse_args()

    if args.pages:
        pages = args.pages
    else:
        pages = list(range(args.start, args.end + 1))

    model_ids = args.models or DEFAULT_MODELS
    models = [ModelSpec(id=mid) for mid in model_ids]

    run_pages(
        pages=pages,
        models=models,
        dpi=args.dpi,
        crop=DEFAULT_CROP,
        prompt=OCR_PROMPT,
        output_root=OUTPUT_ROOT,
        keep_full_page_image=args.keep_full_page_image,
        skip_ocr=args.skip_ocr,
    )
    write_cost_report(OUTPUT_ROOT, len(pages))
    log_progress(f"OCR outputs written under {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
