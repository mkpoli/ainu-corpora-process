<script lang="ts">
	import * as m from '$lib/paraglide/messages.js';
	import { sourceLabel, sourceUrl } from './sources';
	import type { Entry, EtymologyPart } from './types';

	let { entry }: { entry: Entry | null } = $props();

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
	 * −1; everything else is silent. */
	function partValency(part: EtymologyPart): number | undefined {
		if (part.valency !== undefined) return part.valency;
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
</script>

{#snippet partChip(part: EtymologyPart)}
	<a
		href={`/?q=${encodeURIComponent(part.lemma)}`}
		class="group flex min-w-[7rem] flex-col items-center gap-1 rounded-2xl border px-4 py-2 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md
			{chipCategoryClass(part)}"
	>
		<span class="font-mono text-base leading-tight">{part.lemma}</span>
		{#if part.gloss_en}
			<span class="text-xs italic opacity-80">{part.gloss_en}</span>
		{:else if part.gloss_jp}
			<span class="text-xs italic opacity-80">{part.gloss_jp}</span>
		{/if}
		{#if part.morph_type}
			<span class="text-[10px] uppercase tracking-wider opacity-70">{part.morph_type}</span>
		{/if}
		{#if formatValency(partValency(part))}
			<span class="font-mono text-[10px] font-semibold opacity-75">{formatValency(partValency(part))}</span>
		{/if}
	</a>
{/snippet}

{#snippet partColumn(part: EtymologyPart, skipChip = false)}
	<div class="flex flex-col items-center gap-1">
		{#if !skipChip}
			{@render partChip(part)}
		{/if}
		{#if part.derived_from}
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
			{@render partColumn(part.derived_from)}
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
					{@render partColumn(part, part.derived_from != null && part.lemma === entry.lemma)}
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
