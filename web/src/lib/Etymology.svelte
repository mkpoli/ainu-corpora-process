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
		<header class="mb-2 flex flex-wrap items-baseline justify-between gap-2 text-xs text-ink/60">
			<span class="font-semibold uppercase tracking-widest">{m.detail_etymology()}</span>
			<span class="italic opacity-80">{m.detail_etymology_note()}</span>
		</header>

		<!-- Mirror the composition-tree visual: surface header at top,
		     bracket label, then the parts as clickable leaves below. -->
		<div class="flex flex-col items-center gap-3">
			<!-- The lexicalised lemma, in the head-style chip. -->
			<div class="rounded-2xl border border-accent/60 bg-accent-soft px-4 py-1.5 text-center">
				<span class="font-mono text-base text-accent">{entry.lemma}</span>
			</div>

			{#if etymology.parts && etymology.parts.length}
				<div class="flex flex-col items-center">
					<span class="h-3 w-px bg-rule"></span>
					<span
						class="rounded bg-paper px-1.5 py-[1px] font-mono text-[10px] uppercase tracking-widest text-ink/60 ring-1 ring-rule"
					>
						{m.kind_etymology()}
					</span>
					<span class="h-3 w-px bg-rule"></span>
				</div>

				<div class="flex flex-wrap items-start justify-center gap-3">
					{#each etymology.parts as part}
						<a
							href={`/?q=${encodeURIComponent(part.lemma)}`}
							class="group flex min-w-[5.5rem] flex-col items-center gap-0.5 rounded-2xl border border-ink/40 border-dashed bg-paper px-3 py-1.5 shadow-sm transition hover:-translate-y-0.5 hover:border-accent hover:shadow-md"
						>
							<span class="font-mono text-sm">{part.lemma}</span>
							{#if part.gloss_en || part.gloss_jp}
								<span class="text-[10px] italic text-ink/60">
									{part.gloss_en ?? ''}{part.gloss_en && part.gloss_jp ? ' · ' : ''}{part.gloss_jp ?? ''}
								</span>
							{/if}
						</a>
					{/each}
				</div>
			{/if}
		</div>

		{#if etymology.note}
			<p class="mt-3 text-center text-[11px] italic text-ink/60">{etymology.note}</p>
		{/if}

		{#if etymology.source}
			<p class="mt-3 text-right text-[10px]">
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
