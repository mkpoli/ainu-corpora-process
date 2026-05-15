# morpheme_db

A first-pass implementation of the Ainu morpheme database proposed in
`ainu-morpheme-database/report/main.typ` ("アイヌ語形態素データベースの構築と
応用——抱合的構造と結合価の計算に着目して——"). It treats morphemes as the
basic descriptive unit and stores, alongside the usual lexicographic
information, the *local rule* each morpheme applies to its host's argument
structure. Sequences of morphemes can then be fed through a small engine
that derives the effective valency of the whole unit — including unknown
compound forms whose constituents are already in the database.

## What is in the database

Each `Entry` carries:

- `lemma`, `allomorphs`, `category` (XPOS-style) and `category_alt`
- `bound`, `morph_type` (`root` / `prefix` / `suffix` / `clitic` / …)
- `base_frame` — an ordered list of argument `Slot`s (role + realisation)
- `rules` — local operations applied on combination
  (`add_slot`, `remove_slot`, `internalize`, `noop`)
- `attaches_to`, `selection`, glosses, `dialects`, `sources`, `notes`
- `frequency` from the NINJAL corpus and a `verified` flag

The slot representation is what lets us encode the difference between
"argument added" and "argument *internalised*" — central to the paper's
treatment of noun incorporation and reflexive prefixes.

## What it computes

The engine in `morpheme_db.valency` applies rules outward from the head:
suffixes first (left-to-right after the head) and then prefixes
(right-to-left before the head), so that e.g. `-e` creates the causer slot
*before* `si-` tries to internalise it. Concrete cases covered by the
curated seed:

| input         | arity | what changed                                   |
|---------------|-------|------------------------------------------------|
| `nukar`       | 2     | see-er + seen (base)                           |
| `nukar-e`     | 3     | causative `-e` adds an external causer         |
| `si-nukar-e`  | 2     | `si-` internalises the causer (indirect refl.) |
| `yay-nukar`   | 1     | `yay-` internalises the patient (direct refl.) |
| `nukar-yar`   | 2     | `-yar` adds causer, demotes original subject   |
| `i-nukar`     | 1     | `i-` saturates the patient with INDEF          |

Noun incorporation is supported on the engine side via a one-shot
`internalize` rule (see the `test_noun_incorporation_absorbs_patient` test).
The seed leaves `cep`, `kamuy`, etc. without that rule because whether a
noun incorporates is contextual, not a property of the noun itself.

## Sources

The curated seed (`seed/morphemes.json`, 12 entries) is hand-written from
the literature cited in `database.typ` / `system.typ` / `compute.typ` —
notably 佐藤2023 (3項動詞 / 項スロット), ブガエワ2014 (使役),
中川2024 (アリティ整理), and 佐藤2007 (yay-/si-).

A second curated file, `seed/translations.json`, backfills English /
Japanese glosses for compound entries that the Tommy 1949 and Japanese
Wiktionary ingests left one-sided. The map is keyed by lemma; values may
be a string (single English gloss), a list of strings (English glosses),
or `{en: [...], jp: [...]}`. The ingest step only fills empty `glosses_en`
or `glosses_jp` fields — existing data is never overwritten.

The NINJAL ingest (`ingest_ninjal.py`) reads
`corpus/output/ninjal/lexicon/ninjal_morpheme_lexicon.tsv` produced by
`corpus/ninjal/extract_morpheme_lexicon.py` and emits ~1400 unverified
candidate entries. They are merged with the seed in `build.py`: where a
lemma exists in both, the curated valency information wins and the NINJAL
frequency / variants are folded in.

This is the "下位の形態素知識層 (sub-layer of morpheme knowledge)" view
from `database.typ`: existing dictionaries and corpora are kept as
sources, not replaced.

## Usage

```sh
# Build the unified database (writes morpheme_db/output/{json,tsv}).
uv run python -m morpheme_db.cli build

# Compute the effective valency of a morpheme sequence.
uv run python -m morpheme_db.cli compute si-nukar-e
uv run python -m morpheme_db.cli compute nukar-yar
uv run python -m morpheme_db.cli compute "yay-nukar"
```

`compute` accepts either a hyphenated sequence (`si-nukar-e`) or
whitespace-separated tokens (`cep koyki`). Tokens are resolved against
`lemma` and `allomorphs`; anything still unresolved is reported as a
warning.

## Testing

```sh
uv run --package utils pytest morpheme_db/tests
```

13 tests; the valency cases mirror the example walk-through in
`compute.typ` and `system.typ`.

## Limitations / next steps

- Selection restrictions (`attaches_to`, `selection`) are populated but not
  yet enforced during computation.
- Dialect handling is metadata-only; no allomorph routing yet.
- The NINJAL ingest leaves `category` / `base_frame` empty for unverified
  entries. Curation can promote entries by hand-editing
  `seed/morphemes.json` and re-running `build`.
- Other dictionary ingests (Kayano, Tamura, Nakagawa OCR, Wiktionary) are
  not yet wired up; the schema is designed to accept them as additional
  `sources`.
