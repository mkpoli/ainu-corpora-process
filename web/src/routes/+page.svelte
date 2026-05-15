<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import CompositionTree from '$lib/CompositionTree.svelte';
	import Etymology from '$lib/Etymology.svelte';
	import LocaleSwitcher from '$lib/LocaleSwitcher.svelte';
	import MorphemeDetail from '$lib/MorphemeDetail.svelte';
	import * as m from '$lib/paraglide/messages.js';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let inputValue = $state('');
	// User clicks override the auto-selected head; null means "use the head".
	let userSelectedId = $state<string | null>(null);
	// Inline-expand state for leaf chips. Click "..." to drill into a
	// morpheme's own composition / etymology without leaving the page.
	let expanded = $state(new Set<string>());

	function toggleExpand(entryId: string) {
		const next = new Set(expanded);
		if (next.has(entryId)) next.delete(entryId);
		else next.add(entryId);
		expanded = next;
	}

	const entryById = $derived.by(() => {
		const out: Record<string, typeof data.detailEntries[number]> = {};
		for (const e of data.detailEntries) out[e.id] = e;
		return out;
	});

	// data.query refreshes via SvelteKit's data prop after navigation. Keep
	// the input field in sync when the user picks a demo button or arrives
	// via a permalink with ?q=… set. When the page renders the default
	// example (no explicit query), surface that in the field too so the
	// user can edit it directly.
	$effect(() => {
		inputValue = data.query || data.resolvedQuery;
	});

	// Reset the user selection whenever the query changes so the head of the
	// new tree becomes the auto-focus, and clear any inline-expand state
	// since it belongs to the previous tree.
	$effect(() => {
		void data.resolvedQuery;
		userSelectedId = null;
		expanded = new Set<string>();
	});

	function defaultHeadId(): string | null {
		if (!data.composition) return null;
		// For any wrapper kind (fused, compound, or lexeme) the affix slot
		// holds the lexicalised / queried lemma — that's what should be
		// auto-selected. Falling through to body would walk us into the
		// underlying constituents.
		const root = data.composition.tree;
		if (
			(root.kind === 'fused' || root.kind === 'compound' || root.kind === 'lexeme') &&
			root.affix?.entry?.id
		) {
			return root.affix.entry.id;
		}
		let head = root.entry?.id ?? null;
		let cursor = root;
		while (!head && cursor.body) {
			cursor = cursor.body;
			head = cursor.entry?.id ?? null;
		}
		return head;
	}

	const selectedId = $derived(userSelectedId ?? defaultHeadId());

	const selectedEntry = $derived(
		selectedId ? data.detailEntries.find((e) => e.id === selectedId) ?? null : null
	);
	const selectedUses = $derived(
		selectedId ? (data.otherUses[selectedId] ?? []) : []
	);

	// The lexicalised head of the current composition, used to decide
	// whether the Composition region should show an etymology frame for the
	// looked-up word. For fused trees this is the wrapping lemma (inkar,
	// nukar, payoka, …); for atomic queries it's the directly-matched
	// entry.
	const compositionHead = $derived.by(() => {
		const tree = data.composition?.tree;
		if (!tree) return null;
		const isWrapper =
			tree.kind === 'fused' || tree.kind === 'compound' || tree.kind === 'lexeme';
		const headId = (isWrapper ? tree.affix?.entry?.id : null) ?? tree.entry?.id ?? null;
		if (!headId) return null;
		return data.detailEntries.find((e) => e.id === headId) ?? null;
	});

	function submit(event: SubmitEvent) {
		event.preventDefault();
		runQuery(inputValue.trim());
	}

	function runQuery(q: string) {
		const url = new URL(page.url);
		if (q) url.searchParams.set('q', q);
		else url.searchParams.delete('q');
		goto(url, { keepFocus: true });
	}

	function pickDemo(q: string) {
		inputValue = q;
		runQuery(q);
	}
</script>

<div class="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 px-6 py-10">
	<header class="flex flex-col gap-3">
		<div class="flex flex-wrap items-start justify-between gap-3">
			<div class="flex flex-col gap-1">
				<h1 class="text-3xl font-semibold tracking-tight">{m.app_title()}</h1>
				<p class="text-sm text-ink/60 max-w-2xl">{m.app_subtitle()}</p>
			</div>
			<div class="flex flex-col items-end gap-2">
				<div class="flex items-center gap-3 text-xs">
					<a
						href="/morphemes"
						class="text-ink/70 underline-offset-2 hover:text-accent hover:underline"
					>
						{m.morphemes_link()}
					</a>
					<a
						href="/processes"
						class="text-ink/70 underline-offset-2 hover:text-accent hover:underline"
					>
						{m.processes_link()}
					</a>
					<a
						href="/references"
						class="text-ink/70 underline-offset-2 hover:text-accent hover:underline"
					>
						{m.references_link()}
					</a>
					<LocaleSwitcher />
				</div>
				<dl class="flex flex-wrap justify-end gap-3 text-xs text-ink/60">
					<div class="rounded-lg bg-paper px-3 py-1.5 ring-1 ring-rule">
						<dt class="uppercase tracking-widest text-[10px]">{m.stats_entries()}</dt>
						<dd class="font-mono text-base text-ink">{data.stats.total.toLocaleString()}</dd>
					</div>
					<div class="rounded-lg bg-paper px-3 py-1.5 ring-1 ring-rule">
						<dt class="uppercase tracking-widest text-[10px]">{m.stats_curated()}</dt>
						<dd class="font-mono text-base text-ink">{data.stats.verified}</dd>
					</div>
					<div class="rounded-lg bg-paper px-3 py-1.5 ring-1 ring-rule">
						<dt class="uppercase tracking-widest text-[10px]">{m.stats_with_frame()}</dt>
						<dd class="font-mono text-base text-ink">{data.stats.withFrame}</dd>
					</div>
					<div class="rounded-lg bg-paper px-3 py-1.5 ring-1 ring-rule">
						<dt class="uppercase tracking-widest text-[10px]">{m.stats_with_category()}</dt>
						<dd class="font-mono text-base text-ink">{data.stats.withCategory}</dd>
					</div>
				</dl>
			</div>
		</div>

		<form class="flex flex-wrap items-center gap-3" onsubmit={submit}>
			<input
				type="search"
				name="q"
				bind:value={inputValue}
				placeholder={m.search_placeholder()}
				autocomplete="off"
				autocorrect="off"
				autocapitalize="off"
				spellcheck={false}
				class="w-full flex-1 rounded-2xl border border-rule bg-paper px-4 py-2.5 font-mono text-base shadow-inner focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30 sm:w-auto"
			/>
			<button
				type="submit"
				class="rounded-2xl bg-ink px-4 py-2.5 text-sm font-semibold text-paper transition hover:bg-accent disabled:opacity-50"
			>
				{m.search_button()}
			</button>
		</form>

		{#if data.families.length}
			<section class="flex flex-wrap items-center gap-x-2 gap-y-1.5 text-xs text-ink/60">
				<span class="uppercase tracking-widest text-[10px]">{m.try_label()}</span>
				{#each data.families as family, familyIndex (family.key)}
					{#if familyIndex > 0}
						<span aria-hidden="true" class="select-none text-ink/30">·</span>
					{/if}
					{#each family.examples as demo}
						<button
							type="button"
							onclick={() => pickDemo(demo)}
							class="rounded-full bg-paper px-2.5 py-0.5 font-mono ring-1 ring-rule transition hover:bg-accent-soft hover:ring-accent/40"
						>
							{demo}
						</button>
					{/each}
				{/each}
			</section>
		{/if}
	</header>

	<div class="grid grid-cols-1 gap-6 lg:grid-cols-[2fr_1fr]">
		<section class="flex flex-col gap-4 rounded-3xl bg-white/70 p-6 ring-1 ring-rule backdrop-blur">
			{#if data.composition}
				<div class="flex flex-wrap items-baseline justify-between gap-2">
					<h2 class="text-lg font-semibold">{m.composition_heading()}</h2>
					<div class="flex flex-wrap items-center gap-3 text-xs text-ink/60">
						<span>
							{m.composition_input()}: <span class="font-mono">{data.composition.input}</span>
						</span>
						<span>
							{m.composition_tokens()}: <span class="font-mono">{data.composition.tokens.join(' · ')}</span>
						</span>
					</div>
				</div>

				{#if data.composition.unseen}
					<div class="flex flex-col gap-1 rounded-xl bg-accent-soft px-3 py-2 text-xs text-accent">
						<strong class="text-sm">{m.unseen_word_title()}</strong>
						<span>{m.unseen_word_body({ word: data.composition.input })}</span>
					</div>
				{:else if data.composition.unresolved.length}
					<p class="rounded-xl bg-accent-soft px-3 py-2 text-xs text-accent">
						{m.unresolved_segments()}: <span class="font-mono">{data.composition.unresolved.join(', ')}</span>
					</p>
				{/if}

				{#if data.composition.source && data.composition.source !== 'unknown' && data.composition.source !== 'direct'}
					{@const sourceLabels = {
						composition: m.composition_source_composition(),
						split: m.composition_source_split(),
						segmented: m.composition_source_segmented()
					}}
					<p class="text-[11px] italic text-ink/55">
						{sourceLabels[data.composition.source as keyof typeof sourceLabels] ?? ''}
					</p>
				{/if}

				<!-- Wrapper has overflow-x:auto (forces overflow-y:auto in browsers),
				     so we pad py-3/px-3 to keep the 2px selection ring + offset
				     from being clipped by the scroll container. -->
				<div class="flex justify-center overflow-x-auto py-3 px-3">
					<div class="mx-auto flex justify-center">
						<CompositionTree
							node={data.composition.tree}
							{selectedId}
							onSelect={(id) => (userSelectedId = id)}
							subtrees={data.subtrees}
							{expanded}
							onToggleExpand={toggleExpand}
							{entryById}
							matchedEntryId={data.composition.matchedEntry?.id ?? null}
						/>
					</div>
				</div>

				{#if compositionHead?.etymology && !expanded.has(compositionHead.id)}
					<!-- Top-level etymology summary, shown only while the head's
					     leaf chip in the tree hasn't been expanded yet. Once the
					     user clicks "…" on the head, the leaf-level Etymology
					     takes over so we don't render it twice. -->
					<Etymology entry={compositionHead} />
				{/if}

				{#if data.composition.warnings.length}
					<details class="text-xs text-ink/60">
						<summary class="cursor-pointer select-none">{m.warnings_summary()}</summary>
						<ul class="mt-1 list-disc pl-5">
							{#each data.composition.warnings as w}
								<li>{w}</li>
							{/each}
						</ul>
					</details>
				{/if}
			{:else}
				<div class="flex flex-col items-center gap-3 py-12 text-center text-ink/60">
					<p class="max-w-md text-sm">{m.empty_state_help()}</p>
					{#if data.suggestions.morphemes.length}
						<div class="flex flex-wrap justify-center gap-1.5">
							{#each data.suggestions.morphemes.slice(0, 18) as morph}
								<button
									type="button"
									class="rounded-full bg-paper px-2.5 py-0.5 font-mono text-xs ring-1 ring-rule transition hover:bg-leaf-soft hover:ring-leaf/40"
									onclick={() => pickDemo(morph.lemma)}
								>
									{morph.lemma}
								</button>
							{/each}
						</div>
					{/if}
				</div>
			{/if}
		</section>

		<aside class="flex flex-col gap-4 rounded-3xl bg-white/70 p-6 ring-1 ring-rule backdrop-blur">
			<MorphemeDetail
				entry={selectedEntry}
				otherUses={selectedUses}
				onSelectLemma={pickDemo}
			/>
		</aside>
	</div>

</div>
