"""Merge per-page Gemini re-OCR outputs into the Batchelor 1938 TSV.

Reads dictionary/output/batchelor1938-reocr/page-XXX/gemini.tsv (one
entry per line, TSV `LEMMA\tカナ\tBODY`) for every page 1..681, applies
basic cleanups, and writes:
    1938_Batchelor_Ainu-English-Japanese-Dictionary-4ed/original.tsv

with columns: lemma | lemma_normalized | kana | body | page

The original bbox-layout parse output is preserved as
    .../original.bbox.tsv (backup for diffing)
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import sys
from pathlib import Path

csv.field_size_limit(sys.maxsize)

ROOT = Path(__file__).resolve().parents[1]
DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
SRC_FOLDER = DICT_ROOT / "1938_Batchelor_Ainu-English-Japanese-Dictionary-4ed"
OCR_ROOT = ROOT / "dictionary" / "output" / "batchelor1938-reocr"
TSV_OUT = SRC_FOLDER / "original.tsv"
TSV_BACKUP = SRC_FOLDER / "original.bbox.tsv"
TOTAL_PAGES = 681


def normalize_lemma(lemma: str) -> str:
    """Ainu has no /l/. Replace stray `l` with `i`, preserving case."""
    return lemma.replace("l", "i").replace("L", "I")


def clean_field(s: str) -> str:
    s = s.replace(" ", " ")  # non-breaking spaces
    return re.sub(r"\s+", " ", s).strip()


# Fallback: some Gemini outputs emit `Lemma, カナ, body` on one line without
# tabs. Recover three columns from that. Body is optional (terse entries
# may stop after the kana).
_LEMMA_PART_RE = re.compile(r"^(?P<lemma>[A-Z][A-Za-z0-9'’\-]+(?:\s+[a-zA-Z'’\-]+){0,3})\s*,\s*")
_KANA_PART_RE = re.compile(r"^(?P<kana>[ァ-ヴーㇰ-ㇿ・、][^,]*?)\s*(?:[,.]|$)")


def maybe_resplit(lemma: str, kana: str, body: str) -> tuple[str, str, str]:
    """If the lemma column still contains an embedded `Lemma, カナ[, body]`
    pattern (Gemini emitted it without tabs), split into proper fields.
    Runs both when the body/kana are empty AND when they're populated but
    the lemma still has trailing text."""
    text = lemma
    m1 = _LEMMA_PART_RE.match(text)
    if not m1:
        return lemma, kana, body
    rest = text[m1.end():]
    m2 = _KANA_PART_RE.match(rest)
    if not m2:
        return lemma, kana, body
    new_lemma = clean_field(m1["lemma"])
    new_kana = clean_field(m2["kana"])
    # If a body was already supplied via the tab, prefer it; otherwise pull
    # the rest from the lemma string.
    extra = clean_field(rest[m2.end():])
    if body and extra and body != extra:
        # Concatenate — sometimes Gemini emitted both halves.
        new_body = clean_field(body + " " + extra)
    else:
        new_body = body or extra
    return new_lemma, kana or new_kana, new_body


def main() -> None:
    # Back up existing original.tsv as the bbox-layout reference.
    if TSV_OUT.exists() and not TSV_BACKUP.exists():
        shutil.copy2(TSV_OUT, TSV_BACKUP)

    rows: list[dict[str, str]] = []
    page_costs: list[tuple[int, float]] = []
    failed_pages: list[int] = []
    no_entry_pages: list[int] = []
    total_cost = 0.0

    for page in range(1, TOTAL_PAGES + 1):
        d = OCR_ROOT / f"page-{page:03d}"
        tsv = d / "gemini.tsv"
        if not tsv.exists():
            failed_pages.append(page)
            continue
        text = tsv.read_text(encoding="utf-8").strip()
        if text == "NO_ENTRIES":
            no_entry_pages.append(page)
            continue
        # Pull cost if available.
        info = d / "gemini.info"
        if info.exists():
            for line in info.read_text(encoding="utf-8").splitlines():
                if line.startswith("response_cost="):
                    try:
                        c = float(line.split("=", 1)[1])
                        page_costs.append((page, c))
                        total_cost += c
                    except ValueError:
                        pass
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line == "NO_ENTRIES":
                continue
            # Sometimes Gemini adds bullet/quote prefixes — strip them.
            line = line.lstrip("-•* ")
            parts = line.split("\t")
            while len(parts) < 3:
                parts.append("")
            lemma = clean_field(parts[0])
            kana = clean_field(parts[1])
            body = clean_field("\t".join(parts[2:]))
            lemma, kana, body = maybe_resplit(lemma, kana, body)
            if not lemma:
                continue
            rows.append(
                {
                    "lemma": lemma,
                    "lemma_normalized": normalize_lemma(lemma),
                    "kana": kana,
                    "body": body,
                    "page": str(page),
                }
            )

    with TSV_OUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["lemma", "lemma_normalized", "kana", "body", "page"],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "rows": len(rows),
        "pages_processed": TOTAL_PAGES - len(failed_pages) - len(no_entry_pages),
        "failed_pages": failed_pages,
        "no_entry_pages": no_entry_pages,
        "total_cost_usd": round(total_cost, 4),
    }
    (OCR_ROOT / "merge_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
