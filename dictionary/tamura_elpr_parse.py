"""Parse Tamura ELPR A2 OCR text into structured records for routing.

Two parsers:
  - parse_corpus_page(): interlinear oral-text pages -> list of Item(num, kana,
    latin, jpn) plus footnotes. Item.latin feeds the corpus `ain` field, Item.jpn
    the `jpn` field (the 凡例 guarantees a 1:1 line correspondence).
  - parse_vocab_page(): numbered Japanese->Ainu vocabulary -> list of VocabRow.

These operate per OCR page; callers concatenate across a section's page range.
The OCR format (from dictionary/tamura_elpr_ocr.py's prompt) is:

  <number on its own line>
  <katakana Ainu line>
  <latin Ainu line>
  <japanese translation line>
  <blank line>
  ...
  --------------------  (rule)
  ^24 <footnote text>

Vocabulary pages:
  <"3 ページ" source-page header, optional>
  1.  <jp gloss?>  <latin lemma>  <jp note?>
  ...
  ---
  9 = <footnote>
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


RULE_RE = re.compile(r"^[-—―‐_]{3,}$")
# An interlinear item begins with a number, then optionally inline content:
#   "37"                 bare number          (Part I UCASKUMA)
#   "1. アパッチリ …"     number + period      (Part IV oral)
#   "1 パナウンペ …"      number + space+kana  (Part III-001 prose, TUYTAH)
# group(2)=period (or None), group(3)=inline remainder.
_ITEM_START_RE = re.compile(r"^(\d+)\s*([.．])?\s*(.*)$")


def _first_is_kana_or_latin(s: str) -> bool:
    for ch in s:
        if ch.isspace():
            continue
        if not ch.isalpha():
            return False
        name = unicodedata.name(ch, "")
        return "KATAKANA" in name or "LATIN" in name
    return False


def _match_item_start(line: str) -> tuple[int, str] | None:
    """Return (num, inline_content) if the line starts a numbered interlinear
    item, else None. A bare number or 'N.<x>' always counts; 'N <x>' counts
    only when <x> begins with katakana/Latin (Ainu), so a Japanese translation
    line that happens to start with a digit is not mis-read as an item."""
    m = _ITEM_START_RE.match(line)
    if not m:
        return None
    period, rest = m.group(2), m.group(3).strip()
    if period or not rest or _first_is_kana_or_latin(rest):
        return int(m.group(1)), rest
    return None
FOOTNOTE_RE = re.compile(r"^\^?(\d+)\s*(.*)$")
VOCAB_NUM_RE = re.compile(r"^(\d+)\s*[.．]\s*(.*)$")
VOCAB_NUM_BARE_RE = re.compile(r"^(\d+)\s+(.*)$")
SRC_PAGE_RE = re.compile(r"^(\d+)\s*ページ\s*$")

# Latin run incl. Latin-1 Supplement, Extended-A/B (macron vowels ā ē ī ō ū) and
# combining diacritics, plus Ainu-internal ' = - marks.
_LX = r"A-Za-zÀ-ɏ̀-ͯ"


def _script_counts(s: str) -> dict[str, int]:
    # Ainu transcription uses KATAKANA; Japanese translation uses HIRAGANA +
    # kanji (han). Keep them separate so a pure-hiragana translation line is not
    # mistaken for an Ainu katakana line.
    counts = {"katakana": 0, "hiragana": 0, "latin": 0, "han": 0}
    for ch in s:
        if not ch.isalpha():
            continue
        name = unicodedata.name(ch, "")
        if "KATAKANA" in name:
            counts["katakana"] += 1
        elif "HIRAGANA" in name:
            counts["hiragana"] += 1
        elif "CJK" in name:
            counts["han"] += 1
        elif "LATIN" in name:
            counts["latin"] += 1
    return counts


def classify_line(s: str) -> str:
    """Return 'kana', 'latin', 'jpn', or 'other' for a content line."""
    c = _script_counts(s)
    # Any kanji or hiragana => Japanese translation.
    if c["han"] or c["hiragana"]:
        return "jpn"
    if c["katakana"] and c["latin"]:
        return "kana" if c["katakana"] >= c["latin"] else "latin"
    if c["katakana"]:
        return "kana"
    if c["latin"]:
        return "latin"
    return "other"


_CJK_RE = re.compile(
    r"[　-〿぀-ヿ㐀-䶿一-鿿＀-￯「」『』（）｛｝〔〕《》、。･…]"
)


_FOOTNOTE_MARK_RE = re.compile(r"\^\d+|[⁰¹²³⁴⁵⁶⁷⁸⁹]+")


def strip_footnote_markers(s: str) -> str:
    """Remove inline footnote markers (^24, or superscript digits ²⁴) from output
    text. The footnote bodies are already dropped during parsing."""
    s = _FOOTNOTE_MARK_RE.sub("", s)
    # collapse any double space the removal left between words
    return re.sub(r"  +", " ", s).strip()


def extract_ainu_latin(s: str) -> str:
    """Keep only the romanized-Ainu portion of a line: drop CJK text and
    Japanese punctuation (the speaker's spoken-Japanese commentary), normalize
    fullwidth = ' to ASCII, and collapse whitespace. Bracketed [katakana gloss]
    spans should be removed by the caller first."""
    s = _CJK_RE.sub(" ", s)
    s = s.replace("＝", "=").replace("’", "'").replace("‘", "'")
    s = re.sub(r"\s+", " ", s).strip()
    # Drop leading stray punctuation left from stripped Japanese (e.g. "男?" ->
    # "?"), but keep a word-initial apostrophe (glottal stop) and hyphen.
    s = re.sub(r"^[?!.,;:、。）)\]】»>…\s]+", "", s)
    return s


@dataclass
class Item:
    num: int
    kana: str = ""
    latin: str = ""
    jpn: str = ""


@dataclass
class CorpusPage:
    items: list[Item] = field(default_factory=list)
    footnotes: dict[str, str] = field(default_factory=dict)
    # header/song/title lines that weren't numbered items
    extra: list[str] = field(default_factory=list)


def _split_body_footnotes(text: str) -> tuple[list[str], list[str]]:
    lines = text.splitlines()
    # find the last rule line; everything after = footnotes
    rule_idx = None
    for i, ln in enumerate(lines):
        if RULE_RE.match(ln.strip()):
            rule_idx = i
    if rule_idx is None:
        return lines, []
    return lines[:rule_idx], lines[rule_idx + 1 :]


def parse_corpus_page(text: str) -> CorpusPage:
    body, foot = _split_body_footnotes(text)
    page = CorpusPage()

    # footnotes: each starts with ^N or N
    cur_key = None
    for ln in foot:
        ln = ln.rstrip()
        if not ln.strip():
            continue
        m = FOOTNOTE_RE.match(ln.strip())
        if m and m.group(2):
            cur_key = m.group(1)
            page.footnotes[cur_key] = m.group(2).strip()
        elif cur_key:
            page.footnotes[cur_key] += " " + ln.strip()

    # body: group by numbered items
    i = 0
    n = len(body)
    while i < n:
        ln = body[i].strip()
        start = _match_item_start(ln)
        if start is None:
            if ln:
                page.extra.append(ln)
            i += 1
            continue
        num, inline = start
        item = Item(num=num)
        i += 1
        # collect following non-empty lines until a blank or next number line
        bucket: list[tuple[str, str]] = []
        if inline:
            bucket.append((classify_line(inline), inline))
        while i < n:
            l2 = body[i].strip()
            if not l2:
                i += 1
                break
            if _match_item_start(l2):
                break
            bucket.append((classify_line(l2), l2))
            i += 1
        # assemble: join by class in order kana, latin, jpn
        kana = " ".join(s for c, s in bucket if c == "kana")
        latin = " ".join(s for c, s in bucket if c == "latin")
        jpn = " ".join(s for c, s in bucket if c == "jpn")
        # 'other' lines (e.g. pure punctuation) appended to latin as fallback
        other = " ".join(s for c, s in bucket if c == "other")
        item.kana, item.latin, item.jpn = kana, latin, (jpn or other)
        page.items.append(item)
    return page


@dataclass
class VocabRow:
    num: int
    gloss_ja: str = ""
    lemma: str = ""
    notes: str = ""
    src_page: str = ""
    category: str = ""


_LATIN_ANY_RE = re.compile(r"[A-Za-zÀ-ɏ]")

# Notebook layout marks the OCR captures (ditto arrows, braces, box-drawing).
# They carry no lexical content, so strip them from glosses/notes.
_MARKS_RE = re.compile(r"[↑↓←→↗↘↙↖⇒⇐⇔└┌┐┘├┤┬┴┼─━│┃＼／]")


def _strip_marks(s: str) -> str:
    s = _MARKS_RE.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip(" 　-—―、。")


def _is_topic_header(s: str) -> bool:
    """A standalone Japanese topic header like 人体 / 数量 / 代名詞など / 助詞など
    (sometimes OCR'd spaced as '人 体'). No Latin, has kanji, short, no trailing
    sentence punctuation."""
    if _LATIN_ANY_RE.search(s):
        return False
    compact = re.sub(r"\s+", "", s)
    if not compact or len(compact) > 6:
        return False
    if compact[-1] in "。、.":
        return False
    return bool(re.search(r"[一-鿿]", compact))


# ':' is Tamura's vowel-length mark (í:nen, na:taka); keep it inside the run.
LATIN_RUN_RE = re.compile(rf"[{_LX}'’=:.\-]+(?:\s+[{_LX}'’=:.\-]+)*")


def parse_vocab_page(text: str, *, bare_num: bool = False) -> tuple[list[VocabRow], dict[str, str]]:
    body, foot = _split_body_footnotes(text)
    rows: list[VocabRow] = []
    footnotes: dict[str, str] = {}
    src_page = ""

    cur_key = None
    for ln in foot:
        s = ln.strip()
        if not s:
            continue
        m = re.match(r"^(\d+)\s*=\s*(.*)$", s) or FOOTNOTE_RE.match(s)
        if m and m.lastindex and m.group(2):
            cur_key = m.group(1)
            footnotes[cur_key] = m.group(2).strip()
        elif cur_key:
            footnotes[cur_key] += " " + s

    num_re = VOCAB_NUM_BARE_RE if bare_num else VOCAB_NUM_RE
    category = ""
    for ln in body:
        s = ln.strip()
        if not s:
            continue
        sp = SRC_PAGE_RE.match(s)
        if sp:
            src_page = sp.group(1)
            continue
        m = num_re.match(s)
        if not m:
            if _is_topic_header(s):
                category = re.sub(r"\s+", "", s)
                continue
            # continuation of previous row's note
            if rows:
                rows[-1].notes = _strip_marks((rows[-1].notes + " " + s).strip())
            continue
        num = int(m.group(1))
        rest = m.group(2).strip()
        row = VocabRow(num=num, src_page=src_page, category=category)
        # find the first Latin run -> lemma; before = gloss_ja, after = notes
        lm = LATIN_RUN_RE.search(rest)
        if lm:
            row.gloss_ja = _strip_marks(rest[: lm.start()].strip().rstrip("・•·"))
            row.lemma = lm.group(0).strip().strip(".")
            row.notes = _strip_marks(rest[lm.end() :].strip())
        else:
            row.gloss_ja = _strip_marks(rest)
        rows.append(row)
    return rows, footnotes


if __name__ == "__main__":
    import sys
    from pathlib import Path

    path = Path(sys.argv[1])
    txt = path.read_text(encoding="utf-8")
    mode = sys.argv[2] if len(sys.argv) > 2 else "corpus"
    if mode == "corpus":
        pg = parse_corpus_page(txt)
        for it in pg.items:
            print(f"[{it.num}] AIN: {it.latin}")
            print(f"      KANA: {it.kana}")
            print(f"      JPN: {it.jpn}")
        if pg.footnotes:
            print("FOOTNOTES:", pg.footnotes)
        if pg.extra:
            print("EXTRA:", pg.extra)
    else:
        rows, fns = parse_vocab_page(txt)
        for r in rows:
            print(f"[{r.num}] gloss={r.gloss_ja!r} lemma={r.lemma!r} notes={r.notes!r} src_p={r.src_page}")
        if fns:
            print("FOOTNOTES:", fns)
