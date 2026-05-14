#!/usr/bin/env node
// Copy morpheme_db/output/morpheme_database.json into the SvelteKit project
// so it can be bundled with the Worker (which has no filesystem at runtime).
//
// Run automatically before `bun run dev` and `bun run build` via the
// `predev`/`prebuild` scripts in package.json. Run manually after rebuilding
// the Python morpheme database.

import { copyFile, mkdir, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WEB_ROOT = path.resolve(__dirname, '..');
const SRC = path.resolve(WEB_ROOT, '../morpheme_db/output/morpheme_database.json');
const DEST = path.resolve(WEB_ROOT, 'src/lib/data/morpheme_database.json');

async function main() {
	try {
		await stat(SRC);
	} catch {
		console.warn(`[sync-database] source not found at ${SRC} — leaving the existing bundled copy in place.`);
		return;
	}
	await mkdir(path.dirname(DEST), { recursive: true });
	await copyFile(SRC, DEST);
	const info = await stat(DEST);
	const kb = (info.size / 1024).toFixed(1);
	console.log(`[sync-database] copied ${kb} KB → ${path.relative(WEB_ROOT, DEST)}`);
}

main().catch((err) => {
	console.error('[sync-database] failed:', err);
	process.exit(1);
});
