import type { Entry } from '$lib/types';
import bundled from '$lib/data/morpheme_database.json';

interface DatabaseSnapshot {
	entries: Entry[];
	byKey: Map<string, Entry>;
	byId: Map<string, Entry>;
	segmentationKeys: string[];
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

function buildIndex(entries: Entry[]): {
	byKey: Map<string, Entry>;
	byId: Map<string, Entry>;
	segmentationKeys: string[];
} {
	const byKey = new Map<string, Entry>();
	const byId = new Map<string, Entry>();
	const segmentationSet = new Set<string>();

	const sorted = [...entries].sort((a, b) => {
		if (a.verified !== b.verified) return a.verified ? -1 : 1;
		return b.frequency - a.frequency;
	});

	for (const entry of sorted) {
		byId.set(entry.id, entry);
		const keys = new Set<string>([entry.lemma, ...entry.allomorphs]);
		const bare = entry.lemma.replace(/^[-=]+|[-=]+$/g, '');
		if (bare) keys.add(bare);
		for (const key of keys) {
			if (!key) continue;
			if (!byKey.has(key)) byKey.set(key, entry);
			const stripped = key.replace(/^[-=]+|[-=]+$/g, '');
			if (stripped.length >= 1) segmentationSet.add(stripped);
		}
	}

	const segmentationKeys = [...segmentationSet].sort(
		(a, b) => b.length - a.length || a.localeCompare(b)
	);
	return { byKey, byId, segmentationKeys };
}

const ARRAY_FIELDS = [
	'allomorphs',
	'category_alt',
	'rules',
	'attaches_to',
	'selection',
	'glosses_en',
	'glosses_jp',
	'dialects',
	'sources',
	'composition'
] as const;

function rowToEntry(row: Record<string, unknown>): Entry {
	const parseJson = <T>(value: unknown, fallback: T): T => {
		if (value == null || value === '') return fallback;
		if (typeof value !== 'string') return value as T;
		try {
			return JSON.parse(value) as T;
		} catch {
			return fallback;
		}
	};
	const entry: Record<string, unknown> = { ...row };
	for (const field of ARRAY_FIELDS) {
		entry[field] = parseJson(row[field], []);
	}
	entry.base_frame = parseJson(row.base_frame, null);
	entry.bound = !!row.bound;
	entry.verified = !!row.verified;
	entry.frequency = Number(row.frequency ?? 0);
	entry.notes = (row.notes as string | null) ?? '';
	entry.composition_note = (row.composition_note as string | null) ?? '';
	entry.morph_type = (row.morph_type as string | null) ?? 'root';
	entry.category = (row.category as string | null) ?? '';
	return entry as unknown as Entry;
}

// Cache the snapshot per Worker instance / dev-server boot. We invalidate
// purely on cold-start; pushing a new D1 database (different binding) is the
// publish event, so the binding itself acts as the version key.
let cache: DatabaseSnapshot | null = null;
let cacheSource: string | null = null;

export async function loadDatabase(platform?: AppPlatform): Promise<DatabaseSnapshot> {
	const db = platform?.env?.DB;
	const source = db ? 'd1' : 'bundled-json';

	if (cache && cacheSource === source) return cache;

	let entries: Entry[];
	if (db) {
		const result = await db.prepare('SELECT * FROM entries').all<Record<string, unknown>>();
		entries = result.results.map(rowToEntry);
	} else {
		entries = bundled as Entry[];
	}

	const { byKey, byId, segmentationKeys } = buildIndex(entries);
	cache = { entries, byKey, byId, segmentationKeys };
	cacheSource = source;
	return cache;
}

export type { DatabaseSnapshot };
