<script lang="ts">
	import * as m from '$lib/paraglide/messages.js';
	import { categoryLabel } from '$lib/labels';
	import type { PageData } from './$types';
	import type { LexemeRow } from './+page.server';

	let { data }: { data: PageData } = $props();
	let rows = $derived(data.rows as LexemeRow[]);
	let stats = $derived(data.stats);

	let filter = $state('');
	let onlyMultiDialect = $state(false);
	let onlySenseSplit = $state(false);

	const PAGE_SIZE = 50;
	let page = $state(1);

	let filtered = $derived.by(() => {
		let result = rows;
		const f = filter.trim().toLowerCase();
		if (f) {
			result = result.filter(
				(r) =>
					r.lemma.toLowerCase().includes(f) ||
					r.kana.includes(filter.trim()) ||
					r.gloss_jp.includes(filter.trim()) ||
					r.gloss_en.toLowerCase().includes(f)
			);
		}
		if (onlyMultiDialect) result = result.filter((r) => r.dialects.length > 1);
		if (onlySenseSplit) result = result.filter((r) => r.senses > 0);
		return result;
	});

	// Reset to page 1 whenever the filter set changes.
	$effect(() => {
		void filter;
		void onlyMultiDialect;
		void onlySenseSplit;
		page = 1;
	});

	let totalPages = $derived(Math.max(1, Math.ceil(filtered.length / PAGE_SIZE)));
	let paged = $derived(filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE));
</script>

<svelte:head>
	<title>Lexemes / 語彙素 — {m.app_title()}</title>
</svelte:head>

<div class="mx-auto max-w-6xl px-4 py-8">
	<header class="mb-6">
		<nav class="mb-4 text-sm">
			<a class="text-blue-600 hover:underline dark:text-blue-400" href="/">← {m.back_home()}</a>
		</nav>
		<h1 class="text-2xl font-bold tracking-tight">Lexemes <span class="text-neutral-400">語彙素</span></h1>
		<p class="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
			Canonical, source-independent headwords. Each lexeme is composed of one or more morphemes;
			pivot one to see every dictionary's recording of it across dialects.
		</p>
		<p class="mt-2 text-xs text-neutral-500">
			{stats.total.toLocaleString()} lexemes · {stats.multiDialect.toLocaleString()} multi-dialect ·
			{stats.senseSplit.toLocaleString()} sense-split · {stats.morphemeLinked.toLocaleString()} morpheme-linked
		</p>
	</header>

	<div class="mb-4 flex flex-wrap items-center gap-4">
		<input
			class="w-full max-w-xs rounded border border-neutral-300 px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900"
			placeholder="Filter by form or gloss…"
			bind:value={filter}
		/>
		<label class="flex items-center gap-1.5 text-sm">
			<input type="checkbox" bind:checked={onlyMultiDialect} /> multi-dialect only
		</label>
		<label class="flex items-center gap-1.5 text-sm">
			<input type="checkbox" bind:checked={onlySenseSplit} /> sense-split only
		</label>
		<span class="ml-auto text-xs text-neutral-500">{filtered.length.toLocaleString()} results</span>
	</div>

	<div class="overflow-x-auto rounded border border-neutral-200 dark:border-neutral-800">
		<table class="w-full text-sm">
			<thead class="bg-neutral-50 text-left text-xs uppercase text-neutral-500 dark:bg-neutral-900">
				<tr>
					<th class="px-3 py-2">Lemma</th>
					<th class="px-3 py-2">Kana</th>
					<th class="px-3 py-2">POS</th>
					<th class="px-3 py-2">Gloss</th>
					<th class="px-3 py-2">Dialects</th>
					<th class="px-3 py-2 text-right">Recordings</th>
				</tr>
			</thead>
			<tbody>
				{#each paged as r (r.id)}
					<tr class="border-t border-neutral-100 hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900">
						<td class="px-3 py-1.5">
							<a class="font-medium text-blue-600 hover:underline dark:text-blue-400" href="/lexemes/{encodeURIComponent(r.id)}">
								{r.lemma}{#if r.bound}<span class="ml-1 text-xs text-neutral-400">bound</span>{/if}
							</a>
						</td>
						<td class="px-3 py-1.5 text-neutral-600 dark:text-neutral-400">{r.kana}</td>
						<td class="px-3 py-1.5 text-neutral-500">{r.pos ? categoryLabel(r.pos) : '—'}</td>
						<td class="px-3 py-1.5 text-neutral-700 dark:text-neutral-300">{r.gloss_jp || r.gloss_en}</td>
						<td class="px-3 py-1.5">
							{#each r.dialects as d}
								<span class="mr-1 inline-block rounded bg-neutral-100 px-1.5 py-0.5 text-xs dark:bg-neutral-800">{d}</span>
							{/each}
						</td>
						<td class="px-3 py-1.5 text-right tabular-nums text-neutral-600 dark:text-neutral-400">{r.recordings}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	{#if totalPages > 1}
		<div class="mt-4 flex items-center justify-center gap-3 text-sm">
			<button class="rounded border px-3 py-1 disabled:opacity-40 dark:border-neutral-700" disabled={page <= 1} onclick={() => (page -= 1)}>← Prev</button>
			<span class="text-neutral-500">{page} / {totalPages}</span>
			<button class="rounded border px-3 py-1 disabled:opacity-40 dark:border-neutral-700" disabled={page >= totalPages} onclick={() => (page += 1)}>Next →</button>
		</div>
	{/if}
</div>
