<script lang="ts">
	import * as m from '$lib/paraglide/messages.js';
	import type { CompositionNode } from './types';
	import ValencyFrame from './ValencyFrame.svelte';
	import CompositionTree from './CompositionTree.svelte';

	const KIND_LABEL: Record<string, () => string> = {
		head: () => m.kind_head(),
		prefix: () => m.kind_prefix(),
		suffix: () => m.kind_suffix(),
		standalone: () => m.kind_standalone(),
		unknown: () => m.kind_unknown()
	};

	let {
		node,
		selectedId,
		depth = 0,
		onSelect
	}: {
		node: CompositionNode;
		selectedId: string | null;
		depth?: number;
		onSelect: (entryId: string) => void;
	} = $props();

	const KIND_STYLE: Record<string, string> = {
		head: 'border-accent/60 bg-accent-soft text-accent',
		prefix: 'border-affix/60 bg-affix-soft text-affix',
		suffix: 'border-affix/60 bg-affix-soft text-affix',
		standalone: 'border-leaf/60 bg-leaf-soft text-leaf',
		unknown: 'border-rule bg-paper text-ink/60 border-dashed'
	};

	const isLeaf = $derived(node.entry !== null || node.isLeaf);
	const isSelected = $derived(node.entry !== null && node.entry.id === selectedId);
	const sideIsPrefix = $derived(node.kind === 'prefix');

	function handleClick() {
		if (node.entry) onSelect(node.entry.id);
	}
</script>

<div class="flex flex-col items-center gap-3">
	{#if isLeaf}
		<button
			type="button"
			onclick={handleClick}
			disabled={!node.entry}
			class="group flex min-w-[7rem] flex-col items-center gap-1 rounded-2xl border px-4 py-2 shadow-sm transition disabled:cursor-default disabled:opacity-70
				{KIND_STYLE[node.kind] ?? 'border-rule bg-paper'}
				{isSelected ? 'ring-2 ring-accent ring-offset-2 ring-offset-paper' : 'hover:-translate-y-0.5 hover:shadow-md'}"
		>
			<span class="font-mono text-base leading-tight">{node.entry?.lemma ?? node.surface}</span>
			{#if node.entry?.glosses_en?.length}
				<span class="text-xs italic opacity-80">{node.entry.glosses_en[0]}</span>
			{:else if node.kind === 'unknown'}
				<span class="text-xs italic opacity-80">{m.kind_unknown()}</span>
			{/if}
			{#if node.entry?.morph_type}
				<span class="text-[10px] uppercase tracking-wider opacity-70">{node.entry.morph_type}</span>
			{/if}
		</button>
	{:else}
		<!-- Internal node: surface header with the effective valency, then the
		     two-child bracket below. -->
		<div
			class="flex flex-col items-center gap-1 rounded-2xl border border-rule bg-paper/70 px-3 py-1.5"
			title={`${node.kind} composition`}
		>
			<span class="font-mono text-sm text-ink/80">{node.surface}</span>
			{#if node.frame}
				<ValencyFrame frame={node.frame} compact />
			{/if}
		</div>

		<!-- Connector + bracket label -->
		<div class="flex flex-col items-center">
			<span class="h-3 w-px bg-rule"></span>
			<span class="rounded bg-paper px-1.5 py-[1px] font-mono text-[10px] uppercase tracking-widest text-ink/60 ring-1 ring-rule">
				{KIND_LABEL[node.kind]?.() ?? node.kind}
			</span>
			<span class="h-3 w-px bg-rule"></span>
		</div>

		<div class="flex flex-wrap items-start justify-center gap-6">
			{#if sideIsPrefix}
				{#if node.affix}
					<CompositionTree node={node.affix} {selectedId} depth={depth + 1} {onSelect} />
				{/if}
				{#if node.body}
					<CompositionTree node={node.body} {selectedId} depth={depth + 1} {onSelect} />
				{/if}
			{:else}
				{#if node.body}
					<CompositionTree node={node.body} {selectedId} depth={depth + 1} {onSelect} />
				{/if}
				{#if node.affix}
					<CompositionTree node={node.affix} {selectedId} depth={depth + 1} {onSelect} />
				{/if}
			{/if}
		</div>
	{/if}
</div>
