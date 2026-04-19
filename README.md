# Ainu corpora processing tools

This is a repository for general rule-based NLP tasks using the Ainu corpora.

## Corpus Usage

This repository uses [aynumosir/ainu-corpora](https://huggingface.co/datasets/aynumosir/ainu-corpora) dataset. The dataset is not available for public use due to copyright issues, but you can apply for it by contacting the authors (neet and mkpoli).

## OCR Benchmark

Benchmark sampled pages from the Nakagawa dictionary PDF with multimodal LLMs:

```bash
uv run python -m dictionary.nakagawa_ocr_benchmark
```

The default settings live in `dictionary/nakagawa_ocr_benchmark.toml`, including pages, models, prompt, and crop padding.

CLI flags override the config file when needed. For example:

```bash
uv run python -m dictionary.nakagawa_ocr_benchmark \
  --pages 2 68 184 334 \
  --model openrouter/openai/gpt-5.4 \
  --model openrouter/openai/gpt-5.4-mini \
  --model openrouter/google/gemini-3-flash-preview \
  --model openrouter/anthropic/claude-sonnet-4.6
```

Use an alternate config file with:

```bash
uv run python -m dictionary.nakagawa_ocr_benchmark --config path/to/benchmark.toml
```

The benchmark uses cropped raw page images only, writes one OCR file per model, skips successful reruns when the page image and prompt are unchanged, and generates `cost_report.md` / `cost_report.json` under `dictionary/output/nakagawa-ocr-benchmark/`.

API keys can be provided in either `.env` at repo root or `dictionary/.env`; `dictionary/.env` overrides root values.

Typical keys:

```env
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GOOGLE_API_KEY=...
OPENROUTER_API_KEY=...
```

The checked-in benchmark config defaults to OpenRouter model IDs, so `OPENROUTER_API_KEY` is enough for the default run.

Use `--skip-ocr` to render and crop pages without calling any models.

Outputs are written under `dictionary/output/nakagawa-ocr-benchmark/`, including `backend_status.json`, rendered page images, and per-backend OCR text files.
