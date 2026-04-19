from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv
from litellm import completion, cost_per_token, token_counter
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "dictionary" / "input" / "nakagawa" / "アイヌ語千歳方言辞典.pdf"
BENCH_ROOT = ROOT / "dictionary" / "output" / "nakagawa-ocr-benchmark"
DEFAULT_PAGES = [2, 68, 184, 334]
DEFAULT_MODELS = ["openai/gpt-5.4", "openai/gpt-5.4-mini"]
TOTAL_PDF_PAGES = 455
CROP_PADDING_LEFT = 23
CROP_PADDING_TOP = 36
CROP_PADDING_RIGHT = 23
CROP_PADDING_BOTTOM = 50
CROP_RANGE_ADJUST = 0
CROP_BACKGROUND_THRESHOLD = 245
CROP_MIN_DARK_PIXELS_PER_ROW = 40
CROP_MIN_DARK_PIXELS_PER_COL = 12
CROP_MIN_ROW_RUN = 2
CROP_MIN_COL_RUN = 20
AINU_SMALL_KANA = "ㇰ ㇱ ㇲ ㇳ ㇴ ㇵ ㇶ ㇷ゚ ㇸ ㇹ ㇺ ㇻ ㇼ ㇽ ㇾ ㇿ"
OCR_PROMPT = f"""You are performing OCR on a scanned Japanese dictionary page containing Ainu written in katakana and adjacent Latin transliteration.

Return only the recognized text in reading order.
Preserve line breaks where they are visually meaningful.
Do not add explanations, notes, or Markdown.
Do not normalize away unusual characters.

Important Ainu rule:
Small katakana for final consonants are semantically important. Pay close attention to the adjacent Latin transliteration and use it to restore the intended small kana when the scan is ambiguous.

Examples:
- Output ウイㇼクㇽ when the adjacent Latin is uirkur, not ウイリクル.
- Output ウエウㇱ when the adjacent Latin is ueus.
- Output ウエカㇻパレ when the adjacent Latin indicates uekarpare.

Relevant small kana include: {AINU_SMALL_KANA}

If the katakana looks ambiguous but the neighboring Latin transcription is clear, prefer the reading supported by the Latin transcription.
"""


@dataclass
class CropPadding:
    left: int
    top: int
    right: int
    bottom: int


@dataclass
class ModelSpec:
    id: str


@dataclass
class ModelStatus:
    id: str
    available: bool
    detail: str


@dataclass
class BenchmarkStatusFile:
    page: int
    dpi: int
    crop_padding: CropPadding
    crop_range_adjust: int
    prompt_hash: str
    inputs: dict[str, str]
    runs: dict[str, dict[str, object]]


@dataclass
class OCRRunResult:
    text: str
    usage: dict[str, int]
    response_ms: float | None
    response_cost: float | None


def run_command(
    command: list[str], *, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def log_progress(message: str) -> None:
    print(message, flush=True)


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def string_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sanitize_model_id(model_id: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", ".", "_"} else "_" for char in model_id)


def load_env_files() -> None:
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / "dictionary" / ".env", override=True)


def provider_env_var_names(model_id: str) -> list[str]:
    provider = model_id.split("/", 1)[0]
    if provider == "openai":
        return ["OPENAI_API_KEY"]
    if provider == "anthropic":
        return ["ANTHROPIC_API_KEY"]
    if provider in {"gemini", "vertex_ai"}:
        return ["GEMINI_API_KEY", "GOOGLE_API_KEY", "VERTEXAI_PROJECT"]
    if provider == "deepseek":
        return ["DEEPSEEK_API_KEY"]
    if provider == "openrouter":
        return ["OPENROUTER_API_KEY"]
    return []


def model_statuses(models: list[ModelSpec]) -> list[ModelStatus]:
    statuses: list[ModelStatus] = []
    for model in models:
        env_vars = provider_env_var_names(model.id)
        available = True
        detail = "ready"
        if env_vars and not any(os.getenv(name) for name in env_vars):
            available = False
            detail = f"set one of: {', '.join(env_vars)}"
        statuses.append(ModelStatus(id=model.id, available=available, detail=detail))
    return statuses


def read_status_file(path: Path) -> BenchmarkStatusFile | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    crop_padding_payload = payload.get("crop_padding", {})
    return BenchmarkStatusFile(
        page=payload["page"],
        dpi=payload["dpi"],
        crop_padding=CropPadding(
            left=crop_padding_payload.get("left", CROP_PADDING_LEFT),
            top=crop_padding_payload.get("top", CROP_PADDING_TOP),
            right=crop_padding_payload.get("right", CROP_PADDING_RIGHT),
            bottom=crop_padding_payload.get("bottom", CROP_PADDING_BOTTOM),
        ),
        crop_range_adjust=payload.get("crop_range_adjust", CROP_RANGE_ADJUST),
        prompt_hash=payload.get("prompt_hash", ""),
        inputs=payload.get("inputs", {}),
        runs=payload.get("runs", {}),
    )


def write_status_file(path: Path, status: BenchmarkStatusFile) -> None:
    write_text(
        path,
        json.dumps(
            {
                "page": status.page,
                "dpi": status.dpi,
                "crop_padding": asdict(status.crop_padding),
                "crop_range_adjust": status.crop_range_adjust,
                "prompt_hash": status.prompt_hash,
                "inputs": status.inputs,
                "runs": status.runs,
            },
            ensure_ascii=False,
            indent=2,
        ),
    )


def build_input_hashes(raw_image: Path) -> dict[str, str]:
    return {
        "pdf": file_sha256(PDF_PATH),
        "raw_image": file_sha256(raw_image),
    }


def run_key(model_id: str) -> str:
    return sanitize_model_id(model_id)


def should_skip_run(
    previous_status: BenchmarkStatusFile | None,
    *,
    model_id: str,
    inputs: dict[str, str],
    dpi: int,
    crop_padding: CropPadding,
    prompt_hash: str,
) -> bool:
    if previous_status is None:
        return False
    if previous_status.dpi != dpi:
        return False
    if previous_status.crop_padding != crop_padding:
        return False
    if previous_status.crop_range_adjust != CROP_RANGE_ADJUST:
        return False
    if previous_status.prompt_hash != prompt_hash:
        return False
    if previous_status.inputs != inputs:
        return False
    run_status = previous_status.runs.get(run_key(model_id))
    return bool(run_status and run_status.get("ok"))


def record_run_status(
    status: BenchmarkStatusFile,
    *,
    model_id: str,
    ok: bool,
    output_path: Path,
    usage: dict[str, int] | None = None,
    response_ms: float | None = None,
    response_cost: float | None = None,
    error: str | None = None,
) -> None:
    status.runs[run_key(model_id)] = {
        "model_id": model_id,
        "ok": ok,
        "output_path": str(output_path),
        "usage": usage,
        "response_ms": response_ms,
        "response_cost": response_cost,
        "error": error,
    }


def cost_report_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for status_path in sorted(BENCH_ROOT.glob("page-*/status.json")):
        status = read_status_file(status_path)
        if status is None:
            continue
        for run in status.runs.values():
            if not run.get("ok"):
                continue
            rows.append(
                {
                    "page": status.page,
                    "model_id": run.get("model_id"),
                    "response_cost": run.get("response_cost"),
                    "response_ms": run.get("response_ms"),
                    "usage": run.get("usage") or {},
                }
            )
    return rows


def write_cost_report() -> None:
    rows = cost_report_rows()
    by_model: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        model_id = row["model_id"]
        if not isinstance(model_id, str):
            continue
        by_model.setdefault(model_id, []).append(row)

    report_rows: list[dict[str, object]] = []
    for model_id, model_rows in sorted(by_model.items()):
        sampled_pages = len(model_rows)
        known_costs = [
            float(row["response_cost"])
            for row in model_rows
            if row.get("response_cost") is not None
        ]
        prompt_tokens = [
            int((row.get("usage") or {}).get("prompt_tokens", 0)) for row in model_rows
        ]
        completion_tokens = [
            int((row.get("usage") or {}).get("completion_tokens", 0)) for row in model_rows
        ]
        total_tokens = [
            int((row.get("usage") or {}).get("total_tokens", 0)) for row in model_rows
        ]
        response_ms = [
            float(row["response_ms"])
            for row in model_rows
            if row.get("response_ms") is not None
        ]
        average_cost = sum(known_costs) / len(known_costs) if known_costs else None
        report_rows.append(
            {
                "model_id": model_id,
                "sampled_pages": sampled_pages,
                "sample_coverage": sampled_pages / TOTAL_PDF_PAGES,
                "avg_prompt_tokens": sum(prompt_tokens) / sampled_pages if sampled_pages else 0,
                "avg_completion_tokens": sum(completion_tokens) / sampled_pages if sampled_pages else 0,
                "avg_total_tokens": sum(total_tokens) / sampled_pages if sampled_pages else 0,
                "avg_response_ms": sum(response_ms) / len(response_ms) if response_ms else None,
                "avg_cost_per_page": average_cost,
                "estimated_full_dictionary_cost": average_cost * TOTAL_PDF_PAGES
                if average_cost is not None
                else None,
                "estimated_full_dictionary_cost_sampled_only": average_cost * sampled_pages
                if average_cost is not None
                else None,
            }
        )

    write_text(
        BENCH_ROOT / "cost_report.json",
        json.dumps(
            {
                "total_pdf_pages": TOTAL_PDF_PAGES,
                "report_rows": report_rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
    )

    markdown_lines = [
        "# OCR Cost Report",
        "",
        f"Total dictionary pages: {TOTAL_PDF_PAGES}",
        "",
        "| Model | Sampled pages | Avg prompt tokens | Avg completion tokens | Avg total tokens | Avg response ms | Avg cost/page | Estimated full cost |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report_rows:
        avg_response_ms = row["avg_response_ms"]
        avg_cost_per_page = row["avg_cost_per_page"]
        estimated_full_cost = row["estimated_full_dictionary_cost"]
        markdown_lines.append(
            "| {model} | {sampled_pages} | {avg_prompt_tokens:.1f} | {avg_completion_tokens:.1f} | {avg_total_tokens:.1f} | {avg_response_ms} | {avg_cost_per_page} | {estimated_full_cost} |".format(
                model=row["model_id"],
                sampled_pages=row["sampled_pages"],
                avg_prompt_tokens=row["avg_prompt_tokens"],
                avg_completion_tokens=row["avg_completion_tokens"],
                avg_total_tokens=row["avg_total_tokens"],
                avg_response_ms=f"{avg_response_ms:.1f}" if avg_response_ms is not None else "n/a",
                avg_cost_per_page=f"${avg_cost_per_page:.6f}" if avg_cost_per_page is not None else "n/a",
                estimated_full_cost=f"${estimated_full_cost:.2f}" if estimated_full_cost is not None else "n/a",
            )
        )
    write_text(BENCH_ROOT / "cost_report.md", "\n".join(markdown_lines) + "\n")


def render_page(page: int, output_png: Path, dpi: int) -> None:
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
            str(PDF_PATH),
            str(prefix),
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"pdftoppm failed for page {page}")

    rendered = output_png.parent / f"{prefix.name}-{page:03d}.png"
    if not rendered.exists():
        raise FileNotFoundError(f"Expected rendered page not found: {rendered}")
    shutil.move(rendered, output_png)


def find_content_bounds(
    counts: list[int], *, minimum_pixels: int, minimum_run: int, strategy: str
) -> tuple[int, int] | None:
    runs: list[tuple[int, int]] = []
    run_start: int | None = None

    for index, count in enumerate(counts):
        if count >= minimum_pixels:
            if run_start is None:
                run_start = index
            continue
        if run_start is not None:
            if index - run_start >= minimum_run:
                runs.append((run_start, index))
            run_start = None

    if run_start is not None and len(counts) - run_start >= minimum_run:
        runs.append((run_start, len(counts)))

    if not runs:
        return None

    if strategy == "largest":
        return max(runs, key=lambda run: run[1] - run[0])
    return runs[0][0], runs[-1][1]


def detect_crop_box(
    image: Image.Image, crop_padding: CropPadding
) -> tuple[int, int, int, int] | None:
    gray = ImageOps.grayscale(image)
    binary = gray.point(
        lambda px: 255 if px < CROP_BACKGROUND_THRESHOLD else 0,
        mode="1",
    )
    ink = binary.load()

    row_counts = [
        sum(1 for x in range(binary.width) if ink[x, y] != 0)
        for y in range(binary.height)
    ]
    col_counts = [
        sum(1 for y in range(binary.height) if ink[x, y] != 0)
        for x in range(binary.width)
    ]

    row_bounds = find_content_bounds(
        row_counts,
        minimum_pixels=CROP_MIN_DARK_PIXELS_PER_ROW,
        minimum_run=CROP_MIN_ROW_RUN,
        strategy="outer",
    )
    col_bounds = find_content_bounds(
        col_counts,
        minimum_pixels=CROP_MIN_DARK_PIXELS_PER_COL,
        minimum_run=CROP_MIN_COL_RUN,
        strategy="largest",
    )
    if row_bounds is None or col_bounds is None:
        return None

    top, bottom = row_bounds
    left, right = col_bounds
    left = max(0, left - crop_padding.left + CROP_RANGE_ADJUST)
    top = max(0, top - crop_padding.top + CROP_RANGE_ADJUST)
    right = min(image.width, right + crop_padding.right - CROP_RANGE_ADJUST)
    bottom = min(image.height, bottom + crop_padding.bottom - CROP_RANGE_ADJUST)
    if left >= right or top >= bottom:
        return None
    return left, top, right, bottom


def crop_image(source: Path, destination: Path, crop_box: tuple[int, int, int, int]) -> None:
    ensure_dir(destination.parent)
    with Image.open(source) as image:
        image.crop(crop_box).save(destination)


def parse_models(model_args: list[str] | None) -> list[ModelSpec]:
    model_ids = model_args or DEFAULT_MODELS
    return [ModelSpec(id=model_id) for model_id in model_ids]


def image_data_url(image_path: Path) -> str:
    encoded_image = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded_image}"


def estimate_usage_and_cost(
    *, model_id: str, prompt: str, image_data: str, output_text: str
) -> tuple[dict[str, int], float | None]:
    prompt_messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_data}},
            ],
        }
    ]
    prompt_tokens = int(token_counter(model=model_id, messages=prompt_messages) or 0)
    completion_tokens = int(token_counter(model=model_id, text=output_text) or 0)
    total_tokens = prompt_tokens + completion_tokens
    prompt_cost, completion_cost = cost_per_token(
        model=model_id,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
    return (
        {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        },
        float(prompt_cost + completion_cost),
    )


def completion_text(response: Any) -> str:
    message = response.choices[0].message
    content = message.content
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if text:
                    parts.append(text)
            elif hasattr(item, "type") and getattr(item, "type") == "text":
                text = getattr(item, "text", None)
                if text:
                    parts.append(text)
        return "\n".join(parts).strip()
    return ""


def run_llm_ocr(image_path: Path, model: ModelSpec, prompt: str) -> OCRRunResult:
    image_data = image_data_url(image_path)
    response = completion(
        model=model.id,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_data},
                    },
                ],
            }
        ],
        temperature=0,
        max_tokens=8000,
        timeout=600,
    )
    text = completion_text(response)
    usage = getattr(response, "usage", None) or {}
    response_ms = getattr(response, "response_ms", None)
    response_cost = getattr(response, "_hidden_params", {}).get("response_cost")
    if not usage or response_cost is None:
        usage, estimated_cost = estimate_usage_and_cost(
            model_id=model.id,
            prompt=prompt,
            image_data=image_data,
            output_text=text,
        )
        if response_cost is None:
            response_cost = estimated_cost
    return OCRRunResult(
        text=text,
        usage={
            "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
            "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
            "total_tokens": int(usage.get("total_tokens", 0) or 0),
        },
        response_ms=float(response_ms) if response_ms is not None else None,
        response_cost=float(response_cost) if response_cost is not None else None,
    )


def bench_pages(
    pages: Iterable[int],
    *,
    dpi: int,
    skip_ocr: bool,
    models: list[ModelSpec],
    crop_padding: CropPadding,
    prompt: str,
) -> None:
    ensure_dir(BENCH_ROOT)
    statuses = model_statuses(models)
    write_text(
        BENCH_ROOT / "backend_status.json",
        json.dumps([asdict(status) for status in statuses], ensure_ascii=False, indent=2),
    )

    available = {status.id: status.available for status in statuses}
    prompt_hash = string_sha256(prompt)

    for page in pages:
        log_progress(f"[page {page}] rendering")
        page_dir = BENCH_ROOT / f"page-{page:03d}"
        status_path = page_dir / "status.json"
        previous_status = read_status_file(status_path)
        raw_image = page_dir / "images" / "raw.png"
        render_page(page, raw_image, dpi)

        with Image.open(raw_image) as rendered:
            crop_box = detect_crop_box(rendered, crop_padding)
        if crop_box is not None:
            log_progress(f"[page {page}] cropping raw")
            crop_image(raw_image, raw_image, crop_box)

        current_status = BenchmarkStatusFile(
            page=page,
            dpi=dpi,
            crop_padding=crop_padding,
            crop_range_adjust=CROP_RANGE_ADJUST,
            prompt_hash=prompt_hash,
            inputs=build_input_hashes(raw_image),
            runs={},
        )
        write_status_file(status_path, current_status)

        if skip_ocr:
            log_progress(f"[page {page}] skip_ocr enabled")
            continue

        for model in models:
            output_name = f"{sanitize_model_id(model.id)}.txt"
            output_path = page_dir / "ocr" / output_name
            error_path = page_dir / "ocr" / f"{sanitize_model_id(model.id)}.error.txt"

            if not available.get(model.id, False):
                log_progress(f"[page {page}] unavailable {model.id}")
                record_run_status(
                    current_status,
                    model_id=model.id,
                    ok=False,
                    output_path=error_path,
                    usage=None,
                    response_ms=None,
                    response_cost=None,
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
                crop_padding=crop_padding,
                prompt_hash=prompt_hash,
            ) and output_path.exists():
                log_progress(f"[page {page}] skipping {model.id}")
                record_run_status(
                    current_status,
                    model_id=model.id,
                    ok=True,
                    output_path=output_path,
                    usage=previous_status.runs[run_key(model.id)].get("usage"),
                    response_ms=previous_status.runs[run_key(model.id)].get("response_ms"),
                    response_cost=previous_status.runs[run_key(model.id)].get("response_cost"),
                )
                write_status_file(status_path, current_status)
                continue

            try:
                log_progress(f"[page {page}] running {model.id}")
                result = run_llm_ocr(raw_image, model, prompt)
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
            except Exception as exc:  # pragma: no cover - best effort benchmark
                log_progress(f"[page {page}] failed {model.id}")
                write_text(error_path, str(exc))
                record_run_status(
                    current_status,
                    model_id=model.id,
                    ok=False,
                    output_path=error_path,
                    usage=None,
                    response_ms=None,
                    response_cost=None,
                    error=str(exc),
                )
            write_status_file(status_path, current_status)

    write_cost_report()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark multimodal LLM OCR on sampled Nakagawa pages."
    )
    parser.add_argument("--pages", nargs="*", type=int, default=DEFAULT_PAGES)
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--model", action="append", dest="models")
    parser.add_argument("--prompt")
    parser.add_argument("--crop-pad-left", type=int, default=CROP_PADDING_LEFT)
    parser.add_argument("--crop-pad-top", type=int, default=CROP_PADDING_TOP)
    parser.add_argument("--crop-pad-right", type=int, default=CROP_PADDING_RIGHT)
    parser.add_argument("--crop-pad-bottom", type=int, default=CROP_PADDING_BOTTOM)
    parser.add_argument(
        "--skip-ocr",
        action="store_true",
        help="Only render and crop pages without calling any models",
    )
    return parser.parse_args()


def main() -> None:
    load_env_files()
    args = parse_args()
    crop_padding = CropPadding(
        left=args.crop_pad_left,
        top=args.crop_pad_top,
        right=args.crop_pad_right,
        bottom=args.crop_pad_bottom,
    )
    models = parse_models(args.models)
    bench_pages(
        args.pages,
        dpi=args.dpi,
        skip_ocr=args.skip_ocr,
        models=models,
        crop_padding=crop_padding,
        prompt=args.prompt or OCR_PROMPT,
    )
    print(f"Wrote benchmark outputs to {BENCH_ROOT}")


if __name__ == "__main__":
    main()
