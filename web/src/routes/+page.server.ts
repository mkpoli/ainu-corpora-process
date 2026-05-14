import { loadDatabase } from '$lib/server/database';
import { compose, findOtherUses } from '$lib/composition';
import type { CompositionResult, Entry } from '$lib/types';
import type { PageServerLoad } from './$types';

interface SuggestionsBuckets {
	morphemes: Entry[];
	compounds: Entry[];
}

const DEFAULT_EXAMPLE = 'e-yay-ko-si-ram-suy-pa';

export const load: PageServerLoad = async ({ url }) => {
	const db = await loadDatabase();
	// If no explicit query is supplied, fall back to the paper's signature
	// polysynthetic example so the empty state actually showcases the tree.
	const explicitQ = url.searchParams.get('q')?.trim() ?? '';
	const q = explicitQ || DEFAULT_EXAMPLE;
	const isDefault = !explicitQ;

	const composition: CompositionResult | null = q
		? compose(q, { byKey: db.byKey, segmentationKeys: db.segmentationKeys })
		: null;

	const detailEntries: Entry[] = [];
	const otherUses: Record<string, Entry[]> = {};
	if (composition) {
		const visited = new Set<string>();
		const collect = (entry: Entry | null | undefined) => {
			if (!entry) return;
			if (visited.has(entry.id)) return;
			visited.add(entry.id);
			detailEntries.push(entry);
			otherUses[entry.id] = findOtherUses(entry, db.entries, 8);
		};
		const walk = (
			node: typeof composition.tree | undefined,
			seen: Set<typeof composition.tree>
		) => {
			if (!node || seen.has(node)) return;
			seen.add(node);
			collect(node.entry);
			walk(node.affix as typeof composition.tree | undefined, seen);
			walk(node.body as typeof composition.tree | undefined, seen);
		};
		walk(composition.tree, new Set());
	}

	const sample = pickSamples(db.entries);

	const suggestions: SuggestionsBuckets = {
		morphemes: db.entries
			.filter((e) => e.verified || e.base_frame !== null || e.rules.length)
			.sort((a, b) => b.frequency - a.frequency)
			.slice(0, 30),
		compounds: db.entries
			.filter((e) => e.lemma.includes('-') && e.frequency >= 1)
			.slice(0, 12)
	};

	return {
		query: explicitQ,
		resolvedQuery: q,
		isDefault,
		composition,
		detailEntries,
		otherUses,
		suggestions,
		sample,
		stats: {
			total: db.entries.length,
			verified: db.entries.filter((e) => e.verified).length,
			withFrame: db.entries.filter((e) => e.base_frame).length,
			withCategory: db.entries.filter((e) => e.category).length
		}
	};
};

function pickSamples(entries: Entry[]): string[] {
	// Curated demo queries that showcase the tree, with the paper's
	// signature polysynthetic example up front.
	const demos = [
		'e-yay-ko-si-ram-suy-pa',
		'si-nukar-e',
		'yay-ko-nukar',
		'nukar-e',
		'yay-nukar',
		'i-nukar',
		'nukar-yar',
		'cep koyki',
		'nukar'
	];
	// Drop any that don't resolve in the current DB to anything.
	const byKey = new Set<string>();
	for (const e of entries) {
		byKey.add(e.lemma);
		for (const v of e.allomorphs) byKey.add(v);
		byKey.add(e.lemma.replace(/^[-=]+|[-=]+$/g, ''));
	}
	return demos.filter((d) =>
		d
			.split(/[\s-]+/)
			.filter(Boolean)
			.some((tok) => byKey.has(tok) || byKey.has(tok.replace(/^[-=]+|[-=]+$/g, '')))
	);
}
