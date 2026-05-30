"""Read the pilot dictionaries into a common :class:`SourceEntry` shape.

Pilot sources (all read straight from ``ainu-dictionaries``):

* ``1995_Nakagawa_Ainu-Chitose-Dialect-Dictionary`` — Chitose (千歳). Clean
  ``kana / latn / pos / definition / page`` columns.
* ``1996_Tamura_Ainu-Saru-Dialect-Dictionary`` — Saru (沙流). ``lemma /
  translit / definition``; POS lives in a leading ``【…】`` bracket.
* ``1996_Kayano_Kayanos-Ainu-Dictionary`` — Saru (沙流). ``lemma / definition``;
  the definition opens with kana + ``【latn】`` + gloss + ``〔POS〕``.

Each reader yields :class:`SourceEntry` records with a normalised XPOS, a short
Japanese gloss, an optional sense split, and the full definition preserved for
the crosswalk. Glosses are best-effort — the load-bearing output is the link,
and the verbatim definition is always kept on the attestation.
"""

from __future__ import annotations

import csv
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from lexeme_db.normalize import normalize_pos, pos_from_definition

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")

NAKAGAWA = DICT_ROOT / "1995_Nakagawa_Ainu-Chitose-Dialect-Dictionary" / "nakagawa_terms.tsv"
TAMURA = DICT_ROOT / "1996_Tamura_Ainu-Saru-Dialect-Dictionary" / "original.tsv"
KAYANO = DICT_ROOT / "1996_Kayano_Kayanos-Ainu-Dictionary" / "kayano-entries.tsv"

# Sense bullets used by 中川 (①②③ …) and occasional (1)(2) numbering.
_CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮"
_SENSE_SPLIT_RE = re.compile(f"([{_CIRCLED}])")

_BRACKET_LEAD_RE = re.compile(r"^[\s　]*(?:【[^】]*】|〔[^〕]*〕|［[^］]*］)")
_NUMBER_PAREN_RE = re.compile(r"（[単複]）|\([単複]\)")
_KANA_LEAD_RE = re.compile(r"^[\sァ-ヴーㇰ-ㇿ・゙゚ャュョッ]+")
# An Ainu example starts with a run of Latin letters; the gloss is the CJK
# text before it. Used to clip examples off a short gloss.
_EXAMPLE_RE = re.compile(r"[A-Za-zàáèéìíòóùúÀ-Ý][A-Za-zàáèéìíòóùúÀ-Ý '=\-]{2,}")
_CITATION_TAG_RE = re.compile(r"[〔\[][A-Z][0-9A-Za-z.]+[〕\]]")


@dataclass(slots=True)
class SourceEntry:
    """One dictionary entry normalised to a common shape."""

    source: str
    dialect: str
    entry_ref: str
    latn: str
    kana: str = ""
    pos: str = ""
    pos_raw: str = ""
    gloss_jp: list[str] = field(default_factory=list)
    senses: list[tuple[str, str]] = field(default_factory=list)
    """``(sense_id, gloss_jp)`` pairs when the entry numbers senses; else []."""
    definition: str = ""


def _clean_gloss(text: str) -> str:
    """Best-effort short Japanese gloss from a definition segment."""
    s = text.strip()
    s = _BRACKET_LEAD_RE.sub("", s).strip()
    s = _NUMBER_PAREN_RE.sub("", s).strip()
    s = _CITATION_TAG_RE.sub("", s)
    # Cut at the first sentence/clause boundary.
    for sep in ("。", "；", ";", "\n"):
        idx = s.find(sep)
        if 0 <= idx <= 60:
            s = s[:idx]
            break
    # Drop a trailing Ainu example clause if one slipped in.
    m = _EXAMPLE_RE.search(s)
    if m and m.start() > 0:
        s = s[: m.start()]
    return s.strip(" 　、,:：。；;")


def _split_senses(definition: str) -> list[tuple[str, str]]:
    """Split a definition on ①②③ markers into ``(id, gloss)`` pairs."""
    parts = _SENSE_SPLIT_RE.split(definition)
    if len(parts) < 3:  # no real split
        return []
    senses: list[tuple[str, str]] = []
    # parts = [pre, '①', seg1, '②', seg2, ...]
    it = iter(parts[1:])
    n = 0
    for _marker, seg in zip(it, it):
        n += 1
        gloss = _clean_gloss(seg)
        if gloss:
            senses.append((str(n), gloss))
    return senses


def _leading_kana(text: str) -> str:
    m = _KANA_LEAD_RE.match(text.strip())
    return m.group(0).strip() if m else ""


_FIRST_BRACKET_RE = re.compile(r"[【〔]([^】〕]{1,8})[】〕]")


def _first_bracket(defn: str) -> str:
    m = _FIRST_BRACKET_RE.search(defn)
    return m.group(1) if m else ""


def _glosses_or_empty(defn: str) -> list[str]:
    g = _clean_gloss(defn)
    return [g] if g else []


def read_nakagawa(path: Path = NAKAGAWA) -> Iterator[SourceEntry]:
    source = path.parent.name
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for i, row in enumerate(reader):
            latn = (row.get("latn") or "").strip()
            if not latn:
                continue
            defn = (row.get("definition") or "").strip()
            pos_raw = (row.get("pos") or "").strip()
            senses = _split_senses(defn)
            yield SourceEntry(
                source=source,
                dialect="千歳",
                entry_ref=f"row{i}",
                latn=latn,
                kana=(row.get("kana") or "").strip(),
                pos=normalize_pos(pos_raw),
                pos_raw=pos_raw,
                gloss_jp=[g for _, g in senses] if senses else _glosses_or_empty(defn),
                senses=senses,
                definition=defn,
            )


def read_tamura(path: Path = TAMURA) -> Iterator[SourceEntry]:
    source = path.parent.name
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for i, row in enumerate(reader):
            latn = (row.get("lemma") or "").strip()
            if not latn:
                continue
            defn = (row.get("definition") or "").strip()
            senses = _split_senses(defn)
            yield SourceEntry(
                source=source,
                dialect="沙流",
                entry_ref=f"row{i}",
                latn=latn,
                kana=(row.get("translit") or "").strip(),
                pos=pos_from_definition(defn),
                pos_raw=_first_bracket(defn),
                gloss_jp=[g for _, g in senses] if senses else _glosses_or_empty(defn),
                senses=senses,
                definition=defn,
            )


def read_kayano(path: Path = KAYANO) -> Iterator[SourceEntry]:
    source = path.parent.name
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for i, row in enumerate(reader):
            latn = (row.get("lemma") or "").strip()
            if not latn:
                continue
            defn = (row.get("definition") or "").strip()
            senses = _split_senses(defn)
            yield SourceEntry(
                source=source,
                dialect="沙流",
                entry_ref=f"row{i}",
                latn=latn,
                kana=_leading_kana(defn),
                pos=pos_from_definition(defn),
                pos_raw=_first_bracket(defn),
                gloss_jp=[g for _, g in senses] if senses else _glosses_or_empty(defn),
                senses=senses,
                definition=defn,
            )


READERS = {
    "nakagawa": read_nakagawa,
    "tamura": read_tamura,
    "kayano": read_kayano,
}


def read_all() -> list[SourceEntry]:
    """All pilot sources, in seed-priority order (modern descriptive first)."""
    entries: list[SourceEntry] = []
    for reader in (read_nakagawa, read_tamura, read_kayano):
        entries.extend(reader())
    return entries


__all__ = [
    "SourceEntry",
    "read_all",
    "read_kayano",
    "read_nakagawa",
    "read_tamura",
]
