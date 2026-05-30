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
	/** The lexeme's multi-morpheme composition, resolved to display lemmas
	 *  (e.g. ["i-","nukar"]). Empty for monomorphemic / unlinked lexemes. */
	morphemes: string[];
	/** Whether the lexeme links into the morpheme bank at all (for the stat). */
	morphemeLinked: boolean;
	senses: number;
}

export const load: PageServerLoad = async ({ url, platform }) => {
	const bank = await loadLexemes(platform);
	const db = await loadDatabase(platform);
	const lemmaOf = (mid: string) => db.byId.get(mid)?.lemma ?? mid;

	// The lexeme's own `morphemes` field is just a single link into the
	// morpheme bank — the real multi-morpheme breakdown lives on that
	// morpheme's `composition` (e.g. inkar -> i- + nukar). Resolve through to
	// it, flatten any nested bracketing, and map to display lemmas. Empty when
	// the lexeme is monomorphemic / unlinked (nothing to combine).
	const flatten = (comp: unknown[]): string[] =>
		comp.flatMap((item) => (Array.isArray(item) ? flatten(item) : [String(item)]));
	const combinationOf = (morphemeIds: string[]): string[] => {
		const entry = morphemeIds[0] ? db.byId.get(morphemeIds[0]) : undefined;
		const comp = entry?.composition ?? [];
		return comp.length > 1 ? flatten(comp).map(lemmaOf) : [];
	};

	// Reverse cross-link from the morpheme explorer: ?morph=<morpheme-id>
	// narrows the list to lexemes that compose that morpheme.
	const morphId = url.searchParams.get('morph')?.trim() ?? '';
	let morphFilter: { id: string; lemma: string } | null = null;
	let source = bank.lexemes;
	if (morphId) {
		source = bank.lexemes.filter((lx) => lx.morphemes.includes(morphId));
		morphFilter = { id: morphId, lemma: lemmaOf(morphId) };
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
		morphemes: combinationOf(lx.morphemes),
		morphemeLinked: lx.morphemes.length > 0,
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
			morphemeLinked: rows.filter((r) => r.morphemeLinked).length
		}
	};
};
