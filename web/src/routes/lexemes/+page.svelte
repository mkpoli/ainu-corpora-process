<script lang="ts">
	import * as m from '$lib/paraglide/messages.js';
	import { categoryLabel } from '$lib/labels';
	import LocaleSwitcher from '$lib/LocaleSwitcher.svelte';
	import type { PageData } from './$types';
	import type { LexemeRow } from './+page.server';

	let { data }: { data: PageData } = $props();
	let rows = $derived(data.rows as LexemeRow[]);
	let stats = $derived(data.stats);
	let morphFilter = $derived(data.morphFilter);

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
					r.gloss_en.toLowerCase().includes(f) ||
					r.morphemes.some((mo) => mo.toLowerCase().includes(f))
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
	<title>{m.lexemes_title()} — {m.app_title()}</title>
</svelte:head>

<div class="mx-auto flex min-h-screen max-w-7xl flex-col gap-5 px-6 py-8">
	<header class="flex flex-col gap-3">
		<div class="flex flex-wrap items-start justify-between gap-3">
			<div class="flex flex-col gap-1">
				<a href="/" class="text-xs uppercase tracking-widest text-ink/60 hover:text-accent">← {m.back_home()}</a>
				<h1 class="text-3xl font-semibold tracking-tight">{m.lexemes_title()}</h1>
				<p class="text-sm text-ink/60 max-w-2xl">{m.lexemes_subtitle()}</p>
			</div>
			<div class="flex items-center gap-3 text-xs">
				<a href="/morphemes" class="text-ink/70 underline-offset-2 hover:text-accent hover:underline">
					{m.morphemes_link()}
				</a>
				<a href="/references" class="text-ink/70 underline-offset-2 hover:text-accent hover:underline">
					{m.references_link()}
				</a>
				<LocaleSwitcher />
			</div>
		</div>

		{#if morphFilter}
			<div class="flex flex-wrap items-center gap-2 rounded-2xl bg-accent-soft/50 px-3 py-2 text-sm text-accent ring-1 ring-accent/30">
				<span>{m.lexemes_filtered_by({ morph: morphFilter.lemma })}</span>
				<a href="/lexemes" class="ml-auto text-xs underline-offset-2 hover:underline">{m.lexemes_clear_filter()} ✕</a>
			</div>
		{/if}

		<div class="flex flex-wrap items-center gap-3">
			<input
				class="w-full max-w-xs flex-1 rounded-2xl border border-rule bg-paper px-3 py-1.5 font-mono text-sm shadow-inner focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30 sm:w-auto"
				placeholder={m.lexemes_filter_placeholder()}
				bind:value={filter}
			/>
			<label class="inline-flex items-center gap-1.5 text-xs text-ink/70">
				<input type="checkbox" bind:checked={onlyMultiDialect} /> {m.lexemes_only_multidialect()}
			</label>
			<label class="inline-flex items-center gap-1.5 text-xs text-ink/70">
				<input type="checkbox" bind:checked={onlySenseSplit} /> {m.lexemes_only_sensesplit()}
			</label>
			<span class="ml-auto text-xs text-ink/60">{m.lexemes_results({ n: filtered.length.toLocaleString() })}</span>
		</div>

		<p class="text-xs text-ink/60">
			{m.lexemes_stats({
				total: stats.total.toLocaleString(),
				multi: stats.multiDialect.toLocaleString(),
				sense: stats.senseSplit.toLocaleString(),
				morph: stats.morphemeLinked.toLocaleString()
			})}
		</p>
	</header>

	<div class="overflow-x-auto rounded-2xl bg-white/70 ring-1 ring-rule">
		<table class="w-full border-collapse text-sm">
			<thead class="text-left text-[10px] uppercase tracking-widest text-ink/60">
				<tr class="border-b border-rule">
					<th class="px-3 py-2">{m.lexemes_col_lemma()}</th>
					<th class="px-3 py-2">{m.lexemes_col_kana()}</th>
					<th class="px-3 py-2">{m.lexemes_col_pos()}</th>
					<th class="px-3 py-2">{m.lexemes_col_gloss()}</th>
					<th class="px-3 py-2">{m.lexemes_col_morphemes()}</th>
					<th class="px-3 py-2">{m.lexemes_col_dialects()}</th>
					<th class="px-3 py-2 text-right">{m.lexemes_col_recordings()}</th>
				</tr>
			</thead>
			<tbody>
				{#each paged as r (r.id)}
					<tr class="border-b border-rule/50 align-top text-ink/85 odd:bg-paper/40 hover:bg-accent-soft/40">
						<td class="px-3 py-2 font-mono">
							<a class="text-accent hover:underline" href="/lexemes/{encodeURIComponent(r.id)}">
								{r.lemma}
							</a>
							{#if r.bound}<span class="ml-1 rounded-full bg-affix-soft px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-affix">bound</span>{/if}
						</td>
						<td class="px-3 py-2 text-[12px] text-ink/70">{r.kana || '—'}</td>
						<td class="px-3 py-2 text-[12px] text-ink/70">{r.pos ? categoryLabel(r.pos) : '—'}</td>
						<td class="px-3 py-2 text-[12px]">{r.gloss_jp || r.gloss_en || '—'}</td>
						<td class="px-3 py-2 font-mono text-[11px] text-ink/65">
							{#if r.morphemes.length}{r.morphemes.join(' + ')}{:else}—{/if}
						</td>
						<td class="px-3 py-2">
							{#each r.dialects as d}
								<span class="mr-1 inline-block rounded-full bg-leaf/10 px-2 py-0.5 text-[11px] text-leaf">{d}</span>
							{/each}
						</td>
						<td class="px-3 py-2 text-right font-mono text-[12px] text-ink/70">{r.recordings || '—'}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	{#if totalPages > 1}
		<nav class="flex items-center justify-center gap-1 text-xs text-ink/70">
			<button class="rounded-full px-3 py-1 ring-1 ring-rule disabled:opacity-50" disabled={page <= 1} onclick={() => (page -= 1)}>← {m.morphemes_prev()}</button>
			<span class="px-2 font-mono">{page} / {totalPages}</span>
			<button class="rounded-full px-3 py-1 ring-1 ring-rule disabled:opacity-50" disabled={page >= totalPages} onclick={() => (page += 1)}>{m.morphemes_next()} →</button>
		</nav>
	{/if}
</div>
