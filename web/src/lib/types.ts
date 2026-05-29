// Mirror of morpheme_db.schema (Python). Keep the shape in sync.

export type SlotRealization =
	| 'external'
	| 'internal_incorp'
	| 'internal_refl'
	| 'internal_indef'
	| 'absorbed';

export interface Slot {
	role: string;
	realization: SlotRealization;
	label_jp: string;
}

export interface ValencyFrame {
	slots: Slot[];
}

export interface Rule {
	operation: 'add_slot' | 'remove_slot' | 'internalize' | 'noop';
	role?: string;
	realization?: SlotRealization;
	position?: 'front' | 'back';
	target_index?: number;
	label_jp?: string;
	description?: string;
}

export interface Entry {
	id: string;
	lemma: string;
	allomorphs: string[];
	category: string;
	category_alt: string[];
	bound: boolean;
	morph_type: 'root' | 'prefix' | 'suffix' | 'clitic' | 'stem' | 'particle';
	/** Morphotactic slot(s) per Bugaeva 2014's revision of Tamura 1955 —
	 * Roman numerals "I"–"VI". Empty for non-template morphemes. Affixes
	 * that can sit in multiple slots (applicatives I/III, productive -re
	 * V/VI) list each. Used for display only — does not constrain
	 * segmentation. */
	slot: string[];
	base_frame: ValencyFrame | null;
	rules: Rule[];
	attaches_to: string[];
	selection: string[];
	glosses_en: string[];
	glosses_jp: string[];
	dialects: string[];
	sources: string[];
	notes: string;
	frequency: number;
	verified: boolean;
	/** Ordered morpheme ids — or, where bracketing matters (e.g. fossilised
	 * (ci= e)-p in cep), a list with nested string-arrays for sub-groups.
	 * The rendering engine builds inner groups first and treats the result
	 * as a single constituent at the outer level. */
	composition: (string | string[])[];
	/** Source-text surface form for each slot in `composition` — present
	 * when the upstream ingest (Tommy 1949, Wiktionary) recorded the
	 * actual form used, which can differ from the resolved entry's lemma
	 * when allomorphs are clustered (`-te` → entry `-e`). Renderers should
	 * prefer this over `entry.lemma` for the composition graph so `upakte`
	 * displays as `u-pak-te` rather than the phonologically impossible
	 * `u-pak-e`. Empty array (or shorter than `composition`) means fall
	 * back to the resolved entry's lemma. */
	composition_surface: string[];
	composition_note: string;
	/** Reconstructed proto-forms, keyed by reconstruction-source short
	 * name (e.g. `SRPA` for Shiratori's Proto-Ainu Reconstruction).
	 * Values are conventionally prefixed with `*`. */
	reconstructed: Record<string, string>;
	etymology?: Etymology | null;
}

export interface EtymologyPart {
	lemma: string;
	id?: string;
	category?: string;
	morph_type?: string;
	gloss_en?: string;
	gloss_jp?: string;
	/** Static valency annotation for this form: +N for arity, displayed in
	 * the chip like the synchronic +1/−1 badge. Optional. */
	valency?: number;
	/** If this part is itself derived from another morpheme, the underlying
	 * form. Renders as another chip beneath this one, connected by a labelled
	 * arrow. */
	derived_from?: EtymologyPart;
	/** Name of the derivational process that produced this part from
	 * `derived_from`. E.g. "zero-derivation N←V". */
	process?: string;
	/** Signed arity change applied by `process` (e.g. -1 for zero-derivation
	 * dropping the verbal argument). */
	process_delta?: number;
}

export interface Etymology {
	parts: EtymologyPart[];
	note?: string;
	source?: string;
}

// One node in the bracketed composition tree.
export type CompositionKind =
	| 'head'
	| 'prefix'
	| 'suffix'
	| 'standalone'
	| 'unknown'
	| 'fused'
	| 'compound'
	| 'incorporation'
	| 'lexeme';

export interface CompositionNode {
	// Surface form for this constituent — for a leaf, the morpheme; for an
	// internal node, the surface concatenation of its children.
	surface: string;
	// 'head' for the resolved verb/noun root, 'prefix'/'suffix' for affixes,
	// 'standalone' for a single-token expression, 'unknown' for unresolved
	// segments.
	kind: CompositionKind;
	entry: Entry | null;
	// Effective valency frame after applying everything inside this subtree.
	frame: ValencyFrame | null;
	// For internal nodes: the affix being applied at this level (left for
	// prefix-headed nodes, right for suffix-headed nodes) and the child
	// subtree it wraps.
	affix?: CompositionNode;
	body?: CompositionNode;
	// Which side of the host the `affix` sits on. Decoupled from `kind`
	// because category-derived labels like 'incorporation' and 'compound'
	// can occur on either side (ram is incorporated *before* suy on the
	// prefix side; kur is suffixed *after* cep-koyki on the suffix side).
	// Internal nodes only.
	side?: 'prefix' | 'suffix';
	// Set to true for the originally-resolved token at the deepest layer.
	// Helps the UI render a different chip style.
	isLeaf: boolean;
}

export type CompositionSource = 'direct' | 'composition' | 'split' | 'segmented' | 'unknown';

export interface CompositionResult {
	input: string;
	matchedEntry: Entry | null;
	tree: CompositionNode;
	tokens: string[];
	unresolved: string[];
	warnings: string[];
	source: CompositionSource;
	/** True when the input did not match any entry and segmentation also
	 * could not produce a useful decomposition. The UI shows a "we've never
	 * seen this word" warning in that case. */
	unseen: boolean;
}
