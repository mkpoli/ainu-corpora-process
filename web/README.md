# Ainu Morpheme Explorer (web)

A SvelteKit UI for browsing the morpheme database produced by
`../morpheme_db`. Given an Ainu word, it shows the lexical entry (gloss,
category, valency), the bracketed composition tree, and the effective
valency frame at every level.

## Running

```sh
bun install
bun run dev          # http://localhost:5173
bun run check        # type-check
bun run build && bun run preview
```

The page reads `../morpheme_db/output/morpheme_database.json` at request
time (with a `mtime`-keyed cache). Rebuild it with
`uv run python -m morpheme_db.cli build` after editing the seed or
re-running NINJAL extraction.

## What the UI does

- **Search**: type a word (`si-nukar-e`, `yay-ko-nukar`, `cep koyki`). Words
  with internal dashes are split on `-`; whitespace tokens are kept as the
  user typed them. The home page surfaces curated demos.
- **Direct entry match**: if the input is a known lemma we use that entry
  directly. If the lemma itself decomposes into known morphemes, we also
  show the internal tree.
- **Fallback segmentation**: unknown words are greedy-longest-matched
  against the known morpheme inventory. Anything that can't be matched is
  reported as `Unrecognised segments`.
- **Composition tree**: built outward from the head — suffixes apply
  inside-out, then prefixes outside-in. So `si-nukar-e` renders as
  `si-(nukar-e)`, not `((si-nukar)-e)`. Every internal node shows the
  surface form and the effective valency at that bracket; every leaf is a
  clickable chip that reveals the morpheme detail panel.
- **Detail panel**: gloss(es), morph_type / category, base frame and
  local rules with realisation badges, allomorphs, attachment / category
  alternatives, notes, sources, frequency, and a compact "appears in"
  list of other database entries containing the morpheme.

## Architecture

- `src/lib/server/database.ts` — loads + caches the JSON DB; builds the
  lemma/allomorph lookup map and a length-sorted key list for greedy
  segmentation.
- `src/lib/composition.ts` — TypeScript port of `morpheme_db.valency`,
  with two extras: greedy whole-word segmentation and the hierarchical
  tree builder that mirrors `si-(nukar-e)` bracketing.
- `src/lib/types.ts` — the schema types, kept structurally identical to
  the Python `Entry` / `Slot` / `Rule` / `ValencyFrame`.
- `src/lib/CompositionTree.svelte` — recursive tree component. Internal
  nodes are non-clickable surface headers; leaves are clickable chips.
- `src/lib/MorphemeDetail.svelte` — side panel.
- `src/lib/ValencyFrame.svelte` — slot chips with realisation colour
  coding (external / incorporated / reflexive / indefinite / absorbed).
- `src/routes/+page.server.ts` — runs the composition on the server side
  so the very first paint already has the tree.

## Things to know / current limits

- Segmentation is naive greedy-longest. For words like
  `e-yay-ko-tuyma-si-ram-suy-pa` the segmenter may pick shorter homographs
  (`kot` over `ko`+`t…`) when the longer morpheme isn't in the database.
  A beam search with linguistic priors is left as future work — the
  segmenter exists primarily to give *something* useful for unknown
  compounds, not to compete with a full morphological analyser.
- Internal nodes have no "entry" — they describe a constituent built by
  the engine. Clicking them is a no-op by design; click a leaf instead.
- The page is server-rendered (load runs in `+page.server.ts`). Switching
  to client-only would lose Node FS access to the JSON.

## Deploying to Cloudflare Workers

The app builds with `@sveltejs/adapter-cloudflare` and deploys as a single
Worker with the bundled JSON as a static module — no runtime filesystem
access required. The custom domain `mdb.aynu.org` is configured in
`wrangler.jsonc`; `workers_dev = false` so the `*.workers.dev` preview URL
is disabled.

```sh
# one-time auth
bunx wrangler login

# build + deploy
bun run deploy
```

The `predev` / `prebuild` hooks copy
`../morpheme_db/output/morpheme_database.json` into
`src/lib/data/morpheme_database.json` so the latest data goes into the
Worker bundle. Re-run `uv run python -m morpheme_db.cli build` first if
you've edited the seed or the NINJAL extractor.

You can verify the bundle without uploading via `bunx wrangler deploy
--dry-run --outdir /tmp/wrangler-dry`.

## Stack

- SvelteKit 2 + Svelte 5 (runes) + `@sveltejs/adapter-cloudflare`
- Tailwind v4 (`@tailwindcss/vite`)
- `@inlang/paraglide-js` for i18n (en + ja)
- TypeScript strict mode
- Bun + Wrangler
