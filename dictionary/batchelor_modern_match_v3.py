"""Batchelor 1938 → modern correspondence, v3.

Adds three new strategies on top of v2:

  A. **Broader morphological prefix stripping**. Many Batchelor entries
     are passive/reflexive/causative derivations of base verbs (e.g.
     `Yaikahawashpa` = yay= + kahawaspa, `Aapkara` = a= + apkara,
     `Ukoyki` = uko= + ki). We strip a configured list of well-known
     prefixes — a, ae, ai, an, e, i, ko, eko, esi, iko, yay, uko, uwe,
     sir, ar, eu — and add the bare stem to the lookup-key list. We
     only strip when the residue stays ≥ 3 chars.
  B. **Edit-distance-1 fuzzy fallback**. For unmatched lemmas of length
     ≥ 5 we generate the set of single-edit neighbours (one
     substitution, deletion, or insertion of an Ainu-alphabet letter)
     and check whether any of them is a known modern lemma. Gloss
     overlap is required (≥0.10 Jaccard with the modern definition) to
     keep the false-positive rate down.
  C. **Brief-gloss reverse lookup**. Build inverted indices from
     English / Japanese definition tokens → modern lemma. For an
     unmatched Batchelor row, take its `body` text, extract the first
     short English gloss and the first Japanese phrase, intersect with
     the inverted index, and rank candidates by token-overlap score.
"""

from __future__ import annotations

import csv
import re
import string
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
    if not s:
        return ""
    m = _KANA_HEAD_RE.match(s.strip())
    if not m:
        return ""
    return m.group(0)


# Latin Ainu alphabet (post-normalization).
AINU_LETTERS = "aceèhiklmnoprstuwy'-"

# Stop-words for English-gloss reverse lookup — don't index on these.
EN_STOP = {
    "a", "an", "and", "the", "to", "of", "is", "it", "in", "on", "for",
    "as", "or", "by", "with", "from", "that", "this", "be", "are", "was",
    "were", "him", "her", "his", "she", "he", "they", "them", "we", "our",
    "you", "your", "i", "my", "me", "do", "did", "does", "not", "no",
    "any", "some", "all", "but", "if", "when", "where", "what", "who",
    "which", "have", "has", "had", "been", "being", "one's", "ones",
    "n", "v", "vt", "vi", "adj", "adv", "conj", "prep", "interj", "part",
    "pron", "ph",
}

# Japanese function tokens to filter out of reverse indices.
JA_STOP = {
    "の", "に", "を", "は", "が", "と", "で", "から", "まで", "や",
    "そして", "また", "など", "こと", "もの", "ため", "ある", "いる",
    "する", "なる", "れる", "られる", "せる", "させる",
}


def tokenize_en(text: str) -> set[str]:
    return {
        tok.lower().strip("',.;:!?\"")
        for tok in re.findall(r"[A-Za-z'\-]{3,}", text or "")
    } - EN_STOP


def tokenize_ja(text: str) -> set[str]:
    # 2-gram CJK + standalone runs of 2+ kanji/kana.
    out: set[str] = set()
    for run in re.findall(r"[一-鿿ぁ-ゖァ-ヺ]{2,}", text or ""):
        if run not in JA_STOP and len(run) >= 2:
            out.add(run)
    return out


def tokenize(text: str) -> set[str]:
    return tokenize_en(text) | tokenize_ja(text)


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ---------- prefix stripping ----------
# Known Ainu morpheme-initial elements. Listed longest-first so we try
# `ikoy` before `i`. Strip is only valid when the residue is ≥3 chars
# AND the residue starts with a consonant or vowel that yields a plausible
# Ainu morpheme shape.
KNOWN_PREFIXES = (
    "yayko", "yaykoy",
    "ikoy", "ikoy",
    "ako", "aki", "ane", "ami", "ane", "asi",
    "yay", "yai", "uko", "uwe", "sir", "esi", "eko", "eu", "an",
    "ae", "ai", "ar", "ko",
    "ku", "e", "i", "a",
)


def strip_prefix_variants(lemma: str) -> list[str]:
    """Return additional bare-stem keys after morpheme prefix stripping."""
    out: list[str] = []
    seen: set[str] = set()
    for pref in KNOWN_PREFIXES:
        if lemma.startswith(pref):
            stem = lemma[len(pref):].lstrip("'-")
            if len(stem) >= 3 and stem[0] in AINU_LETTERS and stem not in seen:
                seen.add(stem)
                out.append(stem)
    return out


def stem_variants(latn: str) -> list[str]:
    out: list[str] = [latn]
    if len(latn) >= 3 and latn[-1] in "aeiou" and latn[-2] not in "aeiou":
        out.append(latn[:-1])
    for suf in ("ha", "hi", "hu", "he", "ho"):
        if latn.endswith(suf) and len(latn) >= len(suf) + 2:
            out.append(latn[: -len(suf)])
    # Hyphen heads/tails.
    if "-" in latn:
        parts = latn.split("-")
        if len(parts) >= 2:
            head = parts[0]
            tail = parts[-1]
            if len(head) >= 2:
                out.append(head)
            if len(tail) >= 2:
                out.append(tail)
            if len(head) == 1:
                rest = "-".join(parts[1:])
                if rest:
                    out.append(rest)
                    out.append(rest.replace("-", ""))
    out.extend(strip_prefix_variants(latn))
    return out


def all_lookup_keys(lemma: str) -> list[str]:
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
        self.en_index: dict[str, list[dict]] = defaultdict(list)
        self.ja_index: dict[str, list[dict]] = defaultdict(list)
        self.base_conf = base_conf
        self.lemma_set: set[str] = set()

    def add(self, lemma_latn: str, lemma_kana: str, definition: str, **extra) -> None:
        rec = {
            "source": self.name,
            "lemma": lemma_latn or lemma_kana,
            "lemma_kana": lemma_kana,
            "definition": definition,
            **extra,
        }
        if lemma_latn:
            k = norm_latn(lemma_latn)
            self.latn[k].append(rec)
            self.lemma_set.add(k)
        if lemma_kana:
            self.kana[norm_kana(lemma_kana)].append(rec)
        # Reverse-gloss index: only attach if there's a Latin lemma to point at,
        # otherwise kana lemma. Bound by 6 tokens to avoid noise.
        en_tokens = list(tokenize_en(definition))[:6]
        for tok in en_tokens:
            if 3 <= len(tok) <= 20:
                self.en_index[tok].append(rec)
        ja_tokens = list(tokenize_ja(definition))[:6]
        for tok in ja_tokens:
            self.ja_index[tok].append(rec)


def load_sources() -> list[Source]:
    sources: list[Source] = []

    kay = Source("kayano", 0.90)
    for row in _load_tsv(DICT_ROOT / "1996_Kayano_Kayanos-Ainu-Dictionary/kayano-entries.tsv"):
        lem = row.get("lemma", "").strip()
        if lem:
            kay.add(lem, "", row.get("definition", ""))
    sources.append(kay)

    nak = Source("nakagawa", 0.92)
    for row in _load_tsv(DICT_ROOT / "1995_Nakagawa_Ainu-Chitose-Dialect-Dictionary/nakagawa_terms.tsv"):
        latn = row.get("latn", "").strip()
        kana = row.get("kana", "").strip()
        if latn or kana:
            nak.add(latn, kana, row.get("definition", ""), pos=row.get("pos", ""))
    sources.append(nak)

    tam = Source("tamura", 0.85)
    for row in _load_tsv(DICT_ROOT / "1996_Tamura_Ainu-Saru-Dialect-Dictionary/original.tsv"):
        kana = row.get("lemma", "").strip()
        if kana:
            tam.add(row.get("translit", "").strip(), kana, row.get("definition", ""))
    sources.append(tam)

    tom = Source("tomita", 0.80)
    for row in _load_tsv(DICT_ROOT / "2021_Tomita_Aynu-Online-Dictionary/original.tsv"):
        lem = row.get("lemma", "").strip()
        if lem:
            tom.add(lem, "", row.get("explanation", "") + " " + row.get("etymology", ""))
    sources.append(tom)

    silja = Source("silja", 0.82)
    for row in _load_tsv(DICT_ROOT / "2023_Silja_Ainu-English-Ainu-vocabulary-list/Ainu-English.tsv"):
        lem = row.get("Ainu", "").strip()
        eng = row.get("English", "")
        pos = row.get("Part of speech", "")
        if lem:
            silja.add(lem, "", f"{pos} {eng}".strip())
    sources.append(silja)

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

    nel = Source("northeuralex", 0.80)
    for row in _load_tsv(DICT_ROOT / "2020_NorthEuraLex_Hokkaido-Ainu/original.tsv"):
        lem = row.get("lemma_raw", "") or row.get("lemma", "")
        eng = row.get("concept_en", "")
        if lem:
            nel.add(lem.strip(), "", eng)
    sources.append(nel)

    lwb = Source("loanwordbank", 0.78)
    for row in _load_tsv(DICT_ROOT / "XXXX_Loanwordbank_Wiktionary-Ainu/original.tsv"):
        lem = row.get("lemma", "").strip()
        if lem:
            lwb.add(lem, "", row.get("gloss_en", ""))
    sources.append(lwb)

    enwikt = Source("en_wiktionary", 0.78)
    for row in _load_tsv(DICT_ROOT / "XXXX_English-Wiktionary/wiktionary-en-entries.tsv"):
        lem = row.get("lemma", "") or row.get("term", "")
        defn = row.get("definition", "") or row.get("gloss", "")
        if lem:
            enwikt.add(lem.strip(), "", defn)
    sources.append(enwikt)

    jawikt = Source("ja_wiktionary", 0.78)
    for row in _load_tsv(DICT_ROOT / "XXXX_Japanese-Wiktionary/wiktionary-entries.tsv"):
        lem = row.get("lemma", "") or row.get("term", "")
        defn = row.get("definition", "") or row.get("gloss", "")
        if lem:
            jawikt.add(lem.strip(), "", defn)
    sources.append(jawikt)

    for cat in ("animals", "human-1", "human-2", "plants"):
        c = Source(f"chiri.{cat}", 0.80)
        for row in _load_tsv(
            DICT_ROOT / "1987_Chiri_Categorized-Ainu-Dictionary" / f"chiri-{cat}-entries.tsv"
        ):
            lem = row.get("lemma", "").strip()
            if lem:
                c.add(lem, "", row.get("definition", ""))
        sources.append(c)

    rb = Source("shibatani_raccoonbend", 0.78)
    for row in _load_tsv(DICT_ROOT / "1990_Shibatani_RaccoonBend-Ainu-English-Wordlist/original.tsv"):
        lem = row.get("lemma", "").strip()
        if lem:
            rb.add(lem, "", row.get("meaning_en", ""))
    sources.append(rb)

    lex = Source("lexicons_ru", 0.76)
    for row in _load_tsv(DICT_ROOT / "2024_LexiconsRu_Ainu-English-Ainu/original.tsv"):
        lem = row.get("lemma", "").strip()
        if lem:
            lex.add(lem, "", row.get("meaning_en", ""))
    sources.append(lex)

    pan = Source("pannous_swadesh", 0.70)
    for row in _load_tsv(DICT_ROOT / "XXXX_PannousSwadesh_Ainu-Swadesh/original.tsv"):
        lem = row.get("ain", "").strip()
        if lem:
            pan.add(lem, "", row.get("concept_en", ""))
    sources.append(pan)

    muk = Source("mukawa", 0.82)
    for row in _load_tsv(DICT_ROOT / "XXXX_Chiba_Mukawa-Dialect-Japanese-Ainu-Dictionary/original.tsv"):
        lem = row.get("lemma", "").strip()
        if lem:
            muk.add(lem, "", row.get("translation", ""))
    sources.append(muk)

    # 18. Kanazawa NINJAL Topical (Latin lemma, JP translation)
    kan = Source("kanazawa_ninjal", 0.78)
    for row in _load_tsv(DICT_ROOT / "1898_Kanazawa_NINJAL-Topical-Ainu-Conversation-Dictionary/original.tsv"):
        lem = row.get("lemma", "").strip()
        if lem:
            kan.add(lem, "", row.get("translation", ""))
    sources.append(kan)

    # 19. Urakawa private (kana lemma, JP gloss)
    ura = Source("urakawa", 0.78)
    for row in _load_tsv(DICT_ROOT / "1985_Urakawa_Private-Ainu-Dictionary/original.tsv"):
        kana = row.get("lemma_kana", "").strip()
        if kana:
            ura.add("", kana, row.get("gloss_ja", ""))
    sources.append(ura)

    # 20. Akulov Russian-Ainu (Latin lemma in `ain` column)
    aku = Source("akulov", 0.72)
    for row in _load_tsv(DICT_ROOT / "2009_Akulov_Russian-Ainu-Dictionary/original.tsv"):
        ain = row.get("ain", "").strip()
        rus = (row.get("rus", "") + " " + row.get("rus_gloss", "")).strip()
        if ain:
            # Some entries are multi-word phrases — take first token too
            aku.add(ain, "", rus)
            head = ain.split()[0] if ain.split() else ain
            if head != ain and len(head) > 2:
                aku.add(head, "", rus)
    sources.append(aku)

    # 21. ASJP varieties (multi-dialect Latin forms)
    asjp = Source("asjp", 0.65)
    for row in _load_tsv(DICT_ROOT / "2020_ASJP_Ainu-Varieties/original.tsv"):
        lem = (row.get("lemma") or row.get("asjp_form") or "").strip()
        cpt = row.get("concept_en", "")
        if lem:
            asjp.add(lem, "", cpt)
    sources.append(asjp)

    # 22. Bugaeva ValPaL verbs (Latin lemma)
    bug = Source("bugaeva_valpal", 0.85)
    for row in _load_tsv(DICT_ROOT / "2013_Bugaeva_ValPaL-Ainu-Verbs/original.tsv"):
        lem = (row.get("lemma") or row.get("lemma_raw") or "").strip()
        if lem:
            bug.add(lem, "", row.get("meaning_en", ""))
    sources.append(bug)

    # 23. Dobrotvorsky (Latin lemma, Russian def)
    dob = Source("dobrotvorsky", 0.70)
    for row in _load_tsv(DICT_ROOT / "1875_Dobrotvorsky_Ainu-Russian-Dictionary/original.tsv"):
        lem = row.get("lemma", "").strip()
        if lem:
            dob.add(lem, "", row.get("body", ""))
    sources.append(dob)

    # 24. Vovin Proto-Ainu (Latin lemma)
    vov = Source("vovin_proto", 0.72)
    for row in _load_tsv(DICT_ROOT / "1993_Vovin_Proto-Ainu-ABVD/original.tsv"):
        lem = (row.get("lemma") or row.get("form") or "").strip()
        if lem:
            vov.add(lem, "", row.get("concept_en", "") or row.get("meaning", ""))
    sources.append(vov)

    # 25. Torii Kuril wordlist
    tor = Source("torii_kuril", 0.65)
    for row in _load_tsv(DICT_ROOT / "1903_Torii_Kuril-Ainu_wordlist/original.tsv"):
        lem = (row.get("lemma") or row.get("ainu") or "").strip()
        if lem:
            tor.add(lem, "", row.get("translation", "") or row.get("japanese", ""))
    sources.append(tor)

    # 26. Translation Directory Wikipedia (Latin + EN gloss)
    tdw = Source("wikipedia_td", 0.70)
    for row in _load_tsv(DICT_ROOT / "2009_TranslationDirectory_Wikipedia-Ainu-English/original.tsv"):
        lem = (row.get("lemma") or row.get("ainu") or "").strip()
        if lem:
            tdw.add(lem, "", row.get("english", "") or row.get("translation", ""))
    sources.append(tdw)

    # 27. Compilation Ainu Dialect Database — Hattori 1964 + later sheets.
    # Each row has multi-dialect Latin forms keyed by Japanese gloss.
    # Extract every plausible Latin lemma per row and index against the
    # Japanese gloss as definition.
    dia = Source("dialect_db", 0.72)
    _add_compilation_sheets(dia, DICT_ROOT / "XXXX_Compilation_Ainu-Dialect-Database/sheets")
    sources.append(dia)

    # 28. Compilation Ainu Old Documents — similar structure.
    old = Source("old_documents", 0.68)
    _add_compilation_sheets(old, DICT_ROOT / "XXXX_Compilation_Ainu-Old-Documents/sheets")
    sources.append(old)

    # 29. Shimabukuro Proto-Ainu Swadesh
    sha = Source("shimabukuro_proto", 0.65)
    for row in _load_tsv(DICT_ROOT / "2015_Shimabukuro_Proto-Ainu-Swadesh/original.tsv"):
        lem = (row.get("lemma") or row.get("form") or "").strip()
        if lem:
            sha.add(lem, "", row.get("concept_en", "") or row.get("meaning", ""))
    sources.append(sha)

    # 30. Mizushina Kuril Meteorology
    miz = Source("mizushina_kuril", 0.60)
    for row in _load_tsv(DICT_ROOT / "1893_Mizushina_Kuril-Ainu-Meteorology/original.tsv"):
        lem = (row.get("lemma") or row.get("ainu") or "").strip()
        if lem:
            miz.add(lem, "", row.get("translation", "") or row.get("japanese", ""))
    sources.append(miz)

    # 31. Omniglot numerals
    omn = Source("omniglot_numerals", 0.65)
    for row in _load_tsv(DICT_ROOT / "XXXX_Omniglot_Ainu-Numerals/original.tsv"):
        lem = (row.get("lemma") or row.get("ainu") or "").strip()
        if lem:
            omn.add(lem, "", row.get("english", "") or row.get("number", ""))
    sources.append(omn)

    return sources


# Plausible Latin Ainu form regex for compilation-sheet column scanning.
_LATIN_FORM_RE = re.compile(r"[a-zA-Z][a-zA-Z'\-́̀̄́̀áéíóú]{2,}")
# Anywhere matches like "sapá" or "''otop" or "pake".
_LATIN_TOKEN_RE = re.compile(r"['ʼ`]*([A-Za-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ][A-Za-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ'\-]{1,})")


def _strip_diacritics(s: str) -> str:
    import unicodedata
    nfd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def _add_compilation_sheets(src: "Source", folder: Path) -> None:
    """Scan every .tsv in `folder`; treat header columns as fields, pull
    Latin forms from cells, JP gloss from the rest. Best-effort: we treat
    any short Latin-looking token as a candidate form."""
    if not folder.exists():
        return
    for tsv in sorted(folder.glob("*.tsv")):
        with tsv.open(encoding="utf-8", errors="replace") as fh:
            reader = csv.reader(fh, delimiter="\t")
            header = next(reader, None)
            if not header:
                continue
            # Identify columns containing 'ja' / 日本語 / 意味 / 単語 vs the rest.
            ja_idxs: list[int] = []
            for i, h in enumerate(header):
                h_low = (h or "").lower()
                if (
                    "意味" in (h or "")
                    or "単語" in (h or "")
                    or "和" in (h or "")
                    or "ja" in h_low
                    or "japanese" in h_low
                    or "english" in h_low
                    or "en_" in h_low
                ):
                    ja_idxs.append(i)
            for row in reader:
                if not row:
                    continue
                ja_def_parts = [row[i] for i in ja_idxs if i < len(row) and row[i]]
                ja_def = " / ".join(ja_def_parts)
                # Scan every cell for Latin-looking Ainu forms.
                for cell in row:
                    if not cell or any(ord(c) > 127 and not _is_latin_ext(c) for c in cell):
                        # Cell likely contains kanji/kana – split off Latin runs.
                        pass
                    for m in _LATIN_TOKEN_RE.finditer(cell):
                        tok = m.group(1)
                        clean = _strip_diacritics(tok).lower().replace("'", "").replace("''", "")
                        clean = clean.strip("-")
                        # Drop English/Japanese helper tokens that aren't Ainu forms.
                        if 3 <= len(clean) <= 25 and clean.isascii() and not _looks_english(clean):
                            src.add(clean, "", ja_def or "")


def _is_latin_ext(c: str) -> bool:
    return c in "àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿĀāĒēĪīŌōŪū"


_ENGLISH_BLOCKLIST = {
    "the", "and", "of", "to", "in", "is", "for", "with", "from", "this",
    "that", "as", "an", "by", "or", "on", "at", "be", "are", "was", "were",
    "head", "hair", "body", "hand", "foot", "eye", "ear", "nose", "mouth",
    "see", "use", "name", "type", "var", "etc", "see", "old", "new", "one",
    "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "man", "woman", "child", "tree", "water", "fire", "wind",
}


def _looks_english(s: str) -> bool:
    return s.lower() in _ENGLISH_BLOCKLIST


class OtaIndex:
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


# ---------- edit-distance-1 fuzzy ----------
def edit1_neighbors(s: str) -> set[str]:
    """All single-edit (sub/ins/del) neighbors of `s` using AINU_LETTERS."""
    out: set[str] = set()
    letters = AINU_LETTERS
    for i in range(len(s)):
        out.add(s[:i] + s[i + 1:])  # delete
        for c in letters:
            if c != s[i]:
                out.add(s[:i] + c + s[i + 1:])  # substitute
    for i in range(len(s) + 1):
        for c in letters:
            out.add(s[:i] + c + s[i:])  # insert
    out.discard(s)
    out.discard("")
    return out


def fuzzy_lookup(
    keys: list[str],
    gloss_tokens: set[str],
    sources: list[Source],
) -> dict | None:
    """Edit-distance-1 fuzzy match against any source's Latin lemma index.
    Requires gloss overlap to claim a hit."""
    best_rec = None
    best_score = -1.0
    for k in keys:
        if len(k) < 5:
            continue
        nbrs = edit1_neighbors(k)
        for src in sources:
            for nb in nbrs:
                hits = src.latn.get(nb)
                if not hits:
                    continue
                for hit in hits:
                    overlap = jaccard(gloss_tokens, tokenize(hit.get("definition", "")))
                    if overlap < 0.10:
                        continue
                    score = (src.base_conf - 0.20) + 0.20 * overlap
                    score = min(0.90, score)
                    if score > best_score:
                        best_score = score
                        best_rec = {**hit, "match_kind": "fuzzy_edit1", "score": score}
    return best_rec


# ---------- reverse-gloss lookup ----------
_REVERSE_GLOSS_BLOCKED_SOURCES = {"asjp", "pannous_swadesh", "shimabukuro_proto"}


def reverse_gloss_lookup(
    en_tokens: set[str],
    ja_tokens: set[str],
    sources: list[Source],
) -> dict | None:
    """Find a modern entry whose definition tokens best overlap with the
    Batchelor entry's gloss. Excludes Swadesh-concept sources (asjp /
    pannous / shimabukuro) — their wildcard concepts (`*one`, `*water`)
    produce spurious overlaps.

    Quality bar: ≥3 weighted shared tokens AND Jaccard ≥ 0.20 of the
    candidate's definition with the union of Batchelor's gloss tokens.
    Confidence is capped at 0.75 so reverse_gloss matches stay clearly
    distinguishable from direct lemma matches."""
    best_rec = None
    best_score = -1.0
    candidates: dict[tuple[str, str], int] = defaultdict(int)
    candidate_recs: dict[tuple[str, str], dict] = {}

    for tok in en_tokens:
        for src in sources:
            if src.name in _REVERSE_GLOSS_BLOCKED_SOURCES:
                continue
            for rec in src.en_index.get(tok, ()):
                key = (rec["source"], rec.get("lemma") or rec.get("lemma_kana") or "")
                candidates[key] += 1
                candidate_recs.setdefault(key, rec)
    for tok in ja_tokens:
        for src in sources:
            if src.name in _REVERSE_GLOSS_BLOCKED_SOURCES:
                continue
            for rec in src.ja_index.get(tok, ()):
                key = (rec["source"], rec.get("lemma") or rec.get("lemma_kana") or "")
                candidates[key] += 2
                candidate_recs.setdefault(key, rec)

    for key, weight in candidates.items():
        if weight < 3:
            continue
        rec = candidate_recs[key]
        # Filter out trivially short / placeholder definitions.
        defn = rec.get("definition", "") or ""
        if len(defn.strip()) < 3:
            continue
        defn_tokens = tokenize(defn)
        overlap = jaccard(en_tokens | ja_tokens, defn_tokens)
        if overlap < 0.20:
            continue
        src_conf = 0.50
        score = src_conf + 0.25 * overlap
        score = min(0.75, score)
        if score > best_score:
            best_score = score
            best_rec = {**rec, "match_kind": "reverse_gloss", "score": score}
    return best_rec


# ---------- match logic ----------
def best_match(
    latn_keys: list[str],
    batchelor_kana: str,
    gloss_tokens: set[str],
    sources: list[Source],
    ota: OtaIndex,
) -> dict | None:
    best_rec = None
    best_score = -1.0

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

    for variant in latn_keys:
        if not variant or len(variant) < 3:
            continue
        hits = ota.by_lemma.get(variant)
        if not hits:
            continue
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
    en_idx = sum(len(s.en_index) for s in sources)
    ja_idx = sum(len(s.ja_index) for s in sources)
    print(
        f"loaded {len(sources)} sources, {total_keys} index entries; "
        f"ota lookup {len(ota.by_lemma)} word forms; "
        f"reverse-gloss index: {en_idx} EN tokens, {ja_idx} JA tokens"
    )

    out_rows: list[dict[str, str]] = []
    matched = 0
    by_source: dict[str, int] = defaultdict(int)
    by_kind: dict[str, int] = defaultdict(int)
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

            # Fallback 1: edit-distance-1 against modern lemmas.
            if not hit:
                hit = fuzzy_lookup(keys, gloss_tokens, sources)

            # Fallback 2: reverse gloss lookup (EN+JA token overlap).
            if not hit:
                en_tokens = tokenize_en(body) | tokenize_en(brief)
                ja_tokens = tokenize_ja(body) | tokenize_ja(brief)
                hit = reverse_gloss_lookup(en_tokens, ja_tokens, sources)

            if hit:
                matched += 1
                by_source[hit["source"]] += 1
                by_kind[hit.get("match_kind", "")] += 1
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
    print("by match kind:")
    for k, n in sorted(by_kind.items(), key=lambda kv: -kv[1]):
        print(f"  {k:20}  {n:6}")


if __name__ == "__main__":
    main()
