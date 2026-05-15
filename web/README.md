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

## Routes

- `/` — interactive composition explorer (search box + bracketed tree
  + detail panel for the selected morpheme).
- `/morphemes` — sortable / filterable table of every entry in the
  database. Useful for browsing the inventory without driving the
  composition engine.
- `/references` — bibliography of dictionaries, corpora, and papers
  cited by the morpheme database. Source chips on the home and table
  routes link to anchors on this page.

## Deploying to Cloudflare Workers

The app builds with `@sveltejs/adapter-cloudflare` and deploys as a single
Worker. The custom domain `mdb.aynu.org` is configured in
`wrangler.jsonc`; `workers_dev = false` so the `*.workers.dev` preview URL
is disabled.

```sh
# one-time auth
bunx wrangler login

# build + deploy
bun run deploy
```

### Data: bundled JSON (default) vs D1 (recommended for production)

Two data sources are supported by `src/lib/server/database.ts`:

1. **Bundled JSON** — `src/lib/data/morpheme_database.json` is imported
   statically and bundled into the Worker. The
   `predev` / `prebuild` hooks copy
   `../morpheme_db/output/morpheme_database.json` here automatically.
   This is what runs locally and is the fallback in production when no
   D1 binding is present. Re-run
   `uv run python -m morpheme_db.cli build` to refresh the data.

2. **Cloudflare D1** — if `platform.env.DB` is bound, the loader reads
   from the D1 `entries` table on cold start instead. To publish a new
   snapshot:

   ```sh
   bun run publish:d1     # creates a new ainu-mdb-<UTC-timestamp> db
                          # and imports the SQL dump from morpheme_db
   bun run deploy
   ```

   The `publish:d1` script (see `scripts/publish-d1.mjs`):

   - Re-runs `python -m morpheme_db.export_sqlite` to regenerate
     `morpheme_db/output/morpheme_database.sql`.
   - Mints a fresh D1 database `ainu-mdb-YYYYMMDD-HHMM` (UTC).
   - Imports the SQL dump via `wrangler d1 execute --remote --file=…`.
   - Rewrites the `d1_databases` block in `wrangler.jsonc` to point at
     the new database, leaving the previous one available as a
     rollback target.

   Every publish creates a new database rather than overwriting the
   previous one — following Cloudflare's import/export guidance
   ([docs](https://developers.cloudflare.com/d1/best-practices/import-export-data/)).
   The `d1_databases` block in `wrangler.jsonc` is commented out by
   default so a freshly cloned checkout works without D1 credentials;
   `publish:d1` activates and populates it on first run.

You can verify the bundle without uploading via `bunx wrangler deploy
--dry-run --outdir /tmp/wrangler-dry`.

### Deploying from GitHub Actions

`.github/workflows/deploy.yml` runs on two triggers:

1. **Push to `main`** — auto-deploys whenever changes land under
   `web/`, `morpheme_db/`, or the workflow itself. Other paths are
   ignored. The D1 re-publish step is skipped on push events, so the
   live database stays untouched and the Worker just gets a fresh
   build of the bundled JSON fallback.
2. **`workflow_dispatch`** (manual from the Actions tab) — same job,
   plus an optional `publish_d1: true` input that mints a fresh
   `ainu-mdb-<UTC-timestamp>` D1 database, imports the SQL dump,
   rewrites `wrangler.jsonc`, then deploys.

Both triggers share a concurrency group so overlapping deploys are
cancelled.

Required repository secrets:

- `CLOUDFLARE_API_TOKEN` — token with `Workers Scripts:Edit`,
  `User Details:Read`, and (for D1 re-publish) `D1:Edit`.
- `CLOUDFLARE_ACCOUNT_ID` — your account UUID.

## Stack

- SvelteKit 2 + Svelte 5 (runes) + `@sveltejs/adapter-cloudflare`
- Tailwind v4 (`@tailwindcss/vite`)
- `@inlang/paraglide-js` for i18n (en + ja)
- TypeScript strict mode
- Bun + Wrangler
