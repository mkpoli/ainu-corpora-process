"""Tests for the valency-computation engine.

The cases below are taken directly from
``ainu-morpheme-database/report/sections/system.typ`` and
``.../compute.typ``:

- ``nukar``         (2 args)
- ``nukar-e``       (3 args; causative adds a causer)
- ``si-nukar-e``    (back to 2 args; indirect reflexive internalises the causer)
- ``cep-koyki``     (2 → 1 arg; noun incorporation absorbs the patient)
- ``i-nukar``       (2 → 1 arg; indefinite-object prefix saturates the patient)
- ``nukar-yar``     (2 → 2 args; indefinite causative is arity-neutral)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from morpheme_db.schema import Entry, Rule, Slot, SlotRealization, ValencyFrame, load_entries
from morpheme_db.valency import compute_valency

SEED_PATH = Path(__file__).resolve().parents[1] / "seed" / "morphemes.json"


@pytest.fixture(scope="module")
def index() -> dict[str, Entry]:
    """Indexed by entry ID, so test cases can disambiguate homographs.

    Several lemmas now collide because productive vs. inflectional variants
    coexist in the seed (e.g. ``-e`` causative ``id=-e`` vs. inflectional
    singular-action ``id=-e-infl``). A lemma-keyed index loses one of the
    two; an ID-keyed index keeps both. For convenience we also accept the
    plain lemma when it's unambiguous.
    """
    entries = load_entries(SEED_PATH)
    by_id: dict[str, Entry] = {entry.id: entry for entry in entries}
    # Layer bare lemmas on top so the lemma-only lookups still resolve, but
    # only for lemmas that aren't already taken as an ID — IDs win on
    # collision.
    for entry in entries:
        if entry.lemma not in by_id:
            by_id[entry.lemma] = entry
    return by_id


def _arity_of(*lemmas: str, index: dict[str, Entry]) -> int:
    result = compute_valency([index[lemma] for lemma in lemmas])
    return result.arity


def test_nukar_alone_is_two_args(index: dict[str, Entry]) -> None:
    assert _arity_of("nukar", index=index) == 2


def test_causative_adds_external_causer(index: dict[str, Entry]) -> None:
    result = compute_valency([index["nukar"], index["-e"]])
    assert result.arity == 3
    assert result.final_frame.slots[0].role == "causer"
    assert result.final_frame.slots[0].realization == SlotRealization.EXTERNAL


def test_si_internalises_the_new_causer(index: dict[str, Entry]) -> None:
    result = compute_valency([index["si-"], index["nukar"], index["-e"]])
    assert result.arity == 2
    causer = next(s for s in result.final_frame.slots if s.role == "causer")
    assert causer.realization == SlotRealization.INTERNAL_REFL


def test_yay_internalises_the_patient(index: dict[str, Entry]) -> None:
    result = compute_valency([index["yay-"], index["nukar"]])
    assert result.arity == 1
    patient = next(s for s in result.final_frame.slots if s.role == "patient")
    assert patient.realization == SlotRealization.INTERNAL_REFL


def test_i_prefix_saturates_patient(index: dict[str, Entry]) -> None:
    result = compute_valency([index["i-"], index["nukar"]])
    assert result.arity == 1
    patient = next(s for s in result.final_frame.slots if s.role == "patient")
    assert patient.realization == SlotRealization.INTERNAL_INDEF


def test_indefinite_causative_is_arity_neutral(index: dict[str, Entry]) -> None:
    result = compute_valency([index["nukar"], index["-yar"]])
    assert result.arity == 2
    roles = [s.role for s in result.final_frame.slots]
    assert "causer" in roles
    assert "agent" not in roles


def test_noun_incorporation_absorbs_patient() -> None:
    """A 2-arg verb whose patient is filled by an incorporated noun has arity 1.

    Modelled here by giving the incorporated noun a one-shot rule that
    internalises the host's patient slot.
    """
    cep = Entry(
        id="cep",
        lemma="cep",
        category="n",
        morph_type="root",
        rules=[
            Rule(
                operation="internalize",
                role="patient",
                realization=SlotRealization.INTERNAL_INCORP,
                label_jp="魚",
                description="incorporated as object of host verb",
            )
        ],
    )
    koyki = Entry(
        id="koyki",
        lemma="koyki",
        category="vt",
        morph_type="root",
        base_frame=ValencyFrame(
            slots=[
                Slot("agent", SlotRealization.EXTERNAL, "捕る人"),
                Slot("patient", SlotRealization.EXTERNAL, "獲られるもの"),
            ]
        ),
    )
    result = compute_valency([cep, koyki])
    assert result.arity == 1
    patient = next(s for s in result.final_frame.slots if s.role == "patient")
    assert patient.realization == SlotRealization.INTERNAL_INCORP


def test_empty_sequence_returns_empty_frame() -> None:
    result = compute_valency([])
    assert result.arity == 0
    assert result.final_frame.slots == []


def test_warns_when_no_base_frame() -> None:
    affix = Entry(
        id="-e",
        lemma="-e",
        category="sfx",
        bound=True,
        morph_type="suffix",
        rules=[Rule(operation="add_slot", role="causer")],
    )
    result = compute_valency([affix])
    assert result.warnings  # one warning recorded
    assert result.arity == 1
