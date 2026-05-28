"""Ingest Tommy 1949 (Batchelor's reorganised dictionary) decomposition data.

Two files under ``dictionary/output/``:

- ``tommy1949_decomposed_words.json`` — ``{lemma: [morpheme, ...]}`` (~10 K).
- ``tommy1949_aynudictionary_glosses.json`` — ``[{lemma, glosses[]}, ...]``,
  ~14 K rows (multiple per lemma when there are homographs).

For each decomposed word, we resolve constituents against the current entry
inventory and either attach the composition to an existing entry (if it
doesn't already have one) or create a new ``tommy1949:<lemma>`` entry.
Tommy glosses are folded in where the entry's Japanese glosses are empty.
"""

from __future__ import annotations

import json
from pathlib import Path

from morpheme_db.schema import Entry


def _resolve_in_context(key: str, position: int, total: int, index: dict[str, Entry]) -> Entry | None:
    """Position-aware resolve for a Tommy decomposition key.

    Tommy 1949 records decompositions with bare-form keys (``e``, ``ko``,
    ``te``) regardless of whether they're affixes or roots. The default
    ``index.get(key)`` then prefers whichever entry registered under the
    bare form first — which is typically the higher-frequency *lexical*
    homophone (e.g. ``e`` 'eat' wins over the applicative prefix ``e-``).

    This helper consults the position of the key in the decomposition:
    a bare key at index 0 of a multi-part decomposition is much more
    likely to be a prefix, and a bare key at the last index is much
    more likely to be a suffix. We try the appropriate dashed form
    first, then fall back to the original bare lookup.

    Keys that already carry an attachment marker (``-``/``=``) are
    looked up verbatim — the source already disambiguated direction.
    """
    explicit = index.get(key)
    if "-" in key or "=" in key:
        return explicit

    if total > 1 and position == 0:
        cand = index.get(key + "-")
        if cand is not None and cand.morph_type == "prefix":
            return cand
    if total > 1 and position == total - 1:
        cand = index.get("-" + key)
        if cand is not None and cand.morph_type == "suffix":
            return cand

    if explicit is not None:
        return explicit
    return index.get(key.strip("-="))


def _surface_with_marker(key: str, entry: Entry) -> str:
    """Reattach the attachment marker to a bare-form decomposition key.

    Tommy 1949 records affixes with the marker stripped (``pak + te`` for
    ``pakte``). For graph rendering we want the marker back (``pak + -te``)
    so the surface form is unambiguous. The resolved entry's ``morph_type``
    tells us where the marker goes.
    """
    if not key or "-" in key or "=" in key:
        return key
    if entry.morph_type == "suffix":
        return "-" + key
    if entry.morph_type == "prefix":
        return key + "-"
    if entry.morph_type == "clitic":
        # Clitics in this DB use ``=`` and can attach on either side. The
        # entry's own lemma encodes the direction (``a=`` vs ``=an``), so
        # mirror that.
        if entry.lemma.startswith("="):
            return "=" + key
        if entry.lemma.endswith("="):
            return key + "="
    return key


def load_decomposed(path: Path) -> dict[str, list[str]]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_glosses(path: Path) -> dict[str, list[str]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    grouped: dict[str, list[str]] = {}
    for row in raw:
        lemma = row.get("lemma")
        glosses = row.get("glosses") or []
        if not lemma:
            continue
        bucket = grouped.setdefault(lemma, [])
        for g in glosses:
            if g and g not in bucket:
                bucket.append(g)
    return grouped


def _build_lemma_index(entries: list[Entry]) -> dict[str, Entry]:
    sorted_entries = sorted(entries, key=lambda e: (0 if e.verified else 1, -e.frequency))
    index: dict[str, Entry] = {}
    for entry in sorted_entries:
        keys = {entry.lemma, *entry.allomorphs}
        bare = entry.lemma.strip("-=")
        if bare:
            keys.add(bare)
        for key in keys:
            if not key:
                continue
            index.setdefault(key, entry)
    return index


def ingest_tommy1949(
    entries: list[Entry],
    decomposed: dict[str, list[str]],
    glosses: dict[str, list[str]],
) -> tuple[list[Entry], dict[str, int]]:
    """Returns ``(entries, counters)``."""
    index = _build_lemma_index(entries)
    by_lemma: dict[str, Entry] = {e.lemma: e for e in entries}

    counters = {
        "compositions_attached": 0,
        "compositions_skipped": 0,
        "new_entries": 0,
        "glosses_added": 0,
    }

    for lemma, morph_keys in decomposed.items():
        if not isinstance(morph_keys, list) or len(morph_keys) < 2:
            counters["compositions_skipped"] += 1
            continue

        resolved_ids: list[str] = []
        surfaces: list[str] = []
        all_resolved = True
        for position, key in enumerate(morph_keys):
            entry = _resolve_in_context(key, position, len(morph_keys), index)
            if entry is None:
                all_resolved = False
                break
            resolved_ids.append(entry.id)
            surfaces.append(_surface_with_marker(key, entry))
        if not all_resolved:
            counters["compositions_skipped"] += 1
            continue

        gloss_list = list(glosses.get(lemma, []))
        existing = by_lemma.get(lemma)
        if existing is not None:
            updated = False
            # Curated entries own their composition (the lexicographer's
            # call about synchronic vs etymological structure). Tommy can
            # still contribute Japanese glosses to them, though.
            if not existing.composition and not existing.verified:
                existing.composition = resolved_ids
                existing.composition_surface = surfaces
                if not existing.composition_note:
                    existing.composition_note = (
                        f"Decomposition from Tommy 1949: {' + '.join(morph_keys)}."
                    )
                counters["compositions_attached"] += 1
                updated = True
            if gloss_list and not existing.glosses_jp:
                existing.glosses_jp = gloss_list
                counters["glosses_added"] += 1
                updated = True
            if updated and "Tommy 1949" not in existing.sources:
                existing.sources.append("Tommy 1949")
        else:
            new_entry = Entry(
                id=f"tommy1949:{lemma}",
                lemma=lemma,
                composition=resolved_ids,
                composition_surface=surfaces,
                composition_note=f"Decomposition from Tommy 1949: {' + '.join(morph_keys)}.",
                glosses_jp=gloss_list,
                sources=["Tommy 1949"],
                verified=False,
            )
            entries.append(new_entry)
            by_lemma[lemma] = new_entry
            counters["compositions_attached"] += 1
            counters["new_entries"] += 1
            if gloss_list:
                counters["glosses_added"] += 1

    return entries, counters


__all__ = ["ingest_tommy1949", "load_decomposed", "load_glosses"]
