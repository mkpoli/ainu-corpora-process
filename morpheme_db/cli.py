"""Command-line entry point for the morpheme database.

Subcommands:

- ``build``    — assemble the unified database from seed + NINJAL.
- ``compute``  — given a hyphen- or space-separated morpheme sequence,
  print the effective valency frame after applying local rules.

Example::

    uv run python -m morpheme_db.cli build
    uv run python -m morpheme_db.cli compute si-nukar-e
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from morpheme_db.build import (
    NINJAL_LEXICON_PATH,
    OUTPUT_DIR,
    SEED_PATH,
    TOMMY_DECOMP_PATH,
    TOMMY_GLOSS_PATH,
    WIKT_COMPOSITIONS_PATH,
    WIKT_EN_GLOSS_PATH,
    WIKT_JA_GLOSS_PATH,
    WIKT_JA_POS_PATH,
    main as build_main,
)
from morpheme_db.schema import Entry, load_entries


def _split_sequence(text: str) -> list[str]:
    """Split a user-supplied morpheme sequence on ``-`` / whitespace.

    The split preserves attachment markers: leading ``-`` keeps the form as a
    suffix (``-e`` stays ``-e``) and trailing ``-`` keeps it as a prefix
    (``si-`` stays ``si-``). Bare tokens stay bare.
    """
    raw_tokens = [tok for tok in re.split(r"\s+", text.strip()) if tok]
    if not raw_tokens:
        return []
    if len(raw_tokens) > 1:
        return raw_tokens

    sole = raw_tokens[0]
    parts = sole.split("-")
    out: list[str] = []
    last_index = len(parts) - 1
    for i, part in enumerate(parts):
        if part == "":
            continue
        if i == 0 and last_index > 0 and parts[1] != "":
            # ``si-nukar-e`` → first non-empty part is the prefix ``si-``.
            out.append(part + "-")
        elif i == last_index and i > 0 and parts[i - 1] != "":
            out.append("-" + part)
        else:
            out.append(part)
    return out or [sole]


def _resolve(tokens: list[str], entries: list[Entry]) -> tuple[list[Entry], list[str]]:
    """Map tokens to entries by ``lemma`` / ``allomorphs``.

    Tokens may carry attachment markers (``yay-``, ``-e``) that aren't a
    perfect match for the stored lemma. Resolution tries, in order: exact
    match → bare form → as-suffix → as-prefix → as-clitic. This makes the
    CLI tolerant of common shorthand inputs like ``yay-ko-nukar`` where the
    naive hyphen-splitter can't tell whether ``ko`` is a prefix or a root.

    Returns ``(matched_entries, unresolved_tokens)``.
    """
    index: dict[str, Entry] = {}
    for entry in entries:
        index.setdefault(entry.lemma, entry)
        for variant in entry.allomorphs:
            index.setdefault(variant, entry)

    matched: list[Entry] = []
    unresolved: list[str] = []
    for token in tokens:
        bare = token.strip("-=")
        candidates = [
            token,
            bare,
            f"-{bare}",
            f"{bare}-",
            f"={bare}",
            f"{bare}=",
        ]
        entry = None
        for cand in candidates:
            if cand and cand in index:
                entry = index[cand]
                break
        if entry is None:
            unresolved.append(token)
        else:
            matched.append(entry)
    return matched, unresolved


def cmd_compute(args: argparse.Namespace) -> int:
    from morpheme_db.valency import compute_valency

    db_path = args.db
    if not db_path.exists():
        # Fall back to seed-only data so ``compute`` works without a prior build.
        entries = load_entries(SEED_PATH)
    else:
        entries = load_entries(db_path)

    tokens = _split_sequence(args.sequence)
    if not tokens:
        print("error: empty morpheme sequence", flush=True)
        return 2

    matched, unresolved = _resolve(tokens, entries)
    if unresolved:
        print(f"warning: could not resolve {unresolved}")
    if not matched:
        print("error: no recognised morphemes in input")
        return 2

    result = compute_valency(matched)
    print(result.describe())
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    return build_main(
        [
            "--seed",
            str(args.seed),
            "--ninjal",
            str(args.ninjal),
            "--wikt-ja",
            str(args.wikt_ja),
            "--wikt-en",
            str(args.wikt_en),
            "--wikt-ja-pos",
            str(args.wikt_ja_pos),
            "--wikt-compositions",
            str(args.wikt_compositions),
            "--tommy-decomp",
            str(args.tommy_decomp),
            "--tommy-gloss",
            str(args.tommy_gloss),
            "--output-dir",
            str(args.output_dir),
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="morpheme_db")
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="Build the unified morpheme database.")
    p_build.add_argument("--seed", type=Path, default=SEED_PATH)
    p_build.add_argument("--ninjal", type=Path, default=NINJAL_LEXICON_PATH)
    p_build.add_argument("--wikt-ja", type=Path, default=WIKT_JA_GLOSS_PATH)
    p_build.add_argument("--wikt-en", type=Path, default=WIKT_EN_GLOSS_PATH)
    p_build.add_argument("--wikt-ja-pos", type=Path, default=WIKT_JA_POS_PATH)
    p_build.add_argument(
        "--wikt-compositions", type=Path, default=WIKT_COMPOSITIONS_PATH
    )
    p_build.add_argument("--tommy-decomp", type=Path, default=TOMMY_DECOMP_PATH)
    p_build.add_argument("--tommy-gloss", type=Path, default=TOMMY_GLOSS_PATH)
    p_build.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    p_build.set_defaults(func=cmd_build)

    p_compute = sub.add_parser(
        "compute",
        help="Compute the effective valency of a hyphen-separated morpheme sequence.",
    )
    p_compute.add_argument("sequence", help="e.g. 'si-nukar-e' or 'cep koyki'")
    p_compute.add_argument(
        "--db",
        type=Path,
        default=OUTPUT_DIR / "morpheme_database.json",
        help="Path to a built morpheme database JSON. Falls back to the seed if absent.",
    )
    p_compute.set_defaults(func=cmd_compute)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
