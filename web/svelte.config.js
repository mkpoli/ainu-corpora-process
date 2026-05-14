import adapter from '@sveltejs/adapter-cloudflare';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	compilerOptions: {
		// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
		runes: ({ filename }) => (filename.split(/[/\\]/).includes('node_modules') ? undefined : true)
	},
	kit: {
		adapter: adapter({
			// Bundle the SvelteKit server into a single Worker entry. The
			// adapter wires up the static-assets binding for SvelteKit's
			// _app/* and any files under static/.
			platformProxy: { persist: false }
		})
	}
};

export default config;
