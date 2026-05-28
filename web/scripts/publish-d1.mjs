#!/usr/bin/env node
/**
 * Versioned D1 publish pipeline for the Ainu morpheme database.
 *
 *   bun run publish:d1
 *
 * Steps (idempotent within a timestamp):
 *  1. Rebuild morpheme_db/output/morpheme_database.sql via the Python exporter.
 *  2. Mint a new D1 database named `ainu-mdb-<YYYYMMDD-HHMM>` (UTC).
 *     If `--reuse <name>` is given, skip creation and import into that db.
 *  3. Import the SQL dump via `wrangler d1 execute … --file=… --remote`.
 *  4. Rewrite wrangler.jsonc so the `DB` binding points at the new db.
 *
 * Deploy with `bun run deploy` after this completes.
 *
 * Why a new database per push? Cloudflare's docs recommend treating D1
 * imports as a fresh-database operation rather than a destructive overwrite
 * of a live db, because reimport requires DROP/CREATE and there's no native
 * transaction across the whole import.
 * See: https://developers.cloudflare.com/d1/best-practices/import-export-data/
 */

import { execFileSync, spawnSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WEB_ROOT = path.resolve(__dirname, '..');
const REPO_ROOT = path.resolve(WEB_ROOT, '..');
const SQL_FILE = path.resolve(REPO_ROOT, 'morpheme_db/output/morpheme_database.sql');
const WRANGLER_CONFIG = path.resolve(WEB_ROOT, 'wrangler.jsonc');

function utcTimestamp() {
	const now = new Date();
	const pad = (n) => String(n).padStart(2, '0');
	return (
		now.getUTCFullYear().toString() +
		pad(now.getUTCMonth() + 1) +
		pad(now.getUTCDate()) +
		'-' +
		pad(now.getUTCHours()) +
		pad(now.getUTCMinutes())
	);
}

function run(cmd, args, opts = {}) {
	const result = spawnSync(cmd, args, { stdio: 'inherit', cwd: WEB_ROOT, ...opts });
	if (result.status !== 0) {
		throw new Error(`${cmd} ${args.join(' ')} exited with code ${result.status}`);
	}
}

function captured(cmd, args) {
	const out = execFileSync(cmd, args, { cwd: WEB_ROOT, encoding: 'utf-8' });
	return out;
}

function rebuildSqlDump() {
	console.log('▸ Rebuilding SQL dump via morpheme_db.export_sqlite …');
	run('uv', ['run', 'python', '-m', 'morpheme_db.export_sqlite'], { cwd: REPO_ROOT });
}

function createD1(name) {
	console.log(`▸ Creating D1 database '${name}' …`);
	const stdout = captured('bunx', ['wrangler', 'd1', 'create', name]);
	const idMatch = stdout.match(/"database_id":\s*"([0-9a-f-]+)"/);
	if (!idMatch) {
		console.error(stdout);
		throw new Error('could not parse database_id from wrangler output');
	}
	return idMatch[1];
}

function importSql(name) {
	console.log(`▸ Importing SQL into '${name}' (remote) …`);
	run('bunx', ['wrangler', 'd1', 'execute', name, '--remote', `--file=${SQL_FILE}`]);
}

function updateWranglerConfig(name, id) {
	const raw = readFileSync(WRANGLER_CONFIG, 'utf-8');
	const bindingBlock = `	"d1_databases": [
		{
			"binding": "DB",
			"database_name": "${name}",
			"database_id": "${id}"
		}
	],`;

	// The stub starts commented out (``// "d1_databases": [ … ],``) and
	// gets uncommented on first publish. Subsequent publishes need to
	// rewrite the active block. Match both shapes — the inactive form
	// (every line prefixed with ``// ``) and the live block.
	const commentedBlock = /\t(?:\/\/\s*)?"d1_databases":\s*\[(?:[\s\S]*?(?:\/\/\s*)?)*?\],?/;
	const liveBlock = /\t"d1_databases":\s*\[[\s\S]*?\],?/;

	let updated;
	let anchorFound = true;
	if (liveBlock.test(raw)) {
		updated = raw.replace(liveBlock, bindingBlock);
	} else if (commentedBlock.test(raw)) {
		updated = raw.replace(commentedBlock, bindingBlock);
	} else {
		const assetsBlock = /(\t"assets":\s*\{[\s\S]*?\}\s*,)/;
		anchorFound = assetsBlock.test(raw);
		updated = raw.replace(assetsBlock, `$1\n${bindingBlock}`);
	}

	if (!anchorFound) {
		throw new Error(
			'failed to update wrangler.jsonc — no d1_databases anchor found and no assets block to insert after',
		);
	}

	writeFileSync(WRANGLER_CONFIG, updated);
	console.log(`▸ Updated ${path.basename(WRANGLER_CONFIG)} → binding 'DB' → ${name}`);
}

function main() {
	const args = process.argv.slice(2);
	const reuseIndex = args.indexOf('--reuse');
	let name;
	let id;

	rebuildSqlDump();

	if (reuseIndex !== -1) {
		name = args[reuseIndex + 1];
		if (!name) throw new Error('--reuse expects a database name');
		// Look up the id from `wrangler d1 list`.
		const list = captured('bunx', ['wrangler', 'd1', 'list', '--json']);
		const dbs = JSON.parse(list);
		const match = dbs.find((d) => d.name === name);
		if (!match) throw new Error(`D1 database '${name}' not found in account`);
		id = match.uuid ?? match.database_id ?? match.id;
	} else {
		name = `ainu-mdb-${utcTimestamp()}`;
		id = createD1(name);
	}

	importSql(name);
	updateWranglerConfig(name, id);

	console.log('\n✓ D1 publish complete. Next: bun run deploy');
}

try {
	main();
} catch (err) {
	console.error('publish-d1 failed:', err.message ?? err);
	process.exit(1);
}
