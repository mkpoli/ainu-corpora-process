import type { Reroute } from '@sveltejs/kit';
import { deLocalizeHref } from '$lib/paraglide/runtime';

// SvelteKit's reroute runs in both server and client. Strip any locale
// prefix from the incoming URL so the file-based router sees the same path
// regardless of the active locale. Return only the pathname — including the
// search string would make SvelteKit treat the whole "?q=…" as part of the
// route and 404.
export const reroute: Reroute = ({ url }) => deLocalizeHref(url.pathname);
