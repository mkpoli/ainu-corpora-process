from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path

from litellm import completion

from dictionary.nakagawa_ocr_common import (
    ROOT,
    completion_text,
    config_value,
    estimate_usage_and_cost,
    image_data_url,
    load_env_files,
    log_progress,
    parse_models,
    read_config_section,
    resolve_output_root,
    resolve_pages,
    sanitize_model_id,
)


DEFAULT_CONFIG_PATH = ROOT / "dictionary" / "nakagawa_ocr_compare.toml"
DEFAULT_INPUT_ROOT = ROOT / "dictionary" / "output" / "nakagawa-ocr-prod"
DEFAULT_OUTPUT_ROOT = ROOT / "dictionary" / "output" / "nakagawa-ocr-compare"
DEFAULT_PAGES = list(range(17, 448))
DEFAULT_CANDIDATE_MODELS = [
    "openrouter/openai/gpt-5.4",
    "openrouter/google/gemini-3-flash-preview",
]
DEFAULT_TIE_WINNER = "openrouter/openai/gpt-5.4"
DEFAULT_JUDGE_MODEL = "openrouter/openai/gpt-5.4-nano"
DEFAULT_JUDGE_MIN_CONFIDENCE = 0.75
DEFAULT_JUDGE_MAX_TOKENS = 400
PREFERRED_REPLACEMENTS = {
    ("リ", "ㇼ"),
    ("ル", "ㇽ"),
    ("ラ", "ㇻ"),
    ("レ", "ㇾ"),
    ("ロ", "ㇿ"),
    ("ク", "ㇰ"),
    ("シ", "ㇱ"),
    ("ツ", "ッ"),
    ("ム", "ㇺ"),
}


@dataclass
class CompareConfig:
    pages: list[int]
    input_root: Path
    output_root: Path
    candidate_models: list[str]
    preferred_tie_winner: str
    judge_model: str
    judge_min_confidence: float
    judge_max_tokens: int
    skip_judge: bool


@dataclass
class JudgeDecision:
    winner: str | None
    confidence: float | None
    reason_code: str
    notes: str
    raw_response: str
    usage: dict[str, int] | None
    response_cost: float | None


def build_compare_config(args: argparse.Namespace) -> CompareConfig:
    config_path = Path(args.config) if args.config is not None else DEFAULT_CONFIG_PATH
    file_config = read_config_section(config_path, "compare")
    pages = resolve_pages(
        cli_pages=args.pages,
        cli_page_start=args.page_start,
        cli_page_end=args.page_end,
        file_pages=file_config.get("pages"),
        file_page_range=file_config.get("page_range"),
        default_pages=DEFAULT_PAGES,
    )
    candidate_models = [
        model.id
        for model in parse_models(
            config_value(args.models, file_config.get("candidate_models"), DEFAULT_CANDIDATE_MODELS)
        )
    ]
    input_root = resolve_output_root(
        str(file_config.get("input_dir")) if file_config.get("input_dir") is not None else None,
        DEFAULT_INPUT_ROOT,
    )
    output_root = resolve_output_root(
        str(file_config.get("output_dir")) if file_config.get("output_dir") is not None else None,
        DEFAULT_OUTPUT_ROOT,
    )
    return CompareConfig(
        pages=pages,
        input_root=input_root,
        output_root=output_root,
        candidate_models=candidate_models,
        preferred_tie_winner=str(
            config_value(args.preferred_tie_winner, file_config.get("preferred_tie_winner"), DEFAULT_TIE_WINNER)
        ),
        judge_model=str(config_value(args.judge_model, file_config.get("judge_model"), DEFAULT_JUDGE_MODEL)),
        judge_min_confidence=float(
            config_value(args.judge_min_confidence, file_config.get("judge_min_confidence"), DEFAULT_JUDGE_MIN_CONFIDENCE)
        ),
        judge_max_tokens=int(
            config_value(args.judge_max_tokens, file_config.get("judge_max_tokens"), DEFAULT_JUDGE_MAX_TOKENS)
        ),
        skip_judge=bool(args.skip_judge),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare completed Nakagawa OCR outputs and adjudicate one winner per page."
    )
    parser.add_argument("--config")
    parser.add_argument("--pages", nargs="*", type=int)
    parser.add_argument("--page-start", type=int)
    parser.add_argument("--page-end", type=int)
    parser.add_argument("--model", action="append", dest="models")
    parser.add_argument("--preferred-tie-winner")
    parser.add_argument("--judge-model")
    parser.add_argument("--judge-min-confidence", type=float)
    parser.add_argument("--judge-max-tokens", type=int)
    parser.add_argument(
        "--skip-judge",
        action="store_true",
        help="Do not call the judge model; unresolved pages go to manual review",
    )
    return parser.parse_args()


def normalize_for_compare(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace("　", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def strip_spaces(text: str) -> str:
    return re.sub(r"\s+", "", text)


def candidate_output_path(root: Path, page: int, model_id: str) -> Path:
    return root / f"page-{page:03d}" / "ocr" / f"{sanitize_model_id(model_id)}.txt"


def cropped_image_path(root: Path, page: int) -> Path:
    return root / f"page-{page:03d}" / "images" / "cropped_page.png"


def preferred_small_kana_heuristic(text_a: str, text_b: str) -> tuple[str | None, str]:
    matcher = SequenceMatcher(a=strip_spaces(text_a), b=strip_spaces(text_b), autojunk=False)
    prefer_a = 0
    prefer_b = 0
    saw_non_preferred = False
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        left = strip_spaces(text_a)[i1:i2]
        right = strip_spaces(text_b)[j1:j2]
        if not left and not right:
            continue
        if len(left) != len(right):
            saw_non_preferred = True
            break
        for char_a, char_b in zip(left, right):
            if char_a == char_b:
                continue
            if (char_a, char_b) in PREFERRED_REPLACEMENTS:
                prefer_b += 1
                continue
            if (char_b, char_a) in PREFERRED_REPLACEMENTS:
                prefer_a += 1
                continue
            saw_non_preferred = True
            break
        if saw_non_preferred:
            break
    if saw_non_preferred or prefer_a == prefer_b:
        return None, ""
    if prefer_a > prefer_b:
        return "a", f"preferred_small_kana:{prefer_a}>{prefer_b}"
    return "b", f"preferred_small_kana:{prefer_b}>{prefer_a}"


def judge_prompt(model_a: str, text_a: str, model_b: str, text_b: str) -> str:
    return f"""You are adjudicating between two OCR transcriptions of the same Ainu dictionary page image.

Choose the candidate that better matches the image and adjacent Latin transliteration.
This is not ordinary Japanese OCR. Preserve Ainu orthography and unusual kana exactly.

Important Ainu rules:
- Small kana are semantically important.
- Prefer the transcription supported by the adjacent Latin transliteration.
- Especially for syllable-final r after a vowel:
  - ar -> ㇻ
  - ir -> ㇼ
  - ur -> ㇽ
  - er -> ㇾ
  - or -> ㇿ
- Examples:
  - uirkur -> ウイㇼクㇽ
  - ueus -> ウエウㇱ
  - uekarpare -> ウエカㇻパレ

Candidate A ({model_a}):
<<<A>>>
{text_a}
<<<END_A>>>

Candidate B ({model_b}):
<<<B>>>
{text_b}
<<<END_B>>>

Return JSON only with this schema:
{{
  "winner": "A" | "B" | "unclear",
  "confidence": 0.0,
  "reason_code": "short_snake_case",
  "notes": "one short sentence"
}}
"""


def parse_judge_response(response_text: str) -> tuple[str | None, float | None, str, str]:
    match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if match is None:
        return None, None, "invalid_json", response_text.strip()
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None, None, "invalid_json", response_text.strip()
    winner = payload.get("winner")
    confidence = payload.get("confidence")
    reason_code = str(payload.get("reason_code", "unspecified"))
    notes = str(payload.get("notes", ""))
    if winner == "A":
        normalized_winner = "a"
    elif winner == "B":
        normalized_winner = "b"
    else:
        normalized_winner = None
    try:
        normalized_confidence = float(confidence) if confidence is not None else None
    except (TypeError, ValueError):
        normalized_confidence = None
    return normalized_winner, normalized_confidence, reason_code, notes


def run_judge(
    *,
    image_path: Path,
    model_id: str,
    model_a: str,
    text_a: str,
    model_b: str,
    text_b: str,
    max_tokens: int,
) -> JudgeDecision:
    prompt = judge_prompt(model_a, text_a, model_b, text_b)
    image_data = image_data_url(image_path)
    response = completion(
        model=model_id,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_data}},
                ],
            }
        ],
        temperature=0,
        max_tokens=max_tokens,
        timeout=600,
    )
    response_text = completion_text(response)
    usage = getattr(response, "usage", None) or {}
    response_cost = getattr(response, "_hidden_params", {}).get("response_cost")
    if not usage or response_cost is None:
        usage, estimated_cost = estimate_usage_and_cost(
            model_id=model_id,
            prompt=prompt,
            image_data=image_data,
            output_text=response_text,
        )
        if response_cost is None:
            response_cost = estimated_cost
    winner, confidence, reason_code, notes = parse_judge_response(response_text)
    return JudgeDecision(
        winner=winner,
        confidence=confidence,
        reason_code=reason_code,
        notes=notes,
        raw_response=response_text,
        usage={
            "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
            "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
            "total_tokens": int(usage.get("total_tokens", 0) or 0),
        },
        response_cost=float(response_cost) if response_cost is not None else None,
    )


def write_tsv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def compare_pages(config: CompareConfig) -> None:
    config.output_root.mkdir(parents=True, exist_ok=True)
    decision_rows: list[dict[str, object]] = []
    review_rows: list[dict[str, object]] = []
    override_template_rows: list[dict[str, object]] = []
    judge_cost_total = 0.0
    judge_pages = 0

    if len(config.candidate_models) != 2:
        raise ValueError("compare requires exactly two candidate models")
    model_a, model_b = config.candidate_models
    total_pages = len(config.pages)

    log_progress(
        f"[compare] starting comparison for {total_pages} pages from {config.input_root}"
    )
    log_progress(f"[compare] candidate A: {model_a}")
    log_progress(f"[compare] candidate B: {model_b}")
    if config.skip_judge:
        log_progress("[compare] judge disabled; unresolved pages will go to manual review")
    else:
        log_progress(
            f"[compare] judge model: {config.judge_model} (min confidence {config.judge_min_confidence:.2f})"
        )

    for index, page in enumerate(config.pages, start=1):
        page_dir = config.output_root / f"page-{page:03d}"
        page_dir.mkdir(parents=True, exist_ok=True)
        log_progress(f"[compare {index}/{total_pages}] page {page}: loading candidates")
        path_a = candidate_output_path(config.input_root, page, model_a)
        path_b = candidate_output_path(config.input_root, page, model_b)
        image_path = cropped_image_path(config.input_root, page)
        if not path_a.exists() or not path_b.exists():
            raise FileNotFoundError(f"Missing OCR output for page {page}: {path_a} or {path_b}")
        if not image_path.exists():
            raise FileNotFoundError(f"Missing cropped image for page {page}: {image_path}")

        text_a = path_a.read_text(encoding="utf-8")
        text_b = path_b.read_text(encoding="utf-8")
        normalized_a = normalize_for_compare(text_a)
        normalized_b = normalize_for_compare(text_b)

        winner: str | None = None
        method = ""
        confidence: float | None = None
        review_required = False
        note = ""
        judge: JudgeDecision | None = None

        if text_a == text_b:
            winner = "a" if config.preferred_tie_winner == model_a else "b"
            method = "exact_match"
            confidence = 1.0
            note = "candidate texts identical"
            log_progress(f"[compare {index}/{total_pages}] page {page}: exact match")
        elif normalized_a == normalized_b:
            winner = "a" if config.preferred_tie_winner == model_a else "b"
            method = "normalized_match"
            confidence = 0.98
            note = "differences only in whitespace or line wrapping"
            log_progress(f"[compare {index}/{total_pages}] page {page}: normalized match")
        else:
            heuristic_winner, heuristic_note = preferred_small_kana_heuristic(text_a, text_b)
            if heuristic_winner is not None:
                winner = heuristic_winner
                method = "small_kana_heuristic"
                confidence = 0.85
                note = heuristic_note
                heuristic_model = model_a if heuristic_winner == "a" else model_b
                log_progress(
                    f"[compare {index}/{total_pages}] page {page}: heuristic selected {heuristic_model} ({heuristic_note})"
                )
            elif not config.skip_judge:
                log_progress(
                    f"[compare {index}/{total_pages}] page {page}: sending disagreement to judge {config.judge_model}"
                )
                judge = run_judge(
                    image_path=image_path,
                    model_id=config.judge_model,
                    model_a=model_a,
                    text_a=text_a,
                    model_b=model_b,
                    text_b=text_b,
                    max_tokens=config.judge_max_tokens,
                )
                judge_pages += 1
                if judge.response_cost is not None:
                    judge_cost_total += judge.response_cost
                method = "judge"
                winner = judge.winner
                confidence = judge.confidence
                note = f"{judge.reason_code}: {judge.notes}".strip()
                judge_winner_model = model_a if winner == "a" else model_b if winner == "b" else "unclear"
                log_progress(
                    f"[compare {index}/{total_pages}] page {page}: judge result winner={judge_winner_model} confidence={confidence if confidence is not None else 'n/a'} cost=${judge.response_cost:.6f}"
                    if judge.response_cost is not None
                    else f"[compare {index}/{total_pages}] page {page}: judge result winner={judge_winner_model} confidence={confidence if confidence is not None else 'n/a'}"
                )
                if winner is None or confidence is None or confidence < config.judge_min_confidence:
                    review_required = True
                    log_progress(
                        f"[compare {index}/{total_pages}] page {page}: flagged for manual review"
                    )
            else:
                method = "manual_review"
                review_required = True
                note = "judge skipped"
                log_progress(
                    f"[compare {index}/{total_pages}] page {page}: unresolved, added to manual review"
                )

        if winner is None:
            review_required = True

        selected_model_id = model_a if winner == "a" else model_b if winner == "b" else ""
        selected_output_path = path_a if winner == "a" else path_b if winner == "b" else None
        decision_payload = {
            "page": page,
            "candidate_a_model_id": model_a,
            "candidate_a_path": str(path_a),
            "candidate_b_model_id": model_b,
            "candidate_b_path": str(path_b),
            "image_path": str(image_path),
            "method": method,
            "winner": winner,
            "selected_model_id": selected_model_id,
            "selected_output_path": str(selected_output_path) if selected_output_path is not None else "",
            "confidence": confidence,
            "review_required": review_required,
            "note": note,
            "judge": asdict(judge) if judge is not None else None,
        }
        (page_dir / "decision.json").write_text(
            json.dumps(decision_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        decision_rows.append(decision_payload)
        if review_required:
            review_row = {
                "page": page,
                "method": method,
                "suggested_model_id": selected_model_id,
                "confidence": confidence if confidence is not None else "",
                "note": note,
                "candidate_a_model_id": model_a,
                "candidate_a_path": str(path_a),
                "candidate_b_model_id": model_b,
                "candidate_b_path": str(path_b),
                "image_path": str(image_path),
            }
            review_rows.append(review_row)
            override_template_rows.append(
                {
                    "page": page,
                    "selected_model_id": selected_model_id,
                    "custom_text_path": "",
                    "comment": "",
                }
            )
        elif selected_model_id:
            log_progress(
                f"[compare {index}/{total_pages}] page {page}: selected {selected_model_id} via {method}"
            )

    summary = {
        "pages_total": len(config.pages),
        "exact_match_pages": sum(1 for row in decision_rows if row["method"] == "exact_match"),
        "normalized_match_pages": sum(1 for row in decision_rows if row["method"] == "normalized_match"),
        "heuristic_pages": sum(1 for row in decision_rows if row["method"] == "small_kana_heuristic"),
        "judge_pages": judge_pages,
        "review_required_pages": sum(1 for row in decision_rows if row["review_required"]),
        "winner_counts": {
            model_a: sum(1 for row in decision_rows if row["selected_model_id"] == model_a),
            model_b: sum(1 for row in decision_rows if row["selected_model_id"] == model_b),
        },
        "judge_model": config.judge_model,
        "judge_cost_total": judge_cost_total,
    }
    (config.output_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown = [
        "# OCR Comparison Summary",
        "",
        f"Pages compared: {summary['pages_total']}",
        f"Exact matches: {summary['exact_match_pages']}",
        f"Normalized matches: {summary['normalized_match_pages']}",
        f"Small-kana heuristic decisions: {summary['heuristic_pages']}",
        f"Judge-decided pages: {summary['judge_pages']}",
        f"Manual review required: {summary['review_required_pages']}",
        f"Judge model: {summary['judge_model']}",
        f"Judge cost total: ${summary['judge_cost_total']:.6f}",
        "",
        "## Winner Counts",
        "",
        f"- {model_a}: {summary['winner_counts'][model_a]}",
        f"- {model_b}: {summary['winner_counts'][model_b]}",
    ]
    (config.output_root / "summary.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    (config.output_root / "page_decisions.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in decision_rows),
        encoding="utf-8",
    )
    write_tsv(
        config.output_root / "manual_review.tsv",
        review_rows,
        [
            "page",
            "method",
            "suggested_model_id",
            "confidence",
            "note",
            "candidate_a_model_id",
            "candidate_a_path",
            "candidate_b_model_id",
            "candidate_b_path",
            "image_path",
        ],
    )
    write_tsv(
        config.output_root / "manual_overrides.template.tsv",
        override_template_rows,
        ["page", "selected_model_id", "custom_text_path", "comment"],
    )
    log_progress(
        f"[compare] complete: exact={summary['exact_match_pages']} normalized={summary['normalized_match_pages']} heuristic={summary['heuristic_pages']} judge={summary['judge_pages']} review={summary['review_required_pages']}"
    )
    log_progress(
        f"[compare] winner counts: {model_a}={summary['winner_counts'][model_a]} {model_b}={summary['winner_counts'][model_b]}"
    )
    log_progress(
        f"[compare] wrote summary to {config.output_root / 'summary.md'} and review queue to {config.output_root / 'manual_review.tsv'}"
    )


def main() -> None:
    load_env_files()
    args = parse_args()
    config = build_compare_config(args)
    compare_pages(config)
    print(f"Wrote comparison outputs to {config.output_root}")


if __name__ == "__main__":
    main()
