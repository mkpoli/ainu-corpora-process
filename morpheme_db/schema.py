"""Schema for the Ainu morpheme database.

The design follows ``report/sections/database.typ`` and
``report/sections/compute.typ`` from the companion paper
``ainu-morpheme-database``: each entry stores not only a representative form
and glosses, but also the morpheme's *base valency frame* (which argument
slots it introduces) and the *local rule* it applies when it combines with
another morpheme — i.e., the structural operation it performs on its host's
argument structure (adding a causer, internalising a slot via reflexive,
absorbing an argument via noun incorporation, etc.).

The schema deliberately keeps "argument count" (arity) and "slot structure"
separate. Arity is a derived view; the slot list is the load-bearing
representation, because operations like ``yay-`` / ``si-`` and noun
incorporation change *which* slot is externally realised, not just how many
slots exist.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class SlotRealization(str, Enum):
    """How an argument slot is realised on the surface."""

    EXTERNAL = "external"
    """Realised as an external NP / pronominal — counts toward surface arity."""

    INTERNAL_INCORP = "internal_incorp"
    """Filled by an incorporated noun (cep-koyki style)."""

    INTERNAL_REFL = "internal_refl"
    """Saturated by a reflexive prefix (yay- / si-)."""

    INTERNAL_INDEF = "internal_indef"
    """Saturated by an indefinite-object prefix (i-)."""

    ABSORBED = "absorbed"
    """Removed from the clause entirely (e.g. -yar/-ar demoted subject)."""


@dataclass(slots=True)
class Slot:
    """A single argument slot in a valency frame."""

    role: str
    """Generic role label: ``agent``, ``patient``, ``causer``, ``recipient``,
    ``theme``, ``beneficiary``, ``location``, etc."""

    realization: SlotRealization = SlotRealization.EXTERNAL
    label_jp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "realization": self.realization.value,
            "label_jp": self.label_jp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Slot:
        return cls(
            role=data["role"],
            realization=SlotRealization(data.get("realization", "external")),
            label_jp=data.get("label_jp", ""),
        )


@dataclass(slots=True)
class ValencyFrame:
    """Ordered list of argument slots."""

    slots: list[Slot] = field(default_factory=list)

    @property
    def arity(self) -> int:
        """External arity — number of slots realised on the surface."""
        return sum(1 for s in self.slots if s.realization == SlotRealization.EXTERNAL)

    def copy(self) -> ValencyFrame:
        return ValencyFrame(slots=[Slot(s.role, s.realization, s.label_jp) for s in self.slots])

    def to_dict(self) -> dict[str, Any]:
        return {"slots": [s.to_dict() for s in self.slots]}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ValencyFrame | None:
        if data is None:
            return None
        return cls(slots=[Slot.from_dict(s) for s in data.get("slots", [])])


@dataclass(slots=True)
class Rule:
    """Local combination rule a morpheme applies to its host's frame.

    ``operation`` is the action; the remaining fields parameterise it.
    Multiple operations on the same morpheme are handled by listing several
    rules in ``Entry.rules``.
    """

    operation: str
    """One of:
    - ``add_slot``     — append a new slot (e.g. causative -e, applicative ko-).
    - ``remove_slot``  — drop a slot from the frame (e.g. unspecified causative -yar).
    - ``internalize``  — change a slot's realisation away from ``external``
      (e.g. si-/yay- reflexive, i- indefinite, noun incorporation).
    - ``noop``         — explicit identity; useful for marking discourse particles.
    """

    role: str = ""
    """For ``add_slot``: the role of the new slot. For ``remove_slot`` /
    ``internalize``: the role of the slot to target (when ``target_index``
    is not given)."""

    realization: SlotRealization = SlotRealization.EXTERNAL
    """For ``add_slot`` and ``internalize``: the realisation channel to set."""

    position: str = "front"
    """For ``add_slot``: where to insert the new slot (``front`` or ``back``)."""

    target_index: int | None = None
    """For ``remove_slot`` / ``internalize``: 0-indexed slot to target. Takes
    precedence over ``role`` matching when set."""

    label_jp: str = ""
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"operation": self.operation}
        if self.role:
            out["role"] = self.role
        if self.realization != SlotRealization.EXTERNAL:
            out["realization"] = self.realization.value
        if self.position != "front":
            out["position"] = self.position
        if self.target_index is not None:
            out["target_index"] = self.target_index
        if self.label_jp:
            out["label_jp"] = self.label_jp
        if self.description:
            out["description"] = self.description
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Rule:
        return cls(
            operation=data["operation"],
            role=data.get("role", ""),
            realization=SlotRealization(data.get("realization", "external")),
            position=data.get("position", "front"),
            target_index=data.get("target_index"),
            label_jp=data.get("label_jp", ""),
            description=data.get("description", ""),
        )


@dataclass(slots=True)
class Entry:
    """A morpheme entry."""

    id: str
    lemma: str
    """Representative form, with attachment markers preserved
    (e.g. ``-e``, ``si-``, ``=an``)."""

    allomorphs: list[str] = field(default_factory=list)

    category: str = ""
    """Primary XPOS-style category. See ``dictionary/XPOS.md`` for the inventory
    used elsewhere in this repository (e.g. ``vt``, ``vi``, ``n``, ``pfx``,
    ``sfx``, ``pers``)."""

    category_alt: list[str] = field(default_factory=list)
    """Alternative categories the morpheme can convert into (per 佐藤2020)."""

    bound: bool = False
    morph_type: str = "root"
    """``root`` | ``prefix`` | ``suffix`` | ``clitic`` | ``particle`` | ``stem``."""

    slot: list[str] = field(default_factory=list)
    """Morphotactic slot(s) this affix occupies in the Ainu verbal template,
    as Roman numerals ``"I"``–``"VI"`` (Bugaeva 2014, after Tamura 1955):

    - **I**   inner applicative (``e-``, ``ko-``, ``o-``)
    - **II**  reciprocal / reflexive / indefinite-object (``u-``, ``yay-``,
      ``si-``, ``i-``)
    - **III** outer applicative (same forms as I, layered further out)
    - **IV**  number suffix (verbal plural ``-pa``)
    - **V**   transitivising / direct causative (``-ka``, ``-V``, ``-ke``,
      ``-re``/``-e``/``-te`` direct)
    - **VI**  indirect causative (``-re``/``-e``/``-te`` indirect, ``-yar``)

    Forms that occupy more than one slot list each (e.g. the applicatives
    are ``["I", "III"]``; productive ``-re``/``-e``/``-te`` is
    ``["V", "VI"]``). Empty for entries that aren't part of this template
    (roots, clitics, nominalisers)."""

    base_frame: ValencyFrame | None = None
    """Base argument structure when the morpheme heads a unit. Free roots and
    independent verbs/nouns set this; pure affixes typically leave it ``None``
    and contribute only via ``rules``."""

    rules: list[Rule] = field(default_factory=list)
    """Local rules applied when the morpheme combines with a host frame."""

    attaches_to: list[str] = field(default_factory=list)
    """Categories this morpheme can attach to (for bound morphemes)."""

    selection: list[str] = field(default_factory=list)
    glosses_en: list[str] = field(default_factory=list)
    glosses_jp: list[str] = field(default_factory=list)
    dialects: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    notes: str = ""
    frequency: int = 0
    verified: bool = False
    """True for hand-curated entries; False for entries auto-ingested from the
    NINJAL lexicon or other observational sources."""

    composition: list[str] = field(default_factory=list)
    """Underlying composition as an ordered list of morpheme ``id``s.

    Used for lexicalised reductions where the surface form has undergone
    phonological fusion and can no longer be recovered by simple text
    segmentation (e.g. ``inkar`` ← ``i-`` + ``nukar``). When present, the
    valency engine and UI tree use this list as the structural truth, and
    the surface ``lemma`` is shown as the lexicalised head."""

    composition_surface: list[str] = field(default_factory=list)
    """Source-text surface form for each entry in :attr:`composition`.

    Resolves the allomorph-vs-lemma display mismatch: ``upakte`` decomposes
    as ``u + pak + te``, but the ``te`` slot resolves to the ``-e`` entry
    (since ``-e/-re/-te`` are stored as one allomorph cluster). Without a
    parallel surface array the graph would render ``u-pak-e`` — phono-
    logically impossible. When this field is empty the renderer falls
    back to the resolved entry's lemma. Indices align 1:1 with
    :attr:`composition`."""

    composition_note: str = ""
    """Short note explaining the reduction (e.g. ``phonological fusion of
    i-nukar with loss of medial vowel``). Shown in the UI."""

    reconstructed: dict[str, str] = field(default_factory=dict)
    """Reconstructed proto-forms, keyed by reconstruction-source short name.

    Example: ``{"SRPA": "*-de"}`` for the ``-e/-re/-te`` causative cluster,
    where ``SRPA`` denotes Shiratori's Proto-Ainu Reconstruction. Values
    are conventionally prefixed with ``*`` to mark them as reconstructed.
    Empty when no reconstruction has been recorded."""

    etymology: dict[str, Any] | None = None
    """Optional historical / etymological decomposition.

    Distinct from :attr:`composition`, which records the synchronic
    structure. Etymology captures analyses that hold diachronically but are
    *not* part of the synchronic grammar — e.g. ``nukar`` is synchronically
    atomic but historically analysable as ``nu (eye) + kar (act on)`` (per
    Nakagawa 1995).

    Shape::

        {
            "parts": [
                {"lemma": "nu²", "gloss_en": "eye (root)", "gloss_jp": "目（語根）"},
                {"lemma": "kar",  "gloss_en": "act on",   "gloss_jp": "〜に作用する"}
            ],
            "note":   "ヌペ nu-pe 'tear' parallels the analysis.",
            "source": "中川1995アイヌ語千歳方言辞典"
        }

    The ``source`` field is a refs.yml citation key. ``parts`` may be empty
    if all that's known is a textual note. Entries that are perfectly
    transparent synchronically don't need this field."""

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id": self.id,
            "lemma": self.lemma,
            "allomorphs": list(self.allomorphs),
            "category": self.category,
            "category_alt": list(self.category_alt),
            "bound": self.bound,
            "morph_type": self.morph_type,
            "slot": list(self.slot),
            "base_frame": self.base_frame.to_dict() if self.base_frame is not None else None,
            "rules": [r.to_dict() for r in self.rules],
            "attaches_to": list(self.attaches_to),
            "selection": list(self.selection),
            "glosses_en": list(self.glosses_en),
            "glosses_jp": list(self.glosses_jp),
            "dialects": list(self.dialects),
            "sources": list(self.sources),
            "notes": self.notes,
            "frequency": self.frequency,
            "verified": self.verified,
            "composition": list(self.composition),
            "composition_surface": list(self.composition_surface),
            "composition_note": self.composition_note,
            "reconstructed": dict(self.reconstructed),
            "etymology": self.etymology,
        }
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Entry:
        return cls(
            id=data["id"],
            lemma=data["lemma"],
            allomorphs=list(data.get("allomorphs", [])),
            category=data.get("category", ""),
            category_alt=list(data.get("category_alt", [])),
            bound=bool(data.get("bound", False)),
            morph_type=data.get("morph_type", "root"),
            slot=list(data.get("slot", [])),
            base_frame=ValencyFrame.from_dict(data.get("base_frame")),
            rules=[Rule.from_dict(r) for r in data.get("rules", [])],
            attaches_to=list(data.get("attaches_to", [])),
            selection=list(data.get("selection", [])),
            glosses_en=list(data.get("glosses_en", [])),
            glosses_jp=list(data.get("glosses_jp", [])),
            dialects=list(data.get("dialects", [])),
            sources=list(data.get("sources", [])),
            notes=data.get("notes", ""),
            frequency=int(data.get("frequency", 0)),
            verified=bool(data.get("verified", False)),
            composition=list(data.get("composition", [])),
            composition_surface=list(data.get("composition_surface", [])),
            composition_note=data.get("composition_note", ""),
            reconstructed=dict(data.get("reconstructed", {})),
            etymology=data.get("etymology"),
        )


def save_entries(entries: Iterable[Entry], path: Path) -> None:
    """Write entries to ``path`` as a JSON array."""
    payload = [entry.to_dict() for entry in entries]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def load_entries(path: Path) -> list[Entry]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Entry.from_dict(item) for item in data]


__all__ = [
    "Entry",
    "Rule",
    "Slot",
    "SlotRealization",
    "ValencyFrame",
    "asdict",
    "load_entries",
    "save_entries",
]
