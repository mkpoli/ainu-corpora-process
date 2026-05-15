"""Convert the companion paper's ``refs.yml`` to structured JSON for the web UI.

The morpheme database tags each entry with a ``sources`` list using Hayagriva
citation keys (e.g. ``佐藤2023アイヌ語の動詞の結合価と3項動詞``). The keys
come from ``ainu-morpheme-database/report/refs.yml`` (Hayagriva format used
by Typst). This script reads that YAML and emits a flat JSON file that the
SvelteKit app can bundle and render as a bibliography page.

Output schema (``references.json``)::

    {
        "<key>": {
            "key": "<key>",
            "type": "book"|"article"|"misc"|...,
            "title": "...",
            "author": "..." | ["...", "..."],
            "date": "2024" | "2024-10" | "2024-10-15",
            "publisher": "...",
            "journal": "...",
            "volume": "...",
            "issue": "...",
            "page_range": "...",
            "url": "...",
            "doi": "...",
            "isbn": "..."
        },
        ...
    }

Run with::

    uv run python -m morpheme_db.export_references \\
        --input  ../ainu-morpheme-database/report/refs.yml \\
        --output web/src/lib/data/references.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO_ROOT.parent / "ainu-morpheme-database" / "report" / "refs.yml"
DEFAULT_OUTPUT = REPO_ROOT / "web" / "src" / "lib" / "data" / "references.json"


def _normalise_author(value: Any) -> str | list[str]:
    if isinstance(value, list):
        return [str(v) for v in value if v]
    if value is None:
        return ""
    return str(value)


def _flatten_serial(entry: dict[str, Any], out: dict[str, Any]) -> None:
    serial = entry.get("serial-number")
    if not isinstance(serial, dict):
        return
    for key, value in serial.items():
        normalised = key.lower().replace("-", "_")
        out[normalised] = str(value)


def _maybe(d: dict[str, Any], key: str) -> str:
    value = d.get(key)
    if value is None:
        return ""
    return str(value)


def convert(refs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for key, raw in refs.items():
        if not isinstance(raw, dict):
            continue
        entry: dict[str, Any] = {
            "key": key,
            "type": _maybe(raw, "type").lower(),
            "title": _maybe(raw, "title"),
            "author": _normalise_author(raw.get("author")),
            "date": _maybe(raw, "date"),
            "publisher": _maybe(raw, "publisher"),
            "journal": _maybe(raw, "journal"),
            "volume": _maybe(raw, "volume"),
            "issue": _maybe(raw, "number") or _maybe(raw, "issue"),
            "page_range": _maybe(raw, "page-range"),
            "url": _maybe(raw, "url"),
            "language": _maybe(raw, "language"),
        }
        # parent block (some Hayagriva entries nest journal info under parent)
        parent = raw.get("parent")
        if isinstance(parent, dict):
            if not entry["journal"]:
                entry["journal"] = _maybe(parent, "title")
            if not entry["volume"]:
                entry["volume"] = _maybe(parent, "volume")
        _flatten_serial(raw, entry)

        # Strip empty fields so the JSON is compact.
        entry = {k: v for k, v in entry.items() if v not in ("", None, [], {})}
        out[key] = entry
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"refs.yml not found at {args.input}; skipping bibliography export.")
        return 0

    with args.input.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"expected a top-level mapping in {args.input}")

    refs = convert(raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(refs, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(refs)} references → {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
