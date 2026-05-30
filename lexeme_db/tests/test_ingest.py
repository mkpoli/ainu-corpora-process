"""Tests for the ingest helpers — sense splitting and gloss cleanup."""

from __future__ import annotations

from lexeme_db.ingest import _clean_gloss, _split_senses


def test_split_senses_circled():
    defn = "①（話相手を含む）われわれが。 ②あなたが（女性から成人男子へ）。"
    senses = _split_senses(defn)
    assert [sid for sid, _ in senses] == ["1", "2"]
    assert "われわれが" in senses[0][1]


def test_split_senses_none_when_unmarked():
    assert _split_senses("座る；きちんと座る意。") == []


def test_clean_gloss_drops_brackets_and_examples():
    # Leading 【…】 POS bracket and a trailing Ainu example are removed.
    g = _clean_gloss("【接尾】…が優れている。 kam カㇺ 肉")
    assert "が優れている" in g
    assert "kam" not in g


def test_clean_gloss_strips_number_markers():
    g = _clean_gloss("（単）ロㇰ（複）。座る")
    # The 単/複 paren markers go; we keep a short CJK gloss.
    assert "単" not in g
