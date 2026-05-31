# Ainu corpora processing tools

This is a repository for general rule-based NLP tasks using the Ainu corpora.

## Corpus Usage

This repository uses [aynumosir/ainu-corpora](https://huggingface.co/datasets/aynumosir/ainu-corpora) dataset. The dataset is not available for public use due to copyright issues, but you can apply for it by contacting the authors (neet and mkpoli).

## Dictionary Tools

Dictionary-specific OCR and other dictionary processing workflows are documented in `dictionary/README.md`.

## Morpheme / Lexeme Database & Web Explorer (moved)

The morpheme database (`morpheme_db`), lexeme bank (`lexeme_db`), and the
SvelteKit explorer (`web`) have moved to
[mkpoli/ainu-morpheme-database](https://github.com/mkpoli/ainu-morpheme-database),
which now builds them standalone (it vendors the derived inputs this repo
produces under `corpus/output/` and `dictionary/output/`). This repo remains
the upstream that regenerates those inputs; point `AINU_MDB_DATA` at a checkout
of this repo to re-snapshot them there.
