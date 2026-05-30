"""Route Tamura ELPR A2 OCR into ainu-corpora and ainu-dictionaries.

Reads the per-page OCR under dictionary/output/tamura-elpr-ocr/ and writes:

  CORPUS  -> <ainu-corpora>/texts/<slug>/{manifest.yaml, NNN.yaml}
  DICT    -> <ainu-dictionaries>/<YEAR_Tamura_...>/{metadata.yaml, original.tsv}

Routing (decided with the maintainer):
  - Part I  藤山ハル  (Sakhalin) oral lit + songs        -> corpus
  - Part II 山田ハヨ  (Sakhalin) notebook: vocab->dict, oral->corpus
  - Part III 北風磯吉 (Nayoro)  001 prose + 002-145 elicited sentences -> corpus
  - Part IV 徹辺重次郎 (Kushiro) 語彙->dict, 言い伝え->corpus
  - アイヌ語索引 concordances: skipped.

Page numbers below are PDF (1-indexed) pages = printed + 7.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from dictionary.tamura_elpr_parse import (
    classify_line,
    extract_ainu_latin,
    parse_corpus_page,
    parse_vocab_page,
    strip_footnote_markers,
)
from dictionary.tamura_elpr_kana import restore_small_kana

ROOT = Path(__file__).resolve().parents[1]
OCR_DIR = ROOT / "dictionary" / "output" / "tamura-elpr-ocr"
CORPORA = ROOT.parent / "ainu-corpora"
DICTS = ROOT.parent / "ainu-dictionaries"

MODEL_FILE = "openrouter_google_gemini-3.5-flash.txt"

# Title-marker lines that are section headers, not content.
TITLE_RE = re.compile(
    r"^(ウチャシクマ|UCASKUMA|トゥイタハ|TUYTAH|イフンケ|IHUNKE|シノホサ|SINOHSA|"
    r"言い伝え|子守歌|酒歌|挿入歌|散文説話|語彙|第[0-9０-９]+部|[0-9]+\s*ページ)\b"
)


def ocr_text(pdf_page: int) -> str:
    f = OCR_DIR / f"page-{pdf_page:03d}" / "ocr" / MODEL_FILE
    return f.read_text(encoding="utf-8") if f.exists() else ""


def yaml_dump(data: object) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=10_000)


# --------------------------------------------------------------------------
# Corpus: interlinear story pages -> sentences [{ain, jpn}]
# --------------------------------------------------------------------------
def build_interlinear_doc(pages: range, title: str) -> dict:
    sentences: list[dict] = []
    notes: dict[str, str] = {}
    for p in pages:
        txt = ocr_text(p)
        if not txt:
            continue
        page = parse_corpus_page(txt)
        notes.update(page.footnotes)
        for it in page.items:
            if not (it.latin or it.jpn):
                continue
            s: dict = {}
            s["ain"] = strip_footnote_markers(it.latin.strip())
            if it.jpn.strip():
                s["jpn"] = it.jpn.strip()
            if it.kana.strip():
                # Restore small kana that Gemini flattened, using the Latin.
                kana = restore_small_kana(it.latin.strip(), it.kana.strip())
                s["ain-kana"] = strip_footnote_markers(kana)
            sentences.append(s)
    doc: dict = {"title": title, "sentences": sentences}
    return doc


# --------------------------------------------------------------------------
# Corpus: Kitakaze elicited sentences 002-145
#   NNN. 「<jp prompt>」
#   【北風】 ... <latin> ... [<katakana> <morpheme gloss>]
#   【註釈】/【直訳】 ...
# --------------------------------------------------------------------------
KITA_NUM_RE = re.compile(r"^(\d{3})\s*[.．]\s*(.*)$")
TAG_RE = re.compile(r"^【([^】]+)】\s*(.*)$")
INNER_BRACKET_RE = re.compile(r"\[[^\[\]]*\]")
HAS_LATIN_RE = re.compile(r"[A-Za-zÀ-ɏ]")


def _clean_prompt(s: str) -> str:
    return s.replace("「", "").replace("」", "").strip()


def _strip_gloss_brackets(s: str) -> str:
    # Remove the editorial [katakana + morpheme gloss] annotations. Brackets can
    # nest one level (an illegible [?] inside a gloss), so strip innermost-first
    # until stable.
    prev = None
    while prev != s:
        prev = s
        s = INNER_BRACKET_RE.sub(" ", s)
    return s


def _clean_utterance(s: str) -> str:
    # Keep the spoken text FAITHFULLY, including Japanese code-switches; only the
    # editorial bracket glosses are removed. Tidy whitespace around Japanese
    # punctuation that the bracket removal left behind.
    s = _strip_gloss_brackets(s)
    s = s.replace("＝", "=").replace("’", "'").replace("‘", "'")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s+([、。，？！」』）)])", r"\1", s)
    s = re.sub(r"([「『（(])\s+", r"\1", s)
    return strip_footnote_markers(s.strip(" 、。"))


def build_kitakaze_doc(pages: range, title: str) -> dict:
    sentences: list[dict] = []
    cur: dict | None = None
    for p in pages:
        for raw in ocr_text(p).splitlines():
            line = raw.strip()
            if not line:
                continue
            m = KITA_NUM_RE.match(line)
            if m:
                if cur:
                    sentences.append(cur)
                cur = {"num": int(m.group(1)), "jpn": _clean_prompt(m.group(2)), "ain": ""}
                continue
            tm = TAG_RE.match(line)
            if tm and cur is not None:
                tag, body = tm.group(1), tm.group(2)
                if tag == "北風":
                    cur["ain"] = (cur.get("ain", "") + " " + _clean_utterance(body)).strip()
                elif tag == "直訳":
                    cur["jpn_literal"] = body.strip()
                # 註釈 etc. dropped from the sentence (annotation, not translation)
                continue
            # continuation of a 【北風】 response line (carries a [kana gloss])
            if cur is not None and "[" in line:
                cur["ain"] = (cur["ain"] + " " + _clean_utterance(line)).strip()
    if cur:
        sentences.append(cur)

    out_sentences = []
    for s in sentences:
        ain = s.get("ain", "").strip()
        # Keep turns that contain at least some Ainu; pure-Japanese turns (e.g.
        # 「わからない」) are not Ainu data. Japanese *within* an Ainu turn (a
        # code-switch) is preserved.
        if not ain or not HAS_LATIN_RE.search(ain):
            continue
        d: dict = {"ain": ain}
        if s.get("jpn"):
            d["jpn"] = s["jpn"]
        if s.get("jpn_literal"):
            d["jpn"] = d.get("jpn", "") + (" / " if d.get("jpn") else "") + s["jpn_literal"]
        out_sentences.append(d)
    return {"title": title, "sentences": out_sentences}


# --------------------------------------------------------------------------
# Corpus: Yamada oral narrative   N <latin> 《<jpn>》
# --------------------------------------------------------------------------
# Yamada oral lines: "N <latin> 《<jpn>》" (inline) or, when the number sits on
# its own line, "<latin> 《<jpn>》" on the following line. Match the ain《jpn》
# core regardless of whether a leading number is present.
YAMADA_CORE_RE = re.compile(r"^(?:\d+\s+)?(.*?)\s*《(.*?)》\s*$")
BARE_NUM_RE = re.compile(r"^\d+\s*$")
PAGE_HDR_RE = re.compile(r"^\d+\s*ページ\s*$")


def build_yamada_oral_doc(pages: range, title: str) -> dict:
    # The translation 《...》 may sit inline after the Ainu (p198) or on its own
    # line below it (p199). Buffer the most recent Ainu line and flush when a
    # 《jpn》 is seen.
    sentences = []
    pending = ""
    for p in pages:
        for raw in ocr_text(p).splitlines():
            line = raw.strip()
            if not line or BARE_NUM_RE.match(line) or PAGE_HDR_RE.match(line):
                continue
            if "《" in line:
                m = YAMADA_CORE_RE.match(line)
                jpn = m.group(2).strip() if m else line
                inline_ain = extract_ainu_latin(m.group(1)) if m else ""
                ain = strip_footnote_markers(inline_ain or pending)
                if ain:
                    sentences.append({"ain": ain, "jpn": jpn})
                pending = ""
            else:
                pending = extract_ainu_latin(line)
    return {"title": title, "sentences": sentences}


def write_corpus_collection(slug: str, manifest: dict, docs: list[tuple[str, dict]]) -> None:
    d = CORPORA / "texts" / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.yaml").write_text(yaml_dump(manifest), encoding="utf-8")
    for name, doc in docs:
        (d / name).write_text(yaml_dump(doc), encoding="utf-8")
    total = sum(len(doc["sentences"]) for _, doc in docs)
    print(f"  corpus {slug}: {len(docs)} docs, {total} sentences -> {d}")


# --------------------------------------------------------------------------
# Dictionary: numbered vocab pages -> original.tsv + metadata.yaml
# --------------------------------------------------------------------------
def build_vocab_tsv(pages: range, *, bare_num: bool = False) -> list[list[str]]:
    rows: list[list[str]] = [["num", "src_page", "category", "gloss_ja", "lemma", "notes"]]
    for p in pages:
        txt = ocr_text(p)
        if not txt:
            continue
        vrows, footnotes = parse_vocab_page(txt, bare_num=bare_num)
        for r in vrows:
            rows.append(
                [
                    str(r.num),
                    r.src_page,
                    r.category,
                    strip_footnote_markers(r.gloss_ja),
                    strip_footnote_markers(r.lemma),
                    strip_footnote_markers(r.notes),
                ]
            )
    return rows


def write_dict_source(folder: str, metadata: dict, tsv_rows: list[list[str]]) -> None:
    d = DICTS / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / "metadata.yaml").write_text(yaml_dump(metadata), encoding="utf-8")
    lines = ["\t".join(c.replace("\t", " ").replace("\n", " ") for c in row) for row in tsv_rows]
    (d / "original.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  dict {folder}: {len(tsv_rows) - 1} rows -> {d}")


def route_dictionaries() -> None:
    print("Tamura ELPR routing (dictionary phase)")

    # ---- Part IV: 徹辺重次郎 (Kushiro) 語彙1+語彙2 ------------------------
    tetsube_rows = build_vocab_tsv(range(258, 314))  # vocab bodies (skip title pages)
    write_dict_source(
        "1960_Tamura_Kushiro-Ainu-Tetsube-Vocabulary",
        {
            "type": "wordlist",
            "title": "徹辺重次郎さんの語彙（アイヌ語釧路方言）",
            "title_en": "Tetsube Jujiro's vocabulary — Kushiro Ainu (Tamura field recording)",
            "author": {"ja": "田村 すず子（採録）", "en": "Suzuko Tamura (rec.)"},
            "publisher": {"ja": "環太平洋の言語 (ELPR)", "en": "Endangered Languages of the Pacific Rim (ELPR)"},
            "year": 1960,
            "dialect": "釧路",
            "recorded_at": "1960-01-08, 1960-01-09, 1960-10-25",
            "license": "All rights reserved (ELPR A2; research use)",
            "source": (
                "OCR of ELPR publication A2 『アイヌ語 樺太・名寄・釧路方言の資料』 "
                "(田村すず子採録), 第IV編 徹辺重次郎さんの語彙 (語彙1・語彙2). "
                "Speaker 徹辺重次郎 (1894–1966), 釧路市千代ノ浦. Edited by 田村雅史. "
                "OCR'd with gemini-3.5-flash; see ainu-corpora-process/dictionary/tamura_elpr_ocr.py."
            ),
            "notes": (
                "Topical vocabulary elicitation (kinship, body parts, numbers, pronouns, "
                "particles, clothing, …). Some entries are example phrases/sentences rather "
                "than single words. Latin lemmas carry acute pitch accents. Companion oral "
                "texts are in ainu-corpora/texts/tamura-kushiro-tetsube."
            ),
            "columns": {
                "num": "running entry number within a notebook page",
                "src_page": "原本 (Tamura's notebook) page number",
                "category": "topical section header (人体, 数量, 代名詞, 助詞, …) when present",
                "gloss_ja": "Japanese gloss / prompt",
                "lemma": "romanized Ainu (Tamura transcription, acute = pitch accent)",
                "notes": "remarks, dialect notes, possessive forms, footnote markers",
            },
            "parent": {
                "type": "book",
                "title": "アイヌ語 樺太・名寄・釧路方言の資料 (ELPR A2)",
                "publisher": "文部科学省特定領域研究「環太平洋の『消滅に瀕した言語』にかんする緊急調査研究」",
            },
        },
        tetsube_rows,
    )

    # ---- Part II: 山田ハヨ (Sakhalin) vocabulary portion -----------------
    yamada_rows = build_vocab_tsv(range(183, 198), bare_num=True)  # pp.1–15 (oral lit pp.16–17 -> corpus)
    write_dict_source(
        "1958_Tamura_Sakhalin-Ainu-Yamada-Vocabulary",
        {
            "type": "wordlist",
            "title": "山田ハヨさんの語彙（アイヌ語樺太方言）",
            "title_en": "Yamada Hayo's vocabulary — Sakhalin Ainu (Tamura field notes)",
            "author": {"ja": "田村 すず子（筆録）", "en": "Suzuko Tamura (rec.)"},
            "publisher": {"ja": "環太平洋の言語 (ELPR)", "en": "Endangered Languages of the Pacific Rim (ELPR)"},
            "year": 1958,
            "dialect": "樺太",
            "recorded_at": "1958-07-30",
            "license": "All rights reserved (ELPR A2; research use)",
            "source": (
                "OCR of ELPR publication A2 『アイヌ語 樺太・名寄・釧路方言の資料』 "
                "(田村すず子採録), 第II編 山田ハヨさんの語彙 (notebook pp.1–15). "
                "Speaker 山田ハヨ (b.1894), Sakhalin roots (多蘭泊), recorded by 田村すず子 "
                "as handwritten notes (no audio). Edited by 北原次郎太. "
                "OCR'd with gemini-3.5-flash."
            ),
            "notes": (
                "Romanized Ainu only (no katakana — there is no audio source). Acute = pitch "
                "accent. Mixes single words with short example sentences. The oral-literature "
                "passage (notebook pp.16–17) is in ainu-corpora/texts/tamura-karafuto-yamada."
            ),
            "columns": {
                "num": "running entry number within a notebook page",
                "src_page": "原本 (notebook) page number",
                "category": "topical section header when present",
                "gloss_ja": "Japanese gloss / prompt",
                "lemma": "romanized Ainu (Tamura transcription, acute = pitch accent)",
                "notes": "remarks, dialect notes, footnote markers",
            },
            "parent": {
                "type": "book",
                "title": "アイヌ語 樺太・名寄・釧路方言の資料 (ELPR A2)",
                "publisher": "文部科学省特定領域研究「環太平洋の『消滅に瀕した言語』にかんする緊急調査研究」",
            },
        },
        yamada_rows,
    )


if __name__ == "__main__":
    print("Tamura ELPR routing (corpus phase)")

    # ---- Part I: 藤山ハル (Sakhalin / 来知志) -------------------------------
    fujiyama_sections = [
        ("001.yaml", "ウチャシクマ 1 (言い伝え1)", range(18, 27)),
        ("002.yaml", "ウチャシクマ 2 (言い伝え2)", range(37, 43)),
        ("003.yaml", "ウチャシクマ 3 (言い伝え3)", range(47, 55)),
        ("004.yaml", "ウチャシクマ 4 (言い伝え4)", range(63, 96)),
        ("005.yaml", "トゥイタハ (言い伝え5)", range(112, 146)),
        ("006.yaml", "イフンケ 1 (子守歌1)", range(157, 161)),
        ("007.yaml", "イフンケ 2 (子守歌2)", range(161, 166)),
        ("008.yaml", "シノホサ (酒歌)", range(166, 169)),
        ("009.yaml", "イフンケ 3 (子守歌3)", range(169, 171)),
    ]
    fujiyama_docs = [(n, build_interlinear_doc(r, t)) for n, t, r in fujiyama_sections]
    write_corpus_collection(
        "tamura-karafuto-fujiyama",
        {
            "title": "藤山ハルさんの口頭文芸と歌（樺太方言）",
            "author": "藤山 ハル",
            "dialect": {"name": "ライチシカ", "path": "樺太/西海岸/来知志"},
            "recorded_at": "1959-10-20",
            "recorded_by": "田村 すず子",
            "published_at": "2003",
            "uri": "urn:elpr:A2",
        },
        fujiyama_docs,
    )

    # ---- Part III: 北風磯吉 (Nayoro) -------------------------------------
    kita_docs = [
        ("001.yaml", build_interlinear_doc(range(215, 217), "散文説話 (001)")),
        ("002.yaml", build_kitakaze_doc(range(218, 242), "語彙（問答・例文 002〜145）")),
    ]
    write_corpus_collection(
        "tamura-nayoro-kitakaze",
        {
            "title": "北風磯吉さんの口頭文芸と語彙（名寄方言）",
            "author": "北風 磯吉",
            "dialect": {"name": "名寄", "path": "北海道/北東/名寄"},
            "recorded_at": "1962-08-19",
            "recorded_by": "田村 すず子",
            "published_at": "2003",
            "uri": "urn:elpr:A2",
        },
        kita_docs,
    )

    # ---- Part IV: 徹辺重次郎 (Kushiro) oral lit --------------------------
    tetsube_docs = [
        ("001.yaml", build_interlinear_doc(range(316, 319), "ウチャシクマ 1 (言い伝え1)")),
        ("002.yaml", build_interlinear_doc(range(319, 322), "ウチャシクマ 2 (言い伝え2)")),
    ]
    write_corpus_collection(
        "tamura-kushiro-tetsube",
        {
            "title": "徹辺重次郎さんの口頭文芸（釧路方言）",
            "author": "徹辺 重次郎",
            "dialect": "北海道/北東/釧路",
            "recorded_at": "1960-01-08/1960-10-25",
            "recorded_by": "田村 すず子",
            "published_at": "2003",
            "uri": "urn:elpr:A2",
        },
        tetsube_docs,
    )

    # ---- Part II: 山田ハヨ (Sakhalin) oral narrative ---------------------
    yamada_oral = build_yamada_oral_doc(range(198, 200), "口頭文芸（ある村の物語）")
    write_corpus_collection(
        "tamura-karafuto-yamada",
        {
            "title": "山田ハヨさんの口頭文芸（樺太方言）",
            "author": "山田 ハヨ",
            "dialect": "樺太",
            "recorded_at": "1958-07-30",
            "recorded_by": "田村 すず子",
            "published_at": "2003",
            "uri": "urn:elpr:A2",
        },
        [("001.yaml", yamada_oral)],
    )

    route_dictionaries()
