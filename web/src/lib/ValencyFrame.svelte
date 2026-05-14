<script lang="ts">
	import * as m from '$lib/paraglide/messages.js';
	import type { ValencyFrame } from './types';

	let { frame, compact = false }: { frame: ValencyFrame | null; compact?: boolean } = $props();

	const REALIZATION_LABEL: Record<string, () => string> = {
		external: () => m.realization_external(),
		internal_incorp: () => m.realization_internal_incorp(),
		internal_refl: () => m.realization_internal_refl(),
		internal_indef: () => m.realization_internal_indef(),
		absorbed: () => m.realization_absorbed()
	};

	const REALIZATION_STYLE: Record<string, string> = {
		external: 'bg-leaf-soft text-leaf border-leaf/40',
		internal_incorp: 'bg-affix-soft text-affix border-affix/40',
		internal_refl: 'bg-accent-soft text-accent border-accent/40',
		internal_indef: 'bg-affix-soft text-affix border-affix/40',
		absorbed: 'bg-rule/30 text-ink/60 border-rule line-through'
	};

	const arity = $derived(
		frame ? frame.slots.filter((s) => s.realization === 'external').length : 0
	);
</script>

{#if frame}
	{#if compact}
		<span class="font-mono text-xs text-ink/70">⟨{arity}⟩</span>
	{:else}
		<div class="flex flex-wrap items-center gap-1.5">
			<span class="rounded-full bg-ink/85 px-2 py-0.5 text-xs font-medium text-paper">
				{m.frame_arity({ n: arity })}
			</span>
			{#each frame.slots as slot}
				<span
					class="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs {REALIZATION_STYLE[
						slot.realization
					] ?? 'border-rule bg-paper'}"
					title={REALIZATION_LABEL[slot.realization]?.() ?? slot.realization}
				>
					<span class="font-mono lowercase">{slot.role}</span>
					{#if slot.label_jp}
						<span class="text-ink/60">· {slot.label_jp}</span>
					{/if}
				</span>
			{/each}
		</div>
	{/if}
{/if}
