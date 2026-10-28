/**
 * The deck's city module (src/lib/city) against the City Pack (cities/<id>/city.json + landmarks.json).
 *
 *   node tests/city.unit.mjs
 *
 *   1. src/lib/city/city.generated.ts is what scripts/gen_deck_city.mjs makes from the pack today (byte for
 *      byte): a pack edit without a regenerated module fails here;
 *   2. the API reads the pack: names EN/BN/HI, centre, the boxes, the cameras inside the city, landmarks by id,
 *      emergency numbers, agencies;
 *   3. the plate helpers: the pack's format ("WB 02 AB 1234"), any case and spacing, and every sample code is a
 *      mark the console's mask hides (workspace/mask.ts) — the mask stays the one rule;
 *   4. the map and corridor surfaces read the module, not literals: ops/endpoints re-exports the module's boxes,
 *      the planner's POIs are pack landmarks, and the map files carry no longitude literal of their own.
 *
 * esbuild bundles the REAL modules ($lib aliased, .svelte stubbed) in memory. Exits 0 with `ok` lines, 1 on any
 * failure.
 */

import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DECK = path.resolve(HERE, '..');
const REPO = path.resolve(DECK, '..', '..');

let failures = 0;
function ok(name, cond, detail = '') {
	if (cond) console.log(`ok   ${name}${detail ? ` — ${detail}` : ''}`);
	else {
		failures++;
		console.error(`FAIL ${name}${detail ? ` — ${detail}` : ''}`);
	}
}

// ─── 1. the generated module is up to date with the pack ────────────────────

const generated = readFileSync(path.join(DECK, 'src/lib/city/city.generated.ts'), 'utf8');
let fresh = '';
try {
	fresh = execFileSync(process.execPath, [path.join(DECK, 'scripts/gen_deck_city.mjs'), '--stdout'], { encoding: 'utf8' });
} catch (e) {
	fresh = `generator failed: ${e.message}`;
}
ok('city.generated.ts matches the City Pack (node scripts/gen_deck_city.mjs to refresh)', generated === fresh, `${generated.length} / ${fresh.length} bytes`);

const pack = JSON.parse(readFileSync(path.join(REPO, 'cities/kolkata/city.json'), 'utf8'));
const lm = JSON.parse(readFileSync(path.join(REPO, 'cities/kolkata/landmarks.json'), 'utf8'));

// ─── bundle the real modules ─────────────────────────────────────────────────

const esbuild = createRequire(path.join(DECK, 'package.json'))('esbuild');
const ENTRY = `
export * as city from './src/lib/city';
export * as mask from './src/lib/workspace/mask';
export * as endpoints from './src/lib/ops/endpoints';
`;
const built = await esbuild.build({
	stdin: { contents: ENTRY, resolveDir: DECK, loader: 'ts', sourcefile: 'city-entry.ts' },
	absWorkingDir: DECK,
	alias: { $lib: './src/lib' },
	bundle: true,
	format: 'esm',
	platform: 'node',
	write: false,
	logLevel: 'silent',
});
ok('bundle builds (esbuild, $lib aliased, in memory)', built.errors.length === 0 && built.outputFiles.length === 1);
const { city: C, mask: M, endpoints: E } = await import(`data:text/javascript;base64,${Buffer.from(built.outputFiles[0].text).toString('base64')}`);

// ─── 2. the API reads the pack ───────────────────────────────────────────────

ok('city id', C.CITY_ID === pack.id && pack.id === 'kolkata', C.CITY_ID);
ok(
	'city names EN/BN/HI from the pack (EN for any other code)',
	C.cityName('en') === pack.name.en && C.cityName('bn') === pack.name.bn && C.cityName('hi') === pack.name.hi && C.cityName('xx') === pack.name.en && C.cityName(null) === pack.name.en,
	`${C.cityName('en')} · ${C.cityName('bn')} · ${C.cityName('hi')}`,
);
ok('state names', C.stateName('en') === 'West Bengal' && C.stateName('bn') === pack.state.bn && C.stateName('hi') === pack.state.hi);
ok('river name', C.riverName('en') === pack.hydrology.river.en && C.riverName('bn') === pack.hydrology.river.bn);
ok('timezone', C.CITY_TIMEZONE === 'Asia/Kolkata');
ok('centre = city.json centre', C.CITY_CENTRE.lon === pack.centre.lon && C.CITY_CENTRE.lat === pack.centre.lat, JSON.stringify(C.CITY_CENTRE));
const B = pack.bbox;
const sameBox = (b) => b.minLon === B.west && b.minLat === B.south && b.maxLon === B.east && b.maxLat === B.north;
ok('CITY_BBOX and NETWORK_BBOX = city.json bbox', sameBox(C.CITY_BBOX) && sameBox(C.NETWORK_BBOX), JSON.stringify(C.CITY_BBOX));
ok('bboxArray is [west, south, east, north]', JSON.stringify(C.bboxArray(C.CITY_BBOX)) === JSON.stringify([B.west, B.south, B.east, B.north]));
const core = C.CITY_CORE_BBOX;
ok('the core box lies inside the city box', core.minLon > B.west && core.maxLon < B.east && core.minLat > B.south && core.maxLat < B.north && core.minLon < core.maxLon && core.minLat < core.maxLat, JSON.stringify(core));
const { home2d, home3d } = C.CITY_CAMERAS;
ok('the 2D home targets the city centre, pitched down', home2d.lon === pack.centre.lon && home2d.lat === pack.centre.lat && home2d.pitchDeg < -30 && home2d.range > 2000);
const esp = lm.landmarks.find((l) => l.id === 'esplanade');
const hb = lm.landmarks.find((l) => l.id === 'howrah_bridge');
const between = (x, a, b) => x >= Math.min(a, b) && x <= Math.max(a, b);
ok(
	'the 3D home is an oblique between Esplanade and Howrah Bridge, looking toward the bridge (north-ish)',
	between(home3d.lon, esp.lon, hb.lon) && between(home3d.lat, esp.lat, hb.lat) && home3d.headingDeg > -45 && home3d.headingDeg < 15 && home3d.pitchDeg <= -30 && home3d.pitchDeg >= -60,
	JSON.stringify(home3d),
);
ok('both homes lie in the city box', C.inBox(home2d.lon, home2d.lat) && C.inBox(home3d.lon, home3d.lat) && !C.inBox(72.58, 23.02));
ok('every landmark from the pack, with its names', C.LANDMARKS.length === lm.landmarks.length && lm.landmarks.every((l) => C.landmarkName(l.id, 'bn') === l.bn && C.landmarkName(l.id, 'en') === l.en && C.landmarkName(l.id, 'hi') === l.hi), `${C.LANDMARKS.length} landmarks`);
ok('landmark lookups', C.landmark('howrah_bridge')?.kind === 'bridge' && JSON.stringify(C.landmarkLonLat('esplanade')) === JSON.stringify([esp.lon, esp.lat]) && C.landmark('nope') === null && C.landmarkName('nope') === 'nope');
ok('emergency numbers', C.EMERGENCY.ambulance === '108' && C.EMERGENCY.unified === '112' && C.EMERGENCY.police === '100' && C.EMERGENCY.fire === '101');
ok('agencies with names EN/BN/HI', C.AGENCIES.length === pack.agencies.length && C.agencyName('kp_traffic', 'en') === 'Kolkata Traffic Police' && C.agencyName('kmc', 'bn') === pack.agencies.find((a) => a.id === 'kmc').bn && C.agencyName('none') === null);

// ─── 3. plates ───────────────────────────────────────────────────────────────

ok('plate state code and example from the pack', C.PLATE.stateCode === 'WB' && C.PLATE.example === 'WB 02 AB 1234' && C.PLATE.regex.source === pack.plates.regex);
const fmt = [
	['wb02ab1234', 'WB 02 AB 1234'],
	['WB-02-AB-1234', 'WB 02 AB 1234'],
	[' wb 2 ab 1234 ', 'WB 02 AB 1234'],
	['WB11C7', 'WB 11 C 7'],
	['WB 08 1234', 'WB 08 1234'],
	['not a plate', 'not a plate'],
];
const badFmt = fmt.filter(([i, o]) => C.formatPlate(i) !== o);
ok('formatPlate writes the pack form; other text comes back trimmed', badFmt.length === 0, badFmt.map(([i]) => `${i} → ${C.formatPlate(i)}`).join(' | '));
ok('isCityPlate: WB marks in any case; another state is not this city', C.isCityPlate('wb 02 ab 1234') && C.isCityPlate('WB-12-AB-1') && !C.isCityPlate('DL 8C AB 1234') && !C.isCityPlate('') && !C.isCityPlate(null));
const samples = C.PLATE.sampleCodes.map((code) => C.samplePlate(code, 'AB', '1234'));
const unmasked = samples.filter((p) => M.maskMarks(p) !== p.replace(/1234$/, '•••4') || !M.hasRawMark(p));
ok('every sample mark is masked by the deck mask (WB 02 AB 1234 → WB 02 AB •••4)', samples.length >= 8 && unmasked.length === 0, unmasked.join(' | ') || samples.join(', '));
ok('the mask still covers every state (a visitor’s mark is hidden too)', M.maskMarks('DL8CAB1234') === 'DL8CAB•••4' && M.STATE_CODES.includes('WB') && M.STATE_CODES.length === 39);

// ─── 4. the surfaces read the module ─────────────────────────────────────────

ok('ops/endpoints CITY_BBOX / NETWORK_BBOX are the module’s', E.CITY_BBOX === C.CITY_BBOX && E.NETWORK_BBOX === C.NETWORK_BBOX);

const poiSrc = readFileSync(path.join(DECK, 'src/lib/corridor/escort-state.svelte.ts'), 'utf8');
const poiIds = [...poiSrc.matchAll(/^\t'([a-z0-9_]+)',$/gm)].map((m) => m[1]);
ok('the planner POIs are pack landmarks (14, Nabanna at 1, the airport at 12)', poiIds.length === 14 && poiIds.every((id) => C.landmark(id)) && poiIds[1] === 'nabanna' && poiIds[12] === 'airport', poiIds.join(','));

// A longitude literal for India (68–97 °E, 2+ decimals) in a map/home file means a hard-coded city.
const LON = /(?<![\w.])(?:6[89]|[7-9]\d)\.\d{2,}(?![\w.])/;
const MAP_FILES = [
	'src/lib/gods-eye/GodsEyeCanvas.svelte',
	'src/lib/gods-eye/hud/map/MapReadout.svelte',
	'src/lib/gods-eye/layers/basemap.ts',
	'src/lib/gods-eye/layers/photoreal-3d.ts',
	'src/lib/gods-eye/layers/draping.ts',
	'src/lib/v3/map/MapPage.svelte',
	'src/lib/v3/map/LayersSheet.svelte',
	'src/lib/v3/map/MapThumb.svelte',
	'src/lib/ops/endpoints.ts',
	'src/lib/decisions/wall/share.ts',
	'src/lib/citizen/LightCorridorMap.svelte',
	'src/lib/corridor/escort-state.svelte.ts',
];
const literal = MAP_FILES.map((f) => {
	const lines = readFileSync(path.join(DECK, f), 'utf8').split('\n');
	const i = lines.findIndex((l) => LON.test(l));
	return i >= 0 ? `${f}:${i + 1}` : null;
}).filter(Boolean);
ok('no map/home file carries a longitude literal (boxes and cameras come from $lib/city)', literal.length === 0, literal.join(' | ') || `${MAP_FILES.length} files`);

if (failures) {
	console.error(`city.unit: ${failures} failure(s)`);
	process.exit(1);
}
console.log('city.unit: all green');
