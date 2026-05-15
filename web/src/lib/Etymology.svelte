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

	// Localised, short labels for derivational processes — the explainer
	// page at /processes documents each one in detail.
	const PROCESS_LABEL: Record<string, () => string> = {
		zero_derivation: () => m.process_zero_derivation()
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
		class="group flex min-w-[6rem] flex-col items-center gap-0.5 rounded-2xl border border-dashed border-ink/40 bg-paper px-3 py-1.5 shadow-sm transition hover:-translate-y-0.5 hover:border-accent hover:shadow-md"
	>
		<span class="font-mono text-sm">{part.lemma}</span>
		{#if part.gloss_en || part.gloss_jp}
			<span class="text-[10px] italic text-ink/60">
				{part.gloss_en ?? ''}{part.gloss_en && part.gloss_jp ? ' · ' : ''}{part.gloss_jp ?? ''}
			</span>
		{/if}
		<div class="flex items-center gap-1 text-[10px] uppercase tracking-wider text-ink/55">
			{#if part.morph_type}
				<span>{part.morph_type}</span>
			{/if}
			{#if part.category}
				<span class="font-mono">{part.category}</span>
			{/if}
			{#if formatValency(part.valency)}
				<span class="font-mono font-semibold opacity-75">{formatValency(part.valency)}</span>
			{/if}
		</div>
	</a>
{/snippet}

{#snippet partColumn(part: EtymologyPart)}
	<div class="flex flex-col items-center gap-1">
		{@render partChip(part)}
		{#if part.derived_from}
			<!-- Vertical derivation connector + label inside the part column. -->
			<span class="h-3 w-px bg-rule"></span>
			{@const href = processHref(part.process)}
			{@const label = processLabel(part.process)}
			{@const delta = formatValency(part.process_delta)}
			{#if href}
				<a
					{href}
					class="rounded bg-paper px-1.5 py-[1px] font-mono text-[10px] uppercase tracking-widest text-ink/65 ring-1 ring-rule transition hover:bg-accent-soft hover:text-accent hover:ring-accent/40"
					title="see /processes for details"
				>
					{label}{delta ? ` ${delta}` : ''}
				</a>
			{:else}
				<span
					class="rounded bg-paper px-1.5 py-[1px] font-mono text-[10px] uppercase tracking-widest text-ink/55 ring-1 ring-rule"
				>
					{label}{delta ? ` ${delta}` : ''}
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
					{@render partColumn(part)}
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
