import * as m from '$lib/paraglide/messages.js';

const CATEGORY_LABELS: Record<string, () => string> = {
	adn: m.category_adn,
	adv: m.category_adv,
	advp: m.category_advp,
	auxv: m.category_auxv,
	cconj: m.category_cconj,
	colloc: m.category_colloc,
	cop: m.category_cop,
	det: m.category_det,
	idiom: m.category_idiom,
	int: m.category_int,
	intj: m.category_intj,
	n: m.category_n,
	nl: m.category_nl,
	nmlz: m.category_nmlz,
	num: m.category_num,
	padv: m.category_padv,
	parti: m.category_parti,
	pers: m.category_pers,
	pfx: m.category_pfx,
	post: m.category_post,
	postp: m.category_postp,
	pron: m.category_pron,
	propn: m.category_propn,
	punct: m.category_punct,
	rel: m.category_rel,
	root: m.category_root,
	sconj: m.category_sconj,
	sfp: m.category_sfp,
	sfx: m.category_sfx,
	v: m.category_v,
	vc: m.category_vc,
	vd: m.category_vd,
	vi: m.category_vi,
	vt: m.category_vt
};

const MORPH_TYPE_LABELS: Record<string, () => string> = {
	clitic: m.morph_type_clitic,
	prefix: m.morph_type_prefix,
	root: m.morph_type_root,
	suffix: m.morph_type_suffix
};

export function categoryLabel(code: string | null | undefined): string {
	if (!code) return '';
	return CATEGORY_LABELS[code]?.() ?? code;
}

export function morphTypeLabel(code: string | null | undefined): string {
	if (!code) return '';
	return MORPH_TYPE_LABELS[code]?.() ?? code;
}

type CategoryGroupKey =
	| 'verb'
	| 'aux'
	| 'noun'
	| 'pron'
	| 'adv'
	| 'particle'
	| 'conj'
	| 'intj'
	| 'affix'
	| 'num'
	| 'other';

const CATEGORY_GROUPS: { key: CategoryGroupKey; label: () => string; codes: string[] }[] = [
	{ key: 'verb', label: m.category_group_verb, codes: ['v', 'vi', 'vt', 'vd', 'vc'] },
	{ key: 'aux', label: m.category_group_aux, codes: ['auxv', 'cop'] },
	{ key: 'noun', label: m.category_group_noun, codes: ['n', 'nl', 'nmlz', 'propn'] },
	{ key: 'pron', label: m.category_group_pron, codes: ['pron', 'adn', 'det', 'int'] },
	{ key: 'adv', label: m.category_group_adv, codes: ['adv'] },
	{
		key: 'particle',
		label: m.category_group_particle,
		codes: ['parti', 'post', 'postp', 'advp', 'padv', 'sfp', 'pers']
	},
	{ key: 'conj', label: m.category_group_conj, codes: ['cconj', 'sconj'] },
	{ key: 'intj', label: m.category_group_intj, codes: ['intj'] },
	{ key: 'affix', label: m.category_group_affix, codes: ['pfx', 'sfx', 'root'] },
	{ key: 'num', label: m.category_group_num, codes: ['num'] },
	{ key: 'other', label: m.category_group_other, codes: ['rel', 'colloc', 'idiom', 'punct'] }
];

export type CategoryOptGroup = {
	key: CategoryGroupKey;
	label: string;
	options: { code: string; label: string }[];
};

export function groupCategories(codes: readonly string[]): CategoryOptGroup[] {
	const present = new Set(codes);
	const claimed = new Set<string>();
	const groups: CategoryOptGroup[] = [];

	for (const group of CATEGORY_GROUPS) {
		const options = group.codes
			.filter((c) => present.has(c))
			.map((code) => {
				claimed.add(code);
				return { code, label: categoryLabel(code) };
			});
		if (options.length) {
			groups.push({ key: group.key, label: group.label(), options });
		}
	}

	const leftovers = codes.filter((c) => !claimed.has(c)).sort();
	if (leftovers.length) {
		const other = groups.find((g) => g.key === 'other');
		const extras = leftovers.map((code) => ({ code, label: categoryLabel(code) }));
		if (other) other.options.push(...extras);
		else groups.push({ key: 'other', label: m.category_group_other(), options: extras });
	}

	return groups;
}
