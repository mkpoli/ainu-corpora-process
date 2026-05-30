<script lang="ts">
	import * as m from '$lib/paraglide/messages.js';
	import { getLocale } from '$lib/paraglide/runtime';
	import type { CompositionNode } from './types';
	import { effectiveValencyDelta } from './composition';
	import Etymology from './Etymology.svelte';
	import ValencyFrame from './ValencyFrame.svelte';
	import CompositionTree from './CompositionTree.svelte';

	/**
	 * Locale-aware gloss for chips. In `ja` we prefer the Japanese gloss
	 * (笑う) and fall back to English only when no JP gloss exists; in any
	 * other locale we prefer English. Returns ``null`` so callers can skip
	 * the gloss row entirely when there's nothing to show.
	 */
	function localisedGloss(entry: import('./types').Entry | null | undefined): string | null {
		if (!entry) return null;
		const locale = getLocale();
		if (locale === 'ja') return entry.glosses_jp?.[0] ?? entry.glosses_en?.[0] ?? null;
		return entry.glosses_en?.[0] ?? entry.glosses_jp?.[0] ?? null;
	}

	const KIND_LABEL: Record<string, () => string> = {
		head: () => m.kind_head(),
		prefix: () => m.kind_prefix(),
		suffix: () => m.kind_suffix(),
		standalone: () => m.kind_standalone(),
		unknown: () => m.kind_unknown(),
		fused: () => m.kind_fused(),
		compound: () => m.kind_compound(),
		incorporation: () => m.kind_incorporation(),
		lexeme: () => m.kind_lexeme()
	};

	// Pick a colour scheme for a chip based on the morpheme's *grammatical
	// category*, so the UI consistently signals what kind of morpheme each
	// chip is — red/accent for verb roots, green/leaf for nouns, blue/affix
	// for prefixes and suffixes — instead of leaking the structural role
	// (head vs prefix-wrap vs suffix-wrap) into the colour.
	function chipCategoryClass(entry: import('./types').Entry | null | undefined): string {
		if (!entry) return 'border-rule bg-paper text-ink/60 border-dashed';
		const cat = entry.category;
		if (cat === 'vt' || cat === 'vi' || cat === 'vd' || cat === 'vc' || cat === 'v') {
			return 'border-accent/60 bg-accent-soft text-accent';
		}
		if (cat === 'n' || cat === 'nl' || cat === 'nmlz' || cat === 'propn') {
			return 'border-leaf/60 bg-leaf-soft text-leaf';
		}
		if (cat === 'pfx' || entry.morph_type === 'prefix') {
			return 'border-affix/60 bg-affix-soft text-affix';
		}
		if (cat === 'sfx' || entry.morph_type === 'suffix') {
			return 'border-affix/60 bg-affix-soft text-affix';
		}
		return 'border-rule bg-paper';
	}

	import type { Entry } from './types';

	let {
		node,
		selectedId,
		depth = 0,
		onSelect,
		subtrees = {},
		expanded = new Set<string>(),
		onToggleExpand,
		entryById = {},
		ancestors = new Set<string>(),
		matchedEntryId = null,
		skipRootChip = false
	}: {
		node: CompositionNode;
		selectedId: string | null;
		depth?: number;
		onSelect: (entryId: string) => void;
		subtrees?: Record<string, CompositionNode>;
		expanded?: Set<string>;
		onToggleExpand?: (entryId: string) => void;
		entryById?: Record<string, Entry>;
		ancestors?: Set<string>;
		/** The entry the user originally queried. Its own leaf doesn't get
		 *  the "..." expand affordance — the top-level Etymology block under
		 *  the tree already covers the head's derivation. */
		matchedEntryId?: string | null;
		/** When this sub-tree is rendered directly under a leaf's "…" expand,
		 *  the leaf chip already shows the wrap's matched entry — skip the
		 *  redundant root chip/header and start with the bracket label. */
		skipRootChip?: boolean;
	} = $props();

	const expandable = $derived.by(() => {
		if (!node.entry) return false;
		// Don't offer to expand the same node we're already inside a sub-tree
		// of — that would loop forever.
		if (ancestors.has(node.entry.id)) return false;
		// Don't offer to expand the queried entry's own leaf — its derivation
		// is already shown at the top level of the Composition section.
		if (matchedEntryId && node.entry.id === matchedEntryId) return false;
		const hasSub = subtrees[node.entry.id] !== undefined;
		const entry = entryById[node.entry.id] ?? node.entry;
		const hasEtym = entry?.etymology != null;
		// Sub-tree from composition OR an etymology block to reveal.
		return hasSub || hasEtym;
	});

	const isExpanded = $derived(node.entry ? expanded.has(node.entry.id) : false);

	const childAncestors = $derived.by(() => {
		if (!node.entry) return ancestors;
		const next = new Set(ancestors);
		next.add(node.entry.id);
		return next;
	});

	// Legacy structural-kind → colour map (only used as a fallback when an
	// entry has no category to colour by).
	const KIND_STYLE: Record<string, string> = {
		head: 'border-accent/60 bg-accent-soft text-accent',
		prefix: 'border-affix/60 bg-affix-soft text-affix',
		suffix: 'border-affix/60 bg-affix-soft text-affix',
		standalone: 'border-leaf/60 bg-leaf-soft text-leaf',
		unknown: 'border-rule bg-paper text-ink/60 border-dashed',
		fused: 'border-accent/60 bg-accent-soft text-accent',
		compound: 'border-rule bg-paper text-ink/85',
		incorporation: 'border-rule bg-paper text-ink/85',
		lexeme: 'border-rule bg-paper text-ink/85'
	};

	// Pure leaf-vs-internal decision: internal wraps now also carry an
	// optional `entry` (set on the tree root so the whole-word chip is
	// clickable), but they must still render as wraps with children, not as
	// flat leaf buttons.
	const isLeaf = $derived(node.isLeaf);
	const isSelected = $derived(node.entry !== null && node.entry.id === selectedId);
	// Prefer the explicit `side` field (records which side of the host the
	// affix sits on); fall back to the structural kind for legacy nodes.
	const sideIsPrefix = $derived(node.side ? node.side === 'prefix' : node.kind === 'prefix');

	function handleClick() {
		if (node.entry) onSelect(node.entry.id);
	}

	function handleToggle(event: MouseEvent) {
		event.stopPropagation();
		if (node.entry && onToggleExpand) onToggleExpand(node.entry.id);
	}

	/**
	 * Pick a short label to render under the lemma. The seed marks most
	 * free-standing words as ``morph_type=root`` which is misleading on a
	 * chip — "root" reads as "this isn't a word, just a bound morpheme",
	 * whereas these chips often represent the whole word being inspected.
	 *
	 * Rule:
	 *   - For affixes / clitics, show the structural role (prefix / suffix /
	 *     clitic) — that's the informative bit.
	 *   - For everything else (incl. ``root``, ``stem``, ``particle``), show
	 *     the grammatical category instead (vt, vi, n, pron, advp, …).
	 */
	function chipRoleLabel(entry: Entry | null | undefined): string | null {
		if (!entry) return null;
		const mt = entry.morph_type;
		if (mt === 'prefix' || mt === 'suffix' || mt === 'clitic') return mt;
		return entry.category || mt || null;
	}

	// The affix-flatten experiment that collapsed consecutive same-side
	// wraps into a single row was reverted: it preserved surface order at
	// the cost of losing each wrap's binary bracket — i.e. the structural
	// information about *which* affix scoped over which. Keep the tree
	// strictly binary so each level shows exactly one wrap.
</script>

<div class="flex flex-col items-center gap-3">
	{#if isLeaf}
		<button
			type="button"
			onclick={handleClick}
			disabled={!node.entry}
			class="group flex min-w-[7rem] flex-col items-center gap-1 rounded-2xl border px-4 py-2 shadow-sm transition disabled:cursor-default disabled:opacity-70
				{node.entry ? chipCategoryClass(node.entry) : KIND_STYLE[node.kind] ?? 'border-rule bg-paper'}
				{isSelected ? 'ring-2 ring-accent ring-offset-2 ring-offset-paper' : 'hover:-translate-y-0.5 hover:shadow-md'}"
		>
			<span class="font-mono text-base leading-tight">{node.entry?.lemma ?? node.surface}</span>
			{#if localisedGloss(node.entry)}
				<span class="text-xs italic opacity-80">{localisedGloss(node.entry)}</span>
			{:else if node.kind === 'unknown'}
				<span class="text-xs italic opacity-80">{m.kind_unknown()}</span>
			{/if}
			{#if node.entry}
				{@const role = chipRoleLabel(node.entry)}
				{#if role}
					<span class="text-[10px] uppercase tracking-wider opacity-70">{role}</span>
				{/if}
				{@const delta = effectiveValencyDelta(node.entry)}
				{#if delta !== null && delta !== 0}
					<span
						class="font-mono text-[10px] font-semibold opacity-75"
						title="arity change applied by this morpheme"
					>
						{delta > 0 ? `+${delta}` : delta}
					</span>
				{/if}
			{/if}
		</button>

		{#if expandable && node.entry}
			{#if isExpanded}
				{@const subEntry = entryById[node.entry.id] ?? node.entry}
				{@const sub = subtrees[node.entry.id]}
				<div class="flex flex-col items-center">
					<span class="h-2 w-px bg-rule"></span>
					<button
						type="button"
						onclick={handleToggle}
						aria-label="collapse derivations"
						class="rounded-full bg-paper px-2 py-0.5 font-mono text-[10px] text-ink/60 ring-1 ring-rule transition hover:bg-accent-soft hover:text-accent hover:ring-accent/40"
					>
						−
					</button>
					<span class="h-2 w-px bg-rule"></span>
				</div>
				<div class="flex flex-col items-center gap-2">
					{#if sub}
						<CompositionTree
							node={sub}
							{selectedId}
							depth={depth + 1}
							{onSelect}
							{subtrees}
							{expanded}
							{onToggleExpand}
							{entryById}
							ancestors={childAncestors}
							{matchedEntryId}
							skipRootChip={!sub.isLeaf && sub.entry?.id === node.entry.id}
						/>
					{/if}
					{#if subEntry?.etymology}
						<Etymology entry={subEntry} {entryById} />
					{/if}
				</div>
			{:else}
				<button
					type="button"
					onclick={handleToggle}
					aria-label="expand further derivations"
					title="expand further derivations"
					class="mt-1 rounded-full bg-paper px-2 py-0.5 font-mono text-[10px] text-ink/55 ring-1 ring-rule transition hover:bg-accent-soft hover:text-accent hover:ring-accent/40"
				>
					…
				</button>
			{/if}
		{/if}
	{:else}
		<!-- Internal node: surface header with the effective valency, then the
		     two-child bracket below. When the wrap carries an `entry`
		     (notably the tree root — the whole-word entry), the header is
		     rendered as a clickable chip so the side panel can show its
		     details, mirroring the way leaf chips behave. -->
		{#if skipRootChip}
			<!-- The parent already shows the chip for this wrap; just drop
			     straight into the bracket label + children. -->
		{:else if node.entry}
			<button
				type="button"
				onclick={handleClick}
				class="flex flex-col items-center gap-1 rounded-2xl border px-3 py-1.5 shadow-sm transition
					{chipCategoryClass(node.entry)}
					{isSelected ? 'ring-2 ring-accent ring-offset-2 ring-offset-paper' : 'hover:-translate-y-0.5 hover:shadow-md'}"
				title={`${node.kind} composition — click to inspect`}
			>
				<span class="font-mono text-base leading-tight">{node.entry.lemma}</span>
				{#if localisedGloss(node.entry)}
					<span class="text-xs italic opacity-80">{localisedGloss(node.entry)}</span>
				{/if}
				{#if node.entry}
					{@const role = chipRoleLabel(node.entry)}
					{#if role}
						<span class="text-[10px] uppercase tracking-wider opacity-70">{role}</span>
					{/if}
					{@const delta = effectiveValencyDelta(node.entry)}
					{#if delta !== null && delta !== 0}
						<span
							class="font-mono text-[10px] font-semibold opacity-75"
							title="arity change applied by this morpheme"
						>
							{delta > 0 ? `+${delta}` : delta}
						</span>
					{/if}
				{/if}
			</button>
		{:else}
			<div
				class="flex flex-col items-center gap-1 rounded-2xl border border-rule bg-paper/70 px-3 py-1.5"
				title={`${node.kind} composition`}
			>
				<span class="font-mono text-sm text-ink/80">{node.surface}</span>
				{#if node.frame}
					<ValencyFrame frame={node.frame} compact />
				{/if}
			</div>
		{/if}

		<!-- Connector + bracket label -->
		<div class="flex flex-col items-center">
			<span class="h-3 w-px bg-rule"></span>
			<span class="rounded bg-paper px-1.5 py-[1px] font-mono text-[10px] uppercase tracking-widest text-ink/60 ring-1 ring-rule">
				{KIND_LABEL[node.kind]?.() ?? node.kind}
			</span>
			<span class="h-3 w-px bg-rule"></span>
		</div>

		<div class="flex flex-nowrap items-start justify-center gap-6">
			{#if sideIsPrefix}
				{#if node.affix}
					<CompositionTree
					node={node.affix}
					{selectedId}
					depth={depth + 1}
					{onSelect}
					{subtrees}
					{expanded}
					{onToggleExpand}
					{entryById}
					ancestors={childAncestors}
					{matchedEntryId}
				/>
				{/if}
				{#if node.body}
					<CompositionTree
					node={node.body}
					{selectedId}
					depth={depth + 1}
					{onSelect}
					{subtrees}
					{expanded}
					{onToggleExpand}
					{entryById}
					ancestors={childAncestors}
					{matchedEntryId}
				/>
				{/if}
			{:else}
				{#if node.body}
					<CompositionTree
					node={node.body}
					{selectedId}
					depth={depth + 1}
					{onSelect}
					{subtrees}
					{expanded}
					{onToggleExpand}
					{entryById}
					ancestors={childAncestors}
					{matchedEntryId}
				/>
				{/if}
				{#if node.affix}
					<CompositionTree
					node={node.affix}
					{selectedId}
					depth={depth + 1}
					{onSelect}
					{subtrees}
					{expanded}
					{onToggleExpand}
					{entryById}
					ancestors={childAncestors}
					{matchedEntryId}
				/>
				{/if}
			{/if}
		</div>
	{/if}
</div>
