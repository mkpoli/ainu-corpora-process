from __future__ import annotations

import argparse
import csv
import json
import hashlib
from pathlib import Path

from dictionary.nakagawa_ocr_common import (
    ROOT,
    config_value,
    read_config_section,
    resolve_output_root,
)


DEFAULT_CONFIG_PATH = ROOT / "dictionary" / "nakagawa_ocr_finalize.toml"
DEFAULT_COMPARE_ROOT = ROOT / "dictionary" / "output" / "nakagawa-ocr-compare"
DEFAULT_FINAL_ROOT = ROOT / "dictionary" / "output" / "nakagawa-ocr-final"
DEFAULT_REVIEW_ROOT = ROOT / "dictionary" / "output" / "nakagawa-ocr-review"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Finalize one OCR output per page after automatic comparison and optional human overrides."
    )
    parser.add_argument("--config")
    parser.add_argument("--compare-dir")
    parser.add_argument("--output-dir")
    parser.add_argument("--overrides")
    parser.add_argument("--review-dir")
    parser.add_argument(
        "--allow-unresolved-fallback",
        action="store_true",
        help="Finalize unresolved pages using the compare suggestion if present",
    )
    return parser.parse_args()


def read_overrides(path: Path | None) -> dict[int, dict[str, str]]:
    if path is None or not path.exists():
        return {}
    overrides: dict[int, dict[str, str]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            page_value = row.get("page", "").strip()
            if not page_value:
                continue
            overrides[int(page_value)] = {
                "selected_model_id": row.get("selected_model_id", "").strip(),
                "custom_text_path": row.get("custom_text_path", "").strip(),
                "comment": row.get("comment", "").strip(),
            }
    return overrides


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def review_file_is_modified(review_dir: Path) -> bool:
    final_path = review_dir / "final.txt"
    review_state_path = review_dir / "review_state.json"
    if not final_path.exists() or not review_state_path.exists():
        return False
    payload = json.loads(review_state_path.read_text(encoding="utf-8"))
    seed_source_path = Path(payload["seed_source_path"])
    if not seed_source_path.exists():
        return True
    return file_sha256(final_path) != file_sha256(seed_source_path)


def build_paths(args: argparse.Namespace) -> tuple[Path, Path, Path | None, Path, bool]:
    config_path = Path(args.config) if args.config is not None else DEFAULT_CONFIG_PATH
    file_config = read_config_section(config_path, "finalize")
    compare_root = resolve_output_root(
        str(config_value(args.compare_dir, file_config.get("compare_dir"), str(DEFAULT_COMPARE_ROOT))),
        DEFAULT_COMPARE_ROOT,
    )
    output_root = resolve_output_root(
        str(config_value(args.output_dir, file_config.get("output_dir"), str(DEFAULT_FINAL_ROOT))),
        DEFAULT_FINAL_ROOT,
    )
    overrides_value = config_value(args.overrides, file_config.get("overrides_path"), None)
    overrides_path = resolve_output_root(str(overrides_value), DEFAULT_COMPARE_ROOT) if overrides_value else None
    review_root = resolve_output_root(
        str(config_value(args.review_dir, file_config.get("review_dir"), str(DEFAULT_REVIEW_ROOT))),
        DEFAULT_REVIEW_ROOT,
    )
    allow_unresolved_fallback = bool(
        config_value(args.allow_unresolved_fallback, file_config.get("allow_unresolved_fallback"), False)
    )
    return compare_root, output_root, overrides_path, review_root, allow_unresolved_fallback


def main() -> None:
    compare_root, output_root, overrides_path, review_root, allow_unresolved_fallback = build_paths(parse_args())
    decision_paths = sorted(compare_root.glob("page-*/decision.json"))
    if not decision_paths:
        raise FileNotFoundError(f"No comparison decisions found in {compare_root}")

    overrides = read_overrides(overrides_path)
    unresolved_pages: list[int] = []
    index_rows: list[dict[str, object]] = []
    output_root.mkdir(parents=True, exist_ok=True)

    for decision_path in decision_paths:
        payload = json.loads(decision_path.read_text(encoding="utf-8"))
        page = int(payload["page"])
        override = overrides.get(page, {})
        selected_model_id = payload.get("selected_model_id", "")
        selected_output_path = payload.get("selected_output_path", "")
        source_method = str(payload.get("method", ""))
        source_note = str(payload.get("note", ""))
        review_required = bool(payload.get("review_required", False))

        custom_text_path = override.get("custom_text_path", "")
        override_model_id = override.get("selected_model_id", "")
        final_text_path: Path | None = None
        resolution = source_method
        review_final_path = review_root / f"page-{page:03d}" / "final.txt"
        review_page_dir = review_root / f"page-{page:03d}"

        if review_final_path.exists() and review_file_is_modified(review_page_dir):
            final_text_path = review_final_path
            selected_model_id = "review_final"
            resolution = "review_workspace_final"
            review_required = False
        elif custom_text_path:
            final_text_path = Path(custom_text_path)
            if not final_text_path.is_absolute():
                final_text_path = ROOT / custom_text_path
            selected_model_id = "custom"
            resolution = "manual_custom_text"
            review_required = False
        elif override_model_id:
            if override_model_id == payload.get("candidate_a_model_id"):
                final_text_path = Path(payload["candidate_a_path"])
            elif override_model_id == payload.get("candidate_b_model_id"):
                final_text_path = Path(payload["candidate_b_path"])
            else:
                raise ValueError(f"Invalid override model for page {page}: {override_model_id}")
            selected_model_id = override_model_id
            resolution = "manual_model_override"
            review_required = False
        elif selected_output_path:
            final_text_path = Path(selected_output_path)
        elif allow_unresolved_fallback:
            fallback_path = payload.get("candidate_a_path") or payload.get("candidate_b_path")
            if fallback_path:
                final_text_path = Path(fallback_path)
                selected_model_id = payload.get("candidate_a_model_id", "")
                resolution = "fallback_first_candidate"
                review_required = False

        if final_text_path is None or review_required:
            unresolved_pages.append(page)
            continue
        if not final_text_path.exists():
            raise FileNotFoundError(f"Final text source missing for page {page}: {final_text_path}")

        page_dir = output_root / f"page-{page:03d}"
        page_dir.mkdir(parents=True, exist_ok=True)
        final_text = final_text_path.read_text(encoding="utf-8")
        (page_dir / "final.txt").write_text(final_text, encoding="utf-8")
        (page_dir / "final.json").write_text(
            json.dumps(
                {
                    "page": page,
                    "selected_model_id": selected_model_id,
                    "source_path": str(final_text_path),
                    "resolution": resolution,
                    "original_method": source_method,
                    "note": source_note,
                    "override_comment": override.get("comment", ""),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        index_rows.append(
            {
                "page": page,
                "selected_model_id": selected_model_id,
                "source_path": str(final_text_path),
                "resolution": resolution,
                "original_method": source_method,
                "override_comment": override.get("comment", ""),
            }
        )

    if unresolved_pages:
        (output_root / "unresolved_pages.txt").write_text(
            "\n".join(str(page) for page in unresolved_pages) + "\n",
            encoding="utf-8",
        )
        raise RuntimeError(
            "Cannot finalize all pages yet. Resolve the pages listed in "
            f"{output_root / 'unresolved_pages.txt'} via review workspace edits or manual overrides."
        )

    (output_root / "final_index.json").write_text(
        json.dumps(index_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (output_root / "final_index.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["page", "selected_model_id", "source_path", "resolution", "original_method", "override_comment"],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(index_rows)
    print(f"Wrote final OCR outputs to {output_root}")


if __name__ == "__main__":
    main()
