/**
 * Agency and data-source marks (static/logos; owners and sources in static/logos/NOTICE.md). Used as-is — trimmed and
 * resized only, never redrawn or recoloured — on a light plate where a mark needs one. The marks belong to their
 * owners; Sahoshi is a prototype and is not affiliated with or endorsed by them (the credit line says so where credits
 * live). When a mark is missing, the caller falls back to the generic agency tile (static/illustrations/agencies).
 */
import { MARK_ROWS } from './logos.data';

export interface Mark {
	key: string;
	/** The owner's name as the owner writes it (EN; the pack has HI / BN). */
	name: string;
	src: string;
	w: number;
	h: number;
	/** 'light': a white plate (a dark or transparent mark that would vanish on the night ground); 'dark': a dark plate (white lettering); 'none'. */
	plate: 'light' | 'dark' | 'none';
}

export const MARKS: readonly Mark[] = MARK_ROWS;
const BY_KEY = new Map(MARKS.map((m) => [m.key, m]));

/** Roles the deck speaks of → the marks that stand for them, best first (keys are cities/kolkata/city.json agency ids). */
// West Bengal Fire & Emergency Services, ERSS 112, the ambulance (108) service and citizen volunteers have no mark on
// file: they keep the generic badge.
const ROLE: Readonly<Record<string, readonly string[]>> = {
	police: ['kp', 'wbp'],
	zone: ['kp', 'wbp'],
	traffic: ['kp'],
	kp_traffic: ['kp'],
	patrol: ['kp', 'wbp'],
	state_police: ['wbp'],
	bidhannagar: ['bpc'],
	salt_lake: ['bpc'],
	howrah: ['hcp'],
	municipal: ['kmc'],
	corporation: ['kmc'],
	new_town: ['nkda'],
	disaster: ['wbsdma', 'ndma'],
	sdrf: ['wbsdma', 'ndma'],
	sdma: ['wbsdma'],
	ndrf: ['ndma'],
	sachet: ['ndma_sachet'],
	weather: ['imd'],
	metro: ['metro'],
	bus: ['wbtc'],
	transport: ['wbtc'],
	osm: ['openstreetmap'],
	rain: ['open_meteo'],
	nowcast: ['open_meteo'],
	satellite: ['copernicus'],
	sentinel: ['copernicus'],
	dem: ['copernicus'],
	globe: ['cesium'],
};

/** The mark for a role, an agency or a source name (null when none is on file). */
export function markFor(role: string | null | undefined): Mark | null {
	const k = (role ?? '').toLowerCase().trim().replace(/[\s-]+/g, '_');
	if (!k) return null;
	const direct = BY_KEY.get(k);
	if (direct) return direct;
	for (const key of ROLE[k] ?? []) {
		const m = BY_KEY.get(key);
		if (m) return m;
	}
	return null;
}

/** A source's mark from its publisher / feed name or domain (Sachet, IMD, Open-Meteo, the corporation …); null when none is on file. */
export function sourceMark(publisher: string | null | undefined): Mark | null {
	const p = (publisher ?? '').toLowerCase();
	if (!p) return null;
	if (/sachet/.test(p)) return markFor('sachet');
	if (/wbsdma|wbdmd|west bengal (state )?disaster|disaster management (and|&) civil defence/.test(p)) return markFor('wbsdma');
	if (/ndma|disaster management/.test(p)) return markFor('ndma');
	if (/\bimd\b|meteorolog|mausam|alipore/.test(p)) return markFor('imd');
	if (/open-?meteo/.test(p)) return markFor('open_meteo');
	if (/copernicus|sentinel/.test(p)) return markFor('copernicus');
	if (/openstreetmap|\bosm\b/.test(p)) return markFor('openstreetmap');
	if (/\bkmc\b|kolkata municipal|kmcgov/.test(p)) return markFor('kmc');
	if (/\bnkda\b|new town kolkata/.test(p)) return markFor('nkda');
	if (/bidhannagar/.test(p)) return markFor('bpc');
	if (/howrah city police|howrahcitypolice/.test(p)) return markFor('hcp');
	if (/west bengal police|wbpolice/.test(p)) return markFor('wbp');
	if (/police/.test(p)) return markFor('police');
	if (/metro/.test(p)) return markFor('metro');
	if (/\bwbtc\b|transport corporation/.test(p)) return markFor('wbtc');
	return null;
}
