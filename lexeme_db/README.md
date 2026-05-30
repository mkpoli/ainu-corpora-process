# lexeme_db

A source-independent **lexeme bank** (語彙素層) for Ainu, modelled on UniDic's
lexeme / word-form split. It sits *above* `morpheme_db` and lets you pivot from
one canonical, linguistically-described headword out to **every dictionary's
recording of that word**.

## Two-layer design

```
lexeme_db   ← canonical headwords (語彙素): citation form + POS + gloss + senses
   │           each lexeme = a composition of ↓
morpheme_db ← morphemes (atoms): source-independent ids (form + sense)
```

- A **free** morpheme can head a lexeme on its own (`sapa` → lexeme `sapa.n`).
- A **bound** morpheme only ever appears inside a lexeme (`=an`, `-pa`).
- Neither layer's ids name a dictionary. *Which* dictionaries attest an item
  lives in the **crosswalk**, never in the id (this is what fixes the old
  `ninjal:…` source-dependence).

## The crosswalk = the annotation the dictionaries get

`output/crosswalk.tsv` is one row per **source dictionary entry**, carrying the
`lexeme_id` it maps to plus the surface form / dialect / POS / sense /
confidence as that source recorded it. Joining the crosswalk to itself on
`lexeme_id` gives every dictionary's recording of one word.

```
lexeme_id  source  dialect  entry_ref  surface_latn  surface_kana  pos_raw  sense_id  match_kind  confidence  gloss_raw
```

`match_kind` is `seed` (this source defined the lexeme), `exact`, `normalized`
(equal after `normalize.form_key`), or `fuzzy` (reserved for cross-form
matching — see Limitations).

## Pilot scope & current numbers

Three modern descriptive dictionaries:

| source | dialect | role |
|--------|---------|------|
| `1995_Nakagawa_Ainu-Chitose-Dialect-Dictionary` | 千歳 Chitose | cross-dialect axis |
| `1996_Tamura_Ainu-Saru-Dialect-Dictionary`      | 沙流 Saru   | same-dialect agreement |
| `1996_Kayano_Kayanos-Ainu-Dictionary`           | 沙流 Saru   | same-dialect agreement |

Build (`cli build`):

- **15,839** lexemes from **21,260** source entries (crosswalk rows)
- **1,802** lexemes attested in more than one dialect (Chitose ∩ Saru)
- **684** sense-split lexemes (from ①②③ numbering)
- **11,082** lexemes linked down to a morpheme-bank id

## Important limitation discovered by the pilot

Clustering is currently on `(form_key, pos)`. `form_key` collapses **spelling**
differences (glottal `a'`, markers `- =`, 田村 accents, sense-number
superscripts) — so it unifies the *same form written differently* across
sources. It does **not** unify *genuinely different dialectal forms of the same
word* (e.g. Chitose `ahkari` vs Saru `akkari`): those get different keys and
become separate lexemes.

Consequence in the current build: of the 1,802 cross-dialect lexemes, **1,493
have an identical normalised form** in both dialects (shared core vocabulary)
and **309 differ only in spacing / glottal / word-boundary** (`ape etok` 千歳 /
`apeetok` 沙流; `cise kor kamuy` / `cisekorkamuy`) — i.e. transcription
conventions, not lexical divergence. The genuinely **divergent dialectal forms**
— the most interesting "dialectal variation" — are *not yet linked*: they need a
**gloss/cognate matcher** that pairs different forms by meaning, recorded as
`match_kind = fuzzy`. That is the top next step, not yet implemented. The
schema, crosswalk, and pivot are all ready to carry those links once the matcher
exists.

## Usage

```sh
uv run python -m lexeme_db.cli build          # (re)build bank + crosswalk
uv run python -m lexeme_db.cli pivot sapa     # every dialect's recording
uv run python -m lexeme_db.cli pivot --id ekira.vi
uv run python -m lexeme_db.cli stats          # dialect overlaps, splits, links
```

Outputs land in `lexeme_db/output/` (regenerable; not committed):

- `lexeme_bank.json` — canonical lexemes (`schema.Lexeme`).
- `crosswalk.tsv` — per-entry annotations (`schema.Attestation`).

## How lexemes are formed

1. **Ingest** (`ingest.py`) reads each dictionary into a common `SourceEntry`
   (citation Latin, kana, normalised XPOS, short gloss, optional sense split,
   full definition kept verbatim).
2. **Cluster** (`build.py`) groups entries on `(form_key, pos)`.
3. **Citation form** is taken from the highest-priority descriptive source
   (中川 > 田村 > 萱野); `dialect_base` records which dialect that form is from.
4. **Sense-split** copies a contributor's ①②③ numbering onto the lexeme and
   tags each attestation with the sense it matches by index.
5. **Morpheme link**: a monomorphemic form whose key is a known morpheme gets
   `morphemes=[that id]`. Multi-morpheme decomposition is left empty, not
   guessed.

## Next steps

1. **Cross-form dialect matcher** (`fuzzy`): pair divergent dialectal forms by
   gloss/cognate similarity so `ahkari`/`akkari` land on one lexeme. This is
   what turns the bank into a real dialect-variation pivot.
2. **Match non-descriptive sources INTO the bank** (Batchelor, Dobrotvorsky,
   the wordlists) rather than co-seeding. Batchelor already has a
   `modern_correspondence.tsv` in `ainu-dictionaries` to bootstrap from.
3. **Multi-morpheme composition**: wire lexemes to morpheme *sequences*, the
   bridge back to `morpheme_db`'s valency engine.
4. **Cross-source sense alignment** by gloss similarity (currently index-based).

## Testing

```sh
uv run --package utils pytest lexeme_db/tests   # 11 tests
```
