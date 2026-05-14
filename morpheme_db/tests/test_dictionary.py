"""Tests for the combined-dictionary enrichment step."""

from __future__ import annotations

from morpheme_db.ingest_dictionary import _pick_primary, enrich_entries
from morpheme_db.schema import Entry


def test_pick_primary_prefers_specific_verb_tag() -> None:
    primary, alts = _pick_primary(["v", "vt"])
    assert primary == "vt"
    assert "v" in alts


def test_pick_primary_keeps_alternatives() -> None:
    primary, alts = _pick_primary(["n", "v", "pron"])
    # 'v' is ranked higher than 'n' in PREFERENCE.
    assert primary == "v"
    assert "n" in alts and "pron" in alts


def test_enrich_fills_empty_category_but_preserves_curated() -> None:
    curated = Entry(id="nukar", lemma="nukar", category="vt", verified=True)
    candidate = Entry(id="ninjal:foo", lemma="foo", category="")
    pos = {"nukar": ["v"], "foo": ["n", "v"]}
    gl = {"foo": ["bar"]}
    enriched = enrich_entries([curated, candidate], pos, gl)
    assert enriched[0].category == "vt"  # curated wins
    assert enriched[1].category == "v"
    assert enriched[1].glosses_jp == ["bar"]
    assert "Dictionary" in enriched[1].sources


def test_enrich_strips_clitic_markers_for_dictionary_lookup() -> None:
    candidate = Entry(id="ninjal:=an", lemma="=an", category="")
    pos = {"an": ["v"]}
    enriched = enrich_entries([candidate], pos, {})
    assert enriched[0].category == "v"


def test_enrich_upgrades_root_to_prefix_when_dictionary_says_so() -> None:
    candidate = Entry(id="ninjal:p", lemma="p", category="", morph_type="root")
    # ``p`` is a nominaliser suffix in the combined dictionary, with no
    # competing verbal POS — so ``sfx`` wins and the morph_type / bound flags
    # are pulled across.
    pos = {"p": ["sfx"]}
    enriched = enrich_entries([candidate], pos, {})
    assert enriched[0].category == "sfx"
    assert enriched[0].morph_type == "suffix"
    assert enriched[0].bound is True


def test_enrich_keeps_pfx_in_alternatives_when_verb_wins() -> None:
    candidate = Entry(id="ninjal:e", lemma="e", category="", morph_type="root")
    pos = {"e": ["pfx", "v"]}
    enriched = enrich_entries([candidate], pos, {})
    # ``v`` is the more specific primary (vs structural ``pfx``), but ``pfx``
    # should still be visible as an alternative.
    assert enriched[0].category == "v"
    assert "pfx" in enriched[0].category_alt
