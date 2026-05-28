"""Build correspondence from Batchelor lemmas to modern-dictionary lemmas.

For every Batchelor 1938 entry we:
  1. Compute orthography-normalized lemma + variants (Batchelor → modern
     academic conventions). See batchelor_normalize_lib.
  2. Look the variants up in Nakagawa 1995 (Chitose), Kayano 1996, and
     Tamura 1996. Each modern dictionary stores its lemma in slightly
     different columns; we build a per-dict {lemma → [rows]} index.
  3. Disambiguate with English/Japanese gloss overlap when a candidate
     dictionary has multiple entries under the same lemma. Overlap is
     measured by token-set Jaccard on lowercased glosses.
  4. Emit one TSV row per Batchelor entry with:
       batchelor_lemma | batchelor_normalized | batchelor_kana |
       batchelor_gloss_brief | match_modern_lemma | match_modern_source |
       match_modern_definition | confidence

Confidence is 1.0 for exact normalized match + non-zero gloss overlap,
0.6-0.9 for normalized match without gloss overlap (or only kana
agreement), and lower for fallback / variant matches.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

from dictionary.batchelor_normalize_lib import normalize_lemma, variants

csv.field_size_limit(sys.maxsize)

DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
BATCHELOR_TSV = (
    DICT_ROOT
    / "1938_Batchelor_Ainu-English-Japanese-Dictionary-4ed"
    / "original.tsv"
)
OUT_TSV = (
    DICT_ROOT
    / "1938_Batchelor_Ainu-English-Japanese-Dictionary-4ed"
    / "modern_correspondence.tsv"
)


def tokenize(text: str) -> set[str]:
    return {
        tok.lower()
        for tok in re.findall(r"[A-Za-z぀-ヿ一-鿿]{2,}", text or "")
    }


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


_SUPERSCRIPTS = "¹²³⁴⁵⁶⁷⁸⁹⁰"


def _norm_key(s: str) -> str:
    """Lookup key: lowercase, no trailing punctuation, no `=` clitic marker,
    no superscript/index digits (Nakagawa uses `kor²` for the 2nd sense)."""
    s = s.lower().strip().rstrip(",.;:'’`")
    s = s.lstrip("=").rstrip("=")
    # Strip trailing numeric/superscript subscripts (kor² kor³ etc.).
    s = s.rstrip(_SUPERSCRIPTS + "0123456789")
    return s


def _variants_extra(latn: str) -> list[str]:
    """For Batchelor lemmas, also try dropping a final vowel — Batchelor
    often spells modern bare consonant stems with a trailing /a/e/i/o/u/
    (Koro vs modern kor, Mata vs modern mat). Only the last vowel; only
    if the stem becomes ≥2 chars."""
    out = [latn]
    if len(latn) >= 3 and latn[-1] in "aeiou":
        stem = latn[:-1]
        if stem[-1] not in "aeiou":
            out.append(stem)
    return out


def load_kayano() -> dict[str, list[dict]]:
    path = DICT_ROOT / "1996_Kayano_Kayanos-Ainu-Dictionary/kayano-entries.tsv"
    idx: dict[str, list[dict]] = defaultdict(list)
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            lem = row.get("lemma", "").strip()
            if not lem:
                continue
            idx[_norm_key(lem)].append(
                {"source": "kayano", "lemma": lem, "definition": row.get("definition", "")}
            )
    return idx


def load_nakagawa() -> dict[str, list[dict]]:
    path = DICT_ROOT / "1995_Nakagawa_Ainu-Chitose-Dialect-Dictionary/nakagawa_terms.tsv"
    idx: dict[str, list[dict]] = defaultdict(list)
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            lem = row.get("latn", "").strip()
            if not lem:
                continue
            idx[_norm_key(lem)].append(
                {
                    "source": "nakagawa",
                    "lemma": lem,
                    "kana": row.get("kana", ""),
                    "pos": row.get("pos", ""),
                    "definition": row.get("definition", ""),
                }
            )
    return idx


def load_tamura() -> dict[str, list[dict]]:
    """Tamura's `translit` column is mostly katakana, not Latin. We index by
    the katakana `lemma` field instead and use the kana from Batchelor for
    matching when available.
    """
    path = DICT_ROOT / "1996_Tamura_Ainu-Saru-Dialect-Dictionary/original.tsv"
    idx: dict[str, list[dict]] = defaultdict(list)
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            lem = row.get("lemma", "").strip()
            if not lem:
                continue
            idx[lem].append(
                {
                    "source": "tamura",
                    "lemma": lem,
                    "translit": row.get("translit", ""),
                    "definition": row.get("definition", ""),
                }
            )
    return idx


def best_match(
    variants_list: list[str],
    kana: str,
    gloss_tokens: set[str],
    kayano: dict[str, list[dict]],
    nakagawa: dict[str, list[dict]],
    tamura: dict[str, list[dict]],
) -> tuple[dict | None, float]:
    """Return (best modern row, confidence)."""
    # Latin-keyed lookup first (Nakagawa, Kayano). Normalize the variant
    # casing/punctuation to match the index keys. Expand each variant by
    # also trying the bare-consonant stem (Koro → kor).
    expanded: list[str] = []
    for raw_variant in variants_list:
        norm = _norm_key(raw_variant)
        for v in _variants_extra(norm):
            if v and v not in expanded:
                expanded.append(v)
    for variant in expanded:
        for source_idx, base_conf in (
            (nakagawa, 0.85),
            (kayano, 0.85),
        ):
            hits = source_idx.get(variant)
            if not hits:
                continue
            # Rank hits by gloss overlap.
            best = None
            best_score = -1.0
            for hit in hits:
                overlap = jaccard(gloss_tokens, tokenize(hit.get("definition", "")))
                score = base_conf + 0.15 * overlap
                if overlap > 0:
                    score = min(1.0, score)
                if score > best_score:
                    best_score = score
                    best = hit
            if best is not None:
                return best, best_score
    # Kana-keyed lookup for Tamura (using the leading-kana token of Batchelor's
    # kana field, stripped of trailing punctuation).
    if kana:
        kana_head = re.match(r"[ァ-ヴーㇰ-ㇿ・]+", kana)
        if kana_head:
            hits = tamura.get(kana_head.group(0))
            if hits:
                best = None
                best_score = -1.0
                for hit in hits:
                    overlap = jaccard(gloss_tokens, tokenize(hit.get("definition", "")))
                    score = 0.7 + 0.2 * overlap
                    if score > best_score:
                        best_score = score
                        best = hit
                if best is not None:
                    return best, best_score
    return None, 0.0


def extract_brief_gloss(body: str) -> str:
    """Return a short summary of the entry body — the first English sentence
    after the POS tag, capped to ~60 chars."""
    m = re.search(
        r"\b(?:n|v|vt|vi|v\.t|v\.i|adj|adv|conj|prep|interj|part|pron|a)\b\.?\s+(.+?)\s*[.;]",
        body or "",
    )
    if m:
        text = m.group(1)
    else:
        text = body or ""
    text = text.replace("\n", " ").strip()
    if len(text) > 80:
        text = text[:77] + "..."
    return text


def main() -> None:
    kayano = load_kayano()
    nakagawa = load_nakagawa()
    tamura = load_tamura()
    print(
        f"loaded: kayano={sum(len(v) for v in kayano.values())} keys={len(kayano)}, "
        f"nakagawa={sum(len(v) for v in nakagawa.values())} keys={len(nakagawa)}, "
        f"tamura={sum(len(v) for v in tamura.values())} keys={len(tamura)}"
    )

    out_rows: list[dict[str, str]] = []
    matched = 0
    with BATCHELOR_TSV.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            lemma = row.get("lemma", "").strip()
            kana = row.get("kana", "").strip()
            body = row.get("body", "")
            if not lemma:
                continue
            norm = normalize_lemma(lemma)
            vars_ = variants(lemma)
            brief = extract_brief_gloss(body)
            gloss_tokens = tokenize(body)
            hit, conf = best_match(vars_, kana, gloss_tokens, kayano, nakagawa, tamura)
            if hit:
                matched += 1
                out_rows.append(
                    {
                        "batchelor_lemma": lemma,
                        "batchelor_normalized": norm,
                        "batchelor_kana": kana,
                        "batchelor_gloss_brief": brief,
                        "match_modern_lemma": hit.get("lemma", ""),
                        "match_modern_source": hit.get("source", ""),
                        "match_modern_definition": re.sub(
                            r"\s+", " ", hit.get("definition", "")
                        )[:200],
                        "confidence": f"{conf:.2f}",
                    }
                )
            else:
                out_rows.append(
                    {
                        "batchelor_lemma": lemma,
                        "batchelor_normalized": norm,
                        "batchelor_kana": kana,
                        "batchelor_gloss_brief": brief,
                        "match_modern_lemma": "",
                        "match_modern_source": "",
                        "match_modern_definition": "",
                        "confidence": "0.00",
                    }
                )

    columns = [
        "batchelor_lemma",
        "batchelor_normalized",
        "batchelor_kana",
        "batchelor_gloss_brief",
        "match_modern_lemma",
        "match_modern_source",
        "match_modern_definition",
        "confidence",
    ]
    with OUT_TSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(out_rows)

    print(
        f"wrote {len(out_rows)} rows; {matched} ({100*matched/len(out_rows):.1f}%) "
        f"matched a modern dictionary entry → {OUT_TSV}"
    )


if __name__ == "__main__":
    main()
