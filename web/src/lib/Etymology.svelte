<script lang="ts">
	import * as m from '$lib/paraglide/messages.js';
	import { getLocale } from '$lib/paraglide/runtime';
	import { sourceLabel, sourceUrl } from './sources';
	import { effectiveValencyDelta } from './composition';
	import type { Entry, EtymologyPart } from './types';

	function localisedPartGloss(part: EtymologyPart): string | null {
		const locale = getLocale();
		if (locale === 'ja') return part.gloss_jp ?? part.gloss_en ?? null;
		return part.gloss_en ?? part.gloss_jp ?? null;
	}

	let {
		entry,
		entryById = {}
	}: { entry: Entry | null; entryById?: Record<string, Entry> } = $props();

	// Look up the full Entry for a part by its `id` if curated, otherwise
	// by lemma. We use this so the chip's valency badge stays in sync with
	// what the same morpheme shows on its own page (e.g. ko- = +1 because
	// of its add_slot rule, even if the etymology JSON doesn't restate
	// `valency: 1`).
	function partEntry(part: EtymologyPart): Entry | null {
		if (part.id && entryById[part.id]) return entryById[part.id];
		// Fall back to a lemma lookup across the index.
		for (const e of Object.values(entryById)) {
			if (e.lemma === part.lemma) return e;
		}
		return null;
	}

	const etymology = $derived(entry?.etymology ?? null);
	const sourceHref = $derived.by(() => {
		if (!entry || !etymology?.source) return null;
		return sourceUrl(etymology.source, entry.lemma);
	});

	function formatValency(v: number | undefined): string | null {
		if (v === undefined || v === 0) return null;
		return v > 0 ? `+${v}` : String(v);
	}

	/** Infer a default valency from a part's category when the seed didn't
	 * give one explicitly: verb roots contribute +N for arity N (vi=+1,
	 * vt=+2, vd=+3); noun roots are canonically incorporable and contribute
	 * −1; applicative prefixes contribute +1; everything else is silent.
	 *
	 * Prefers (a) an explicit `valency` on the etymology part, (b) the
	 * effective valency delta of the matched Entry (so ko-/e-/o- pick up
	 * their +1 from the add_slot rule), and only then falls back to the
	 * category-based heuristic.
	 */
	function partValency(part: EtymologyPart): number | undefined {
		if (part.valency !== undefined) return part.valency;
		const e = partEntry(part);
		if (e) {
			const delta = effectiveValencyDelta(e);
			if (delta !== null) return delta;
		}
		switch (part.category) {
			case 'vi':
				return 1;
			case 'vt':
				return 2;
			case 'vd':
				return 3;
			case 'vc':
				return 0;
			case 'n':
			case 'nl':
			case 'nmlz':
			case 'propn':
				return -1;
		}
		return undefined;
	}

	// Colour etymology chips by morpheme category, matching the
	// CompositionTree leaves so blue = affix, red = verb root, green =
	// noun root, etc.
	function chipCategoryClass(part: EtymologyPart): string {
		const cat = part.category ?? '';
		if (cat === 'vt' || cat === 'vi' || cat === 'vd' || cat === 'vc' || cat === 'v') {
			return 'border-accent/60 bg-accent-soft text-accent';
		}
		if (cat === 'n' || cat === 'nl' || cat === 'nmlz' || cat === 'propn') {
			return 'border-leaf/60 bg-leaf-soft text-leaf';
		}
		if (cat === 'pfx' || part.morph_type === 'prefix') {
			return 'border-affix/60 bg-affix-soft text-affix';
		}
		if (cat === 'sfx' || part.morph_type === 'suffix') {
			return 'border-affix/60 bg-affix-soft text-affix';
		}
		return 'border-rule bg-paper';
	}

	// Localised, short labels for derivational processes — the explainer
	// page at /processes documents each one in detail.
	const PROCESS_LABEL: Record<string, () => string> = {
		zero_derivation: () => m.process_zero_derivation(),
		reduplication: () => m.process_reduplication(),
		affixation: () => m.process_affixation(),
		grammaticalization: () => m.process_grammaticalization()
	};

	function processLabel(key: string | undefined): string {
		if (!key) return '';
		return PROCESS_LABEL[key]?.() ?? key;
	}

	function processHref(key: string | undefined): string | null {
		if (!key) return null;
		if (PROCESS_LABEL[key]) return `/processes#${encodeURIComponent(key)}`;
		return null;
	}

	function partRoleLabel(part: EtymologyPart): string {
		const mt = part.morph_type;
		if (mt === 'prefix' || mt === 'suffix' || mt === 'clitic') return mt;
		return part.category || mt || '';
	}

	/** A chip in the etymology chain duplicates the leaf chip rendered above the
	 *  etymology frame when both its lemma and category match the entry. We
	 *  skip such chips (and any orphan process arrow that would lead to them)
	 *  so the user doesn't see the same morpheme twice in a row. Soft match on
	 *  category: if the part doesn't carry one, we still dedup on lemma alone.
	 */
	function chipMatchesEntry(part: EtymologyPart | undefined, e: Entry | null): boolean {
		if (!part || !e) return false;
		if (part.lemma !== e.lemma) return false;
		if (part.category && part.category !== e.category) return false;
		return true;
	}

	function chainHasContent(part: EtymologyPart | undefined, e: Entry | null): boolean {
		if (!part) return false;
		if (!chipMatchesEntry(part, e)) return true;
		return chainHasContent(part.derived_from, e);
	}

	// Cap recursive nested-etymology rendering. Most Ainu derivations are
	// 2-3 morphemes deep; capping at 2 keeps multi-step chains
	// (koyki → ko- + (i- + ki)) readable as a tree without ballooning into
	// a tall vertical column for long polysynthetic words like
	// yaykosiramsuypa or ewkoysoytak.
	const NESTED_ETYM_DEPTH = 2;

	/** Return the matched Entry's own etymology when (a) the matched Entry
	 *  isn't the page's own entry (we don't want to render an entry's
	 *  etymology inside itself) and (b) the etymology actually has parts
	 *  to display. Otherwise returns null. */
	function nestedEtymologyFor(part: EtymologyPart): { parts: EtymologyPart[]; note?: string } | null {
		const e = partEntry(part);
		if (!e || e === entry) return null;
		const etym = e.etymology;
		if (!etym?.parts?.length) return null;
		return etym;
	}
</script>

{#snippet partChip(part: EtymologyPart)}
	<a
		href={`/?q=${encodeURIComponent(part.lemma)}`}
		class="group flex min-w-[7rem] flex-col items-center gap-1 rounded-2xl border px-4 py-2 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md
			{chipCategoryClass(part)}"
	>
		<span class="font-mono text-base leading-tight">{part.lemma}</span>
		{#if localisedPartGloss(part)}
			<span class="text-xs italic opacity-80">{localisedPartGloss(part)}</span>
		{/if}
		{#if partRoleLabel(part)}
			<span class="text-[10px] uppercase tracking-wider opacity-70">{partRoleLabel(part)}</span>
		{/if}
		{#if formatValency(partValency(part))}
			<span class="font-mono text-[10px] font-semibold opacity-75">{formatValency(partValency(part))}</span>
		{/if}
	</a>
{/snippet}

{#snippet partColumn(part: EtymologyPart, skipChip = false, depth = NESTED_ETYM_DEPTH)}
	<div class="flex flex-col items-center gap-1">
		{#if !skipChip}
			{@render partChip(part)}
		{/if}
		{#if part.derived_from && chainHasContent(part.derived_from, entry)}
			{@const skipDF = chipMatchesEntry(part.derived_from, entry)}
			<!-- Vertical derivation connector + label inside the part column.
			     The label names the process only — the underlying chip already
			     carries the +N valency badge, so we don't duplicate the delta
			     here. Details are on /processes. -->
			{#if !skipChip}
				<span class="h-3 w-px bg-rule"></span>
			{/if}
			{@const href = processHref(part.process)}
			{@const label = processLabel(part.process)}
			{#if href}
				<a
					{href}
					class="rounded bg-paper px-1.5 py-[1px] font-mono text-[10px] uppercase tracking-widest text-ink/65 ring-1 ring-rule transition hover:bg-accent-soft hover:text-accent hover:ring-accent/40"
					title="see /processes for details"
				>
					{label}
				</a>
			{:else}
				<span
					class="rounded bg-paper px-1.5 py-[1px] font-mono text-[10px] uppercase tracking-widest text-ink/55 ring-1 ring-rule"
				>
					{label}
				</span>
			{/if}
			<span class="h-3 w-px bg-rule"></span>
			{@render partColumn(part.derived_from, skipDF, depth)}
		{:else if depth > 0 && !skipChip}
			{@const nested = nestedEtymologyFor(part)}
			{#if nested}
				<!-- The matched morpheme has its own etymology. Expand it
				     inline as a small nested frame so multi-step chains
				     (koyki ← ko- + iki ← ko- + i- + ki) read in one view.
				     Depth-limited to avoid runaway descent on data cycles. -->
				<span class="mt-1 h-3 w-px bg-rule"></span>
				<div class="rounded-xl border border-dashed border-ink/25 bg-white/40 px-3 pt-1 pb-2">
					<div class="mb-1 flex flex-col items-center">
						<span class="rounded bg-paper px-1 py-[1px] font-mono text-[9px] uppercase tracking-widest text-ink/55 ring-1 ring-rule">
							{m.kind_etymology()}
						</span>
					</div>
					<div class="flex flex-wrap items-start justify-center gap-3">
						{#each nested.parts as subPart}
							{@render partColumn(subPart, false, depth - 1)}
						{/each}
					</div>
					{#if nested.note}
						<p class="mt-2 text-center text-[10px] italic text-ink/55">{nested.note}</p>
					{/if}
				</div>
			{/if}
		{/if}
	</div>
{/snippet}

{#if entry && etymology}
	<!-- Connector from the synchronic tree above DOWN INTO the etymology
	     frame. The line crosses the dashed border, so the etymology reads
	     as a continuation of the same tree (different "kind" of bracket). -->
	<div class="-mb-3 flex flex-col items-center">
		<span class="h-3 w-px bg-rule"></span>
	</div>
	<section class="rounded-2xl border-2 border-dashed border-ink/40 bg-white/70 p-4 pt-2">
		<!-- The "etymology" bracket label sits at the top, immediately under
		     the inbound connector. -->
		<div class="flex flex-col items-center">
			<span
				class="rounded bg-paper px-1.5 py-[1px] font-mono text-[10px] uppercase tracking-widest text-ink/60 ring-1 ring-rule"
			>
				{m.kind_etymology()}
			</span>
			<span class="h-3 w-px bg-rule"></span>
		</div>

		{#if etymology.parts && etymology.parts.length}
			<div class="flex flex-wrap items-start justify-center gap-4">
				{#each etymology.parts as part}
					{#if chainHasContent(part, entry)}
						{@render partColumn(part, chipMatchesEntry(part, entry))}
					{/if}
				{/each}
			</div>
		{/if}

		{#if etymology.note}
			<p class="mt-3 text-center text-[11px] italic text-ink/60">{etymology.note}</p>
		{/if}

		{#if etymology.source}
			<p class="mt-2 text-right text-[10px]">
				{#if sourceHref}
					<a
						href={sourceHref}
						target={sourceHref.startsWith('/') ? undefined : '_blank'}
						rel={sourceHref.startsWith('/') ? undefined : 'noopener noreferrer'}
						class="rounded-full bg-paper px-2 py-0.5 text-ink/65 ring-1 ring-rule transition hover:bg-accent-soft hover:text-accent hover:ring-accent/40"
					>
						{sourceLabel(etymology.source)}
					</a>
				{:else}
					<span class="rounded-full bg-paper px-2 py-0.5 text-ink/65 ring-1 ring-rule">
						{sourceLabel(etymology.source)}
					</span>
				{/if}
			</p>
		{/if}
	</section>
{/if}
