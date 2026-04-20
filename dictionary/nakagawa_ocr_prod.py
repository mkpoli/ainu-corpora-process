from __future__ import annotations

import argparse
from pathlib import Path

from dictionary.nakagawa_ocr_common import (
    DEFAULT_CROP_PADDING_BOTTOM,
    DEFAULT_CROP_PADDING_LEFT,
    DEFAULT_CROP_PADDING_RIGHT,
    DEFAULT_CROP_PADDING_TOP,
    DEFAULT_OCR_PROMPT,
    OCRConfig,
    ROOT,
    CropPadding,
    config_value,
    load_env_files,
    parse_models,
    read_config_section,
    resolve_output_root,
    resolve_pages,
    run_ocr_pages,
)


DEFAULT_CONFIG_PATH = ROOT / "dictionary" / "nakagawa_ocr_prod.toml"
DEFAULT_OUTPUT_ROOT = ROOT / "dictionary" / "output" / "nakagawa-ocr-prod"
DEFAULT_PROD_PAGES = list(range(17, 448))
DEFAULT_PROD_MODELS = [
    "openrouter/openai/gpt-5.4",
    "openrouter/google/gemini-3-flash-preview",
]


def build_prod_config(args: argparse.Namespace) -> OCRConfig:
    config_path = Path(args.config) if args.config is not None else DEFAULT_CONFIG_PATH
    file_config = read_config_section(config_path, "prod")
    crop_config = file_config.get("crop_padding", {}) if isinstance(file_config.get("crop_padding", {}), dict) else {}
    pages = resolve_pages(
        cli_pages=args.pages,
        cli_page_start=args.page_start,
        cli_page_end=args.page_end,
        file_pages=file_config.get("pages"),
        file_page_range=file_config.get("page_range"),
        default_pages=DEFAULT_PROD_PAGES,
    )
    output_root = resolve_output_root(
        str(file_config.get("output_dir")) if file_config.get("output_dir") is not None else None,
        DEFAULT_OUTPUT_ROOT,
    )
    keep_full_page_image = bool(file_config.get("keep_full_page_image", False))
    return OCRConfig(
        pages=pages,
        dpi=int(config_value(args.dpi, file_config.get("dpi"), 300)),
        models=parse_models(config_value(args.models, file_config.get("models"), DEFAULT_PROD_MODELS)),
        prompt=str(config_value(args.prompt, file_config.get("prompt"), DEFAULT_OCR_PROMPT)),
        crop_padding=CropPadding(
            left=float(config_value(args.crop_pad_left, crop_config.get("left"), DEFAULT_CROP_PADDING_LEFT)),
            top=float(config_value(args.crop_pad_top, crop_config.get("top"), DEFAULT_CROP_PADDING_TOP)),
            right=float(config_value(args.crop_pad_right, crop_config.get("right"), DEFAULT_CROP_PADDING_RIGHT)),
            bottom=float(config_value(args.crop_pad_bottom, crop_config.get("bottom"), DEFAULT_CROP_PADDING_BOTTOM)),
        ),
        output_root=output_root,
        keep_full_page_image=keep_full_page_image,
        estimated_total_pages=len(pages),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run production Nakagawa OCR across the configured page range."
    )
    parser.add_argument("--config")
    parser.add_argument("--pages", nargs="*", type=int)
    parser.add_argument("--page-start", type=int)
    parser.add_argument("--page-end", type=int)
    parser.add_argument("--dpi", type=int)
    parser.add_argument("--model", action="append", dest="models")
    parser.add_argument("--prompt")
    parser.add_argument("--crop-pad-left", type=float)
    parser.add_argument("--crop-pad-top", type=float)
    parser.add_argument("--crop-pad-right", type=float)
    parser.add_argument("--crop-pad-bottom", type=float)
    parser.add_argument(
        "--skip-ocr",
        action="store_true",
        help="Only render and crop pages without calling any models",
    )
    return parser.parse_args()


def main() -> None:
    load_env_files()
    args = parse_args()
    config = build_prod_config(args)
    run_ocr_pages(config, skip_ocr=args.skip_ocr)
    print(f"Wrote production OCR outputs to {config.output_root}")


if __name__ == "__main__":
    main()
