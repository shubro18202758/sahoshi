/**
 * Bengali script check (the third UI language is বাংলা). For every BN string pack in the deck,
 * reported PER FILE so a failure is attributable to the stream that owns that file:
 *
 *   parity       the BN pack has exactly the EN pack's keys (none missing, none extra);
 *   script       every visible BN text piece is Bengali script (NFC-normalised): once interpolations and the
 *                allowed Latin tokens are removed (ALL-CAPS acronyms and codes such as ANPR,
 *                FIR, ETA, ID, EMULATED, WB 02 AB 1234; identifiers, paths and units with a
 *                digit, `_`, `/` or `.`; the short list of names in LATIN_OK), no Latin letter
 *                is left, and no Gujarati or Devanagari character appears anywhere. A piece
 *                with any letter must carry Bengali (U+0980–U+09FF). The few exemptions are per key, with
 *                their reason, in SCRIPT_EXEMPT (printed on every run);
 *   placeholders the `{x}` / `%s` placeholders and the markup tags of a string equal EN's;
 *                a function value is run with distinct numeric arguments and then with
 *                distinct text arguments, and BN must render exactly the same argument
 *                values and digit runs as EN (so no number is dropped, invented or moved
 *                out of Western digits, and no argument is lost);
 *   no Gujarati  no source file under src/ carries Gujarati script any more (the old third
 *                language), reported per file;
 *   switch       বাংলা is the third language (label, compact mark বাং);
 *   formatter    the optional Bengali-digit formatter (bengaliDigits, localizeNumber, publicNumber)
 *                renders ০–৯ with Indian grouping, keeps 0–9 on request, and is imported only by
 *                public surfaces (citizen, driver, public/landing pages, the citizen advisory text).
 *
 * Packs: every `*.bn.ts` module (export const bn) paired with its base module's `en` literal,
 * and every inline pack (a top-level `const bn = {…}` beside `const en`, a `bn: {…}` property
 * beside `en: {…}` in one object, or `registerPack('bn', {…})` beside `registerPack('en', {…})`
 * — the last checked on its source only), skipping a never-registered text mirror whose
 * `*.bn.ts` copy exists (tests/perf2.unit.mjs pins the two equal).
 *
 *   node tests/bn-script.unit.mjs                 all files
 *   node tests/bn-script.unit.mjs --only <text>   files whose path contains <text> (repeatable)
 *   node tests/bn-script.unit.mjs --all-details   every problem line, not the first 12 per file
 *   node tests/bn-script.unit.mjs --calibrate-hi  run the same rules on the HI packs (Devanagari),
 *                                                 a review aid for the rules themselves
 *
 * Exits 0 with `ok` lines, 1 on any failure.
 */

import { createRequire } from 'node:module';
import { existsSync, mkdirSync, readFileSync, readdirSync, statSync, rmSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DECK = path.resolve(HERE, '..');
const SRC = path.join(DECK, 'src');
const LIB = path.join(SRC, 'lib');
const require = createRequire(path.join(DECK, 'package.json'));
const ts = require('typescript');
const esbuild = require('esbuild');

const args = process.argv.slice(2);
const ONLY = args.flatMap((a, i) => (args[i - 1] === '--only' ? [a] : []));
const ALL_DETAILS = args.includes('--all-details');
const HI = args.includes('--calibrate-hi');
const L = HI ? 'hi' : 'bn';
const rel = (f) => path.relative(DECK, f);
const wanted = (f) => ONLY.length === 0 || ONLY.some((o) => rel(f).includes(o));

// ── the script rule ──────────────────────────────────────────────────────────

const BENGALI = HI ? /[ऀ-ॿ]/ : /[ঀ-৿]/;
/** । and ॥ (U+0964/U+0965) sit in the Devanagari block but are Bengali's own full stops (shared code points). */
const DANDA = /[\u0964\u0965]/g;
const GUJARATI = /[઀-૿]/;
const DEVANAGARI = HI ? /[ঀ-৿]/ : /[ऀ-ॿ]/;
/** Mixed-case Latin a BN string may keep: product, protocol and licence names, keys on a keyboard, time-format letters, units. */
const LATIN_OK = new Set(
	(
		'Gemma Nemotron Qwen Cesium ion Google OpenStreetMap OSM Mapillary WhatsApp WebSocket Esc Escape Enter Shift Ctrl Alt Tab Cmd ' +
		'ODbL csv json hh mm ss km m s ms min h kmh px veh Hz dB'
	).split(/\s+/),
);
/** A Latin token that is a code, not a word: ALL-CAPS (acronyms, codes, bands), or carries a digit, `_`, `/`, `.`, `@`, `#`, `=`. */
const isCodeToken = (tok) => /^[A-Z0-9][A-Z0-9_\-/.:+•×]*$/.test(tok) || /[0-9_/.@#=]/.test(tok);

/** The Latin words left in a text once codes and allowed names are removed. */
function latinWords(text) {
	const out = [];
	for (const tok of text.split(/[\s,;:!?()[\]{}"'“”‘’«»<>|—–…·• ‌‍]+/)) {
		if (!/[A-Za-z]/.test(tok)) continue;
		const bare = tok.replace(/^[^A-Za-z0-9]+|[^A-Za-z0-9]+$/g, '');
		if (!bare || isCodeToken(bare) || LATIN_OK.has(bare)) continue;
		// a Bengali word glued to a code (e.g. "ANPR-এর", "WB-তে") is fine: drop the Bengali part and look again
		const latinPart = bare.replace(HI ? /[ऀ-ॿ]+/g : /[ঀ-৿]+/g, ' ').trim();
		if (latinPart.split(/\s+/).every((p) => !/[A-Za-z]/.test(p) || isCodeToken(p.replace(/[^A-Za-z0-9_/.]+$/, '')) || LATIN_OK.has(p.replace(/[^A-Za-z0-9]+$/, '')))) continue;
		out.push(bare);
	}
	return out;
}

/**
 * Script-rule exemptions, per key, each with its reason (printed on every run). Parity, placeholders and digits
 * still apply to them.
 *   *lang_short*      a language switch shows every language's mark in that language's own script (EN · हिं · বাং);
 *   pal_placeholder   the ⌘K palette's example commands: the command grammar (lib/workspace/search.ts parseCommand) is
 *                     English, so the examples stay typeable English, as in HI.
 */
const SCRIPT_EXEMPT = [
	{ file: /./, key: /lang_short/, why: 'a language switch shows each language in its own script' },
	{ file: /i18n\/packs\.agent\.bn\.ts$/, key: /^pal_placeholder$/, why: 'typeable English command examples (the ⌘K grammar is English)' },
];
const exemptFor = (file, key) => SCRIPT_EXEMPT.find((x) => x.file.test(rel(file)) && x.key.test(key));
/** 'Gujarati' / 'Devanagari' when a text carries that script; the dari । and ॥ (U+0964/U+0965) alone are Bengali. */
const foreignScript = (text) => (GUJARATI.test(text) ? 'Gujarati' : DEVANAGARI.test(text.replace(DANDA, '')) ? 'Devanagari' : null);

// ── AST: pack literals and their visible text pieces ─────────────────────────

const unwrap = (n) => {
	while (n && (ts.isAsExpression(n) || ts.isSatisfiesExpression?.(n) || ts.isParenthesizedExpression(n) || ts.isTypeAssertionExpression?.(n))) n = n.expression;
	return n;
};
const parse = (file) => ts.createSourceFile(file, readFileSync(file, 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
const propName = (p) => (p.name && (ts.isIdentifier(p.name) || ts.isStringLiteral(p.name) || ts.isNumericLiteral(p.name)) ? p.name.text : null);

/** The visible text pieces of an initializer: literals in result position (never a comparison operand or a call argument). */
function pieces(node, out = []) {
	const n = unwrap(node);
	if (!n) return out;
	if (ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n)) out.push(n.text);
	else if (ts.isTemplateExpression(n)) {
		out.push(n.head.text);
		for (const sp of n.templateSpans) {
			pieces(sp.expression, out);
			out.push(sp.literal.text);
		}
	} else if (ts.isConditionalExpression(n)) {
		pieces(n.whenTrue, out);
		pieces(n.whenFalse, out);
	} else if (ts.isBinaryExpression(n)) {
		const k = n.operatorToken.kind;
		if (k === ts.SyntaxKind.PlusToken || k === ts.SyntaxKind.QuestionQuestionToken || k === ts.SyntaxKind.BarBarToken) {
			pieces(n.left, out);
			pieces(n.right, out);
		} else if (k === ts.SyntaxKind.AmpersandAmpersandToken) pieces(n.right, out);
	} else if (ts.isArrayLiteralExpression(n)) for (const e of n.elements) pieces(e, out);
	else if (ts.isCallExpression(n) && ts.isPropertyAccessExpression(n.expression) && n.expression.name.text === 'join') {
		pieces(n.expression.expression, out);
		if (n.arguments[0]) pieces(n.arguments[0], out);
	} else if (ts.isArrowFunction(n) || ts.isFunctionExpression(n)) {
		if (!ts.isBlock(n.body)) pieces(n.body, out);
		else
			(function walk(x) {
				if (ts.isReturnStatement(x) && x.expression) pieces(x.expression, out);
				else if (ts.isVariableDeclaration(x) && x.initializer) pieces(x.initializer, out);
				if (!ts.isFunctionLike(x)) ts.forEachChild(x, walk);
			})(n.body);
	}
	return out;
}

/** key → initializer node, from an object literal. */
function members(obj) {
	const map = new Map();
	for (const p of obj.properties) {
		if (ts.isPropertyAssignment(p)) {
			const k = propName(p);
			if (k !== null) map.set(k, p.initializer);
		} else if (ts.isMethodDeclaration(p)) {
			const k = propName(p);
			if (k !== null) map.set(k, p);
		}
	}
	return map;
}

/** Top-level `const <name> = {…}` object literals of a file, by name. */
function topConsts(sf) {
	const out = {};
	for (const st of sf.statements) {
		if (!ts.isVariableStatement(st)) continue;
		for (const d of st.declarationList.declarations) {
			const init = unwrap(d.initializer);
			if (ts.isIdentifier(d.name) && init && ts.isObjectLiteralExpression(init)) out[d.name.text] = init;
		}
	}
	return out;
}

// ── discovery ────────────────────────────────────────────────────────────────

function walkFiles(dir, out = []) {
	for (const name of readdirSync(dir)) {
		const f = path.join(dir, name);
		const st = statSync(f);
		if (st.isDirectory()) walkFiles(f, out);
		else out.push(f);
	}
	return out;
}
const ALL_SRC = walkFiles(SRC);
const TS_FILES = ALL_SRC.filter((f) => f.endsWith('.ts') && !f.endsWith('.d.ts'));

/**
 * One pack: where its BN and EN literals live, and how the bundle reaches each value.
 *   { file (the BN source, the attribution), enFile, bnObj, enObj, enAccess, bnAccess }
 * access = { file, binding, prop? } — a top-level binding (optionally one property of it).
 */
const PACKS = [];
for (const f of TS_FILES) {
	if (f.endsWith(`.${L}.ts`)) {
		const base = f.slice(0, -`.${L}.ts`.length) + '.ts';
		const bnObj = topConsts(parse(f))[L];
		const enObj = existsSync(base) ? topConsts(parse(base)).en : undefined;
		PACKS.push({ file: f, enFile: base, bnObj, enObj, bnAccess: { file: f, binding: L }, enAccess: { file: base, binding: 'en' } });
		continue;
	}
	if (f.endsWith('.hi.ts') || f.endsWith('.bn.ts')) continue;
	const sf = parse(f);
	const consts = topConsts(sf);
	// an inline pack: const en + const bn (skip a text mirror whose .bn.ts copy exists)
	if (consts[L] && consts.en && !existsSync(f.replace(/\.ts$/, `.${L}.ts`))) {
		PACKS.push({ file: f, enFile: f, bnObj: consts[L], enObj: consts.en, bnAccess: { file: f, binding: L }, enAccess: { file: f, binding: 'en' } });
	}
	// an inline registration: registerPack('en', {…}) and registerPack('bn', {…}) in one file (AST checks only)
	const reg = {};
	for (const st of sf.statements) {
		const c = ts.isExpressionStatement(st) && ts.isCallExpression(st.expression) ? st.expression : null;
		if (!c || !ts.isIdentifier(c.expression) || c.expression.text !== 'registerPack' || c.arguments.length < 2) continue;
		const [code, obj] = c.arguments;
		if (ts.isStringLiteral(code) && ts.isObjectLiteralExpression(unwrap(obj))) reg[code.text] = unwrap(obj);
	}
	if (reg[L] && reg.en) PACKS.push({ file: f, enFile: f, bnObj: reg[L], enObj: reg.en, bnAccess: null, enAccess: null, inline: true });
	// a nested pack: X = { en: {…}, bn: {…} } at the top level
	for (const [name, obj] of Object.entries(consts)) {
		const m = members(obj);
		const en = unwrap(m.get('en'));
		const bn = unwrap(m.get(L));
		if (en && bn && ts.isObjectLiteralExpression(en) && ts.isObjectLiteralExpression(bn)) {
			PACKS.push({ file: f, enFile: f, bnObj: bn, enObj: en, bnAccess: { file: f, binding: name, prop: L }, enAccess: { file: f, binding: name, prop: 'en' } });
		}
	}
}

// ── runtime values (one bundle exposes every pack's EN and BN objects) ───────

const OUT_DIR = path.join(os.tmpdir(), `sahoshi-bn-script-${process.pid}`);
mkdirSync(OUT_DIR, { recursive: true });
const selected = PACKS.filter((p) => wanted(p.file));
const exposeByFile = new Map(); // file → Set(binding)
for (const p of selected) {
	for (const a of [p.enAccess, p.bnAccess].filter(Boolean)) {
		if (!exposeByFile.has(a.file)) exposeByFile.set(a.file, new Set());
		exposeByFile.get(a.file).add(a.binding);
	}
}
const exportName = (file, binding) => `__bnscript_${[...exposeByFile.keys()].indexOf(file)}_${binding}`;
const expose = {
	name: 'bn-script-expose',
	setup(b) {
		b.onResolve({ filter: /^\$(app|env)\// }, (a) => ({ path: a.path, namespace: 'stub-app' }));
		b.onLoad({ filter: /.*/, namespace: 'stub-app' }, () => ({
			contents: 'export const browser = false, dev = false, building = false; export const goto = async () => {}; export const page = {}; export const navigating = {}; export const env = {};',
			loader: 'js',
		}));
		b.onLoad({ filter: /\.ts$/ }, (a) => {
			const bindings = exposeByFile.get(a.path);
			if (!bindings) return undefined;
			const src = readFileSync(a.path, 'utf8');
			const extra = [...bindings].map((bd) => `export { ${bd} as ${exportName(a.path, bd)} };`).join('\n');
			return { contents: `${src}\n${extra}\n`, loader: 'ts' };
		});
	},
};

let VALUES = null;
let CORE = null;
let bundleError = null;
if (selected.length) {
	const entry = [...exposeByFile.keys()].map((f, i) => `export * as M${i} from ${JSON.stringify(f)};`).join('\n') + `\nexport * as CORE from ${JSON.stringify(path.join(LIB, 'i18n/strings.ts'))};`;
	const outfile = path.join(OUT_DIR, 'bn-script.mjs');
	try {
		await esbuild.build({
			stdin: { contents: entry, resolveDir: DECK, loader: 'ts', sourcefile: 'bn-script-entry.ts' },
			absWorkingDir: DECK,
			alias: { $lib: './src/lib' },
			bundle: true,
			format: 'esm',
			platform: 'node',
			define: { 'process.env.NODE_ENV': '"test"', 'import.meta.env.SSR': 'true', 'import.meta.env.DEV': 'true', 'import.meta.env.PROD': 'false' },
			outfile,
			logLevel: 'silent',
			loader: { '.svelte': 'empty', '.css': 'empty', '.png': 'empty', '.svg': 'empty', '.json': 'json' },
			plugins: [expose],
		});
		globalThis.$state = Object.assign((v) => v, { raw: (v) => v, snapshot: (v) => v });
		globalThis.$derived = Object.assign((v) => v, { by: (f) => f() });
		globalThis.$effect = Object.assign(() => {}, { root: () => () => {}, pre: () => {} });
		const mod = await import(pathToFileURL(outfile).href);
		CORE = mod.CORE;
		VALUES = (a) => {
			const m = mod[`M${[...exposeByFile.keys()].indexOf(a.file)}`];
			const v = m?.[exportName(a.file, a.binding)];
			return a.prop ? v?.[a.prop] : v;
		};
	} catch (e) {
		bundleError = String(e?.message ?? e).split('\n').slice(0, 6).join(' | ');
	} finally {
		rmSync(OUT_DIR, { recursive: true, force: true });
	}
}

// ── checks ───────────────────────────────────────────────────────────────────

const NUM_ARGS = [7301, 7302, 7303, 7304, 7305, 7306];
const TXT_ARGS = ['‹a0›', '‹a1›', '‹a2›', '‹a3›', '‹a4›', '‹a5›'];
const PLACEHOLDERS = /\{[A-Za-z_][A-Za-z0-9_]*\}|%(?:\d+\$)?[sdif]/g;
const TAGS = /<\/?[a-z][a-z0-9]*\b[^>]*>/gi;
const sorted = (a) => [...a].sort().join(' ');
const call = (fn, argv) => {
	try {
		return { ok: true, out: String(fn(...argv)) };
	} catch (e) {
		return { ok: false, out: String(e?.message ?? e) };
	}
};
// a number must survive translation; Bengali digits (০–৯, public pages) count as the same number
const digitRuns = (s) => sorted(s.replace(/[০-৯]/g, (c) => String(c.charCodeAt(0) - 0x09e6)).match(/\d+/g) ?? []);
const textArgs = (s) => sorted(s.match(/‹a\d›/g) ?? []);

let failures = 0;
function ok(name, cond, detail = '') {
	if (cond) console.log(`ok   ${name}${detail ? ` — ${detail}` : ''}`);
	else {
		failures++;
		console.error(`FAIL ${name}${detail ? ` — ${detail}` : ''}`);
	}
	return cond;
}

ok('bn-script: the runtime bundle of the selected packs builds and loads', !bundleError, bundleError ?? `${selected.length} pack(s)`);
if (!HI)
	ok(
		'bn-script: the script rule allows exactly the dari । ॥ from the Devanagari block (Bengali full stops) and rejects every other Devanagari or Gujarati character',
		foreignScript('অনুমোদিত। আবার দেখুন॥') === null && foreignScript('অনুমোদিত.') === null && foreignScript('অনুমোদিত । क') === 'Devanagari' &&
			foreignScript('অনুমোদিত\u0966') === 'Devanagari' && foreignScript('ভালো\u0963') === 'Devanagari' && foreignScript('ક') === 'Gujarati' && foreignScript('\u0AE6') === 'Gujarati',
	);

for (const p of selected) {
	const label = rel(p.file) + (p.inline ? " (registerPack('bn', …))" : p.bnAccess.prop ? ` (${p.bnAccess.binding}.bn)` : '');
	const problems = [];
	if (!p.bnObj || !p.enObj) {
		ok(`bn-script: ${label}`, false, !p.bnObj ? 'no bn object literal' : `no en literal in ${rel(p.enFile)}`);
		continue;
	}
	const bn = members(p.bnObj);
	const en = members(p.enObj);
	const missing = [...en.keys()].filter((k) => !bn.has(k));
	const extra = [...bn.keys()].filter((k) => !en.has(k));
	for (const k of missing) problems.push(`parity   ${k}: missing in BN`);
	for (const k of extra) problems.push(`parity   ${k}: not an EN key`);

	// script, on every visible literal piece (all branches)
	for (const [k, init] of bn) {
		const ps = pieces(init).filter((s) => s.length);
		if (ps.some((x) => x !== x.normalize('NFC'))) problems.push(`script   ${k}: not NFC-normalised (one spelling per word, so search and matching agree)`);
		const ex = exemptFor(p.file, k);
		if (ex) {
			console.log(`       ${rel(p.file)}  script rule exempt: ${k} — ${ex.why}`);
			continue;
		}
		for (const s of ps) {
			const foreign = foreignScript(s);
			if (foreign) problems.push(`script   ${k}: ${foreign} script — "${s.slice(0, 80)}"`);
			const lw = latinWords(s);
			if (lw.length) problems.push(`script   ${k}: Latin words ${JSON.stringify(lw.slice(0, 5))} — "${s.slice(0, 80)}"`);
		}
		const joined = ps.join(' ');
		const enJoined = pieces(en.get(k) ?? init).join(' ');
		// a piece with letters must be Bengali, unless EN itself is only codes there (e.g. 'ETA', 'IST')
		if (/[A-Za-zऀ-ॿ઀-૿]/.test(joined) && !BENGALI.test(joined) && latinWords(enJoined).length) problems.push(`script   ${k}: no Bengali at all — "${joined.slice(0, 80)}"`);
	}

	// placeholders, markup, arguments and digits, at runtime
	if (VALUES && p.bnAccess) {
		const enV = VALUES(p.enAccess) ?? {};
		const bnV = VALUES(p.bnAccess) ?? {};
		for (const k of en.keys()) {
			if (!bn.has(k)) continue;
			const e = enV[k];
			const b = bnV[k];
			if (typeof e === 'string' && typeof b === 'string') {
				if (sorted(e.match(PLACEHOLDERS) ?? []) !== sorted(b.match(PLACEHOLDERS) ?? [])) problems.push(`place    ${k}: placeholders ${JSON.stringify(e.match(PLACEHOLDERS) ?? [])} vs ${JSON.stringify(b.match(PLACEHOLDERS) ?? [])}`);
				if (sorted(e.match(TAGS) ?? []) !== sorted(b.match(TAGS) ?? [])) problems.push(`markup   ${k}: tags ${JSON.stringify(e.match(TAGS) ?? [])} vs ${JSON.stringify(b.match(TAGS) ?? [])}`);
				if (digitRuns(e) !== digitRuns(b)) problems.push(`digits   ${k}: EN [${digitRuns(e)}] vs BN [${digitRuns(b)}]`);
			} else if (typeof e === 'function' && typeof b === 'function') {
				for (const argv of [NUM_ARGS, TXT_ARGS]) {
					const re = call(e, argv);
					const rb = call(b, argv);
					if (re.ok !== rb.ok) {
						problems.push(`place    ${k}: EN ${re.ok ? 'renders' : 'throws'} but BN ${rb.ok ? 'renders' : `throws (${rb.out.slice(0, 60)})`} for (${argv[0]}, …)`);
						continue;
					}
					if (!re.ok) continue;
					if (argv === NUM_ARGS && digitRuns(re.out) !== digitRuns(rb.out)) problems.push(`place    ${k}: numbers EN [${digitRuns(re.out)}] vs BN [${digitRuns(rb.out)}] — "${rb.out.slice(0, 70)}"`);
					if (argv === TXT_ARGS && textArgs(re.out) !== textArgs(rb.out)) problems.push(`place    ${k}: arguments EN [${textArgs(re.out)}] vs BN [${textArgs(rb.out)}] — "${rb.out.slice(0, 70)}"`);
					if (sorted(re.out.match(TAGS) ?? []) !== sorted(rb.out.match(TAGS) ?? [])) problems.push(`markup   ${k}: tags differ`);
					if (sorted(re.out.match(PLACEHOLDERS) ?? []) !== sorted(rb.out.match(PLACEHOLDERS) ?? [])) problems.push(`place    ${k}: placeholders differ`);
				}
			} else if (e !== undefined && b !== undefined && typeof e !== typeof b) problems.push(`place    ${k}: EN is a ${typeof e}, BN a ${typeof b}`);
		}
	}

	const shown = ALL_DETAILS ? problems : problems.slice(0, 12);
	ok(`bn-script: ${label}`, problems.length === 0, problems.length ? `${problems.length} problem(s)` : `${en.size} keys, Bengali, placeholders as EN`);
	for (const line of shown) console.error(`       ${label}  ${line}`);
	if (shown.length < problems.length) console.error(`       ${label}  … ${problems.length - shown.length} more (--all-details)`);
}

// the language switch and the optional Bengali-digit formatter (public pages only)
if (CORE && ONLY.length === 0) {
	const bnLang = CORE.SUPPORTED.find((x) => x.code === 'bn');
	ok('switch: বাংলা is the third language, its compact mark বাং', !!bnLang && bnLang.label === 'বাংলা' && CORE.langShort('bn') === 'বাং' && CORE.SUPPORTED.map((x) => x.code).join() === 'en,hi,bn', JSON.stringify(bnLang));
	ok(
		'formatter: Bengali digits on demand — bengaliDigits, localizeNumber(…, "bn"), publicNumber with Indian grouping; native:false keeps 0–9',
		CORE.bengaliDigits('12:05') === '১২:০৫' && CORE.localizeNumber(108, 'bn') === '১০৮' && CORE.localizeNumber(108, 'bn', false) === '108' &&
			CORE.publicNumber(1234567, 'bn') === '১২,৩৪,৫৬৭' && CORE.publicNumber(1234567, 'bn', { native: false }) === '12,34,567' && CORE.publicNumber(1234567, 'en') === '12,34,567' && CORE.localizeNumber(42, 'en') === '42',
		`${CORE.bengaliDigits('12:05')} · ${CORE.publicNumber(1234567, 'bn')}`,
	);
	// public pages only: the native-digit helpers are imported by public surfaces (and the citizen advisory text), never the
	// console. The v2 advisory desk (routes/(deck)/comms) is listed because it previews the citizen drafts in each language;
	// its two console-language fact lines pass `native: false` (.orchestration/patches/lang-a-console-digits.patch).
	const PUBLIC_OK = /^src\/(lib\/(citizen|v3\/public|v3\/landing)\/|lib\/comms\/advisory\.ts$|lib\/i18n\/strings(\.citizen)?\.ts$|routes\/\(public\)\/|routes\/\(deck\)\/comms\/\+page\.svelte$)/;
	const importers = TS_FILES.concat(ALL_SRC.filter((f) => f.endsWith('.svelte')))
		.filter((f) => /import\s*\{[^}]*\b(localizeNumber|bengaliDigits|publicNumber)\b[^}]*\}\s*from\s*'(\$lib\/i18n\/strings|\.\/strings)'/.test(readFileSync(f, 'utf8')))
		.map(rel);
	const consoleUse = importers.filter((f) => !PUBLIC_OK.test(f));
	ok('formatter: native digits stay on public pages (no console module imports the digit helpers)', consoleUse.length === 0, consoleUse.join(', ') || `${importers.length} public importer(s)`);
}

// no Gujarati script left anywhere under src/ (per file)
for (const f of HI ? [] : ALL_SRC.filter((x) => /\.(ts|js|svelte|css|html|json)$/.test(x) && wanted(x))) {
	const text = readFileSync(f, 'utf8');
	if (!GUJARATI.test(text)) continue;
	const lines = text.split('\n').map((l, i) => [i + 1, l]).filter(([, l]) => GUJARATI.test(l));
	ok(`bn-script: ${rel(f)} carries no Gujarati script`, false, `${lines.length} line(s), first at line ${lines[0][0]}`);
}
if (ONLY.length === 0) ok('bn-script: every BN pack file was examined', PACKS.length >= 16, `${PACKS.length} packs`);

console.log(failures ? `\n${failures} check(s) failed` : '\nall bn-script checks passed');
process.exit(failures ? 1 : 0);
