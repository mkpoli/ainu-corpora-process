import { error } from '@sveltejs/kit';
import { loadLexemes } from '$lib/server/lexemes';
import { loadDatabase } from '$lib/server/database';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, platform }) => {
	const bank = await loadLexemes(platform);
	const lexeme = bank.byId.get(params.id);
	if (!lexeme) throw error(404, `No lexeme '${params.id}'`);

	// Resolve the morpheme composition to lemmas/glosses for display + linking.
	const db = await loadDatabase(platform);
	const morphemes = lexeme.morphemes.map((mid) => {
		const e = db.byId.get(mid);
		return {
			id: mid,
			lemma: e?.lemma ?? mid,
			gloss_en: e?.glosses_en?.[0] ?? '',
			gloss_jp: e?.glosses_jp?.[0] ?? '',
			resolved: !!e
		};
	});

	// Group recordings by dialect — this is the cross-dialect pivot.
	const byDialect = new Map<string, typeof lexeme.attestations>();
	for (const att of lexeme.attestations) {
		const key = att.dialect || '—';
		if (!byDialect.has(key)) byDialect.set(key, []);
		byDialect.get(key)!.push(att);
	}
	const dialectGroups = [...byDialect.entries()]
		.map(([dialect, attestations]) => ({ dialect, attestations }))
		.sort((a, b) => a.dialect.localeCompare(b.dialect));

	return { lexeme, morphemes, dialectGroups };
};
