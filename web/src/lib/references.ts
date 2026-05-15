import refs from '$lib/data/references.json';

export interface Reference {
	key: string;
	type?: string;
	title?: string;
	author?: string | string[];
	date?: string;
	publisher?: string;
	journal?: string;
	volume?: string;
	issue?: string;
	page_range?: string;
	url?: string;
	doi?: string;
	isbn?: string;
	language?: string;
}

const REFS = refs as Record<string, Reference>;

// Friendly source labels (used in the Entry.sources array and the UI) map to
// the canonical refs.yml key when the link should resolve to a bibliography
// entry. Anything not listed here is looked up by exact key match against
// references.json first; otherwise treated as a raw label with no biblio
// destination.
const ALIASES: Record<string, string> = {
	'Wiktionary JA': '日本語ウィクショナリー',
	WiktionaryJA: '日本語ウィクショナリー',
	'Wiktionary EN': '英語Wiktionary',
	WiktionaryEN: '英語Wiktionary',
	'NINJAL Corpus': 'NINJALCorpus',
	NINJALCorpus: 'NINJALCorpus',
	'NAM Archive': 'NAMCorpus',
	NAMCorpus: 'NAMCorpus',
	'AA-Corpus': 'AACorpus',
	AACorpus: 'AACorpus',
	'ainu-corpora': 'AinuCorpora',
	'Ainu Corpora': 'AinuCorpora',
	AinuCorpora: 'AinuCorpora'
};

export function resolveReferenceKey(source: string): string | null {
	if (ALIASES[source]) return ALIASES[source];
	if (REFS[source]) return source;
	return null;
}

export function getReference(source: string): Reference | null {
	const key = resolveReferenceKey(source);
	if (!key) return null;
	return REFS[key] ?? null;
}

export function allReferences(): Reference[] {
	return Object.values(REFS).sort((a, b) => a.key.localeCompare(b.key, 'ja'));
}

export function formatAuthor(author: Reference['author']): string {
	if (!author) return '';
	if (Array.isArray(author)) return author.join('; ');
	return String(author);
}

export function formatCitation(ref: Reference): string {
	const parts: string[] = [];
	if (ref.author) parts.push(formatAuthor(ref.author));
	if (ref.date) parts.push(`(${ref.date})`);
	if (ref.title) parts.push(`「${ref.title}」`);
	const meta: string[] = [];
	if (ref.journal) meta.push(ref.journal);
	if (ref.volume) meta.push(`vol. ${ref.volume}`);
	if (ref.issue) meta.push(`no. ${ref.issue}`);
	if (ref.page_range) meta.push(`pp. ${ref.page_range}`);
	if (ref.publisher) meta.push(ref.publisher);
	if (meta.length) parts.push(meta.join(', '));
	return parts.join(' ');
}
