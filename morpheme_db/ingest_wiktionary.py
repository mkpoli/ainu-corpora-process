"""Per-source Wiktionary enrichment for the morpheme database.

This replaces the older ``ingest_dictionary.py`` path which collapsed several
upstream sources into a generic ``Dictionary`` attribution. We now read the
underlying Wiktionary files directly and tag entries as either ``Wiktionary
JA`` or ``Wiktionary EN`` so the UI can deep-link to the exact reference.

Files consumed (all under ``dictionary/output/``):

- ``wiktionary_ainu_glosses.json``    — ``{lemma: {lemma, pos, glosses[]}}``
- ``wiktionary_ainu_glosses_en.json`` — ``{lemma: {lemma, lemma_original, pos, glosses[]}}``
- ``wiktionary_ainu_part_of_speech.json`` — ``{lemma: [pos, ...]}``

Curated entries retain their hand-chosen category, valency, and glosses;
only empty fields are filled in.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from morpheme_db.schema import Entry

# Maps accented Latin vowels (used in Tamura / Wiktionary to mark stress
# or pitch on Ainu transcriptions) back to plain ASCII. This lets us check
# whether two strings differ *only* in accent marks: ``deaccent(símon-)``
# returns ``simon-``.
_ACCENT_TABLE = str.maketrans("áéíóúÁÉÍÓÚ", "aeiouAEIOU")


def _deaccent(text: str) -> str:
    return text.translate(_ACCENT_TABLE)


def _has_accent(text: str) -> bool:
    return any(ch in "áéíóúÁÉÍÓÚ" for ch in text)


# Matches ``{{l|ain|TARGET|DISPLAY|...}}``, ``{{l/ain|TARGET|DISPLAY|...}}``,
# and ``{{m|ain|TARGET|DISPLAY|...}}`` link/mention templates. We extract
# the (TARGET, DISPLAY) pair and later filter to pairs where DISPLAY
# differs from TARGET only by accents.
_ACCENT_LINK_RE = re.compile(
    r"\{\{(?:l(?:/ain)?|m)\|ain\|([^|}=]+)\|([^|}=]+)(?=[|}])"
)

# Maps the raw Wiktionary POS labels to the XPOS inventory used elsewhere
# in this repository (see ``dictionary/XPOS.md``).
WIKTIONARY_XPOS_MAP: dict[str, str] = {
    "noun": "n",
    "verb": "v",
    "conj": "cconj",
    "pron": "pron",
    "pronoun": "pron",
    "adv": "adv",
    "parti": "parti",
    "num": "num",
    "interj": "intj",
    "suffix": "sfx",
    "prefix": "pfx",
    "root": "root",
    "auxverb": "auxv",
    "adnom": "adn",
    "postpadv": "padv",
    "colloc": "colloc",
    "determiner": "det",
    "rel": "rel",
}

# Lemmas whose Wiktionary "parti" tag actually refers to a case particle
# (格助詞 / postposition). Wiktionary lumps every 助詞 under a single tag,
# but Ainu distinguishes 格助詞 (locative ta, allative un, …) from other
# 助詞 (e.g. focus ka, topic anak), so we override the mapping for the
# known case particles. ``wa`` is intentionally excluded here because its
# dominant NINJAL sense is the conjunctive ``and`` (して), not the
# ablative case particle ``from``; the ablative ``wa`` lives as a separate
# curated seed entry instead.
CASE_PARTICLE_LEMMAS: frozenset[str] = frozenset({"ta", "un"})


def load_json_dict(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _lookup_keys(entry: Entry) -> list[str]:
    keys = [entry.lemma]
    bare = entry.lemma.strip("-=")
    if bare and bare != entry.lemma:
        keys.append(bare)
    for variant in entry.allomorphs:
        if variant and variant not in keys:
            keys.append(variant)
    return keys


def _add_source(entry: Entry, source: str) -> None:
    if source not in entry.sources:
        entry.sources.append(source)


def _xpos_from(raw: str | None, *, lemma: str = "") -> str:
    if not raw:
        return ""
    xpos = WIKTIONARY_XPOS_MAP.get(raw, "")
    if xpos == "parti" and lemma.strip("-=") in CASE_PARTICLE_LEMMAS:
        return "postp"
    return xpos


def enrich_with_wiktionary(
    entries: list[Entry],
    ja_glosses: dict[str, Any],
    en_glosses: dict[str, Any],
    ja_pos: dict[str, list[str]],
) -> list[Entry]:
    """Fold Wiktionary data into ``entries`` in-place; return same list."""
    for entry in entries:
        keys = _lookup_keys(entry)

        ja_record: dict[str, Any] | None = None
        en_record: dict[str, Any] | None = None
        pos_record: list[str] | None = None
        for k in keys:
            if ja_record is None and k in ja_glosses:
                ja_record = ja_glosses[k]
            if en_record is None and k in en_glosses:
                en_record = en_glosses[k]
            if pos_record is None and k in ja_pos:
                pos_record = ja_pos[k]

        if ja_record:
            if not entry.glosses_jp:
                entry.glosses_jp = list(ja_record.get("glosses", []))
            if not entry.category:
                xpos = _xpos_from(ja_record.get("pos"), lemma=entry.lemma)
                if xpos:
                    entry.category = xpos
            _add_source(entry, "Wiktionary JA")

        if en_record:
            if not entry.glosses_en:
                entry.glosses_en = list(en_record.get("glosses", []))
            if not entry.category:
                xpos = _xpos_from(en_record.get("pos"), lemma=entry.lemma)
                if xpos:
                    entry.category = xpos
            _add_source(entry, "Wiktionary EN")

        if pos_record:
            mapped: list[str] = []
            for raw in pos_record:
                xpos = _xpos_from(raw, lemma=entry.lemma)
                if xpos:
                    if xpos not in mapped:
                        mapped.append(xpos)
                elif raw not in entry.category_alt:
                    entry.category_alt.append(raw)
            if mapped:
                # Known case particles: the postposition reading is the
                # dominant one (e.g. locative ``ta``, ablative ``wa``,
                # allative ``un``). Force ``postp`` as the primary category
                # and demote any other reading to ``category_alt``, even if
                # an earlier JA-only verb record already set the category.
                is_case_particle = (
                    entry.lemma.strip("-=") in CASE_PARTICLE_LEMMAS
                    and "postp" in mapped
                )
                if is_case_particle:
                    if entry.category and entry.category != "postp":
                        if entry.category not in entry.category_alt:
                            entry.category_alt.append(entry.category)
                    entry.category = "postp"
                    _add_source(entry, "Wiktionary JA")
                elif not entry.category:
                    entry.category = mapped[0]
                    _add_source(entry, "Wiktionary JA")
                # Surface any POS the lemma carries beyond the chosen one so
                # genuinely polysemous forms (e.g. ``ta`` as both particle and
                # verb) keep their alternatives visible in the UI. Skip the
                # generic ``v`` when the primary category is already a more
                # specific transitivity (vt/vi/vd/vc) — ``v`` is just less
                # informative, not a distinct reading.
                specific_verbs = {"vt", "vi", "vd", "vc"}
                for xpos in mapped:
                    if xpos == entry.category:
                        continue
                    if xpos == "v" and entry.category in specific_verbs:
                        continue
                    if xpos not in entry.category_alt:
                        entry.category_alt.append(xpos)

    # Note: the bound/morph_type flip used to live here but is now applied
    # globally by ``morpheme_db.build._apply_bound_flag`` after every ingest
    # has finished, so this function only enriches and never structurally
    # rewrites entries.

    return entries


# Wiktionary POS labels that imply a bound morpheme worth promoting to a
# first-class entry. ``root`` is intentionally excluded — bare roots run a
# high risk of collision with unrelated NINJAL homographs (e.g. body-part
# ``mon`` vs the borrowed ``mon`` 門), so they're enriched in place by
# ``enrich_with_wiktionary`` and (when appropriate) flipped to ``bound`` by
# the central post-pass, but never used to mint new entries here.
_BOUND_POS_PROMOTION: dict[str, tuple[str, str]] = {
    "prefix": ("pfx", "prefix"),
    "suffix": ("sfx", "suffix"),
    "adnom": ("adn", "root"),
}


def _canonicalise_affix_lemma(wikt_lemma: str, pos: str) -> str:
    """Add the appropriate attachment marker for an affix lemma.

    Wiktionary keys are *usually* dashed correctly (``simon-``, ``-te``),
    but a handful of bare forms slip through (``te`` tagged as suffix,
    ``i`` tagged as prefix). Normalise to the dashed canonical form so the
    new entry slots into the morpheme database the same way the seed and
    Tamura-style sources do.
    """
    if pos == "prefix" and not wikt_lemma.endswith("-"):
        return wikt_lemma + "-"
    if pos == "suffix" and not wikt_lemma.startswith("-"):
        return "-" + wikt_lemma
    return wikt_lemma


def _build_form_index(entries: list[Entry]) -> dict[str, Entry]:
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


def promote_wiktionary_bound_lemmas(
    entries: list[Entry],
    ja_glosses: dict[str, Any],
    en_glosses: dict[str, Any],
) -> int:
    """Mint entries for Wiktionary-only prefix/suffix/adnominal lemmas.

    The standard enrichment path only modifies existing entries — so a
    Wiktionary lemma with no NINJAL or seed counterpart (e.g. ``simon-``)
    never makes it into the morpheme database. This function fills that
    gap. It only ever creates entries; existing ones are skipped (the
    regular enrich pass handles them).
    """
    index = _build_form_index(entries)
    created = 0
    for wikt_lemma, record in ja_glosses.items():
        if not isinstance(record, dict):
            continue
        pos = record.get("pos")
        promotion = _BOUND_POS_PROMOTION.get(pos)
        if promotion is None:
            continue
        canon = _canonicalise_affix_lemma(wikt_lemma, pos)
        bare = canon.strip("-=")
        # Skip only when the canonical (dashed) form is already present —
        # if just the bare form exists, mint the dashed entry and let the
        # build-level dedupe pass collapse the pair into the canonical.
        if canon in index:
            continue
        # ...but if a non-canonical existing entry already carries a
        # structural bound category that contradicts ours (e.g. ``ka``
        # tagged ``sfx`` for the causative seed), defer to it.
        bare_entry = index.get(bare) if bare else None
        if bare_entry is not None and bare_entry.bound and bare_entry.category and bare_entry.category != promotion[0]:
            continue

        category, morph_type = promotion
        ja_list = list(record.get("glosses", []))
        en_record = en_glosses.get(wikt_lemma) or (en_glosses.get(bare) if bare else None)
        en_list = (
            list(en_record.get("glosses", [])) if isinstance(en_record, dict) else []
        )
        allomorphs: list[str] = []
        if wikt_lemma != canon:
            allomorphs.append(wikt_lemma)

        new_entry = Entry(
            id=f"wiktja:{canon}",
            lemma=canon,
            allomorphs=allomorphs,
            category=category,
            bound=True,
            morph_type=morph_type,
            glosses_jp=ja_list,
            glosses_en=en_list,
            sources=["Wiktionary JA"],
            verified=False,
        )
        entries.append(new_entry)
        index[canon] = new_entry
        if bare:
            index[bare] = new_entry
        for variant in allomorphs:
            index.setdefault(variant, new_entry)
        created += 1
    return created


def harvest_wiktionary_accents(
    entries: list[Entry],
    wikt_entries_path: Path,
) -> dict[str, int]:
    """Collect accent-marked allomorphs from Wiktionary entries.

    Wiktionary JA stores stress/pitch-marked display forms via the
    ``{{l|ain|TARGET|DISPLAY|...}}`` template — for instance
    ``{{l|ain|simon-|símon-|t=右}}`` says the bare lemma is ``simon-`` and
    the accented citation form is ``símon-``. The accent isn't stored on
    the page title, so without parsing the wikitext we'd lose the only
    record of where the stress lives.

    This function scans the dumped Wiktionary entries, extracts every
    ``(target, display)`` pair where the display differs from the target
    *only* in accents, and registers ``display`` as an allomorph on the
    matching entry. Existing allomorphs are not duplicated.

    Returns counters describing what was added.
    """
    counters = {"accent_pairs_found": 0, "allomorphs_added": 0}
    if not wikt_entries_path.exists():
        return counters

    data = json.loads(wikt_entries_path.read_text(encoding="utf-8"))
    index = _build_form_index(entries)

    seen_pairs: set[tuple[str, str]] = set()
    for page in data:
        if not isinstance(page, dict):
            continue
        text = page.get("text") or ""
        for target, display in _ACCENT_LINK_RE.findall(text):
            if not _has_accent(display):
                continue
            if _deaccent(display) != target:
                continue
            key = (target, display)
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            counters["accent_pairs_found"] += 1

            entry = (
                index.get(target)
                or index.get(target.strip("-="))
                or index.get(_deaccent(target).strip("-="))
            )
            if entry is None:
                continue
            if display not in entry.allomorphs and display != entry.lemma:
                entry.allomorphs.append(display)
                counters["allomorphs_added"] += 1
                if "Wiktionary JA" not in entry.sources:
                    entry.sources.append("Wiktionary JA")

    return counters


__all__ = [
    "WIKTIONARY_XPOS_MAP",
    "enrich_with_wiktionary",
    "harvest_wiktionary_accents",
    "load_json_dict",
    "promote_wiktionary_bound_lemmas",
]
