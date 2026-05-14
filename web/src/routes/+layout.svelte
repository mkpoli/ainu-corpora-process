<script lang="ts">
	import * as m from '$lib/paraglide/messages.js';
	import '../app.css';

	let { children } = $props();
</script>

<svelte:head>
	<title>{m.app_title()}</title>
	<meta name="description" content={m.app_subtitle()} />
</svelte:head>

{@render children()}
