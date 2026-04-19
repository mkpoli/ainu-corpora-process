# AGENTS

## Workspace Facts
- Use `uv` for Python commands at repo root. The root `pyproject.toml` defines the main `process` package and a workspace member `utils`; `wiktionary-dump-extractor` is a local path dependency and `wiktionary` comes from a pinned Git dependency.
- The repository requires Python `>=3.12` at the root. The `utils` package declares `>=3.11`, but the checked-in root environment is 3.12.
- The corpus data referenced in `README.md` is not public. If a task depends on real corpus contents, expect local access to be missing unless the dataset has already been provisioned.

## Verified Commands
- Run the maintained test suite with `uv run --package utils pytest`.
- Run one test file from repo root with `uv run --package utils pytest utils/src/utils/test_tokenize.py`.
- Acquire English Wiktionary source data with `uv run python -m dictionary.enwikt.acquire_dump`.
- Generate English Wiktionary filtered JSON/gloss JSON/TSV with `uv run python -m dictionary.enwikt.generate_entries`.
- There is no verified repo-level lint, typecheck, formatter, pre-commit, or CI workflow config in this checkout. Do not invent those steps in `AGENTS.md` updates or task summaries.

## Package Boundaries
- `utils/src/utils/` is the only area with automated tests. Its tests are simple pure-Python unit tests colocated as `test_*.py` next to modules.
- `wiktionary-dump-extractor/` is a Rust `pyo3` extension exposing Python functions used by dictionary pipelines.
- `dictionary/` is mostly notebook-driven data processing with a few helper scripts that read/write files under `dictionary/output/`.

## Rust Extension
- After editing `wiktionary-dump-extractor/src/lib.rs`, rebuild/reinstall the extension from `wiktionary-dump-extractor/` with `maturin develop --uv`.
- The extension currently exports both `extract_ainu_entries(...)` and `extract_ainu_entries_en(...)`; keep the `.pyi` stub in sync with Rust exports.

## Dictionary Pipeline Gotchas
- Large artifacts should go under `AINU_LARGE_DATA_DIR`, which is a shared root for multi-GB files and is loaded from `.env` via `python-dotenv`. On WSL, point it at a Windows mount such as `/mnt/m/Workspace/Ainu`; each pipeline uses its own subdirectory under that root (for English Wiktionary: `wiktionary-dumps/`).
- Several scripts hardcode absolute paths to this checkout, e.g. `/home/mkpoli/projects/Ainu/ainu-corpora-process/...` in `dictionary/jawikt/generate_tsv.py`, `dictionary/enwikt/generate_entries.py`, `run_split.py`, and `run_split_light.py`. If you move code or try to reuse scripts elsewhere, path handling must be fixed explicitly.
- Japanese Wiktionary TSV generation is separate from English generation:
  - `dictionary/jawikt/generate_tsv.py` reads `dictionary/output/wiktionary_ainu_glosses.json` and writes `dictionary/output/wiktionary-entries.tsv`.
  - `dictionary/enwikt/acquire_dump.py` downloads/decompresses the English dump into `AINU_LARGE_DATA_DIR/wiktionary-dumps/` and extracts `dictionary/output/wiktionary_ainu_entries_en.json`.
  - `dictionary/enwikt/generate_entries.py` reads `dictionary/output/wiktionary_ainu_entries_en.json` and writes `dictionary/output/wiktionary_ainu_entries_en_filtered.json`, `dictionary/output/wiktionary_ainu_glosses_en.json`, and `dictionary/output/wiktionary-en-entries.tsv`.
- `run_split.py` and `run_split_light.py` are one-off splitters for `dictionary/output/ainu-archive/cleaned-dictionary.tsv`; they generate per-citation TSVs in `dictionary/output/ainu-archive/`.

## Low-Risk Verification
- For small script changes outside `utils`, a practical verified check is `uv run python -m py_compile <path>`.
- For `utils` changes, run the narrowest affected `pytest` file first, then `uv run --package utils pytest` if the change touches shared logic.
