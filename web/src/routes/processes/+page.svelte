<script lang="ts">
	import * as m from '$lib/paraglide/messages.js';
	import LocaleSwitcher from '$lib/LocaleSwitcher.svelte';
</script>

<svelte:head>
	<title>{m.processes_title()} — {m.app_title()}</title>
</svelte:head>

<div class="mx-auto flex min-h-screen max-w-3xl flex-col gap-6 px-6 py-10">
	<header class="flex flex-col gap-2">
		<div class="flex items-center justify-between gap-3">
			<a href="/" class="text-xs uppercase tracking-widest text-ink/60 hover:text-accent">← {m.back_home()}</a>
			<LocaleSwitcher />
		</div>
		<h1 class="text-3xl font-semibold tracking-tight">{m.processes_title()}</h1>
		<p class="text-sm text-ink/60">{m.processes_subtitle()}</p>
	</header>

	<section
		id="zero_derivation"
		class="rounded-2xl border border-rule bg-white/70 p-5 scroll-mt-6 target:ring-2 target:ring-accent"
	>
		<h2 class="text-xl font-semibold">{m.processes_zero_deriv_title()}</h2>
		<p class="mt-2 whitespace-pre-line text-sm leading-relaxed text-ink/80">
			{m.processes_zero_deriv_body()}
		</p>
		<p class="mt-3 text-xs text-ink/60">
			<a
				href="/references#%E4%BD%90%E8%97%A42020%E3%82%A2%E3%82%A4%E3%83%8C%E8%AA%9E%E3%81%AB%E3%81%8A%E3%81%91%E3%82%8B%E6%96%87%E6%B3%95%E7%9A%84%E3%82%AB%E3%83%86%E3%82%B4%E3%83%AA%E3%83%BC%E3%81%AE%E8%BB%A2%E6%8F%9B%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6"
				class="rounded-full bg-paper px-2 py-0.5 text-ink/70 ring-1 ring-rule transition hover:bg-accent-soft hover:text-accent hover:ring-accent/40"
			>
				佐藤2020アイヌ語における文法的カテゴリーの転換について
			</a>
		</p>
	</section>
</div>
