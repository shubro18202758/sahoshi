/**
 * What the landing page (/welcome) shows, as data — the page is static content and static assets only: no API call,
 * no store, no operator code. tests/welcome.unit.mjs reads this module (the links, the pictures, the captions), so a
 * change here is a change the test sees.
 *
 * Pictures, each with its honest label:
 *   - reference photos of Kolkata (static/photos, Wikimedia Commons): always "Reference photo · not live" + credit,
 *     drawn by Cover on the picture itself;
 *   - key art and the Hooghly scenes (static/artwork): original illustrations, captioned "Illustration";
 *   - agency and source marks (static/logos): as-is, with the owners' credit line;
 *   - one console screenshot in the hero window, taken on the Kolkata network with exercise (emulated) data and every
 *     plate masked (static/landing/NOTICE.md), captioned "Console screenshot · exercise data" on the picture.
 */
import { photoBySlug, type PlacePhoto } from '../media/photos';
import { markFor, type Mark } from '../media/logos';

/** Where each door leads. The console is an operator document (its own CSP), so links into it reload. */
export const HREF = {
	console: '/',
	analyst: '/analyst',
	citizen: '/citizen',
	driver: '/driver',
	source: 'https://github.com/shubro18202758/sahoshi',
	photoCredits: '/photos/NOTICE.md',
} as const;

/** The operator routes: a link to one of them must load a new document (data-sveltekit-reload). */
export const OPERATOR_HREFS: readonly string[] = [HREF.console, HREF.analyst];

/** A console screenshot (static/landing/console-<file>-{800,1600}.webp), the honest caption is the page's. */
export interface Shot {
	key: 'decide';
	src: string;
	srcset: string;
	w: number;
	h: number;
	alt: string;
}

function shot(key: Shot['key'], file: string, w: number, h: number, alt: string): Shot {
	return { key, src: `/landing/${file}-1600.webp`, srcset: `/landing/${file}-800.webp 800w, /landing/${file}-1600.webp 1600w`, w, h, alt };
}

export const SHOTS: Readonly<Record<Shot['key'], Shot>> = {
	decide: shot('decide', 'console-decide', 1600, 1000, 'v3l_shot_alt_decide'),
};

/** The console shown in the hero window: Decide, one emulated request waiting for a named officer. */
export const HERO_SHOT: Shot['key'] = 'decide';

/** The hero's photograph (Howrah Bridge lit at night) and the closing band's (the Hooghly at dusk). */
export const HERO_PHOTO_SLUG = 'howrah-bridge-night';
export const END_PHOTO_SLUG = 'hooghly-dusk';

export function heroPhoto(): PlacePhoto {
	const p = photoBySlug(HERO_PHOTO_SLUG);
	if (!p) throw new Error(`landing: no reference photo ${HERO_PHOTO_SLUG}`);
	return p;
}

export function endPhoto(): PlacePhoto {
	const p = photoBySlug(END_PHOTO_SLUG);
	if (!p) throw new Error(`landing: no reference photo ${END_PHOTO_SLUG}`);
	return p;
}

/** The city strip under the hero: reference photos of the places Sahoshi watches over (each with its label and credit). */
export const CITY_PHOTO_SLUGS = ['victoria-memorial', 'vidyasagar-setu', 'yellow-taxis', 'heritage-tram', 'kumartuli-idols'] as const;

export function cityPhotos(): PlacePhoto[] {
	return CITY_PHOTO_SLUGS.map((s) => {
		const p = photoBySlug(s);
		if (!p) throw new Error(`landing: no reference photo ${s}`);
		return p;
	});
}

/**
 * TODO-IMPACT — the three modelled figures for Kolkata. They come from IMPACT_REPORT.md once the Kolkata impact run is
 * in; until then each `value` is null and the page shows the metric with "Being modelled" in place of a number. Never
 * fill one with a figure that is not in the report (the report keeps each figure's assumptions).
 */
export const TODO_IMPACT = {
	pending: false,
	source: 'IMPACT_REPORT.md (Kolkata run, central case, MODELLED; range 25×–506×)',
	figures: [
		{ key: 'hold', value: '~2.5 min' as string | null },
		{ key: 'delay', value: '100×' as string | null },
		{ key: 'golden', value: '≈ 33,000' as string | null },
	],
};

/**
 * How it works: three steps, each with the key art of its moment in Kolkata — the storm over Howrah Bridge (see),
 * a waterlogged street and its diversion (decide), the advisory going out (act).
 */
export const STEPS = [
	{ n: 1, key: 'see', art: '/artwork/events/weather.svg' },
	{ n: 2, key: 'decide', art: '/artwork/events/flooding.svg' },
	{ n: 3, key: 'act', art: '/artwork/events/advisory.svg' },
] as const satisfies readonly { n: number; key: string; art: string }[];

/** For everyone: four seats, each with the key art of its work and the door it uses. */
export const AUDIENCES = [
	{ key: 'officer', art: '/artwork/events/protected_movement.svg', href: HREF.console, seat: 'console' },
	{ key: 'analyst', art: '/artwork/scenes/night.svg', href: HREF.analyst, seat: 'console' },
	{ key: 'citizen', art: '/artwork/events/cyclone.svg', href: HREF.citizen, seat: 'public' },
	{ key: 'driver', art: '/artwork/events/green_corridor.svg', href: HREF.driver, seat: 'public' },
] as const satisfies readonly { key: string; art: string; href: string; seat: 'console' | 'public' }[];

/** The principles, each with the glyph that signs it (`sign`; one glyph per noun, never a person). */
export const PRINCIPLES = [
	{ key: 'vehicles', sign: 'car' },
	{ key: 'masked', sign: 'lock' },
	{ key: 'officer', sign: 'badge' },
	{ key: 'holds', sign: 'clock' },
	{ key: 'victim', sign: 'shield' },
	{ key: 'labels', sign: 'verified' },
] as const satisfies readonly { key: string; sign: string }[];

/** Built on: four foundations, each with the marks of its sources (or the glyph that signs it). */
export const BUILT = [
	{ key: 'roads', marks: ['openstreetmap', 'copernicus'], sign: null },
	{ key: 'city', marks: ['cesium'], sign: null },
	{ key: 'alerts', marks: ['imd', 'ndma_sachet', 'open_meteo'], sign: null },
	{ key: 'ai', marks: [], sign: 'spark' },
] as const satisfies readonly { key: string; marks: readonly string[]; sign: string | null }[];

/** The agencies and sources whose marks the row shows (static/logos; city.json agency ids; the owners' credit line sits under it). */
export const MARK_ROW = ['kp', 'wbp', 'bpc', 'hcp', 'kmc', 'nkda', 'wbsdma', 'ndma', 'imd', 'metro', 'wbtc', 'openstreetmap', 'open_meteo', 'copernicus'] as const;

export function marks(keys: readonly string[]): Mark[] {
	return keys.map((k) => markFor(k)).filter((m): m is Mark => m !== null);
}
