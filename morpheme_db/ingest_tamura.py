"""Ingest Tamura 1996 part-of-speech and boundness markers.

``dictionary/output/ainu-archive/tamura-entries.txt`` is a TSV from
Tamura Suzuko's 沙流方言辞典 (Saru dialect dictionary, 1996). Each line is

    lemma\\tkana 【tag】definition [examples] ...

with the POS tag in fullwidth brackets. Tamura's tags carry both a
grammatical category and (for ``接頭``/``接尾``/``人接``/``位名``/``形名``/
``名詞語根``/``自動語幹``/``他動語幹``) an explicit boundness signal that
the morpheme database doesn't otherwise pick up.

This ingest:

1. Reads every Tamura row, extracts the tag and (where possible) a short
   gloss from the definition column (the text up to the first
   sentence-final ``｡``/``。`` or example marker).
2. Maps the tag to the XPOS inventory + a bound flag.
3. For lemmas already present in the database, enriches empty fields:
   sets ``category`` when blank, flips ``bound`` when Tamura says so,
   upgrades ``morph_type`` when the tag is structural (``prefix``/
   ``suffix``/``clitic``), and adds Tamura as a source.
4. Curated entries (``verified=True``) are not overwritten — Tamura is
   just confirmed as a source when its category agrees.
5. Tamura lemmas not in the database become new ``tamura1996:<lemma>``
   entries, bound=True for the explicitly-bound tags.
"""

from __future__ import annotations

import re
from pathlib import Path

from morpheme_db.schema import Entry


# Maps Tamura's POS tag (without the 【】 wrappers) to (xpos, bound, morph_type).
# ``morph_type`` is set to a non-empty value only when the tag is itself a
# structural class (prefix / suffix / clitic-like); for everything else the
# ingest leaves the entry's existing ``morph_type`` alone.
TAMURA_TAGS: dict[str, tuple[str, bool, str]] = {
    "名": ("n", False, ""),
    "自動": ("vi", False, ""),
    "他動": ("vt", False, ""),
    "副": ("adv", False, ""),
    "位名": ("nl", True, "root"),
    "複他動": ("vd", False, ""),
    "間投": ("intj", False, ""),
    "連他動": ("vd", False, ""),
    "完動": ("vc", False, ""),
    "連体": ("adn", True, "root"),
    "後副": ("padv", False, ""),
    "接尾": ("sfx", True, "suffix"),
    "接頭": ("pfx", True, "prefix"),
    "名詞語根": ("n", True, "root"),
    "接助": ("sconj", False, ""),
    "副助": ("advp", False, ""),
    "助動": ("auxv", False, ""),
    "形名": ("nmlz", True, "root"),
    "人接": ("pers", True, "clitic"),
    "自動語幹": ("vi", True, "root"),
    "他動語幹": ("vt", True, "root"),
    "代名": ("pron", False, ""),
    "終助": ("sfp", False, ""),
    "接": ("cconj", False, ""),
    "格助": ("postp", False, ""),
}

_TAG_RE = re.compile(r"【([^】]+)】")
# The definition column starts with the kana spelling, then 【tag】, then
# the gloss. We grab the bit between the first 】 and the first sentence
# terminator (｡, 。, ｟, ☆, ☞, or example markers like a Latin word followed
# by a kana cluster). Keeping the gloss short keeps the JSON tidy.
_GLOSS_TRIM_RE = re.compile(r"[｡。｟☆☞]|(?:\s[a-zA-Z][a-zA-Z\-=]+\s)")


# Cross-reference / pointer fragments that Tamura uses to direct readers
# to a related entry (e.g. "(複は…", "(単は…", "(概は…", "(=…", "→…").
# When the gloss starts with one of these it's not a real definition;
# we strip the fragment and continue, or fall through to empty if nothing
# else remains.
_GLOSS_POINTER_RE = re.compile(
    r"^[\s　]*(?:[\[（(]\s*(?:複|単|概|所|=|＝|→|☞|cf\.?|参照)[^\)\]）]*[\)\]）][\s　]*)+",
    re.IGNORECASE,
)


def _parse_gloss(definition: str, tag_end_index: int) -> str:
    tail = definition[tag_end_index:]

    # Iteratively peel off the noise prefixes Tamura puts in front of
    # the actual gloss. Run BEFORE cutting at the sentence terminator
    # because pointer fragments like ``(複は respa レㇱパ)`` contain
    # Latin words that would otherwise look like an example marker
    # mid-paren and end the cut too early.
    for _ in range(8):
        original = tail
        # Strip leading whitespace / orphan punctuation including the
        # close-brackets left by a previous paren match.
        tail = re.sub(
            r"^[\s　、,;:\]\)）①②③④⑤⑥⑦⑧⑨⑩]+",
            "",
            tail,
        )
        # Drop leading pointer / cross-reference fragments.
        tail = _GLOSS_POINTER_RE.sub("", tail)
        # Drop a single leading parenthesised meta-note, allowing one
        # level of nested parens inside (e.g. ``(複は respa(レㇱパ))``).
        paren_match = re.match(
            r"^[\[\(（](?:[^\[\(（\]\)）]|[\[\(（][^\]\)）]*[\]\)）])*[\]\)）]",
            tail,
        )
        if paren_match:
            tail = tail[paren_match.end():]
        if tail == original:
            break

    # Now cut at the first sentence terminator / example marker.
    m = _GLOSS_TRIM_RE.search(tail)
    if m:
        tail = tail[: m.start()]

    # Final trim of trailing punctuation residue.
    cleaned = tail.strip().rstrip("、,;:")

    # Sanity: drop results that are obviously not a gloss. Patterns that
    # the cleanup has trouble with cleanly:
    #   - purely ASCII (left with just an example marker like ``usa``)
    #   - the leading token is a Latin word followed by kana, which means
    #     the parser cut at the Latin example before reaching the real
    #     definition (e.g. ``-rototke``)
    #   - the result is too short to carry meaning
    if not cleaned:
        return ""
    if all(ord(c) < 128 for c in cleaned):
        return ""
    if len(cleaned) < 2:
        return ""
    if re.match(r"^[a-zA-Z]", cleaned):
        return ""
    return cleaned


def parse_tamura_entries(path: Path) -> list[dict[str, str]]:
    """Return a list of ``{lemma, tag, xpos, bound, morph_type, gloss_jp}``."""
    out: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as handle:
        next(handle, None)  # header
        for raw in handle:
            if "\t" not in raw:
                continue
            lemma, definition = raw.split("\t", 1)
            lemma = lemma.strip()
            if not lemma:
                continue
            tag_match = _TAG_RE.search(definition)
            if not tag_match:
                continue
            tag = tag_match.group(1).strip()
            mapping = TAMURA_TAGS.get(tag)
            if mapping is None:
                continue
            xpos, bound, morph_type = mapping
            gloss = _parse_gloss(definition, tag_match.end())
            out.append(
                {
                    "lemma": lemma,
                    "tag": tag,
                    "xpos": xpos,
                    "bound": bound,
                    "morph_type": morph_type,
                    "gloss_jp": gloss,
                }
            )
    return out


def enrich_with_tamura(entries: list[Entry], rows: list[dict[str, str]]) -> dict[str, int]:
    """Fold Tamura POS rows into ``entries``.

    Strategy mirrors the FF Ainu Saru ingest:
    - Existing entries get their ``category`` set when blank, ``bound``
      flipped when Tamura says so, ``morph_type`` upgraded when the tag is
      structural, and Tamura added as a source.
    - Curated entries keep their category/bound/morph_type but Tamura is
      still recorded as a source when the tags agree.
    - Tamura headwords not in the database become new ``tamura1996:<lemma>``
      entries.

    Returns counters describing what changed so the build summary can
    surface it.
    """
    counters = {
        "categories_set": 0,
        "categories_alt": 0,
        "bound_flipped": 0,
        "morph_type_upgraded": 0,
        "new_entries": 0,
        "glosses_added": 0,
    }

    # Build a lookup over every existing surface form.
    index: dict[str, Entry] = {}
    for entry in entries:
        forms = {entry.lemma, *entry.allomorphs}
        bare = entry.lemma.strip("-=")
        if bare:
            forms.add(bare)
        for form in forms:
            if form:
                index.setdefault(form, entry)

    source_label = "田村1996アイヌ語沙流方言辞典"

    for row in rows:
        lemma = row["lemma"]
        xpos = row["xpos"]
        is_bound = row["bound"]
        morph_type = row["morph_type"]
        gloss = row["gloss_jp"]

        # Bound forms (those carrying an attachment marker in Tamura's
        # headword) must match exactly — falling back to the bare-form
        # lookup would wrongly enrich the free-standing homophone (e.g.
        # the bound suffix ``-a`` would end up enriching the free ``a``
        # entry, and the bound entry would never be created).
        is_bound_lemma = lemma.startswith(("-", "=")) or lemma.endswith(("-", "="))
        if is_bound_lemma:
            existing = index.get(lemma)
        else:
            existing = index.get(lemma) or index.get(lemma.strip("-="))
        if existing is not None:
            changed = False
            if not existing.verified:
                if not existing.category:
                    existing.category = xpos
                    counters["categories_set"] += 1
                    changed = True
                elif existing.category != xpos and xpos not in existing.category_alt:
                    existing.category_alt.append(xpos)
                    counters["categories_alt"] += 1
                    changed = True
                if is_bound and not existing.bound:
                    existing.bound = True
                    counters["bound_flipped"] += 1
                    changed = True
                if morph_type and existing.morph_type == "root" and morph_type != "root":
                    existing.morph_type = morph_type
                    counters["morph_type_upgraded"] += 1
                    changed = True
            if gloss and not existing.glosses_jp:
                existing.glosses_jp = [gloss]
                counters["glosses_added"] += 1
                changed = True
            if changed and source_label not in existing.sources:
                existing.sources.append(source_label)
            continue

        new_entry = Entry(
            id=f"tamura1996:{lemma}",
            lemma=lemma,
            category=xpos,
            bound=is_bound,
            morph_type=morph_type or "root",
            glosses_jp=[gloss] if gloss else [],
            sources=[source_label],
            verified=False,
        )
        entries.append(new_entry)
        index[lemma] = new_entry
        bare = lemma.strip("-=")
        if bare and bare not in index:
            index[bare] = new_entry
        counters["new_entries"] += 1
        if gloss:
            counters["glosses_added"] += 1

    return counters


__all__ = ["TAMURA_TAGS", "enrich_with_tamura", "parse_tamura_entries"]
