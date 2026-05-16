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

/**
 * The arity delta a single morpheme contributes to the running frame.
 *
 * Two sources stack:
 *
 *  - A verb/noun root introduces its own ``base_frame``, so it contributes
 *    +N where N is the external arity of that frame (e.g. nukar = +2,
 *    an = +1, cepkoyki = +1 because the patient is incorporated).
 *  - Each rule on the entry shifts arity by +1 (``add_slot`` to external
 *    slot), −1 (``remove_slot`` / ``internalize`` of an external slot),
 *    or 0 otherwise.
 *
 * Returns ``null`` when the entry has neither a base_frame nor rules — so
 * pure-data nouns without their own frame contribute no chip.
 */
export function valencyDelta(entry: Entry): number | null {
	if (!entry.base_frame && !entry.rules.length) return null;
	let delta = 0;
	if (entry.base_frame) {
		for (const slot of entry.base_frame.slots) {
			if (slot.realization === 'external') delta += 1;
		}
	}
	for (const rule of entry.rules) {
		switch (rule.operation) {
			case 'add_slot':
				if (!rule.realization || rule.realization === 'external') delta += 1;
				break;
			case 'remove_slot':
				delta -= 1;
				break;
			case 'internalize':
				delta -= 1;
				break;
			default:
				break;
		}
	}
	return delta;
}

/**
 * Heuristic arity for entries that carry neither a ``base_frame`` nor
 * explicit ``rules`` — read off from the part-of-speech alone.
 *
 *  - Verbs: vi=+1, vt=+2, vd=+3, vc=0 (impersonal). Generic ``v`` stays
 *    unknown.
 *  - Common nouns and proper nouns: −1 (the canonical incorporable, e.g.
 *    cep in cep-koyki saturates one external slot).
 *  - Possessed-noun classes (``nl`` locative noun, ``nmlz`` formal noun): 0
 *    — the possessor is part of the noun's own frame, not a host's.
 *  - Person clitics / personal affixes: −1 by default; ``eci=`` is −2
 *    (encodes 2pl agent + 1sg object simultaneously).
 *  - Everything else (adverbials, particles, conjunctions, …): 0.
 *
 * Returns ``null`` when the category gives no usable signal.
 */
const NOUN_INCORP_CATEGORIES = new Set(['n', 'propn']);
const NEUTRAL_CATEGORIES = new Set([
	'adv',
	'adn',
	'advp',
	'auxv',
	'cconj',
	'colloc',
	'cop',
	'det',
	'idiom',
	'int',
	'intj',
	'nl',
	'nmlz',
	'num',
	'padv',
	'parti',
	'post',
	'postp',
	'punct',
	'rel',
	'sconj',
	'sfp',
	'sfx',
	'pfx',
	'root'
]);
const PERSON_CATEGORIES = new Set(['pers', 'pron']);

function isPersonClitic(entry: Entry): boolean {
	if (!PERSON_CATEGORIES.has(entry.category)) return false;
	return entry.morph_type === 'clitic' || entry.lemma.includes('=');
}

export function inferredValencyDelta(entry: Entry): number | null {
	switch (entry.category) {
		case 'vi':
			return 1;
		case 'vt':
			return 2;
		case 'vd':
			return 3;
		case 'vc':
			return 0;
	}
	if (NOUN_INCORP_CATEGORIES.has(entry.category)) {
		// Common/proper nouns are canonically incorporable: as a morpheme
		// building block they saturate one external slot of their host.
		return -1;
	}
	if (isPersonClitic(entry)) {
		// eci= uniquely fuses 2pl agent + 1sg object → saturates two slots.
		const bare = entry.lemma.replace(/^[-=]+|[-=]+$/g, '');
		if (bare === 'eci') return -2;
		return -1;
	}
	if (NEUTRAL_CATEGORIES.has(entry.category)) return 0;
	return null;
}

/**
 * Effective delta for UI/sort purposes: explicit when available, otherwise
 * the category-based inference. Callers that need to distinguish the two
 * (e.g. to render the inferred value in a softer style) can compare against
 * ``valencyDelta`` directly.
 */
export function effectiveValencyDelta(entry: Entry): number | null {
	const explicit = valencyDelta(entry);
	if (explicit !== null) return explicit;
	return inferredValencyDelta(entry);
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

	// Phonotactically, only `p` and `n` (the nominaliser / definitiser) are
	// plausible as a 1-character Ainu morpheme. Any other 1-character match
	// (a, e, i, k, t, …) is almost certainly a segmentation artefact, so we
	// penalise such segments heavily — heavier than leaving the character
	// unresolved — to push the search toward longer, real-morpheme matches
	// (askepet → aske + pet, not aske + ke + t).
	const SINGLE_CHAR_PLAUSIBLE = new Set(['p', 'n']);
	const scoreOf = (p: Parse): number => {
		// Big bonus for a head with a base_frame — pins the analysis onto a
		// real verb root. Then reward recognised characters, then penalise
		// leftover characters.
		const headBonus = p.hasHead ? 1000 : 0;
		const unresolvedChars = p.unresolved.reduce((sum, u) => sum + u.length, 0);
		let dubiousSingles = 0;
		for (const seg of p.segments) {
			const bare = seg.replace(/^[-=]+|[-=]+$/g, '');
			if (bare.length === 1 && !SINGLE_CHAR_PLAUSIBLE.has(bare)) dubiousSingles += 1;
		}
		return (
			headBonus +
			p.recognised * 10 -
			unresolvedChars * 5 -
			p.segments.length -
			dubiousSingles * 100
		);
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

	// Pick the head as the RIGHTMOST entry that meets the criteria, so in
	// compounds with multiple verb roots (tuyma + siram + suypa) the
	// outermost / final verb (suypa) is the head and everything to its left
	// wraps as inner modifiers. Walking right-to-left lets us prefer:
	//   1. a non-affix, non-clitic entry with an explicit base_frame
	//   2. otherwise any non-affix, non-clitic lexical entry (so productive
	//      affixes like e- / ko- don't accidentally become "head")
	//   3. otherwise the rightmost entry with a base_frame (incl. affixes)
	//   4. otherwise any rightmost matched entry
	let headIndex = -1;
	const isAffixOrClitic = (e: Entry | null | undefined) =>
		e?.morph_type === 'prefix' || e?.morph_type === 'suffix' || e?.morph_type === 'clitic';
	for (let i = matched.length - 1; i >= 0; i -= 1) {
		const e = matched[i].entry;
		if (e?.base_frame && !isAffixOrClitic(e)) {
			headIndex = i;
			break;
		}
	}
	if (headIndex === -1) {
		for (let i = matched.length - 1; i >= 0; i -= 1) {
			const e = matched[i].entry;
			if (e && !isAffixOrClitic(e)) {
				headIndex = i;
				break;
			}
		}
	}
	if (headIndex === -1) {
		for (let i = matched.length - 1; i >= 0; i -= 1) {
			if (matched[i].entry?.base_frame) {
				headIndex = i;
				break;
			}
		}
	}
	if (headIndex === -1) {
		for (let i = matched.length - 1; i >= 0; i -= 1) {
			if (matched[i].entry) {
				headIndex = i;
				break;
			}
		}
	}
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

	// Productive prefixes / suffixes (morph_type === 'prefix' | 'suffix') are
	// applied OUTERMOST; non-affix lexical material (incorporated nouns,
	// deverbal nominalisers like -kur, -pe) binds tightly to the head and
	// is applied innermost. This gives the bracketing (cep-koyki)-kur for
	// cepkoykikur — kur wraps the cep+koyki incorporation core — while
	// si-(nukar-e) still works because both si- and -e are productive
	// affixes and -e (closer to head) still applies before si-.
	const isClitic = (m: { entry: Entry | null }) => m.entry?.morph_type === 'clitic';
	const isAffixPart = (m: { entry: Entry | null }) =>
		m.entry?.morph_type === 'prefix' || m.entry?.morph_type === 'suffix';

	// Pass 1: lexical (non-affix) elements on the prefix side (innermost,
	// closest to head first → right-to-left walk). Clitics are deferred to
	// Pass 5 (outermost scope) and skipped here even though they're not
	// strictly "affixes" in the morph_type sense.
	for (let i = headIndex - 1; i >= 0; i -= 1) {
		if (isAffixPart(matched[i])) continue;
		if (isClitic(matched[i])) continue;
		node = wrapAffix(node, matched[i], 'prefix', warnings);
	}

	// Pass 2: lexical (non-affix) elements on the suffix side (closest to
	// head first → left-to-right walk).
	for (let i = headIndex + 1; i < matched.length; i += 1) {
		if (isAffixPart(matched[i])) continue;
		if (isClitic(matched[i])) continue;
		node = wrapAffix(node, matched[i], 'suffix', warnings);
	}

	// Pass 3: productive suffix affixes (still inner-to-outer in the suffix
	// direction so -e applies before -yar, and -e creates a slot that an
	// outer si- can later see).
	for (let i = headIndex + 1; i < matched.length; i += 1) {
		if (!isAffixPart(matched[i])) continue;
		node = wrapAffix(node, matched[i], 'suffix', warnings);
	}

	// Pass 4: productive prefix affixes (closest to head first, working
	// outward, so ko- applies before yay-, and si- still applies after
	// -e has run in Pass 3). Clitics are deferred to Pass 5 because they
	// have the lowest scope priority — personal-affix clitics (a=, =an,
	// ku=, e=, eci=) are syntactic and bind outside every derivational
	// affix.
	for (let i = headIndex - 1; i >= 0; i -= 1) {
		if (!isAffixPart(matched[i])) continue;
		if (isClitic(matched[i])) continue;
		node = wrapAffix(node, matched[i], 'prefix', warnings);
	}

	// Pass 5: clitics on either side, outermost. Pre-head clitics wrap
	// right-to-left (closest to head first); post-head clitics wrap
	// left-to-right.
	for (let i = headIndex + 1; i < matched.length; i += 1) {
		if (!isClitic(matched[i])) continue;
		node = wrapAffix(node, matched[i], 'suffix', warnings);
	}
	for (let i = headIndex - 1; i >= 0; i -= 1) {
		if (!isClitic(matched[i])) continue;
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
	// Strip every directional marker AND internal hyphens from the body so
	// the wrap header reads like the concatenated lemma — e.g. the body of
	// eyaykewtumekosanniyo shows as "yaykewtumekosanniyo", not
	// "yay-kewtum-ekosanniyo", so the e- affix doesn't look detached from
	// an oddly-hyphenated rest.
	const bodyBare = body.surface.replace(/[-=]+/g, '');
	const surface = side === 'prefix' ? `${affixBare}${bodyBare}` : `${bodyBare}${affixBare}`;

	// Pick a bracket kind: productive affixes (morph_type prefix/suffix) and
	// personal-affix clitics keep the structural prefix/suffix label; other
	// non-affix lexical material is labelled either incorporation (noun
	// adjacent to a verb host) or compound (everything else).
	let wrapKind: CompositionKind = side;
	if (
		entry &&
		entry.morph_type !== 'prefix' &&
		entry.morph_type !== 'suffix' &&
		entry.morph_type !== 'clitic'
	) {
		const hostEntry =
			body.entry ?? body.body?.entry ?? body.affix?.entry ?? null;
		const hostIsVerb = (() => {
			const c = hostEntry?.category ?? '';
			return c === 'vt' || c === 'vi' || c === 'vd' || c === 'vc' || c === 'v';
		})();
		const cat = entry.category ?? '';
		const isNoun = cat === 'n' || cat === 'nl' || cat === 'nmlz' || cat === 'propn';
		wrapKind = isNoun && hostIsVerb ? 'incorporation' : 'compound';
	}

	return {
		surface,
		kind: wrapKind,
		entry: null,
		frame: nextFrame,
		affix: affixLeaf,
		body,
		side,
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
		// Trust the dictionary entry. A stable lexeme like ``kasuy`` 'help'
		// shouldn't be auto-segmented into ``ka + suy`` just because both
		// substrings happen to be in the morpheme inventory — the fact that
		// kasuy is in NINJAL / Tommy 1949 / Wiktionary as a single attested
		// form is the evidence we trust. Decomposition only happens when the
		// entry itself records a ``composition`` or ``etymology``; the
		// segmentation fallback is reserved for unknown inputs in the
		// ``else`` branch below.
		tokens = [directMatch.lemma];
		matched = [{ token: directMatch.lemma, entry: directMatch }];
		source = 'direct';
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
		// Distinguish actually-reduced compounds (surface lemma ≠ concat of
		// constituents — inkar ≠ i+nukar = inukar, payoka ≠ paye+oka) from
		// purely transparent compounds where the hyphenation is an analytical
		// convention and the surface lemma is just the concatenation of its
		// constituents (nupe = nu+pe, cepkoyki = cep+koyki). Reduced forms
		// keep the wrap-with-head-chip 'fused' treatment; transparent
		// compounds are flattened — no intermediate "cep-koyki" node, no
		// duplicated head leaf, just a single bracket directly above the
		// constituent leaves.
		const composedBare = matched
			.map((mch) => (mch.entry?.lemma ?? mch.token).replace(/^[-=]+|[-=]+$/g, ''))
			.join('');
		const lemmaBare = fusedRoot.lemma.replace(/^[-=]+|[-=]+$/g, '');
		const isReduced = composedBare !== lemmaBare;

		const frame = fusedRoot.base_frame
			? cloneFrame(fusedRoot.base_frame)
			: tree.frame
				? cloneFrame(tree.frame)
				: null;

		if (isReduced) {
			// Wrap the decomposition under a single 'fused' top node. The
			// wrap itself carries the fused entry (so the top chip is the
			// clickable handle for the whole word) — we deliberately do NOT
			// add a separate inner head leaf chip, which would just
			// duplicate the same entry at the bottom of the tree and make
			// the click target position inconsistent with non-fused words
			// where the root is at the top.
			tree = {
				surface: fusedRoot.lemma,
				kind: 'fused',
				entry: fusedRoot,
				frame,
				body: tree,
				isLeaf: false
			};
		} else if (!tree.isLeaf) {
			// Pick a bracket label based on the constituents:
			//   noun + verb  → incorporation (cep + koyki, aynu + koyki, …)
			//   prefix/suffix involved → keep the structural prefix/suffix
			//     wrapping (ukoyki = u- + koyki is prefixation, not
			//     compounding)
			//   everything else (n+n, v+v, …) → plain 'compound'
			const isAffix = (e: Entry | null | undefined) =>
				e?.morph_type === 'prefix' || e?.morph_type === 'suffix';
			const isNoun = (e: Entry | null | undefined) => {
				const c = e?.category ?? '';
				return c === 'n' || c === 'nl' || c === 'nmlz' || c === 'propn';
			};
			const isVerb = (e: Entry | null | undefined) => {
				const c = e?.category ?? '';
				return c === 'vt' || c === 'vi' || c === 'vd' || c === 'vc' || c === 'v';
			};
			const hasAffix = matched.some((m) => isAffix(m.entry));
			const newKind: CompositionKind = hasAffix
				? tree.kind
				: matched.some((m) => isNoun(m.entry)) && matched.some((m) => isVerb(m.entry))
					? 'incorporation'
					: 'compound';
			tree = { ...tree, kind: newKind, surface: fusedRoot.lemma, frame };
		}
	}
	const matchedEntry = directMatch ?? null;
	const matchedAnyEntry = matched.some((m) => m.entry !== null);
	const unseen =
		!directMatch && !matchedAnyEntry; // nothing recognised at all

	// Walk the tree and attach a matching entry to every internal wrap whose
	// surface corresponds to a known lemma. That way intermediate units like
	// `eyaykotuymasiramsuypa` inside `aeyaykotuymasiramsuypa`, or `nukare`
	// inside `sinukare`, render as clickable chips parallel to leaf chips —
	// not as flat non-interactive headers. The top-level matched entry is
	// attached unconditionally (its lemma may differ from the surface for
	// fused forms), then we resolve every deeper wrap by surface lookup.
	const resolveWrap = (n: CompositionNode | undefined): void => {
		if (!n || n.isLeaf) return;
		if (!n.entry) {
			const found = index.byKey.get(n.surface);
			if (found) n.entry = found;
		}
		resolveWrap(n.affix);
		resolveWrap(n.body);
	};
	if (matchedEntry && !tree.isLeaf && tree.entry === null) {
		tree.entry = matchedEntry;
	}
	resolveWrap(tree.affix);
	resolveWrap(tree.body);

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

// "Appears in" — return only candidates where we have *positive structural
// evidence* that this morpheme is a constituent. Two trusted sources:
//
//   1. The candidate's `composition` field explicitly references this entry
//      by id (curated truth, used for fused forms like inkar ← [i-, nukar]).
//   2. The candidate's lemma is a hyphen-/equals-marked compound and one
//      of its segments matches this morpheme's bare form.
//
// We deliberately do *not* fall back to substring matching: ‘inkar’ contains
// ‘kar’ as a substring but morphologically it is i- + nukar, so naive
// substring search would lie. If the data doesn't say so, we don't claim it.
export function findOtherUses(
	entry: Entry,
	allEntries: Entry[],
	limit = 20
): Entry[] {
	const target = entry.lemma.replace(/^[-=]+|[-=]+$/g, '').toLowerCase();
	if (!target) return [];
	const out: Entry[] = [];
	const seen = new Set<string>();

	for (const candidate of allEntries) {
		if (candidate.id === entry.id) continue;
		if (seen.has(candidate.id)) continue;

		// Source 1: curated composition reference.
		if (candidate.composition?.length && candidate.composition.includes(entry.id)) {
			out.push(candidate);
			seen.add(candidate.id);
			if (out.length >= limit) break;
			continue;
		}

		// Source 2: lemma is an explicit hyphen/equals-marked compound and
		// one of its segments is this morpheme's bare form.
		const lemma = candidate.lemma.toLowerCase();
		if (!/[-=]/.test(lemma)) continue;
		const segments = lemma
			.split(/[-=]/)
			.map((s) => s.trim())
			.filter(Boolean);
		if (segments.length < 2) continue;
		if (!segments.includes(target)) continue;

		out.push(candidate);
		seen.add(candidate.id);
		if (out.length >= limit) break;
	}
	return out;
}
