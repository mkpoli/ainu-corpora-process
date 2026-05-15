import { loadDatabase } from '$lib/server/database';
import { compose, findOtherUses } from '$lib/composition';
import type { CompositionResult, Entry } from '$lib/types';
import type { PageServerLoad } from './$types';

interface SuggestionsBuckets {
	morphemes: Entry[];
	compounds: Entry[];
}

const DEFAULT_EXAMPLE = 'eyaykotuymasiramsuypa';

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
			examples: ['nukar', 'inkar', 'nukar-e', 'si-nukar-e', 'yay-nukar']
		},
		{
			key: 'nu-family',
			// The nu / "sensory" family: nu (hear/sense) zero-derives to a
			// noun 'eye' in compounds; same root underlies nukar (see),
			// nupe (tear), yaynu (think), inu (listen), enukor (watch over).
			examples: ['nu', 'nupe', 'yaynu', 'inu', 'enukor']
		},
		{
			key: 'koyki',
			// Noun-incorporation family — all curated from田村1996/中川1995.
			examples: ['koyki', 'cepkoyki', 'aynukoyki', 'cikapkoyki', 'ukoyki', 'cepkoykikur']
		},
		{
			key: 'ku',
			// 'drink' family — bare root plus the lexicalised i-ku reduction.
			examples: ['ku', 'iku']
		},
		{
			key: 'ruska',
			// Bugaeva 2014 — extreme valency manipulation with stacked
			// applicatives / reflexives / reciprocals / causatives.
			examples: [
				'ruska',
				'koiruska',
				'sikoiruska',
				'iruskare',
				'koiruskare',
				'sikoiruskare',
				'ukoiruskare'
			]
		},
		{
			key: 'applicative-refl',
			// Applicative + reflexive / reciprocal stacks.
			examples: [
				'eyaykopuntek',
				'ewkoysoytak',
				'iyayraykere',
				'uminare',
				'sikasuyre'
			]
		},
		{
			key: 'incorporation-heavy',
			// Noun incorporation + multiple affixes.
			examples: [
				'eyayrampokwen',
				'eyaypoktacis',
				'eyayrikikurkosnepuni',
				'eyaykewtumekosanniyo'
			]
		},
		{
			key: 'suypa',
			// The "ponder" family. Single-word lemmas are the attested forms;
			// eyaykotuymasiramsuypa is the paper's headline polysynthetic
			// example (introduction.typ §1).
			examples: [
				'suye',
				'yaykosiramsuypa',
				'eyaykosiramsuypa',
				'yaykotuymasiramsuypa',
				'eyaykotuymasiramsuypa',
				'aeyaykotuymasiramsuypa'
			]
		}
	];

	return families
		.map((family) => ({ ...family, examples: family.examples.filter(resolves) }))
		.filter((family) => family.examples.length > 0);
}
