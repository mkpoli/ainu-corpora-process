"""Tests for form/POS normalisation — the clustering backbone."""

from __future__ import annotations

from lexeme_db.normalize import (
    form_key,
    has_bound_marker,
    normalize_pos,
    pos_from_definition,
)


def test_form_key_strips_glottal_and_markers():
    # 中川 writes glottal-initial a as a'; 萱野/田村 use =/- markers.
    assert form_key("a'") == "a"
    assert form_key("a'=") == "a"
    assert form_key("=an") == "an"
    assert form_key("-pa") == "pa"
    assert form_key("sapa") == "sapa"


def test_form_key_strips_accent_and_sense_numbers():
    assert form_key("sápa") == "sapa"
    assert form_key("poro²") == "poro"
    assert form_key("TÚ-") == "tu"


def test_cross_source_forms_share_a_key():
    # The whole point: divergent source spellings collapse to one key.
    assert form_key("a'") == form_key("a") == form_key("á")
    assert form_key("=an") == form_key("an")


def test_has_bound_marker():
    assert has_bound_marker("=an")
    assert has_bound_marker("-pa")
    assert has_bound_marker("ko-")
    assert not has_bound_marker("sapa")


def test_normalize_pos_known_labels():
    assert normalize_pos("動1") == "vi"
    assert normalize_pos("動2") == "vt"
    assert normalize_pos("名") == "n"
    assert normalize_pos("人接") == "pers"
    assert normalize_pos("接尾") == "sfx"
    assert normalize_pos("慣用句") == "idiom"


def test_normalize_pos_unknown():
    assert normalize_pos("") == ""
    assert normalize_pos("謎ラベル") == ""


def test_pos_from_definition_brackets():
    assert pos_from_definition("【接尾】[名詞の所属形形成]…") == "sfx"
    assert pos_from_definition("アン 【=an】私〔人称接辞〕．") == "pers"
    assert pos_from_definition("ターラ 【tara】〜に，…") == ""
