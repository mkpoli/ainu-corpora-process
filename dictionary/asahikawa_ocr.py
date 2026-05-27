"""OCR pipeline for Asahikawa City Museum Research Bulletin Ainu sections.

OCRs four articles by 魚井 一山 from the Asahikawa City Museum Research Bulletin:
- Vol.1 (1995) 旭川採集アイヌ語動詞語彙集Ⅰ  pages 17–31
- Vol.2 (1996) 旭川採集アイヌ語動詞語彙集Ⅱ  pages 2–19
- Vol.12 (2006) 旭川採集アイヌ語名詞集 (part 1)  pages 2–21
- Vol.13 (2007) 旭川採集アイヌ語名詞集 (part 2)  pages 2–11

Pages contain romanized Ainu lemmas with Japanese definitions in a 2-column
layout. Unlike the Nakagawa dictionary there is no katakana, so the prompt is
adapted to focus on faithful Latin + Japanese transcription.

Outputs land under dictionary/output/asahikawa-ocr/vol{NN}/page-{PPP}/ following
the same status/cost-report layout used by nakagawa_ocr_*.
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
    OCRConfig,
    OCRStatusFile,
    build_image_hashes,
    completion_text,  # noqa: F401  re-exported for parity
    crop_image,
    detect_crop_box,
    ensure_dir,
    estimate_usage_and_cost,  # noqa: F401
    file_sha256,
    format_crop_box,
    image_data_url,  # noqa: F401
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
INPUT_DIR = ROOT / "dictionary" / "input" / "asahikawa"
OUTPUT_ROOT = ROOT / "dictionary" / "output" / "asahikawa-ocr"

DEFAULT_DPI = 300
DEFAULT_MODELS = [
    "openrouter/google/gemini-3-flash-preview",
    "openrouter/openai/gpt-5.4",
]

# Articles in scope. Page numbers are PDF (1-indexed) page numbers.
ARTICLES: dict[str, dict[str, object]] = {
    "vol01": {
        "pdf": "kenkyu01.pdf",
        "page_start": 17,
        "page_end": 31,
        "title": "旭川採集アイヌ語動詞語彙集Ⅰ",
        "year": 1995,
    },
    "vol02": {
        "pdf": "kenkyu02.pdf",
        "page_start": 2,
        "page_end": 19,
        "title": "旭川採集アイヌ語動詞語彙集Ⅱ",
        "year": 1996,
    },
    "vol12": {
        "pdf": "kenkyu12.pdf",
        "page_start": 2,
        "page_end": 21,
        "title": "旭川採集アイヌ語名詞集 (part 1)",
        "year": 2006,
    },
    "vol13": {
        "pdf": "kenkyu13.pdf",
        "page_start": 2,
        "page_end": 11,
        "title": "旭川採集アイヌ語名詞集 (part 2)",
        "year": 2007,
    },
}

# Margins on this scan are mild; the printed mirror area is well inside the page
# but column gutters are wide. Light crop to remove header/footer noise.
DEFAULT_CROP = CropPadding(left=3.0, top=3.5, right=3.0, bottom=4.0)

OCR_PROMPT = """You are performing OCR on a scanned Japanese journal page from the Asahikawa City Museum Research Bulletin. The article is an Ainu-Japanese vocabulary list.

Layout: two columns per page. Read the left column top-to-bottom first, then the right column. Do not interleave.

Each entry typically has this shape:
  lemma  〈grammar tag〉 〈Japanese definition〉   〈example phrase〉  〈Japanese gloss〉
The lemma is romanized Ainu (lowercase Latin, sometimes italic, sometimes containing a hyphen or apostrophe). The grammar tag is bracketed Japanese such as 〈他〉 〈自〉 〈名〉 〈他完〉. The definition mixes Japanese kana, kanji, and additional romanized Ainu example phrases.

Return only the recognized text in reading order. Use a blank line between entries when one is visually clear. Preserve hyphens, apostrophes, parentheses, dots and other punctuation exactly as printed. Do not normalize away unusual characters or invent words you can't read - mark uncertain glyphs with [?] instead.

Do not output markdown, headings, page numbers, or any explanatory text. Do not translate. Do not collapse Latin/Japanese together - keep them in the order they appear on the page.

The Ainu romanization here uses ONLY Latin letters; there is no katakana on the page, so do not output any katakana.
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

    # pdftoppm picks the suffix width based on total pages; try a few widths.
    candidates = list(output_png.parent.glob(f"{prefix.name}-*.png"))
    if not candidates:
        raise FileNotFoundError(f"Expected rendered page not found for {pdf_path}:{page}")
    if len(candidates) > 1:
        # Choose the one matching this page number; warn otherwise.
        match = [c for c in candidates if c.stem.endswith(str(page))]
        candidates = match or candidates
    shutil.move(candidates[0], output_png)


def build_image_hashes_local(pdf_path: Path, image_paths: dict[str, Path]) -> dict[str, str]:
    hashes = {"pdf": file_sha256(pdf_path)}
    for label, path in image_paths.items():
        hashes[label] = file_sha256(path)
    return hashes


def run_article(
    article_key: str,
    *,
    models: list[ModelSpec],
    dpi: int,
    crop: CropPadding,
    prompt: str,
    pages: list[int] | None,
    output_root: Path,
    keep_full_page_image: bool,
    skip_ocr: bool,
) -> None:
    article = ARTICLES[article_key]
    pdf_path = INPUT_DIR / str(article["pdf"])
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF missing: {pdf_path}")

    if pages is None:
        pages = list(
            range(int(article["page_start"]), int(article["page_end"]) + 1)  # type: ignore[arg-type]
        )

    article_root = output_root / article_key
    ensure_dir(article_root)

    statuses = model_statuses(models)
    write_text(
        article_root / "backend_status.json",
        json.dumps([asdict(status) for status in statuses], ensure_ascii=False, indent=2),
    )
    available = {status.id: status.available for status in statuses}
    prompt_hash = string_sha256(prompt)

    for page in pages:
        log_progress(f"[{article_key} page {page}] rendering")
        page_dir = article_root / f"page-{page:03d}"
        status_path = page_dir / "status.json"
        previous_status = read_status_file(status_path, crop)
        full_page_image = page_dir / "images" / "full_page.png"
        cropped_page_image = page_dir / "images" / "cropped_page.png"
        render_page(pdf_path, page, full_page_image, dpi)

        with Image.open(full_page_image) as rendered:
            rendered_size = rendered.size
            crop_box = detect_crop_box(rendered, crop)
        log_progress(
            f"[{article_key} page {page}] crop margins L={crop.left:.2f}% T={crop.top:.2f}% R={crop.right:.2f}% B={crop.bottom:.2f}%"
        )
        if crop_box is not None:
            log_progress(
                f"[{article_key} page {page}] crop on {rendered_size[0]}x{rendered_size[1]}: {format_crop_box(crop_box)}"
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
            inputs=build_image_hashes_local(pdf_path, image_paths),
            runs={},
        )
        write_status_file(status_path, current_status)

        if skip_ocr:
            log_progress(f"[{article_key} page {page}] skip_ocr enabled")
            continue

        for model in models:
            output_path = page_dir / "ocr" / f"{sanitize_model_id(model.id)}.txt"
            error_path = page_dir / "ocr" / f"{sanitize_model_id(model.id)}.error.txt"

            if not available.get(model.id, False):
                log_progress(f"[{article_key} page {page}] unavailable {model.id}")
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
                log_progress(f"[{article_key} page {page}] skipping {model.id} (cached)")
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
                log_progress(f"[{article_key} page {page}] running {model.id}")
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
                log_progress(f"[{article_key} page {page}] failed {model.id}: {exc}")
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
        description="Run OCR over the four Asahikawa Ainu articles, or a sample range."
    )
    parser.add_argument(
        "--articles",
        nargs="*",
        choices=sorted(ARTICLES.keys()),
        help="Subset of articles to process (default: all four).",
    )
    parser.add_argument(
        "--pages",
        nargs="*",
        type=int,
        help="Specific page numbers to render (overrides article ranges).",
    )
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI)
    parser.add_argument("--model", action="append", dest="models")
    parser.add_argument("--keep-full-page-image", action="store_true")
    parser.add_argument("--skip-ocr", action="store_true")
    return parser.parse_args()


def main() -> None:
    load_env_files()
    args = parse_args()

    article_keys = args.articles or list(ARTICLES.keys())
    model_ids = args.models or DEFAULT_MODELS
    models = [ModelSpec(id=mid) for mid in model_ids]

    ensure_dir(OUTPUT_ROOT)

    for key in article_keys:
        run_article(
            key,
            models=models,
            dpi=args.dpi,
            crop=DEFAULT_CROP,
            prompt=OCR_PROMPT,
            pages=args.pages,
            output_root=OUTPUT_ROOT,
            keep_full_page_image=args.keep_full_page_image,
            skip_ocr=args.skip_ocr,
        )
        # Per-article cost report.
        estimated = (
            int(ARTICLES[key]["page_end"]) - int(ARTICLES[key]["page_start"]) + 1  # type: ignore[arg-type]
        )
        write_cost_report(OUTPUT_ROOT / key, estimated)

    log_progress(f"OCR outputs written under {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
