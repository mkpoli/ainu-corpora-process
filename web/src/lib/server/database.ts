import type { Entry } from '$lib/types';
import bundled from '$lib/data/morpheme_database.json';

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

// Built once per worker / dev-server boot. The JSON is statically imported so
// it lives inside the bundle — important for Cloudflare Workers, which has no
// filesystem at runtime.
let cache: DatabaseSnapshot | null = null;

export async function loadDatabase(): Promise<DatabaseSnapshot> {
	if (cache) return cache;
	const entries = bundled as Entry[];
	const { byKey, byId, segmentationKeys } = buildIndex(entries);
	cache = { entries, byKey, byId, segmentationKeys };
	return cache;
}

export type { DatabaseSnapshot };
