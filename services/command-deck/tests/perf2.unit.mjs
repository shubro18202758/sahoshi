/**
 * FIX-E-PERF2 unit test (round 2) — the per-language packs, their loading on
 * the SHIPPED (production) path, and the split icon set.
 *
 *   node tests/perf2.unit.mjs                       # the checks
 *   node tests/perf2.unit.mjs --print-golden <src>  # recompute the golden from a tree (review aid)
 *
 * 1. Strings never change, per module × language × copy. PACK_GOLDEN below
 *    was computed ONCE from main's pre-split packs (`--print-golden` on main's
 *    src, reviewed) and is written into this file: for every one of the 16
 *    pack modules and each language, the key count and a sha256 of the
 *    canonical (key, initializer source text) list. Every copy is checked ON
 *    ITS OWN against it — EN in the base module; HI and BN in the `.hi.ts` /
 *    `.bn.ts` modules (the copy that runs: the server, vite dev, the tests and
 *    the production browser all import it); and, for the four packs two AST
 *    readers still read as text (packs, packs.map, packs.workspace,
 *    packs.agent), the never-registered text mirror in the base module. No
 *    merging by key name, no git: a changed value, a dropped or added key in
 *    any one copy fails. The other twelve base modules hold no HI/BN literal
 *    at all (one source of truth).
 * 2. Loading on the production path. The pack modules, lib/i18n/load.ts and
 *    the ops store are bundled with the PRODUCTION client defines
 *    (process.env.NODE_ENV='production', import.meta.env.SSR=false) — the
 *    branch that registers every language eagerly folds away exactly as in
 *    the shipped build — and each path is driven in a fresh module instance:
 *      a. a switch (`ensureLang`) lands HI, then BN, for EVERY one of the 16
 *         modules (one sampled key per module, compared with its .hi/.bn
 *         value); while a chunk is in flight t() answers EN, never a raw key;
 *         the registration hook fires (the re-render signal);
 *      b. the cold path: `<html lang="bn">` set before the modules evaluate →
 *         every module's BN strings are in before evaluation finishes (what
 *         hydration waits for), HI is not fetched;
 *      c. the ops store's `lang` setter alone, and `adoptLangCookie()` alone
 *         (sahoshi_lang cookie), each land the language for all 16 modules;
 *      d. a real Svelte 5 `$effect` reading t() re-runs once the chunk lands
 *         (svelte compiled for the client; flushSync), showing HI.
 * 3. Icons. `ICONS_16` / `ICONS_20` are complete, frozen and in main's order
 *    with main's path data (golden hashes); in the production bundle
 *    `isIconName` knows all 206 names before anything loads, a deferred glyph
 *    has no paths until `loadRestIcons()` lands and then every name resolves
 *    at 16 and 20 px. The first-paint half is EXACTLY the pinned
 *    first-viewport sets plus the map-marker glyphs (every KIND_ICON /
 *    EVENT_KIND_ICON glyph) plus the canvas's Layers / Legend panel glyphs. With a production build present, the server
 *    render of `/`, `/ops` and `/gods-eye` (EN/HI/BN) is collected and every
 *    glyph it draws must be in the first-paint half and in that route's
 *    pinned set (tests/perf2-prod-smoke.mjs checks the browser's first
 *    viewport for blank glyphs).
 *
 * Exits 0 with `ok` lines, 1 on any failure.
 */

import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { WORKSPACE } from './lib/routes.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DECK = path.resolve(HERE, '..');
const require = createRequire(path.join(DECK, 'package.json'));
const ts = require('typescript');

const MODULES = [
	'strings', 'strings.ops', 'strings.citizen', 'packs', 'packs.ui', 'packs.wall', 'packs.views', 'packs.decisions',
	'packs.dss', 'packs.analysis', 'packs.assistant', 'packs.osint', 'packs.corridor', 'packs.map', 'packs.workspace', 'packs.agent',
];
/** The four packs tests/thermal-toolbar.unit.mjs and tests/omnibar-lookup.unit.mjs read as text (FIX-E-PERF2 blocked request). */
const MIRRORED = new Set(['packs', 'packs.map', 'packs.workspace', 'packs.agent']);
const LANGS = ['en', 'hi', 'bn'];

// ── the canonical form of one pack literal ───────────────────────────────────

function unwrap(n) {
	while (n && (ts.isAsExpression(n) || ts.isSatisfiesExpression?.(n) || ts.isParenthesizedExpression(n))) n = n.expression;
	return n;
}

/** Top-level `[export] const <name> = { … }` object literals of a file, by name. */
function packLiterals(file) {
	const sf = ts.createSourceFile(file, readFileSync(file, 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
	const out = {};
	for (const st of sf.statements) {
		if (!ts.isVariableStatement(st)) continue;
		for (const d of st.declarationList.declarations) {
			const init = unwrap(d.initializer);
			if (ts.isIdentifier(d.name) && init && ts.isObjectLiteralExpression(init)) out[d.name.text] = { sf, obj: init };
		}
	}
	return out;
}

/** key → { text (whitespace-normalised initializer source), value (a plain string literal's value, else null) }. */
function entries({ sf, obj }) {
	const map = new Map();
	let odd = 0;
	for (const p of obj.properties) {
		if (!ts.isPropertyAssignment(p) || !(ts.isIdentifier(p.name) || ts.isStringLiteral(p.name))) {
			odd++;
			continue;
		}
		const init = p.initializer;
		const lit = ts.isStringLiteral(init) || ts.isNoSubstitutionTemplateLiteral(init) ? init.text : null;
		map.set(p.name.text, { text: init.getText(sf).replace(/\s+/g, ' ').trim(), value: lit, dup: map.has(p.name.text) });
	}
	return { map, odd };
}

function digest(lit) {
	const { map, odd } = entries(lit);
	const lines = [...map.entries()].sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)).map(([k, v]) => `${k}\u0000${v.text}`);
	return { count: map.size, sha: createHash('sha256').update(lines.join('\n')).digest('hex'), odd };
}

// ── --print-golden: recompute the table from a tree (pre-split or split src) ──
// HI/BN are read from the per-language module (`<m>.hi.ts`, `<m>.bn.ts`: the copy that runs) when the tree has
// one, else from the base module's literal (main's pre-split packs). Review the printed rows before pasting them.

if (process.argv[2] === '--print-golden') {
	const dir = path.join(process.argv[3], 'lib/i18n');
	const table = {};
	for (const m of MODULES) {
		const lits = packLiterals(path.join(dir, `${m}.ts`));
		for (const l of ['hi', 'bn']) {
			const split = path.join(dir, `${m}.${l}.ts`);
			if (existsSync(split)) lits[l] = packLiterals(split)[l];
		}
		table[m] = {};
		for (const l of LANGS) {
			if (!lits[l]) throw new Error(`${m}: no const ${l} literal`);
			const d = digest(lits[l]);
			table[m][l] = [d.count, d.sha];
		}
	}
	console.log(JSON.stringify(table, null, '\t'));
	process.exit(0);
}

/**
 * The golden: main's packs before the split (VVIP main, the base this work
 * package is cut against), per module × language: [key count, sha256 of the
 * sorted (key, initializer source) list]. Recompute with --print-golden.
 * Since the split, a row changes only with a reviewed copy change and says why at its end (2026-10-28: the
 * Sahoshi rename and the Gujarati → Bengali switch; the split packs are digested EN from the base module and
 * HI/BN from the `.hi.ts`/`.bn.ts` modules, exactly as the checks below read them).
 */
const PACK_GOLDEN = {
	// Re-derived 2026-10-28 (Sahoshi): the Bengali packs (danda sentence ends), the Kolkata EN/HI copy, and the merged streams' pack edits — recomputed with `--print-golden src` after every stream merged.
	// 2026-10-29 (UI audit): strings.citizen gains map_title / map_credits (the citizen map's accessible name); packs HI band words in Hindi.
	// 2026-10-29 (look): packs nav_citizen / nav_driver say "Your road" and "Ambulance (108)" in all three languages.
	// 2026-10-29 (look, round 2): packs.decisions dec_live_movement says "Protected movement" (not "VVIP") in all three languages.
	'strings': { en: [146, '3eb5587af4790de100b40a9bae8b75235d0a05c25cf5fbcb2fee2e5116fc7da0'], hi: [146, '11d5788965ac7584b895b95e73cdaaccbc32f636a8d1acf7347cd5d79133e29a'], bn: [146, 'a1858c295e29999dd874a6597fd90c6ebe80d82422f70042e1e80ce1313802ad'] },
	'strings.ops': { en: [438, 'df2a64a61f561a8ea444e72a8629dedb67029b0b867f3c5faedca98b3d6f40f8'], hi: [438, 'a15d4339be4e0e76069121c3fc9f038be1c03a4cd91f59bfdf36e890fda6371f'], bn: [438, '53300ddb8b8ab714eee67ec3bdf5b769d5582b5a97f497296193e7563a991f58'] },
	'strings.citizen': { en: [205, 'be6fa4c9773cc7dd431fb03ac0a85ddccc2bbab3bcf820daa393df2987737bf7'], hi: [205, 'a02687be419746ff41109b8babf2dc6581a7d68677028410ecbe162c50e7abd7'], bn: [205, '99a9ffaeddd346ea46ac7e5d228171d25bcb963e58690a351dd261fee041729e'] },
	'packs': { en: [390, 'c2196d3b5d3b1bd69cac8fd528fea747d2ef2ea6d73f741b7bf658020e7c1d42'], hi: [390, 'e985a217fa57808d57226b9bcfc4dff2a68a6561e151c376421ac37a61414f96'], bn: [390, 'cacc8f462f4567b5852982af610adcf4ea3e0ec800e46e1d7a4591da8ba33cdb'] },
	'packs.ui': { en: [77, '336571b9c2618b1f5a04460921c2071561d77c328e72959512b7757c5ab10e10'], hi: [77, '0b50bf2c25811a196aad26e73662f949fee8b30f3aab17d89ca0e55f4dbfc376'], bn: [77, '41019938c39a785c8a9ccc6fd901731c045a5f22845e5d4be6b5f1248ffaf39b'] },
	'packs.wall': { en: [358, 'd7d2d6dc7448c87859689955cb90fe8ba4e487e3c999d3202fdea440d075b9a7'], hi: [358, '16a48ed8fd550fbabee3bee346c9654d78299be01a656237f4f4b3cf030596cf'], bn: [358, '03cc0675fc6f2674868ca529e987d6217d29c9346e60c8dd0c370f0129c5064c'] },
	'packs.views': { en: [229, '98a28fe74628344d747b42ff18af4fe7018a25dff31f8ee374e0d4e972a7ba08'], hi: [229, '518219e53accd6c8b5f7b4265a8fd00050ef6b1cb7c293e3e68f2aa79d57b6c2'], bn: [229, '88ae04de0d97e1d40060f72b57005e97e7a8d649acb35f36a6893449c9e98fd4'] },
	'packs.decisions': { en: [307, '070745b59961087cc586a07a9af65623d3ff37b9f09741269f8d75df890e1a3f'], hi: [307, 'a1948d811c5061110acdf91dd8f9084473a976c5da141f1ef7bb3ad6500b1259'], bn: [307, '6b9856f6db602750c469d9906cf4e8f4f41a40a8263b582833c7727ab6528c72'] },
	'packs.dss': { en: [115, 'b25153a715932d2f8207d8859d42dade04a34451939c3fdbeabc6d2a6331bff4'], hi: [115, '9d71078d6f862d5aeac9f49f9673765dc171670796a01aae5dc0a466d7efb488'], bn: [115, 'f4cb5c10ec2097d1d14b8d1df18edd8e4f139f2b311e9fc3addb178a671f672b'] },
	'packs.analysis': { en: [168, '493a23b005d3e02ac47ea00ccd3d89a0242bc7500ea5a674cc45c837591b305e'], hi: [168, '410466f50de291dd5e8a1e9cdd293314777709668b35dc29e48a291565dd6a46'], bn: [168, 'db0d8025e832c1ce5d93482eec695bd140fb99d79a52b9851cbe4ff05d953ef6'] },
	'packs.assistant': { en: [38, 'af4bb64b66c21e42eaea9fce14058ec133fe434f8be1c27ec56c1965aaf075b8'], hi: [38, '45e5f285d426a55b6638ff18b45e41a739fc4fe707ff85dc7905ffbb9d2a820e'], bn: [38, '6711e35062c51696dc1484977608749890e0b237049ab7f35b15446390daf8c9'] },
	'packs.osint': { en: [72, '12da05b1c89b0b6ae8239f991a69feb0a99053593c22785a255d37e8bf3eb201'], hi: [72, 'a34c6e32dbbfa5ecdf7ccdd6118c0cc7781441ad0e24fb14afdca0ff9b118117'], bn: [72, 'bd72c4b08f834c32be6778159a54bda14191a48ad9a4cdd5a4fcbdbc4e2e585a'] },
	'packs.corridor': { en: [81, 'edd81f6987321cece7dfb3c4c9ad45a0190860a6839686297fb4113926ba1049'], hi: [81, 'd007c06776943ab06a0d868c3f1484d8b6bae1e48dd6db1c26ebee4e6bd87f3e'], bn: [81, 'c1491a64bce2d6f6dd5645360d75648b712c469c3c0029224117bb67e0173c17'] },
	'packs.map': { en: [101, '6cf7c2b55e7e1d74be3bf846fc644d5e67fc6a6f83650e92a03ed5409a03abb7'], hi: [101, '291c2d552140735837313581834865e3740d1a663d56cbf3d3e1ef311347413f'], bn: [101, 'c9b77e8d768ace7072905aec5094a8415d45c23f761ee4c0e74af272d0f06a17'] },
	'packs.workspace': { en: [436, '20251af95f3eb9af851d47242739988019036454b8269327c626a41b495e4c9e'], hi: [436, '68444cc11cc6820697c38ccc8a2a5bd4077ca9e7167f7f489c4cd366e6347d8c'], bn: [436, '12456a02c7c5af34c864c90e2e93e5fffb49e735bfcb4adaead9b24a55e6db93'] },
	'packs.agent': { en: [54, '8915524394e87e2c5d5c06e9afd3f141d7b0d6a960b574a0751afbd2cf360f2c'], hi: [54, 'e0b9ebecbbb8210eacd0def679ebe00b12b7c051c07699bb2ccfcce1a2bac555'], bn: [54, 'e40ea9911986e74b06c352056ceace9db4de1c59e308b1201fcb86a049c87689'] },
};

/**
 * The golden icon tables: main's ICONS_16 / ICONS_20 before the split — the
 * name count, a sha256 of the names in table order, and a sha256 of the
 * name+paths list in table order.
 */
const ICON_GOLDEN = {
	n16: 206,
	order16: '6522ab22c7e4f7de6d82dc1f59e82a866065145f0c92e6859f8eb575cca6985d',
	paths16: 'c987a82ad9cf052a81a006a5b6d06f31542ad85347fe467b4a3313a9529d4f16',
	n20: 24,
	paths20: '06aa6824a60a3def1800f6c4f8e7de0e26f06ff239e889c8e601d01dedbba5d2',
};

let failures = 0;
function ok(name, cond, detail = '') {
	if (cond) console.log(`ok   ${name}${detail ? ` — ${detail}` : ''}`);
	else {
		failures++;
		console.error(`FAIL ${name}${detail ? ` — ${detail}` : ''}`);
	}
}

const I18N = path.join(DECK, 'src/lib/i18n');

// ── 1. strings, per module × language × copy ─────────────────────────────────

/**
 * One sampled key per module (a plain string in all three languages, translated), with its HI and BN values. The key
 * is one NO other module defines: registration is first-wins, so a key two modules share (the six OSINT event kinds
 * live in both strings and packs.osint) answers from whichever registered first and cannot prove this module's chunk
 * landed.
 */
const SAMPLE = {};
const OWNERS = new Map(); // EN key → how many of the 16 modules define it
for (const m of MODULES) {
	const lit = packLiterals(path.join(I18N, `${m}.ts`)).en;
	if (lit) for (const k of entries(lit).map.keys()) OWNERS.set(k, (OWNERS.get(k) ?? 0) + 1);
}
for (const m of MODULES) {
	const base = packLiterals(path.join(I18N, `${m}.ts`));
	const copies = [['en', 'base module', base.en]];
	for (const l of ['hi', 'bn']) {
		const f = path.join(I18N, `${m}.${l}.ts`);
		copies.push([l, `${m}.${l}.ts (the copy that runs)`, existsSync(f) ? packLiterals(f)[l] : undefined]);
		// the text mirror may go once the two AST readers read the per-language modules (blocked request): while it exists it is pinned too
		if (MIRRORED.has(m) && base[l]) copies.push([l, 'base-module text mirror', base[l]]);
	}
	for (const [l, where, lit] of copies) {
		const want = PACK_GOLDEN[m]?.[l];
		if (!lit) {
			ok(`strings: ${m} ${l} — ${where} present`, false, 'no such object literal');
			continue;
		}
		const d = digest(lit);
		ok(
			`strings: ${m} ${l} — ${where} matches main (${d.count} keys)`,
			!!want && d.count === want[0] && d.sha === want[1] && d.odd === 0,
			want ? `count ${d.count}/${want[0]} sha ${d.sha.slice(0, 12)}/${want[1].slice(0, 12)}${d.odd ? ` · ${d.odd} non-literal members` : ''}` : 'no golden',
		);
	}
	if (!MIRRORED.has(m)) ok(`strings: ${m} base module holds no HI/BN literal (one source of truth)`, !base.hi && !base.bn);
	const en = base.en && entries(base.en).map;
	const hi = existsSync(path.join(I18N, `${m}.hi.ts`)) ? entries(packLiterals(path.join(I18N, `${m}.hi.ts`)).hi).map : new Map();
	const bn = existsSync(path.join(I18N, `${m}.bn.ts`)) ? entries(packLiterals(path.join(I18N, `${m}.bn.ts`)).bn).map : new Map();
	const key = en && [...en.keys()].sort().find((k) => OWNERS.get(k) === 1 && en.get(k).value && hi.get(k)?.value && bn.get(k)?.value && hi.get(k).value !== en.get(k).value && bn.get(k).value !== en.get(k).value);
	if (key) SAMPLE[m] = { key, en: en.get(key).value, hi: hi.get(key).value, bn: bn.get(key).value };
	ok(`strings: ${m} has a sampled key for the loading checks`, !!key, key ?? 'none');
}
for (const m of MIRRORED) {
	const src = readFileSync(path.join(I18N, `${m}.ts`), 'utf8');
	const mirror = /\nconst (hi|bn)\b/.test(src);
	ok(
		`strings: ${m}'s text mirror (if still present) is never registered — astTextMirror declared, never called`,
		!mirror || (/function astTextMirror\(\)/.test(src) && (src.match(/astTextMirror\s*\(/g) ?? []).length === 1 && !/registerPack\('(hi|bn)', (hi|bn)\)/.test(src.replace(/function astTextMirror\(\)[\s\S]*?\n\}/, ''))),
		mirror ? 'mirror present' : 'no mirror',
	);
}
// the samples must be distinct keys across modules so each probes its own module
const sampleKeys = Object.values(SAMPLE).map((s) => s.key);
ok('strings: the 16 sampled keys are distinct (each probes its own module)', new Set(sampleKeys).size === sampleKeys.length && sampleKeys.length === 16, sampleKeys.length + ' keys');

// ── 2. loading on the production path ────────────────────────────────────────

const esbuild = require('esbuild');
const OUT_DIR = process.env.PERF2_UNIT_OUT ?? path.join(os.tmpdir(), 'sahoshi-perf2-unit');
mkdirSync(OUT_DIR, { recursive: true });
const PROD_DEFINE = { 'process.env.NODE_ENV': '"production"', 'import.meta.env.SSR': 'false', 'import.meta.env.DEV': 'false', 'import.meta.env.PROD': 'true' };
const stubApp = {
	name: 'stub-app',
	setup(b) {
		b.onResolve({ filter: /^\$(app|env)\// }, (a) => ({ path: a.path, namespace: 'stub-app' }));
		b.onLoad({ filter: /.*/, namespace: 'stub-app' }, () => ({ contents: 'export const browser = false, dev = false, building = false; export const goto = async () => {}; export const page = {}; export const navigating = {}; export const env = {};', loader: 'js' }));
	},
};
const IMPORTS = MODULES.map((m) => `import './src/lib/i18n/${m}';`).join('\n');

async function bundle(name, contents, extra = {}) {
	const outfile = path.join(OUT_DIR, `${name}.mjs`);
	const r = await esbuild.build({
		stdin: { contents, resolveDir: DECK, loader: 'ts', sourcefile: `${name}-entry.ts` },
		absWorkingDir: DECK,
		alias: { $lib: './src/lib' },
		bundle: true,
		format: 'esm',
		platform: 'node',
		define: PROD_DEFINE,
		outfile,
		logLevel: 'silent',
		loader: { '.svelte': 'empty' },
		plugins: [stubApp],
		...extra,
	});
	ok(`bundle ${name} builds with the production client defines`, r.errors.length === 0, `${r.errors.length} errors`);
	return outfile;
}
let instance = 0;
const fresh = (file) => import(`${pathToFileURL(file).href}?i=${++instance}`);

// runes as identity macros for the stores (as tests/wall.unit.mjs runs them)
globalThis.$state = Object.assign((v) => v, { raw: (v) => v, snapshot: (v) => v });
globalThis.$derived = Object.assign((v) => v, { by: (f) => f() });
globalThis.$effect = Object.assign(() => {}, { root: () => () => {}, pre: () => {} });

const covered = (t, lang) => MODULES.filter((m) => SAMPLE[m] && t(lang, SAMPLE[m].key) === SAMPLE[m][lang]);
const missingOf = (t, lang) => MODULES.filter((m) => !SAMPLE[m] || t(lang, SAMPLE[m].key) !== SAMPLE[m][lang]);
const settle = async (cond, ms = 3000) => {
	const end = Date.now() + ms;
	while (!cond() && Date.now() < end) await new Promise((r) => setTimeout(r, 10));
	return cond();
};

const LOADER = await bundle('perf2-loader', `${IMPORTS}\nexport * as L from './src/lib/i18n/load';\nexport { t } from './src/lib/i18n/strings';\n`);
{
	// a. a switch
	delete globalThis.document;
	delete globalThis.window;
	const { L, t } = await fresh(LOADER);
	let bumps = 0;
	L.setPacksRegisteredHook(() => bumps++);
	const preHi = covered(t, 'hi');
	ok('prod path: nothing but EN is registered before any language is asked for (the eager branch folded away)', preHi.length === 0, preHi.join(', ') || 'none in');
	const flight = L.ensureLang('hi');
	const during = MODULES.filter((m) => SAMPLE[m] && t('hi', SAMPLE[m].key) !== SAMPLE[m].en && t('hi', SAMPLE[m].key) !== SAMPLE[m].hi);
	ok('prod path: while the HI chunks are in flight t() answers EN — never a raw key', during.length === 0, during.join(', ') || 'EN fallback everywhere');
	await flight;
	ok('prod path: ensureLang("hi") lands HI for all 16 pack modules', missingOf(t, 'hi').length === 0, missingOf(t, 'hi').join(', ') || '16/16');
	ok('prod path: BN is not fetched by a HI switch', covered(t, 'bn').length === 0, covered(t, 'bn').join(', ') || 'none');
	ok('prod path: every landing fires the re-render signal (setPacksRegisteredHook)', bumps >= 16, `${bumps} signals`);
	await L.ensureLang('bn');
	ok('prod path: ensureLang("bn") lands BN for all 16 pack modules', missingOf(t, 'bn').length === 0, missingOf(t, 'bn').join(', ') || '16/16');
	const before = bumps;
	await L.ensureLang('hi');
	ok('prod path: a repeat call is free (no re-fetch, no extra signal)', bumps === before);
}
{
	// b. the cold path: the document's language, before the modules finish evaluating. Its own CODE-SPLIT build:
	// each language chunk is a separate file, so a chunk that is fetched but not awaited is still out when the
	// import resolves (an in-bundle chunk would land within the same microtask run and hide a missing await)
	const coldDir = path.join(OUT_DIR, 'cold');
	const coldEntry = path.join(OUT_DIR, 'perf2-cold-entry.ts');
	writeFileSync(coldEntry, MODULES.map((m) => `import '${path.join(DECK, 'src/lib/i18n', m)}';`).join('\n') + `\nexport { t } from '${path.join(DECK, 'src/lib/i18n/strings')}';\n`);
	const r = await esbuild.build({ entryPoints: { cold: coldEntry }, absWorkingDir: DECK, alias: { $lib: './src/lib' }, bundle: true, splitting: true, format: 'esm', platform: 'node', define: PROD_DEFINE, outdir: coldDir, outExtension: { '.js': '.mjs' }, logLevel: 'silent', plugins: [stubApp] });
	ok('bundle perf2-cold (code-split: one file per language chunk) builds with the production client defines', r.errors.length === 0, `${r.errors.length} errors`);
	globalThis.window = { addEventListener() {} };
	globalThis.document = { documentElement: { lang: 'bn' }, cookie: '', querySelectorAll: () => [] };
	const { t } = await import(pathToFileURL(path.join(coldDir, 'cold.mjs')).href);
	ok('cold path: <html lang="bn"> → every module\'s BN strings are in when the modules finish evaluating', missingOf(t, 'bn').length === 0, missingOf(t, 'bn').join(', ') || '16/16');
	ok('cold path: only the document\'s language is fetched (no HI)', covered(t, 'hi').length === 0, covered(t, 'hi').join(', ') || 'none');
	delete globalThis.document;
	delete globalThis.window;
}

const STORE = await bundle('perf2-store', `${IMPORTS}\nexport { ops } from './src/lib/ops/store.svelte';\nexport { t } from './src/lib/i18n/strings';\n`);
{
	// c. the ops store's setter alone
	const { ops, t } = await fresh(STORE);
	ok('store: before a switch, no HI module is in', covered(t, 'hi').length === 0);
	ops.lang = 'hi';
	await settle(() => missingOf(t, 'hi').length === 0);
	ok('store: the `lang` setter alone lands HI for all 16 pack modules', missingOf(t, 'hi').length === 0, missingOf(t, 'hi').join(', ') || '16/16');
}
{
	// c. adoptLangCookie() alone
	const { ops, t } = await fresh(STORE);
	globalThis.document = { documentElement: { lang: 'en' }, cookie: 'sahoshi_lang=bn', querySelectorAll: () => [] };
	ops.adoptLangCookie();
	await settle(() => missingOf(t, 'bn').length === 0);
	ok('store: adoptLangCookie() alone (sahoshi_lang=bn) lands BN for all 16 pack modules', ops.lang === 'bn' && missingOf(t, 'bn').length === 0, `lang=${ops.lang}; missing ${missingOf(t, 'bn').join(', ') || 'none'}`);
	delete globalThis.document;
}

{
	// d. a real Svelte 5 effect re-runs when the chunk lands
	const { compileModule } = require('svelte/compiler');
	// a virtual client-compiled module: one $effect that reads t()
	const PROBE_SRC = `import { t } from '$lib/i18n/strings';\nexport function watch(lang, key, out) {\n\treturn $effect.root(() => {\n\t\t$effect(() => {\n\t\t\tout.push(t(lang, key));\n\t\t});\n\t});\n}\n`;
	const runes = {
		name: 'svelte-client-runes',
		setup(b) {
			b.onResolve({ filter: /^perf2-probe$/ }, () => ({ path: 'perf2-probe.svelte.js', namespace: 'perf2-probe' }));
			b.onLoad({ filter: /.*/, namespace: 'perf2-probe' }, () => ({ contents: compileModule(PROBE_SRC, { filename: 'perf2-probe.svelte.js', generate: 'client', dev: false }).js.code, loader: 'js', resolveDir: DECK }));
			b.onLoad({ filter: /\.svelte\.(ts|js)$/ }, async (a) => {
				const src = readFileSync(a.path, 'utf8');
				const plain = a.path.endsWith('.ts') ? (await esbuild.transform(src, { loader: 'ts' })).code : src;
				return { contents: compileModule(plain, { filename: a.path, generate: 'client', dev: false }).js.code, loader: 'js', resolveDir: path.dirname(a.path) };
			});
		},
	};
	let R = null;
	try {
		const file = await bundle(
			'perf2-runes',
			`${IMPORTS}\nimport './src/lib/i18n/pack-registry.svelte';\nexport { watch } from 'perf2-probe';\nexport { ensureLang } from './src/lib/i18n/load';\nexport { flushSync } from 'svelte';\n`,
			{ plugins: [stubApp, runes], conditions: ['svelte', 'browser'] },
		);
		R = await fresh(file);
	} catch (e) {
		ok('runes: the client-compiled probe loads', false, String(e?.message ?? e).slice(0, 300));
	}
	if (R) {
		const s = SAMPLE['packs.wall'];
		const seen = [];
		const stop = R.watch('hi', s.key, seen);
		R.flushSync();
		await R.ensureLang('hi');
		R.flushSync();
		stop();
		ok('runes: a $effect reading t() ran first with EN (never the raw key) and re-ran with HI once the chunk landed', seen[0] === s.en && seen.at(-1) === s.hi, JSON.stringify(seen.map((x) => x.slice(0, 24))));
	}
}

// ── 3. icons ──────────────────────────────────────────────────────────────────

const DESIGN = path.join(DECK, 'src/lib/design');
const ICONS = await bundle('perf2-icons', `export * as I from './src/lib/design/icons';\nexport * as C from './src/lib/design/icons-core';\n`);
{
	delete globalThis.document;
	delete globalThis.window;
	const { I, C } = await fresh(ICONS);
	const names16 = Object.keys(I.ICONS_16);
	const pathsSha = (tbl) => createHash('sha256').update(Object.entries(tbl).map(([n, p]) => `${n}\u0000${(p ?? []).join('\u0001')}`).join('\n')).digest('hex');
	ok('icons: ICONS_16 is complete, frozen and in main\'s order with main\'s path data', names16.length === ICON_GOLDEN.n16 && Object.isFrozen(I.ICONS_16) && createHash('sha256').update(names16.join('\n')).digest('hex') === ICON_GOLDEN.order16 && pathsSha(I.ICONS_16) === ICON_GOLDEN.paths16, `${names16.length} names`);
	ok('icons: ICONS_20 is complete, frozen, with main\'s path data', Object.keys(I.ICONS_20).length === ICON_GOLDEN.n20 && Object.isFrozen(I.ICONS_20) && pathsSha(I.ICONS_20) === ICON_GOLDEN.paths20, `${Object.keys(I.ICONS_20).length} names`);
	ok('icons: ICON_NAMES is the full set in table order', C.ICON_NAMES.length === names16.length && C.ICON_NAMES.every((n, i) => n === names16[i]));
	const core = new Set(Object.keys(C.CORE_16));
	const deferred = names16.filter((n) => !core.has(n));
	ok('icons (prod): isIconName knows every name before anything loads, and rejects others', names16.every((n) => I.isIconName(n)) && !I.isIconName('person') && !I.isIconName('') && !I.isIconName(42), `${names16.length} names, ${deferred.length} deferred`);
	ok('icons (prod): a first-paint glyph draws at once; a deferred one has no paths until its half lands', [...core].every((n) => I.iconPaths(n, 16).paths.length > 0) && deferred.length > 0 && deferred.every((n) => I.iconPaths(n, 16).paths.length === 0 && !I.iconReady(n)));
	ok('icons (prod): nothing has asked for the deferred half yet', I.restIconsInFlight() === null && !I.restIconsLoaded());
	await I.loadRestIcons();
	const bad = names16.filter((n) => {
		const p16 = I.iconPaths(n, 16);
		const p20 = I.iconPaths(n, 20);
		return p16.paths.length === 0 || p16.paths !== I.ICONS_16[n] || p20.grid !== (I.ICONS_20[n] ? 20 : 16) || p20.paths !== (I.ICONS_20[n] ?? I.ICONS_16[n]);
	});
	ok('icons (prod): after loadRestIcons() EVERY name resolves at 16 and 20 px to main\'s drawing', bad.length === 0, bad.slice(0, 6).join(', ') || `${names16.length}/${names16.length}`);
	const pinned = new Set([...Object.values(C.FIRST_PAINT_ICONS).flat(), ...C.MAP_GLYPHS, ...C.CANVAS_PANEL_ICONS]);
	ok('icons: the first-paint half is EXACTLY the pinned first-viewport sets + the map-marker glyphs + the canvas panels\' glyphs', pinned.size === core.size && [...pinned].every((n) => core.has(n)), `${core.size} glyphs`);
	const coreHas20 = Object.keys(C.CORE_20).every((n) => core.has(n)) && [...core].every((n) => !I.ICONS_20[n] || C.CORE_20[n]);
	ok('icons: a first-paint glyph carries its 20 px drawing too (no scaled stand-in until the rest lands)', coreHas20);
	const mapNeed = [...new Set([...Object.values(I.KIND_ICON), ...Object.values(I.EVENT_KIND_ICON), 'dot', 'lock'])];
	ok('icons: every glyph a map marker can draw is first-paint (a canvas billboard cannot redraw itself)', mapNeed.every((n) => C.MAP_GLYPHS.includes(n) && core.has(n)), mapNeed.filter((n) => !core.has(n)).join(', ') || `${mapNeed.length} glyphs`);
}

// the server render of the three routes: every glyph drawn must be first-paint and pinned for that route
{
	const SERVER = path.join(DECK, '.svelte-kit/output/server/index.js');
	const MANIFEST = path.join(DECK, '.svelte-kit/output/server/manifest.js');
	if (!existsSync(SERVER) || !existsSync(MANIFEST)) {
		console.log('skip icons: server-render pin — no production build (.svelte-kit/output/server); `sem.sh deck-build 2 npm run build:cpu` then re-run');
	} else {
		// nothing the render does may reach a backend: point every upstream at the discard port
		for (const k of ['ORACLE_PORT', 'BRAIN_PORT', 'EMULATOR_PORT']) process.env[k] = '9';
		for (const k of ['SAHOSHI_OPERATOR_PIN', 'SAHOSHI_OPERATOR_PIN_FILE', 'SAHOSHI_SESSION_SECRET', 'SAHOSHI_CESIUM_ION_TOKEN']) delete process.env[k];
		globalThis.crypto ??= (await import('node:crypto')).webcrypto; // node 18: what adapter-node's shims install
		const { Server } = await import(pathToFileURL(SERVER).href);
		const { manifest } = await import(pathToFileURL(MANIFEST).href);
		const server = new Server(manifest);
		await server.init({ env: process.env });
		const C = await import(`${pathToFileURL(path.join(OUT_DIR, 'perf2-icons.mjs')).href}?i=${++instance}`).then((m) => m.C);
		const core = new Set(Object.keys(C.CORE_16));
		// FIRST_PAINT_ICONS is keyed by the LOGICAL route ('/' is the workspace's pinned set); the URL it is served at is WORKSPACE
		const pinKey = (route) => (route === WORKSPACE ? '/' : route);
		for (const route of [WORKSPACE, '/ops', '/gods-eye']) {
			const drawn = new Set();
			for (const lang of LANGS) {
				const res = await server.respond(new Request(`http://127.0.0.1${route}`, { headers: { cookie: `sahoshi_lang=${lang}` } }), { getClientAddress: () => '127.0.0.1' });
				const html = await res.text();
				for (const m of html.matchAll(/data-icon="([a-z0-9-]+)"/g)) drawn.add(m[1]);
			}
			const notCore = [...drawn].filter((n) => !core.has(n));
			const notPinned = [...drawn].filter((n) => !C.FIRST_PAINT_ICONS[pinKey(route)].includes(n));
			ok(`icons: the server render of ${route} (EN/HI/BN) draws only first-paint glyphs pinned for the route`, drawn.size > 0 && notCore.length === 0 && notPinned.length === 0, `${drawn.size} glyphs${notCore.length ? `; not first-paint: ${notCore.join(', ')}` : ''}${notPinned.length ? `; not pinned: ${notPinned.join(', ')}` : ''}`);
		}
	}
}

if (failures) {
	console.error(`\n${failures} check(s) failed`);
	process.exit(1);
}
console.log('\nok   perf2 — every pack copy matches main, every language lands on the production path for all 16 modules, and the icon set is whole');
process.exit(0);
