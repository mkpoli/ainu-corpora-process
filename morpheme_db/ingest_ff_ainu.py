"""Refine entry categories using the FF Ainu Saru POS list.

The Wiktionary POS file is the broadest source of part-of-speech data, but
it only carries a generic ``verb`` tag — it loses the 他動/自動/複他 (vt/vi/vd)
distinction that Tamura 1996 and other curated dictionaries record. That
distinction is preserved in ``dictionary/output/ff-ainu-saru-terms.json``
(FF Ainu's Saru-dialect list, transcribed from Tamura), which tags each
lemma with a Japanese POS abbreviation like ``他``, ``自``, ``複他``.

This module reads that file, maps the abbreviations to the XPOS inventory
(see ``dictionary/XPOS.md``), and folds the result into morpheme_db
entries. Refinement is *upgrade-only*:

- An entry with no category at all gets the FF Ainu category.
- An entry tagged with the generic ``v`` (from Wiktionary's plain ``verb``)
  is upgraded to ``vt``/``vi``/``vd``/``vc`` when FF Ainu has the specific
  one.
- An entry already tagged with a specific transitivity is left alone, but
  any additional FF Ainu POS values are recorded in ``category_alt`` so
  polysemous lemmas don't lose their alternative readings.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from morpheme_db.schema import Entry

# Map the Japanese POS abbreviations FF Ainu uses to the XPOS inventory.
# ``動`` is the generic ``動詞`` (no transitivity info) — mapped to ``v``
# so it cannot accidentally overwrite a more specific tag like ``vt``.
# ``自動`` is a verbose spelling of ``自`` that appears in a handful of
# entries; treat it as the same as ``自``.
FF_AINU_POS_MAP: dict[str, str] = {
    "他": "vt",
    "自": "vi",
    "自動": "vi",
    "複他": "vd",
    "完": "vc",
    "動": "v",
    "名": "n",
    "代名": "pron",
    "位名": "nl",
    "形名": "nmlz",
    "副": "adv",
    "後副": "padv",
    "連体": "adn",
    "間投": "intj",
    "助動": "auxv",
    "格助": "postp",
    "副助": "advp",
    "終助": "sfp",
    "接助": "sconj",
    "人接": "pers",
    "接頭": "pfx",
    "接尾": "sfx",
    "位名＋格助": "colloc",
    "名＋格助": "colloc",
}

# Categories considered specific enough that FF Ainu shouldn't overwrite
# them. A lemma already tagged ``vt`` should not be downgraded to ``v``,
# and FF Ainu's value (if different) belongs in ``category_alt`` instead.
SPECIFIC_VERB_CATEGORIES: frozenset[str] = frozenset({"vt", "vi", "vd", "vc"})


def load_ff_ainu_pos(path: Path) -> dict[str, list[str]]:
    """Read ff-ainu-saru-terms.json into ``{latn_lemma: [xpos, ...]}``.

    Source rows look like ``{"kana": "カラ", "latn": "kar", "glss": "～を作る",
    "pos": "他"}``. ``pos`` may also be a ``／``-separated list of POS tags
    (e.g. ``他／自`` for a verb attested both transitively and intransitively).
    We split on ``／`` and map each component, dropping any unrecognised
    abbreviations silently — the unmapped ones are typically dialect or
    grammatical tags that don't belong in the XPOS inventory.
    """
    data: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for entry in data:
        lemma = (entry.get("latn") or "").strip()
        raw_pos = (entry.get("pos") or "").strip()
        if not lemma or not raw_pos:
            continue
        mapped: list[str] = []
        for chunk in raw_pos.split("／"):
            xpos = FF_AINU_POS_MAP.get(chunk.strip())
            if xpos and xpos not in mapped:
                mapped.append(xpos)
        if not mapped:
            continue
        # Last writer wins for duplicate lemmas: the FF Ainu list does
        # contain a few homograph rows but they generally agree on POS.
        out[lemma] = mapped
    return out


def _lookup_keys(entry: Entry) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    for form in (entry.lemma, *entry.allomorphs):
        if not form:
            continue
        if form not in seen:
            keys.append(form)
            seen.add(form)
        bare = form.strip("-=")
        if bare and bare not in seen:
            keys.append(bare)
            seen.add(bare)
    return keys


def _add_source(entry: Entry, source: str) -> None:
    if source not in entry.sources:
        entry.sources.append(source)


def enrich_with_ff_ainu(
    entries: list[Entry],
    ff_pos: dict[str, list[str]],
    *,
    source_label: str = "FF Ainu Saru",
) -> dict[str, int]:
    """Refine categories in-place using FF Ainu Saru POS data.

    Returns counters describing what changed so the build summary can
    surface how many entries actually got a transitivity upgrade.
    """
    counters = {
        "categories_set": 0,
        "categories_upgraded": 0,
        "alts_added": 0,
    }
    for entry in entries:
        if entry.verified:
            # Curated entries already have hand-checked categories; don't
            # let an automated source overwrite them.
            continue
        found: list[str] | None = None
        for key in _lookup_keys(entry):
            if key in ff_pos:
                found = ff_pos[key]
                break
        if not found:
            continue

        primary, *rest = found
        changed = False
        if not entry.category:
            entry.category = primary
            counters["categories_set"] += 1
            changed = True
        elif entry.category == "v" and primary in SPECIFIC_VERB_CATEGORIES:
            # Upgrade the generic Wiktionary ``v`` to FF Ainu's specific
            # transitivity tag — this is the main goal of this ingest.
            if entry.category not in entry.category_alt:
                # Keep the old generic category visible as an alternative
                # only if it's *not* the same family as the upgrade.
                # ``v`` is just less specific, so drop it instead.
                pass
            entry.category = primary
            counters["categories_upgraded"] += 1
            changed = True
        elif entry.category != primary and primary not in entry.category_alt:
            entry.category_alt.append(primary)
            counters["alts_added"] += 1
            changed = True

        for alt in rest:
            if alt != entry.category and alt not in entry.category_alt:
                entry.category_alt.append(alt)
                counters["alts_added"] += 1
                changed = True

        # If we upgraded ``v`` → ``vt``/``vi``/``vd``/``vc``, scrub the now-
        # redundant generic ``v`` if a previous pass parked it in
        # ``category_alt``: it's strictly less informative than the new
        # primary and would just clutter the UI's "Also" line.
        if entry.category in SPECIFIC_VERB_CATEGORIES and "v" in entry.category_alt:
            entry.category_alt.remove("v")

        if changed:
            _add_source(entry, source_label)

    return counters


__all__ = [
    "FF_AINU_POS_MAP",
    "enrich_with_ff_ainu",
    "load_ff_ainu_pos",
]
