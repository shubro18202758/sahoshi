/**
 * Reference photographs of real places (static/photos; credits and licences in static/photos/NOTICE.md). A photo is
 * ALWAYS shown with "Reference photo · not live" and its credit, never where a live camera or a map is expected, and
 * never as the current situation: it shows what the place looks like, not what is happening there.
 */
import { PHOTO_ROWS } from './photos.data';

export interface PlacePhoto {
	slug: string;
	title: string;
	/** The curated place key: a landmarks.json id (howrah_bridge, victoria_memorial, eden_gardens …) or a subject (taxi, tram, pandal …). */
	place: string;
	lat: number;
	lon: number;
	/** The coordinates are the photo's own place (false: the city's centroid; never matched by distance). */
	near: boolean;
	author: string;
	license: string;
	licenseUrl: string;
	/** The Wikimedia Commons file page. */
	source: string;
	/** "Photo: <author> · <licence> · Wikimedia Commons". */
	credit: string;
}

export const PHOTOS: readonly PlacePhoto[] = PHOTO_ROWS;
const BY_SLUG = new Map(PHOTOS.map((p) => [p.slug, p]));

export function photoBySlug(slug: string | null | undefined): PlacePhoto | null {
	return (slug && BY_SLUG.get(slug)) || null;
}

export function photoSrc(p: PlacePhoto, w: 640 | 1600 = 640): string {
	return `/photos/${p.slug}-${w}.webp`;
}

export function photoSrcset(p: PlacePhoto): string {
	return `${photoSrc(p, 640)} 640w, ${photoSrc(p, 1600)} 1600w`;
}

/** A place photographed more than once by time of day (Howrah Bridge by day and at night): the one that matches the IST hour. */
function variant(list: readonly PlacePhoto[], hour: number | null): PlacePhoto | null {
	if (!list.length) return null;
	if (hour == null || list.length === 1) return list[0];
	const want = hour >= 7 && hour < 17 ? ['day', 'dusk'] : hour >= 17 && hour < 19 ? ['dusk', 'night'] : ['night', 'dusk'];
	for (const w of want) {
		const hit = list.find((p) => p.slug.endsWith(`-${w}`));
		if (hit) return hit;
	}
	return list[0];
}

/** A photo of a curated place key. */
export function photoForPlace(place: string | null | undefined, hour: number | null = null): PlacePhoto | null {
	if (!place) return null;
	return variant(
		PHOTOS.filter((p) => p.place === place),
		hour,
	);
}

const R = 6_371_000;
function metres(aLon: number, aLat: number, bLon: number, bLat: number): number {
	const r = Math.PI / 180;
	const dLat = (bLat - aLat) * r;
	const dLon = (bLon - aLon) * r;
	const h = Math.sin(dLat / 2) ** 2 + Math.cos(aLat * r) * Math.cos(bLat * r) * Math.sin(dLon / 2) ** 2;
	return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
}

/** The nearest photographed place within `maxM` metres of a point (only photos whose coordinates are their own). */
export function photoNear(lon: number | null | undefined, lat: number | null | undefined, maxM = 900, hour: number | null = null): PlacePhoto | null {
	if (lon == null || lat == null || !Number.isFinite(lon) || !Number.isFinite(lat)) return null;
	let best: PlacePhoto | null = null;
	let bestD = Infinity;
	for (const p of PHOTOS) {
		if (!p.near) continue;
		const d = metres(lon, lat, p.lon, p.lat);
		if (d < bestD) {
			best = p;
			bestD = d;
		}
	}
	if (!best || bestD > maxM) return null;
	const place = best.place;
	return variant(PHOTOS.filter((p) => p.place === place && p.near), hour) ?? best;
}

/** Place names in a title or a road name that have a photograph (word-bounded, case-insensitive). */
const WORDS: readonly [RegExp, string][] = [
	[/\bhowrah\s+(bridge|setu)\b|\brabindra\s+setu\b|হাওড়া ব্রিজ|रवींद्र सेतु|हावड़ा ब्रिज/i, 'howrah_bridge'],
	[/\b(vidyasagar|second hooghly)\s+(setu|bridge)\b|বিদ্যাসাগর সেতু|विद्यासागर सेतु/i, 'vidyasagar_setu'],
	[/\bvictoria\s+memorial\b|ভিক্টোরিয়া মেমোরিয়াল|विक्टोरिया मेमोरियल/i, 'victoria_memorial'],
	[/\bpark\s+street\b|পার্ক স্ট্রিট|पार्क स्ट्रीट/i, 'park_street'],
	[/\b(esplanade|chowringhee|dharmatala|jawaharlal nehru road|jl nehru road)\b|এসপ্ল্যানেড|ধর্মতলা|एस्प्लेनेड/i, 'esplanade'],
	[/\bprinsep\s+ghat\b|প্রিন্সেপ ঘাট/i, 'prinsep_ghat'],
	[/\beden\s+gardens\b|ইডেন গার্ডেন্স|ईडन गार्डन्स/i, 'eden_gardens'],
	[/\b(salt\s?lake\s+stadium|yuva\s?bharati)\b|যুবভারতী/i, 'salt_lake_stadium'],
	[/\b(biswa\s+bangla\s+(gate|sarani)|new\s?town)\b|বিশ্ব বাংলা|নিউ টাউন|न्यू टाउन/i, 'biswa_bangla_sarani'],
	[/\bscience\s+city\b|সায়েন্স সিটি|साइंस सिटी/i, 'science_city'],
	[/\bred\s+road\b|রেড রোড|रेड रोड/i, 'red_road'],
	[/\bhowrah\s+(station|junction|terminus)\b|হাওড়া স্টেশন|हावड़ा स्टेशन/i, 'howrah_station'],
	[/\bsealdah\b|শিয়ালদহ|सियालदह/i, 'sealdah'],
	[/\bkumartuli\b|কুমোরটুলি|कुमारटुली/i, 'kumartuli'],
	[/\b(hooghly|hugli)\b|হুগলি|हुगली/i, 'hooghly_river'],
	[/\b(metro|underground)\b|মেট্রো|मेट्रो/i, 'metro'],
	[/\b(tram|tramway)\b|ট্রাম|ट्राम/i, 'tram'],
	[/\b(ferry|launch|jetty)\b|ফেরি|লঞ্চ|फ़ेरी/i, 'ferry'],
	[/\b(pandal|durga\s+puja|puja)\b|প্যান্ডেল|পুজো|পূজা|पंडाल|दुर्गा पूजा/i, 'pandal'],
	[/\b(waterlog\w*|flooded street)\b|জল জমা|জলমগ্ন|जलभराव/i, 'waterlogging'],
	[/\b(taxi|ambassador)\b|ট্যাক্সি|टैक्सी/i, 'taxi'],
];

/** A photo for the first place named in a text (a title, a road, a destination). */
export function photoForText(text: string | null | undefined, hour: number | null = null): PlacePhoto | null {
	if (!text) return null;
	for (const [re, place] of WORDS) if (re.test(text)) return photoForPlace(place, hour);
	return null;
}
