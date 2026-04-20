from __future__ import annotations

import argparse
import csv
import json
import shutil
from difflib import unified_diff
from pathlib import Path

from dictionary.nakagawa_ocr_common import ROOT, config_value, read_config_section, resolve_output_root


DEFAULT_CONFIG_PATH = ROOT / "dictionary" / "nakagawa_ocr_prepare_review.toml"
DEFAULT_COMPARE_ROOT = ROOT / "dictionary" / "output" / "nakagawa-ocr-compare"
DEFAULT_REVIEW_ROOT = ROOT / "dictionary" / "output" / "nakagawa-ocr-review"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare an editor-friendly OCR review workspace from comparison results."
    )
    parser.add_argument("--config")
    parser.add_argument("--compare-dir")
    parser.add_argument("--output-dir")
    parser.add_argument(
        "--all-pages",
        action="store_true",
        help="Prepare review files for all pages, not only pages flagged for manual review",
    )
    return parser.parse_args()


def build_paths(args: argparse.Namespace) -> tuple[Path, Path, bool]:
    config_path = Path(args.config) if args.config is not None else DEFAULT_CONFIG_PATH
    file_config = read_config_section(config_path, "review")
    compare_root = resolve_output_root(
        str(config_value(args.compare_dir, file_config.get("compare_dir"), str(DEFAULT_COMPARE_ROOT))),
        DEFAULT_COMPARE_ROOT,
    )
    review_root = resolve_output_root(
        str(config_value(args.output_dir, file_config.get("output_dir"), str(DEFAULT_REVIEW_ROOT))),
        DEFAULT_REVIEW_ROOT,
    )
    prepare_all_pages = bool(config_value(args.all_pages, file_config.get("all_pages"), False))
    return compare_root, review_root, prepare_all_pages


def model_slug(model_id: str) -> str:
    if model_id == "openrouter/openai/gpt-5.4":
        return "gpt-5.4"
    if model_id == "openrouter/google/gemini-3-flash-preview":
        return "gemini-3-flash-preview"
    return model_id.replace("/", "__")


def copy_text(source_path: Path, destination_path: Path) -> None:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination_path)


def write_review_notes(path: Path, payload: dict[str, object]) -> None:
    lines = [
        f"page: {payload['page']}",
        f"method: {payload.get('method', '')}",
        f"selected_model_id: {payload.get('selected_model_id', '')}",
        f"review_required: {payload.get('review_required', False)}",
        f"confidence: {payload.get('confidence', '')}",
        f"note: {payload.get('note', '')}",
        f"candidate_a_model_id: {payload.get('candidate_a_model_id', '')}",
        f"candidate_b_model_id: {payload.get('candidate_b_model_id', '')}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_candidate_diff(
    path: Path,
    *,
    candidate_a_name: str,
    candidate_a_text: str,
    candidate_b_name: str,
    candidate_b_text: str,
) -> None:
    diff_lines = list(
        unified_diff(
            candidate_a_text.splitlines(keepends=True),
            candidate_b_text.splitlines(keepends=True),
            fromfile=candidate_a_name,
            tofile=candidate_b_name,
            lineterm="",
        )
    )
    if diff_lines:
        content = "\n".join(diff_lines) + "\n"
    else:
        content = "No textual differences detected.\n"
    path.write_text(content, encoding="utf-8")


def prepare_review_workspace(compare_root: Path, review_root: Path, prepare_all_pages: bool) -> None:
    decision_paths = sorted(compare_root.glob("page-*/decision.json"))
    if not decision_paths:
        raise FileNotFoundError(f"No comparison decisions found in {compare_root}")

    prepared_rows: list[dict[str, object]] = []
    for decision_path in decision_paths:
        payload = json.loads(decision_path.read_text(encoding="utf-8"))
        page = int(payload["page"])
        review_required = bool(payload.get("review_required", False))
        if not prepare_all_pages and not review_required:
            continue

        page_dir = review_root / f"page-{page:03d}"
        page_dir.mkdir(parents=True, exist_ok=True)

        candidate_a_path = Path(str(payload["candidate_a_path"]))
        candidate_b_path = Path(str(payload["candidate_b_path"]))
        candidate_a_model_id = str(payload["candidate_a_model_id"])
        candidate_b_model_id = str(payload["candidate_b_model_id"])
        selected_output_path = str(payload.get("selected_output_path", "")).strip()
        selected_model_id = str(payload.get("selected_model_id", "")).strip()
        image_path = Path(str(payload["image_path"]))
        candidate_a_name = f"{model_slug(candidate_a_model_id)}.txt"
        candidate_b_name = f"{model_slug(candidate_b_model_id)}.txt"
        candidate_a_text = candidate_a_path.read_text(encoding="utf-8")
        candidate_b_text = candidate_b_path.read_text(encoding="utf-8")

        copy_text(candidate_a_path, page_dir / candidate_a_name)
        copy_text(candidate_b_path, page_dir / candidate_b_name)
        shutil.copy2(image_path, page_dir / "cropped_page.png")
        write_candidate_diff(
            page_dir / "candidates.diff",
            candidate_a_name=candidate_a_name,
            candidate_a_text=candidate_a_text,
            candidate_b_name=candidate_b_name,
            candidate_b_text=candidate_b_text,
        )

        if selected_output_path:
            seed_source_path = Path(selected_output_path)
        elif candidate_a_path.exists():
            seed_source_path = candidate_a_path
            selected_model_id = candidate_a_model_id
        else:
            seed_source_path = candidate_b_path
            selected_model_id = candidate_b_model_id
        copy_text(seed_source_path, page_dir / "final.txt")

        (page_dir / "decision.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (page_dir / "review_state.json").write_text(
            json.dumps(
                {
                    "page": page,
                    "seed_source_path": str(seed_source_path),
                    "seed_model_id": selected_model_id,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        write_review_notes(page_dir / "README.txt", payload)

        prepared_rows.append(
            {
                "page": page,
                "review_required": review_required,
                "seed_model_id": selected_model_id,
                "method": payload.get("method", ""),
                "confidence": payload.get("confidence", ""),
                "note": payload.get("note", ""),
                "workspace_dir": str(page_dir),
            }
        )

    review_root.mkdir(parents=True, exist_ok=True)
    with (review_root / "review_index.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["page", "review_required", "seed_model_id", "method", "confidence", "note", "workspace_dir"],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(prepared_rows)
    summary_lines = [
        "# OCR Review Workspace",
        "",
        f"Prepared pages: {len(prepared_rows)}",
        f"Source compare dir: {compare_root}",
        f"Workspace dir: {review_root}",
        "",
        "Each prepared page directory contains:",
        "- final.txt: editable seeded final text",
        "- gpt-5.4.txt or candidate-specific file: candidate A text",
        "- gemini-3-flash-preview.txt or candidate-specific file: candidate B text",
        "- candidates.diff: unified diff between the two candidate texts",
        "- cropped_page.png: page image for visual review",
        "- decision.json: automatic comparison decision payload",
        "- review_state.json: seed metadata used to detect later edits",
        "- README.txt: quick page-level notes",
    ]
    (review_root / "README.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")


def main() -> None:
    compare_root, review_root, prepare_all_pages = build_paths(parse_args())
    prepare_review_workspace(compare_root, review_root, prepare_all_pages)
    print(f"Wrote review workspace to {review_root}")


if __name__ == "__main__":
    main()
