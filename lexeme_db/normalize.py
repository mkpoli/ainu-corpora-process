"""Form and POS normalisation shared by ingest, build, and matching.

Two normalisation jobs:

* **Form key** — collapse the surface spelling differences between sources
  (accents, glottal ``'``, attachment markers ``- =``, superscript sense
  numbers, case) into a single matching key, while remembering whether the
  original was bound. The key is what lexemes cluster on; the original spelling
  is kept verbatim on the attestation.
* **POS** — map each source's descriptive label (中川's ``動1``, 田村/萱野's
  bracketed ``【接尾】``, ``〔人称接辞〕``) onto the repo's XPOS inventory
  (``dictionary/XPOS.md``).
"""

from __future__ import annotations

import re
import unicodedata

# Accents 田村 prints on citation forms; stripped for the key only.
_ACCENT_TABLE = str.maketrans("áéíóúàèìòùÁÉÍÓÚ", "aeiouaeiouAEIOU")

_SUPERSCRIPT = "¹²³⁴⁵⁶⁷⁸⁹⁰"
_SUP_RE = re.compile(f"[{_SUPERSCRIPT}0-9]+$")


def has_bound_marker(form: str) -> bool:
    """True when the citation form carries an attachment marker (``-``/``=``)."""
    s = form.strip()
    return s.startswith(("-", "=")) or s.endswith(("-", "="))


def form_key(form: str) -> str:
    """Normalise an Ainu Latin form to a clustering key.

    Lowercase, NFC, drop accents, leading glottal ``'``, attachment markers,
    trailing sense-number superscripts, and internal spaces. ``a'`` → ``a``,
    ``=an`` → ``an``, ``tú-`` → ``tu``, ``poro²`` → ``poro``.
    """
    if not form:
        return ""
    s = unicodedata.normalize("NFC", form).strip().lower()
    s = s.translate(_ACCENT_TABLE)
    s = s.strip("-=")
    s = s.lstrip("'’`")
    s = _SUP_RE.sub("", s)
    s = s.replace("'", "").replace("’", "")
    s = re.sub(r"\s+", "", s)
    return s


# ---- POS normalisation --------------------------------------------------

# 中川千歳 uses a compact descriptive label set in its `pos` column; 田村/萱野
# embed the same notions in 【…】 / 〔…〕 brackets in the definition text.
# Map the labels we see onto XPOS (dictionary/XPOS.md).
_POS_MAP: dict[str, str] = {
    # verbs
    "動": "v",
    "動1": "vi",
    "動2": "vt",
    "動3": "vd",
    "自動詞": "vi",
    "他動詞": "vt",
    "複他動詞": "vd",
    "完全動詞": "vc",
    "自": "vi",
    "他": "vt",
    # aux / copula
    "助動": "auxv",
    "助動詞": "auxv",
    "繋辞": "cop",
    # nominals
    "名": "n",
    "名詞": "n",
    "位置名詞": "nl",
    "形式名詞": "nmlz",
    "代": "pron",
    "代名詞": "pron",
    "固有名詞": "propn",
    # modifiers / adverbials
    "連体": "adn",
    "連体詞": "adn",
    "副": "adv",
    "副詞": "adv",
    "後置副詞": "padv",
    # function words
    "接続": "cconj",
    "接続詞": "cconj",
    "接助": "sconj",
    "接続助詞": "sconj",
    "助": "post",
    "助詞": "post",
    "格助詞": "postp",
    "副助詞": "advp",
    "終助": "sfp",
    "終助詞": "sfp",
    "間投": "intj",
    "間投詞": "intj",
    "感動詞": "intj",
    # affixes / bound
    "接頭": "pfx",
    "接頭辞": "pfx",
    "接尾": "sfx",
    "接尾辞": "sfx",
    "人接": "pers",
    "人称接辞": "pers",
    "語根": "root",
    # multiword
    "数": "num",
    "数詞": "num",
    "疑問": "int",
    "疑問詞": "int",
    "連語": "colloc",
    "慣用句": "idiom",
}

# Bracketed-label extractor for 田村/萱野 definitions: 【接尾】, 〔人称接辞〕.
_BRACKET_RE = re.compile(r"[【〔［\[]([^】〕］\]]+)[】〕］\]]")


def normalize_pos(label: str) -> str:
    """Map a raw source POS label to XPOS; ``""`` when unrecognised."""
    if not label:
        return ""
    raw = label.strip()
    if raw in _POS_MAP:
        return _POS_MAP[raw]
    # Strip a trailing digit (動1 → 動) and retry, but keep the 動1/動2 split
    # when present (handled above). Also try the first bracketed token.
    base = raw.rstrip("0123456789")
    if base in _POS_MAP:
        return _POS_MAP[base]
    return ""


def pos_from_definition(definition: str) -> str:
    """Pull the first bracketed POS label out of a 田村/萱野 definition."""
    for m in _BRACKET_RE.finditer(definition):
        token = m.group(1).strip()
        # Labels are short; bail on long bracketed prose.
        if len(token) > 6:
            continue
        mapped = normalize_pos(token)
        if mapped:
            return mapped
        # Try a leading run of CJK label chars (e.g. 接尾, 人称接辞).
        for cand in (token[:4], token[:3], token[:2]):
            mapped = normalize_pos(cand)
            if mapped:
                return mapped
    return ""


__all__ = [
    "form_key",
    "has_bound_marker",
    "normalize_pos",
    "pos_from_definition",
]
