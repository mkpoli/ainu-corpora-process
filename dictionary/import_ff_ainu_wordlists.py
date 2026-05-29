"""Import the three ff-ainu (FRPAC, 公益財団法人アイヌ文化振興・研究推進機構)
dialect wordlists — Saru (沙流), Ishikari (石狩川), Karafuto (樺太) — as
sibling dictionaries with a unified schema.

Source PDFs (downloaded into dictionary/output/src/ via the existing
ff-ainu/extract_words.ipynb pipeline):
  https://www.ff-ainu.or.jp/web/potal_site/files/saru_tango.pdf
  https://www.ff-ainu.or.jp/web/potal_site/files/ishikari_tango.pdf
  https://www.ff-ainu.or.jp/web/potal_site/files/karahuto_tango.pdf

Output: one folder per dialect under ainu-dictionaries/ with
  original.tsv (kana | lemma | gloss_ja | pos | notes | page)
  metadata.yaml
  source.pdf (Git LFS)

The Saru and Karafuto TSVs already exist in dictionary/output/src/ from
the older notebook; we reuse them and normalize the schema. Ishikari is
parsed fresh from the PDF text layer.
"""

from __future__ import annotations

import csv
import re
import shutil
import subprocess
import sys
from pathlib import Path

csv.field_size_limit(sys.maxsize)

ROOT = Path(__file__).resolve().parents[1]
DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
SRC = ROOT / "dictionary" / "output" / "src"


FIELDS = ["kana", "lemma", "gloss_ja", "pos", "notes", "page"]


# ---------- helpers ----------
_POS_RE = re.compile(r"【([^】]+)】")
_SUB_RE = re.compile(r"［([^］]+)］")
# Entry head: katakana run + space + Latin form. Allow `=` for clitics
# (a=, ku=) and `~` for valence markers; ASCII or full-width `(...)` for
# inflection notes.
_ENTRY_HEAD_RE = re.compile(
    r"^(?P<kana>[ァ-ヴーㇰ-ㇿ゠]+(?:\s*[(（][^)）]+[)）])?)\s+"
    r"(?P<latn>[A-Za-z][A-Za-z=~’'\-]*(?:[(（][^)）]+[)）])?)"
    r"(?:\s+(?P<rest>.+))?$"
)


def normalize_pos(pos: str) -> str:
    """Strip surrounding 【】 and whitespace from POS tag."""
    s = pos.strip()
    s = s.strip("【】").strip()
    return s


def normalize_field(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("　", " ")).strip()


# ---------- existing TSV importers (Saru / Karafuto) ----------
def load_existing_saru() -> list[dict[str, str]]:
    """Existing 4-column TSV: kana\tlatn\tgloss\tpos (no notes/pages)."""
    path = SRC / "ff-ainu-saru-terms.tsv"
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as fh:
        reader = csv.reader(fh, delimiter="\t")
        for row in reader:
            if len(row) < 4:
                continue
            kana, latn, gloss, pos = (row + [""] * 4)[:4]
            rows.append(
                {
                    "kana": normalize_field(kana),
                    "lemma": normalize_field(latn),
                    "gloss_ja": normalize_field(gloss),
                    "pos": normalize_pos(pos),
                    "notes": "",
                    "page": "",
                }
            )
    return rows


def load_existing_karafuto() -> list[dict[str, str]]:
    """Existing 5-column TSV: kana\tlatn\tgloss\tpos\tnotes."""
    path = SRC / "ff-ainu-karahuto-terms.tsv"
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as fh:
        reader = csv.reader(fh, delimiter="\t")
        for row in reader:
            if len(row) < 4:
                continue
            row = (row + [""] * 5)[:5]
            kana, latn, gloss, pos, notes = row
            rows.append(
                {
                    "kana": normalize_field(kana),
                    "lemma": normalize_field(latn),
                    "gloss_ja": normalize_field(gloss),
                    "pos": normalize_pos(pos),
                    "notes": normalize_field(notes),
                    "page": "",
                }
            )
    return rows


# ---------- fresh parser for Ishikari ----------
import html as _html
_WORD_RE = re.compile(
    r'<word\s+xMin="(?P<xmin>[\d.]+)"\s+yMin="(?P<ymin>[\d.]+)"'
    r'\s+xMax="(?P<xmax>[\d.]+)"\s+yMax="(?P<ymax>[\d.]+)">(?P<text>[^<]*)</word>'
)


# Inline split: a line may contain a wrapped portion of the previous
# entry followed by the start of the next entry, e.g.
# "（彼）の指 アシケペチ askepeci（hi） 【名】". We split at every internal
# `KANA<space>latin` boundary by looking for the pattern in the middle.
_INLINE_HEAD_RE = re.compile(
    r"(?<=\s)(?=[ァ-ヴーㇰ-ㇿ゠]+\s+[A-Za-z][A-Za-z=~’'\-]*(?:[(（][^)）]+[)）])?\s)"
)


def parse_ishikari(pdf: Path) -> list[dict[str, str]]:
    """Simpler / cleaner parser using default pdftotext reading-order
    output. Each entry takes 1-3 lines; we join continuation lines into
    the current entry until a new `KANA latin ...` line begins. Skip the
    header/back-matter (the JP→Ainu index lives on pages 10+ in some
    dialects but Ishikari is Ainu→JP only)."""
    out = subprocess.run(
        ["pdftotext", str(pdf), "-"],
        check=True, capture_output=True, text=True,
    )
    pages = out.stdout.split("\f")
    rows: list[dict[str, str]] = []
    for page_idx, page_text in enumerate(pages[1:], start=2):
        current: list[str] = []
        for raw_line in page_text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("■") or line.startswith("＊"):
                if current:
                    rec = _parse_entry(" ".join(current), page_idx)
                    if rec:
                        rows.append(rec)
                    current = []
                continue
            # Split inline boundaries (wrap-fusion fix).
            chunks = _INLINE_HEAD_RE.split(line)
            for chunk in chunks:
                chunk = chunk.strip()
                if not chunk:
                    continue
                if _ENTRY_HEAD_RE.match(chunk):
                    if current:
                        rec = _parse_entry(" ".join(current), page_idx)
                        if rec:
                            rows.append(rec)
                    current = [chunk]
                elif current:
                    current.append(chunk)
        if current:
            rec = _parse_entry(" ".join(current), page_idx)
            if rec:
                rows.append(rec)
    return rows


def _parse_ishikari_bbox_old(pdf: Path) -> list[dict[str, str]]:
    """Use pdftotext -bbox-layout to recover word coordinates, then
    split each page into three columns at X-boundaries derived empirically
    (column starts are around x=51 / x=195 / x=340 in PDF user-space units).
    Within each column, cluster words into reading-order lines by Y, then
    group lines into entries (a new entry begins on a line that matches
    `KANA<space>latin`)."""
    xml_path = pdf.with_suffix(".bbox.xml")
    if not xml_path.exists() or xml_path.stat().st_size < 100_000:
        subprocess.run(
            ["pdftotext", "-bbox-layout", str(pdf), str(xml_path)],
            check=True,
        )
    xml = xml_path.read_text(encoding="utf-8", errors="replace")

    rows: list[dict[str, str]] = []
    page_re = re.compile(r"<page\b[^>]*>(.*?)</page>", re.DOTALL)
    for page_idx, page_match in enumerate(page_re.finditer(xml), start=1):
        if page_idx < 2:  # skip cover
            continue
        body = page_match.group(1)
        words: list[tuple[float, float, float, str]] = []
        for m in _WORD_RE.finditer(body):
            text = _html.unescape(m["text"])
            if not text.strip():
                continue
            words.append(
                (
                    float(m["ymin"]),
                    float(m["xmin"]),
                    float(m["xmax"]),
                    text,
                )
            )
        # Drop header/footer.
        words = [w for w in words if 140.0 <= w[0] <= 660.0]
        if not words:
            continue
        # Cluster all words on the page into Y-rows (tight tolerance: a
        # row spans all three columns and should be < 4 vert. units thick).
        words.sort()
        page_rows: list[list[tuple[float, float, str]]] = []
        current_row: list[tuple[float, float, str]] = []
        cluster_y: float | None = None
        Y_TOL = 4.0
        for ymin, xmin, xmax, text in words:
            if cluster_y is None or ymin - cluster_y > Y_TOL:
                if current_row:
                    page_rows.append(current_row)
                current_row = [(xmin, xmax, text)]
                cluster_y = ymin
            else:
                current_row.append((xmin, xmax, text))
                cluster_y = max(cluster_y, ymin)
        if current_row:
            page_rows.append(current_row)

        # For each row, split cells by X-gap > 25 units (column gap),
        # then assign each cell to a column by its leftmost X position.
        col_streams: list[list[str]] = [[], [], []]
        for row in page_rows:
            row.sort()
            cells: list[list[tuple[float, float, str]]] = [[]]
            prev_xmax = None
            for xmin, xmax, text in row:
                if prev_xmax is not None and xmin - prev_xmax > 25.0:
                    cells.append([])
                cells[-1].append((xmin, xmax, text))
                prev_xmax = max(prev_xmax or 0.0, xmax)
            for cell in cells:
                if not cell:
                    continue
                xmin0 = cell[0][0]
                if xmin0 < 145.0:
                    col = 0
                elif xmin0 < 290.0:
                    col = 1
                else:
                    col = 2
                line_text = _join_cell(cell)
                if line_text:
                    col_streams[col].append(line_text)

        for col in col_streams:
            current: list[str] = []
            for line in col:
                line = line.strip()
                if not line or line.startswith("■"):
                    if current:
                        rec = _parse_entry(" ".join(current), page_idx)
                        if rec:
                            rows.append(rec)
                        current = []
                    continue
                if _ENTRY_HEAD_RE.match(line):
                    if current:
                        rec = _parse_entry(" ".join(current), page_idx)
                        if rec:
                            rows.append(rec)
                    current = [line]
                elif current:
                    current.append(line)
            if current:
                rec = _parse_entry(" ".join(current), page_idx)
                if rec:
                    rows.append(rec)
    return rows


def _join_cell(cell: list[tuple[float, float, str]]) -> str:
    """Build a line string from a row-cell. Glue adjacent kana words
    together when the X-gap between them is < 5 units."""
    if not cell:
        return ""
    cell = sorted(cell)
    pieces: list[str] = [cell[0][2]]
    last_xmax = cell[0][1]
    for xmin, xmax, text in cell[1:]:
        prev = pieces[-1]
        glue = (
            prev
            and text
            and _KANA_CHAR_RE.search(prev[-1])
            and _KANA_CHAR_RE.search(text[0])
            and xmin - last_xmax < 5.0
        )
        if glue:
            pieces[-1] = prev + text
        else:
            pieces.append(text)
        last_xmax = xmax
    return " ".join(pieces)


_KANA_CHAR_RE = re.compile(r"[ァ-ヴーㇰ-ㇿ゠]")


def _join_words(words: list[tuple[float, float, str]]) -> str:
    """Build a line string, dropping space between adjacent kana words
    (pdftotext sometimes emits per-character <word> tags for kana). Two
    adjacent words are concatenated without space if both ends are kana
    AND the X gap is small (< ~3 user-units)."""
    if not words:
        return ""
    words = sorted(words, key=lambda x: x[1])
    pieces: list[str] = [words[0][2]]
    last_xmax = words[0][1] + len(words[0][2]) * 6  # rough char width
    for _, xmin, text in words[1:]:
        prev = pieces[-1]
        # Heuristic: glue together if prev ends with kana AND text starts
        # with kana AND the gap is small.
        glue = (
            prev
            and text
            and _KANA_CHAR_RE.search(prev[-1])
            and _KANA_CHAR_RE.search(text[0])
            and xmin - last_xmax < 5.0
        )
        if glue:
            pieces[-1] = prev + text
        else:
            pieces.append(text)
        last_xmax = xmin + len(text) * 6
    return " ".join(pieces)


def _cluster_lines(words: list[tuple[float, float, str]], y_tol: float) -> list[str]:
    if not words:
        return []
    words = sorted(words)
    out: list[str] = []
    current: list[tuple[float, float, str]] = []
    cluster_y: float | None = None
    for ymin, xmin, text in words:
        if cluster_y is None or ymin - cluster_y > y_tol:
            if current:
                out.append(_join_words(current))
            current = [(ymin, xmin, text)]
            cluster_y = ymin
        else:
            current.append((ymin, xmin, text))
    if current:
        out.append(_join_words(current))
    return out


def _parse_entry(text: str, page: int) -> dict[str, str] | None:
    text = normalize_field(text)
    m = _ENTRY_HEAD_RE.match(text)
    if not m:
        return None
    kana = m["kana"].strip()
    latn = m["latn"].strip()
    rest = (m["rest"] or "").strip()
    pos_m = _POS_RE.search(rest)
    pos = ""
    if pos_m:
        pos = pos_m.group(1)
        gloss = rest[: pos_m.start()].strip()
        notes = rest[pos_m.end():].strip()
    else:
        gloss = rest
        notes = ""
    # Pull any 補足 [...] tag out into notes.
    sub_m = _SUB_RE.search(notes)
    if sub_m:
        notes = (notes[: sub_m.start()] + " " + sub_m.group(1) + " " + notes[sub_m.end():]).strip()
    return {
        "kana": kana,
        "lemma": latn,
        "gloss_ja": gloss,
        "pos": normalize_pos(pos),
        "notes": notes,
        "page": str(page),
    }


# ---------- writer ----------
def write_dict(folder_name: str, rows: list[dict[str, str]], dialect_ja: str,
               dialect_en: str, source_pdf: Path) -> None:
    folder = DICT_ROOT / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / "original.tsv"
    with out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    # Copy source PDF for Git LFS.
    pdf_dest = folder / "source.pdf"
    if not pdf_dest.exists():
        shutil.copy2(source_pdf, pdf_dest)

    meta = folder / "metadata.yaml"
    meta.write_text(
        f"""type: dictionary
title: 単語リスト (アイヌ語・日本語) — {dialect_ja}
title_en: FRPAC Ainu-Japanese Wordlist — {dialect_en} dialect
publisher:
  ja: 公益財団法人アイヌ文化振興・研究推進機構 (FRPAC)
  en: Foundation for Research and Promotion of Ainu Culture (FRPAC)
year_range:
  - 2005
  - 2007
source: |
  Downloaded from https://www.ff-ainu.or.jp/web/potal_site/files/
  ({source_pdf.name}). Companion wordlist to the FRPAC introductory /
  beginner / intermediate Ainu textbooks for the {dialect_en} dialect.
  Source PDF preserved in source.pdf via Git LFS.
sibling_dictionaries: |
  - XXXX_FRPAC_Saru-Wordlist  (sibling, Saru dialect)
  - XXXX_FRPAC_Ishikari-Wordlist (sibling, Ishikari dialect)
  - XXXX_FRPAC_Karafuto-Wordlist (sibling, Karafuto / Sakhalin dialect)
columns:
  kana: katakana headword as printed
  lemma: Latin (academic Hattori-1964) headword
  gloss_ja: short Japanese gloss / definition
  pos: part-of-speech tag (名=noun, 自=intransitive verb, 他=transitive verb,
       副=adverb, 助動=auxiliary, 人接=personal affix, etc.)
  notes: inflection notes, possessive form, scientific name, or remarks
         that follow [補足] / parenthetical tags in the source PDF
  page: 1-based source PDF page where the entry appears
""",
        encoding="utf-8",
    )
    print(f"wrote {len(rows):>5} entries → {out}")


def main() -> None:
    saru = load_existing_saru()
    write_dict(
        "XXXX_FRPAC_Saru-Ainu-Wordlist",
        saru,
        "沙流",
        "Saru",
        SRC / "saru_tango.pdf",
    )

    karafuto = load_existing_karafuto()
    write_dict(
        "XXXX_FRPAC_Karafuto-Ainu-Wordlist",
        karafuto,
        "樺太",
        "Karafuto / Sakhalin",
        SRC / "karahuto_tango.pdf",
    )

    ishikari = parse_ishikari(SRC / "ishikari_tango.pdf")
    write_dict(
        "XXXX_FRPAC_Ishikari-Ainu-Wordlist",
        ishikari,
        "石狩川",
        "Ishikari",
        SRC / "ishikari_tango.pdf",
    )


if __name__ == "__main__":
    main()
