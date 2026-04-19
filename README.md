# Ainu corpora processing tools

This is a repository for general rule-based NLP tasks using the Ainu corpora.

## Corpus Usage

This repository uses [aynumosir/ainu-corpora](https://huggingface.co/datasets/aynumosir/ainu-corpora) dataset. The dataset is not available for public use due to copyright issues, but you can apply for it by contacting the authors (neet and mkpoli).

## OCR Benchmark

Benchmark sampled pages from the Nakagawa dictionary PDF with:

```bash
uv run python -m dictionary.nakagawa_ocr_benchmark --skip-ocr
```

Use `--skip-ocr` to render pages, preprocess them, and extract the existing ABBYY text layer only. Remove `--skip-ocr` after installing OCR backends such as `tesseract` and `paddleocr`.

Outputs are written under `dictionary/output/nakagawa-ocr-benchmark/`, including `backend_status.json`, rendered page images, and per-backend OCR text files.
