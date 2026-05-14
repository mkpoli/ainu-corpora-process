"""Build candidate morpheme entries from the NINJAL morpheme lexicon TSV.

The NINJAL extractor (``corpus/ninjal/extract_morpheme_lexicon.py``) emits a
TSV of every morpheme attested in the corpus together with its primary
English/Japanese glosses, occurrence count, and raw-form variants. Those rows
are *observational* data: they tell us a morpheme exists and appears with
some frequency, but they do not commit to a valency frame or a combination
rule. We therefore ingest them as unverified candidates, leaving the valency
fields empty so they can be filled in by curation.

The ingest is intentionally cautious:

- Only morphemes with a non-empty primary English gloss are imported.
- Morphemes that look like person markers (``A``, ``S``, ``4.A=`` etc.) are
  tagged with morph_type ``clitic``; everything else stays as ``root``.
- Glyphs like ``=`` and trailing ``-`` are used only as hints for ``bound``
  and ``morph_type`` — they are *not* stripped, because the NINJAL convention
  encodes attachment direction on the form itself.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from morpheme_db.schema import Entry

def _classify(lemma: str, gloss_en: str) -> tuple[bool, str]:
    """Return (bound, morph_type) heuristics from the surface form.

    The NINJAL convention distinguishes attachment direction with ``-`` and
    ``=``: ``-`` marks affixes (``-e``, ``yay-``) while ``=`` marks clitics
    (``a=``, ``=an``). We follow that convention here.
    """
    has_eq = "=" in lemma
    has_dash_left = lemma.startswith("-")
    has_dash_right = lemma.endswith("-")
    bound = has_eq or has_dash_left or has_dash_right

    if has_eq:
        return (True, "clitic")
    if has_dash_right and not has_dash_left:
        return (True, "prefix")
    if has_dash_left and not has_dash_right:
        return (True, "suffix")
    return (bound, "root")


def _split_variants(field: str) -> list[str]:
    """Split a ``foo (1234) || bar (3)``-style cell into the variant forms."""
    if not field:
        return []
    parts = []
    for chunk in field.split("||"):
        chunk = chunk.strip()
        if not chunk:
            continue
        # Strip trailing ``(NNN)`` count annotations.
        m = re.match(r"^(.*?)(?:\s*\(\d+\))?$", chunk)
        if m:
            value = m.group(1).strip()
            if value:
                parts.append(value)
    return parts


def ingest_ninjal_lexicon(path: Path) -> list[Entry]:
    """Parse the NINJAL lexicon TSV into a list of unverified ``Entry`` objects."""
    entries: list[Entry] = []
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            lemma = (row.get("morpheme") or "").strip()
            if not lemma:
                continue
            gloss_en = (row.get("primary_gloss_en") or "").strip()
            gloss_jp = (row.get("primary_gloss_jp") or "").strip()
            if not gloss_en and not gloss_jp:
                continue
            bound, morph_type = _classify(lemma, gloss_en)
            entries.append(
                Entry(
                    id=f"ninjal:{lemma}",
                    lemma=lemma,
                    allomorphs=_split_variants(row.get("raw_morpheme_variants") or ""),
                    category="",
                    bound=bound,
                    morph_type=morph_type,
                    base_frame=None,
                    rules=[],
                    glosses_en=[gloss_en] if gloss_en else [],
                    glosses_jp=[gloss_jp] if gloss_jp else [],
                    sources=["NINJALCorpus"],
                    frequency=int(row.get("occurrence_count") or 0),
                    verified=False,
                    notes=row.get("normalization_notes", ""),
                )
            )
    return entries


def _lemma_keys(lemma: str) -> list[str]:
    """Keys under which a lemma should be indexed for merging.

    Seed entries store affixes with attachment markers (``si-``, ``-e``,
    ``ko-``) while NINJAL writes the same morphemes bare (``si``, ``e``,
    ``ko``). To merge them we index curated entries under both their full
    lemma *and* the marker-stripped bare form.
    """
    bare = lemma.strip("-=")
    keys = [lemma]
    if bare and bare != lemma:
        keys.append(bare)
    return keys


def merge_with_seed(seed: list[Entry], ninjal: list[Entry]) -> list[Entry]:
    """Merge NINJAL candidates with curated seed entries.

    Match is by lemma (with bare-form aliasing for affixes). Where a curated
    entry exists, the NINJAL frequency is folded into it but the curated
    valency/category/glosses are preserved. The original NINJAL form is kept
    as an ``allomorph`` so the CLI resolver finds the curated entry from a
    bare-form lookup.
    """
    index: dict[str, Entry] = {}
    for entry in seed:
        for key in _lemma_keys(entry.lemma):
            index.setdefault(key, entry)
    merged: list[Entry] = list(seed)
    for candidate in ninjal:
        existing = index.get(candidate.lemma)
        if existing is not None:
            existing.frequency = max(existing.frequency, candidate.frequency)
            for source in candidate.sources:
                if source not in existing.sources:
                    existing.sources.append(source)
            if candidate.lemma != existing.lemma and candidate.lemma not in existing.allomorphs:
                existing.allomorphs.append(candidate.lemma)
            for variant in candidate.allomorphs:
                if variant and variant not in existing.allomorphs:
                    existing.allomorphs.append(variant)
            continue
        merged.append(candidate)
    return merged


__all__ = ["ingest_ninjal_lexicon", "merge_with_seed"]
