"""Overlay ainu-corpora frequencies onto morpheme database entries.

The NINJAL ingest seeds each ``Entry`` with a ``frequency`` taken from the
glossed corpus's occurrence count (~1.4 k morphemes covered). The Ainu
corpora repository (``../ainu-corpora``) is an order of magnitude larger,
so we overlay its token / lemma counts on top of the NINJAL number:

- First try the surface token table (``token_frequency.tsv``), looking up
  ``entry.lemma`` and any allomorphs. Surface tokens still carry the
  attachment markers (``=an``, ``a=``, ``-e``, ``ko-``), which is how
  affixes are stored in the morpheme database.
- If no surface match is found, fall back to the marker-stripped lemma
  table (``lemma_frequency.tsv``), keyed by ``entry.lemma.strip("-=")``.
  This is what catches inflected variants the surface table doesn't list.

Whatever we find replaces ``entry.frequency``. The source attribution gets
an ``"ainu-corpora"`` entry alongside ``"NINJALCorpus"`` (when applicable)
so the UI can show where the number came from.
"""

from __future__ import annotations

import csv
from pathlib import Path

from morpheme_db.schema import Entry


def load_frequency_table(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    out: dict[str, int] = {}
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            form = (row.get("form") or "").strip()
            if not form:
                continue
            try:
                out[form] = int(row.get("frequency") or 0)
            except ValueError:
                continue
    return out


def apply_corpora_frequencies(
    entries: list[Entry],
    token_freq: dict[str, int],
    lemma_freq: dict[str, int],
) -> dict[str, int]:
    """Overlay ainu-corpora counts on each entry, but never go lower.

    Bound affixes (``-e``, ``yay-``, ``si-`` …) are usually written attached
    to their host in the corpus, so the surface tokeniser only sees them
    when an author chose to write the hyphen — which is rare. The NINJAL
    glossed corpus is morphologically segmented and gives a much truer
    count for those. So when the existing ``frequency`` (typically from
    NINJAL) is larger than what we'd compute from ainu-corpora, we keep
    the NINJAL number. The ``ainu-corpora`` source is still recorded
    whenever a non-zero match exists, so users can see we did look there.
    """
    counters = {
        "matched_token": 0,
        "matched_lemma": 0,
        "unmatched": 0,
        "replaced": 0,
        "kept_existing": 0,
    }
    for entry in entries:
        keys = [entry.lemma, *entry.allomorphs]
        found: int | None = None
        match_kind: str | None = None
        for key in keys:
            if key and key in token_freq:
                found = token_freq[key]
                match_kind = "matched_token"
                break
        if found is None:
            bare = entry.lemma.strip("-=")
            if bare and bare in lemma_freq:
                found = lemma_freq[bare]
                match_kind = "matched_lemma"

        if found is None:
            counters["unmatched"] += 1
            continue

        counters[match_kind] += 1
        if "ainu-corpora" not in entry.sources:
            entry.sources.append("ainu-corpora")

        if found > entry.frequency:
            entry.frequency = found
            counters["replaced"] += 1
        else:
            counters["kept_existing"] += 1
    return counters


__all__ = ["apply_corpora_frequencies", "load_frequency_table"]
