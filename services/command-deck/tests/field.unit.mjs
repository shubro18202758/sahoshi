/**
 * Field AI unit test (the voice field report, the camera road state, the forecast and waterlogging panels, the public
 * waterlogging card and Listen) — zero browser, zero network.
 *
 *   node tests/field.unit.mjs
 *
 * esbuild bundles the REAL modules (src/lib/v3/field/{model, labels, api, samples, packs.field*}, the object model, the
 * public projection's firewall) with `$lib` aliased; recorded service answers live in tests/fixtures/field.
 *
 * Asserts:
 *   - packs: EN / HI / BN carry the same fld_ keys (the main pack and the first-paint core); every fld_ key the code
 *     uses (literal or built from a kind, state, class, label) exists; ≤ one " · " per EN string; BN carries no
 *     Devanagari (the dari । aside) and HI no Bengali; the privacy line says audio is not stored
 *   - honesty: a field report is UNVERIFIED-FIELD and a camera reading UNVERIFIED-CAMERA whatever the wire says; a policy
 *     refusal is an answer; the forecast keeps its SIMULATED label; the nowcast's drivers keep theirs
 *   - the board: the ingestion payload (POST /api/v1/events) is `planning`-bound — no verification_state, never
 *     CONFIRMED, created by a named officer (2..64 characters, no control or bidirectional characters), unverified in its
 *     title, metadata and provenance, no person key anywhere (the oracle's own denylist), no closure; a clear or unclear
 *     camera reading makes none; the oracle's real request model accepts every draft (the gate venv, when present)
 *   - the public firewall: a field- or camera-sourced row never reaches the citizen or driver feed
 *   - the road under a place, the waterlogging order and lead, tide and rain in words, the forecast chart, speakable text
 *   - the sample stills: every file exists, is the vision service's pixelated fixture byte for byte, and NOTICE.md
 *     credits it; the page labels it "Sample still · not live"
 *   - boundaries: the public card and Listen import no operator code and never write; the shell has ONE entry point that
 *     loads the sheet lazily; the road-state panel never sends a question (so never one about a person); the sheet keeps
 *     the privacy line and never stores audio (no storage API, no download)
 *
 * Exits 0 with `ok <name>` lines, 1 on any failure.
 */
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DECK = path.resolve(HERE, '..');
const REPO = path.resolve(DECK, '../..');
const OUT = path.join(HERE, 'artifacts', 'field-bundle.mjs');
const FIX = path.join(HERE, 'fixtures', 'field');

let failures = 0;
function ok(name, cond, detail = '') {
	if (cond) console.log(`ok   ${name}${detail ? ` — ${detail}` : ''}`);
	else {
		failures++;
		console.error(`FAIL ${name}${detail ? ` — ${detail}` : ''}`);
	}
}
const read = (rel) => readFileSync(path.join(DECK, rel), 'utf8');
const fixture = (f) => JSON.parse(readFileSync(path.join(FIX, f), 'utf8'));
const walk = (d, out = []) => {
	for (const e of readdirSync(path.join(DECK, d), { withFileTypes: true })) {
		const p = `${d}/${e.name}`;
		if (e.isDirectory()) walk(p, out);
		else if (/\.(svelte|ts)$/.test(e.name)) out.push(p);
	}
	return out;
};

// ─── bundle the real modules ────────────────────────────────────────────────

mkdirSync(path.dirname(OUT), { recursive: true });
const esbuild = createRequire(path.join(DECK, 'package.json'))('esbuild');
const ENTRY = `
export * as model from './src/lib/v3/field/model';
export * as labels from './src/lib/v3/field/labels';
export * as api from './src/lib/v3/field/api';
export * as samples from './src/lib/v3/field/samples';
export * as packs from './src/lib/v3/field/packs.field';
export { hi } from './src/lib/v3/field/packs.field.hi';
export { bn } from './src/lib/v3/field/packs.field.bn';
export { FIELD_CORE_PACKS } from './src/lib/v3/field/packs.field.core';
export { pickMime } from './src/lib/v3/field/recorder.svelte';
export * as objModel from './src/lib/v3/object/model';
export { isOsintRow, isFieldReportRow } from './src/lib/citizen/public-api.server';
export { t } from './src/lib/i18n/strings';
`;
const svelteStub = {
	name: 'svelte-component-stub',
	setup(build) {
		build.onResolve({ filter: /\.svelte$/ }, (args) => {
			const file = args.path.startsWith('$lib/') ? path.join(DECK, 'src/lib', args.path.slice(5)) : path.resolve(args.resolveDir, args.path);
			if (existsSync(`${file}.ts`) || existsSync(`${file}.js`)) return undefined;
			return { path: file, namespace: 'svelte-stub' };
		});
		build.onLoad({ filter: /.*/, namespace: 'svelte-stub' }, (args) => ({
			contents: `export default function ${path.basename(args.path, '.svelte').replace(/[^A-Za-z0-9_]/g, '_')}() {}`,
			loader: 'js',
		}));
		build.onResolve({ filter: /^\$app\// }, (args) => ({ path: args.path, namespace: 'app-stub' }));
		build.onLoad({ filter: /.*/, namespace: 'app-stub' }, () => ({ contents: 'export const browser = false; export const dev = true; export const building = false;', loader: 'js' }));
	},
};
const built = await esbuild.build({
	stdin: { contents: ENTRY, resolveDir: DECK, loader: 'ts', sourcefile: 'field-entry.ts' },
	absWorkingDir: DECK,
	alias: { $lib: './src/lib' },
	bundle: true,
	format: 'esm',
	platform: 'node',
	outfile: OUT,
	logLevel: 'silent',
	plugins: [svelteStub],
});
ok('bundle builds (esbuild, $lib aliased, .svelte stubbed)', built.errors.length === 0, `${built.errors.length} errors`);

globalThis.$state = Object.assign((v) => v, { raw: (v) => v, snapshot: (v) => v });
globalThis.$derived = Object.assign((v) => v, { by: (f) => f() });
globalThis.$effect = Object.assign(() => {}, { root: () => () => {}, pre: () => {} });
const calls = [];
globalThis.fetch = async (url, init = {}) => {
	calls.push(`${(init.method ?? 'GET').toUpperCase()} ${url}`);
	return new Response('{"detail":"offline test"}', { status: 503, headers: { 'content-type': 'application/json' } });
};

const M = await import(`${pathToFileURL(OUT).href}?t=${Date.now()}`);
const { model, labels, samples, packs } = M;

// ─── the packs ───────────────────────────────────────────────────────────────

{
	const en = Object.keys(packs.FIELD_PACKS.en);
	const same = (a, b) => a.length === b.length && a.every((k) => b.includes(k));
	ok('packs: EN / HI / BN carry the same keys, all fld_', same(en, Object.keys(M.hi)) && same(en, Object.keys(M.bn)) && en.every((k) => k.startsWith('fld_')), `${en.length} keys`);
	const core = M.FIELD_CORE_PACKS;
	ok('packs: the first-paint core carries the same keys in EN / HI / BN, none repeated in the main pack', same(Object.keys(core.en), Object.keys(core.hi)) && same(Object.keys(core.en), Object.keys(core.bn)) && Object.keys(core.en).every((k) => !en.includes(k)), Object.keys(core.en).join(', '));
	const all = new Set([...en, ...Object.keys(core.en)]);
	const files = [...walk('src/lib/v3/field'), ...walk('src/lib/v3/object'), ...walk('src/lib/v3/public'), ...walk('src/lib/citizen'), 'src/routes/(public)/driver/+page.svelte'].filter((f) => !/packs\.field/.test(f));
	const used = new Set();
	for (const f of files) for (const m of read(f).matchAll(/['"`](fld_[a-z0-9_]+)['"`]/g)) used.add(m[1]);
	const dyn = [
		...model.REPORT_KINDS.map((k) => `fld_kind_${k}`),
		...model.SEVERITIES.map((k) => `fld_sev_${k}`),
		...model.ROAD_STATES.map((k) => `fld_state_${k}`),
		...model.DEPTH_BANDS.map((k) => `fld_depth_${k}`),
		...model.VEHICLE_KEYS.map((k) => `fld_veh_${k}`),
		...[0, 1, 2, 3].flatMap((c) => [`fld_risk_${c}`, `fld_risk_${c}_sub`, `fld_pub_road_${c}`]),
		...['live', 'modelled', 'emulated', 'simulated'].map((k) => `fld_lbl_${k}`),
		...['night', 'dawn', 'morning', 'noon', 'afternoon', 'evening'].map((k) => `fld_say_${k}`),
	];
	const missing = [...used, ...dyn].filter((k) => !all.has(k));
	ok('packs: every fld_ key the code uses (literal or built) exists', missing.length === 0, missing.join(', ') || `${used.size} literal + ${dyn.length} built`);
	const text = (v) => (typeof v === 'function' ? v('‹x›', '‹y›', '‹z›', '‹w›') : v);
	const seps = Object.entries({ ...packs.FIELD_PACKS.en, ...core.en }).filter(([, v]) => (String(text(v)).match(/ · /g) ?? []).length > 1);
	ok('packs: at most one " · " per EN string', seps.length === 0, seps.map(([k]) => k).join(', '));
	const bnAll = { ...M.bn, ...core.bn };
	const hiAll = { ...M.hi, ...core.hi };
	const deva = Object.entries(bnAll).filter(([, v]) => /[ऀ-ॿ]/.test(String(text(v)).replace(/[।॥]/g, '')));
	const beng = Object.entries(hiAll).filter(([, v]) => /[ঀ-৿]/.test(String(text(v))));
	ok('packs: BN carries no Devanagari (the dari aside), HI no Bengali', deva.length === 0 && beng.length === 0, [...deva, ...beng].map(([k]) => k).join(', '));
	const bnSentences = Object.entries(M.bn).filter(([, v]) => typeof v === 'string' && /[।]/.test(v) && /\.\s*$/.test(v));
	ok('packs: a Bengali sentence ends with the dari, never a full stop', bnSentences.length === 0, bnSentences.map(([k]) => k).join(', '));
	const untranslated = en.filter((k) => typeof packs.FIELD_PACKS.en[k] === 'string' && packs.FIELD_PACKS.en[k].length > 3 && (M.bn[k] === packs.FIELD_PACKS.en[k] || M.hi[k] === packs.FIELD_PACKS.en[k]));
	ok('packs: HI and BN are translated', untranslated.length === 0, untranslated.join(', '));
	ok('packs: the privacy line says audio is not stored (EN / BN / HI)', /Audio is not stored/.test(M.t('en', 'fld_privacy')) && /অডিও রাখা হয় না/.test(M.t('bn', 'fld_privacy')) && /ऑडियो सहेजा नहीं/.test(M.t('hi', 'fld_privacy')));
	ok('packs: Listen is শুনুন in Bengali, सुनें in Hindi', M.t('bn', 'fld_listen') === 'শুনুন' && M.t('hi', 'fld_listen') === 'सुनें' && M.t('en', 'fld_listen') === 'Listen');
	ok('packs: the camera page says "Sample still · not live"', M.t('en', 'fld_rs_sample') === 'Sample still · not live' && M.t('bn', 'fld_rs_sample') === 'নমুনা ছবি · লাইভ নয়');
}

// ─── the field report ────────────────────────────────────────────────────────

const RAW_REPORT = {
	report_id: '039b66e2-22b6-416f-8572-1f1217569798',
	received_at: '2026-10-28T11:51:07+00:00',
	place: { id: 'gariahat', name_en: 'Gariahat crossing', name_bn: 'গড়িয়াহাট মোড়', lat: 22.519, lon: 88.366, match_score: 1.0, matched_text: 'গড়িয়াহাট মোড়ে', source: 'landmarks' },
	place_candidates: [
		{ id: 'gariahat', name_en: 'Gariahat crossing', name_bn: 'গড়িয়াহাট মোড়', lat: 22.519, lon: 88.366, match_score: 1.0 },
		{ id: 'rashbehari', name_en: 'Rashbehari crossing', name_bn: 'রাসবিহারী মোড়', lat: 22.518, lon: 88.35, match_score: 1.0 },
		{ id: 'gariahat', name_en: 'dup', name_bn: 'dup', lat: 1, lon: 1, match_score: 0.2 },
	],
	kind: 'waterlogging',
	kind_cues: ['জল জম'],
	severity: 'medium',
	severity_cues: ['হাঁটু'],
	transcript: 'গড়িয়াহাট মোড়ে হাঁটু জল জমেছে দয়া করে রাসবিহারী হয়ে বিকল্প পথ নিন',
	language: 'bn',
	asr: { model: 'bengaliAI/tugstugi_bengaliai-asr_whisper-medium', confidence: 0.995, audio_seconds: 7.99 },
	verification_state: 'OFFICIAL-VERIFIED',
	requires_confirmation: false,
};
const report = model.parseFieldReport(RAW_REPORT);
{
	ok('report: parsed; the label is UNVERIFIED-FIELD even when the wire claims more', report?.verification === 'UNVERIFIED-FIELD' && report.place?.id === 'gariahat' && report.kind === 'waterlogging' && report.severity === 'medium');
	ok('report: candidates deduped, at most three', report.candidates.length === 2 && report.candidates[1].id === 'rashbehari');
	ok('report: an unknown kind reads "other", an unknown severity "medium"; garbage is no report', model.parseFieldReport({ ...RAW_REPORT, kind: 'riot', severity: 'apocalyptic' }).kind === 'other' && model.parseFieldReport({ ...RAW_REPORT, severity: 'x' }).severity === 'medium' && model.parseFieldReport({ transcript: '' }) === null && model.parseFieldReport(null) === null);
	const runs = model.cueRuns(report.transcript, ['হাঁটু জল', 'জল জম (≈)']);
	ok('report: the cue words are marked in the transcript (the fuzzy "(≈)" suffix dropped)', runs.some((r) => r.cue && r.text === 'হাঁটু জল') && runs.map((r) => r.text).join('') === report.transcript);
	ok('report: the place ring widens as the match is less sure', model.placeRingM(1) < model.placeRingM(0.9) && model.placeRingM(0.9) < model.placeRingM(0.8));
}

// ─── the camera reading ──────────────────────────────────────────────────────

{
	const r = model.parseRoadState({ state: 'waterlogged', confidence: 0.98, vehicles_estimate: { cars: 2.6, buses: -1, two_wheelers: null }, water_depth_band: 'up_to_wheel_hub', rationale: 'Road is flooded.', verification_state: 'CONFIRMED', filtered: true });
	ok('camera: parsed; UNVERIFIED-CAMERA whatever the wire says; counts rounded, never negative', r?.ok === true && r.reading.verification === 'UNVERIFIED-CAMERA' && r.reading.vehicles.cars === 3 && r.reading.vehicles.buses === 0 && r.reading.vehicles.two_wheelers === null && r.reading.depth === 'up_to_wheel_hub' && r.reading.filtered === true);
	const refusal = model.parseRoadState({ refused: true, policy: 'vehicles-and-roads-only', reason: 'This service describes roads and vehicles only.' });
	ok('camera: a policy refusal is an answer (policy and reason kept)', refusal?.ok === false && refusal.policy === 'vehicles-and-roads-only' && /roads and vehicles/.test(refusal.reason));
	ok('camera: a state outside the list is no reading', model.parseRoadState({ state: 'crowded_with_people' }) === null);
	ok('camera: clear and unclear are never sent to the board', !model.sendableState('clear') && !model.sendableState('unknown') && model.sendableState('tree_fall'));
}

// ─── the board ───────────────────────────────────────────────────────────────

const PERSON = /author|person|handle|username|byline|reporter|poster|uploader|suspect|accused|victim|owner|driver_name|face|biometric|individual_/i;
const keysDeep = (o, out = []) => {
	if (o && typeof o === 'object') for (const [k, v] of Object.entries(o)) {
		if (!Array.isArray(o)) out.push(k);
		keysDeep(v, out);
	}
	return out;
};
const NOW = Date.parse('2026-10-28T12:00:00Z');
const drafts = [];
{
	ok('board: a named officer is 2..64 characters with no control or bidirectional characters', model.officerOf('Insp. R. Sen') === 'Insp. R. Sen' && model.officerOf('x') === null && model.officerOf('Ra‮jesh') === null && model.officerOf('  Insp.   R.  Sen ') === 'Insp. R. Sen' && model.officerOf('অফিসার সেন') === 'অফিসার সেন');
	const d = model.boardDraftFromReport(report, report.place, 1034, 'Insp. R. Sen', NOW, true);
	drafts.push(d);
	ok('board: a field report enters as a reported situation (flooding), created by the named officer, no closure', d.event_kind === 'flooding' && d.officer === 'Insp. R. Sen' && d.source_kind === 'operator' && d.protection_class === 'none' && !('phases' in d) && d.route_spines[0].segment_ids[0] === 1034);
	ok('board: never confirmed — no verification_state (the oracle creates it in planning), unverified in title, metadata and provenance', !('verification_state' in d) && !/CONFIRMED/.test(JSON.stringify(d)) && /^Unverified field report/.test(d.title) && d.metadata.source === 'field-voice' && d.metadata.verification === 'UNVERIFIED-FIELD' && d.provenance.verification === 'UNVERIFIED-FIELD' && d.provenance.audio_stored === false);
	ok('board: the transcript, place and cues travel in the description for the confirming officer', d.description.includes(report.transcript) && d.description.includes('Gariahat crossing') && /not an action/.test(d.description));
	ok('board: no person key anywhere (the oracle denylist)', !keysDeep(d).some((k) => PERSON.test(k)), keysDeep(d).filter((k) => PERSON.test(k)).join(', '));
	ok('board: the geotag rides only inside the city', d.geotag?.lon === 88.366 && model.boardDraftFromReport(report, report.place, 1034, 'Insp. R. Sen', NOW, false).geotag === null);
	ok('board: every report kind maps to an oracle event kind', model.REPORT_KINDS.every((k) => typeof model.BOARD_KIND_FOR_REPORT[k] === 'string'));
	for (const k of model.REPORT_KINDS) drafts.push(model.boardDraftFromReport({ ...report, kind: k, typed: k === 'other' }, report.place, 1034, 'Insp. R. Sen', NOW, true));
	const reading = model.parseRoadState({ state: 'tree_fall', confidence: 0.95, vehicles_estimate: { cars: 3, buses: 0, two_wheelers: 2, autos: 0 }, rationale: 'Fallen tree branches obstruct the road.' }).reading;
	const cam = { id: 'EM-J12', label: 'Jawaharlal Nehru Road approach (EM-J12)', lon: 88.3501, lat: 22.5549, sample: 'amphan_shyambazar_09' };
	const c = model.boardDraftFromReading(reading, cam, 1018, 'Insp. R. Sen', NOW, true);
	drafts.push(c);
	ok('board: a camera reading enters labelled UNVERIFIED-CAMERA, the sample still named, no image stored', c.metadata.source === 'camera-ai' && c.metadata.verification === 'UNVERIFIED-CAMERA' && /^Unverified camera reading/.test(c.title) && c.provenance.image_stored === false && c.description.includes('not a live frame') && !keysDeep(c).some((k) => PERSON.test(k)));
	ok('board: a clear or unclear reading makes no entry', model.boardDraftFromReading({ ...reading, state: 'clear' }, cam, 1018, 'x y', NOW, true) === null && model.boardDraftFromReading({ ...reading, state: 'unknown' }, cam, 1018, 'x y', NOW, true) === null);
	for (const s of model.ROAD_STATES) {
		const dd = model.boardDraftFromReading({ ...reading, state: s }, cam, 1018, 'Insp. R. Sen', NOW, true);
		if (dd) drafts.push(dd);
	}
	ok('board: the object page labels a field / camera board entry (its one provenance tag)', M.objModel.provenanceOf({ kind: 'event', source: 'live', verification: null, test: false, props: { metadata: { source: 'field-voice' } } }) === 'UNVERIFIED-FIELD' && M.labels.fieldLabelOf({ source: 'camera-ai' }) === 'UNVERIFIED-CAMERA' && M.labels.fieldLabelOf({ source: 'osint' }) === null);
	// the oracle's own request model (pydantic) must accept every draft — the payload is exactly what the board ingests
	const py = '/home/sandy050405/argus/sahoshi/.venvs/gate/bin/python';
	const oracleSrc = path.join(REPO, 'services/traffic-oracle/src');
	if (existsSync(py) && existsSync(oracleSrc)) {
		const tmp = path.join(HERE, 'artifacts', 'field-drafts.json');
		writeFileSync(tmp, JSON.stringify(drafts));
		const r = spawnSync(py, ['-c', `
import json, sys
from traffic_oracle.events import CorridorEventRequest
bad = []
for d in json.load(open(sys.argv[1])):
    try:
        CorridorEventRequest.model_validate(d)
    except Exception as e:
        bad.append(str(e)[:200])
print(json.dumps({"n": len(json.load(open(sys.argv[1]))), "bad": bad}))
`, tmp], { env: { ...process.env, PYTHONPATH: oracleSrc }, encoding: 'utf8', timeout: 120000 });
		let res = null;
		try {
			res = JSON.parse((r.stdout || '').trim().split('\n').pop());
		} catch {
			res = null;
		}
		ok("board: the oracle's CorridorEventRequest accepts every draft (field kinds, camera states)", !!res && res.bad.length === 0, res ? `${res.n} drafts${res.bad.length ? ` — ${res.bad[0]}` : ''}` : (r.stderr || '').slice(-200));
	} else console.log('skip board: the gate venv or the oracle source is not here — the pydantic check did not run');
}

// ─── the public firewall ─────────────────────────────────────────────────────

{
	ok('public: a field- or camera-sourced row never reaches the citizen or driver feed', M.isFieldReportRow({ metadata: { source: 'field-voice' } }) && M.isOsintRow({ metadata: { source: 'camera-ai' } }) && !M.isOsintRow({ metadata: { source: 'brain' } }));
	ok('public: a procession reported from the field is still held back (whatever its kind)', M.isOsintRow({ event_kind: 'procession', status: 'approved', metadata: { source: 'field-voice' } }));
}

// ─── the road under a place ──────────────────────────────────────────────────

{
	const segs = [
		{ segmentId: 1, coordinates: [[88.36, 22.52], [88.37, 22.52]] },
		{ segmentId: 2, coordinates: [[88.30, 22.60], [88.31, 22.60]] },
	];
	const near = model.nearestSegment([88.366, 22.519], segs);
	ok('road: the nearest network road within 1.5 km', near?.segmentId === 1 && near.distanceM < 200, JSON.stringify(near));
	ok('road: none when nothing is that close', model.nearestSegment([88.5, 22.7], segs) === null);
}

// ─── waterlogging, tide, rain ────────────────────────────────────────────────

{
	const raw = fixture('nowcast.json');
	const n = model.parseNowcast(raw);
	ok('water: the recorded nowcast parses; every segment keeps its drivers and their labels', n && n.segments.length === 4 && n.segments.every((s) => s.drivers.rain?.label && s.drivers.tide?.label && s.drivers.pumps?.label === 'EMULATED'), `${n?.segments.length}`);
	ok('water: the honest labels in words (LIVE / MODELLED (approximate) / EMULATED / SIMULATED)', model.labelKey('LIVE') === 'live' && model.labelKey('MODELLED (approximate)') === 'modelled' && model.labelKey('EMULATED') === 'emulated' && model.labelKey('SIMULATED') === 'simulated' && model.labelKey(undefined) === 'modelled');
	const base = raw.segments[0];
	const crafted = model.parseNowcast({ ...raw, segments: [
		{ ...base, segment_id: 9001, risk_class: 1, lead_time_min: 60 },
		{ ...base, segment_id: 9002, risk_class: 3, lead_time_min: 45, lead_time_deep_min: 30 },
		{ ...base, segment_id: 9003, risk_class: 2, lead_time_min: 75, lead_time_deep_min: 40 },
		{ ...base, segment_id: 9004, risk_class: 2, lead_time_min: 15, lead_time_deep_min: 0 },
	] });
	ok('water: roads at risk, worst first, then soonest', model.atRisk(crafted).map((s) => s.segmentId).join() === '9002,9004,9003,9001');
	ok('water: the lead a citizen hears — deep water for class ≥ 2, null when it is already so', model.leadFor(crafted.segments[2]) === 40 && model.leadFor(crafted.segments[3]) === null && model.leadFor(crafted.segments[0]) === 60);
	ok('water: class counts and the flagged list (class ≥ 2)', crafted.counts.join() === '0,1,2,1' && crafted.flagged.join() === '9002,9003,9004');
	const now = Date.parse(fixture('tide.json').now.t);
	const tide = model.parseTide(fixture('tide.json'), now);
	ok('tide: level, direction, gates and the next high water after now', tide && tide.levelM !== null && typeof tide.rising === 'boolean' && tide.nextHighAt > now && tide.series.length > 10, tide ? `${tide.levelM} m, next high ${new Date(tide.nextHighAt).toISOString()}` : '');
	const rain = model.parseRain(fixture('rain.json'), now);
	ok('rain: the city mean now and the next two hours (recorded dry evening → none)', rain && rain.nowMmH === 0 && model.rainWord(rain) === 'none');
	const wet = model.parseRain({ city: { series: [0, 1, 2, 3, 4, 5, 6, 7, 8].map((i) => ({ t: new Date(now + i * 900_000).toISOString(), mm_h: 12 })) } }, now);
	ok('rain: heavy when ≥ 7.5 mm an hour or ≥ 15 mm in 2 h', model.rainWord(wet) === 'heavy' && model.rainWord({ nowMmH: 1, next2hMm: 2 }) === 'light');
}

// ─── the forecast ────────────────────────────────────────────────────────────

{
	const fc = model.parseSegmentForecast(fixture('forecast_1043_crossing.json'));
	ok('forecast: parsed with its SIMULATED label, the crossing and the proposal', fc && fc.dataLabel === 'SIMULATED' && fc.crossing?.inMin === 15 && fc.proposal && fc.steps.length === 8 && fc.steps.every((s) => s.p10 <= s.p50 && s.p50 <= s.p90));
	const ch = model.forecastChart(fc, 640, 200);
	ok('forecast: the chart has a closed band, a median, the 0.8 line inside the plot and the crossing marked', ch.band.endsWith('Z') && ch.median.startsWith('M') && ch.thresholdY > ch.pad.t && ch.thresholdY < ch.h - ch.pad.b && !!ch.crossPt && ch.yMin <= 0.8 && ch.yMax >= 0.8);
	const quiet = model.parseSegmentForecast(fixture('forecast_1052.json'));
	ok('forecast: a road without a crossing has none, and keeps its label', quiet && quiet.crossing === null && quiet.dataLabel === 'SIMULATED');
	ok('forecast: garbage is no forecast', model.parseSegmentForecast({}) === null && model.parseSegmentForecast({ segment: { steps: [] } }) === null);
}

// ─── Listen ──────────────────────────────────────────────────────────────────

{
	const long = 'জল জমেছে। '.repeat(80);
	const s = model.speakable(long);
	ok('listen: at most 400 characters, cut at a sentence end', s.length <= 400 && s.endsWith('।'), `${s.length}`);
	const c = model.spokenClock(Date.parse('2026-10-28T21:52:00Z'), Date.parse('2026-10-28T12:00:00Z'));
	ok('listen: a clock for the ear — 03:22 IST the next day is "night, 3, 22, tomorrow"', c.part === 'night' && c.hour === 3 && c.minute === 22 && c.tomorrow === true, JSON.stringify(c));
	ok('listen: the Bengali voice hears "রাত 3টে 22 মিনিটে" and "3 দশমিক 6", never "03:22" or "3.6"', M.t('bn', 'fld_say_clock', M.t('bn', 'fld_say_night'), 3, 22) === 'রাত 3টে 22 মিনিটে' && M.t('bn', 'fld_say_decimal', 3, 6) === '3 দশমিক 6' && M.t('en', 'fld_say_clock', M.t('en', 'fld_say_night'), 3, 5) === 'at 3:05 at night');
		ok('listen: the page language (bn | en | hi), Bengali for anything else', model.speakLang('en') === 'en' && model.speakLang('hi') === 'hi' && model.speakLang('bn') === 'bn' && model.speakLang('gu') === 'bn' && model.speakLang(null) === 'bn');
	ok('listen: the speech path is the one the deck gate admits publicly', M.api.SPEECH === '/api/speech/speech' && M.api.HYDRO === '/api/hydro/hydro');
	ok('recorder: Opus in WebM first, then the browser’s other audio types', M.pickMime((t) => t !== 'audio/webm;codecs=opus') === 'audio/webm' && M.pickMime(() => true) === 'audio/webm;codecs=opus' && M.pickMime(() => false) === null);
	ok('recorder: the audio type sent to the service drops codec parameters', M.api.audioType({ type: 'audio/webm;codecs=opus' }) === 'audio/webm' && M.api.audioType({ type: '' }) === 'audio/webm');
}

// ─── the sample stills ───────────────────────────────────────────────────────

{
	const notice = read('static/samples/cameras/NOTICE.md');
	const vfix = path.join(REPO, 'services/vision/tests/fixtures');
	const rows = samples.SAMPLE_STILLS;
	const bad = rows.filter((s) => {
		const f = path.join(DECK, 'static', s.src);
		if (!existsSync(f)) return true;
		if (!notice.includes(path.basename(s.src)) || !notice.includes(s.author) || !notice.includes(s.licence)) return true;
		const v = path.join(vfix, path.basename(s.src));
		return existsSync(v) && !readFileSync(v).equals(readFileSync(f));
	});
	ok('samples: 4–6 stills, each present, credited in NOTICE.md, and the pixelated vision fixture byte for byte', rows.length >= 4 && rows.length <= 6 && bad.length === 0, bad.map((s) => s.id).join(', ') || rows.map((s) => s.id).join(', '));
	const stray = readdirSync(path.join(DECK, 'static/samples/cameras')).filter((f) => f !== 'NOTICE.md' && !rows.some((s) => s.src.endsWith(`/${f}`)));
	ok('samples: nothing in static/samples/cameras is unlisted', stray.length === 0, stray.join(', '));
	ok('samples: a camera keeps its sample (stable per camera)', samples.sampleFor('EM-J12').id === samples.sampleFor('EM-J12').id && rows.includes(samples.sampleFor('anything')));
	const panel = read('src/lib/v3/object/RoadStatePanel.svelte');
	ok('samples: the camera page labels the still "Sample still · not live" and prints its credit', /fld_rs_sample/.test(panel) && /fld_rs_credit/.test(panel) && /sample\.source/.test(panel));
}

// ─── boundaries and ethics in the code ───────────────────────────────────────

{
	const pub = ['src/lib/v3/public/WaterOnYourRoad.svelte', 'src/lib/v3/public/ListenButton.svelte', 'src/lib/v3/public/LazyWater.svelte', 'src/lib/v3/public/LazyListen.svelte'];
	const DENY = /(\$lib\/(ops|shell|workspace|decisions|gods-eye\/entities)|\/board['"]|\.\.\/object\/|\.\.\/shell\/|field\/board)/;
	const offenders = pub.flatMap((f) => [...read(f).matchAll(/(?:from|import)\s*\(?\s*['"]([^'"]+)['"]/g)].filter((m) => DENY.test(m[1])).map((m) => `${f} → ${m[1]}`));
	ok('boundary: the public card and Listen import no operator code and no board writer', offenders.length === 0, offenders.join(' | '));
	const apiSrc = read('src/lib/v3/field/api.ts').replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
	ok('boundary: the public client (api.ts) has no writer — the board entry lives in board.ts (operator pages only)', !/\/api\/v1\/events|EVENTS_API/.test(apiSrc) && /EVENTS_API/.test(read('src/lib/v3/field/board.ts')));
	ok('boundary: only the sheet and the camera panel import the board writer', [...walk('src/lib'), ...walk('src/routes')].filter((f) => /from '(\.\/|\.\.\/field\/)board'/.test(read(f))).sort().join() === ['src/lib/v3/field/FieldReportSheet.svelte', 'src/lib/v3/object/RoadStatePanel.svelte'].join());
	const top = read('src/lib/v3/shell/TopBar.svelte');
	ok('shell: ONE entry point in the top bar', (top.match(/<FieldReportEntry\b/g) ?? []).length === 1);
	const entry = read('src/lib/v3/field/FieldReportEntry.svelte');
	ok('shell: the entry loads the sheet lazily (no recorder, map or writer in the first load)', /import\('\.\/FieldReportSheet\.svelte'\)/.test(entry) && !/import\s+\w+\s+from\s+'\.\/FieldReportSheet/.test(entry) && /packs\.field\.core/.test(entry) && !/'\.\/packs\.field'/.test(entry));
	const panel = read('src/lib/v3/object/RoadStatePanel.svelte');
	ok('ethics: the road-state panel never sends a question (so never one about a person)', !/question/i.test(panel) && !/question/.test(apiSrc.slice(apiSrc.indexOf('readRoadState'))));
	const sheet = read('src/lib/v3/field/FieldReportSheet.svelte');
	const rec = read('src/lib/v3/field/recorder.svelte.ts');
	ok('privacy: the sheet keeps the line, and no recording is stored (no storage, no download, the microphone released)', /fld_privacy/.test(sheet) && !/localStorage|sessionStorage|indexedDB|download=|createObjectURL/.test(sheet + rec) && /getTracks\(\)[^;]*tr\.stop\(\)/.test(rec));
	ok('honesty: the sheet shows UNVERIFIED-FIELD and the camera panel UNVERIFIED-CAMERA', /data-label="UNVERIFIED-FIELD"/.test(sheet) && /data-label="UNVERIFIED-CAMERA"/.test(panel) && /data-label="SIMULATED"/.test(read('src/lib/v3/object/SegmentForecastPanel.svelte')) && /data-label="MODELLED"/.test(read('src/lib/v3/object/SegmentWaterPanel.svelte')) && /data-label="MODELLED"/.test(read('src/lib/v3/public/WaterOnYourRoad.svelte')));
	ok('honesty: the sheet never confirms — no confirm verb, one POST per press through the writer', !/confirm\w*\(/.test(sheet.replace(/\/\*[\s\S]*?\*\//g, '')) && (sheet.match(/writeBoardEntry\(/g) ?? []).length === 1);
	const patch = path.join(REPO, '..', '.orchestration', 'patches', 'int-field-microphone.patch');
	const p2 = '/home/sandy050405/argus/sahoshi/.orchestration/patches/int-field-microphone.patch';
	const pf = existsSync(patch) ? patch : p2;
	if (existsSync(pf)) ok('microphone: the hooks patch grants the microphone to this origin on the (v3) console only', /microphone=\(\$\{microphone \? 'self' : ''\}\)/.test(readFileSync(pf, 'utf8')) && /startsWith\('\/\(v3\)'\)/.test(readFileSync(pf, 'utf8')));
	else console.log('skip microphone: the hooks patch is not in this checkout (it ships through .orchestration/patches)');
	ok('offline: nothing in this test reached the network', calls.length === 0, calls.join(' | '));
}

if (failures) {
	console.error(`\nfield: ${failures} failure(s)`);
	process.exit(1);
}
console.log('\nall field checks passed');
