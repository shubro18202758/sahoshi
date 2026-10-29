/**
 * The landing page's string pack (/welcome). EN here; HI and BN in ./packs.landing.hi.ts and
 * ./packs.landing.bn.ts, complete for every key (tests/welcome.unit.mjs checks it). Registered additively through
 * registerPack(); loaded only by the landing page. Every key starts with `v3l_`.
 *
 * Copy rules (the deck's): sentence case, at most one " · " per string, titles and headings ≤ 32 characters, no
 * all-caps word outside the acronym list. Honest wording: the figures are modelled and say so; minutes returned to
 * the golden hour are never a claim about patients' outcomes; until the Kolkata run is in, the figures say "Being
 * modelled" (content.ts TODO_IMPACT); a reference photo is never live; the agencies' marks belong to their owners (packs.media says so).
 */
import { registerPack } from '$lib/i18n/strings';
import { langChunks } from '$lib/i18n/load';

type Fn = (...args: unknown[]) => string;
export type LandingPack = Record<string, string | Fn>;

const s = (v: unknown) => String(v ?? '');

const en = {
	v3l_doc: 'Sahoshi · Keep Kolkata moving',
	v3l_meta: 'Sahoshi gives Kolkata\'s traffic police, the corporation, disaster teams and ambulance (108) crews one live picture of the roads, the rain and the crowds. The AI proposes; a named officer decides.',
	v3l_skip: 'Skip to the page',
	v3l_logo: 'Sahoshi',
	v3l_nav: 'Sahoshi pages',
	v3l_lang: 'Language',
	v3l_nav_how: 'How it works',
	v3l_nav_rules: 'Principles',
	v3l_nav_citizen: 'Your road',
	v3l_nav_driver: 'Ambulance (108)',
	v3l_open_console: 'Open the console',
	v3l_check_road: 'Check your road',
	v3l_hero_eyebrow: 'City operations · Kolkata',
	v3l_hero_h: 'Keep Kolkata moving.',
	v3l_hero_sub: 'One live picture of Kolkata\'s roads, rain and crowds — the AI proposes, a named officer decides.',
	v3l_hero_rule: 'Vehicles only. Plates stay masked until an officer is named.',
	v3l_tagline_gloss: 'Not by stopping, by steering.',
	v3l_tagline_lead: 'Not by stopping.',
	v3l_tagline_turn: 'By steering.',
	v3l_shot_tag: 'Console screenshot · exercise data',
	v3l_shot_alt_decide: 'Screenshot of Decide: an ambulance (108) corridor request on the Kolkata map, waiting for a named officer',
	v3l_city_kicker: 'The city',
	v3l_city_heading: 'Built for Kolkata',
	v3l_city_lead: 'Two banks of the Hooghly and the bridges between them, a monsoon that meets the tide, and a Puja that fills every street.',
	v3l_problem_kicker: 'The problem',
	v3l_problem_line: 'When heavy rain meets a high tide on the Hooghly, the outfalls close and streets go under within the hour.',
	v3l_problem_rule: 'Add the Puja crowds, two bridges that carry both banks and cyclones that fell trees across arterials. Sahoshi puts it in one picture, so an officer can steer the city instead of stopping it.',
	v3l_fig_hold_label: 'a rolling hold per junction for a protected movement, in place of a full freeze',
	v3l_fig_delay_label: 'less junction-freeze delay for commuters on Kolkata\'s corridors',
	v3l_fig_golden_label: 'golden-hour minutes a year returned to ambulance (108) trips',
	v3l_fig_pending: 'Being modelled',
	v3l_modelled: 'Modelled',
	v3l_modelled_note: 'Model outputs on Kolkata\'s road network under stated assumptions — not field measurements, and not a claim about patient outcomes.',
	v3l_modelled_todo: 'The Kolkata figures are being modelled; they appear here when the impact run is published.',
	v3l_how_kicker: 'How it works',
	v3l_how_heading: 'See. Decide. Act.',
	v3l_how_lead: 'Each step is one screen, with one job and one primary button.',
	v3l_step: (n: unknown) => `Step ${s(n)}`,
	v3l_see: 'See',
	v3l_see_title: 'One live picture',
	v3l_see_body: 'Roads, rain, tide and crowds on one map: official alerts, sensors and public reports about places, never people.',
	v3l_decide: 'Decide',
	v3l_decide_title: 'The AI proposes, you decide',
	v3l_decide_body: 'A diversion, a rolling hold or an advisory, with what changes if you approve it and a named officer on the record.',
	v3l_act: 'Act',
	v3l_act_title: 'Steer, don\'t stop',
	v3l_act_body: 'Rolling holds instead of freezes, advisories in Bengali, English and Hindi, and a corridor window for the ambulance (108).',
	v3l_who_kicker: 'For everyone',
	v3l_who_heading: 'Four seats, one picture',
	v3l_who_officer: 'Duty officer',
	v3l_who_officer_body: 'What needs me now, the map of the place, and my name on every decision.',
	v3l_who_analyst: 'Analyst',
	v3l_who_analyst_body: 'The full workspace one click deeper: timeline, audit trail, forecasts and replay.',
	v3l_who_citizen: 'Citizen',
	v3l_who_citizen_body: 'Which roads are waterlogged, held or diverted, in plain words and in your language. No sign-in.',
	v3l_who_driver: 'Ambulance (108) crew',
	v3l_who_driver_body: 'Ask for a green corridor in one tap, Bengali first, with a live countdown.',
	v3l_seat_console: 'In the console',
	v3l_seat_public: 'Public page',
	v3l_rules_kicker: 'Principles',
	v3l_rules_heading: 'Rules the code enforces',
	v3l_rule_vehicles: 'Vehicles only',
	v3l_rule_vehicles_body: 'Cameras read number plates. No face, no person and no biometric field anywhere.',
	v3l_rule_masked: 'Plates masked',
	v3l_rule_masked_body: 'A number plate stays masked until a duty officer is named on the console.',
	v3l_rule_officer: 'The AI proposes, an officer decides',
	v3l_rule_officer_body: 'Nothing is approved, dispatched or rerouted without a named officer.',
	v3l_rule_holds: 'No answer, the plan holds',
	v3l_rule_holds_body: 'A time-boxed proposal expires and the current plan stays in force.',
	v3l_rule_victim: 'No fine on a theft victim',
	v3l_rule_victim_body: 'Reads of a stolen vehicle are evidence only. An e-challan on it is refused.',
	v3l_rule_labels: 'Honest labels',
	v3l_rule_labels_body: 'Emulated, simulated, modelled, unverified or official: every source says which.',
	v3l_built_kicker: 'Built on',
	v3l_built_heading: 'Real roads, real sources',
	v3l_built_roads: 'Real roads',
	v3l_built_roads_body: 'Kolkata\'s road network from OpenStreetMap, and Copernicus terrain for where water collects.',
	v3l_built_city: 'The photoreal city',
	v3l_built_city_body: 'Google Photorealistic 3D Tiles through Cesium ion. A reference picture, not a live image.',
	v3l_built_alerts: 'Official alerts',
	v3l_built_alerts_body: 'IMD and NDMA Sachet warnings for West Bengal, and an Open-Meteo rain nowcast, read when each feed is on.',
	v3l_built_ai: 'Local open-source AI',
	v3l_built_ai_body: 'Open models on one server beside the control room, with no cloud. Every answer is checked against the data.',
	v3l_marks_heading: 'Agencies and sources',
	v3l_end_heading: 'One city, one picture',
	v3l_end_body: 'Officers work in the console. Everyone else can check a road or ask for a corridor, with no sign-in.',
	v3l_driver_page: 'Open the ambulance (108) page',
	v3l_foot_pages: 'Pages',
	v3l_foot_console: 'Console',
	v3l_foot_citizen: 'Citizen',
	v3l_foot_driver: 'Ambulance (108) crew',
	v3l_foot_source: 'Source code on GitHub',
	v3l_foot_credits: 'Credits',
	v3l_foot_osm: 'Road data © OpenStreetMap contributors, ODbL 1.0.',
	v3l_foot_code: 'The code is open source.',
	v3l_foot_proto: 'Sahoshi is a prototype. Every feed it emulates or simulates is labelled as such.',
	v3l_illustration: 'Illustration',
};

export type LandingKey = keyof typeof en;

registerPack('en', en);

export const LANDING_PACK_KEYS: readonly LandingKey[] = Object.keys(en) as LandingKey[];
export const LANDING_PACKS: Record<string, LandingPack> = { en };

/** Register one language chunk (lib/i18n/load.ts's landing site; additive, first registration wins). */
export function adopt(code: 'hi' | 'bn', pack: LandingPack): void {
	LANDING_PACKS[code] = pack;
	registerPack(code, pack);
}

/*
 * Language chunks (the deck's FIX-E-PERF2 pattern): HI and BN live only in their own files. The server render and every
 * non-production run register both before this module finishes evaluating; the production browser awaits the document's
 * language and loads the other on the first switch.
 */
if (process.env.NODE_ENV !== 'production' || import.meta.env.SSR !== false) {
	adopt('hi', (await import('./packs.landing.hi')).hi);
	adopt('bn', (await import('./packs.landing.bn')).bn);
} else {
	await langChunks('packs.landing', (code) =>
		code === 'hi' ? import('./packs.landing.hi').then((c) => adopt('hi', c.hi)) : import('./packs.landing.bn').then((c) => adopt('bn', c.bn)),
	);
}
