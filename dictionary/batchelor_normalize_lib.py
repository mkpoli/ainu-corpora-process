"""Map Batchelor (1889-1938) Ainu orthography to standard modern academic form.

Batchelor's romanization predates the Hattori 1964 conventions used by modern
dictionaries (Kayano, Tamura, Nakagawa, Bugaeva, NINJAL). The mapping is
mostly mechanical but has a few judgement-call edge cases.

Rules applied in order (case-preserving where possible):

1.  Digraphs:
      tch       → cc        (geminated affricate /cc/)
      ch        → c         (affricate /c/ = [tʃ])
      sh        → s         (palatal sibilant /s/ when followed by /i/)
      ts        → c         (Batchelor sometimes writes ts where /c/ is meant)
2.  Voiced ↔ voiceless obstruents (voicing is non-phonemic in Ainu):
      b → p, d → t, g → k, z → s, j → c
3.  Vowel-glide codas:
      Vi followed by consonant or word-end  → Vy   (kamui  → kamuy)
      Vu followed by consonant or word-end  → Vw   (chau   → caw)
    where V ∈ {a, e, i, o, u} (and corresponding V ≠ second vowel).
4.  Macron-marked long vowels → doubled vowels:
      ā→aa, ē→ee, ī→ii, ō→oo, ū→uu
5.  Hyphen handling: kept by default; an optional pass collapses them for
    bare-stem comparison.

The function returns the normalized lemma; a second function returns a list
of variants (with and without hyphens, voicing kept vs collapsed) so a
caller can probe modern dictionaries for the best match.
"""

from __future__ import annotations

import re
import unicodedata


_DIGRAPHS = [
    ("tch", "cc"),
    ("Tch", "Cc"),
    ("TCH", "CC"),
    ("ch", "c"),
    ("Ch", "C"),
    ("CH", "C"),
    ("sh", "s"),
    ("Sh", "S"),
    ("SH", "S"),
    ("ts", "c"),
    ("Ts", "C"),
    ("TS", "C"),
]

_VOICED = str.maketrans(
    {
        "b": "p",
        "B": "P",
        "d": "t",
        "D": "T",
        "g": "k",
        "G": "K",
        "z": "s",
        "Z": "S",
        "j": "c",
        "J": "C",
    }
)

# Ainu has no /l/ phoneme; any `l` in a lemma is an OCR slip for `i`.
_NON_AINU_LETTERS = str.maketrans({"l": "i", "L": "I"})

# Coda glide rules — apply after the consonant substitutions so we don't get
# false matches inside `ch`, `sh`, etc.
# Vi → Vy and Vu → Vw at word/morpheme boundary (before consonant or end).
_CODA_I = re.compile(r"([aeouAEOU])i(?=$|[^aeiouAEIOUyYwW])")
_CODA_U = re.compile(r"([aeioAEIO])u(?=$|[^aeiouAEIOUyYwW])")

# Macrons: standard Unicode `LATIN SMALL LETTER A WITH MACRON` etc.
_MACRON_MAP = {
    "ā": "aa",
    "ē": "ee",
    "ī": "ii",
    "ō": "oo",
    "ū": "uu",
    "Ā": "AA",
    "Ē": "EE",
    "Ī": "II",
    "Ō": "OO",
    "Ū": "UU",
}


def _replace_digraphs(text: str) -> str:
    for old, new in _DIGRAPHS:
        text = text.replace(old, new)
    return text


def _replace_macrons(text: str) -> str:
    # Normalize precomposed forms; map both NFC and NFD.
    text = unicodedata.normalize("NFC", text)
    for old, new in _MACRON_MAP.items():
        text = text.replace(old, new)
    return text


def _replace_codas(text: str) -> str:
    text = _CODA_I.sub(r"\1y", text)
    text = _CODA_U.sub(r"\1w", text)
    return text


def normalize_lemma(lemma: str, *, devoice: bool = True, codas: bool = True) -> str:
    """Apply Batchelor → modern academic orthography rules.

    `devoice=False` keeps b/d/g/z/j intact (useful if you want to inspect
    Batchelor's voicing decisions). `codas=False` keeps trailing i/u
    (useful for comparing with Kayano which doesn't use y/w codas).
    """
    s = lemma
    s = s.translate(_NON_AINU_LETTERS)
    s = _replace_macrons(s)
    s = _replace_digraphs(s)
    if devoice:
        s = s.translate(_VOICED)
    if codas:
        s = _replace_codas(s)
    return s


def variants(lemma: str) -> list[str]:
    """Return likely modern-orthography variants for matching.

    Order: most-standard first, then progressively more permissive (hyphens
    collapsed, codas reverted, etc.). Callers can probe each variant against
    a target dictionary until a hit.
    """
    out: list[str] = []
    base = normalize_lemma(lemma)
    out.append(base)

    # No hyphens (Kayano writes compounds together).
    no_hyphen = base.replace("-", "")
    if no_hyphen != base:
        out.append(no_hyphen)

    # Keep coda vowels (Kayano style).
    no_codas = normalize_lemma(lemma, codas=False)
    if no_codas != base:
        out.append(no_codas)
        nh = no_codas.replace("-", "")
        if nh != no_codas:
            out.append(nh)

    # Keep voicing (rare for matching but useful for diagnostic).
    voiced = normalize_lemma(lemma, devoice=False)
    if voiced != base:
        out.append(voiced)

    # Original Batchelor lemma exactly as printed.
    if lemma != base:
        out.append(lemma)
        nh = lemma.replace("-", "")
        if nh != lemma:
            out.append(nh)

    # Deduplicate while preserving order.
    seen: set[str] = set()
    deduped: list[str] = []
    for v in out:
        if v not in seen:
            seen.add(v)
            deduped.append(v)
    return deduped


# ---------- self-test / examples ----------
if __name__ == "__main__":
    examples = [
        "shi",
        "chise",
        "chip",
        "kamui",
        "kamoy",
        "wakka",
        "tch",
        "Iresu-kamui",
        "A-shik",
        "yub",
        "yupi",
        "huchi",
        "Etch-uki",
        "bos",
        "abe",
        "kotan",
        "ainu",
        "shongo",
        "shinrit",
        "Kamul",  # known OCR error, should still normalize
        "Tono-rumua",
        "Tsushi",
    ]
    for ex in examples:
        print(f"{ex:25} → {normalize_lemma(ex):25} variants={variants(ex)}")
