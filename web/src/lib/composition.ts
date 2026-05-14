// Composition + valency engine, ported from morpheme_db/valency.py.
//
// Two responsibilities:
//   1. Build the hierarchical bracketing for a morpheme sequence, with the
//      head verb/noun at the deepest layer, suffixes wrapping it from the
//      inside out, and prefixes wrapping the whole thing from the outside
//      in. So si-nukar-e renders as si-(nukar-e), not ((si-nukar)-e).
//   2. Apply each entry's local rules to derive the effective valency frame
//      attached to every node in the tree.

import type {
	CompositionKind,
	CompositionNode,
	CompositionResult,
	CompositionSource,
	Entry,
	Rule,
	Slot,
	ValencyFrame
} from './types';

interface EntryIndex {
	byKey: Map<string, Entry>;
	byId?: Map<string, Entry>;
	segmentationKeys: string[];
}

export interface CompositionInput {
	input: string;
	index: EntryIndex;
}

function cloneFrame(frame: ValencyFrame | null): ValencyFrame | null {
	if (!frame) return null;
	return { slots: frame.slots.map((s) => ({ ...s })) };
}

function findSlotIndex(frame: ValencyFrame, role: string): number {
	return frame.slots.findIndex((s) => s.role === role);
}

function applyRule(frame: ValencyFrame, rule: Rule, warnings: string[], context: string): ValencyFrame {
	const next: ValencyFrame = cloneFrame(frame)!;
	switch (rule.operation) {
		case 'noop':
			return next;
		case 'add_slot': {
			const slot: Slot = {
				role: rule.role || 'arg',
				realization: rule.realization || 'external',
				label_jp: rule.label_jp || ''
			};
			if (rule.position === 'back') next.slots.push(slot);
			else next.slots.unshift(slot);
			return next;
		}
		case 'remove_slot': {
			let index = rule.target_index;
			if (index === undefined && rule.role) index = findSlotIndex(next, rule.role);
			if (index === undefined || index < 0 || index >= next.slots.length) {
				warnings.push(`${context}: remove_slot missed target (role=${rule.role ?? ''})`);
				return next;
			}
			next.slots.splice(index, 1);
			return next;
		}
		case 'internalize': {
			let index = rule.target_index;
			if (index === undefined && rule.role) index = findSlotIndex(next, rule.role);
			if (index === undefined) {
				index = next.slots.findIndex((s) => s.realization === 'external');
			}
			if (index === undefined || index < 0 || index >= next.slots.length) {
				warnings.push(`${context}: internalize missed target (role=${rule.role ?? ''})`);
				return next;
			}
			const slot = next.slots[index];
			slot.realization = rule.realization || 'internal_refl';
			if (rule.label_jp) slot.label_jp = rule.label_jp;
			return next;
		}
		default:
			warnings.push(`${context}: unknown operation ${rule.operation}`);
			return next;
	}
}

function applyRules(
	frame: ValencyFrame,
	entry: Entry,
	warnings: string[]
): ValencyFrame {
	let current = frame;
	for (const rule of entry.rules) {
		current = applyRule(current, rule, warnings, `${entry.id}`);
	}
	return current;
}

export function arity(frame: ValencyFrame | null): number {
	if (!frame) return 0;
	return frame.slots.filter((s) => s.realization === 'external').length;
}

// --- Token resolution ----------------------------------------------------

function resolveToken(token: string, byKey: Map<string, Entry>): Entry | null {
	const bare = token.replace(/^[-=]+|[-=]+$/g, '');
	const candidates = [token, bare, `-${bare}`, `${bare}-`, `=${bare}`, `${bare}=`];
	for (const cand of candidates) {
		if (!cand) continue;
		const e = byKey.get(cand);
		if (e) return e;
	}
	return null;
}

// Best-scoring segmentation against the known morpheme inventory.
//
// The naïve "longest-first match" is wrong for cases like `sinukare`, where
// `sinu` is a valid morpheme but the right parse is `si-, nukar, -e`. We do
// a small dynamic-programming search over all valid segmentations, then
// score each candidate so that parses including a verb head outrank parses
// that don't, parses with more recognised affixes outrank shorter ones,
// and shorter unresolved spans outrank longer ones.
function segmentBest(
	text: string,
	keys: string[],
	byKey: Map<string, Entry>
): { segments: string[]; unresolved: string[] } {
	const cleaned = text.toLowerCase();
	const n = cleaned.length;
	if (!n) return { segments: [], unresolved: [] };

	type Parse = {
		segments: string[];
		unresolved: string[];
		hasHead: boolean;
		recognised: number;
		score: number;
	};

	const keysByPrefixLength = [...keys].sort((a, b) => b.length - a.length);

	// best[i] = best parse covering cleaned[0..i]
	const best: (Parse | null)[] = new Array(n + 1).fill(null);
	best[0] = { segments: [], unresolved: [], hasHead: false, recognised: 0, score: 0 };

	const scoreOf = (p: Parse): number => {
		// Big bonus for a head with a base_frame — pins the analysis onto a
		// real verb root. Then reward recognised characters, then penalise
		// leftover characters.
		const headBonus = p.hasHead ? 1000 : 0;
		const unresolvedChars = p.unresolved.reduce((sum, u) => sum + u.length, 0);
		return headBonus + p.recognised * 10 - unresolvedChars * 5 - p.segments.length;
	};

	const extend = (prev: Parse, atEnd: number, addSegment: string | null, addChar: string | null): Parse => {
		const segments = [...prev.segments];
		const unresolved = [...prev.unresolved];
		let hasHead = prev.hasHead;
		let recognised = prev.recognised;
		if (addSegment) {
			segments.push(addSegment);
			recognised += addSegment.length;
			// Resolve the segment against any registered key variant.
			const entry = resolveToken(addSegment, byKey);
			if (entry?.base_frame) hasHead = true;
		} else if (addChar) {
			if (unresolved.length && segments.length === 0) {
				// Run of unresolved chars at the start: keep appending.
				unresolved[unresolved.length - 1] += addChar;
			} else if (unresolved.length && atEnd === prev.segments.length) {
				unresolved[unresolved.length - 1] += addChar;
			} else {
				unresolved.push(addChar);
			}
		}
		const next: Parse = { segments, unresolved, hasHead, recognised, score: 0 };
		next.score = scoreOf(next);
		return next;
	};

	for (let i = 0; i < n; i += 1) {
		const here = best[i];
		if (!here) continue;
		// Option A: skip an unrecognised character.
		const skipNext = extend(here, here.segments.length, null, cleaned[i]);
		if (!best[i + 1] || skipNext.score > best[i + 1]!.score) best[i + 1] = skipNext;
		// Option B: consume a known morpheme.
		for (const key of keysByPrefixLength) {
			if (key.length > n - i) continue;
			if (cleaned.startsWith(key, i)) {
				const candidate = extend(here, here.segments.length, key, null);
				const target = i + key.length;
				if (!best[target] || candidate.score > best[target]!.score) best[target] = candidate;
			}
		}
	}

	const final = best[n];
	if (!final) return { segments: [], unresolved: [text] };
	return { segments: final.segments, unresolved: final.unresolved.filter(Boolean) };
}

// --- Splitting user input -------------------------------------------------

export function splitInput(input: string): string[] {
	const trimmed = input.trim();
	if (!trimmed) return [];
	// Whitespace-separated tokens win — they encode the user's own segmentation.
	const wsTokens = trimmed.split(/\s+/).filter(Boolean);
	if (wsTokens.length > 1) return wsTokens;
	const sole = wsTokens[0];
	if (!sole.includes('-')) return [sole];
	const parts = sole.split('-');
	const out: string[] = [];
	const last = parts.length - 1;
	for (let i = 0; i < parts.length; i += 1) {
		const part = parts[i];
		if (part === '') continue;
		if (i === 0 && last > 0 && parts[1] !== '') out.push(part + '-');
		else if (i === last && i > 0 && parts[i - 1] !== '') out.push('-' + part);
		else out.push(part);
	}
	return out.length ? out : [sole];
}

// --- Tree builder --------------------------------------------------------

function classify(entry: Entry, isHead: boolean): CompositionKind {
	if (isHead) return 'head';
	if (entry.morph_type === 'prefix') return 'prefix';
	if (entry.morph_type === 'suffix') return 'suffix';
	// Heuristic for affixes that NINJAL writes bare but have rules attached.
	if (entry.rules.length) {
		const lemma = entry.lemma;
		if (lemma.endsWith('-')) return 'prefix';
		if (lemma.startsWith('-')) return 'suffix';
	}
	return 'standalone';
}

function buildTree(
	matched: { token: string; entry: Entry | null }[],
	warnings: string[]
): CompositionNode {
	// Locate the head: first entry that carries a base_frame. If none, fall
	// back to the first entry; if there are no matches at all, return an
	// unknown leaf so the UI can still render something.
	if (matched.length === 0) {
		return {
			surface: '',
			kind: 'unknown',
			entry: null,
			frame: null,
			isLeaf: true
		};
	}

	let headIndex = matched.findIndex((m) => m.entry?.base_frame);
	if (headIndex === -1) headIndex = matched.findIndex((m) => m.entry);
	if (headIndex === -1) {
		// Everything unresolved.
		return {
			surface: matched.map((m) => m.token).join('-'),
			kind: 'unknown',
			entry: null,
			frame: null,
			isLeaf: true
		};
	}

	const headMatch = matched[headIndex];
	const headEntry = headMatch.entry!;
	const headFrame =
		cloneFrame(headEntry.base_frame) ??
		(headEntry.rules.length ? { slots: [] } : null);

	// Apply head's own rules (if any) before wrapping in affixes.
	const startingFrame = headFrame ? applyRules(headFrame, headEntry, warnings) : null;

	// Use the canonical lemma (with markers stripped) so the surface of any
	// later wrapping doesn't pick up the splitter's directional hint. e.g.
	// for the input "nukar-yar" we want the head surface to be "nukar", not
	// "nukar-", so the wrapped surface is "nukar-yar" rather than "nukar--yar".
	const headSurface = headEntry.lemma.replace(/^[-=]+|[-=]+$/g, '');

	let node: CompositionNode = {
		surface: headSurface || headEntry.lemma,
		kind: 'head',
		entry: headEntry,
		frame: startingFrame,
		isLeaf: true
	};

	// Wrap suffixes inside-out (i.e. apply -e before applying anything else
	// that sits further right).
	for (let i = headIndex + 1; i < matched.length; i += 1) {
		node = wrapAffix(node, matched[i], 'suffix', warnings);
	}

	// Wrap prefixes outside-in (so si- in si-nukar-e applies AFTER -e has
	// already created the causer slot).
	for (let i = headIndex - 1; i >= 0; i -= 1) {
		node = wrapAffix(node, matched[i], 'prefix', warnings);
	}

	return node;
}

function wrapAffix(
	body: CompositionNode,
	child: { token: string; entry: Entry | null },
	side: 'prefix' | 'suffix',
	warnings: string[]
): CompositionNode {
	const entry = child.entry;
	const affixLeaf: CompositionNode = entry
		? {
				surface: entry.lemma,
				kind: classify(entry, false),
				entry,
				frame: null,
				isLeaf: true
			}
		: {
				surface: child.token,
				kind: 'unknown',
				entry: null,
				frame: null,
				isLeaf: true
			};
	const nextFrame = entry && body.frame ? applyRules(body.frame, entry, warnings) : cloneFrame(body.frame);
	const affixBare = (entry?.lemma ?? child.token).replace(/^[-=]+|[-=]+$/g, '');
	const bodyBare = body.surface.replace(/^[-=]+|[-=]+$/g, '');
	const surface = side === 'prefix' ? `${affixBare}-${bodyBare}` : `${bodyBare}-${affixBare}`;
	return {
		surface,
		kind: side,
		entry: null,
		frame: nextFrame,
		affix: affixLeaf,
		body,
		isLeaf: false
	};
}

// --- Public entry point ---------------------------------------------------

function resolveById(id: string, index: EntryIndex): Entry | null {
	if (index.byId) {
		const found = index.byId.get(id);
		if (found) return found;
	}
	// Fall back to byKey if the caller didn't supply byId.
	for (const e of index.byKey.values()) {
		if (e.id === id) return e;
	}
	return null;
}

export function compose(input: string, index: EntryIndex): CompositionResult {
	const warnings: string[] = [];
	const raw = input.trim();
	if (!raw) {
		return {
			input,
			matchedEntry: null,
			tokens: [],
			unresolved: [],
			warnings,
			tree: { surface: '', kind: 'unknown', entry: null, frame: null, isLeaf: true },
			source: 'unknown',
			unseen: false
		};
	}

	// Case 1: the whole input matches a known entry directly. Three sub-cases
	// in priority order:
	//   1a. The entry declares an explicit `composition` (e.g. inkar →
	//       [i-, nukar]). We trust that as the structural truth and build
	//       the tree from it, regardless of what segmentation would suggest.
	//   1b. The entry's lemma cleanly segments into multiple known morphemes
	//       and the input doesn't already look hyphen-segmented — we expose
	//       that internal structure.
	//   1c. Otherwise we keep the direct match as a standalone leaf.
	const directMatch = index.byKey.get(raw) ?? index.byKey.get(raw.toLowerCase());
	const looksCompound = raw.includes('-') || /\s/.test(raw);

	let tokens: string[];
	let unresolved: string[] = [];
	let matched: { token: string; entry: Entry | null }[] = [];
	let source: CompositionSource = 'unknown';
	let fusedRoot: Entry | null = null;

	if (directMatch && directMatch.composition.length && !looksCompound) {
		const resolved = directMatch.composition.map((id) => {
			const entry = resolveById(id, index);
			if (!entry) {
				warnings.push(`composition references unknown entry id ${id}`);
				unresolved.push(id);
			}
			return { token: entry?.lemma ?? id, entry };
		});
		tokens = resolved.map((r) => r.entry?.lemma ?? r.token);
		matched = resolved;
		fusedRoot = directMatch;
		source = 'composition';
	} else if (directMatch && !looksCompound) {
		const seg = segmentBest(directMatch.lemma.replace(/^[-=]+|[-=]+$/g, ''), index.segmentationKeys, index.byKey);
		if (seg.segments.length >= 2 && seg.unresolved.length === 0) {
			tokens = seg.segments;
			matched = tokens.map((t) => ({ token: t, entry: resolveToken(t, index.byKey) }));
			source = 'segmented';
		} else {
			tokens = [directMatch.lemma];
			matched = [{ token: directMatch.lemma, entry: directMatch }];
			source = 'direct';
		}
	} else {
		tokens = splitInput(raw);
		if (tokens.length === 1 && !directMatch) {
			const seg = segmentBest(tokens[0].toLowerCase(), index.segmentationKeys, index.byKey);
			if (seg.segments.length >= 1) {
				tokens = seg.segments;
				unresolved = seg.unresolved;
				source = 'segmented';
			}
		} else if (looksCompound) {
			source = 'split';
		}
		matched = tokens.map((t) => {
			const entry = resolveToken(t, index.byKey);
			if (!entry) unresolved.push(t);
			return { token: t, entry };
		});
		unresolved = [...new Set(unresolved)];
	}

	let tree = buildTree(matched, warnings);
	if (fusedRoot) {
		// Wrap the structural tree in a "fused" root that displays the lexicalised
		// surface form. The inner tree carries the i-/nukar structure.
		const frame = tree.frame ? cloneFrame(tree.frame) : null;
		const fusedLeaf: CompositionNode = {
			surface: fusedRoot.lemma,
			kind: 'head',
			entry: fusedRoot,
			frame,
			isLeaf: true
		};
		tree = {
			surface: fusedRoot.lemma,
			kind: 'fused',
			entry: null,
			frame,
			affix: fusedLeaf,
			body: tree,
			isLeaf: false
		};
	}
	const matchedEntry = directMatch ?? null;
	const matchedAnyEntry = matched.some((m) => m.entry !== null);
	const unseen =
		!directMatch && !matchedAnyEntry; // nothing recognised at all

	return {
		input,
		matchedEntry,
		tokens,
		unresolved,
		warnings,
		tree,
		source,
		unseen
	};
}

export function findOtherUses(
	entry: Entry,
	allEntries: Entry[],
	limit = 20
): Entry[] {
	const target = entry.lemma.replace(/^[-=]+|[-=]+$/g, '').toLowerCase();
	if (!target) return [];
	const out: Entry[] = [];
	for (const candidate of allEntries) {
		if (candidate.id === entry.id) continue;
		const lemma = candidate.lemma.replace(/^[-=]+|[-=]+$/g, '').toLowerCase();
		if (lemma === target) continue;
		if (lemma.length <= target.length) continue;
		if (
			lemma.includes(`-${target}`) ||
			lemma.includes(`${target}-`) ||
			lemma.startsWith(`${target}`) ||
			lemma.endsWith(`${target}`) ||
			lemma.includes(target)
		) {
			out.push(candidate);
			if (out.length >= limit) break;
		}
	}
	return out;
}
