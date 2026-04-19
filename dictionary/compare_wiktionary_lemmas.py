from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from dictionary.enwikt.paths import small_output_dir


OUTPUT_DIR = small_output_dir()
JA_GLOSSES_PATH = OUTPUT_DIR / "wiktionary_ainu_glosses.json"
EN_GLOSSES_PATH = OUTPUT_DIR / "wiktionary_ainu_glosses_en.json"


@dataclass(frozen=True)
class EntryView:
    lemma: str
    pos: str
    glosses: tuple[str, ...]
    lemma_original: str | None = None


def load_entries(path: Path, *, english: bool) -> dict[str, list[EntryView]]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    grouped: dict[str, list[EntryView]] = defaultdict(list)
    for key, data in raw.items():
        lemma = data.get("lemma", key)
        pos = data.get("pos", "")
        glosses = tuple(data.get("glosses", []))
        lemma_original = data.get("lemma_original") if english else None
        grouped[lemma].append(
            EntryView(
                lemma=lemma,
                pos=pos,
                glosses=glosses,
                lemma_original=lemma_original,
            )
        )

    return dict(grouped)


def format_entry(entry: EntryView, *, english: bool) -> str:
    parts = [f"pos={entry.pos or '-'}"]
    if english and entry.lemma_original and entry.lemma_original != entry.lemma:
        parts.append(f"original={entry.lemma_original}")

    gloss_label = "translation" if english else "definition"
    gloss_text = "; ".join(entry.glosses) if entry.glosses else "-"
    parts.append(f"{gloss_label}={gloss_text}")
    return ", ".join(parts)


def print_section(
    title: str,
    lemmas: list[str],
    entries: dict[str, list[EntryView]],
    *,
    english: bool,
    limit: int | None,
) -> None:
    shown = lemmas if limit is None else lemmas[:limit]
    print(f"## {title}: {len(lemmas)}")
    for lemma in shown:
        print(f"- {lemma}")
        for entry in sorted(
            entries[lemma],
            key=lambda item: (item.pos, item.lemma_original or item.lemma),
        ):
            print(f"  - {format_entry(entry, english=english)}")
    if limit is not None and len(lemmas) > limit:
        print(f"... {len(lemmas) - limit} more")
    print()


def print_overlap_section(
    lemmas: list[str],
    ja_entries: dict[str, list[EntryView]],
    en_entries: dict[str, list[EntryView]],
    *,
    limit: int | None,
) -> None:
    shown = lemmas if limit is None else lemmas[:limit]
    print(f"## In Both Japanese And English: {len(lemmas)}")
    for lemma in shown:
        print(f"- {lemma}")
        for entry in sorted(ja_entries[lemma], key=lambda item: (item.pos, item.lemma)):
            print(f"  - ja: {format_entry(entry, english=False)}")
        for entry in sorted(
            en_entries[lemma],
            key=lambda item: (item.pos, item.lemma_original or item.lemma),
        ):
            print(f"  - en: {format_entry(entry, english=True)}")
    if limit is not None and len(lemmas) > limit:
        print(f"... {len(lemmas) - limit} more")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare Japanese and English Wiktionary Ainu lemmas."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum lemmas to show per section (default: 50). Use 0 for all.",
    )
    parser.add_argument(
        "--view",
        choices=["all", "both", "ja-only", "en-only", "a-b", "b-a", "axb"],
        default="all",
        help=(
            "Which set to print: all, both/axb, ja-only/a-b, or en-only/b-a "
            "(A=Japanese, B=English)."
        ),
    )
    args = parser.parse_args()

    limit = None if args.limit == 0 else args.limit

    ja_entries = load_entries(JA_GLOSSES_PATH, english=False)
    en_entries = load_entries(EN_GLOSSES_PATH, english=True)

    ja_only = sorted(set(ja_entries) - set(en_entries))
    en_only = sorted(set(en_entries) - set(ja_entries))
    both = sorted(set(ja_entries) & set(en_entries))

    print(f"Japanese lemmas: {len(ja_entries)}")
    print(f"English lemmas: {len(en_entries)}")
    print(f"Overlap: {len(both)}")
    print()

    view = args.view
    if view in {"all", "both", "axb"}:
        print_overlap_section(both, ja_entries, en_entries, limit=limit)
    if view in {"all", "ja-only", "a-b"}:
        print_section(
            "In Japanese But Not English",
            ja_only,
            ja_entries,
            english=False,
            limit=limit,
        )
    if view in {"all", "en-only", "b-a"}:
        print_section(
            "In English But Not Japanese",
            en_only,
            en_entries,
            english=True,
            limit=limit,
        )


if __name__ == "__main__":
    main()
