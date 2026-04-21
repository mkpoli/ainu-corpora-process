# NINJAL corpus helpers

Download or sync the latest NINJAL glossed corpus incrementally with:

```bash
uv run python -m corpus.ninjal.sync_glossed_corpus
```

This checks the live story index and downloads only missing story JSON files into `corpus/output/ninjal/`.

To force-refresh all local story files:

```bash
uv run python -m corpus.ninjal.sync_glossed_corpus --force
```

`extract_morpheme_lexicon.py` builds a morpheme-level lexicon from the downloaded NINJAL story JSON files in `corpus/output/ninjal/`.

Run it from the repo root with:

```bash
uv run python -m corpus.ninjal.extract_morpheme_lexicon
```

It writes three TSV files under `corpus/output/ninjal/lexicon/`:

- `ninjal_morpheme_lexicon.tsv`: one row per morpheme with counts, gloss variants, and one example.
- `ninjal_morpheme_occurrences.tsv`: one row per extracted morpheme occurrence.
- `ninjal_morpheme_unresolved.tsv`: units where hyphen-based morpheme splitting does not align cleanly with the gloss segmentation and should be reviewed manually.

The extractor splits `morpheme`, `gloss_en`, and `gloss_jp` on `||` first, then splits compounds on `-` only when all three fields align to the same number of parts.
