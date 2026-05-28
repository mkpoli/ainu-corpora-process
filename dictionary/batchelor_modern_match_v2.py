"""Expanded correspondence: Batchelor 1938 → every modern dictionary.

Indexes Kayano, Nakagawa, Tamura, Tomita, Silja, Tane-an, Chiri, Ota,
Asahikawa Uoi (verbs+nouns), NorthEuraLex, Loanwordbank/Wiktionary, and
the Japanese & English Wiktionaries by both Latin lemma and katakana
lemma. For each Batchelor row we try:

  1. Latin lookup against every source by normalized variants (Batchelor
     → modern academic orthography).
  2. Katakana lookup against every source's kana index, with simple kana
     normalization (drop trailing 、・,. and stretch marks).
  3. Bare-stem fallback (Koro → kor, Aini → ayn).
  4. Suffix-stripping for Kayano-style possessive forms
     (-he/-hi/-hu/-ha trailing).
  5. Optional fuzzy match (edit distance ≤ 1 on the normalized stem)
     when no exact hit is found and the stem is reasonably long.

Outputs `modern_correspondence.tsv` with one row per Batchelor entry and
columns:

  batchelor_lemma, batchelor_normalized, batchelor_kana,
  batchelor_gloss_brief, match_modern_lemma, match_modern_kana,
  match_modern_source, match_modern_definition, match_kind,
  confidence
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


# ---------- normalization helpers ----------
_SUPERSCRIPTS = "¹²³⁴⁵⁶⁷⁸⁹⁰"


def norm_latn(s: str) -> str:
    s = s.lower().strip().rstrip(",.;:'’`\"")
    s = s.strip("=")
    s = s.rstrip(_SUPERSCRIPTS + "0123456789")
    return s


_KANA_TRAILING = re.compile(r"[、,.。\s。]+$")
_KANA_HEAD_RE = re.compile(r"^[ァ-ヴーㇰ-ㇿ・]+")


def norm_kana(s: str) -> str:
    """Pull the leading katakana run, normalize."""
    if not s:
        return ""
    m = _KANA_HEAD_RE.match(s.strip())
    if not m:
        return ""
    return m.group(0)


def tokenize(text: str) -> set[str]:
    return {
        tok.lower()
        for tok in re.findall(r"[A-Za-z぀-ヿ一-鿿]{2,}", text or "")
    }


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def stem_variants(latn: str) -> list[str]:
    """Generate stem/suffix variants. latn is already lowercased."""
    out: list[str] = [latn]
    if len(latn) >= 3 and latn[-1] in "aeiou" and latn[-2] not in "aeiou":
        out.append(latn[:-1])
    # Kayano-style possessive suffixes.
    for suf in ("ha", "hi", "hu", "he", "ho"):
        if latn.endswith(suf) and len(latn) >= len(suf) + 2:
            out.append(latn[: -len(suf)])
    # Batchelor passive `a-` prefix: lemmas spelled like "aainukoro" or
    # "aakkari" are `a=` (4p) + base verb. Drop the leading `a`.
    if len(latn) >= 4 and latn[0] == "a" and latn[1] == "a":
        out.append(latn[1:])
    # Hyphenated compounds: try the head and the last morpheme separately.
    if "-" in latn:
        parts = latn.split("-")
        if len(parts) >= 2:
            head = parts[0]
            tail = parts[-1]
            if len(head) >= 2:
                out.append(head)
            if len(tail) >= 2:
                out.append(tail)
            # Also: drop a leading short single-letter morpheme like `a-`.
            if len(head) == 1:
                rest = "-".join(parts[1:])
                if rest:
                    out.append(rest)
                    out.append(rest.replace("-", ""))
    return out


def all_lookup_keys(lemma: str) -> list[str]:
    """All sensible lookup keys for a Batchelor lemma, deduplicated."""
    out: list[str] = []
    seen: set[str] = set()
    for v in variants(lemma):
        k = norm_latn(v)
        for sv in stem_variants(k):
            if sv and sv not in seen:
                seen.add(sv)
                out.append(sv)
    return out


# ---------- per-dictionary loaders ----------
def _load_tsv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


class Source:
    def __init__(self, name: str, base_conf: float = 0.85):
        self.name = name
        self.latn: dict[str, list[dict]] = defaultdict(list)
        self.kana: dict[str, list[dict]] = defaultdict(list)
        self.base_conf = base_conf

    def add(self, lemma_latn: str, lemma_kana: str, definition: str, **extra) -> None:
        rec = {
            "source": self.name,
            "lemma": lemma_latn or lemma_kana,
            "lemma_kana": lemma_kana,
            "definition": definition,
            **extra,
        }
        if lemma_latn:
            self.latn[norm_latn(lemma_latn)].append(rec)
        if lemma_kana:
            self.kana[norm_kana(lemma_kana)].append(rec)


def load_sources() -> list[Source]:
    sources: list[Source] = []

    # 1. Kayano 1996 (Latin lemma, JP definition)
    kay = Source("kayano", 0.90)
    for row in _load_tsv(DICT_ROOT / "1996_Kayano_Kayanos-Ainu-Dictionary/kayano-entries.tsv"):
        lem = row.get("lemma", "").strip()
        if lem:
            kay.add(lem, "", row.get("definition", ""))
    sources.append(kay)

    # 2. Nakagawa 1995 Chitose (kana + Latin + JP)
    nak = Source("nakagawa", 0.92)
    for row in _load_tsv(DICT_ROOT / "1995_Nakagawa_Ainu-Chitose-Dialect-Dictionary/nakagawa_terms.tsv"):
        latn = row.get("latn", "").strip()
        kana = row.get("kana", "").strip()
        if latn or kana:
            nak.add(latn, kana, row.get("definition", ""), pos=row.get("pos", ""))
    sources.append(nak)

    # 3. Tamura 1996 Saru (kana lemma, JP definition)
    tam = Source("tamura", 0.85)
    for row in _load_tsv(DICT_ROOT / "1996_Tamura_Ainu-Saru-Dialect-Dictionary/original.tsv"):
        kana = row.get("lemma", "").strip()
        if kana:
            tam.add("", kana, row.get("definition", ""), translit=row.get("translit", ""))
    sources.append(tam)

    # 4. Tomita 2021 (Latin lemma, big definition)
    tom = Source("tomita", 0.80)
    for row in _load_tsv(DICT_ROOT / "2021_Tomita_Aynu-Online-Dictionary/original.tsv"):
        lem = row.get("lemma", "").strip()
        if lem:
            tom.add(lem, "", row.get("explanation", "") + " " + row.get("etymology", ""))
    sources.append(tom)

    # 5. Silja 2023 Ainu-English (Latin + English def)
    silja = Source("silja", 0.82)
    for row in _load_tsv(DICT_ROOT / "2023_Silja_Ainu-English-Ainu-vocabulary-list/Ainu-English.tsv"):
        lem = row.get("Ainu", "").strip()
        eng = row.get("English", "")
        pos = row.get("Part of speech", "")
        if lem:
            silja.add(lem, "", f"{pos} {eng}".strip())
    sources.append(silja)

    # 6. Tane an Aynuitak-kotupte (Latin + JP)
    tane = Source("tane_an", 0.82)
    csv_path = DICT_ROOT / "2024_Tane_an_Aynuitak-kotupte_Itak-uoeroskip/ainu-glossary.csv"
    if csv_path.exists():
        with csv_path.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                lem = (row.get("ainu") or row.get("Ainu") or row.get("lemma") or "").strip()
                jdef = (row.get("japanese") or row.get("Japanese") or row.get("definition") or "").strip()
                if lem:
                    tane.add(lem, "", jdef)
    sources.append(tane)

    # 7. Asahikawa Uoi (Verbs I/II, Nouns I/II) — already in modern academic orth.
    for sub in (
        "1995_Uoi_Asahikawa-Ainu-Verbs-I",
        "1996_Uoi_Asahikawa-Ainu-Verbs-II",
        "2006_Uoi_Asahikawa-Ainu-Nouns-I",
        "2007_Uoi_Asahikawa-Ainu-Nouns-II",
    ):
        src = Source(f"asahikawa.{sub.split('_')[0]}.{sub.split('_')[-1]}", 0.85)
        for row in _load_tsv(DICT_ROOT / sub / "original.tsv"):
            lem = (row.get("lemma_normalized") or row.get("lemma") or "").strip()
            if lem:
                src.add(lem, "", row.get("body", ""))
        sources.append(src)

    # 8. NorthEuraLex 2020 Hokkaido Ainu (Latin + English concept)
    nel = Source("northeuralex", 0.80)
    for row in _load_tsv(DICT_ROOT / "2020_NorthEuraLex_Hokkaido-Ainu/original.tsv"):
        lem = row.get("lemma_raw", "") or row.get("lemma", "")
        eng = row.get("concept_en", "")
        if lem:
            nel.add(lem.strip(), "", eng)
    sources.append(nel)

    # 9. Loanwordbank Wiktionary (Latin + IPA + English)
    lwb = Source("loanwordbank", 0.78)
    for row in _load_tsv(DICT_ROOT / "XXXX_Loanwordbank_Wiktionary-Ainu/original.tsv"):
        lem = row.get("lemma", "").strip()
        if lem:
            lwb.add(lem, "", row.get("gloss_en", ""))
    sources.append(lwb)

    # 10. English Wiktionary entries
    enwikt = Source("en_wiktionary", 0.78)
    for row in _load_tsv(DICT_ROOT / "XXXX_English-Wiktionary/wiktionary-en-entries.tsv"):
        lem = row.get("lemma", "") or row.get("term", "")
        defn = row.get("definition", "") or row.get("gloss", "")
        if lem:
            enwikt.add(lem.strip(), "", defn)
    sources.append(enwikt)

    # 11. Japanese Wiktionary entries
    jawikt = Source("ja_wiktionary", 0.78)
    for row in _load_tsv(DICT_ROOT / "XXXX_Japanese-Wiktionary/wiktionary-entries.tsv"):
        lem = row.get("lemma", "") or row.get("term", "")
        defn = row.get("definition", "") or row.get("gloss", "")
        if lem:
            jawikt.add(lem.strip(), "", defn)
    sources.append(jawikt)

    # 12. Chiri 1987 categorized (4 files)
    for cat in ("animals", "human-1", "human-2", "plants"):
        c = Source(f"chiri.{cat}", 0.80)
        for row in _load_tsv(
            DICT_ROOT / "1987_Chiri_Categorized-Ainu-Dictionary" / f"chiri-{cat}-entries.tsv"
        ):
            lem = row.get("lemma", "").strip()
            if lem:
                c.add(lem, "", row.get("definition", ""))
        sources.append(c)

    # 13. Ota Japanese-Ainu dictionary (description contains Ainu words)
    # We add Ota only by *Japanese* gloss search later — not by lemma — so skip
    # adding to lemma indices here. See ota_lookup() below.

    # 14. RaccoonBend/Shibatani 605-entry list
    rb = Source("shibatani_raccoonbend", 0.78)
    for row in _load_tsv(DICT_ROOT / "1990_Shibatani_RaccoonBend-Ainu-English-Wordlist/original.tsv"):
        lem = row.get("lemma", "").strip()
        if lem:
            rb.add(lem, "", row.get("meaning_en", ""))
    sources.append(rb)

    # 15. Lexicons.ru Ainu-English (605 entries from Shibatani)
    lex = Source("lexicons_ru", 0.76)
    for row in _load_tsv(DICT_ROOT / "2024_LexiconsRu_Ainu-English-Ainu/original.tsv"):
        lem = row.get("lemma", "").strip()
        if lem:
            lex.add(lem, "", row.get("meaning_en", ""))
    sources.append(lex)

    # 16. Pannous Swadesh
    pan = Source("pannous_swadesh", 0.70)
    for row in _load_tsv(DICT_ROOT / "XXXX_PannousSwadesh_Ainu-Swadesh/original.tsv"):
        lem = row.get("ain", "").strip()
        if lem:
            pan.add(lem, "", row.get("concept_en", ""))
    sources.append(pan)

    # 17. Mukawa dialect dictionary
    muk = Source("mukawa", 0.82)
    for row in _load_tsv(DICT_ROOT / "XXXX_Chiba_Mukawa-Dialect-Japanese-Ainu-Dictionary/original.tsv"):
        lem = row.get("lemma", "").strip()
        if lem:
            muk.add(lem, "", row.get("translation", ""))
    sources.append(muk)

    return sources


# ---------- Ota reverse lookup ----------
class OtaIndex:
    """Ota's `description` column contains Ainu words inline; build a
    forward index lemma → JP gloss by extracting Latin words from
    descriptions."""

    def __init__(self):
        self.by_lemma: dict[str, list[dict]] = defaultdict(list)
        path = DICT_ROOT / "2022_Ota_Japanese-Ainu_Dictionary/original.tsv"
        if not path.exists():
            return
        WORD_RE = re.compile(r"\b([a-z][a-z\-']{2,})\b")
        with path.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                ja = row.get("title", "")
                desc = row.get("description", "")
                if not ja:
                    continue
                for word in WORD_RE.findall(desc):
                    if 3 <= len(word) <= 20:
                        self.by_lemma[word].append({"source": "ota", "lemma": word, "definition": ja})


# ---------- match logic ----------
def best_match(
    latn_keys: list[str],
    batchelor_kana: str,
    gloss_tokens: set[str],
    sources: list[Source],
    ota: OtaIndex,
) -> dict | None:
    """Return the best (highest-confidence) modern record for this Batchelor
    entry, or None."""
    best_rec = None
    best_score = -1.0

    # Latin lookups.
    for variant in latn_keys:
        if not variant:
            continue
        for src in sources:
            hits = src.latn.get(variant)
            if not hits:
                continue
            for hit in hits:
                overlap = jaccard(gloss_tokens, tokenize(hit.get("definition", "")))
                score = src.base_conf + 0.10 * overlap
                score = min(1.0, score)
                if score > best_score:
                    best_score = score
                    best_rec = {**hit, "match_kind": "latn", "score": score}

    # Kana lookups.
    kana_key = norm_kana(batchelor_kana)
    if kana_key:
        for src in sources:
            hits = src.kana.get(kana_key)
            if not hits:
                continue
            for hit in hits:
                overlap = jaccard(gloss_tokens, tokenize(hit.get("definition", "")))
                score = (src.base_conf - 0.05) + 0.15 * overlap
                score = min(1.0, score)
                if score > best_score:
                    best_score = score
                    best_rec = {**hit, "match_kind": "kana", "score": score}

    # Ota fallback (Ainu word appearing inside a Japanese description).
    for variant in latn_keys:
        if not variant or len(variant) < 3:
            continue
        hits = ota.by_lemma.get(variant)
        if not hits:
            continue
        # Pick the Ota hit with most gloss overlap.
        for hit in hits:
            overlap = jaccard(gloss_tokens, tokenize(hit.get("definition", "")))
            score = 0.65 + 0.20 * overlap
            score = min(0.95, score)
            if score > best_score:
                best_score = score
                best_rec = {**hit, "match_kind": "ota_reverse", "score": score}

    return best_rec


def extract_brief_gloss(body: str) -> str:
    m = re.search(
        r"\b(?:n|v|vt|vi|v\.t|v\.i|adj|adv|conj|prep|interj|part|pron|a)\b\.?\s+(.+?)\s*[.;]",
        body or "",
    )
    text = (m.group(1) if m else (body or "")).replace("\n", " ").strip()
    if len(text) > 80:
        text = text[:77] + "..."
    return text


def main() -> None:
    sources = load_sources()
    ota = OtaIndex()
    total_keys = sum(len(s.latn) + len(s.kana) for s in sources)
    print(
        f"loaded {len(sources)} sources, {total_keys} index entries; "
        f"ota lookup {len(ota.by_lemma)} word forms"
    )

    out_rows: list[dict[str, str]] = []
    matched = 0
    by_source: dict[str, int] = defaultdict(int)
    with BATCHELOR_TSV.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            lemma = row.get("lemma", "").strip()
            kana = row.get("kana", "").strip()
            body = row.get("body", "")
            if not lemma:
                continue
            norm = normalize_lemma(lemma)
            keys = all_lookup_keys(lemma)
            brief = extract_brief_gloss(body)
            gloss_tokens = tokenize(body) | tokenize(brief)
            hit = best_match(keys, kana, gloss_tokens, sources, ota)
            if hit:
                matched += 1
                by_source[hit["source"]] += 1
                out_rows.append(
                    {
                        "batchelor_lemma": lemma,
                        "batchelor_normalized": norm,
                        "batchelor_kana": kana,
                        "batchelor_gloss_brief": brief,
                        "match_modern_lemma": hit.get("lemma", ""),
                        "match_modern_kana": hit.get("lemma_kana", ""),
                        "match_modern_source": hit["source"],
                        "match_modern_definition": re.sub(
                            r"\s+", " ", hit.get("definition", "")
                        )[:300],
                        "match_kind": hit.get("match_kind", ""),
                        "confidence": f"{hit['score']:.2f}",
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
                        "match_modern_kana": "",
                        "match_modern_source": "",
                        "match_modern_definition": "",
                        "match_kind": "",
                        "confidence": "0.00",
                    }
                )

    columns = [
        "batchelor_lemma",
        "batchelor_normalized",
        "batchelor_kana",
        "batchelor_gloss_brief",
        "match_modern_lemma",
        "match_modern_kana",
        "match_modern_source",
        "match_modern_definition",
        "match_kind",
        "confidence",
    ]
    with OUT_TSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(out_rows)

    print(
        f"wrote {len(out_rows)} rows; {matched} ({100*matched/len(out_rows):.1f}%) "
        f"matched → {OUT_TSV}"
    )
    print("by source:")
    for src, n in sorted(by_source.items(), key=lambda kv: -kv[1]):
        print(f"  {src:30}  {n:6}")


if __name__ == "__main__":
    main()
