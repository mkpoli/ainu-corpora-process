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
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from morpheme_db.ingest_ff_ainu import enrich_with_ff_ainu, load_ff_ainu_pos
from morpheme_db.ingest_tamura import enrich_with_tamura, parse_tamura_entries
from morpheme_db.ingest_ninjal import ingest_ninjal_lexicon, merge_with_seed
from morpheme_db.ingest_wiktionary import (
    enrich_with_wiktionary,
    harvest_wiktionary_accents,
    load_json_dict,
    promote_wiktionary_bound_lemmas,
)
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
WIKT_JA_ENTRIES_PATH = REPO_ROOT / "dictionary" / "output" / "wiktionary_ainu_entries.json"
TAMURA_ENTRIES_PATH = REPO_ROOT / "dictionary" / "output" / "ainu-archive" / "tamura-entries.txt"
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


_TAMURA_ACCENT_TABLE = str.maketrans("áéíóúÁÉÍÓÚ", "aeiouAEIOU")


def _tamura_deaccent(text: str) -> str:
    return text.translate(_TAMURA_ACCENT_TABLE)


def _harvest_tamura_accents(entries: list[Entry], tamura_path: Path) -> dict[str, int]:
    """Read Tamura's TSV and register accent-marked lemmas as allomorphs.

    Tamura 1996 prints stress on Ainu citation forms — the lemma column of
    ``tamura-entries.txt`` carries forms like ``aenínuype`` for the bare
    ``aeninuype``. We treat each accented Tamura headword as an allomorph
    of the deaccented lemma when that lemma is already in the database.
    No new entries are created from this source — coverage gaps belong to
    the upstream ingests.
    """
    counters = {"tamura_accent_pairs": 0, "tamura_allomorphs_added": 0}
    if not tamura_path.exists():
        return counters

    index = _build_form_index_for_accents(entries)

    with tamura_path.open(encoding="utf-8") as handle:
        next(handle, None)  # header
        for raw in handle:
            lemma = raw.split("\t", 1)[0].strip()
            if not lemma or not any(ch in "áéíóúÁÉÍÓÚ" for ch in lemma):
                continue
            deaccented = _tamura_deaccent(lemma)
            counters["tamura_accent_pairs"] += 1
            # When the Tamura form carries an attachment marker (e.g.
            # ``tú-``), require an exact-match target — falling back to the
            # bare lemma would wrongly attach a bound prefix to a free
            # noun (``tu`` vs ``tú-``). Bare Tamura forms can still match
            # bare *or* dashed targets via the bare-strip fallback.
            has_marker = deaccented.startswith(("-", "=")) or deaccented.endswith(("-", "="))
            if has_marker:
                target = index.get(deaccented)
            else:
                target = index.get(deaccented) or index.get(deaccented.strip("-="))
            if target is None:
                continue
            if lemma == target.lemma or lemma in target.allomorphs:
                continue
            target.allomorphs.append(lemma)
            counters["tamura_allomorphs_added"] += 1
            if "田村1996アイヌ語沙流方言辞典" not in target.sources:
                target.sources.append("田村1996アイヌ語沙流方言辞典")

    return counters


def _build_form_index_for_accents(entries: list[Entry]) -> dict[str, Entry]:
    """Form index used by accent harvesters (mirrors the Wiktionary one)."""
    index: dict[str, Entry] = {}
    for entry in entries:
        forms = {entry.lemma, *entry.allomorphs}
        bare = entry.lemma.strip("-=")
        if bare:
            forms.add(bare)
        for form in forms:
            if form:
                index.setdefault(form, entry)
    return index


# Characters that flag an allomorph as a transcription artefact rather
# than a real morpheme variant — curly quotes / typographic marks and
# the uncertainty annotator ``?`` used in NINJAL's raw_morpheme_variants
# field. Comma and stray whitespace are similarly excluded.
_ALLOMORPH_NOISE_CHARS: frozenset[str] = frozenset('“”„"\'?!,;()[]{}<> \t\n')


def _is_noise_allomorph(form: str) -> bool:
    if not form:
        return True
    return any(ch in _ALLOMORPH_NOISE_CHARS for ch in form)


def _clean_allomorphs(entries: list[Entry]) -> int:
    """Drop transcription-noise and self-reference allomorphs.

    Two cleanups:

    1. Self-reference: an entry's own lemma should never appear in its
       ``allomorphs`` list — the lemma is already the canonical form, so
       repeating it adds nothing and clutters the UI display.
    2. Transcription noise: forms containing curly quotes, ``?``, commas,
       or other non-Ainu punctuation are NINJAL's ``raw_morpheme_variants``
       artefacts (e.g. ``re?``, ``"te``) and not real allomorphs.

    Bare attachment-marker-less forms (``te`` alongside ``-te``) are
    *kept* because the web's segmentation lookup relies on them — the UI
    layer hides them at display time.
    """
    dropped = 0
    for entry in entries:
        cleaned: list[str] = []
        for variant in entry.allomorphs:
            if variant == entry.lemma:
                dropped += 1
                continue
            if _is_noise_allomorph(variant):
                dropped += 1
                continue
            if variant in cleaned:
                dropped += 1
                continue
            cleaned.append(variant)
        entry.allomorphs = cleaned
    return dropped


# Categories whose presence implies the morpheme is bound. ``adn``
# (連体) is included per the convention that adnominal forms in Ainu only
# appear modifying a head noun and never as independent words.
_BOUND_CATEGORIES: frozenset[str] = frozenset({"pfx", "sfx", "adn"})

_CATEGORY_TO_MORPH_TYPE: dict[str, str] = {
    "pfx": "prefix",
    "sfx": "suffix",
}


def _apply_bound_flag(entries: list[Entry]) -> dict[str, int]:
    """Centralised bound/morph_type promotion.

    Runs once after every ingest+enrichment step has finished. The rule is:

    - Category in {pfx, sfx, adn} → ``bound=True``; pfx/sfx also set
      ``morph_type`` to prefix/suffix when it is still the default ``root``.
    - ``root`` appearing in ``category_alt`` is Wiktionary/FF-Ainu's way of
      saying "this lemma is attested as a bound nominal root" (e.g. ``mon``
      is tagged both ``noun`` and ``root``). Treat it as a boundness signal
      and flip ``bound=True``. We keep ``morph_type='root'`` because the
      slot it fills in the verbal template is a nominal root, not an affix.
    - Curated entries (``verified=True``) are left alone; the lexicographer
      has already made the call. Same for entries whose lemma carries an
      explicit attachment marker — the NINJAL ingest already classified
      those.
    """
    counters = {"bound_flipped": 0, "morph_type_upgraded": 0}
    for entry in entries:
        if entry.verified:
            continue
        wants_bound = entry.category in _BOUND_CATEGORIES or "root" in entry.category_alt
        if wants_bound and not entry.bound:
            entry.bound = True
            counters["bound_flipped"] += 1
        target_morph = _CATEGORY_TO_MORPH_TYPE.get(entry.category)
        if target_morph and entry.morph_type == "root":
            entry.morph_type = target_morph
            counters["morph_type_upgraded"] += 1
    return counters


_SOURCE_ID_PREFIX_RE = re.compile(r"^[a-z0-9-]+:")


def _normalise_ids(entries: list[Entry]) -> int:
    """Strip ``source:`` prefixes from auto-ingest ids and update refs.

    A morpheme is identified by its lemma + sense, not by which dictionary
    first attested it. The auto-ingests minted ids like ``ninjal:kar``,
    ``tommy1949:foo``, ``tamura1996:bar`` and ``wiktja:baz`` — useful as a
    breadcrumb but misleading for the user: it suggests the morpheme
    belongs to one source. After every ingest+merge has settled we rewrite
    those ids to drop the prefix, and update every composition reference
    (top-level + one level of nested groups) accordingly. Curated ids
    (those without a ``:``) are untouched. Sources still live on
    ``entry.sources``; only the id changes.

    Collisions are a build error — if a curated id is the same as a
    prefix-stripped auto id, the earlier merge step should already have
    folded them.
    """
    rewrites: dict[str, str] = {}
    for entry in entries:
        if _SOURCE_ID_PREFIX_RE.match(entry.id):
            new_id = _SOURCE_ID_PREFIX_RE.sub("", entry.id)
            if new_id:
                rewrites[entry.id] = new_id

    if not rewrites:
        return 0

    # Detect any post-strip collision: two entries that would end up
    # sharing an id. The merge layer is supposed to prevent this, but
    # surface it explicitly if it ever happens.
    seen: set[str] = set()
    for entry in entries:
        final = rewrites.get(entry.id, entry.id)
        if final in seen:
            raise RuntimeError(
                f"id normalisation would collide on '{final}' — the merge "
                f"step needs to handle this case before _normalise_ids runs."
            )
        seen.add(final)

    def remap(token: Any) -> Any:
        if isinstance(token, str):
            return rewrites.get(token, token)
        if isinstance(token, list):
            return [remap(t) for t in token]
        return token

    for entry in entries:
        entry.id = rewrites.get(entry.id, entry.id)
        entry.composition = [remap(item) for item in entry.composition]
    return len(rewrites)


_BOUND_MARKER_CHARS = ("-", "=")


def _is_dashed(lemma: str) -> bool:
    return lemma.startswith(_BOUND_MARKER_CHARS) or lemma.endswith(_BOUND_MARKER_CHARS)


def _norm_gloss(text: str) -> str:
    return text.strip().lower().rstrip("?")


def _gloss_overlap(a: Entry, b: Entry) -> bool:
    a_set = {_norm_gloss(g) for g in (*a.glosses_en, *a.glosses_jp) if g}
    b_set = {_norm_gloss(g) for g in (*b.glosses_en, *b.glosses_jp) if g}
    if not a_set or not b_set:
        # If one side has no glosses we can't disprove identity; be permissive.
        return True
    return bool(a_set & b_set)


def _can_merge_pair(canonical: Entry, candidate: Entry) -> bool:
    """Decide whether a bare entry should fold into a dashed canonical.

    Same logic as :func:`ingest_ninjal.merge_with_seed`'s fuzzy step: agreed
    category counts as a strong signal, and otherwise we require gloss
    overlap so distinct homographs (``ka`` particle vs ``-ka`` causative)
    stay separate.

    An uncategorised bare candidate is trusted whenever the canonical
    carries a structural bound category (pfx/sfx/clitic/adn) — these
    canonicals only exist when an upstream source has explicitly marked
    the form as bound, so the bare form is almost always the same morpheme
    written without its attachment marker.
    """
    if canonical.category and candidate.category and canonical.category == candidate.category:
        return True
    if not candidate.category:
        if canonical.category in _BOUND_CATEGORIES or canonical.morph_type == "clitic":
            return True
        return _gloss_overlap(canonical, candidate)
    return False


def _absorb(canonical: Entry, victim: Entry) -> None:
    if victim.lemma and victim.lemma not in canonical.allomorphs:
        canonical.allomorphs.append(victim.lemma)
    for variant in victim.allomorphs:
        if variant and variant not in canonical.allomorphs:
            canonical.allomorphs.append(variant)
    if victim.frequency > canonical.frequency:
        canonical.frequency = victim.frequency
    for source in victim.sources:
        if source not in canonical.sources:
            canonical.sources.append(source)
    for gloss in victim.glosses_en:
        if gloss not in canonical.glosses_en:
            canonical.glosses_en.append(gloss)
    for gloss in victim.glosses_jp:
        if gloss not in canonical.glosses_jp:
            canonical.glosses_jp.append(gloss)
    for alt in victim.category_alt:
        if alt != canonical.category and alt not in canonical.category_alt:
            canonical.category_alt.append(alt)
    for dialect in victim.dialects:
        if dialect not in canonical.dialects:
            canonical.dialects.append(dialect)


def _canonicalise_bound_pairs(entries: list[Entry]) -> tuple[list[Entry], int]:
    """Collapse ``X`` + ``X-`` / ``-X`` / ``X=`` / ``=X`` duplicates.

    NINJAL writes bound morphemes bare while Wiktionary writes them with the
    attachment marker, so we end up with two entries for the same morpheme
    (e.g. ``oar`` from NINJAL, ``oar-`` from the Wiktionary-compositions
    ingest). After all ingests have finished we run this pass to merge any
    such pair into the dashed canonical form, preserving the bare form as
    an allomorph.

    Returns the deduplicated entry list and the number of entries removed.
    """
    by_bare: dict[str, list[Entry]] = defaultdict(list)
    for entry in entries:
        bare = entry.lemma.strip("-=")
        if bare:
            by_bare[bare].append(entry)

    to_remove: set[int] = set()
    for group in by_bare.values():
        if len(group) < 2:
            continue
        dashed = [e for e in group if _is_dashed(e.lemma)]
        bare_entries = [e for e in group if not _is_dashed(e.lemma)]
        if not dashed or not bare_entries:
            continue
        # Choose canonical: prefer the dashed entry that is already marked
        # bound, then highest frequency, then verified status.
        canonical = max(
            dashed,
            key=lambda e: (int(e.verified), int(e.bound), e.frequency),
        )
        for cand in bare_entries:
            if cand is canonical or id(cand) in to_remove:
                continue
            if cand.verified and not canonical.verified:
                # Don't absorb a curated entry into an automated one.
                continue
            if _can_merge_pair(canonical, cand):
                _absorb(canonical, cand)
                to_remove.add(id(cand))

    if not to_remove:
        return entries, 0
    return [e for e in entries if id(e) not in to_remove], len(to_remove)


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

    promoted_bound = 0
    if ja_glosses:
        promoted_bound = promote_wiktionary_bound_lemmas(entries, ja_glosses, en_glosses)

    ff_ainu_pos = (
        load_ff_ainu_pos(ff_ainu_saru_path)
        if ff_ainu_saru_path and ff_ainu_saru_path.exists()
        else {}
    )
    if ff_ainu_pos:
        ff_counters = enrich_with_ff_ainu(entries, ff_ainu_pos)
    else:
        ff_counters = {"categories_set": 0, "categories_upgraded": 0, "alts_added": 0}

    tamura_pos_counters = {
        "categories_set": 0,
        "categories_alt": 0,
        "bound_flipped": 0,
        "morph_type_upgraded": 0,
        "new_entries": 0,
        "glosses_added": 0,
    }
    if TAMURA_ENTRIES_PATH.exists():
        tamura_rows = parse_tamura_entries(TAMURA_ENTRIES_PATH)
        tamura_pos_counters = enrich_with_tamura(entries, tamura_rows)

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
        "wikt_bound_promoted": promoted_bound,
        "tamura_pos_categories_set": tamura_pos_counters["categories_set"],
        "tamura_pos_categories_alt": tamura_pos_counters["categories_alt"],
        "tamura_pos_bound_flipped": tamura_pos_counters["bound_flipped"],
        "tamura_pos_morph_type_upgraded": tamura_pos_counters["morph_type_upgraded"],
        "tamura_pos_new_entries": tamura_pos_counters["new_entries"],
        "tamura_pos_glosses_added": tamura_pos_counters["glosses_added"],
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

    bound_counters = _apply_bound_flag(entries)
    counters["bound_flag_applied"] = bound_counters["bound_flipped"]
    counters["morph_type_upgraded"] = bound_counters["morph_type_upgraded"]

    entries, dedup_removed = _canonicalise_bound_pairs(entries)
    counters["bound_pairs_merged"] = dedup_removed

    # Re-apply the bound flag after the dedupe pass: when a bare/dashed pair
    # gets collapsed, the surviving canonical may have inherited category
    # information from the absorbed entry that warrants a fresh flip.
    bound_counters_2 = _apply_bound_flag(entries)
    counters["bound_flag_applied"] += bound_counters_2["bound_flipped"]
    counters["morph_type_upgraded"] += bound_counters_2["morph_type_upgraded"]

    # Accented allomorphs: harvest after dedupe so they attach to the
    # canonical post-merge entry (e.g. ``símon-`` lands on ``simon-`` even
    # if a bare ``simon`` was just absorbed).
    if WIKT_JA_ENTRIES_PATH.exists():
        accent_counters = harvest_wiktionary_accents(entries, WIKT_JA_ENTRIES_PATH)
        counters["accent_pairs_found"] = accent_counters["accent_pairs_found"]
        counters["accent_allomorphs_added"] = accent_counters["allomorphs_added"]

    if TAMURA_ENTRIES_PATH.exists():
        tamura_counters = _harvest_tamura_accents(entries, TAMURA_ENTRIES_PATH)
        counters["tamura_accent_pairs"] = tamura_counters["tamura_accent_pairs"]
        counters["tamura_allomorphs_added"] = tamura_counters["tamura_allomorphs_added"]

    # Final cleanup pass: drop transcription noise and self-references from
    # every entry's allomorph list. Done last so it covers everything every
    # ingest may have added.
    counters["allomorphs_dropped_noise"] = _clean_allomorphs(entries)

    # Normalise auto-ingest ids — drop the ``source:`` prefix so morphemes
    # are identified independently of which dictionary first attested them.
    # Composition references are updated to point at the new ids.
    counters["ids_normalised"] = _normalise_ids(entries)

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
        f"alts_added={counters['ff_ainu_alts_added']}\n"
        f"  Boundness: bound_flipped={counters.get('bound_flag_applied', 0)} "
        f"morph_type_upgraded={counters.get('morph_type_upgraded', 0)} "
        f"bound_pairs_merged={counters.get('bound_pairs_merged', 0)} "
        f"wikt_bound_promoted={counters.get('wikt_bound_promoted', 0)}\n"
        f"  Accents: pairs_found={counters.get('accent_pairs_found', 0)} "
        f"allomorphs_added={counters.get('accent_allomorphs_added', 0)} "
        f"tamura_pairs={counters.get('tamura_accent_pairs', 0)} "
        f"tamura_allomorphs_added={counters.get('tamura_allomorphs_added', 0)}\n"
        f"  Allomorph cleanup: dropped={counters.get('allomorphs_dropped_noise', 0)}\n"
        f"  Tamura POS: cat_set={counters.get('tamura_pos_categories_set', 0)} "
        f"cat_alt={counters.get('tamura_pos_categories_alt', 0)} "
        f"bound_flipped={counters.get('tamura_pos_bound_flipped', 0)} "
        f"new_entries={counters.get('tamura_pos_new_entries', 0)} "
        f"glosses_added={counters.get('tamura_pos_glosses_added', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
