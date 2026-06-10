# Sakhalin dictionary review bundle — June 2026

Everything below is **review-gated**: the live site already shows only the
high-confidence automatic layer, and nothing in these queues changes the
dictionary until a decision is recorded. Each queue lists where decisions go
and what happens on the next `uv run python dictionary/build_ainu_itah_terms.py`.

## What is already live (no action needed)

- Homographic clitic frequencies split via the marker-preserving token table:
  `an` 987 / `an=` 394 (incl. 13 hyphen-spelled) / `=an` 147; 26 entries carry
  the ≈ marker qualifier.
- 151 regular word-forms nested as collapsible sub-entries under their bases
  (possessives incl. glide `-yehe/-wehe`, collectives, causatives,
  postpositional forms), with interlinear analyses and rolled+own frequencies.
- 96 lexicalized compounds show their morphological make-up (`aynuitah =
  aynu+itah`).
- 547 entries carry typed Sakhalin↔Hokkaido same-etymon correspondences
  (667 auto pairs + 53 curated incl. `kayki = ka iki` with the `≠ka` negative,
  `manuyke ~ manu hike`, `nah : nak`).
- Search extrapolation (`itah.ts`) runs on the 22-rule audited sound-rule
  table (81/81 example checks).

## Queue 1 — Word-form tiering (988 rows)

**File:** `ainu-morpheme-database/sakhalin/output/review.tsv`
(frequency-descending; columns `… suggested_tier, parse, root, flags, decision`).

Fill `decision` per row: `accept` · `t1` (keep as own lexeme) ·
`t2: ROOT + AFFIXES` / `t3: A+B` (accept with corrected parse) · `defer`.
Decisions are then transcribed into
`dictionary/input/sakhalin/analysis_overrides.json` as
`{"<lemma>": "accept" | "reject"}` (ask Claude to batch-transcribe the TSV).

Auto-accepted without review (already nested): flag-free, suffix-only,
gloss-coherent parses only. **Everything held is in this queue**, notably:

- all proclitic parses (`kucise = ku=+cise` is genuine; `anpa`, `inkara`,
  `kuru` were machine-misreads and are correctly held),
- all coda-alias parses (`sapahci → sap-/sah`, `makapahci → makap-/makah`),
- glossless rows (`ciseta`, `kucise`, `cisehehcin` — coherence unverifiable),
- audit-distrusted shapes: roots like `ki/ye/oka`, possessive-of-possessive
  bases (`hawehe→hawe`), `an=/ku=` + bare noun.

## Queue 2 — Hokkaido correspondence suggestions (1,370 rows)

**File:** `ainu-morpheme-database/sakhalin/output/correspondence_suggestions.tsv`
(phonological matches held for gloss incoherence, no gloss basis, short-lemma
gating, or near-miss edit distance 1, e.g. `yuhpo ~ yupo` 兄).

Accepted rows graduate into
`ainu-morpheme-database/sakhalin/correspondences_curated.json` (`pairs`, typed);
rejected rows into its `negativePairs` (which then veto future auto-assertion).
Known residual false positive in the *asserted* layer to weed: `ni` 木 ~ `ni¹`
吸う.

## Queue 3 — Sakaguchi candidates (145+, coverage still completing)

**Files:** `dictionary/input/sakhalin/sakaguchi_candidates.json` (145 candidates,
123 clear-OCR; 3 of 8 source chunks still being re-read — numbers may grow),
`sakaguchi_paradigm.json` (27 person/number marker rows),
`sakaguchi_orthography_proposal.md` (8 orthography deltas).

Headline ruling adopted: **lemma `raanuh`, resurfacing stem `raanup-`,
vt 'to love'** (long `aa`; `rannu` has zero occurrences in any source;
`inranu` = `in=raanup` with final `-p > -h`; `ikoiraanuh` recorded as a form
under it — the `i-ko-i-raanu-p` segmentation is editorial, Sakaguchi gives no
decomposition). Provenance cites Sakaguchi 2024 + Piłsudski 1912 per form.

Accepted candidates should be appended to
`dictionary/input/sakhalin/new_terms_from_corpus_2026.json` (the build's merge
input) — or ask Claude to wire a `decision`-aware merge of the candidates file.

## Queue 4 — Upstream POS / data bugs (fix in the curated store)

- `taa` "that" tagged `vt` (should be `adn`; second row already adn)
- `ko` "and then" tagged `vt` (should be `sconj`)
- `kuu` "bow" tagged `vt`+`n` (should be `n`)
- `sah` one gloss family spread over vt/vi/n rows
- `hecirehci` tagged `sfx` (blocks its genuine `hecire + =hci` parse)
- `unka` (freq 2, unglossed) — likely truncation of `unkame` 化物
- junk rows: lemma `=` ; bare `eci`/`in`/`hci` rows duplicating marked clitics
- `=anahcihi`, `-ahci` spelled with markers inconsistent with the token corpus

## Open linguistic calls (your ruling shapes the data)

1. **`hankayki`** — one lexeme or `hanka + kayki` collocation? (dict has both
   parts; Sakaguchi attests the sequence)
2. **`-ke` productivity** — verb-structure and valency grammar chapters
   disagree; the affix inventory silently took the segmentation-safe side.
3. **`oyki` as a headword** — required for `kimoyki` to display `kim-oyki`
   structure (analyzer can only use dictionary lemmas as roots).
4. **`ehci` boundary** — `e + =hci` (eat=COLL) vs the machine's `eh + =ci`;
   vowel-shortening before `=hci` is unmodeled, affects `kihci/yehci` class.
5. **`yuppa → yuhpa` respelling** (dict has no `pp` lemmas; cf. `kosiyuhpa`).
6. **Paradigm reconciliation** — `sakaguchi_paradigm.json` vs
   `ainu-morpheme-database/sakhalin/affixes.json` vs `utils/lemmatize.py`
   `PERS_SYSTEM` (esp. `in=` 1PL.EXC.O East/West variation, logophoric notes,
   `anokayahcin`).
7. **Orthography deltas** — review the 8 proposals in
   `sakaguchi_orthography_proposal.md` (vowel length conventions etc.);
   each lists affected-entry counts.

## Pipeline reference

```
corpus (ainu-corpora) ──build_frequency──▶ token/lemma tables ─┐
grammar (.svx) ──▶ affixes.json + sound_rules.json             │
dict lemmas ──analyze.py──▶ sakhalin-analysis.json + review.tsv│
Hokkaido bank ──build_correspondences.py──▶ correspondences ───┤
your overrides/decisions ──────────────────────────────────────┤
                                                               ▼
                          build_ainu_itah_terms.py ──▶ data.json (site)
```

Regenerate everything: `analyze.py` → `build_correspondences.py` (both in
ainu-morpheme-database) → `build_ainu_itah_terms.py` (here). All three are
deterministic and assert their acceptance traps.
