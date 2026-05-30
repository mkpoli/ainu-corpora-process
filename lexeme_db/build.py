"""Build the lexeme bank and the dictionary crosswalk from the pilot sources.

Flow:

1. Read every pilot dictionary into :class:`SourceEntry` records.
2. Cluster records into lexemes on ``(form_key, pos)`` — the source-independent
   identity. The first source (in descriptive-priority order) to introduce a
   key *seeds* the lexeme and donates the citation form; later sources *attest*
   it. Same dialect agreeing (田村/萱野) and different dialects diverging
   (中川千歳 vs Saru) both surface as separate attestations on one lexeme.
3. Sense-split: if a contributing entry numbered its senses (①②③), copy that
   split onto the lexeme and tag each contributing attestation with the sense
   it matches by index.
4. Link each lexeme into the morpheme bank: a monomorphemic form whose key is a
   known morpheme gets ``morphemes=[that id]``; multi-morpheme decomposition is
   left for later (kept empty, not guessed).
5. Emit ``output/lexeme_bank.json`` and ``output/crosswalk.tsv``.

The crosswalk is the annotation layer the user asked for: pivot on ``lexeme_id``
to read every dialect's recording of one word.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from lexeme_db.ingest import SourceEntry, read_all
from lexeme_db.normalize import form_key, has_bound_marker
from lexeme_db.schema import Attestation, Lexeme, Sense, save_lexemes

REPO_ROOT = Path(__file__).resolve().parents[1]
MORPHEME_DB = REPO_ROOT / "morpheme_db" / "output" / "morpheme_database.json"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"

# Descriptive-priority order: which source's citation form wins when several
# attest one lexeme. Modern, well-edited Hokkaido descriptive dicts first.
_SOURCE_PRIORITY = {
    "1995_Nakagawa_Ainu-Chitose-Dialect-Dictionary": 0,
    "1996_Tamura_Ainu-Saru-Dialect-Dictionary": 1,
    "1996_Kayano_Kayanos-Ainu-Dictionary": 2,
}

_BOUND_POS = {"pfx", "sfx", "pers", "root"}


def load_morpheme_index() -> dict[str, str]:
    """Map a form key → morpheme id for monomorphemic resolution."""
    if not MORPHEME_DB.exists():
        return {}
    data = json.loads(MORPHEME_DB.read_text(encoding="utf-8"))
    index: dict[str, str] = {}
    for entry in data:
        forms = [entry.get("lemma", ""), *entry.get("allomorphs", [])]
        for form in forms:
            key = form_key(form)
            if key:
                index.setdefault(key, entry["id"])
    return index


def _priority(entry: SourceEntry) -> int:
    return _SOURCE_PRIORITY.get(entry.source, 99)


def _bucket_pos(entries: list[SourceEntry]) -> dict[str, list[SourceEntry]]:
    """Sub-group a form_key cluster by POS.

    Entries with a known POS bucket by that POS. Entries with no POS are folded
    into the unique non-empty POS bucket when there is exactly one (the common
    case: one source labelled it, another didn't); otherwise they form their
    own ``""`` bucket so we never silently merge genuine homographs.
    """
    by_pos: dict[str, list[SourceEntry]] = defaultdict(list)
    for e in entries:
        by_pos[e.pos].append(e)
    if "" in by_pos and len(by_pos) == 2:
        (other_pos,) = [p for p in by_pos if p != ""]
        by_pos[other_pos].extend(by_pos.pop(""))
    return by_pos


def _make_id(key: str, pos: str, taken: set[str]) -> str:
    base = f"{key}.{pos}" if pos else key
    if base not in taken:
        return base
    n = 2
    while f"{base}~{n}" in taken:
        n += 1
    return f"{base}~{n}"


def _match_kind(entry: SourceEntry, lemma: str, *, is_seed: bool) -> str:
    if is_seed:
        return "seed"
    if entry.latn.strip().lower() == lemma.strip().lower():
        return "exact"
    return "normalized"


def build() -> tuple[list[Lexeme], list[Attestation], dict[str, int]]:
    entries = read_all()
    morph_index = load_morpheme_index()

    by_key: dict[str, list[SourceEntry]] = defaultdict(list)
    for e in entries:
        key = form_key(e.latn)
        if key:
            by_key[key].append(e)

    lexemes: list[Lexeme] = []
    attestations: list[Attestation] = []
    taken_ids: set[str] = set()
    counters = {
        "source_entries": len(entries),
        "lexemes": 0,
        "attestations": 0,
        "sense_split": 0,
        "morpheme_linked": 0,
        "multi_dialect": 0,
    }

    for key, group in sorted(by_key.items()):
        for pos, bucket in _bucket_pos(group).items():
            bucket.sort(key=_priority)
            seed = bucket[0]
            lex_id = _make_id(key, pos, taken_ids)
            taken_ids.add(lex_id)

            # Sense split: take the richest split among contributors.
            best_senses = max((e.senses for e in bucket), key=len, default=[])
            senses = (
                [Sense(id=sid, gloss_jp=[g]) for sid, g in best_senses]
                if len(best_senses) >= 2
                else []
            )

            bound = bool(pos in _BOUND_POS or has_bound_marker(seed.latn))
            morphemes: list[str] = []
            mid = morph_index.get(key)
            if mid:
                morphemes = [mid]
                counters["morpheme_linked"] += 1

            gloss_jp: list[str] = []
            for e in bucket:
                for g in e.gloss_jp:
                    if g and g not in gloss_jp:
                        gloss_jp.append(g)

            lex = Lexeme(
                id=lex_id,
                lemma=seed.latn,
                kana=seed.kana,
                pos=pos,
                gloss_jp=gloss_jp[:6],
                bound=bound,
                dialect_base=seed.dialect,
                morphemes=morphemes,
                senses=senses,
                sources=sorted({e.source for e in bucket}),
            )
            lexemes.append(lex)
            if senses:
                counters["sense_split"] += 1
            if len({e.dialect for e in bucket}) > 1:
                counters["multi_dialect"] += 1

            for idx, e in enumerate(bucket):
                sense_id = ""
                if senses and e.senses and len(e.senses) == len(senses):
                    sense_id = e.senses[0][0]  # aligned-index split
                same_form = e.latn.strip().lower() == seed.latn.strip().lower()
                attestations.append(
                    Attestation(
                        lexeme_id=lex_id,
                        source=e.source,
                        dialect=e.dialect,
                        entry_ref=e.entry_ref,
                        surface_latn=e.latn,
                        surface_kana=e.kana,
                        pos_raw=e.pos_raw,
                        gloss_raw=e.definition,
                        sense_id=sense_id,
                        match_kind=_match_kind(e, seed.latn, is_seed=(idx == 0)),
                        confidence=1.0 if (idx == 0 or same_form) else 0.9,
                    )
                )

    counters["lexemes"] = len(lexemes)
    counters["attestations"] = len(attestations)
    return lexemes, attestations, counters


def write_crosswalk(attestations: list[Attestation], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerow(Attestation.HEADER)
        for att in attestations:
            writer.writerow(att.to_row())


def main() -> int:
    lexemes, attestations, counters = build()
    save_lexemes(lexemes, OUTPUT_DIR / "lexeme_bank.json")
    write_crosswalk(attestations, OUTPUT_DIR / "crosswalk.tsv")
    print(
        f"Built lexeme bank: {counters['lexemes']} lexemes from "
        f"{counters['source_entries']} source entries.\n"
        f"  crosswalk attestations : {counters['attestations']}\n"
        f"  multi-dialect lexemes   : {counters['multi_dialect']} "
        f"(attested in >1 dialect)\n"
        f"  sense-split lexemes     : {counters['sense_split']}\n"
        f"  morpheme-linked lexemes : {counters['morpheme_linked']}\n"
        f"  -> {OUTPUT_DIR / 'lexeme_bank.json'}\n"
        f"  -> {OUTPUT_DIR / 'crosswalk.tsv'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
