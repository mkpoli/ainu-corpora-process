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
	title: string;
	gloss_en: string;
	gloss_jp: string;
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
			.some((tok) => byKey.has(tok) || byKey.has(tok.replace(/^[-=]+|[-=]+$/g, '')));

	const families: WordFamily[] = [
		{
			title: 'nukar',
			gloss_en: '“see” — derivations',
			gloss_jp: '「見る」 の派生',
			examples: ['nukar', 'inkar', 'nukar-e', 'si-nukar-e', 'yay-nukar', 'i-nukar', 'yay-ko-nukar', 'nukar-yar']
		},
		{
			title: 'ku',
			gloss_en: '“drink” — fused indef object',
			gloss_jp: '「飲む」 と i-ku の縮約',
			examples: ['ku', 'iku', 'i-ku']
		},
		{
			title: 'kor',
			gloss_en: '“have” — applicative & indef',
			gloss_jp: '「持つ」 への ko-/i- 派生',
			examples: ['kor', 'i-kor', 'ko-kor', 'yay-kor']
		},
		{
			title: 'ki',
			gloss_en: '“do” — light verb compounds',
			gloss_jp: '「する」 軽動詞構文',
			examples: ['ki', 'i-ki', 'ki-yar', 'si-ki']
		},
		{
			title: 'ye',
			gloss_en: '“say” — quotative compounds',
			gloss_jp: '「言う」 引用関連',
			examples: ['ye', 'ko-ye', 'e-ye', 'i-ye', 'ye-yar']
		},
		{
			title: 'an / oka',
			gloss_en: '“be (sg/pl)” — suppletion',
			gloss_jp: '「ある」 単複の補充',
			examples: ['an', 'oka']
		},
		{
			title: 'arpa / paye',
			gloss_en: '“go (sg/pl)” — suppletion',
			gloss_jp: '「行く」 単複の補充',
			examples: ['arpa', 'paye']
		},
		{
			title: 'cep koyki',
			gloss_en: 'noun incorporation',
			gloss_jp: '名詞抱合',
			examples: ['cep koyki', 'koyki', 'cep']
		},
		{
			title: 'paper example',
			gloss_en: 'polysynthetic compound from §1',
			gloss_jp: '第 1 節の複合形',
			examples: ['e-yay-ko-si-ram-suy-pa']
		}
	];

	return families
		.map((family) => ({ ...family, examples: family.examples.filter(resolves) }))
		.filter((family) => family.examples.length > 0);
}
