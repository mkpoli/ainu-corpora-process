import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import type { Entry } from '$lib/types';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATABASE_PATH = path.resolve(__dirname, '../../../../morpheme_db/output/morpheme_database.json');
const SEED_FALLBACK_PATH = path.resolve(__dirname, '../../../../morpheme_db/seed/morphemes.json');

interface DatabaseSnapshot {
	entries: Entry[];
	// Lookup map: surface form → entry. Includes lemma + allomorphs, with
	// verified entries indexed first so they win ties.
	byKey: Map<string, Entry>;
	// Lookup by stable entry id — used for `composition` references.
	byId: Map<string, Entry>;
	// Morphemes sorted by descending length for greedy segmentation. We keep
	// only the surface keys that can appear inside a longer compound — i.e.
	// the lemma stripped of attachment markers, plus markered variants when
	// they're meaningfully distinct.
	segmentationKeys: string[];
	// File timestamp, so callers can decide to refresh.
	mtimeMs: number;
}

let cache: DatabaseSnapshot | null = null;
let cachedSource: string | null = null;

async function readJson(filePath: string): Promise<Entry[]> {
	const raw = await fs.readFile(filePath, 'utf-8');
	return JSON.parse(raw) as Entry[];
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
			// For greedy segmentation we want the bare form (no attachment
			// markers), because that's what appears inside compounds.
			const stripped = key.replace(/^[-=]+|[-=]+$/g, '');
			if (stripped.length >= 1) segmentationSet.add(stripped);
		}
	}

	const segmentationKeys = [...segmentationSet].sort((a, b) => b.length - a.length || a.localeCompare(b));
	return { byKey, byId, segmentationKeys };
}

export async function loadDatabase(): Promise<DatabaseSnapshot> {
	let source = DATABASE_PATH;
	let stat;
	try {
		stat = await fs.stat(DATABASE_PATH);
	} catch {
		stat = null;
	}
	if (!stat) {
		source = SEED_FALLBACK_PATH;
		stat = await fs.stat(source);
	}

	if (cache && cachedSource === source && cache.mtimeMs === stat.mtimeMs) {
		return cache;
	}

	const entries = await readJson(source);
	const { byKey, byId, segmentationKeys } = buildIndex(entries);
	cache = { entries, byKey, byId, segmentationKeys, mtimeMs: stat.mtimeMs };
	cachedSource = source;
	return cache;
}

export type { DatabaseSnapshot };
