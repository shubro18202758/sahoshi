/** packs.pub3 — the BN strings (see ./packs.pub3.ts). */
import type { PubKey } from './packs.pub3';

type Fn = (...args: unknown[]) => string;
const s = (v: unknown) => String(v ?? '');

export const bn: Record<PubKey, string | Fn> = {
	v3p_skip: 'মূল পাতায় যান',
	v3p_logo: 'সাহসী',
	v3p_lang_short_en: 'EN',
	v3p_lang_short_hi: 'हिं',
	v3p_lang_short_bn: 'বাং',
	v3p_hold_map_alt: 'এই ঘটনার জন্য যে রাস্তাগুলি আটকে থাকবে, তার মানচিত্র',
	v3p_step: (n: unknown) => `ধাপ ${s(n)}`,
	v3p_sat_credit: 'মানচিত্রের তথ্য © OpenStreetMap অবদানকারীরা',
	v3p_map_title: 'করিডরের মানচিত্র',
	v3p_open_driver: 'চালকের পাতা খুলুন',
	v3p_view_tabs: 'সর্বজনীন পাতা',
};
