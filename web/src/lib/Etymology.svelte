<script lang="ts">
	import * as m from '$lib/paraglide/messages.js';
	import { sourceLabel, sourceUrl } from './sources';
	import type { Entry } from './types';

	let { entry }: { entry: Entry | null } = $props();

	const etymology = $derived(entry?.etymology ?? null);
	const sourceHref = $derived.by(() => {
		if (!entry || !etymology?.source) return null;
		return sourceUrl(etymology.source, entry.lemma);
	});
</script>

{#if entry && etymology}
	<section class="rounded-2xl border-2 border-dashed border-ink/30 bg-paper/60 p-4 shadow-inner">
		<div class="mb-2 flex flex-wrap items-baseline justify-between gap-2">
			<h3 class="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-widest text-ink/60">
				{m.detail_etymology()}
				<span class="rounded-full bg-paper px-2 py-0.5 text-[10px] normal-case text-ink/55 ring-1 ring-rule">
					{m.detail_etymology_note()}
				</span>
			</h3>
		</div>
		<div class="flex flex-col items-center gap-2 px-2 py-2">
			<!-- The lexicalised surface form, encapsulated inside the etymology frame. -->
			<span
				class="rounded-2xl border border-accent/60 bg-accent-soft px-4 py-1.5 font-mono text-base text-accent"
			>
				{entry.lemma}
			</span>
			{#if etymology.parts && etymology.parts.length}
				<span aria-hidden="true" class="text-[10px] uppercase tracking-widest text-ink/40"
					>←</span
				>
				<div class="flex flex-wrap items-center justify-center gap-1.5">
					{#each etymology.parts as part, idx}
						{#if idx > 0}
							<span aria-hidden="true" class="text-ink/40">+</span>
						{/if}
						<div class="rounded-xl bg-paper px-2.5 py-1 text-center ring-1 ring-rule">
							<div class="font-mono text-sm">{part.lemma}</div>
							{#if part.gloss_en || part.gloss_jp}
								<div class="text-[10px] italic text-ink/55">
									{part.gloss_en ?? ''}{part.gloss_en && part.gloss_jp ? ' · ' : ''}{part.gloss_jp ?? ''}
								</div>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		</div>
		{#if etymology.note}
			<p class="mt-1 text-xs italic leading-relaxed text-ink/70">{etymology.note}</p>
		{/if}
		{#if etymology.source}
			<p class="mt-2 text-[11px] text-ink/55">
				{#if sourceHref}
					<a
						href={sourceHref}
						target={sourceHref.startsWith('/') ? undefined : '_blank'}
						rel={sourceHref.startsWith('/') ? undefined : 'noopener noreferrer'}
						class="rounded-full bg-paper px-2 py-0.5 ring-1 ring-rule transition hover:bg-accent-soft hover:text-accent hover:ring-accent/40"
					>
						{sourceLabel(etymology.source)}
					</a>
				{:else}
					<span class="rounded-full bg-paper px-2 py-0.5 ring-1 ring-rule">
						{sourceLabel(etymology.source)}
					</span>
				{/if}
			</p>
		{/if}
	</section>
{/if}
