import type { Lexeme } from '$lib/types';
import bundled from '$lib/data/lexemes.json';

export interface LexemeBank {
	lexemes: Lexeme[];
	byId: Map<string, Lexeme>;
}

interface D1PreparedStatement {
	all<T = unknown>(): Promise<{ results: T[] }>;
}

interface D1Database {
	prepare(query: string): D1PreparedStatement;
}

interface AppPlatform {
	env?: { DB?: D1Database };
}

// JSON-encoded columns in the D1 `lexemes` table (see
// lexeme_db/export_sqlite.py); everything else is a scalar.
const ARRAY_FIELDS = [
	'gloss_jp',
	'gloss_en',
	'morphemes',
	'senses',
	'sources',
	'attestations',
	'dialects'
] as const;

function rowToLexeme(row: Record<string, unknown>): Lexeme {
	const parseJson = <T>(value: unknown, fallback: T): T => {
		if (value == null || value === '') return fallback;
		if (typeof value !== 'string') return value as T;
		try {
			return JSON.parse(value) as T;
		} catch {
			return fallback;
		}
	};
	const lx: Record<string, unknown> = { ...row };
	for (const field of ARRAY_FIELDS) {
		lx[field] = parseJson(row[field], []);
	}
	lx.bound = !!row.bound;
	lx.recordings = Number(row.recordings ?? 0);
	lx.notes = (row.notes as string | null) ?? '';
	lx.kana = (row.kana as string | null) ?? '';
	lx.pos = (row.pos as string | null) ?? '';
	lx.dialect_base = (row.dialect_base as string | null) ?? '';
	return lx as unknown as Lexeme;
}

// Cache per Worker instance / dev-server boot, keyed by source — same
// strategy as server/database.ts (the live D1 binding is the version key).
let cache: LexemeBank | null = null;
let cacheSource: string | null = null;

export async function loadLexemes(platform?: AppPlatform): Promise<LexemeBank> {
	const db = platform?.env?.DB;
	const source = db ? 'd1' : 'bundled-json';

	if (cache && cacheSource === source) return cache;

	let lexemes: Lexeme[];
	if (db) {
		try {
			const result = await db.prepare('SELECT * FROM lexemes').all<Record<string, unknown>>();
			lexemes = result.results.map(rowToLexeme);
		} catch (err) {
			// The `lexemes` table only lands once `publish:d1` has been re-run
			// since the lexeme bank was added. Until then (and on any transient
			// D1 error) fall back to the bundled snapshot so the page renders
			// instead of 500-ing. Cached under the d1 key so we retry at most
			// once per Worker instance.
			console.warn(
				'[lexemes] D1 query failed, falling back to bundled JSON:',
				(err as Error)?.message ?? err
			);
			lexemes = bundled as unknown as Lexeme[];
		}
	} else {
		lexemes = bundled as unknown as Lexeme[];
	}

	const byId = new Map<string, Lexeme>();
	for (const lx of lexemes) byId.set(lx.id, lx);
	cache = { lexemes, byId };
	cacheSource = source;
	return cache;
}

/**
 * Cheap lexeme count for headline stats — a D1 `COUNT(*)` (or the bundled
 * length) so the homepage doesn't pull the whole 10 MB bank just to show a
 * number. Falls back to the bundled snapshot if the table isn't there yet.
 */
export async function countLexemes(platform?: AppPlatform): Promise<number> {
	const db = platform?.env?.DB;
	if (db) {
		try {
			const r = await db
				.prepare('SELECT count(*) AS n FROM lexemes')
				.all<{ n: number }>();
			return Number(r.results?.[0]?.n ?? 0);
		} catch {
			return (bundled as unknown[]).length;
		}
	}
	return (bundled as unknown[]).length;
}
