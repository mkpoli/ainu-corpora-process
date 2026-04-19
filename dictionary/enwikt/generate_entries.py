import csv
import io
import json
from pathlib import Path
from typing import TypedDict

import ainconv
import regex as re
from wiktionary.document import Document
from contextlib import redirect_stdout

from dictionary.enwikt.paths import (
    FILTERED_ENTRIES_JSON_NAME,
    GLOSSES_JSON_NAME,
    RAW_ENTRIES_JSON_NAME,
    TSV_NAME,
    small_output_dir,
)


OUTPUT_DIR = small_output_dir()
INPUT_ENTRIES_JSON = OUTPUT_DIR / RAW_ENTRIES_JSON_NAME
OUTPUT_FILTERED_JSON = OUTPUT_DIR / FILTERED_ENTRIES_JSON_NAME
OUTPUT_GLOSSES_JSON = OUTPUT_DIR / GLOSSES_JSON_NAME
OUTPUT_TSV = OUTPUT_DIR / TSV_NAME

NON_POS_SECTIONS = {
    "Alternative forms",
    "Anagrams",
    "Descendants",
    "Derived terms",
    "Etymology",
    "Further reading",
    "Inflection",
    "Pronunciation",
    "References",
    "Related terms",
    "See also",
    "Synonyms",
    "Translations",
}

POS_MAP = {
    "adjective": "verb",
    "adnominal": "adnom",
    "adverb": "adv",
    "conjunction": "conj",
    "determiner": "determiner",
    "interjection": "interj",
    "noun": "noun",
    "numeral": "num",
    "particle": "parti",
    "postposition": "postpadv",
    "prefix": "prefix",
    "pronoun": "pron",
    "proper noun": "noun",
    "root": "root",
    "suffix": "suffix",
    "verb": "verb",
}


class RawEntry(TypedDict):
    title: str
    text: str


class FilteredEntry(TypedDict):
    lemma: str
    lemma_original: str
    text: str


class GlossEntry(TypedDict):
    lemma: str
    lemma_original: str
    pos: str
    glosses: list[str]


TITLE_RE = re.compile(r"^[\p{sc=Latn}=\- '’0-9_]+$")
KANA_TITLE_RE = re.compile(
    r"^[\p{sc=Kana}\p{blk=Katakana_Phonetic_Extensions}ー=\- '’0-9_]+$"
)


def is_candidate_title(title: str) -> bool:
    return bool(TITLE_RE.match(title) or KANA_TITLE_RE.match(title))


def normalize_lemma(title: str) -> str:
    if TITLE_RE.match(title):
        return title

    # ainconv currently prints debug output during conversion, so suppress it.
    with redirect_stdout(io.StringIO()):
        return ainconv.kana2latn(title)


def extract_ainu_sections(entries: list[RawEntry]) -> dict[str, FilteredEntry]:
    filtered_entries: dict[str, FilteredEntry] = {}
    for entry in entries:
        title = entry["title"]
        if not is_candidate_title(title):
            continue

        doc = Document.from_wikitext(entry["text"])
        for section in doc.sections:
            if section.title == "Ainu":
                filtered_entries[title] = {
                    "lemma": normalize_lemma(title),
                    "lemma_original": title,
                    "text": str(object=section),
                }
                break

    return filtered_entries


def normalize_pos(title: str) -> str | None:
    normalized = title.strip().lower()
    return POS_MAP.get(normalized)


def clean_template_markup(text: str) -> str:
    text = re.sub(r"\{\{gloss\|([^{}|]+?)(?:\|[^{}]*?)?\}\}", r"\1", text)
    text = re.sub(r"\{\{qualifier\|([^{}]+?)\}\}", r"\1", text)
    text = re.sub(r"\{\{lb\|[^{}]*\|([^{}]+?)\}\}", r"\1", text)
    text = re.sub(r"\{\{l\|[^{}]*\|([^{}|]+?)(?:\|[^{}]*?)?\}\}", r"\1", text)
    text = re.sub(r"\{\{m\|[^{}]*\|([^{}|]+?)(?:\|[^{}]*?)?\}\}", r"\1", text)
    text = re.sub(r"\{\{[^{}]+\}\}", "", text)
    return text


def clean_gloss(gloss: str) -> str:
    gloss = re.sub(r"<!--.*?-->", "", gloss)
    gloss = re.sub(r"<ref[^>]*>.*?</ref>", "", gloss)
    gloss = re.sub(r"<ref.*", "", gloss)
    gloss = re.sub(r"\[\[(?:[^\]|]+\|)?([^\]]+)\]\]", r"\1", gloss)
    gloss = clean_template_markup(gloss)
    gloss = gloss.replace("''", "")
    gloss = gloss.replace("&lt;", "<").replace("&gt;", ">")
    gloss = re.sub(r"\s+", " ", gloss)
    gloss = re.sub(r"^[;,:.\s-]+", "", gloss)
    gloss = re.sub(r"\s+([,.;:])", r"\1", gloss)
    return gloss.strip()


def extract_glosses(section_text: str) -> list[str]:
    glosses: list[str] = []
    seen: set[str] = set()

    for line in section_text.splitlines():
        if not line.startswith("#"):
            continue
        if line.startswith(("#*", "#:", "##")):
            continue

        gloss = clean_gloss(line[1:].strip())
        if not gloss or gloss in seen:
            continue

        seen.add(gloss)
        glosses.append(gloss)

    return glosses


def extract_gloss_dictionary(
    filtered_entries: dict[str, FilteredEntry],
) -> dict[str, GlossEntry]:
    gloss_dictionary: dict[str, GlossEntry] = {}

    for title, entry in filtered_entries.items():
        doc = Document.from_wikitext(entry["text"])
        for section in doc.sections[0].subsections:
            if section.title in NON_POS_SECTIONS:
                continue

            pos = normalize_pos(section.title)
            if not pos:
                continue

            glosses = extract_glosses(section.content)
            if not glosses:
                continue

            existing = gloss_dictionary.get(title)
            if existing is None:
                gloss_dictionary[title] = {
                    "lemma": entry["lemma"],
                    "lemma_original": entry["lemma_original"],
                    "pos": pos,
                    "glosses": glosses,
                }
                continue

            if existing["pos"] != pos:
                continue

            for gloss in glosses:
                if gloss not in existing["glosses"]:
                    existing["glosses"].append(gloss)

    return gloss_dictionary


def write_tsv(gloss_dictionary: dict[str, GlossEntry], output_path: Path) -> None:
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["lemma", "lemma_original", "pos", "definition"])
        for entry in gloss_dictionary.values():
            writer.writerow(
                [
                    entry["lemma"],
                    entry["lemma_original"],
                    entry["pos"],
                    "; ".join(entry["glosses"]),
                ]
            )


def main() -> None:
    with open(INPUT_ENTRIES_JSON, "r", encoding="utf-8") as f:
        wiktionary_ainu_entries: list[RawEntry] = json.load(f)

    filtered_entries = extract_ainu_sections(wiktionary_ainu_entries)
    with open(OUTPUT_FILTERED_JSON, "w", encoding="utf-8") as f:
        json.dump(filtered_entries, f, ensure_ascii=False, indent=4)

    gloss_dictionary = extract_gloss_dictionary(filtered_entries)
    with open(OUTPUT_GLOSSES_JSON, "w", encoding="utf-8") as f:
        json.dump(gloss_dictionary, f, ensure_ascii=False, indent=4)

    write_tsv(gloss_dictionary, OUTPUT_TSV)

    print(f"Filtered {len(filtered_entries)} English Wiktionary Ainu entries")
    print(f"Generated {len(gloss_dictionary)} English Wiktionary gloss entries")
    print(f"Wrote gloss JSON to {OUTPUT_GLOSSES_JSON}")
    print(f"Wrote TSV to {OUTPUT_TSV}")


if __name__ == "__main__":
    main()
