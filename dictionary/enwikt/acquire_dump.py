"""Download, decompress, and extract the English Wiktionary dump.

Outputs
-------
- Large artifacts (``.bz2`` and ``.xml``) go to ``AINU_LARGE_DATA_DIR`` (see
  ``.env.example``). On WSL, point this at a Windows mount such as
  ``/mnt/m/Workspace/Ainu`` to keep the Linux VHD small.
- The small Ainu-only JSON (~few MB) goes to
  ``dictionary/output/wiktionary_ainu_entries_en.json`` in the repo.

Usage
-----
    uv run python -m dictionary.enwikt.acquire_dump

Re-running is safe: completed steps are skipped based on file presence.
Use ``--force-download`` / ``--force-decompress`` / ``--force-extract`` to
redo a specific step. Pass ``--delete-xml`` if you want the decompressed XML
removed after extraction.
after extraction (default is to remove it to free space).
"""

from __future__ import annotations

import argparse
import bz2
import shutil
import sys
import urllib.request
from pathlib import Path

import wiktionary_dump_extractor

from dictionary.enwikt.paths import (
    DUMP_FILENAME_BZ2,
    DUMP_FILENAME_XML,
    DUMP_URL,
    RAW_ENTRIES_JSON_NAME,
    WIKTIONARY_DUMPS_SUBDIR,
    large_data_subdir,
    small_output_dir,
)


def _human(nbytes: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if nbytes < 1024 or unit == "TiB":
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024  # type: ignore[assignment]
    return f"{nbytes} B"


def _remote_size(url: str) -> int | None:
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            size = resp.headers.get("Content-Length")
            return int(size) if size is not None else None
    except Exception as exc:  # pragma: no cover - network dependent
        print(f"HEAD request failed: {exc}", file=sys.stderr)
        return None


def download_dump(dest: Path, *, force: bool) -> None:
    expected = _remote_size(DUMP_URL)
    if dest.exists() and not force:
        have = dest.stat().st_size
        if expected is None:
            print(f"Found existing dump at {dest} ({_human(have)}); skipping download.")
            return
        if have == expected:
            print(f"Dump already complete ({_human(have)}); skipping download.")
            return
        print(
            f"Resuming download: {_human(have)} / {_human(expected)} at {dest}",
            flush=True,
        )
    else:
        print(f"Downloading {DUMP_URL} -> {dest}", flush=True)

    # curl handles resume (-C -) robustly and shows progress on a TTY.
    import subprocess

    cmd = [
        "curl",
        "-L",
        "--fail",
        "--retry",
        "5",
        "--retry-connrefused",
        "--continue-at",
        "-",
        "-o",
        str(dest),
        DUMP_URL,
    ]
    subprocess.run(cmd, check=True)


def decompress_dump(src_bz2: Path, dst_xml: Path, *, force: bool) -> None:
    if dst_xml.exists() and not force:
        print(f"Decompressed XML already present at {dst_xml}; skipping.")
        return
    print(
        f"Decompressing {src_bz2.name} -> {dst_xml.name} (this is slow; ~10 GiB)",
        flush=True,
    )
    # Stream-decompress without loading everything into RAM.
    with bz2.open(src_bz2, "rb") as src, open(dst_xml, "wb") as dst:
        shutil.copyfileobj(src, dst, length=8 * 1024 * 1024)


def extract_ainu(xml_path: Path, json_out: Path, *, force: bool) -> None:
    if json_out.exists() and not force:
        print(f"Ainu JSON already present at {json_out}; skipping extraction.")
        return
    print(f"Extracting Ainu entries -> {json_out}", flush=True)
    wiktionary_dump_extractor.extract_ainu_entries_en(str(xml_path), str(json_out))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument("--force-decompress", action="store_true")
    parser.add_argument("--force-extract", action="store_true")
    parser.add_argument(
        "--delete-xml",
        action="store_true",
        help="Delete the decompressed XML after extraction (default: keep).",
    )
    args = parser.parse_args()

    data_dir = large_data_subdir(WIKTIONARY_DUMPS_SUBDIR)
    bz2_path = data_dir / DUMP_FILENAME_BZ2
    xml_path = data_dir / DUMP_FILENAME_XML
    json_out = small_output_dir() / RAW_ENTRIES_JSON_NAME

    print(f"Large data dir: {data_dir}")
    print(f"Output JSON:    {json_out}")

    download_dump(bz2_path, force=args.force_download)
    decompress_dump(bz2_path, xml_path, force=args.force_decompress)
    extract_ainu(xml_path, json_out, force=args.force_extract)

    if args.delete_xml and xml_path.exists():
        print(f"Removing decompressed XML to free space: {xml_path}")
        xml_path.unlink()

    size = json_out.stat().st_size
    print(f"Done. {json_out} ({_human(size)})")


if __name__ == "__main__":
    main()
