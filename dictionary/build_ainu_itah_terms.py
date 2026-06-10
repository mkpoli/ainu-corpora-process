"""Refresh the Sakhalin (aynu-itah) dictionary from the rebuilt corpus.

This is an incremental update step layered on top of the curated terms produced
by ``generate_karahuto_data.ipynb``. It does three things, all keyed off the
*current* corpus frequency table (``corpus/output/ainu_corpora/lemma_frequency.tsv``,
which now reflects the rebuilt ``../ainu-corpora/data.jsonl`` including the new
Tamura ELPR A2 / elpr-a2 Sakhalin material):

1. Recomputes every existing entry's ``frequency`` as its **Sakhalin-only**
   count (the ``sakhalin:N`` slice of ``dialect_breakdown``). This matches the
   site's existing semantics (it has always shown Sakhalin frequency) while
   picking up the freshly added material.
2. Merges hand-curated, dictionary-sourced new headwords from
   ``input/sakhalin/new_terms_from_corpus_2026.json`` (well-attested Sakhalin
   forms that were missing; glossed via the ainu-dictionaries collection).
3. Emits both the canonical ``output/ainu-itah/sakhalin-terms-extended.json``
   and the site-ready ``data.json`` (tab-indented, empty arrays stripped,
   matching the format the SvelteKit ``DictionaryTable`` consumes).

Run: ``uv run python dictionary/build_ainu_itah_terms.py``
"""

from __future__ import annotations

import csv
import json
from collections import OrderedDict
from pathlib import Path

from utils.lemmatize import normalize

REPO_ROOT = Path(__file__).resolve().parents[1]
EXTENDED = REPO_ROOT / "dictionary" / "output" / "ainu-itah" / "sakhalin-terms-extended.json"
# ``lemma_frequency.tsv`` has attachment markers stripped (``=an``/``an=``/``an``
# all collapse to ``an``); ``token_frequency.tsv`` preserves them, which is the
# only way to disaggregate homographic clitics. See ``sakhalin_count``.
FREQ = REPO_ROOT / "corpus" / "output" / "ainu_corpora" / "lemma_frequency.tsv"
TOKEN_FREQ = REPO_ROOT / "corpus" / "output" / "ainu_corpora" / "token_frequency.tsv"
NEW_TERMS = REPO_ROOT / "dictionary" / "input" / "sakhalin" / "new_terms_from_corpus_2026.json"
SITE_DATA = REPO_ROOT.parent / "aynu-itah" / "src" / "lib" / "data.json"

KEY_ORDER = ["lemma", "ja", "en", "ru", "poses", "frequency", "cognates", "noncognates"]


def bare(lemma: str) -> str:
    return lemma.strip("-=")


def mp_to_np(word: str) -> str:
    """Sakhalin reconciliation: the corpus stores phonetic ``mp`` while the
    dictionary uses morphophonemic ``np`` (e.g. corpus ``humpa`` ↔ dict
    ``hunpa``). Mirrors ``generate_karahuto_data.ipynb``'s ``mp``→``np`` step."""
    return word.replace("mp", "np")


def load_sakhalin_table(path: Path) -> dict[str, int]:
    """form → Sakhalin count, with an ``mp``→``np`` alias so np-spelled
    dictionary lemmas match the corpus's mp-spelled forms. Works for either the
    marker-stripped ``lemma_frequency.tsv`` or the marker-preserving
    ``token_frequency.tsv`` (the ``form`` column differs; the parse is the same)."""
    freq: dict[str, int] = {}
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            sakh = 0
            for part in row["dialect_breakdown"].split("|"):
                if part.startswith("sakhalin:"):
                    sakh = int(part.split(":", 1)[1])
            if not sakh:
                continue
            form = row["form"]
            freq[form] = sakh
            alias = mp_to_np(form)
            if alias != form:
                # don't let an alias clobber a real distinct form
                freq[alias] = max(freq.get(alias, 0), sakh)
    return freq


def sakhalin_count(
    lemma: str,
    lemma_freq: dict[str, int],
    token_freq: dict[str, int],
    clitic_bares: frozenset[str],
) -> int:
    # A lemma whose surface is itself a clitic (marked ``=an`` / ``an=`` / ``ku=``)
    # or collides with one (the bare verb ``an`` vs the proclitic ``an=`` and the
    # enclitic ``=an``) must take its OWN exact surface count from the marker-
    # PRESERVING token table. The bare ``lemma_frequency.tsv`` strips markers and
    # so collapses all of them onto a single ``an`` total (1528) — the homograph
    # bug. Ordinary lemmas — including content verbs that merely *host* an enclitic
    # (``okay=`` is still the verb ``okay``) — keep the bare aggregate so they are
    # not under-counted.
    norm = normalize(lemma)
    b = bare(lemma)
    nb = normalize(b)
    if not nb:
        # a bare-marker lemma like ``=`` would otherwise match tokenization
        # artifacts in the token table
        return 0
    if norm.strip("-=") != norm or nb in clitic_bares:
        return token_freq.get(norm, 0) or token_freq.get(mp_to_np(norm), 0)
    return (
        lemma_freq.get(nb, 0)
        or lemma_freq.get(b, 0)
        or lemma_freq.get(mp_to_np(nb), 0)
        or lemma_freq.get(mp_to_np(b), 0)
    )


def main() -> int:
    terms = json.loads(EXTENDED.read_text(encoding="utf-8"))

    lemma_freq = load_sakhalin_table(FREQ)
    token_freq = load_sakhalin_table(TOKEN_FREQ)
    # Bare forms that are *also* attested as a clitic lemma (so a same-spelled
    # content word, e.g. verb ``an``, must be disaggregated from ``=an`` / ``an=``
    # rather than inherit their collapsed total).
    clitic_bares = frozenset(
        normalize(bare(t["lemma"]))
        for t in terms
        if normalize(t["lemma"]).strip("-=") != normalize(t["lemma"])
    )
    # np-aware index of existing lemmas (so we never add an mp-spelled duplicate
    # of an np-spelled headword, and vice versa)
    index = {t["lemma"] for t in terms}
    norm_index = {mp_to_np(normalize(bare(t["lemma"]))) for t in terms}

    # 1. refresh existing frequencies (Sakhalin-only). Fall back to the prior
    #    value when the rebuilt corpus has no Sakhalin token for the lemma, so
    #    rare proper nouns / loans keep their existing ranking (no regressions).
    changed = raised = kept = 0
    for t in terms:
        old = t.get("frequency", 0)
        corpus = sakhalin_count(t["lemma"], lemma_freq, token_freq, clitic_bares)
        new = corpus if corpus else old
        if new != old:
            changed += 1
            if new > old:
                raised += 1
        elif corpus == 0 and old > 0:
            kept += 1
        t["frequency"] = new

    # 2. merge curated new headwords
    added = 0
    for nt in json.loads(NEW_TERMS.read_text(encoding="utf-8")):
        lemma = nt["lemma"]
        if lemma in index or mp_to_np(normalize(bare(lemma))) in norm_index:
            continue
        terms.append({
            "lemma": lemma,
            "ja": nt.get("ja", []),
            "en": nt.get("en", []),
            "ru": nt.get("ru", []),
            "poses": nt.get("poses", []),
            "frequency": sakhalin_count(lemma, lemma_freq, token_freq, clitic_bares),
            "cognates": nt.get("cognates", []),
            "noncognates": nt.get("noncognates", []),
        })
        index.add(lemma)
        norm_index.add(mp_to_np(normalize(bare(lemma))))
        added += 1

    # 3a. canonical extended file (compact, all keys)
    EXTENDED.write_text(
        json.dumps(terms, ensure_ascii=False), encoding="utf-8"
    )

    # 3b. site data.json (tab indent, empty arrays stripped, stable key order)
    site_terms = []
    for t in terms:
        ordered = OrderedDict()
        for k in KEY_ORDER:
            v = t.get(k)
            if v == [] or v is None:
                continue
            ordered[k] = v
        site_terms.append(ordered)
    # Emit compact (single line); the aynu-itah repo's prettier pass formats it
    # canonically — short entries collapse to one line, long ones expand — which
    # matches the committed layout and keeps the diff to genuine content changes.
    SITE_DATA.write_text(
        json.dumps(site_terms, ensure_ascii=False), encoding="utf-8"
    )

    print(
        f"terms: {len(terms)} (+{added} new)\n"
        f"frequencies changed: {changed} (raised {raised}); "
        f"kept prior value (0 in corpus): {kept}\n"
        f"wrote: {EXTENDED}\n       {SITE_DATA}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
