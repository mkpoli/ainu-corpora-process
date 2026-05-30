import { loadLexemes } from '$lib/server/lexemes';
import { loadDatabase } from '$lib/server/database';
import type { PageServerLoad } from './$types';

// Slim row shape for the table — we drop the heavy `attestations` array here
// (the detail route loads it per-lexeme) and keep only what the list renders.
export interface LexemeRow {
	id: string;
	lemma: string;
	kana: string;
	pos: string;
	gloss_jp: string;
	gloss_en: string;
	bound: boolean;
	dialects: string[];
	recordings: number;
	sources: number;
	morphemes: number;
	senses: number;
}

export const load: PageServerLoad = async ({ url, platform }) => {
	const bank = await loadLexemes(platform);

	// Reverse cross-link from the morpheme explorer: ?morph=<morpheme-id>
	// narrows the list to lexemes that compose that morpheme. We resolve the
	// id to its lemma (for the banner) from the morpheme bank.
	const morphId = url.searchParams.get('morph')?.trim() ?? '';
	let morphFilter: { id: string; lemma: string } | null = null;
	let source = bank.lexemes;
	if (morphId) {
		source = bank.lexemes.filter((lx) => lx.morphemes.includes(morphId));
		const db = await loadDatabase(platform);
		morphFilter = { id: morphId, lemma: db.byId.get(morphId)?.lemma ?? morphId };
	}

	const rows: LexemeRow[] = source.map((lx) => ({
		id: lx.id,
		lemma: lx.lemma,
		kana: lx.kana,
		pos: lx.pos,
		gloss_jp: lx.gloss_jp[0] ?? '',
		gloss_en: lx.gloss_en[0] ?? '',
		bound: lx.bound,
		dialects: lx.dialects,
		recordings: lx.recordings,
		sources: lx.sources.length,
		morphemes: lx.morphemes.length,
		senses: lx.senses.length
	}));
	// Multi-dialect first (the interesting ones for cross-dialect comparison),
	// then by most recordings, then alphabetically.
	rows.sort(
		(a, b) =>
			b.dialects.length - a.dialects.length ||
			b.recordings - a.recordings ||
			a.lemma.localeCompare(b.lemma)
	);
	return {
		rows,
		morphFilter,
		stats: {
			total: rows.length,
			multiDialect: rows.filter((r) => r.dialects.length > 1).length,
			senseSplit: rows.filter((r) => r.senses > 0).length,
			morphemeLinked: rows.filter((r) => r.morphemes > 0).length
		}
	};
};
