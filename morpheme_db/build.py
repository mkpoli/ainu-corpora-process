"""Build the unified Ainu morpheme database.

Default flow:

1. Load curated entries from ``morpheme_db/seed/morphemes.json``.
2. If a NINJAL morpheme lexicon TSV is available at
   ``corpus/output/ninjal/lexicon/ninjal_morpheme_lexicon.tsv``, load it and
   merge it with the curated set (curated values win on conflict).
3. Write the merged database to ``morpheme_db/output/morpheme_database.json``
   and a flat ``morpheme_database.tsv`` for spreadsheet review.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from morpheme_db.ingest_ninjal import ingest_ninjal_lexicon, merge_with_seed
from morpheme_db.ingest_wiktionary import enrich_with_wiktionary, load_json_dict
from morpheme_db.schema import Entry, load_entries, save_entries

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = REPO_ROOT / "morpheme_db" / "seed" / "morphemes.json"
NINJAL_LEXICON_PATH = (
    REPO_ROOT / "corpus" / "output" / "ninjal" / "lexicon" / "ninjal_morpheme_lexicon.tsv"
)
WIKT_JA_GLOSS_PATH = REPO_ROOT / "dictionary" / "output" / "wiktionary_ainu_glosses.json"
WIKT_EN_GLOSS_PATH = REPO_ROOT / "dictionary" / "output" / "wiktionary_ainu_glosses_en.json"
WIKT_JA_POS_PATH = REPO_ROOT / "dictionary" / "output" / "wiktionary_ainu_part_of_speech.json"
OUTPUT_DIR = REPO_ROOT / "morpheme_db" / "output"


def _format_frame(entry: Entry) -> str:
    if entry.base_frame is None:
        return ""
    parts = [f"{s.role}:{s.realization.value}" for s in entry.base_frame.slots]
    return ", ".join(parts)


def _format_rules(entry: Entry) -> str:
    parts = []
    for rule in entry.rules:
        chunk = rule.operation
        if rule.role:
            chunk += f"({rule.role}"
            if rule.realization.value != "external":
                chunk += f"→{rule.realization.value}"
            chunk += ")"
        parts.append(chunk)
    return "; ".join(parts)


def write_tsv(entries: list[Entry], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(
            [
                "id",
                "lemma",
                "category",
                "bound",
                "morph_type",
                "arity",
                "base_frame",
                "rules",
                "primary_gloss_en",
                "primary_gloss_jp",
                "frequency",
                "verified",
                "sources",
                "notes",
            ]
        )
        for entry in entries:
            writer.writerow(
                [
                    entry.id,
                    entry.lemma,
                    entry.category,
                    "1" if entry.bound else "0",
                    entry.morph_type,
                    entry.base_frame.arity if entry.base_frame else "",
                    _format_frame(entry),
                    _format_rules(entry),
                    entry.glosses_en[0] if entry.glosses_en else "",
                    entry.glosses_jp[0] if entry.glosses_jp else "",
                    entry.frequency,
                    "1" if entry.verified else "0",
                    "|".join(entry.sources),
                    entry.notes.replace("\n", " "),
                ]
            )


def build(
    seed_path: Path = SEED_PATH,
    ninjal_path: Path | None = NINJAL_LEXICON_PATH,
    wikt_ja_gloss_path: Path | None = WIKT_JA_GLOSS_PATH,
    wikt_en_gloss_path: Path | None = WIKT_EN_GLOSS_PATH,
    wikt_ja_pos_path: Path | None = WIKT_JA_POS_PATH,
    output_dir: Path = OUTPUT_DIR,
) -> list[Entry]:
    seed = load_entries(seed_path)
    entries = list(seed)
    if ninjal_path is not None and ninjal_path.exists():
        ninjal = ingest_ninjal_lexicon(ninjal_path)
        entries = merge_with_seed(seed, ninjal)

    ja_glosses = load_json_dict(wikt_ja_gloss_path) if wikt_ja_gloss_path and wikt_ja_gloss_path.exists() else {}
    en_glosses = load_json_dict(wikt_en_gloss_path) if wikt_en_gloss_path and wikt_en_gloss_path.exists() else {}
    ja_pos = load_json_dict(wikt_ja_pos_path) if wikt_ja_pos_path and wikt_ja_pos_path.exists() else {}
    if ja_glosses or en_glosses or ja_pos:
        enrich_with_wiktionary(entries, ja_glosses, en_glosses, ja_pos)

    save_entries(entries, output_dir / "morpheme_database.json")
    write_tsv(entries, output_dir / "morpheme_database.tsv")
    return entries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Ainu morpheme database.")
    parser.add_argument("--seed", type=Path, default=SEED_PATH, help="Curated seed JSON.")
    parser.add_argument(
        "--ninjal",
        type=Path,
        default=NINJAL_LEXICON_PATH,
        help="NINJAL morpheme lexicon TSV (optional).",
    )
    parser.add_argument(
        "--no-ninjal",
        action="store_true",
        help="Skip the NINJAL ingest even when the lexicon TSV is present.",
    )
    parser.add_argument(
        "--wikt-ja",
        type=Path,
        default=WIKT_JA_GLOSS_PATH,
        help="Wiktionary JA glosses JSON (optional).",
    )
    parser.add_argument(
        "--wikt-en",
        type=Path,
        default=WIKT_EN_GLOSS_PATH,
        help="Wiktionary EN glosses JSON (optional).",
    )
    parser.add_argument(
        "--wikt-ja-pos",
        type=Path,
        default=WIKT_JA_POS_PATH,
        help="Wiktionary JA part-of-speech JSON (optional).",
    )
    parser.add_argument(
        "--no-wiktionary",
        action="store_true",
        help="Skip Wiktionary enrichment.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Output directory.",
    )
    args = parser.parse_args(argv)

    ninjal_path = None if args.no_ninjal else args.ninjal
    wikt_ja = None if args.no_wiktionary else args.wikt_ja
    wikt_en = None if args.no_wiktionary else args.wikt_en
    wikt_pos = None if args.no_wiktionary else args.wikt_ja_pos
    entries = build(
        seed_path=args.seed,
        ninjal_path=ninjal_path,
        wikt_ja_gloss_path=wikt_ja,
        wikt_en_gloss_path=wikt_en,
        wikt_ja_pos_path=wikt_pos,
        output_dir=args.output_dir,
    )

    verified = sum(1 for e in entries if e.verified)
    with_category = sum(1 for e in entries if e.category)
    with_frame = sum(1 for e in entries if e.base_frame is not None)
    print(
        f"Wrote {len(entries)} entries to {args.output_dir} "
        f"({verified} curated, {len(entries) - verified} unverified; "
        f"{with_category} with category, {with_frame} with valency frame)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
