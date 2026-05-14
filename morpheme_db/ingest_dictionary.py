"""Enrich morpheme entries with the combined dictionary POS / gloss data.

This wires in the two combined JSON files that live under
``dictionary/output/``:

- ``combined_part_of_speech.json`` — ``{lemma: [xpos, ...]}``, an aggregate of
  Wiktionary, Kayano, Tamura, and other sources.
- ``combined_glosses.json``        — ``{lemma: [japanese_gloss, ...]}``.

Curated entries are never overwritten. NINJAL candidates have their empty
``category`` and missing Japanese glosses filled in; if the dictionary entry
disambiguates transitivity (``vt`` / ``vi`` / ``vd``), that wins over a bare
``v``. Bound morphemes from the dictionaries (``pfx`` / ``sfx``) also pull in
the corresponding ``morph_type`` and ``bound`` flag when the NINJAL ingest
didn't already detect them.
"""

from __future__ import annotations

import json
from pathlib import Path

from morpheme_db.schema import Entry

# Categories ranked by specificity within a single POS group. When multiple
# values are recorded for one lemma we keep the first one in this order; the
# rest go into ``category_alt``.
PREFERENCE: list[str] = [
    "vt", "vi", "vd", "vc", "v",
    "n", "nl", "nmlz", "propn", "pron",
    "pfx", "sfx",
    "adn", "adv", "padv",
    "cconj", "sconj", "post", "postp", "advp", "parti",
    "auxv", "cop",
    "pers", "sfp", "intj",
    "num", "punct",
    "root",
]
PREFERENCE_INDEX = {p: i for i, p in enumerate(PREFERENCE)}


def _rank(category: str) -> int:
    return PREFERENCE_INDEX.get(category, len(PREFERENCE) + 1)


def _pick_primary(categories: list[str]) -> tuple[str, list[str]]:
    """Return ``(primary, alternatives)`` ordered by preference."""
    seen: list[str] = []
    for cat in categories:
        if cat and cat not in seen:
            seen.append(cat)
    if not seen:
        return ("", [])
    ranked = sorted(seen, key=_rank)
    return (ranked[0], ranked[1:])


def load_combined_pos(path: Path) -> dict[str, list[str]]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_combined_glosses(path: Path) -> dict[str, list[str]]:
    return json.loads(path.read_text(encoding="utf-8"))


def enrich_entries(
    entries: list[Entry],
    pos_data: dict[str, list[str]],
    gloss_data: dict[str, list[str]],
) -> list[Entry]:
    """Mutate and return ``entries`` with dictionary information folded in."""
    for entry in entries:
        candidate_keys = [entry.lemma]
        # NINJAL person markers carry ``=`` glyphs; dictionary keys don't, so
        # try a stripped form as well.
        stripped = entry.lemma.strip("-=")
        if stripped and stripped != entry.lemma:
            candidate_keys.append(stripped)

        dict_pos: list[str] = []
        dict_glosses: list[str] = []
        for key in candidate_keys:
            if key in pos_data and not dict_pos:
                dict_pos = pos_data[key]
            if key in gloss_data and not dict_glosses:
                dict_glosses = gloss_data[key]

        if dict_pos:
            primary, alternatives = _pick_primary(dict_pos)
            if not entry.category:
                entry.category = primary
                # Augment morph_type / bound from the dictionary's view when
                # the NINJAL ingest left it as a generic root.
                if primary == "pfx" and entry.morph_type == "root":
                    entry.morph_type = "prefix"
                    entry.bound = True
                elif primary == "sfx" and entry.morph_type == "root":
                    entry.morph_type = "suffix"
                    entry.bound = True
            # Always merge alternative categories — useful for 範疇転換 cases.
            for alt in alternatives:
                if alt and alt != entry.category and alt not in entry.category_alt:
                    entry.category_alt.append(alt)
            if "Dictionary" not in entry.sources:
                entry.sources.append("Dictionary")

        if dict_glosses and not entry.glosses_jp:
            entry.glosses_jp = list(dict_glosses)
            if "Dictionary" not in entry.sources:
                entry.sources.append("Dictionary")

    return entries


__all__ = ["enrich_entries", "load_combined_glosses", "load_combined_pos"]
