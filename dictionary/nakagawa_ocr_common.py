from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv
from litellm import completion, cost_per_token, token_counter
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "dictionary" / "input" / "nakagawa" / "アイヌ語千歳方言辞典.pdf"
TOTAL_PDF_PAGES = 455
DEFAULT_MODELS = [
    "openrouter/openai/gpt-5.4",
    "openrouter/openai/gpt-5.4-mini",
    "openrouter/openai/gpt-5.4-nano",
    "openrouter/google/gemini-3-flash-preview",
    "openrouter/google/gemini-3.1-pro-preview",
    "openrouter/anthropic/claude-sonnet-4.6",
    "openrouter/x-ai/grok-4.20",
    "openrouter/qwen/qwen3.5-27b",
]
DEFAULT_CROP_PADDING_LEFT = 1.13
DEFAULT_CROP_PADDING_TOP = 1.45
DEFAULT_CROP_PADDING_RIGHT = 1.13
DEFAULT_CROP_PADDING_BOTTOM = 1.82
AINU_SMALL_KANA_RULES = """- k -> ㇰ
- s -> ㇱ
- t -> ッ
- p -> ㇷ゚
- m -> ㇺ
- tu -> トゥ"""
DEFAULT_OCR_PROMPT = f"""You are performing OCR on a scanned Japanese dictionary page containing Ainu written in katakana and adjacent Latin transliteration.

Return only the recognized text in reading order.
Keep indentations below each entry (0 for head, 1 full width for definitions).
Preserve line breaks where they are visually meaningful.
Do not add explanations, notes, or Markdown.
Do not normalize away unusual characters.

Important Ainu rule:
Small kana in Ainu orthography are semantically important. Pay close attention to the adjacent Latin transliteration and use it to restore the intended small kana when the scan is ambiguous.

In this dictionary, the relevant small kana are:
{AINU_SMALL_KANA_RULES}

Especially important rule for r:
When Latin transcription shows syllable-final r after a vowel, the katakana should use the corresponding small r kana, not a full-sized リ or ル.
- ar -> ㇻ
- ir -> ㇼ
- ur -> ㇽ
- er -> ㇾ
- or -> ㇿ

This reflects repeated-vowel writing in Ainu orthography, e.g. uirkur is written ウイㇼクㇽ, understood as uir(i)kur(u).
So if the Latin is uirkur, do not output ウイリクル, ウイリクㇽ, or ウイルクㇽ. Output ウイㇼクㇽ.

Examples:
- Output ウイㇼクㇽ when the adjacent Latin is uirkur.
- Output ウエウㇱ when the adjacent Latin is ueus.
- Output ウエカㇻパレ when the adjacent Latin indicates uekarpare.

Don't put = in Kana, only in Latn.
"""


@dataclass
class CropPadding:
    left: float
    top: float
    right: float
    bottom: float


@dataclass
class ModelSpec:
    id: str


@dataclass
class ModelStatus:
    id: str
    available: bool
    detail: str


@dataclass
class OCRStatusFile:
    page: int
    dpi: int
    crop_padding: CropPadding
    prompt_hash: str
    inputs: dict[str, str]
    runs: dict[str, dict[str, object]]


@dataclass
class OCRRunResult:
    text: str
    usage: dict[str, int]
    response_ms: float | None
    response_cost: float | None


@dataclass
class OCRConfig:
    pages: list[int]
    dpi: int
    models: list[ModelSpec]
    prompt: str
    crop_padding: CropPadding
    output_root: Path
    keep_full_page_image: bool
    estimated_total_pages: int


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


def read_config_section(path: Path, section_name: str) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        payload = tomllib.load(handle)
    section = payload.get(section_name, {})
    if not isinstance(section, dict):
        raise ValueError(f"Invalid config section [{section_name}] in {path}")
    return section


def config_value(cli_value: Any, file_value: Any, default_value: Any) -> Any:
    return cli_value if cli_value is not None else file_value if file_value is not None else default_value


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
    if provider in {"x-ai", "xai"}:
        return ["XAI_API_KEY"]
    if provider == "qwen":
        return []
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


def read_status_file(path: Path, crop_padding: CropPadding) -> OCRStatusFile | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    crop_padding_payload = payload.get("crop_padding", {})
    return OCRStatusFile(
        page=payload["page"],
        dpi=payload["dpi"],
        crop_padding=CropPadding(
            left=float(crop_padding_payload.get("left", crop_padding.left)),
            top=float(crop_padding_payload.get("top", crop_padding.top)),
            right=float(crop_padding_payload.get("right", crop_padding.right)),
            bottom=float(crop_padding_payload.get("bottom", crop_padding.bottom)),
        ),
        prompt_hash=payload.get("prompt_hash", ""),
        inputs=payload.get("inputs", {}),
        runs=payload.get("runs", {}),
    )


def write_status_file(path: Path, status: OCRStatusFile) -> None:
    write_text(
        path,
        json.dumps(
            {
                "page": status.page,
                "dpi": status.dpi,
                "crop_padding": asdict(status.crop_padding),
                "prompt_hash": status.prompt_hash,
                "inputs": status.inputs,
                "runs": status.runs,
            },
            ensure_ascii=False,
            indent=2,
        ),
    )


def build_image_hashes(*, pdf_path: Path, image_paths: dict[str, Path]) -> dict[str, str]:
    hashes = {"pdf": file_sha256(pdf_path)}
    for label, image_path in image_paths.items():
        hashes[label] = file_sha256(image_path)
    return hashes


def run_key(model_id: str) -> str:
    return sanitize_model_id(model_id)


def should_skip_run(
    previous_status: OCRStatusFile | None,
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
    if previous_status.prompt_hash != prompt_hash:
        return False
    if previous_status.inputs != inputs:
        return False
    run_status = previous_status.runs.get(run_key(model_id))
    return bool(run_status and run_status.get("ok"))


def record_run_status(
    status: OCRStatusFile,
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


def cost_report_rows(output_root: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for status_path in sorted(output_root.glob("page-*/status.json")):
        status = read_status_file(status_path, CropPadding(0, 0, 0, 0))
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


def write_cost_report(output_root: Path, estimated_total_pages: int) -> None:
    rows = cost_report_rows(output_root)
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
                "sample_coverage": sampled_pages / estimated_total_pages if estimated_total_pages else 0,
                "avg_prompt_tokens": sum(prompt_tokens) / sampled_pages if sampled_pages else 0,
                "avg_completion_tokens": sum(completion_tokens) / sampled_pages if sampled_pages else 0,
                "avg_total_tokens": sum(total_tokens) / sampled_pages if sampled_pages else 0,
                "avg_response_ms": sum(response_ms) / len(response_ms) if response_ms else None,
                "avg_cost_per_page": average_cost,
                "estimated_total_cost": average_cost * estimated_total_pages if average_cost is not None else None,
                "estimated_sample_cost": average_cost * sampled_pages if average_cost is not None else None,
            }
        )

    write_text(
        output_root / "cost_report.json",
        json.dumps(
            {
                "estimated_total_pages": estimated_total_pages,
                "report_rows": report_rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
    )

    markdown_lines = [
        "# OCR Cost Report",
        "",
        f"Estimated total pages: {estimated_total_pages}",
        "",
        "| Model | Sampled pages | Avg prompt tokens | Avg completion tokens | Avg total tokens | Avg response ms | Avg cost/page | Estimated total cost |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report_rows:
        avg_response_ms = row["avg_response_ms"]
        avg_cost_per_page = row["avg_cost_per_page"]
        estimated_total_cost = row["estimated_total_cost"]
        markdown_lines.append(
            "| {model} | {sampled_pages} | {avg_prompt_tokens:.1f} | {avg_completion_tokens:.1f} | {avg_total_tokens:.1f} | {avg_response_ms} | {avg_cost_per_page} | {estimated_total_cost} |".format(
                model=row["model_id"],
                sampled_pages=row["sampled_pages"],
                avg_prompt_tokens=row["avg_prompt_tokens"],
                avg_completion_tokens=row["avg_completion_tokens"],
                avg_total_tokens=row["avg_total_tokens"],
                avg_response_ms=f"{avg_response_ms:.1f}" if avg_response_ms is not None else "n/a",
                avg_cost_per_page=f"${avg_cost_per_page:.6f}" if avg_cost_per_page is not None else "n/a",
                estimated_total_cost=f"${estimated_total_cost:.2f}" if estimated_total_cost is not None else "n/a",
            )
        )
    write_text(output_root / "cost_report.md", "\n".join(markdown_lines) + "\n")


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


def detect_crop_box(
    image: Image.Image, crop_padding: CropPadding
) -> tuple[int, int, int, int] | None:
    left = max(0, round(image.width * crop_padding.left / 100))
    top = max(0, round(image.height * crop_padding.top / 100))
    right = min(image.width, image.width - round(image.width * crop_padding.right / 100))
    bottom = min(
        image.height,
        image.height - round(image.height * crop_padding.bottom / 100),
    )
    if left >= right or top >= bottom:
        return None
    return left, top, right, bottom


def crop_image(source: Path, destination: Path, crop_box: tuple[int, int, int, int]) -> None:
    ensure_dir(destination.parent)
    with Image.open(source) as image:
        image.crop(crop_box).save(destination)


def format_crop_box(crop_box: tuple[int, int, int, int]) -> str:
    left, top, right, bottom = crop_box
    return (
        f"left={left}, top={top}, right={right}, bottom={bottom}, "
        f"width={right - left}, height={bottom - top}"
    )


def parse_models(model_args: list[str] | None) -> list[ModelSpec]:
    model_ids = model_args or DEFAULT_MODELS
    return [ModelSpec(id=model_id) for model_id in model_ids]


def expand_page_range(start: int, end: int) -> list[int]:
    if start > end:
        raise ValueError(f"Invalid page range: start {start} is greater than end {end}")
    return list(range(start, end + 1))


def resolve_pages(
    *,
    cli_pages: list[int] | None,
    cli_page_start: int | None,
    cli_page_end: int | None,
    file_pages: list[int] | None,
    file_page_range: list[int] | None,
    default_pages: list[int],
) -> list[int]:
    if cli_pages is not None:
        return list(cli_pages)
    if cli_page_start is not None or cli_page_end is not None:
        if cli_page_start is None or cli_page_end is None:
            raise ValueError("Both --page-start and --page-end are required together")
        return expand_page_range(cli_page_start, cli_page_end)
    if file_pages is not None:
        return list(file_pages)
    if file_page_range is not None:
        if len(file_page_range) != 2:
            raise ValueError("page_range must be [start, end]")
        return expand_page_range(int(file_page_range[0]), int(file_page_range[1]))
    return list(default_pages)


def resolve_output_root(path_value: str | None, default_root: Path) -> Path:
    if path_value is None:
        return default_root
    path = Path(path_value)
    if path.is_absolute():
        return path
    return ROOT / path


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


def run_ocr_pages(config: OCRConfig, *, skip_ocr: bool) -> None:
    ensure_dir(config.output_root)
    statuses = model_statuses(config.models)
    write_text(
        config.output_root / "backend_status.json",
        json.dumps([asdict(status) for status in statuses], ensure_ascii=False, indent=2),
    )

    available = {status.id: status.available for status in statuses}
    prompt_hash = string_sha256(config.prompt)

    for page in config.pages:
        log_progress(f"[page {page}] rendering")
        page_dir = config.output_root / f"page-{page:03d}"
        status_path = page_dir / "status.json"
        previous_status = read_status_file(status_path, config.crop_padding)
        full_page_image = page_dir / "images" / "full_page.png"
        cropped_page_image = page_dir / "images" / "cropped_page.png"
        render_page(page, full_page_image, config.dpi)

        with Image.open(full_page_image) as rendered:
            rendered_size = rendered.size
            crop_box = detect_crop_box(rendered, config.crop_padding)
        log_progress(
            f"[page {page}] crop margins from config left={config.crop_padding.left:.2f}% top={config.crop_padding.top:.2f}% right={config.crop_padding.right:.2f}% bottom={config.crop_padding.bottom:.2f}%"
        )
        if crop_box is not None:
            log_progress(
                f"[page {page}] detected crop box on rendered {rendered_size[0]}x{rendered_size[1]}: {format_crop_box(crop_box)}"
            )
            crop_image(full_page_image, cropped_page_image, crop_box)
        else:
            log_progress(
                f"[page {page}] crop detection found no content bounds; copying rendered page unchanged"
            )
            ensure_dir(cropped_page_image.parent)
            shutil.copy2(full_page_image, cropped_page_image)

        with Image.open(cropped_page_image) as cropped:
            cropped_size = cropped.size
        log_progress(
            f"[page {page}] wrote cropped page image {cropped_size[0]}x{cropped_size[1]} to {cropped_page_image}"
        )

        image_paths = {"cropped_page_image": cropped_page_image}
        if config.keep_full_page_image:
            image_paths["full_page_image"] = full_page_image
        else:
            full_page_image.unlink(missing_ok=True)

        current_status = OCRStatusFile(
            page=page,
            dpi=config.dpi,
            crop_padding=config.crop_padding,
            prompt_hash=prompt_hash,
            inputs=build_image_hashes(pdf_path=PDF_PATH, image_paths=image_paths),
            runs={},
        )
        write_status_file(status_path, current_status)

        if skip_ocr:
            log_progress(f"[page {page}] skip_ocr enabled")
            continue

        for model in config.models:
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
                dpi=config.dpi,
                crop_padding=config.crop_padding,
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
                result = run_llm_ocr(cropped_page_image, model, config.prompt)
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

    write_cost_report(config.output_root, config.estimated_total_pages)
