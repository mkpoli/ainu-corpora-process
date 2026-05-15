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
from pathlib import Path
from typing import Any

from morpheme_db.schema import Entry

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

        # Upgrade morph_type when category is unambiguously a structural tag.
        if entry.morph_type == "root":
            if entry.category == "pfx":
                entry.morph_type = "prefix"
                entry.bound = True
            elif entry.category == "sfx":
                entry.morph_type = "suffix"
                entry.bound = True

    return entries


__all__ = ["WIKTIONARY_XPOS_MAP", "enrich_with_wiktionary", "load_json_dict"]
