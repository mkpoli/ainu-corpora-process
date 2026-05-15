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

from morpheme_db.ingest_ff_ainu import enrich_with_ff_ainu, load_ff_ainu_pos
from morpheme_db.ingest_ninjal import ingest_ninjal_lexicon, merge_with_seed
from morpheme_db.ingest_wiktionary import enrich_with_wiktionary, load_json_dict
from morpheme_db.ingest_tommy1949 import (
    ingest_tommy1949,
    load_decomposed as load_tommy_decomposed,
    load_glosses as load_tommy_glosses,
)
from morpheme_db.ingest_wiktionary_compositions import (
    ingest_wiktionary_compositions,
    load_compositions,
)
from morpheme_db.ingest_translations import apply_translations, load_translations
from morpheme_db.ingest_corpora_frequency import (
    apply_corpora_frequencies,
    load_frequency_table,
)
from morpheme_db.schema import Entry, load_entries, save_entries

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = REPO_ROOT / "morpheme_db" / "seed" / "morphemes.json"
NINJAL_LEXICON_PATH = (
    REPO_ROOT / "corpus" / "output" / "ninjal" / "lexicon" / "ninjal_morpheme_lexicon.tsv"
)
WIKT_JA_GLOSS_PATH = REPO_ROOT / "dictionary" / "output" / "wiktionary_ainu_glosses.json"
WIKT_EN_GLOSS_PATH = REPO_ROOT / "dictionary" / "output" / "wiktionary_ainu_glosses_en.json"
WIKT_JA_POS_PATH = REPO_ROOT / "dictionary" / "output" / "wiktionary_ainu_part_of_speech.json"
FF_AINU_SARU_PATH = REPO_ROOT / "dictionary" / "output" / "ff-ainu-saru-terms.json"
WIKT_COMPOSITIONS_PATH = (
    REPO_ROOT / "dictionary" / "output" / "wiktionary_ainu_word_compositions.json"
)
TRANSLATIONS_PATH = REPO_ROOT / "morpheme_db" / "seed" / "translations.json"
CORPORA_TOKEN_FREQ_PATH = (
    REPO_ROOT / "corpus" / "output" / "ainu_corpora" / "token_frequency.tsv"
)
CORPORA_LEMMA_FREQ_PATH = (
    REPO_ROOT / "corpus" / "output" / "ainu_corpora" / "lemma_frequency.tsv"
)
TOMMY_DECOMP_PATH = REPO_ROOT / "dictionary" / "output" / "tommy1949_decomposed_words.json"
TOMMY_GLOSS_PATH = REPO_ROOT / "dictionary" / "output" / "tommy1949_aynudictionary_glosses.json"
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
    wikt_compositions_path: Path | None = WIKT_COMPOSITIONS_PATH,
    tommy_decomp_path: Path | None = TOMMY_DECOMP_PATH,
    tommy_gloss_path: Path | None = TOMMY_GLOSS_PATH,
    translations_path: Path | None = TRANSLATIONS_PATH,
    corpora_token_freq_path: Path | None = CORPORA_TOKEN_FREQ_PATH,
    corpora_lemma_freq_path: Path | None = CORPORA_LEMMA_FREQ_PATH,
    ff_ainu_saru_path: Path | None = FF_AINU_SARU_PATH,
    output_dir: Path = OUTPUT_DIR,
) -> tuple[list[Entry], dict[str, int]]:
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

    ff_ainu_pos = (
        load_ff_ainu_pos(ff_ainu_saru_path)
        if ff_ainu_saru_path and ff_ainu_saru_path.exists()
        else {}
    )
    if ff_ainu_pos:
        ff_counters = enrich_with_ff_ainu(entries, ff_ainu_pos)
    else:
        ff_counters = {"categories_set": 0, "categories_upgraded": 0, "alts_added": 0}

    counters = {
        "wikt_compositions_attached": 0,
        "wikt_compositions_skipped": 0,
        "tommy_compositions_attached": 0,
        "tommy_compositions_skipped": 0,
        "tommy_new_entries": 0,
        "tommy_glosses_added": 0,
        "translations_en_added": 0,
        "translations_jp_added": 0,
        "translations_lemmas_not_found": 0,
        "corpora_freq_matched_token": 0,
        "corpora_freq_matched_lemma": 0,
        "corpora_freq_unmatched": 0,
        "corpora_freq_replaced": 0,
        "corpora_freq_kept_existing": 0,
        "ff_ainu_categories_set": ff_counters["categories_set"],
        "ff_ainu_categories_upgraded": ff_counters["categories_upgraded"],
        "ff_ainu_alts_added": ff_counters["alts_added"],
    }
    if wikt_compositions_path and wikt_compositions_path.exists():
        comps = load_compositions(wikt_compositions_path)
        entries, attached, skipped = ingest_wiktionary_compositions(entries, comps)
        counters["wikt_compositions_attached"] = attached
        counters["wikt_compositions_skipped"] = skipped

    if tommy_decomp_path and tommy_decomp_path.exists():
        decomp = load_tommy_decomposed(tommy_decomp_path)
        tommy_gl = (
            load_tommy_glosses(tommy_gloss_path)
            if tommy_gloss_path and tommy_gloss_path.exists()
            else {}
        )
        entries, tc = ingest_tommy1949(entries, decomp, tommy_gl)
        counters["tommy_compositions_attached"] = tc["compositions_attached"]
        counters["tommy_compositions_skipped"] = tc["compositions_skipped"]
        counters["tommy_new_entries"] = tc["new_entries"]
        counters["tommy_glosses_added"] = tc["glosses_added"]

    # Re-run Wiktionary enrichment so entries created by the composition
    # ingests (Wiktionary compositions, Tommy 1949) also pick up Wiktionary
    # JA/EN glosses for their lemma.
    if ja_glosses or en_glosses or ja_pos:
        enrich_with_wiktionary(entries, ja_glosses, en_glosses, ja_pos)

    # Re-run FF Ainu enrichment for the same reason — newly-created entries
    # from the composition ingests need their categories upgraded too.
    if ff_ainu_pos:
        ff_counters2 = enrich_with_ff_ainu(entries, ff_ainu_pos)
        counters["ff_ainu_categories_set"] += ff_counters2["categories_set"]
        counters["ff_ainu_categories_upgraded"] += ff_counters2["categories_upgraded"]
        counters["ff_ainu_alts_added"] += ff_counters2["alts_added"]

    if translations_path and translations_path.exists():
        translations = load_translations(translations_path)
        tcounters = apply_translations(entries, translations)
        counters["translations_en_added"] = tcounters["en_added"]
        counters["translations_jp_added"] = tcounters["jp_added"]
        counters["translations_lemmas_not_found"] = tcounters["lemmas_not_found"]

    if corpora_token_freq_path and corpora_token_freq_path.exists():
        token_freq = load_frequency_table(corpora_token_freq_path)
        lemma_freq = (
            load_frequency_table(corpora_lemma_freq_path)
            if corpora_lemma_freq_path and corpora_lemma_freq_path.exists()
            else {}
        )
        fcounters = apply_corpora_frequencies(entries, token_freq, lemma_freq)
        counters["corpora_freq_matched_token"] = fcounters["matched_token"]
        counters["corpora_freq_matched_lemma"] = fcounters["matched_lemma"]
        counters["corpora_freq_unmatched"] = fcounters["unmatched"]
        counters["corpora_freq_replaced"] = fcounters["replaced"]
        counters["corpora_freq_kept_existing"] = fcounters["kept_existing"]

    save_entries(entries, output_dir / "morpheme_database.json")
    write_tsv(entries, output_dir / "morpheme_database.tsv")
    return entries, counters


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
        "--wikt-compositions",
        type=Path,
        default=WIKT_COMPOSITIONS_PATH,
        help="Wiktionary word-composition JSON (optional).",
    )
    parser.add_argument(
        "--no-wiktionary",
        action="store_true",
        help="Skip Wiktionary enrichment.",
    )
    parser.add_argument(
        "--tommy-decomp",
        type=Path,
        default=TOMMY_DECOMP_PATH,
        help="Tommy 1949 decomposed-words JSON (optional).",
    )
    parser.add_argument(
        "--tommy-gloss",
        type=Path,
        default=TOMMY_GLOSS_PATH,
        help="Tommy 1949 gloss JSON (optional).",
    )
    parser.add_argument(
        "--no-tommy",
        action="store_true",
        help="Skip Tommy 1949 enrichment.",
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
    wikt_comps = None if args.no_wiktionary else args.wikt_compositions
    tommy_decomp = None if args.no_tommy else args.tommy_decomp
    tommy_gloss = None if args.no_tommy else args.tommy_gloss
    entries, counters = build(
        seed_path=args.seed,
        ninjal_path=ninjal_path,
        wikt_ja_gloss_path=wikt_ja,
        wikt_en_gloss_path=wikt_en,
        wikt_ja_pos_path=wikt_pos,
        wikt_compositions_path=wikt_comps,
        tommy_decomp_path=tommy_decomp,
        tommy_gloss_path=tommy_gloss,
        output_dir=args.output_dir,
    )

    verified = sum(1 for e in entries if e.verified)
    with_category = sum(1 for e in entries if e.category)
    with_frame = sum(1 for e in entries if e.base_frame is not None)
    with_composition = sum(1 for e in entries if e.composition)
    print(
        f"Wrote {len(entries)} entries to {args.output_dir} "
        f"({verified} curated, {len(entries) - verified} unverified; "
        f"{with_category} with category, {with_frame} with valency frame, "
        f"{with_composition} with composition).\n"
        f"  Wiktionary compositions: attached={counters['wikt_compositions_attached']} "
        f"skipped={counters['wikt_compositions_skipped']}\n"
        f"  Tommy 1949: attached={counters['tommy_compositions_attached']} "
        f"new={counters['tommy_new_entries']} "
        f"glosses_added={counters['tommy_glosses_added']} "
        f"skipped={counters['tommy_compositions_skipped']}\n"
        f"  Translations: en_added={counters['translations_en_added']} "
        f"jp_added={counters['translations_jp_added']} "
        f"lemmas_not_found={counters['translations_lemmas_not_found']}\n"
        f"  Corpora freq: matched_token={counters['corpora_freq_matched_token']} "
        f"matched_lemma={counters['corpora_freq_matched_lemma']} "
        f"replaced={counters['corpora_freq_replaced']} "
        f"kept_existing={counters['corpora_freq_kept_existing']} "
        f"unmatched={counters['corpora_freq_unmatched']}\n"
        f"  FF Ainu Saru POS: categories_set={counters['ff_ainu_categories_set']} "
        f"transitivity_upgraded={counters['ff_ainu_categories_upgraded']} "
        f"alts_added={counters['ff_ainu_alts_added']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
