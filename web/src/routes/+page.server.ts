import { loadDatabase } from '$lib/server/database';
import { compose, findOtherUses } from '$lib/composition';
import type { CompositionResult, Entry } from '$lib/types';
import type { PageServerLoad } from './$types';

interface SuggestionsBuckets {
	morphemes: Entry[];
	compounds: Entry[];
}

const DEFAULT_EXAMPLE = 'e-yay-ko-si-ram-suy-pa';

export const load: PageServerLoad = async ({ url, platform }) => {
	const db = await loadDatabase(platform);
	// If no explicit query is supplied, fall back to the paper's signature
	// polysynthetic example so the empty state actually showcases the tree.
	const explicitQ = url.searchParams.get('q')?.trim() ?? '';
	const q = explicitQ || DEFAULT_EXAMPLE;
	const isDefault = !explicitQ;

	const composition: CompositionResult | null = q
		? compose(q, { byKey: db.byKey, byId: db.byId, segmentationKeys: db.segmentationKeys })
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

	const families = pickFamilies(db.entries);

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
		families,
		stats: {
			total: db.entries.length,
			verified: db.entries.filter((e) => e.verified).length,
			withFrame: db.entries.filter((e) => e.base_frame).length,
			withCategory: db.entries.filter((e) => e.category).length
		}
	};
};

export interface WordFamily {
	// Optional anchor (the morpheme the row is built around). Not shown as a
	// caption — only used as a stable key on the client side.
	key: string;
	examples: string[];
}

function pickFamilies(entries: Entry[]): WordFamily[] {
	const byKey = new Set<string>();
	for (const e of entries) {
		byKey.add(e.lemma);
		for (const v of e.allomorphs) byKey.add(v);
		byKey.add(e.lemma.replace(/^[-=]+|[-=]+$/g, ''));
	}
	const resolves = (demo: string) =>
		demo
			.split(/[\s-]+/)
			.filter(Boolean)
			.every((tok) => byKey.has(tok) || byKey.has(tok.replace(/^[-=]+|[-=]+$/g, '')));

	// Hand-picked rows of attested forms only. Every entry below either
	// appears in the paper (sections introduction / system / database /
	// compute) or is curated in morpheme_db/seed/morphemes.json. We avoid
	// listing single-morpheme heads (which are not compositions) and we
	// avoid productive forms that aren't recorded as attested Ainu words.
	const families: WordFamily[] = [
		{
			key: 'nukar',
			// Worked example from system.typ §2.1 + the curated inkar reduction.
			examples: ['inkar', 'nukar-e', 'si-nukar-e', 'yay-nukar']
		},
		{
			key: 'koyki',
			// Noun-incorporation example cited in system.typ.
			examples: ['cep koyki']
		},
		{
			key: 'iku',
			// Curated phonological reduction (i- + ku).
			examples: ['iku']
		},
		{
			key: 'polysynthetic',
			// The paper's headline example (introduction.typ §1).
			examples: ['e-yay-ko-si-ram-suy-pa']
		}
	];

	return families
		.map((family) => ({ ...family, examples: family.examples.filter(resolves) }))
		.filter((family) => family.examples.length > 0);
}
