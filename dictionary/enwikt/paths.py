"""Shared filesystem paths for the English Wiktionary pipeline.

Multi-GB artifacts (compressed dumps, decompressed XML, audio corpora,
OCR scratch, etc.) live under ``AINU_LARGE_DATA_DIR`` when set - useful on
WSL where pointing it at ``/mnt/<drive>/...`` avoids bloating the Linux
VHD. Each pipeline uses its own subdirectory under that root. Small
outputs stay in the repo under ``dictionary/output/``.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_env() -> None:
    load_dotenv(REPO_ROOT / ".env")


def large_data_root() -> Path:
    """Return the shared root for all large artifacts.

    Falls back to ``<repo>/dictionary/output/_large`` when the env var is
    not set. The directory is created on demand.
    """
    _load_env()
    raw = os.environ.get("AINU_LARGE_DATA_DIR", "").strip()
    root = Path(raw) if raw else REPO_ROOT / "dictionary" / "output" / "_large"
    root.mkdir(parents=True, exist_ok=True)
    return root


def large_data_subdir(name: str) -> Path:
    """Return a named subdirectory under the large-data root.

    Use one subdirectory per data source (e.g. ``wiktionary-dumps``,
    ``audio``, ``ocr-scratch``). Created on demand.
    """
    sub = large_data_root() / name
    sub.mkdir(parents=True, exist_ok=True)
    return sub


def small_output_dir() -> Path:
    """Return the repo-local directory for small JSON/TSV outputs."""
    out = REPO_ROOT / "dictionary" / "output"
    out.mkdir(parents=True, exist_ok=True)
    return out


# Canonical filenames used by the English Wiktionary pipeline.
WIKTIONARY_DUMPS_SUBDIR = "wiktionary-dumps"
DUMP_FILENAME_BZ2 = "enwiktionary-latest-pages-articles-multistream.xml.bz2"
DUMP_FILENAME_XML = "enwiktionary-latest-pages-articles-multistream.xml"
DUMP_URL = f"https://dumps.wikimedia.org/enwiktionary/latest/{DUMP_FILENAME_BZ2}"

RAW_ENTRIES_JSON_NAME = "wiktionary_ainu_entries_en.json"
FILTERED_ENTRIES_JSON_NAME = "wiktionary_ainu_entries_en_filtered.json"
GLOSSES_JSON_NAME = "wiktionary_ainu_glosses_en.json"
TSV_NAME = "wiktionary-en-entries.tsv"
