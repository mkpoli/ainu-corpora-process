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
	composition: string[];
	composition_note: string;
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
export type CompositionKind = 'head' | 'prefix' | 'suffix' | 'standalone' | 'unknown' | 'fused';

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
