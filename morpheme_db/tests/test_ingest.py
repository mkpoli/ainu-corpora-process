"""Tests for the NINJAL ingest and seed merge."""

from __future__ import annotations

from pathlib import Path

from morpheme_db.ingest_ninjal import _classify, _split_variants, ingest_ninjal_lexicon, merge_with_seed
from morpheme_db.schema import Entry, load_entries


SEED_PATH = Path(__file__).resolve().parents[1] / "seed" / "morphemes.json"


def test_classify_detects_prefix_suffix_clitic() -> None:
    assert _classify("-e", "CAUS") == (True, "suffix")
    assert _classify("si-", "REFL") == (True, "prefix")
    assert _classify("a=", "4.A=") == (True, "clitic")
    assert _classify("nukar", "see") == (False, "root")


def test_split_variants_drops_counts() -> None:
    assert _split_variants("a= (4643) || “a= (2)") == ["a=", "“a="]
    assert _split_variants("") == []
    assert _split_variants("plain") == ["plain"]


def test_ingest_ninjal_round_trip(tmp_path: Path) -> None:
    tsv = tmp_path / "ninjal_morpheme_lexicon.tsv"
    tsv.write_text(
        "morpheme\traw_morpheme_variants\tnormalization_notes\toccurrence_count\t"
        "sentence_count\tprimary_gloss_en\tprimary_gloss_jp\tgloss_en_variants\t"
        "gloss_jp_variants\texample_unit_morpheme\texample_unit_gloss_en\t"
        "example_unit_gloss_jp\texample_story_sentence_id\texample_translation_en\t"
        "example_translation_jp\n"
        "nukar\tnukar (10)\t\t10\t8\tsee\t～を見る\tsee (10)\t～を見る (10)\tnukar\tsee\t～を見る\tK00.001\tx\ty\n"
        "-e\t-e (5)\t\t5\t5\tCAUS\t～させる\tCAUS (5)\t～させる (5)\t-e\tCAUS\t～させる\tK00.002\tx\ty\n",
        encoding="utf-8",
    )
    entries = ingest_ninjal_lexicon(tsv)
    assert len(entries) == 2
    by_lemma = {e.lemma: e for e in entries}
    assert by_lemma["nukar"].frequency == 10
    assert by_lemma["nukar"].morph_type == "root"
    assert by_lemma["-e"].morph_type == "suffix"
    assert by_lemma["-e"].bound is True


def test_merge_preserves_curated_valency(tmp_path: Path) -> None:
    seed = load_entries(SEED_PATH)
    nukar_seed = next(e for e in seed if e.lemma == "nukar")
    assert nukar_seed.base_frame is not None
    original_arity = nukar_seed.base_frame.arity

    fake_ninjal = [
        Entry(
            id="ninjal:nukar",
            lemma="nukar",
            category="",
            base_frame=None,
            frequency=42,
            sources=["NINJALCorpus"],
            glosses_en=["look-at"],
        )
    ]
    merged = merge_with_seed(seed, fake_ninjal)
    nukar_merged = next(e for e in merged if e.lemma == "nukar")
    assert nukar_merged.base_frame is not None
    assert nukar_merged.base_frame.arity == original_arity
    assert nukar_merged.frequency == 42
    assert "NINJALCorpus" in nukar_merged.sources
