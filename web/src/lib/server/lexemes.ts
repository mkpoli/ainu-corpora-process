import type { Lexeme } from '$lib/types';
import rawData from '$lib/data/lexemes.json';

export interface LexemeBank {
	lexemes: Lexeme[];
	byId: Map<string, Lexeme>;
}

let cache: LexemeBank | null = null;

export async function loadLexemes(_platform?: App.Platform): Promise<LexemeBank> {
	if (cache) return cache;
	const lexemes = rawData as unknown as Lexeme[];
	const byId = new Map<string, Lexeme>();
	for (const lx of lexemes) byId.set(lx.id, lx);
	cache = { lexemes, byId };
	return cache;
}
