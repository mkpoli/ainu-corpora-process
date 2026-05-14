// Map source-attribution strings to URLs when we know one. The morpheme
// database uses ad-hoc citation keys (e.g. "佐藤2023…", "NINJALCorpus"), so
// this is a small explicit table rather than something inferred.
//
// `Wiktionary EN` / `Wiktionary JA` get lemma-specific URLs because Wiktionary
// pages exist for each Ainu morpheme.

const FIXED_URLS: Record<string, string> = {
	NINJALCorpus: 'https://ainu.ninjal.ac.jp/topic/',
	NAMCorpus: 'https://ainugo.nam.go.jp/',
	AACorpus: 'https://aacorpus.aa-ken.jp/'
};

export function sourceUrl(source: string, lemma?: string): string | null {
	if (FIXED_URLS[source]) return FIXED_URLS[source];

	const target = (lemma ?? '').replace(/^[-=]+|[-=]+$/g, '');
	if (!target) return null;

	if (source === 'Wiktionary EN' || source === 'WiktionaryEN') {
		return `https://en.wiktionary.org/wiki/${encodeURIComponent(target)}#Ainu`;
	}
	if (source === 'Wiktionary JA' || source === 'WiktionaryJA') {
		return `https://ja.wiktionary.org/wiki/${encodeURIComponent(target)}#.E3.82.A2.E3.82.A4.E3.83.8C.E8.AA.9E`;
	}
	if (source === 'Tommy 1949' || source === 'Tommy1949') {
		return 'https://www.dampopo.jp/~ahirohaifu/aynudictionary.html';
	}
	return null;
}

export function sourceLabel(source: string): string {
	// Normalise a couple of variants for display.
	if (source === 'WiktionaryJA') return 'Wiktionary JA';
	if (source === 'WiktionaryEN') return 'Wiktionary EN';
	if (source === 'Tommy1949') return 'Tommy 1949';
	if (source === 'NINJALCorpus') return 'NINJAL Corpus';
	if (source === 'NAMCorpus') return 'NAM Archive';
	if (source === 'AACorpus') return 'AA-Corpus';
	if (source === 'Dictionary') return 'Dictionary'; // legacy, kept until ingests migrate
	return source;
}
