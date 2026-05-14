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
}

// One node in the bracketed composition tree.
export type CompositionKind = 'head' | 'prefix' | 'suffix' | 'standalone' | 'unknown';

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

export interface CompositionResult {
	input: string;
	matchedEntry: Entry | null;
	tree: CompositionNode;
	tokens: string[];
	unresolved: string[];
	warnings: string[];
}
