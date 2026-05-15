<script lang="ts">
	import * as m from '$lib/paraglide/messages.js';
	import { inferredValencyDelta, valencyDelta } from './composition';
	import { categoryLabel, morphTypeLabel } from './labels';
	import { sourceLabel, sourceUrl } from './sources';
	import type { Entry } from './types';
	import ValencyFrame from './ValencyFrame.svelte';

	let {
		entry,
		otherUses,
		onSelectLemma
	}: {
		entry: Entry | null;
		otherUses: Entry[];
		onSelectLemma: (lemma: string) => void;
	} = $props();

	const REALIZATION_LABEL: Record<string, () => string> = {
		external: () => m.realization_external(),
		internal_incorp: () => m.realization_internal_incorp(),
		internal_refl: () => m.realization_internal_refl(),
		internal_indef: () => m.realization_internal_indef(),
		absorbed: () => m.realization_absorbed()
	};
</script>

{#if entry}
	<article class="flex flex-col gap-5">
		<header class="flex flex-col gap-1 border-b border-rule pb-3">
			<div class="flex items-baseline gap-3">
				<h2 class="font-mono text-3xl text-ink">{entry.lemma}</h2>
				<span class="text-xs uppercase tracking-widest text-ink/60">
					{morphTypeLabel(entry.morph_type)}{entry.category ? ` · ${categoryLabel(entry.category)}` : ''}
				</span>
				{#if entry.verified}
					<span class="rounded-full bg-leaf/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-leaf">{m.detail_curated()}</span>
				{:else}
					<span class="rounded-full bg-rule/40 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-ink/60">{m.detail_unverified()}</span>
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
			{@const inferred = inferredValencyDelta(entry)}
			{#if inferred !== null}
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

		{#if entry.allomorphs.length}
			<section class="flex flex-col gap-2">
				<h3 class="text-xs font-semibold uppercase tracking-widest text-ink/60">{m.detail_allomorphs()}</h3>
				<div class="flex flex-wrap gap-1.5">
					{#each entry.allomorphs as variant}
						<span class="rounded-full bg-paper px-2 py-0.5 font-mono text-xs ring-1 ring-rule">{variant}</span>
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
