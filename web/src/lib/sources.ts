// Decide where to send a user when they click a source-attribution chip.
//
// Resolution order:
//   1. If the source resolves to a refs.yml entry (`resolveReferenceKey`),
//      link to the bibliography page anchor: `/references#<encoded-key>`.
//   2. Otherwise, fall back to a handful of hard-coded URLs for
//      lemma-specific Wiktionary deep links and a couple of corpora
//      that don't have a refs.yml entry.
//   3. Anything else stays non-clickable.
//
// The label is always normalised so legacy ingest strings (WiktionaryJA,
// NINJALCorpus, ...) render with their friendlier names.

import { resolveReferenceKey } from './references';

const FIXED_URLS: Record<string, string> = {
	'Tommy 1949': 'https://www.dampopo.jp/~ahirohaifu/aynudictionary.html',
	Tommy1949: 'https://www.dampopo.jp/~ahirohaifu/aynudictionary.html'
};

export function sourceUrl(source: string, lemma?: string): string | null {
	const refKey = resolveReferenceKey(source);
	if (refKey) return `/references#${encodeURIComponent(refKey)}`;

	if (FIXED_URLS[source]) return FIXED_URLS[source];

	const target = (lemma ?? '').replace(/^[-=]+|[-=]+$/g, '');
	if (target) {
		if (source === 'Wiktionary EN' || source === 'WiktionaryEN') {
			return `https://en.wiktionary.org/wiki/${encodeURIComponent(target)}#Ainu`;
		}
		if (source === 'Wiktionary JA' || source === 'WiktionaryJA') {
			return `https://ja.wiktionary.org/wiki/${encodeURIComponent(target)}#.E3.82.A2.E3.82.A4.E3.83.8C.E8.AA.9E`;
		}
	}
	return null;
}

export function sourceLabel(source: string): string {
	if (source === 'WiktionaryJA') return 'Wiktionary JA';
	if (source === 'WiktionaryEN') return 'Wiktionary EN';
	if (source === 'Tommy1949') return 'Tommy 1949';
	if (source === 'NINJALCorpus') return 'NINJAL Corpus';
	if (source === 'NAMCorpus') return 'NAM Archive';
	if (source === 'AACorpus') return 'AA-Corpus';
	return source;
}
