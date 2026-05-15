"""Hand-curated English/Japanese gloss backfill.

Many compound entries inherited from Tommy 1949 and the Japanese Wiktionary
come with a Japanese gloss but no English one (or vice versa). This module
loads a small JSON file of hand-curated translations and folds them in,
without overwriting any gloss already on the entry.

The translations file is a flat ``{lemma: payload}`` map. ``payload`` may
be any of:

- a string — treated as a single English gloss
- a list of strings — treated as English glosses
- an object ``{"en": ["..."], "jp": ["..."]}`` — both gloss fields
  (also accepts the older ``glosses_en`` / ``glosses_jp`` keys)

The lemma key is matched against ``entry.lemma`` exactly. We touch only
entries that lack that side of the translation; entries that already have
a gloss are left alone.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from morpheme_db.schema import Entry


def load_translations(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize(payload: Any) -> tuple[list[str], list[str]]:
    if isinstance(payload, str):
        return ([payload], [])
    if isinstance(payload, list):
        return ([str(x) for x in payload if x], [])
    if isinstance(payload, dict):
        en = payload.get("en") or payload.get("glosses_en") or []
        jp = payload.get("jp") or payload.get("glosses_jp") or []
        if isinstance(en, str):
            en = [en]
        if isinstance(jp, str):
            jp = [jp]
        return ([str(x) for x in en if x], [str(x) for x in jp if x])
    return ([], [])


def apply_translations(
    entries: list[Entry], translations: dict[str, Any]
) -> dict[str, int]:
    counters = {"en_added": 0, "jp_added": 0, "lemmas_not_found": 0}
    by_lemma: dict[str, list[Entry]] = {}
    for entry in entries:
        by_lemma.setdefault(entry.lemma, []).append(entry)

    for lemma, payload in translations.items():
        if lemma.startswith("_"):  # reserved for in-file metadata
            continue
        matches = by_lemma.get(lemma)
        if not matches:
            counters["lemmas_not_found"] += 1
            continue
        en, jp = _normalize(payload)
        for entry in matches:
            if en and not entry.glosses_en:
                entry.glosses_en = list(en)
                counters["en_added"] += 1
            if jp and not entry.glosses_jp:
                entry.glosses_jp = list(jp)
                counters["jp_added"] += 1
    return counters


__all__ = ["apply_translations", "load_translations"]
