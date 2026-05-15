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

	<section
		id="reduplication"
		class="rounded-2xl border border-rule bg-white/70 p-5 scroll-mt-6 target:ring-2 target:ring-accent"
	>
		<h2 class="text-xl font-semibold">{m.processes_redup_title()}</h2>
		<p class="mt-2 whitespace-pre-line text-sm leading-relaxed text-ink/80">
			{m.processes_redup_body()}
		</p>
		<p class="mt-3 text-xs text-ink/60">
			<a
				href="/references#%E4%BD%90%E8%97%A42008%E3%82%A2%E3%82%A4%E3%83%8C%E6%96%87%E6%B3%95%E3%81%AE%E5%9F%BA%E7%A4%8E"
				class="rounded-full bg-paper px-2 py-0.5 text-ink/70 ring-1 ring-rule transition hover:bg-accent-soft hover:text-accent hover:ring-accent/40"
			>
				佐藤2008アイヌ文法の基礎
			</a>
		</p>
	</section>

	<section
		id="affixation"
		class="rounded-2xl border border-rule bg-white/70 p-5 scroll-mt-6 target:ring-2 target:ring-accent"
	>
		<h2 class="text-xl font-semibold">{m.processes_affixation_title()}</h2>
		<p class="mt-2 whitespace-pre-line text-sm leading-relaxed text-ink/80">
			{m.processes_affixation_body()}
		</p>
		<p class="mt-3 flex flex-wrap gap-2 text-xs text-ink/60">
			<a
				href="/references#%E3%83%96%E3%82%AC%E3%82%A8%E3%83%AF2014%E3%82%A2%E3%82%A4%E3%83%8C%E8%AA%9E%E4%BD%BF%E5%BD%B9%E6%A7%8B%E6%96%87%E3%81%AB%E9%96%A2%E3%81%99%E3%82%8B%E5%86%8D%E8%80%83%E5%AF%9F"
				class="rounded-full bg-paper px-2 py-0.5 text-ink/70 ring-1 ring-rule transition hover:bg-accent-soft hover:text-accent hover:ring-accent/40"
			>
				ブガエワ2014アイヌ語使役構文に関する再考察
			</a>
			<a
				href="/references#%E4%BD%90%E8%97%A42007%E3%82%A2%E3%82%A4%E3%83%8C%E8%AA%9E%E5%8D%83%E6%AD%B3%E6%96%B9%E8%A8%80%E3%81%AE%E5%86%8D%E5%B8%B0%E6%8E%A5%E9%A0%AD%E8%BE%9Eyay%E3%81%A8si%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6"
				class="rounded-full bg-paper px-2 py-0.5 text-ink/70 ring-1 ring-rule transition hover:bg-accent-soft hover:text-accent hover:ring-accent/40"
			>
				佐藤2007アイヌ語千歳方言の再帰接頭辞yayとsiについて
			</a>
		</p>
	</section>

	<section
		id="grammaticalization"
		class="rounded-2xl border border-rule bg-white/70 p-5 scroll-mt-6 target:ring-2 target:ring-accent"
	>
		<h2 class="text-xl font-semibold">{m.processes_grammaticalization_title()}</h2>
		<p class="mt-2 whitespace-pre-line text-sm leading-relaxed text-ink/80">
			{m.processes_grammaticalization_body()}
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
