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
        all_resolved = True
        for key in morph_keys:
            entry = index.get(key) or index.get(key.strip("-="))
            if entry is None:
                all_resolved = False
                break
            resolved_ids.append(entry.id)
        if not all_resolved:
            counters["compositions_skipped"] += 1
            continue

        gloss_list = list(glosses.get(lemma, []))
        existing = by_lemma.get(lemma)
        if existing is not None:
            updated = False
            if not existing.composition:
                existing.composition = resolved_ids
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
