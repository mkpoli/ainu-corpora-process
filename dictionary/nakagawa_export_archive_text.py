"""Write the finalized Nakagawa page texts as one page-keyed file for the scan archive.

The archive keys text by the page's position in the scanned PDF and reads it
from a file committed beside the scan, named after it with the variant in place
of the extension, one `--- page N ---` marker per page. Pages that carry no print
keep their marker with an empty body, so the file covers the whole PDF rather
than only the pages that produced text.
"""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FINAL_ROOT = ROOT / "dictionary" / "output" / "nakagawa-ocr-final"
PDF_PAGE_COUNT = 455
DEFAULT_OUTPUT_PATH = (
    ROOT.parent
    / "ainu-dictionaries"
    / "1995_Nakagawa_Ainu-Chitose-Dialect-Dictionary"
    / "source.gpt5-gemini.txt"
)


def read_final_pages(final_root: Path) -> dict[int, str]:
    pages: dict[int, str] = {}
    for page_dir in sorted(final_root.glob("page-*")):
        page_value = page_dir.name.removeprefix("page-")
        if not page_value.isdigit():
            continue
        final_path = page_dir / "final.txt"
        if not final_path.exists():
            continue
        pages[int(page_value)] = final_path.read_text(encoding="utf-8").strip("\n")
    return pages


def render(pages: dict[int, str], page_count: int) -> str:
    lines: list[str] = []
    for page in range(1, page_count + 1):
        lines.append(f"--- page {page} ---")
        text = pages.get(page, "")
        if text:
            lines.append(text)
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export finalized Nakagawa OCR as page-keyed text for the scan archive."
    )
    parser.add_argument("--final-dir", default=str(FINAL_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--page-count", type=int, default=PDF_PAGE_COUNT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    final_root = Path(args.final_dir)
    pages = read_final_pages(final_root)
    if not pages:
        raise FileNotFoundError(f"No finalized pages found in {final_root}")
    missing = [page for page in range(1, args.page_count + 1) if page not in pages]
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render(pages, args.page_count), encoding="utf-8")
    print(f"Wrote {len(pages)} of {args.page_count} pages to {output_path}")
    if missing:
        print(f"Pages without finalized text: {compact_ranges(missing)}")


def compact_ranges(pages: list[int]) -> str:
    spans: list[str] = []
    start = previous = pages[0]
    for page in pages[1:]:
        if page == previous + 1:
            previous = page
            continue
        spans.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = page
    spans.append(str(start) if start == previous else f"{start}-{previous}")
    return ", ".join(spans)


if __name__ == "__main__":
    main()
