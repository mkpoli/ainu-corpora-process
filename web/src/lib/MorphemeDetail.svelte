<script lang="ts">
	import * as m from '$lib/paraglide/messages.js';
	import { inferredValencyDelta, valencyDelta } from './composition';
	import { categoryLabel, morphTypeLabel, slotLabel } from './labels';
	import { sourceLabel, sourceUrl } from './sources';
	import type { Entry } from './types';
	import ValencyFrame from './ValencyFrame.svelte';

	let {
		entry,
		otherUses,
		computedArities = {},
		onSelectLemma
	}: {
		entry: Entry | null;
		otherUses: Entry[];
		computedArities?: Record<string, number>;
		onSelectLemma: (lemma: string) => void;
	} = $props();

	// Strip allomorphs that are the same string as the lemma (or the lemma's
	// bound-marker-stripped bare form) — those duplicate the title chip.
	// Also strip bare attachment-marker-less variants when a dashed sibling
	// is present in the same list: ``te`` is kept in the data so the
	// segmenter can resolve ``pakte`` → ``pak + te``, but the morpheme
	// detail view only needs to show the canonical ``-te``.
	const variantAllomorphs = $derived.by(() => {
		if (!entry) return [];
		const stripMarkers = (s: string) => s.replace(/^[-=]+|[-=]+$/g, '');
		const bareLemma = stripMarkers(entry.lemma);
		const dashedBares = new Set(
			entry.allomorphs.filter((v) => /^[-=]|[-=]$/.test(v)).map(stripMarkers),
		);
		return entry.allomorphs.filter((v) => {
			if (v === entry.lemma || v === bareLemma) return false;
			const isBare = !/^[-=]|[-=]$/.test(v);
			if (isBare && dashedBares.has(v)) return false;
			return true;
		});
	});

	const REALIZATION_LABEL: Record<string, () => string> = {
		external: () => m.realization_external(),
		internal_incorp: () => m.realization_internal_incorp(),
		internal_refl: () => m.realization_internal_refl(),
		internal_indef: () => m.realization_internal_indef(),
		absorbed: () => m.realization_absorbed()
	};
</script>

{#if entry}
	{@const lemmaSize =
		entry.lemma.length <= 8
			? 'text-3xl'
			: entry.lemma.length <= 14
				? 'text-2xl'
				: 'text-xl'}
	<article class="flex flex-col gap-5">
		<header class="flex flex-col gap-2 border-b border-rule pb-3">
			<!-- Lemma takes its own line and is allowed to wrap; the meta
			     chips below it never get pushed into a stretched single-line
			     row by extreme polysynthetic forms like
			     eyaykotuymasiramsuypa. Font scales down on long lemmas so the
			     sidebar width stays predictable. -->
			<h2 class="font-mono {lemmaSize} break-words text-ink">{entry.lemma}</h2>
			<div class="flex flex-wrap items-center gap-2">
				<span class="text-xs uppercase tracking-widest text-ink/60">
					{morphTypeLabel(entry.morph_type)}{entry.category ? ` · ${categoryLabel(entry.category)}` : ''}
				</span>
				{#if entry.verified}
					<span class="rounded-full bg-leaf/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-leaf">{m.detail_curated()}</span>
				{:else}
					<span class="rounded-full bg-rule/40 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-ink/60">{m.detail_unverified()}</span>
				{/if}
				{#if entry.bound}
					<span class="rounded-full bg-affix-soft px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-affix" title="Bound morpheme — does not occur as a standalone word.">bound</span>
				{:else}
					<span class="rounded-full bg-paper px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-ink/55 ring-1 ring-rule" title="Free morpheme — can occur as a standalone word.">free</span>
				{/if}
				{#if entry.slot?.length}
					<span
						class="rounded-full bg-accent-soft px-2 py-0.5 font-mono text-[10px] font-semibold tracking-wider text-accent ring-1 ring-accent/30"
						title={`${entry.slot.map(slotLabel).join(' / ')}\n\n${m.detail_slot_tooltip()}`}
					>
						{m.detail_slot_value({ slots: entry.slot.join('/') })}
					</span>
				{/if}
			</div>
			{#if entry.glosses_en.length}
				<p class="text-base text-ink/80">{entry.glosses_en.join(', ')}</p>
			{/if}
			{#if entry.glosses_jp.length}
				<p class="text-sm text-ink/70">{entry.glosses_jp.join('、')}</p>
			{/if}
		</header>

		{#if entry.base_frame || entry.rules.length}
			{@const delta = valencyDelta(entry)}
			<section class="flex flex-col gap-2">
				<h3 class="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-ink/60">
					{m.detail_valency()}
					{#if delta !== null && delta !== 0}
						<span class="font-mono text-[10px] normal-case text-ink/70">
							{delta > 0 ? `+${delta}` : delta}
						</span>
					{/if}
				</h3>
				{#if entry.base_frame}
					<div class="flex flex-col gap-2">
						<span class="text-xs text-ink/60">{m.detail_base_frame()}</span>
						<ValencyFrame frame={entry.base_frame} />
					</div>
				{/if}
				{#if entry.rules.length}
					<div class="flex flex-col gap-1">
						<span class="text-xs text-ink/60">{m.detail_local_rules()}</span>
						<ul class="flex flex-col gap-1">
							{#each entry.rules as rule}
								<li class="rounded-xl bg-paper px-3 py-2 ring-1 ring-rule">
									<span class="font-mono text-xs text-affix">{rule.operation}</span>
									{#if rule.role}
										<span class="text-xs text-ink/70">→ {rule.role}{rule.realization && rule.realization !== 'external' ? ` · ${REALIZATION_LABEL[rule.realization]?.() ?? rule.realization}` : ''}</span>
									{/if}
									{#if rule.description}
										<p class="mt-0.5 text-xs italic text-ink/60">{rule.description}</p>
									{/if}
								</li>
							{/each}
						</ul>
					</div>
				{/if}
			</section>
		{:else}
			{@const computed = computedArities[entry.id] ?? null}
			{@const inferred = inferredValencyDelta(entry)}
			{#if computed !== null}
				<section class="flex flex-col gap-1">
					<h3 class="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-ink/60">
						{m.detail_valency()}
						<span class="font-mono text-[10px] normal-case italic text-ink/55" title="Derived by summing the valency deltas of this entry's composition.">
							arity {computed}
						</span>
					</h3>
					<p class="text-xs italic text-ink/55">Derived from the composition chain.</p>
				</section>
			{:else if inferred !== null}
				<section class="flex flex-col gap-1">
					<h3 class="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-ink/60">
						{m.detail_valency()}
						<span class="font-mono text-[10px] normal-case italic text-ink/55" title={m.morphemes_arity_inferred()}>
							{inferred > 0 ? `+${inferred}` : inferred}
						</span>
					</h3>
					<p class="text-xs italic text-ink/55">{m.detail_valency_inferred()}</p>
				</section>
			{/if}
		{/if}

		{#if variantAllomorphs.length}
			<section class="flex flex-col gap-2">
				<h3 class="text-xs font-semibold uppercase tracking-widest text-ink/60">{m.detail_allomorphs()}</h3>
				<div class="flex flex-wrap gap-1.5">
					{#each variantAllomorphs as variant}
						<span class="rounded-full bg-paper px-2 py-0.5 font-mono text-xs ring-1 ring-rule">{variant}</span>
					{/each}
				</div>
			</section>
		{/if}

		{#if entry.reconstructed && Object.keys(entry.reconstructed).length}
			<section class="flex flex-col gap-2">
				<h3 class="text-xs font-semibold uppercase tracking-widest text-ink/60">Reconstructed</h3>
				<div class="flex flex-wrap gap-1.5">
					{#each Object.entries(entry.reconstructed) as [source, form]}
						<span class="rounded-full bg-paper px-2 py-0.5 font-mono text-xs ring-1 ring-rule" title={source}>
							{form} <span class="text-[10px] text-ink/55">({source})</span>
						</span>
					{/each}
				</div>
			</section>
		{/if}

		{#if entry.attaches_to.length || entry.category_alt.length}
			<section class="flex flex-col gap-2">
				<h3 class="text-xs font-semibold uppercase tracking-widest text-ink/60">{m.detail_combinatorics()}</h3>
				{#if entry.attaches_to.length}
					<p class="text-xs text-ink/70">
						{m.detail_attaches_to()}: <span>{entry.attaches_to.map((c) => categoryLabel(c)).join(', ')}</span>
					</p>
				{/if}
				{#if entry.category_alt.length}
					<p class="text-xs text-ink/70">
						{m.detail_also()}: <span>{entry.category_alt.map((c) => categoryLabel(c)).join(', ')}</span>
					</p>
				{/if}
			</section>
		{/if}

		{#if entry.notes}
			<section class="flex flex-col gap-1">
				<h3 class="text-xs font-semibold uppercase tracking-widest text-ink/60">{m.detail_notes()}</h3>
				<p class="text-sm leading-relaxed text-ink/80">{entry.notes}</p>
			</section>
		{/if}

		{#if entry.sources.length}
			<section class="flex flex-col gap-1">
				<h3 class="text-xs font-semibold uppercase tracking-widest text-ink/60">{m.detail_sources()}</h3>
				<ul class="flex flex-wrap gap-1.5">
					{#each entry.sources as src}
						{@const url = sourceUrl(src, entry.lemma)}
						{@const isInternal = url?.startsWith('/') ?? false}
						<li>
							{#if url}
								<a
									href={url}
									target={isInternal ? undefined : '_blank'}
									rel={isInternal ? undefined : 'noopener noreferrer'}
									class="rounded-full bg-paper px-2 py-0.5 text-[11px] text-ink/80 ring-1 ring-rule transition hover:bg-accent-soft hover:text-accent hover:ring-accent/40"
								>
									{sourceLabel(src)}
								</a>
							{:else}
								<span class="rounded-full bg-paper px-2 py-0.5 text-[11px] text-ink/70 ring-1 ring-rule">
									{sourceLabel(src)}
								</span>
							{/if}
						</li>
					{/each}
				</ul>
			</section>
		{/if}

		{#if otherUses.length}
			<section class="flex flex-col gap-2">
				<h3 class="text-xs font-semibold uppercase tracking-widest text-ink/60">
					{otherUses.length === 1 ? m.detail_appears_in_one({ count: otherUses.length }) : m.detail_appears_in_other({ count: otherUses.length })}
				</h3>
				<ul class="flex flex-col gap-1">
					{#each otherUses as use}
						<li>
							<button
								type="button"
								class="flex w-full items-baseline justify-between gap-3 rounded-xl bg-paper px-3 py-1.5 text-left ring-1 ring-rule transition hover:bg-accent-soft hover:ring-accent/40"
								onclick={() => onSelectLemma(use.lemma)}
							>
								<span class="font-mono text-sm">{use.lemma}</span>
								<span class="truncate text-xs italic text-ink/60">
									{use.glosses_en[0] ?? use.glosses_jp[0] ?? ''}
								</span>
							</button>
						</li>
					{/each}
				</ul>
			</section>
		{/if}

		<section>
			<a
				href="/lexemes?morph={encodeURIComponent(entry.id)}"
				class="inline-flex items-center gap-1 text-xs text-ink/60 underline-offset-2 transition hover:text-accent hover:underline"
			>
				{m.detail_lexemes_link()} →
			</a>
		</section>

		{#if entry.frequency > 0}
			<footer class="text-[11px] text-ink/50">
				{m.detail_observed({ count: entry.frequency.toLocaleString() })}
			</footer>
		{/if}
	</article>
{:else}
	<p class="text-sm text-ink/60">
		{m.detail_empty()}
	</p>
{/if}
