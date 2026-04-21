from __future__ import annotations

import csv
import json
import re
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FINAL_ROOT = ROOT / "dictionary" / "output" / "nakagawa-ocr-final"
OUTPUT_PATH = ROOT / "dictionary" / "output" / "nakagawa_terms.jsonl"
TSV_OUTPUT_PATH = ROOT / "dictionary" / "output" / "nakagawa_terms.tsv"

ENTRY_START_RE = re.compile(
    r"(?P<left>[^\n【】]+?)\s*【(?P<pos>[^】]+)】"
)
LATN_ALLOWED_RE = re.compile(r"^[\w=\-_'.,?/~²³⁴]+$", re.UNICODE)
KANA_HEAD_RE = re.compile(r"[ァ-ヶーㇰ-ㇿ゠・､-ﾟ〜～]")
JAPANESE_CHAR_RE = re.compile(r"[ぁ-んァ-ヶ一-龯ㇰ-ㇿー〜～]")
LATIN_CHAR_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]")


@dataclass
class Entry:
    page: int
    head: dict[str, str]
    pos: str
    description: str


def normalize_spaces(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.replace("　", " ")).strip()


def flatten_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("　", " ")).strip()


def is_indented(line: str) -> bool:
    return bool(line) and line[0] in {" ", "　", "\t"}


def looks_like_latn(value: str) -> bool:
    compact = value.strip()
    if not compact:
        return False
    return LATN_ALLOWED_RE.fullmatch(compact) is not None


def looks_like_kana_head(value: str) -> bool:
    return KANA_HEAD_RE.search(value) is not None


def tokenize_head(text: str) -> list[str]:
    return [token for token in normalize_spaces(text).split(" ") if token]


def is_latin_token(token: str) -> bool:
    compact = token.strip()
    if not compact:
        return False
    if JAPANESE_CHAR_RE.search(compact):
        return False
    return LATIN_CHAR_RE.search(compact) is not None


def split_head_and_latn(left_side: str) -> tuple[str, str] | None:
    tokens = tokenize_head(left_side)
    if len(tokens) < 2:
        return None
    split_index = len(tokens)
    while split_index > 0 and is_latin_token(tokens[split_index - 1]):
        split_index -= 1
    if split_index == len(tokens) or split_index == 0:
        return None
    kana = " ".join(tokens[:split_index])
    latn = " ".join(tokens[split_index:])
    if not looks_like_kana_head(kana):
        return None
    if not LATIN_CHAR_RE.search(latn):
        return None
    return kana, latn


def flush_entry(entries: list[Entry], current: tuple[int, str, str, str, list[str]] | None) -> None:
    if current is None:
        return
    page, kana, latn, pos, description_lines = current
    description = normalize_spaces(" ".join(line.strip() for line in description_lines if line.strip()))
    if not description:
        return
    entries.append(
        Entry(
            page=page,
            head={"kana": kana, "latn": latn},
            pos=pos,
            description=description,
        )
    )


def load_corpus_text() -> tuple[str, list[tuple[int, int]]]:
    pieces: list[str] = []
    offsets: list[tuple[int, int]] = []
    offset = 0
    for page_dir in sorted(FINAL_ROOT.glob("page-*")):
        page_value = page_dir.name.removeprefix("page-")
        if not page_value.isdigit():
            continue
        final_path = page_dir / "final.txt"
        if not final_path.exists():
            continue
        page = int(page_value)
        text = final_path.read_text(encoding="utf-8")
        offsets.append((offset, page))
        pieces.append(text)
        offset += len(text)
        pieces.append("\n")
        offset += 1
    return "".join(pieces), offsets


def page_for_offset(offsets: list[tuple[int, int]], index: int) -> int:
    start_positions = [item[0] for item in offsets]
    page_index = bisect_right(start_positions, index) - 1
    if page_index < 0:
        return offsets[0][1]
    return offsets[page_index][1]


def extract_entries(text: str, offsets: list[tuple[int, int]]) -> list[Entry]:
    entries: list[Entry] = []
    matches = list(ENTRY_START_RE.finditer(text))
    for match_index, match in enumerate(matches):
        left_side = normalize_spaces(match.group("left"))
        split_result = split_head_and_latn(left_side)
        if split_result is None:
            continue
        kana, latn = split_result
        if not looks_like_latn(re.sub(r"[〜～]", "", latn.replace(" ", ""))):
            continue
        description_start = match.end()
        description_end = matches[match_index + 1].start() if match_index + 1 < len(matches) else len(text)
        description = flatten_text(text[description_start:description_end])
        if not description:
            continue
        entries.append(
            Entry(
                page=page_for_offset(offsets, match.start()),
                head={"kana": kana, "latn": latn},
                pos=match.group("pos"),
                description=description,
            )
        )
    return entries


def export_jsonl() -> list[Entry]:
    text, offsets = load_corpus_text()
    all_entries = extract_entries(text, offsets)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        for entry in all_entries:
            payload = {
                "page": entry.page,
                "head": entry.head,
                "pos": entry.pos,
                "description": entry.description,
            }
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    with TSV_OUTPUT_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["kana", "latn", "pos", "definition", "page"],
            delimiter="\t",
        )
        writer.writeheader()
        for entry in all_entries:
            writer.writerow(
                {
                    "kana": entry.head["kana"],
                    "latn": entry.head["latn"],
                    "pos": entry.pos,
                    "definition": entry.description,
                    "page": entry.page,
                }
            )
    return all_entries


def main() -> None:
    entries = export_jsonl()
    print(f"Wrote {len(entries)} entries to {OUTPUT_PATH}")
    print(f"Wrote TSV to {TSV_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
