import { existsSync, mkdirSync, copyFileSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
// web/scripts -> web -> ainu-corpora-process (the Python pipeline repo root).
const repoRoot = resolve(__dirname, '..', '..');

// Source artifacts produced by the Python pipeline.
const MORPHEME_SRC = join(repoRoot, 'morpheme_db', 'output', 'morpheme_database.json');
const REFERENCES_SRC = join(repoRoot, 'morpheme_db', 'output', 'references.json');

// Lexeme bank (语彙素 layer) + the dictionary crosswalk. We join them here into
// a single web-friendly file so the viewer can pivot a lexeme out to every
// dictionary's recording of it without parsing the TSV at runtime.
const LEXEME_SRC = join(repoRoot, 'lexeme_db', 'output', 'lexeme_bank.json');
const CROSSWALK_SRC = join(repoRoot, 'lexeme_db', 'output', 'crosswalk.tsv');

// Destinations inside the web app's bundled data dir.
const DATA_DIR = join(__dirname, '..', 'src', 'lib', 'data');
const MORPHEME_DEST = join(DATA_DIR, 'morpheme_database.json');
const REFERENCES_DEST = join(DATA_DIR, 'references.json');
const LEXEME_DEST = join(DATA_DIR, 'lexemes.json');

// Cap the per-attestation gloss carried into the bundle. The crosswalk keeps
// each source's full definition (megabytes); for the viewer a short preview is
// enough and keeps the Worker bundle small.
const GLOSS_PREVIEW_CHARS = 160;

if (!existsSync(DATA_DIR)) mkdirSync(DATA_DIR, { recursive: true });

function syncFile(src, dest, label, placeholder = '[]\n') {
	if (!existsSync(src)) {
		if (existsSync(dest)) {
			console.warn(`[sync-database] WARN: ${label} source missing; keeping existing copy.`);
		} else {
			// Fresh CI checkout: the Python outputs are gitignored under
			// **/output/, so the source isn't there. Drop an empty placeholder
			// so `import … from '$lib/data/…'` resolves at type-check/build time.
			// Never clobbers a real copy; runtime prefers D1 (server/database.ts).
			writeFileSync(dest, placeholder, 'utf-8');
			console.warn(`[sync-database] WARN: ${label} source missing; wrote empty placeholder.`);
		}
		return;
	}
	copyFileSync(src, dest);
	console.log(`[sync-database] copied ${label}`);
}

function parseCrosswalk(tsv) {
	const lines = tsv.split('\n');
	const header = lines[0].split('\t');
	const idx = Object.fromEntries(header.map((h, i) => [h, i]));
	const byLexeme = new Map();
	for (let i = 1; i < lines.length; i++) {
		const line = lines[i];
		if (!line) continue;
		const f = line.split('\t');
		const lexemeId = f[idx.lexeme_id];
		if (!lexemeId) continue;
		const gloss = (f[idx.gloss_raw] ?? '').slice(0, GLOSS_PREVIEW_CHARS);
		const att = {
			source: f[idx.source] ?? '',
			dialect: f[idx.dialect] ?? '',
			entry_ref: f[idx.entry_ref] ?? '',
			surface_latn: f[idx.surface_latn] ?? '',
			surface_kana: f[idx.surface_kana] ?? '',
			pos_raw: f[idx.pos_raw] ?? '',
			sense_id: f[idx.sense_id] ?? '',
			match_kind: f[idx.match_kind] ?? '',
			confidence: Number(f[idx.confidence] ?? '0'),
			gloss
		};
		if (!byLexeme.has(lexemeId)) byLexeme.set(lexemeId, []);
		byLexeme.get(lexemeId).push(att);
	}
	return byLexeme;
}

function syncLexemes() {
	if (!existsSync(LEXEME_SRC)) {
		if (!existsSync(LEXEME_DEST)) writeFileSync(LEXEME_DEST, '[]\n', 'utf-8');
		console.warn(
			`[sync-database] WARN: lexeme_bank.json not found at ${LEXEME_SRC}; ` +
				`wrote/kept lexemes.json placeholder (run: uv run python -m lexeme_db.cli build).`
		);
		return;
	}
	const lexemes = JSON.parse(readFileSync(LEXEME_SRC, 'utf-8'));
	const byLexeme = existsSync(CROSSWALK_SRC)
		? parseCrosswalk(readFileSync(CROSSWALK_SRC, 'utf-8'))
		: new Map();
	if (!existsSync(CROSSWALK_SRC)) {
		console.warn('[sync-database] WARN: crosswalk.tsv not found; lexemes will have no recordings.');
	}

	const out = lexemes.map((lx) => {
		const attestations = byLexeme.get(lx.id) ?? [];
		const dialects = [...new Set(attestations.map((a) => a.dialect).filter(Boolean))].sort();
		return { ...lx, attestations, dialects, recordings: attestations.length };
	});

	writeFileSync(LEXEME_DEST, JSON.stringify(out), 'utf-8');
	const multiDialect = out.filter((l) => l.dialects.length > 1).length;
	console.log(
		`[sync-database] built lexemes.json (${out.length} lexemes, ` +
			`${out.reduce((n, l) => n + l.recordings, 0)} recordings, ${multiDialect} multi-dialect)`
	);
}

syncFile(MORPHEME_SRC, MORPHEME_DEST, 'morpheme_database.json');
syncFile(REFERENCES_SRC, REFERENCES_DEST, 'references.json');
syncLexemes();
