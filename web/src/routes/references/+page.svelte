<script lang="ts">
	import { allReferences, formatAuthor } from '$lib/references';
	import * as m from '$lib/paraglide/messages.js';

	const refs = allReferences();
</script>

<svelte:head>
	<title>{m.references_title()} — {m.app_title()}</title>
</svelte:head>

<div class="mx-auto flex min-h-screen max-w-4xl flex-col gap-6 px-6 py-10">
	<header class="flex flex-col gap-2">
		<a href="/" class="text-xs uppercase tracking-widest text-ink/60 hover:text-accent">← {m.back_home()}</a>
		<h1 class="text-3xl font-semibold tracking-tight">{m.references_title()}</h1>
		<p class="text-sm text-ink/60 max-w-2xl">{m.references_subtitle()}</p>
	</header>

	<ul class="flex flex-col gap-3">
		{#each refs as ref (ref.key)}
			<li
				id={encodeURIComponent(ref.key)}
				class="rounded-2xl bg-white/70 p-4 ring-1 ring-rule scroll-mt-6 target:ring-2 target:ring-accent"
			>
				<div class="flex flex-wrap items-baseline justify-between gap-2">
					<div class="flex-1 min-w-0 flex flex-col gap-1">
						<span class="text-xs font-mono text-ink/55">{ref.key}</span>
						{#if ref.title}
							<span class="text-base font-semibold leading-snug">{ref.title}</span>
						{/if}
						{#if ref.author || ref.date}
							<span class="text-sm text-ink/75">
								{#if ref.author}{formatAuthor(ref.author)}{/if}
								{#if ref.date}{ref.author ? ' · ' : ''}{ref.date}{/if}
							</span>
						{/if}
						{#if ref.journal || ref.publisher || ref.volume || ref.page_range}
							<span class="text-sm text-ink/65">
								{#if ref.journal}<em>{ref.journal}</em>{/if}{#if ref.volume}, vol. {ref.volume}{/if}{#if ref.issue}, no. {ref.issue}{/if}{#if ref.page_range}, pp. {ref.page_range}{/if}{#if ref.publisher}{ref.journal ? ' — ' : ''}{ref.publisher}{/if}
							</span>
						{/if}
					</div>
					<div class="flex flex-col items-end gap-1 text-xs">
						{#if ref.type}
							<span class="rounded-full bg-paper px-2 py-0.5 ring-1 ring-rule">{ref.type}</span>
						{/if}
					</div>
				</div>

				{#if ref.url || ref.doi || ref.isbn}
					<div class="mt-2 flex flex-wrap items-center gap-2 text-xs">
						{#if ref.url}
							<a
								href={ref.url}
								target="_blank"
								rel="noopener noreferrer"
								class="rounded-full bg-paper px-2 py-0.5 text-ink/80 ring-1 ring-rule transition hover:bg-accent-soft hover:text-accent hover:ring-accent/40"
							>
								{ref.url}
							</a>
						{/if}
						{#if ref.doi}
							<a
								href={`https://doi.org/${ref.doi}`}
								target="_blank"
								rel="noopener noreferrer"
								class="rounded-full bg-paper px-2 py-0.5 text-ink/80 ring-1 ring-rule transition hover:bg-accent-soft hover:text-accent hover:ring-accent/40"
							>
								doi:{ref.doi}
							</a>
						{/if}
						{#if ref.isbn}
							<span class="rounded-full bg-paper px-2 py-0.5 text-ink/70 ring-1 ring-rule">ISBN {ref.isbn}</span>
						{/if}
					</div>
				{/if}
			</li>
		{/each}
	</ul>
</div>
