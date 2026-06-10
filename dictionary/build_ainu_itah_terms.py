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

# Morphological analysis produced by ainu-morpheme-database/sakhalin/analyze.py
# (closed-lexicon segmentation of every headword). Optional inputs: the build
# degrades to a flat dictionary when they are absent.
ANALYSIS = (
    REPO_ROOT.parent
    / "ainu-morpheme-database" / "sakhalin" / "output" / "sakhalin-analysis.json"
)
AFFIXES = REPO_ROOT.parent / "ainu-morpheme-database" / "sakhalin" / "affixes.json"
# The linguist's per-lemma verdicts over the automatic analysis:
# { "<lemma>": "accept" | "reject" } — "accept" demotes despite flags,
# "reject" blocks a demotion the analyzer proposed.
OVERRIDES = REPO_ROOT / "dictionary" / "input" / "sakhalin" / "analysis_overrides.json"

# Sakhalin↔Hokkaido same-etymon correspondences (auto layer + curated layer),
# built by ainu-morpheme-database/sakhalin/build_correspondences.py. Optional.
CORR_AUTO = (
    REPO_ROOT.parent
    / "ainu-morpheme-database" / "sakhalin" / "output" / "correspondences.json"
)
CORR_CURATED = (
    REPO_ROOT.parent / "ainu-morpheme-database" / "sakhalin" / "correspondences_curated.json"
)

KEY_ORDER = [
    "lemma", "ja", "en", "ru", "poses",
    "frequency", "frequencyRolled", "freqSource",
    "structure", "forms",
    "hokkaido", "hokkaidoNot",
    "cognates", "noncognates",
]

# affix category (in affixes.json) → the form-type badge the site shows
FORM_TYPE_BY_CATEGORY = {
    "possessive": "possessed",
    "postposition": "case",
    "personal": "personal",
    "plural": "plural",
    "collective": "collective",
    "valency": "valency",
    "negation": "valency",
}


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
) -> tuple[int, str | None]:
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
        return 0, None
    if norm.strip("-=") != norm or nb in clitic_bares:
        # sources vary in marker choice for the same morpheme (``an=`` vs the
        # hyphen-spelled ``an-``), so a marked lemma sums both marker spellings
        alt = norm.replace("=", "-") if "=" in norm else norm.replace("-", "=")
        n = 0
        for v in {norm, alt}:
            n += token_freq.get(v, 0) or token_freq.get(mp_to_np(v), 0)
        return n, ("marker" if n else None)
    n = (
        lemma_freq.get(nb, 0)
        or lemma_freq.get(b, 0)
        or lemma_freq.get(mp_to_np(nb), 0)
        or lemma_freq.get(mp_to_np(b), 0)
    )
    return n, None


def flatten_forms(terms: list[dict]) -> list[dict]:
    """Re-expand nested ``forms`` back into top-level rows so a rerun is
    idempotent: the analysis join below re-decides every demotion from scratch
    against the current analysis + overrides, and demoted rows keep their own
    curated glosses (a sub-entry is a full row, just displayed nested)."""
    out: list[dict] = []
    for t in terms:
        forms = t.pop("forms", None) or []
        t.pop("frequencyRolled", None)
        t.pop("structure", None)
        t.pop("hokkaido", None)
        t.pop("hokkaidoNot", None)
        out.append(t)
        for f in forms:
            row = {
                k: f[k]
                for k in ("lemma", "ja", "en", "ru", "poses", "frequency",
                          "cognates", "noncognates", "freqSource")
                if k in f
            }
            out.append(row)
    return out


_EN_STOPWORDS = frozenset(
    "to the a an of in on at for one's someone's be is are do does it その ~".split()
)


def glosses_cohere(form_row: dict, root_row: dict) -> bool:
    """A demotion is only trusted when the word-form's gloss visibly contains
    its root's meaning (``kemaha`` 足（全体） under ``kema`` 足 — yes;
    ``kihci`` ～をする under the junk homophone ``ki`` 'thing' — no). The
    audit measured the no-coherence failure mode at ~30% of Tier-2, so
    incoherent pairs go to the review queue instead of demoting."""
    # Japanese: share a kanji/katakana character or one gloss contains the other
    for fj in form_row.get("ja") or []:
        for rj in root_row.get("ja") or []:
            if rj and fj and (rj in fj or fj in rj):
                return True
            if set(filter(lambda c: ord(c) > 0x2E80, fj)) & set(
                filter(lambda c: ord(c) > 0x2E80, rj)
            ):
                return True
    # English: shared content token
    def tokens(rows):
        out = set()
        for g in rows or []:
            for w in g.lower().replace("~", " ").split():
                w = w.strip(".,;()'\"-")
                if w and w not in _EN_STOPWORDS:
                    out.add(w)
        return out

    if tokens(form_row.get("en")) & tokens(root_row.get("en")):
        return True
    return False


def apply_analysis(terms: list[dict]) -> tuple[list[dict], str]:
    """Join the morphological analysis: demote clean Tier-2 word-forms into
    their base entry's ``forms``, attach Tier-3 ``structure``, and compute
    ``frequencyRolled``. Returns (new terms list, stats line)."""
    if not ANALYSIS.exists():
        return terms, "analysis: not present (flat dictionary)"
    analysis = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    if isinstance(analysis, dict):  # tolerate {lemma: record} maps
        analysis = list(analysis.values())
    affix_cat: dict[str, str] = {}
    if AFFIXES.exists():
        for a in json.loads(AFFIXES.read_text(encoding="utf-8")):
            affix_cat[a["id"]] = a.get("category", "")
    overrides: dict[str, str] = {}
    if OVERRIDES.exists():
        overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))

    rows_by_lemma: dict[str, list[dict]] = {}
    for t in terms:
        rows_by_lemma.setdefault(t["lemma"], []).append(t)

    demoted: set[int] = set()  # id() of rows pulled under a parent
    n_demoted = n_struct = n_skipped = n_ambig = 0
    for rec in analysis:
        lemma = rec.get("lemma")
        verdict = overrides.get(lemma)
        if verdict == "reject":
            n_skipped += 1
            continue
        parse = rec.get("parse") or []
        pairs = [[p.get("m", ""), p.get("gloss", "")] for p in parse]
        rows = rows_by_lemma.get(lemma, [])
        if rec.get("tier") == 2:
            # Proclitic-containing parses are the empirically-bad zone (the
            # analyzer happily reads the real verb ``anpa`` as ``an=+pa`` and
            # the noun ``kuru`` as ``ku=+ru``), so only suffix-only parses
            # (possessive, collective, postpositional, derivational) demote
            # automatically; anything with a proclitic waits for an explicit
            # "accept" override (e.g. genuine ``kucise`` = ``ku=+cise``).
            has_proclitic = any(p.get("m", "").endswith("=") for p in parse)
            clean = (not rec.get("flags") and not has_proclitic) or verdict == "accept"
            root = rec.get("root")
            root_rows_pre = rows_by_lemma.get(root, [])
            if (
                clean
                and verdict != "accept"
                and rows
                and root_rows_pre
                and not glosses_cohere(rows[0], root_rows_pre[0])
            ):
                # form and root glosses don't visibly relate (or either is
                # unglossed) — hold for the linguist instead of auto-nesting
                n_skipped += 1
                continue
            root_rows = rows_by_lemma.get(root, [])
            if not (clean and rows and root_rows and root != lemma):
                n_skipped += 1
                continue
            if len(rows) > 1:
                # several sense rows share this surface — too ambiguous to
                # demote automatically; leave for the override file
                n_ambig += 1
                continue
            row, parent = rows[0], root_rows[0]
            ftype = "valency"
            for p in parse:
                cat = affix_cat.get(p.get("id", ""))
                if cat in FORM_TYPE_BY_CATEGORY:
                    # outermost affix wins: keep overwriting in parse order
                    ftype = FORM_TYPE_BY_CATEGORY[cat]
            form = dict(row)
            form["analysis"] = pairs
            form["type"] = ftype
            parent.setdefault("forms", []).append(form)
            demoted.add(id(row))
            n_demoted += 1
        elif rec.get("tier") == 3 and pairs and rows:
            # structure is display-only, but don't decorate junk: require a
            # flag-free parse and a glossed row (rows with no ja/en are
            # themselves garbage pending curation), unless overridden
            row = rows[0]
            glossed = row.get("ja") or row.get("en")
            if (not rec.get("flags") and glossed) or verdict == "accept":
                row["structure"] = pairs
                n_struct += 1
            else:
                n_skipped += 1

    kept = [t for t in terms if id(t) not in demoted]
    for t in kept:
        forms = t.get("forms")
        if forms:
            forms.sort(key=lambda f: -f.get("frequency", 0))
            t["frequencyRolled"] = t.get("frequency", 0) + sum(
                f.get("frequency", 0) for f in forms
            )
    return kept, (
        f"analysis: demoted {n_demoted} forms, {n_struct} structures, "
        f"skipped {n_skipped} (flags/overrides/missing), {n_ambig} ambiguous"
    )


def apply_correspondences(terms: list[dict]) -> str:
    """Attach typed Hokkaido same-etymon correspondences to entries. A pair
    matched on a nested form attaches to the base row with the form noted."""
    pairs: list[tuple[dict, bool]] = []  # (pair, curated)
    if CORR_AUTO.exists():
        pairs += [(p, False) for p in json.loads(CORR_AUTO.read_text(encoding="utf-8"))]
    negatives: list[dict] = []
    if CORR_CURATED.exists():
        cur = json.loads(CORR_CURATED.read_text(encoding="utf-8"))
        pairs += [(p, True) for p in cur.get("pairs", [])]
        negatives = cur.get("negativePairs", [])
    if not pairs:
        return "correspondences: not present"

    rows_by_lemma: dict[str, dict] = {}
    for t in terms:
        rows_by_lemma.setdefault(t["lemma"], t)

    attached = 0
    seen: set[tuple[str, str, str]] = set()
    for p, curated in pairs:
        s = p.get("sakhalin") or {}
        target = s.get("baseLemma") if s.get("isForm") else s.get("lemma")
        row = rows_by_lemma.get(target or "")
        if row is None:
            continue
        h_lemma = (p.get("hokkaido") or {}).get("lemma", "")
        key = (target, h_lemma, p.get("type", ""))
        if not h_lemma or key in seen:
            continue
        seen.add(key)
        item: dict = {"lemma": h_lemma, "type": p.get("type", "")}
        if p.get("ruleIds"):
            item["rules"] = p["ruleIds"]
        if curated:
            item["curated"] = True
        elif p.get("confidence") is not None:
            item["conf"] = p["confidence"]
        if s.get("isForm"):
            item["form"] = s.get("lemma")
        row.setdefault("hokkaido", []).append(item)
        attached += 1
    for n in negatives:
        row = rows_by_lemma.get(n.get("sakhalin", ""))
        if row is not None and n.get("hokkaido"):
            row.setdefault("hokkaidoNot", []).append(n["hokkaido"])
    for t in terms:
        if t.get("hokkaido"):
            t["hokkaido"].sort(
                key=lambda i: (not i.get("curated"), -(i.get("conf") or 0), i["lemma"])
            )
    return f"correspondences: attached {attached} pairs, {len(negatives)} negatives"


def main() -> int:
    terms = json.loads(EXTENDED.read_text(encoding="utf-8"))
    terms = flatten_forms(terms)

    # 0. drop byte-identical duplicate rows (the curated store accumulated a few
    #    exact repeats, e.g. ``taa``(vt) twice with identical glosses). Rows that
    #    differ in ANY curated field — ``taa`` vt vs adn, ``sah`` vt vs vi — are
    #    distinct senses/homographs, NOT duplicates, and are kept.
    seen_rows: set[str] = set()
    deduped: list[dict] = []
    dropped = 0
    for t in terms:
        key = json.dumps(
            {k: t.get(k) or [] for k in KEY_ORDER if k != "frequency"},
            ensure_ascii=False,
            sort_keys=True,
        )
        if key in seen_rows:
            dropped += 1
            continue
        seen_rows.add(key)
        deduped.append(t)
    terms = deduped

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
        corpus, source = sakhalin_count(t["lemma"], lemma_freq, token_freq, clitic_bares)
        new = corpus if corpus else old
        if new != old:
            changed += 1
            if new > old:
                raised += 1
        elif corpus == 0 and old > 0:
            kept += 1
        t["frequency"] = new
        if source == "marker" and new == corpus:
            t["freqSource"] = "marker"
        else:
            t.pop("freqSource", None)

    # 2. merge curated new headwords
    added = 0
    for nt in json.loads(NEW_TERMS.read_text(encoding="utf-8")):
        lemma = nt["lemma"]
        if lemma in index or mp_to_np(normalize(bare(lemma))) in norm_index:
            continue
        count, source = sakhalin_count(lemma, lemma_freq, token_freq, clitic_bares)
        new_row = {
            "lemma": lemma,
            "ja": nt.get("ja", []),
            "en": nt.get("en", []),
            "ru": nt.get("ru", []),
            "poses": nt.get("poses", []),
            "frequency": count,
            "cognates": nt.get("cognates", []),
            "noncognates": nt.get("noncognates", []),
        }
        if source == "marker":
            new_row["freqSource"] = "marker"
        terms.append(new_row)
        index.add(lemma)
        norm_index.add(mp_to_np(normalize(bare(lemma))))
        added += 1

    # 2b. morphological analysis join (nest word-forms, attach structures)
    terms, analysis_stats = apply_analysis(terms)

    # 2c. Hokkaido correspondence join
    corr_stats = apply_correspondences(terms)

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
        f"terms: {len(terms)} (+{added} new, -{dropped} duplicate rows)\n"
        f"frequencies changed: {changed} (raised {raised}); "
        f"kept prior value (0 in corpus): {kept}\n"
        f"{analysis_stats}\n"
        f"{corr_stats}\n"
        f"wrote: {EXTENDED}\n       {SITE_DATA}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
