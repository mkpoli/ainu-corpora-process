"""Ingest Wiktionary's word-composition data.

``dictionary/output/wiktionary_ainu_word_compositions.json`` is a dict from
compound lemma → ordered list of ``[morpheme, japanese_gloss]`` pairs, e.g.::

    "rep":     [["re", "三つの"], ["-p", "もの"]]
    "ahupte":  [["ahup", "入る"], ["-te", "させる"]]

For each entry, we resolve the constituent morphemes against the entries
already in the database (by lemma or attachment-stripped bare form). When
all constituents resolve cleanly we either:

  - attach the composition to an existing matching entry (if it doesn't
    already have one and isn't curated as authoritative), or
  - create a new ``wiktja-compound:<lemma>`` entry.

Curated entries are never overwritten — they're treated as the truth.
"""

from __future__ import annotations

import json
from pathlib import Path

from morpheme_db.ingest_tommy1949 import _surface_with_marker
from morpheme_db.schema import Entry


def load_compositions(path: Path) -> dict[str, list[list[str]]]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_lemma_index(entries: list[Entry]) -> dict[str, Entry]:
    """Map every surface key (lemma + allomorphs + bare form) to an entry.

    Curated entries register first so they win ties; NINJAL ingest tagged
    bound morphemes with the ``-`` / ``=`` markers, so we also register the
    bare form for fuzzy matches with Wiktionary's marker-less morpheme names.
    """
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


def ingest_wiktionary_compositions(
    entries: list[Entry], data: dict[str, list[list[str]]]
) -> tuple[list[Entry], int, int]:
    """Returns ``(entries, attached, skipped)``.

    ``attached`` counts the number of compositions actually folded in, and
    ``skipped`` counts entries whose constituents we couldn't fully resolve.
    """
    index = _build_lemma_index(entries)
    by_lemma: dict[str, Entry] = {e.lemma: e for e in entries}

    attached = 0
    skipped = 0

    for lemma, raw_parts in data.items():
        morpheme_keys: list[str] = []
        for part in raw_parts:
            if not isinstance(part, list) or not part:
                morpheme_keys = []
                break
            morpheme_keys.append(part[0])
        if not morpheme_keys or len(morpheme_keys) < 2:
            skipped += 1
            continue

        resolved_ids: list[str] = []
        surfaces: list[str] = []
        all_resolved = True
        for key in morpheme_keys:
            entry = index.get(key) or index.get(key.strip("-="))
            if entry is None:
                all_resolved = False
                break
            resolved_ids.append(entry.id)
            surfaces.append(_surface_with_marker(key, entry))
        if not all_resolved:
            skipped += 1
            continue

        existing = by_lemma.get(lemma)
        if existing is not None:
            # Don't overwrite a curated composition, and don't add an
            # automatic synchronic composition to a curated entry — that
            # decision belongs to the lexicographer (e.g. nukar is
            # synchronically atomic; its nu-kar analysis is etymological,
            # not synchronic). Also don't touch entries that already have a
            # composition.
            if existing.composition:
                continue
            if existing.verified:
                continue
            existing.composition = resolved_ids
            existing.composition_surface = surfaces
            if not existing.composition_note:
                gloss_pairs = ", ".join(
                    f"{p[0]} '{p[1]}'" for p in raw_parts if isinstance(p, list) and len(p) >= 2
                )
                existing.composition_note = (
                    f"Composition recorded by Japanese Wiktionary: {gloss_pairs}."
                ).strip()
            if "Wiktionary JA" not in existing.sources:
                existing.sources.append("Wiktionary JA")
            attached += 1
        else:
            new_entry = Entry(
                id=f"wiktja-compound:{lemma}",
                lemma=lemma,
                composition=resolved_ids,
                composition_surface=surfaces,
                composition_note=(
                    "Composition recorded by Japanese Wiktionary: "
                    + ", ".join(
                        f"{p[0]} '{p[1]}'" for p in raw_parts if isinstance(p, list) and len(p) >= 2
                    )
                ),
                sources=["Wiktionary JA"],
                verified=False,
            )
            entries.append(new_entry)
            by_lemma[lemma] = new_entry
            attached += 1

    return entries, attached, skipped


__all__ = ["ingest_wiktionary_compositions", "load_compositions"]
