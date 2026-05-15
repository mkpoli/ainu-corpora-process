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


_DOUBLED_MARKERS = re.compile(r"(=+)|(-+)")


def _normalise_attachment_markers(lemma: str) -> str:
    """Collapse accidental runs of attachment markers.

    NINJAL contains stray transcription typos like ``a==`` (one occurrence of
    a doubled clitic boundary, semantically identical to ``a=``). Single ``=``
    and ``-`` are the only meaningful markers, so we squash any run down to
    one character.
    """
    return _DOUBLED_MARKERS.sub(lambda m: "=" if m.group(1) else "-", lemma)


_GLOSS_COLON_WRAPPER = re.compile(r"::([^:]*?)::")


def _clean_gloss(text: str) -> str:
    """Strip NINJAL's ``::xxx::`` wrappers from a gloss.

    The corpus extractor emits function-word translations wrapped in ``::``
    (e.g. ``::〜に::``, ``::〜の::``, ``::か::``, or mid-string variants like
    ``するべき/予定/はず::.こと::``). The markers are an artefact of the
    upstream parser and not meaningful here, so we unwrap them wherever they
    appear.
    """
    return _GLOSS_COLON_WRAPPER.sub(lambda m: m.group(1), text).strip()


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
    """Parse the NINJAL lexicon TSV into a list of unverified ``Entry`` objects.

    Lemmas with runs of attachment markers (e.g. ``a==``) are normalised to a
    single marker, with the raw form preserved as an allomorph. Multiple rows
    that collapse onto the same canonical lemma are merged in-place
    (frequencies summed, glosses unioned).
    """
    by_lemma: dict[str, Entry] = {}
    order: list[str] = []
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            raw_lemma = (row.get("morpheme") or "").strip()
            if not raw_lemma:
                continue
            gloss_en = _clean_gloss(row.get("primary_gloss_en") or "")
            gloss_jp = _clean_gloss(row.get("primary_gloss_jp") or "")
            if not gloss_en and not gloss_jp:
                continue
            lemma = _normalise_attachment_markers(raw_lemma)
            variants = _split_variants(row.get("raw_morpheme_variants") or "")
            if raw_lemma != lemma and raw_lemma not in variants:
                variants.append(raw_lemma)
            bound, morph_type = _classify(lemma, gloss_en)
            freq = int(row.get("occurrence_count") or 0)
            existing = by_lemma.get(lemma)
            if existing is not None:
                existing.frequency += freq
                for variant in variants:
                    if variant and variant not in existing.allomorphs:
                        existing.allomorphs.append(variant)
                if gloss_en and gloss_en not in existing.glosses_en:
                    existing.glosses_en.append(gloss_en)
                if gloss_jp and gloss_jp not in existing.glosses_jp:
                    existing.glosses_jp.append(gloss_jp)
                continue
            by_lemma[lemma] = Entry(
                id=f"ninjal:{lemma}",
                lemma=lemma,
                allomorphs=variants,
                category="",
                bound=bound,
                morph_type=morph_type,
                base_frame=None,
                rules=[],
                glosses_en=[gloss_en] if gloss_en else [],
                glosses_jp=[gloss_jp] if gloss_jp else [],
                sources=["NINJALCorpus"],
                frequency=freq,
                verified=False,
                notes=row.get("normalization_notes", ""),
            )
            order.append(lemma)
    return [by_lemma[key] for key in order]


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


def _norm_gloss(text: str) -> str:
    return text.strip().lower().rstrip("?")


def _glosses_overlap(seed: Entry, candidate: Entry) -> bool:
    """Are the seed and candidate plausibly the same morpheme by gloss?

    Used to gate fuzzy bare-form merges. We only require the candidate's
    primary EN gloss to match *some* gloss the seed carries (case- and
    ``?``-stripped). When the seed has no English gloss the check is
    permissive (returns True) because there's nothing to compare against.
    """
    if not candidate.glosses_en:
        return False
    seed_glosses = {_norm_gloss(g) for g in seed.glosses_en if g}
    if not seed_glosses:
        return True
    cand_primary = _norm_gloss(candidate.glosses_en[0])
    return cand_primary in seed_glosses


def merge_with_seed(seed: list[Entry], ninjal: list[Entry]) -> list[Entry]:
    """Merge NINJAL candidates with curated seed entries.

    Match priority:

    1. Exact lemma match (always merges).
    2. Curator-declared allomorph match (always merges — the curator has
       explicitly stated this is the same morpheme).
    3. Bare-form aliasing (e.g. NINJAL ``e`` → seed ``-e``): merges only
       when the candidate's primary English gloss overlaps with the seed's,
       so distinct morphemes that happen to share a bare form (the ``ka``
       particle vs the ``-ka`` causative; ``e`` POSS vs ``-e`` CAUS) stay
       separate.

    Where a merge happens, the NINJAL frequency is folded into the seed but
    the curated valency/category/glosses are preserved.
    """
    exact_index: dict[str, Entry] = {}
    fuzzy_index: dict[str, Entry] = {}
    for entry in seed:
        exact_index.setdefault(entry.lemma, entry)
        # Curator-declared allomorphs match exactly — they're explicit.
        for variant in entry.allomorphs:
            if variant != entry.lemma:
                exact_index.setdefault(variant, entry)
        # Marker-stripped forms (e.g. "-e" → "e", "-te" → "te") are fuzzy
        # aliases: gloss must overlap before they merge.
        for form in (entry.lemma, *entry.allomorphs):
            bare = form.strip("-=")
            if bare and bare not in exact_index:
                fuzzy_index.setdefault(bare, entry)

    def _resolve(candidate: Entry) -> Entry | None:
        if candidate.lemma in exact_index:
            return exact_index[candidate.lemma]
        seed_entry = fuzzy_index.get(candidate.lemma)
        if seed_entry is not None and _glosses_overlap(seed_entry, candidate):
            return seed_entry
        return None

    merged: list[Entry] = list(seed)
    for candidate in ninjal:
        existing = _resolve(candidate)
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
