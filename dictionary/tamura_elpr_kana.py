"""Restore small katakana in OCR'd `ain-kana` using the Latin `ain`.

Gemini OCR flattens Ainu small kana (フㇱコ -> フシコ, ウイㇼクㇽ -> ウイリクル). The
Latin transliteration encodes the true syllable structure, so a deterministic
Latin->katakana conversion (ainconv.latn2kana, which emits small coda kana) tells
us exactly which kana should be small.

We do NOT simply replace the OCR'd kana with the converted kana: the OCR faithfully
reflects the book's own choices (long vowels written ー, spacing, etc.) that a naive
conversion would not reproduce. Instead we ALIGN the two by their large-kana
"skeleton" and only downsize a kana to its small form where the Latin-derived
reference says it is small. Everything else (incl. ー) is kept from the OCR.

    OCR   タハカー   (husko-style flattening: large ハ)
    ref   タㇵカア   (latn2kana: small ㇵ, but ア not ー)
    fixed タㇵカー   (ㇵ restored, ー kept)
"""

from __future__ import annotations

import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

# ainconv-py is a sibling repo, imported directly from source.
_AINCONV_SRC = Path(__file__).resolve().parents[2] / "ainconv-py" / "src"
if str(_AINCONV_SRC) not in sys.path:
    sys.path.insert(0, str(_AINCONV_SRC))
from ainconv.conversion.katakana import latn2kana  # noqa: E402

# Large katakana -> its Ainu small (coda) form.
SMALL_OF = {
    "ク": "ㇰ", "シ": "ㇱ", "ス": "ㇲ", "ト": "ㇳ", "ヌ": "ㇴ",
    "ハ": "ㇵ", "ヒ": "ㇶ", "フ": "ㇷ", "ヘ": "ㇸ", "ホ": "ㇹ",
    "ム": "ㇺ", "ラ": "ㇻ", "リ": "ㇼ", "ル": "ㇽ", "レ": "ㇾ",
    "ロ": "ㇿ", "ツ": "ッ", "プ": "ㇷ゚",
}
LARGE_OF = {small: large for large, small in SMALL_OF.items()}
_PU_KO = "ㇷ゚"  # ㇷ (U+31F7) + ゜ (U+309A)


def _units(s: str) -> list[tuple[str, str, str | None]]:
    """Tokenize katakana into units: (original, large_base, small_form_or_None).
    The third element is the small form ONLY when this char is itself already a
    small kana — so a large kana that merely *has* a small counterpart (an onset)
    is not flagged for downsizing. ㇷ゚ (two codepoints) is one small unit."""
    out: list[tuple[str, str, str | None]] = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "ㇷ" and i + 1 < len(s) and s[i + 1] == "゚":
            out.append((_PU_KO, "プ", _PU_KO))
            i += 2
            continue
        if ch in LARGE_OF:  # already a small kana -> base is its large form
            out.append((ch, LARGE_OF[ch], ch))
        else:  # large kana (or anything else): keep as base, not small
            out.append((ch, ch, None))
        i += 1
    return out


def _clean_latin(ain: str) -> str:
    s = re.sub(r"\^\d+", "", ain)          # footnote markers
    # Keep "=" — ainconv reads it as a syllable break (an=unuhcin -> アンウヌㇷチン,
    # i.e. an closes to アン) without inserting a word space.
    s = s.replace("_", "").replace("*", "").replace("…", " ")
    return s


def restore_small_kana(ain: str, ocr_kana: str) -> str:
    """Fix OCR'd ain-kana against the Latin `ain`, conservatively.

    Principles (kana spacing is NOT the same as Latin spacing, so we don't impose
    it blindly):
      - small kana / syllable codas: the Latin is authoritative, so where the
        reference has a small kana the OCR flattened or misread, use the reference
        — EXCEPT a geminate ッ, which the source writes for h-before-consonant
        (unuhcin -> …ウヌッチン) and the romanization does not capture.
      - long vowels (ー vs アア) and other content: keep the OCR.
      - spacing: KEEP the OCR's own word spaces (they reflect the printed source);
        additionally SUBDIVIDE a merged OCR run at Latin word boundaries (so
        ナハイエヘチ -> ナㇵ イエㇸチ) but never break an existing OCR space.
    """
    if not ocr_kana or not ain:
        return ocr_kana
    ref = latn2kana(_clean_latin(ain))

    # Reference units (no spaces) + indices that begin a Latin word.
    ref_ns: list[tuple[str, str, str | None]] = []
    word_start: set[int] = set()
    prev_space = False
    for u in _units(ref):
        if u[0] == " ":
            prev_space = True
            continue
        if prev_space and ref_ns:
            word_start.add(len(ref_ns))
        ref_ns.append(u)
        prev_space = False

    # OCR units (no spaces) + indices that begin a chunk after an OCR space.
    ocr_ns: list[tuple[str, str, str | None]] = []
    ocr_boundary: set[int] = set()
    prev_space = False
    for u in _units(ocr_kana):
        if u[0] == " ":
            prev_space = True
            continue
        if prev_space and ocr_ns:
            ocr_boundary.add(len(ocr_ns))
        ocr_ns.append(u)
        prev_space = False

    sm = SequenceMatcher(a=[u[1] for u in ref_ns], b=[u[1] for u in ocr_ns], autojunk=False)
    small_at: dict[int, str] = {}
    latin_boundary: set[int] = set()  # Latin word boundaries mapped to OCR indices

    def maybe_override(ri: int, oi: int) -> None:
        small = ref_ns[ri][2]
        if small is not None and ocr_ns[oi][0] != "ッ":  # keep the source geminate
            small_at[oi] = small

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                maybe_override(i1 + k, j1 + k)
                if (i1 + k) in word_start:
                    latin_boundary.add(j1 + k)
        elif tag == "replace":
            if any((r in word_start) for r in range(i1, i2)):
                latin_boundary.add(j1)
            for k in range(min(i2 - i1, j2 - j1)):
                maybe_override(i1 + k, j1 + k)
        elif tag == "delete":
            if any((r in word_start) for r in range(i1, i2)):
                latin_boundary.add(j1)  # boundary falls before the next OCR unit

    # Keep OCR's spaces; add Latin boundaries that fall inside a merged OCR run.
    space_before = ocr_boundary | latin_boundary

    out: list[str] = []
    for idx, u in enumerate(ocr_ns):
        if idx in space_before and out and out[-1] != " ":
            out.append(" ")
        out.append(small_at.get(idx, u[0]))
    result = "".join(out)
    result = re.sub(r"\s+([、。，])", r"\1", result)  # no space before JP punctuation
    return re.sub(r"\s+", " ", result).strip()


if __name__ == "__main__":
    tests = [
        ("husko ohta", "フシコ オホタ"),
        ("nean cise tahkaa, cise tahkaaha,", "ネアン チセ タハカー、チセ タハカーハ、"),
        ("nohkiri eyohtekara ranke an manu.", "ノホキリ エヨホテカラ ランケ アン マヌ。"),
        ("ranma, tah oro suy eruy,", "ランマ、タハ オロ シエルイ、"),
        ("sapane kamuy, kamuy anihi nee", "サパネ カムイ、カムイ アニヒ ネー"),
        ("konkaani maareh sineh kara,", "コンカーニマーレㇳシネㇷカラ、"),  # OCR dropped spaces
    ]
    for ain, kana in tests:
        print(f"AIN : {ain}")
        print(f"OCR : {kana}")
        print(f"FIX : {restore_small_kana(ain, kana)}")
        print()
