import type { Reroute } from '@sveltejs/kit';
import * as paraglide from '$lib/paraglide/runtime';

// SvelteKit's reroute runs in both server and client. Strip any locale
// prefix from the incoming URL so the file-based router sees the same path
// regardless of the active locale. Return only the pathname — including the
// search string would make SvelteKit treat the whole "?q=…" as part of the
// route and 404.
//
// Namespace-import the runtime so Vite's optimised-dep pre-bundle treats it
// as opaque — a named import has tripped a "does not provide an export named
// 'deLocalizeHref'" SyntaxError in the browser when the optimiser cached a
// stale version of the generated runtime.js.
export const reroute: Reroute = ({ url }) => paraglide.deLocalizeHref(url.pathname);
