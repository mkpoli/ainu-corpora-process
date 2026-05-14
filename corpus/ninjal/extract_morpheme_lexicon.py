from __future__ import annotations

import csv
import html
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
INPUT_DIR = ROOT_DIR / "corpus" / "output" / "ninjal"
OUTPUT_DIR = INPUT_DIR / "lexicon"


@dataclass(slots=True)
class MorphemeOccurrence:
    morpheme: str
    raw_morpheme: str
    gloss_en: str
    gloss_jp: str
    normalization_note: str
    story_id: str
    story_sentence_id: str
    unit_index: int
    part_index: int
    unit_morpheme: str
    unit_gloss_en: str
    unit_gloss_jp: str
    translation_en: str
    translation_jp: str


LEADING_QUOTES = '"“”‘’「『'
TRAILING_QUOTES = '"“”‘’」』'
TRAILING_PUNCTUATION = ",.?!;:"
NOISE_VALUES = {"", "―", "ー", "***", "...", "…", "?"}
JAPANESE_TEXT_PATTERN = re.compile(r"[ぁ-んァ-ン一-龯々〆ヵヶ]")
RAW_REFRain_PATTERN = re.compile(r"^V(?:\d+)?(?:[:(].*)?$")
RAW_JAP_SOURCE_PATTERN = re.compile(
    r"^(?P<base>[A-Za-z=\-]+)\(<(?P<source>[^)>]+)>?\)$"
)
RAW_OPTIONAL_SEGMENT_PATTERN = re.compile(r"^\((?P<prefix>[A-Za-z=]*)\)(?P<rest>[A-Za-z=\-]+)$")
RAW_BRACKET_SEGMENT_PATTERN = re.compile(r"^(?P<prefix>[A-Za-z=\-]*)\[(?P<inside>[A-Za-z=]+)\](?P<suffix>[A-Za-z=\-]*)$")
RAW_QUESTION_PATTERN = re.compile(r"^(?P<base>[A-Za-z=\-]+)\(\?\)$")
RAW_NI_DOT_PATTERN = re.compile(r"^NI\.(?P<rest>[A-Za-z=\-]+)$")


@dataclass(slots=True)
class MorphemeNormalization:
    morpheme: str
    note: str
    drop: bool = False


def split_units(text: str) -> list[str]:
    if not text:
        return []
    return text.split("||")


def split_compound(text: str) -> list[str]:
    if not text:
        return []
    return text.split("-")


def normalize_morpheme(text: str) -> str:
    normalized = text.strip()
    normalized = normalized.strip(LEADING_QUOTES + TRAILING_QUOTES)
    normalized = normalized.rstrip(TRAILING_PUNCTUATION)
    normalized = normalized.strip(LEADING_QUOTES + TRAILING_QUOTES)
    normalized = re.sub(r"\s+", "", normalized)
    return normalized


def normalize_gloss(text: str) -> str:
    return text.strip()


def is_noise_morpheme(text: str) -> bool:
    return text in NOISE_VALUES


def combine_notes(*notes: str) -> str:
    return " | ".join(note for note in notes if note)


def normalize_morpheme_with_note(text: str) -> MorphemeNormalization:
    raw = normalize_morpheme(html.unescape(text))
    if not raw:
        return MorphemeNormalization(morpheme="", note="empty", drop=True)

    if is_noise_morpheme(raw):
        return MorphemeNormalization(morpheme=raw, note="noise_token", drop=True)

    if RAW_REFRain_PATTERN.fullmatch(raw):
        return MorphemeNormalization(morpheme=raw, note="refrain_marker", drop=True)

    if raw in {"って", "ここへ、蝿だからここへ"} or JAPANESE_TEXT_PATTERN.search(raw):
        return MorphemeNormalization(morpheme=raw, note="japanese_transcript_noise", drop=True)

    note = ""
    normalized = raw

    match = RAW_JAP_SOURCE_PATTERN.fullmatch(normalized)
    if match:
        normalized = match.group("base")
        note = combine_notes(note, f"source:{match.group('source')}")

    match = RAW_OPTIONAL_SEGMENT_PATTERN.fullmatch(normalized)
    if match:
        normalized = f"{match.group('prefix')}{match.group('rest')}"
        note = combine_notes(note, "optional_segment_unwrapped")

    match = RAW_QUESTION_PATTERN.fullmatch(normalized)
    if match:
        normalized = match.group("base")
        note = combine_notes(note, "uncertain_form_marker_removed")

    match = RAW_BRACKET_SEGMENT_PATTERN.fullmatch(normalized)
    if match:
        normalized = f"{match.group('prefix')}{match.group('inside')}{match.group('suffix')}"
        note = combine_notes(note, "bracket_markup_removed")

    match = RAW_NI_DOT_PATTERN.fullmatch(normalized)
    if match:
        normalized = match.group("rest")
        note = combine_notes(note, "ni_prefix_annotation_removed")

    normalized = normalize_morpheme(normalized)
    if not normalized or is_noise_morpheme(normalized):
        return MorphemeNormalization(morpheme=normalized, note=combine_notes(note, "empty_after_normalization"), drop=True)

    return MorphemeNormalization(morpheme=normalized, note=note, drop=False)


def expand_japanese_gloss(gloss_jp: str, target_len: int) -> list[str] | None:
    if target_len == 1:
        return [gloss_jp]

    parts = split_compound(gloss_jp)
    if len(parts) == target_len:
        return parts
    if len(parts) == 1:
        return [gloss_jp] * target_len
    return None


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

                unit_normalization = normalize_morpheme_with_note(unit_morpheme)
                normalized_unit_morpheme = unit_normalization.morpheme
                normalized_unit_gloss_en = normalize_gloss(unit_gloss_en)
                normalized_unit_gloss_jp = normalize_gloss(unit_gloss_jp)

                if unit_normalization.drop:
                    unresolved.append(
                        {
                            "reason": "dropped_noise_or_annotation",
                            "story_id": story_id,
                            "story_sentence_id": row.get("story_sentence_id", ""),
                            "unit_index": str(unit_index + 1),
                            "unit_morpheme": unit_morpheme,
                            "unit_gloss_en": normalized_unit_gloss_en,
                            "unit_gloss_jp": normalized_unit_gloss_jp,
                            "normalization_note": unit_normalization.note,
                            "translation_en": row.get("translation_en", ""),
                            "translation_jp": row.get("translation_jp", ""),
                        }
                    )
                    continue

                raw_part_units = split_compound(unit_morpheme)
                part_normalizations = [
                    normalize_morpheme_with_note(part)
                    for part in raw_part_units
                ]
                kept_parts = [
                    (raw_part, part)
                    for raw_part, part in zip(raw_part_units, part_normalizations)
                    if not part.drop
                ]
                morpheme_parts = [part.morpheme for _raw_part, part in kept_parts]
                morpheme_part_notes = [part.note for _raw_part, part in kept_parts]
                raw_part_forms = [raw_part for raw_part, _part in kept_parts]
                gloss_en_parts = [
                    normalize_gloss(part) for part in split_compound(normalized_unit_gloss_en)
                ]
                gloss_jp_parts = expand_japanese_gloss(normalized_unit_gloss_jp, len(morpheme_parts))

                if not morpheme_parts:
                    continue

                if len(morpheme_parts) == len(gloss_en_parts) and gloss_jp_parts is not None:
                    for part_index, (morpheme, gloss_en, gloss_jp, raw_part, note_part) in enumerate(
                        zip(
                            morpheme_parts,
                            gloss_en_parts,
                            gloss_jp_parts,
                            raw_part_forms,
                            morpheme_part_notes,
                        ),
                        start=1,
                    ):
                        occurrences.append(
                            MorphemeOccurrence(
                                morpheme=morpheme,
                                raw_morpheme=raw_part,
                                gloss_en=gloss_en,
                                gloss_jp=gloss_jp,
                                normalization_note=combine_notes(unit_normalization.note, note_part),
                                story_id=story_id,
                                story_sentence_id=row.get("story_sentence_id", ""),
                                unit_index=unit_index + 1,
                                part_index=part_index,
                                unit_morpheme=normalized_unit_morpheme,
                                unit_gloss_en=normalized_unit_gloss_en,
                                unit_gloss_jp=normalized_unit_gloss_jp,
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
                        "unit_morpheme": normalized_unit_morpheme,
                        "unit_gloss_en": normalized_unit_gloss_en,
                        "unit_gloss_jp": normalized_unit_gloss_jp,
                        "morpheme_parts": " | ".join(morpheme_parts),
                        "gloss_en_parts": " | ".join(gloss_en_parts),
                        "gloss_jp_parts": "" if gloss_jp_parts is None else " | ".join(gloss_jp_parts),
                        "translation_en": row.get("translation_en", ""),
                        "translation_jp": row.get("translation_jp", ""),
                    }
                )

                if len(morpheme_parts) > 1:
                    fallback_gloss_en_parts = gloss_en_parts
                    if len(fallback_gloss_en_parts) != len(morpheme_parts):
                        fallback_gloss_en_parts = [""] * len(morpheme_parts)

                    fallback_gloss_jp_parts = gloss_jp_parts
                    if fallback_gloss_jp_parts is None or len(fallback_gloss_jp_parts) != len(morpheme_parts):
                        fallback_gloss_jp_parts = [""] * len(morpheme_parts)

                    for part_index, (morpheme, gloss_en, gloss_jp, raw_part, note_part) in enumerate(
                        zip(
                            morpheme_parts,
                            fallback_gloss_en_parts,
                            fallback_gloss_jp_parts,
                            raw_part_forms,
                            morpheme_part_notes,
                        ),
                        start=1,
                    ):
                        occurrences.append(
                            MorphemeOccurrence(
                                morpheme=morpheme,
                                raw_morpheme=raw_part,
                                gloss_en=gloss_en,
                                gloss_jp=gloss_jp,
                                normalization_note=combine_notes(unit_normalization.note, note_part),
                                story_id=story_id,
                                story_sentence_id=row.get("story_sentence_id", ""),
                                unit_index=unit_index + 1,
                                part_index=part_index,
                                unit_morpheme=normalized_unit_morpheme,
                                unit_gloss_en=normalized_unit_gloss_en,
                                unit_gloss_jp=normalized_unit_gloss_jp,
                                translation_en=row.get("translation_en", ""),
                                translation_jp=row.get("translation_jp", ""),
                            )
                        )
                    continue

                occurrences.append(
                    MorphemeOccurrence(
                        morpheme=normalized_unit_morpheme,
                        raw_morpheme=unit_morpheme,
                        gloss_en=normalized_unit_gloss_en,
                        gloss_jp=normalized_unit_gloss_jp,
                        normalization_note=unit_normalization.note,
                        story_id=story_id,
                        story_sentence_id=row.get("story_sentence_id", ""),
                        unit_index=unit_index + 1,
                        part_index=1,
                        unit_morpheme=normalized_unit_morpheme,
                        unit_gloss_en=normalized_unit_gloss_en,
                        unit_gloss_jp=normalized_unit_gloss_jp,
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
                "raw_morpheme",
                "gloss_en",
                "gloss_jp",
                "normalization_note",
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
                    item.raw_morpheme,
                    item.gloss_en,
                    item.gloss_jp,
                    item.normalization_note,
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
    raw_morpheme_counts: dict[str, Counter[str]] = defaultdict(Counter)
    normalization_note_counts: dict[str, Counter[str]] = defaultdict(Counter)
    story_counts: Counter[str] = Counter()
    sentence_counts: Counter[str] = Counter()
    examples: dict[str, MorphemeOccurrence] = {}

    for item in occurrences:
        if item.gloss_en:
            gloss_en_counts[item.morpheme][item.gloss_en] += 1
        if item.gloss_jp:
            gloss_jp_counts[item.morpheme][item.gloss_jp] += 1
        raw_morpheme_counts[item.morpheme][item.raw_morpheme] += 1
        if item.normalization_note:
            normalization_note_counts[item.morpheme][item.normalization_note] += 1
        story_counts[item.morpheme] += 1
        sentence_counts[f"{item.morpheme}\t{item.story_sentence_id}"] += 1
        if item.morpheme not in examples:
            examples[item.morpheme] = item
        elif not examples[item.morpheme].gloss_en and item.gloss_en:
            examples[item.morpheme] = item

    sentence_totals: Counter[str] = Counter()
    for key in sentence_counts:
        morpheme, _sentence_id = key.split("\t", 1)
        sentence_totals[morpheme] += 1

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(
            [
                "morpheme",
                "raw_morpheme_variants",
                "normalization_notes",
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
                    join_counter(raw_morpheme_counts[morpheme]),
                    join_counter(normalization_note_counts[morpheme]),
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
