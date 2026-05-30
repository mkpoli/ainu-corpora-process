"""Schema for the Ainu lexeme bank and the dictionary crosswalk.

Three record types:

* :class:`Lexeme` — a canonical descriptive unit (UniDic 語彙素). Keyed by a
  source-independent id; carries the citation form, POS, glosses, an optional
  list of :class:`Sense`, and a ``morphemes`` composition into the morpheme
  bank.
* :class:`Sense` — an optional sense split inside a lexeme, used when a source
  numbers distinct senses (①②③ …) under one headword.
* :class:`Attestation` — one crosswalk row: "source S, in dialect D, records
  lexeme L as surface form X". This is the annotation layer the user asked for
  — every dictionary entry pointing at its central lexeme.

Ids are deliberately source-independent. A lexeme id is the normalised citation
form (``sapa``), disambiguated by POS and, when sense-split, a sense index
(``sapa.n``, ``a.vi``, ``a.pers.2``). The id never names a dictionary — which
dictionaries attest it lives in the crosswalk, not the id.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class Sense:
    """A single sense inside a lexeme."""

    id: str
    """Sense id, e.g. ``"1"`` / ``"2"`` — unique within the lexeme."""

    gloss_jp: list[str] = field(default_factory=list)
    gloss_en: list[str] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "gloss_jp": list(self.gloss_jp),
            "gloss_en": list(self.gloss_en),
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Sense:
        return cls(
            id=str(data["id"]),
            gloss_jp=list(data.get("gloss_jp", [])),
            gloss_en=list(data.get("gloss_en", [])),
            note=data.get("note", ""),
        )


@dataclass(slots=True)
class Lexeme:
    """A canonical lexeme (語彙素)."""

    id: str
    """Source-independent id: normalised citation form + POS suffix (+ optional
    homograph index), e.g. ``sapa.n``, ``a.vi``, ``a.pers``."""

    lemma: str
    """Canonical phonemic-Latin citation form (attachment markers preserved for
    bound lexemes, e.g. ``=an``, ``-pa``)."""

    kana: str = ""
    """Canonical katakana citation form."""

    pos: str = ""
    """XPOS-style category (see ``dictionary/XPOS.md``)."""

    gloss_jp: list[str] = field(default_factory=list)
    gloss_en: list[str] = field(default_factory=list)

    bound: bool = False
    """True for lexemes that only appear bound (affix-like headwords)."""

    dialect_base: str = ""
    """Dialect whose form was taken as the citation form (provenance of the
    canonical spelling — *not* a claim that the lexeme is dialect-specific)."""

    morphemes: list[str] = field(default_factory=list)
    """Composition into the morpheme bank: ordered morpheme ids. A free
    monomorphemic lexeme has exactly one id equal to its own lemma; empty when
    no morpheme-bank resolution was found yet."""

    senses: list[Sense] = field(default_factory=list)
    """Sense split when the source numbered senses; empty for single-sense
    lexemes (their glosses live directly on ``gloss_*``)."""

    sources: list[str] = field(default_factory=list)
    """Which dictionaries contributed to / attest this lexeme (folder names)."""

    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "lemma": self.lemma,
            "kana": self.kana,
            "pos": self.pos,
            "gloss_jp": list(self.gloss_jp),
            "gloss_en": list(self.gloss_en),
            "bound": self.bound,
            "dialect_base": self.dialect_base,
            "morphemes": list(self.morphemes),
            "senses": [s.to_dict() for s in self.senses],
            "sources": list(self.sources),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Lexeme:
        return cls(
            id=data["id"],
            lemma=data["lemma"],
            kana=data.get("kana", ""),
            pos=data.get("pos", ""),
            gloss_jp=list(data.get("gloss_jp", [])),
            gloss_en=list(data.get("gloss_en", [])),
            bound=bool(data.get("bound", False)),
            dialect_base=data.get("dialect_base", ""),
            morphemes=list(data.get("morphemes", [])),
            senses=[Sense.from_dict(s) for s in data.get("senses", [])],
            sources=list(data.get("sources", [])),
            notes=data.get("notes", ""),
        )


@dataclass(slots=True)
class Attestation:
    """One crosswalk row linking a source dictionary entry to a lexeme."""

    lexeme_id: str
    source: str
    """Source dictionary folder name (e.g. ``1995_Nakagawa_...``)."""

    dialect: str
    """Dialect of this source's recording (e.g. ``千歳``, ``沙流``)."""

    entry_ref: str
    """Stable pointer back into the source: row index or headword key."""

    surface_latn: str = ""
    surface_kana: str = ""
    pos_raw: str = ""
    gloss_raw: str = ""
    sense_id: str = ""
    """Which lexeme sense this entry maps to, when the lexeme is sense-split."""

    match_kind: str = "seed"
    """How the link was made: ``seed`` (this source defined the lexeme),
    ``exact`` (form+pos equal), ``normalized`` (equal after normalisation),
    ``fuzzy`` (edit-distance / gloss-assisted)."""

    confidence: float = 1.0

    def to_row(self) -> list[str]:
        return [
            self.lexeme_id,
            self.source,
            self.dialect,
            self.entry_ref,
            self.surface_latn,
            self.surface_kana,
            self.pos_raw,
            self.sense_id,
            self.match_kind,
            f"{self.confidence:.3f}",
            self.gloss_raw.replace("\t", " ").replace("\n", " "),
        ]

    HEADER = [
        "lexeme_id",
        "source",
        "dialect",
        "entry_ref",
        "surface_latn",
        "surface_kana",
        "pos_raw",
        "sense_id",
        "match_kind",
        "confidence",
        "gloss_raw",
    ]


def save_lexemes(lexemes: Iterable[Lexeme], path: Path) -> None:
    payload = [lx.to_dict() for lx in lexemes]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def load_lexemes(path: Path) -> list[Lexeme]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Lexeme.from_dict(item) for item in data]


__all__ = [
    "Attestation",
    "Lexeme",
    "Sense",
    "load_lexemes",
    "save_lexemes",
]
