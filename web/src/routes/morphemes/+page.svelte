<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import * as m from '$lib/paraglide/messages.js';
	import LocaleSwitcher from '$lib/LocaleSwitcher.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let inputQuery = $state('');

	$effect(() => {
		inputQuery = data.query;
	});

	function pushParam(name: string, value: string | null) {
		const url = new URL(page.url);
		if (value && value !== '') url.searchParams.set(name, value);
		else url.searchParams.delete(name);
		if (name !== 'page') url.searchParams.delete('page');
		goto(url, { keepFocus: true });
	}

	function toggleParam(name: string, current: boolean) {
		pushParam(name, current ? null : '1');
	}

	function setSort(column: string) {
		const sameColumn = data.sort === column;
		const nextDir = sameColumn && data.dir === 'desc' ? 'asc' : 'desc';
		const url = new URL(page.url);
		url.searchParams.set('sort', column);
		url.searchParams.set('dir', nextDir);
		url.searchParams.delete('page');
		goto(url, { keepFocus: true });
	}

	function sortIndicator(column: string): string {
		if (data.sort !== column) return '';
		return data.dir === 'asc' ? '↑' : '↓';
	}

	function submitQuery(event: SubmitEvent) {
		event.preventDefault();
		pushParam('q', inputQuery.trim());
	}

	const totalPages = $derived(Math.max(1, Math.ceil(data.total / data.pageSize)));
</script>

<svelte:head>
	<title>{m.morphemes_title()} — {m.app_title()}</title>
</svelte:head>

<div class="mx-auto flex min-h-screen max-w-7xl flex-col gap-5 px-6 py-8">
	<header class="flex flex-col gap-3">
		<div class="flex flex-wrap items-start justify-between gap-3">
			<div class="flex flex-col gap-1">
				<a href="/" class="text-xs uppercase tracking-widest text-ink/60 hover:text-accent">← {m.back_home()}</a>
				<h1 class="text-3xl font-semibold tracking-tight">{m.morphemes_title()}</h1>
				<p class="text-sm text-ink/60 max-w-2xl">{m.morphemes_subtitle()}</p>
			</div>
			<div class="flex items-center gap-3 text-xs">
				<a href="/references" class="text-ink/70 underline-offset-2 hover:text-accent hover:underline">
					{m.references_link()}
				</a>
				<LocaleSwitcher />
			</div>
		</div>

		<form class="flex flex-wrap items-center gap-2" onsubmit={submitQuery}>
			<input
				type="search"
				bind:value={inputQuery}
				placeholder={m.morphemes_filter_placeholder()}
				class="w-full flex-1 rounded-2xl border border-rule bg-paper px-3 py-1.5 font-mono text-sm shadow-inner focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30 sm:w-auto"
			/>
			<select
				class="rounded-2xl border border-rule bg-paper px-3 py-1.5 text-sm focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
				value={data.category}
				onchange={(e) => pushParam('cat', (e.currentTarget as HTMLSelectElement).value)}
			>
				<option value="">{m.morphemes_all_categories()}</option>
				{#each data.categories as cat}
					<option value={cat}>{cat}</option>
				{/each}
			</select>
			<label class="inline-flex items-center gap-1.5 text-xs text-ink/70">
				<input
					type="checkbox"
					checked={data.verifiedOnly}
					onchange={() => toggleParam('verified', data.verifiedOnly)}
				/>
				{m.morphemes_only_curated()}
			</label>
			<label class="inline-flex items-center gap-1.5 text-xs text-ink/70">
				<input
					type="checkbox"
					checked={data.withComposition}
					onchange={() => toggleParam('composition', data.withComposition)}
				/>
				{m.morphemes_only_composition()}
			</label>
			<label class="inline-flex items-center gap-1.5 text-xs text-ink/70">
				<input
					type="checkbox"
					checked={data.withFrame}
					onchange={() => toggleParam('frame', data.withFrame)}
				/>
				{m.morphemes_only_frame()}
			</label>
		</form>

		<p class="text-xs text-ink/60">
			{m.morphemes_results({ total: data.total, all: data.stats.total })}
		</p>
	</header>

	<div class="overflow-x-auto rounded-2xl bg-white/70 ring-1 ring-rule">
		<table class="w-full border-collapse text-sm">
			<thead class="text-left text-[10px] uppercase tracking-widest text-ink/60">
				<tr class="border-b border-rule">
					<th class="px-3 py-2">
						<button class="hover:text-accent" onclick={() => setSort('lemma')}>
							{m.morphemes_col_lemma()} {sortIndicator('lemma')}
						</button>
					</th>
					<th class="px-3 py-2">
						<button class="hover:text-accent" onclick={() => setSort('category')}>
							{m.morphemes_col_category()} {sortIndicator('category')}
						</button>
					</th>
					<th class="px-3 py-2">
						<button class="hover:text-accent" onclick={() => setSort('morph_type')}>
							{m.morphemes_col_type()} {sortIndicator('morph_type')}
						</button>
					</th>
					<th class="px-3 py-2">{m.morphemes_col_gloss_en()}</th>
					<th class="px-3 py-2">{m.morphemes_col_gloss_jp()}</th>
					<th class="px-3 py-2 text-right">
						<button class="hover:text-accent" onclick={() => setSort('arity')}>
							{m.morphemes_col_arity()} {sortIndicator('arity')}
						</button>
					</th>
					<th class="px-3 py-2 text-right">
						<button class="hover:text-accent" onclick={() => setSort('composition')}>
							{m.morphemes_col_composition()} {sortIndicator('composition')}
						</button>
					</th>
					<th class="px-3 py-2 text-right">
						<button class="hover:text-accent" onclick={() => setSort('frequency')}>
							{m.morphemes_col_frequency()} {sortIndicator('frequency')}
						</button>
					</th>
					<th class="px-3 py-2">
						<button class="hover:text-accent" onclick={() => setSort('verified')}>
							{m.morphemes_col_verified()} {sortIndicator('verified')}
						</button>
					</th>
				</tr>
			</thead>
			<tbody>
				{#each data.rows as row (row.id)}
					<tr class="border-b border-rule/50 align-top text-ink/85 odd:bg-paper/40 hover:bg-accent-soft/40">
						<td class="px-3 py-2 font-mono">
							<a href={`/?q=${encodeURIComponent(row.lemma)}`} class="text-accent hover:underline">
								{row.lemma}
							</a>
						</td>
						<td class="px-3 py-2 font-mono text-[12px] text-ink/70">{row.category || '—'}</td>
						<td class="px-3 py-2 text-[12px] text-ink/70">{row.morph_type}</td>
						<td class="px-3 py-2 text-[12px]">{row.gloss_en || '—'}</td>
						<td class="px-3 py-2 text-[12px]">{row.gloss_jp || '—'}</td>
						<td class="px-3 py-2 text-right font-mono text-[12px]">{row.arity ?? '—'}</td>
						<td class="px-3 py-2 text-right font-mono text-[12px]">{row.composition_length || '—'}</td>
						<td class="px-3 py-2 text-right font-mono text-[12px]">{row.frequency || '—'}</td>
						<td class="px-3 py-2 text-[11px]">
							{#if row.verified}
								<span class="rounded-full bg-leaf/15 px-2 py-0.5 text-leaf">{m.detail_curated()}</span>
							{:else}
								<span class="text-ink/50">{m.detail_unverified()}</span>
							{/if}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	{#if totalPages > 1}
		<nav class="flex items-center justify-center gap-1 text-xs text-ink/70">
			<button
				class="rounded-full px-3 py-1 ring-1 ring-rule disabled:opacity-50"
				disabled={data.page <= 1}
				onclick={() => pushParam('page', String(data.page - 1))}
			>
				← {m.morphemes_prev()}
			</button>
			<span class="px-2 font-mono">{data.page} / {totalPages}</span>
			<button
				class="rounded-full px-3 py-1 ring-1 ring-rule disabled:opacity-50"
				disabled={data.page >= totalPages}
				onclick={() => pushParam('page', String(data.page + 1))}
			>
				{m.morphemes_next()} →
			</button>
		</nav>
	{/if}
</div>
