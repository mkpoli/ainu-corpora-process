"""Build a word-/morpheme-frequency table from the ainu-corpora dataset.

``ainu-corpora`` (sibling repository, ``../ainu-corpora/data.jsonl``) is a
194k-row corpus of Ainu sentences spanning Hokkaido and Sakhalin dialects.
It is substantially larger than the NINJAL glossed corpus (≈1.4 k morpheme
entries) and is therefore a better basis for the per-entry ``frequency``
shown in the morpheme database UI.

This script reads ``data.jsonl``, runs each ``text`` field through
``utils.tokenize.tokenize`` (which splits off Ainu affixes and clitics), and
normalises the resulting tokens via ``utils.lemmatize.normalize`` (strips
accents, removes underscores/square-brackets, etc.). Two tables are written
to ``corpus/output/ainu_corpora/``:

- ``token_frequency.tsv`` — surface tokens after normalisation
  (kept separate so ``=an`` / ``a=`` / ``-e`` retain their attachment
  markers, which is how the morpheme database stores affixes)
- ``lemma_frequency.tsv`` — same table with attachment markers stripped
  (used to back-fill bound morphemes whose surface tokens carry ``-``/``=``)

Both also carry a ``dialect_breakdown`` column with ``hokkaido:N|sakhalin:M``
counts so downstream consumers can filter by dialect.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from utils.lemmatize import normalize
from utils.tokenize import is_word, tokenize

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = REPO_ROOT.parent / "ainu-corpora" / "data.jsonl"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "corpus" / "output" / "ainu_corpora"


def _dialect_bucket(row: dict) -> str:
    lv1 = row.get("dialect_lv1")
    if isinstance(lv1, list):
        if any("樺太" in (x or "") for x in lv1):
            return "sakhalin"
        if any("北海道" in (x or "") for x in lv1):
            return "hokkaido"
    elif isinstance(lv1, str):
        if "樺太" in lv1:
            return "sakhalin"
        if "北海道" in lv1:
            return "hokkaido"
    return "other"


def build(input_path: Path, output_dir: Path) -> dict[str, int]:
    token_counts: Counter[str] = Counter()
    token_by_dialect: dict[str, Counter[str]] = {}
    lemma_counts: Counter[str] = Counter()
    lemma_by_dialect: dict[str, Counter[str]] = {}
    sentence_counts: Counter[str] = Counter()
    rows_seen = 0
    rows_with_text = 0

    with input_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows_seen += 1
            row = json.loads(line)
            text = row.get("text") or ""
            if not text:
                continue
            rows_with_text += 1
            dialect = _dialect_bucket(row)
            sentence_counts[dialect] += 1

            seen_in_sentence: set[str] = set()
            for raw in tokenize(text):
                if not is_word(raw):
                    continue
                surface = normalize(raw)
                if not surface:
                    continue
                token_counts[surface] += 1
                token_by_dialect.setdefault(dialect, Counter())[surface] += 1
                bare = surface.strip("-=")
                if bare:
                    lemma_counts[bare] += 1
                    lemma_by_dialect.setdefault(dialect, Counter())[bare] += 1
                seen_in_sentence.add(surface)

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_table(
        output_dir / "token_frequency.tsv",
        token_counts,
        token_by_dialect,
    )
    _write_table(
        output_dir / "lemma_frequency.tsv",
        lemma_counts,
        lemma_by_dialect,
    )

    summary = {
        "rows_seen": rows_seen,
        "rows_with_text": rows_with_text,
        "unique_tokens": len(token_counts),
        "unique_lemmas": len(lemma_counts),
        "sentences_hokkaido": sentence_counts.get("hokkaido", 0),
        "sentences_sakhalin": sentence_counts.get("sakhalin", 0),
        "sentences_other": sentence_counts.get("other", 0),
    }
    return summary


def _write_table(
    path: Path,
    totals: Counter[str],
    by_dialect: dict[str, Counter[str]],
) -> None:
    rows = totals.most_common()
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["form", "frequency", "dialect_breakdown"])
        for form, count in rows:
            parts = []
            for dialect in ("hokkaido", "sakhalin", "other"):
                n = by_dialect.get(dialect, Counter()).get(form, 0)
                if n:
                    parts.append(f"{dialect}:{n}")
            writer.writerow([form, count, "|".join(parts)])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    summary = build(args.input, args.output_dir)
    print(
        "Built ainu-corpora frequency tables:\n"
        f"  source rows: {summary['rows_seen']} ({summary['rows_with_text']} with text)\n"
        f"  sentences: hokkaido={summary['sentences_hokkaido']} "
        f"sakhalin={summary['sentences_sakhalin']} "
        f"other={summary['sentences_other']}\n"
        f"  unique tokens: {summary['unique_tokens']}\n"
        f"  unique lemmas (markers stripped): {summary['unique_lemmas']}\n"
        f"  output: {args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
