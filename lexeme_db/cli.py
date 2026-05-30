"""Command line for the lexeme bank.

    uv run python -m lexeme_db.cli build
    uv run python -m lexeme_db.cli pivot sapa      # all dialects' recordings
    uv run python -m lexeme_db.cli pivot --id sapa.n
    uv run python -m lexeme_db.cli stats
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from lexeme_db.build import main as build_main
from lexeme_db.normalize import form_key
from lexeme_db.schema import load_lexemes

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
LEXEME_BANK = OUTPUT_DIR / "lexeme_bank.json"
CROSSWALK = OUTPUT_DIR / "crosswalk.tsv"


def _load_crosswalk() -> list[dict[str, str]]:
    with CROSSWALK.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def cmd_pivot(args: argparse.Namespace) -> int:
    """Show one lexeme and every dictionary's recording of it, by dialect."""
    lexemes = {lx.id: lx for lx in load_lexemes(LEXEME_BANK)}
    rows = _load_crosswalk()

    if args.id:
        targets = [args.id] if args.id in lexemes else []
    else:
        key = form_key(args.query)
        targets = [lid for lid in lexemes if lid == key or lid.startswith(key + ".")]
        if not targets:
            targets = [
                lid for lid, lx in lexemes.items() if form_key(lx.lemma) == key
            ]
    if not targets:
        print(f"No lexeme found for {args.id or args.query!r}.")
        return 1

    by_lex: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        by_lex[r["lexeme_id"]].append(r)

    for lid in targets:
        lx = lexemes[lid]
        morph = f"  morphemes: {' + '.join(lx.morphemes)}" if lx.morphemes else ""
        gloss = "；".join(lx.gloss_jp[:3])
        print(
            f"\n=== {lx.id}  「{lx.lemma}」 {lx.kana}  [{lx.pos or '?'}]"
            f"{'  (bound)' if lx.bound else ''} ==="
        )
        if gloss:
            print(f"  gloss: {gloss}")
        if lx.senses:
            for s in lx.senses:
                print(f"   ⟨{s.id}⟩ {'；'.join(s.gloss_jp)}")
        if morph:
            print(morph)
        print(f"  recordings ({len(by_lex.get(lid, []))}):")
        for r in sorted(by_lex.get(lid, []), key=lambda x: (x["dialect"], x["source"])):
            tag = f"[{r['match_kind']}]"
            print(
                f"    {r['dialect']:<4} {r['surface_latn']:<16} "
                f"{r['surface_kana']:<10} {tag:<12} {r['source']}"
            )
    return 0


def cmd_stats(_args: argparse.Namespace) -> int:
    lexemes = load_lexemes(LEXEME_BANK)
    rows = _load_crosswalk()
    by_dialect_pairs: dict[str, int] = defaultdict(int)
    dia_by_lex: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        dia_by_lex[r["lexeme_id"]].add(r["dialect"])
    multi = sum(1 for s in dia_by_lex.values() if len(s) > 1)
    for s in dia_by_lex.values():
        if len(s) > 1:
            by_dialect_pairs["+".join(sorted(s))] += 1
    print(f"lexemes        : {len(lexemes)}")
    print(f"attestations   : {len(rows)}")
    print(f"multi-dialect  : {multi}")
    print(f"sense-split    : {sum(1 for lx in lexemes if lx.senses)}")
    print(f"morpheme-linked: {sum(1 for lx in lexemes if lx.morphemes)}")
    print("dialect overlaps:")
    for combo, n in sorted(by_dialect_pairs.items(), key=lambda x: -x[1]):
        print(f"  {combo}: {n}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ainu lexeme bank.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("build", help="(Re)build the lexeme bank + crosswalk.")

    p_pivot = sub.add_parser("pivot", help="Show a lexeme across all dialects.")
    p_pivot.add_argument("query", nargs="?", default="", help="Citation form, e.g. sapa.")
    p_pivot.add_argument("--id", default="", help="Exact lexeme id, e.g. sapa.n.")

    sub.add_parser("stats", help="Summary statistics.")

    args = parser.parse_args(argv)
    if args.cmd == "build":
        return build_main()
    if args.cmd == "pivot":
        return cmd_pivot(args)
    if args.cmd == "stats":
        return cmd_stats(args)
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
