from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
INPUT_DIR = ROOT_DIR / "corpus" / "output" / "ninjal"
OUTPUT_DIR = INPUT_DIR / "lexicon"


@dataclass(slots=True)
class MorphemeOccurrence:
    morpheme: str
    gloss_en: str
    gloss_jp: str
    story_id: str
    story_sentence_id: str
    unit_index: int
    part_index: int
    unit_morpheme: str
    unit_gloss_en: str
    unit_gloss_jp: str
    translation_en: str
    translation_jp: str


def split_units(text: str) -> list[str]:
    if not text:
        return []
    return text.split("||")


def split_compound(text: str) -> list[str]:
    if not text:
        return []
    return text.split("-")


def load_story_rows(path: Path) -> list[dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("data", [])


def extract_occurrences() -> tuple[list[MorphemeOccurrence], list[dict[str, str]]]:
    occurrences: list[MorphemeOccurrence] = []
    unresolved: list[dict[str, str]] = []

    for path in sorted(INPUT_DIR.glob("*.json")):
        story_id = path.stem
        for row in load_story_rows(path):
            morpheme_units = split_units(row.get("morpheme", ""))
            gloss_en_units = split_units(row.get("gloss_en", ""))
            gloss_jp_units = split_units(row.get("gloss_jp", ""))

            min_len = min(len(morpheme_units), len(gloss_en_units), len(gloss_jp_units))
            if len({len(morpheme_units), len(gloss_en_units), len(gloss_jp_units)}) != 1:
                unresolved.append(
                    {
                        "reason": "unit_count_mismatch",
                        "story_id": story_id,
                        "story_sentence_id": row.get("story_sentence_id", ""),
                        "morpheme": row.get("morpheme", ""),
                        "gloss_en": row.get("gloss_en", ""),
                        "gloss_jp": row.get("gloss_jp", ""),
                        "translation_en": row.get("translation_en", ""),
                        "translation_jp": row.get("translation_jp", ""),
                    }
                )

            for unit_index in range(min_len):
                unit_morpheme = morpheme_units[unit_index]
                unit_gloss_en = gloss_en_units[unit_index]
                unit_gloss_jp = gloss_jp_units[unit_index]

                morpheme_parts = split_compound(unit_morpheme)
                gloss_en_parts = split_compound(unit_gloss_en)
                gloss_jp_parts = split_compound(unit_gloss_jp)

                if len(morpheme_parts) == len(gloss_en_parts) == len(gloss_jp_parts):
                    for part_index, (morpheme, gloss_en, gloss_jp) in enumerate(
                        zip(morpheme_parts, gloss_en_parts, gloss_jp_parts),
                        start=1,
                    ):
                        occurrences.append(
                            MorphemeOccurrence(
                                morpheme=morpheme,
                                gloss_en=gloss_en,
                                gloss_jp=gloss_jp,
                                story_id=story_id,
                                story_sentence_id=row.get("story_sentence_id", ""),
                                unit_index=unit_index + 1,
                                part_index=part_index,
                                unit_morpheme=unit_morpheme,
                                unit_gloss_en=unit_gloss_en,
                                unit_gloss_jp=unit_gloss_jp,
                                translation_en=row.get("translation_en", ""),
                                translation_jp=row.get("translation_jp", ""),
                            )
                        )
                    continue

                unresolved.append(
                    {
                        "reason": "compound_alignment_mismatch",
                        "story_id": story_id,
                        "story_sentence_id": row.get("story_sentence_id", ""),
                        "unit_index": str(unit_index + 1),
                        "unit_morpheme": unit_morpheme,
                        "unit_gloss_en": unit_gloss_en,
                        "unit_gloss_jp": unit_gloss_jp,
                        "morpheme_parts": " | ".join(morpheme_parts),
                        "gloss_en_parts": " | ".join(gloss_en_parts),
                        "gloss_jp_parts": " | ".join(gloss_jp_parts),
                        "translation_en": row.get("translation_en", ""),
                        "translation_jp": row.get("translation_jp", ""),
                    }
                )
                occurrences.append(
                    MorphemeOccurrence(
                        morpheme=unit_morpheme,
                        gloss_en=unit_gloss_en,
                        gloss_jp=unit_gloss_jp,
                        story_id=story_id,
                        story_sentence_id=row.get("story_sentence_id", ""),
                        unit_index=unit_index + 1,
                        part_index=1,
                        unit_morpheme=unit_morpheme,
                        unit_gloss_en=unit_gloss_en,
                        unit_gloss_jp=unit_gloss_jp,
                        translation_en=row.get("translation_en", ""),
                        translation_jp=row.get("translation_jp", ""),
                    )
                )

    return occurrences, unresolved


def write_occurrences(path: Path, occurrences: list[MorphemeOccurrence]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(
            [
                "morpheme",
                "gloss_en",
                "gloss_jp",
                "story_id",
                "story_sentence_id",
                "unit_index",
                "part_index",
                "unit_morpheme",
                "unit_gloss_en",
                "unit_gloss_jp",
                "translation_en",
                "translation_jp",
            ]
        )
        for item in occurrences:
            writer.writerow(
                [
                    item.morpheme,
                    item.gloss_en,
                    item.gloss_jp,
                    item.story_id,
                    item.story_sentence_id,
                    item.unit_index,
                    item.part_index,
                    item.unit_morpheme,
                    item.unit_gloss_en,
                    item.unit_gloss_jp,
                    item.translation_en,
                    item.translation_jp,
                ]
            )


def write_lexicon(path: Path, occurrences: list[MorphemeOccurrence]) -> None:
    gloss_en_counts: dict[str, Counter[str]] = defaultdict(Counter)
    gloss_jp_counts: dict[str, Counter[str]] = defaultdict(Counter)
    story_counts: Counter[str] = Counter()
    sentence_counts: Counter[str] = Counter()
    examples: dict[str, MorphemeOccurrence] = {}

    for item in occurrences:
        gloss_en_counts[item.morpheme][item.gloss_en] += 1
        gloss_jp_counts[item.morpheme][item.gloss_jp] += 1
        story_counts[item.morpheme] += 1
        sentence_counts[f"{item.morpheme}\t{item.story_sentence_id}"] += 1
        examples.setdefault(item.morpheme, item)

    sentence_totals: Counter[str] = Counter()
    for key in sentence_counts:
        morpheme, _sentence_id = key.split("\t", 1)
        sentence_totals[morpheme] += 1

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(
            [
                "morpheme",
                "occurrence_count",
                "sentence_count",
                "primary_gloss_en",
                "primary_gloss_jp",
                "gloss_en_variants",
                "gloss_jp_variants",
                "example_unit_morpheme",
                "example_unit_gloss_en",
                "example_unit_gloss_jp",
                "example_story_sentence_id",
                "example_translation_en",
                "example_translation_jp",
            ]
        )

        for morpheme in sorted(story_counts, key=lambda item: (-story_counts[item], item)):
            example = examples[morpheme]
            writer.writerow(
                [
                    morpheme,
                    story_counts[morpheme],
                    sentence_totals[morpheme],
                    most_common_string(gloss_en_counts[morpheme]),
                    most_common_string(gloss_jp_counts[morpheme]),
                    join_counter(gloss_en_counts[morpheme]),
                    join_counter(gloss_jp_counts[morpheme]),
                    example.unit_morpheme,
                    example.unit_gloss_en,
                    example.unit_gloss_jp,
                    example.story_sentence_id,
                    example.translation_en,
                    example.translation_jp,
                ]
            )


def write_unresolved(path: Path, unresolved: list[dict[str, str]]) -> None:
    if not unresolved:
        unresolved = [{"reason": "none"}]

    fieldnames = sorted({key for row in unresolved for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(unresolved)


def most_common_string(counter: Counter[str]) -> str:
    if not counter:
        return ""
    return counter.most_common(1)[0][0]


def join_counter(counter: Counter[str]) -> str:
    return " || ".join(
        f"{value} ({count})" for value, count in counter.most_common()
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    occurrences, unresolved = extract_occurrences()
    write_occurrences(OUTPUT_DIR / "ninjal_morpheme_occurrences.tsv", occurrences)
    write_lexicon(OUTPUT_DIR / "ninjal_morpheme_lexicon.tsv", occurrences)
    write_unresolved(OUTPUT_DIR / "ninjal_morpheme_unresolved.tsv", unresolved)
    print(f"Extracted {len(occurrences)} morpheme occurrences")
    print(f"Flagged {len(unresolved)} unresolved rows")
    print(f"Wrote outputs to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
