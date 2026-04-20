# Dictionary Tools

This directory contains dictionary-specific processing scripts, configs, inputs, and outputs.

## Nakagawa OCR

Benchmark sampled pages from the Nakagawa dictionary PDF with multimodal LLMs:

```bash
uv run python -m dictionary.nakagawa_ocr_benchmark
```

The default settings live in `dictionary/nakagawa_ocr_benchmark.toml`, including pages, models, prompt, and crop margins. Crop values are percentages of page width/height.

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

Outputs are written under `dictionary/output/nakagawa-ocr-benchmark/`, including `backend_status.json`, `images/full_page.png`, `images/cropped_page.png`, and per-backend OCR text files.

## Nakagawa Production OCR

For the full production dictionary run, use the separate command and config:

```bash
uv run python -m dictionary.nakagawa_ocr_prod
```

The default production config lives at `dictionary/nakagawa_ocr_prod.toml`. It targets pages `17-447`, writes to `dictionary/output/nakagawa-ocr-prod/`, keeps only `images/cropped_page.png`, and writes `cost_report.md` / `cost_report.json` for that run.

## Compare And Adjudicate

After production OCR finishes, compare the two completed model outputs and auto-pick a winner per page with:

```bash
uv run python -m dictionary.nakagawa_ocr_compare
```

This writes comparison outputs under `dictionary/output/nakagawa-ocr-compare/`, including per-page `decision.json`, a `summary.md`, and `manual_review.tsv` plus `manual_overrides.template.tsv` for pages that still need human intervention.

## Prepare Review Workspace

Prepare an editor-friendly review workspace from those compare results with:

```bash
uv run python -m dictionary.nakagawa_ocr_prepare_review
```

This writes review folders under `dictionary/output/nakagawa-ocr-review/` for flagged pages. Each page folder contains:

- `final.txt`: editable seeded final text
- candidate model text files such as `gpt-5.4.txt` and `gemini-3-flash-preview.txt`
- `candidates.diff`: unified diff between the two candidate texts
- `cropped_page.png`
- `decision.json`
- `README.txt`

Edit `final.txt` directly in your editor for the pages you want to correct.

Suggested workflow:

1. Run compare once and keep the existing decisions:

```bash
uv run python -m dictionary.nakagawa_ocr_compare
```

2. Prepare the review workspace for flagged pages:

```bash
uv run python -m dictionary.nakagawa_ocr_prepare_review
```

3. Open `dictionary/output/nakagawa-ocr-review/` in your editor.

4. For each page you want to inspect, compare:
   - `final.txt` (seeded automatic choice)
   - `gpt-5.4.txt`
   - `gemini-3-flash-preview.txt`
   - `candidates.diff`
   - `cropped_page.png`

5. Edit `final.txt` only when you want to override the automatic result.

## Finalize

Finalize all pages with:

```bash
uv run python -m dictionary.nakagawa_ocr_finalize
```

Finalize precedence is:

1. Edited `dictionary/output/nakagawa-ocr-review/page-XXX/final.txt`
2. `manual_overrides.tsv` if present
3. automatic compare decision from `decision.json`

This writes final per-page texts under `dictionary/output/nakagawa-ocr-final/`.

Finalize automatically prefers `dictionary/output/nakagawa-ocr-review/page-XXX/final.txt` when it exists, so you can review by editing files directly instead of creating many separate custom override files.
