<script lang="ts">
	import * as m from '$lib/paraglide/messages.js';
	import { categoryLabel } from '$lib/labels';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	let lx = $derived(data.lexeme);
	let morphemes = $derived(data.morphemes);
	let dialectGroups = $derived(data.dialectGroups);

	function matchColor(kind: string): string {
		switch (kind) {
			case 'seed':
				return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300';
			case 'exact':
				return 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300';
			case 'normalized':
				return 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300';
			default:
				return 'bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400';
		}
	}

	// Shorten the long source folder names for the chips.
	function shortSource(s: string): string {
		return s.replace(/_/g, ' ').replace(/-/g, ' ');
	}
</script>

<svelte:head>
	<title>{lx.lemma} — Lexeme — {m.app_title()}</title>
</svelte:head>

<div class="mx-auto max-w-4xl px-4 py-8">
	<nav class="mb-4 text-sm">
		<a class="text-blue-600 hover:underline dark:text-blue-400" href="/lexemes">← Lexemes</a>
	</nav>

	<header class="mb-6 border-b border-neutral-200 pb-4 dark:border-neutral-800">
		<div class="flex flex-wrap items-baseline gap-3">
			<h1 class="text-3xl font-bold tracking-tight">{lx.lemma}</h1>
			{#if lx.kana}<span class="text-xl text-neutral-500">{lx.kana}</span>{/if}
			{#if lx.pos}<span class="rounded bg-neutral-100 px-2 py-0.5 text-sm text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300">{categoryLabel(lx.pos)}</span>{/if}
			{#if lx.bound}<span class="rounded bg-purple-100 px-2 py-0.5 text-xs text-purple-700 dark:bg-purple-900/40 dark:text-purple-300">bound</span>{/if}
		</div>
		<p class="mt-1 font-mono text-xs text-neutral-400">{lx.id}</p>
		{#if lx.gloss_jp.length || lx.gloss_en.length}
			<p class="mt-2 text-neutral-700 dark:text-neutral-300">
				{[...lx.gloss_jp, ...lx.gloss_en].join('；')}
			</p>
		{/if}
		<p class="mt-2 text-xs text-neutral-500">
			Attested in {lx.dialects.length} dialect{lx.dialects.length === 1 ? '' : 's'}
			({lx.dialects.join('、')}) across {lx.recordings} recording{lx.recordings === 1 ? '' : 's'}.
			Citation form from {lx.dialect_base}.
		</p>
	</header>

	{#if lx.senses.length}
		<section class="mb-6">
			<h2 class="mb-2 text-sm font-semibold uppercase tracking-wide text-neutral-500">Senses</h2>
			<ol class="list-decimal space-y-1 pl-6 text-sm">
				{#each lx.senses as s}
					<li>{[...s.gloss_jp, ...s.gloss_en].join('；')}</li>
				{/each}
			</ol>
		</section>
	{/if}

	{#if morphemes.length}
		<section class="mb-6">
			<h2 class="mb-2 text-sm font-semibold uppercase tracking-wide text-neutral-500">Morphemes</h2>
			<div class="flex flex-wrap gap-2">
				{#each morphemes as mo}
					{#if mo.resolved}
						<a class="rounded border border-neutral-200 px-2 py-1 text-sm hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-900" href="/?q={encodeURIComponent(mo.lemma)}">
							<span class="font-medium">{mo.lemma}</span>
							{#if mo.gloss_en || mo.gloss_jp}<span class="ml-1 text-xs text-neutral-500">{mo.gloss_jp || mo.gloss_en}</span>{/if}
						</a>
					{:else}
						<span class="rounded border border-dashed border-neutral-300 px-2 py-1 text-sm text-neutral-500 dark:border-neutral-700">{mo.lemma}</span>
					{/if}
				{/each}
			</div>
		</section>
	{/if}

	<section>
		<h2 class="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">
			Recordings across dialects
		</h2>
		<div class="space-y-5">
			{#each dialectGroups as group}
				<div>
					<h3 class="mb-2 text-base font-semibold">
						{group.dialect}
						<span class="ml-2 text-xs font-normal text-neutral-400">{group.attestations.length}</span>
					</h3>
					<div class="overflow-x-auto rounded border border-neutral-200 dark:border-neutral-800">
						<table class="w-full text-sm">
							<thead class="bg-neutral-50 text-left text-xs uppercase text-neutral-500 dark:bg-neutral-900">
								<tr>
									<th class="px-3 py-2">Form (Latin)</th>
									<th class="px-3 py-2">Kana</th>
									<th class="px-3 py-2">POS</th>
									<th class="px-3 py-2">Gloss (as recorded)</th>
									<th class="px-3 py-2">Source</th>
									<th class="px-3 py-2">Match</th>
								</tr>
							</thead>
							<tbody>
								{#each group.attestations as a}
									<tr class="border-t border-neutral-100 dark:border-neutral-800">
										<td class="px-3 py-1.5 font-medium">{a.surface_latn}</td>
										<td class="px-3 py-1.5 text-neutral-600 dark:text-neutral-400">{a.surface_kana}</td>
										<td class="px-3 py-1.5 text-neutral-500">{a.pos_raw}</td>
										<td class="px-3 py-1.5 text-neutral-700 dark:text-neutral-300">{a.gloss}</td>
										<td class="px-3 py-1.5 text-xs text-neutral-500">{shortSource(a.source)}</td>
										<td class="px-3 py-1.5">
											<span class="rounded px-1.5 py-0.5 text-xs {matchColor(a.match_kind)}">{a.match_kind}</span>
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
