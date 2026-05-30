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
    s = s.replace("=", "").replace("_", "")  # affix boundaries / Sakhalin marks
    s = s.replace("*", "").replace("…", " ")
    return s


def restore_small_kana(ain: str, ocr_kana: str) -> str:
    """Return ocr_kana with small kana restored per the Latin `ain`."""
    if not ocr_kana or not ain:
        return ocr_kana
    ref = latn2kana(_clean_latin(ain))
    ref_u = _units(ref)
    ocr_u = _units(ocr_kana)
    sm = SequenceMatcher(a=[u[1] for u in ref_u], b=[u[1] for u in ocr_u], autojunk=False)
    out: list[str] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(j2 - j1):
                ref_unit = ref_u[i1 + k]
                ocr_unit = ocr_u[j1 + k]
                # Downsize only when the reference says this kana is small.
                out.append(ref_unit[2] if ref_unit[2] is not None else ocr_unit[0])
        else:
            # genuine divergence (ー vs アア, OCR noise): keep the OCR verbatim
            for k in range(j1, j2):
                out.append(ocr_u[k][0])
    return "".join(out)


if __name__ == "__main__":
    tests = [
        ("husko ohta", "フシコ オホタ"),
        ("nean cise tahkaa, cise tahkaaha,", "ネアン チセ タハカー、チセ タハカーハ、"),
        ("nohkiri eyohtekara ranke an manu.", "ノホキリ エヨホテカラ ランケ アン マヌ。"),
        ("ranma, tah oro suy eruy,", "ランマ、タハ オロ シエルイ、"),
        ("sapane kamuy, kamuy anihi nee", "サパネ カムイ、カムイ アニヒ ネー"),
    ]
    for ain, kana in tests:
        print(f"AIN : {ain}")
        print(f"OCR : {kana}")
        print(f"FIX : {restore_small_kana(ain, kana)}")
        print()
