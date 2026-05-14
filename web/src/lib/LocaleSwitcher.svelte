<script lang="ts">
	import { getLocale, locales, setLocale, type Locale } from '$lib/paraglide/runtime';
	import * as m from '$lib/paraglide/messages.js';

	const current = $derived(getLocale());

	const LABEL: Record<Locale, () => string> = {
		en: () => m.locale_en(),
		ja: () => m.locale_ja()
	};

	function switchTo(locale: Locale) {
		if (locale === current) return;
		// setLocale handles the active strategy (URL prefix + cookie) and
		// triggers a reload so the SSR'd messages reflect the new locale.
		setLocale(locale);
	}
</script>

<div class="inline-flex items-center gap-1 rounded-full bg-paper p-0.5 ring-1 ring-rule">
	{#each locales as locale}
		<button
			type="button"
			class="rounded-full px-2.5 py-0.5 text-xs font-medium transition
				{current === locale ? 'bg-ink text-paper' : 'text-ink/70 hover:bg-rule/40'}"
			onclick={() => switchTo(locale)}
			aria-pressed={current === locale}
		>
			{LABEL[locale]?.() ?? locale}
		</button>
	{/each}
</div>
