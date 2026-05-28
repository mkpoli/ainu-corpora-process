import { loadDatabase } from '$lib/server/database';
import { effectiveValencyDelta, valencyDelta } from '$lib/composition';
import type { Entry } from '$lib/types';
import type { PageServerLoad } from './$types';

const PAGE_SIZE = 80;

export const load: PageServerLoad = async ({ url, platform }) => {
	const db = await loadDatabase(platform);

	const q = (url.searchParams.get('q') ?? '').trim().toLowerCase();
	const category = url.searchParams.get('cat') ?? '';
	const verifiedOnly = url.searchParams.get('verified') === '1';
	const withComposition = url.searchParams.get('composition') === '1';
	const withFrame = url.searchParams.get('frame') === '1';
	const page = Math.max(1, parseInt(url.searchParams.get('page') ?? '1', 10) || 1);
	const sort = url.searchParams.get('sort') ?? 'frequency';
	const dir = url.searchParams.get('dir') === 'asc' ? 'asc' : 'desc';

	const filtered = db.entries.filter((entry) => {
		if (verifiedOnly && !entry.verified) return false;
		if (withComposition && !entry.composition.length) return false;
		if (withFrame && !entry.base_frame) return false;
		if (category && entry.category !== category) return false;
		if (q) {
			const hay = [
				entry.lemma,
				...entry.allomorphs,
				...entry.glosses_en,
				...entry.glosses_jp,
				entry.notes
			]
				.join(' ')
				.toLowerCase();
			if (!hay.includes(q)) return false;
		}
		return true;
	});

	const sorted = [...filtered].sort((a, b) => {
		const compare = compareEntries(a, b, sort);
		return dir === 'asc' ? compare : -compare;
	});

	const total = sorted.length;
	const start = (page - 1) * PAGE_SIZE;
	const slice = sorted.slice(start, start + PAGE_SIZE);

	const categories = [...new Set(db.entries.map((e) => e.category).filter(Boolean))].sort();

	const rows = slice.map((entry) => {
		const explicit = valencyDelta(entry);
		const effective = effectiveValencyDelta(entry);
		return {
			id: entry.id,
			lemma: entry.lemma,
			morph_type: entry.morph_type,
			category: entry.category,
			bound: entry.bound,
			verified: entry.verified,
			frequency: entry.frequency,
			composition_length: entry.composition.length,
			gloss_en: entry.glosses_en[0] ?? '',
			gloss_jp: entry.glosses_jp[0] ?? '',
			source_count: entry.sources.length,
			delta: effective,
			delta_inferred: explicit === null && effective !== null,
			arity: entry.base_frame
				? entry.base_frame.slots.filter((s) => s.realization === 'external').length
				: null
		};
	});

	return {
		rows,
		page,
		pageSize: PAGE_SIZE,
		total,
		query: q,
		category,
		verifiedOnly,
		withComposition,
		withFrame,
		sort,
		dir,
		categories,
		stats: {
			total: db.entries.length,
			verified: db.entries.filter((e) => e.verified).length,
			withFrame: db.entries.filter((e) => e.base_frame).length,
			withComposition: db.entries.filter((e) => e.composition.length).length
		}
	};
};

function compareEntries(a: Entry, b: Entry, sort: string): number {
	switch (sort) {
		case 'lemma':
			return a.lemma.localeCompare(b.lemma);
		case 'category':
			return (a.category || '').localeCompare(b.category || '');
		case 'morph_type':
			return (a.morph_type || '').localeCompare(b.morph_type || '');
		case 'verified':
			return Number(a.verified) - Number(b.verified);
		case 'composition':
			return a.composition.length - b.composition.length;
		case 'arity':
			return arityOf(a) - arityOf(b);
		case 'frequency':
		default:
			return a.frequency - b.frequency;
	}
}

function arityOf(e: Entry): number {
	if (e.base_frame) {
		return e.base_frame.slots.filter((s) => s.realization === 'external').length;
	}
	const inferred = effectiveValencyDelta(e);
	return inferred ?? -1;
}
