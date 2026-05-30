<script lang="ts">
	import * as m from '$lib/paraglide/messages.js';
	import { categoryLabel } from '$lib/labels';
	import LocaleSwitcher from '$lib/LocaleSwitcher.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	let lx = $derived(data.lexeme);
	let morphemes = $derived(data.morphemes);
	let dialectGroups = $derived(data.dialectGroups);

	// Match-kind badge colours, mapped onto the app's semantic palette:
	// seed=leaf (this source defined it), exact=accent, normalized=affix,
	// fuzzy/other=muted.
	function matchClass(kind: string): string {
		switch (kind) {
			case 'seed':
				return 'bg-leaf/15 text-leaf';
			case 'exact':
				return 'bg-accent-soft text-accent';
			case 'normalized':
				return 'bg-affix-soft text-affix';
			default:
				return 'bg-paper text-ink/60 ring-1 ring-rule';
		}
	}

	// Shorten the long source folder names for the chips.
	function shortSource(s: string): string {
		return s.replace(/_/g, ' ').replace(/-/g, ' ');
	}
</script>

<svelte:head>
	<title>{lx.lemma} — {m.lexemes_title()} — {m.app_title()}</title>
</svelte:head>

<div class="mx-auto flex min-h-screen max-w-5xl flex-col gap-5 px-6 py-8">
	<div class="flex flex-wrap items-center justify-between gap-3">
		<a href="/lexemes" class="text-xs uppercase tracking-widest text-ink/60 hover:text-accent">← {m.lexemes_title()}</a>
		<LocaleSwitcher />
	</div>

	<header class="border-b border-rule pb-4">
		<div class="flex flex-wrap items-baseline gap-3">
			<h1 class="font-mono text-3xl font-semibold tracking-tight">{lx.lemma}</h1>
			{#if lx.kana}<span class="text-xl text-ink/50">{lx.kana}</span>{/if}
			{#if lx.pos}<span class="rounded-full bg-paper px-2 py-0.5 text-sm text-ink/70 ring-1 ring-rule">{categoryLabel(lx.pos)}</span>{/if}
			{#if lx.bound}<span class="rounded-full bg-affix-soft px-2 py-0.5 text-xs font-semibold uppercase tracking-wider text-affix">bound</span>{/if}
		</div>
		<p class="mt-1 font-mono text-xs text-ink/40">{lx.id}</p>
		{#if lx.gloss_jp.length || lx.gloss_en.length}
			<p class="mt-2 text-ink/85">{[...lx.gloss_jp, ...lx.gloss_en].join('；')}</p>
		{/if}
		<p class="mt-2 text-xs text-ink/55">
			{m.lexemes_detail_attested({
				recordings: lx.recordings,
				dialects: lx.dialects.length,
				list: lx.dialects.join('、'),
				base: lx.dialect_base || '—'
			})}
		</p>
	</header>

	{#if lx.senses.length}
		<section>
			<h2 class="mb-2 text-[10px] font-semibold uppercase tracking-widest text-ink/60">{m.lexemes_detail_senses()}</h2>
			<ol class="list-decimal space-y-1 pl-6 text-sm text-ink/85">
				{#each lx.senses as s}
					<li>{[...s.gloss_jp, ...s.gloss_en].join('；')}</li>
				{/each}
			</ol>
		</section>
	{/if}

	{#if morphemes.length}
		<section>
			<h2 class="mb-1 text-[10px] font-semibold uppercase tracking-widest text-ink/60">{m.lexemes_detail_morphemes()}</h2>
			<p class="mb-2 text-xs text-ink/50">{m.lexemes_detail_morphemes_hint()}</p>
			<div class="flex flex-wrap items-center gap-2">
				{#each morphemes as mo, i}
					{#if i > 0}<span class="font-mono text-ink/40">+</span>{/if}
					{#if mo.resolved}
						<a
							class="rounded-2xl border border-rule bg-white/70 px-3 py-1.5 text-sm shadow-sm transition hover:-translate-y-0.5 hover:border-accent/40 hover:shadow-md"
							href="/?q={encodeURIComponent(mo.lemma)}"
						>
							<span class="font-mono font-medium text-accent">{mo.lemma}</span>
							{#if mo.gloss_jp || mo.gloss_en}<span class="ml-1 text-xs text-ink/55">{mo.gloss_jp || mo.gloss_en}</span>{/if}
						</a>
					{:else}
						<span class="rounded-2xl border border-dashed border-rule px-3 py-1.5 text-sm text-ink/50">{mo.lemma}</span>
					{/if}
				{/each}
			</div>
		</section>
	{/if}

	<section>
		<h2 class="mb-3 text-[10px] font-semibold uppercase tracking-widest text-ink/60">{m.lexemes_detail_recordings()}</h2>
		<div class="space-y-5">
			{#each dialectGroups as group}
				<div>
					<h3 class="mb-2 flex items-baseline gap-2 text-base font-semibold">
						<span class="rounded-full bg-leaf/10 px-2 py-0.5 text-sm text-leaf">{group.dialect}</span>
						<span class="text-xs font-normal text-ink/40">{group.attestations.length}</span>
					</h3>
					<div class="overflow-x-auto rounded-2xl bg-white/70 ring-1 ring-rule">
						<table class="w-full border-collapse text-sm">
							<thead class="text-left text-[10px] uppercase tracking-widest text-ink/60">
								<tr class="border-b border-rule">
									<th class="px-3 py-2">{m.lexemes_att_form()}</th>
									<th class="px-3 py-2">{m.lexemes_att_kana()}</th>
									<th class="px-3 py-2">{m.lexemes_att_pos()}</th>
									<th class="px-3 py-2">{m.lexemes_att_gloss()}</th>
									<th class="px-3 py-2">{m.lexemes_att_source()}</th>
									<th class="px-3 py-2">{m.lexemes_att_match()}</th>
								</tr>
							</thead>
							<tbody>
								{#each group.attestations as a}
									<tr class="border-b border-rule/50 align-top text-ink/85 odd:bg-paper/40">
										<td class="px-3 py-2 font-mono font-medium">{a.surface_latn}</td>
										<td class="px-3 py-2 text-ink/70">{a.surface_kana}</td>
										<td class="px-3 py-2 text-[12px] text-ink/60">{a.pos_raw}</td>
										<td class="px-3 py-2 text-[12px]">{a.gloss}</td>
										<td class="px-3 py-2 text-[11px] text-ink/55">{shortSource(a.source)}</td>
										<td class="px-3 py-2">
											<span class="rounded-full px-2 py-0.5 text-[11px] {matchClass(a.match_kind)}">{a.match_kind}</span>
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</div>
			{/each}
		</div>
	</section>
</div>
