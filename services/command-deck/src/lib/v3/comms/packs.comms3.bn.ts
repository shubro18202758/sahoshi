/** packs.comms3 — the BN strings (see ./packs.comms3.ts). Nothing here says a draft was sent. */
import type { CommsKey } from './packs.comms3';

type Fn = (...args: unknown[]) => string;
const s = (v: unknown) => String(v ?? '');

export const bn: Record<CommsKey, string | Fn> = {
	v3c_sub: 'অফিসার কপি করে পাঠাবেন, তার জন্য খসড়া',
	v3c_events: 'ঘটনা',
	v3c_events_aria: 'যেসব ঘটনার পরামর্শ লেখা যায়',
	v3c_map_alt: (title: unknown) => `${s(title)}: জায়গার মানচিত্র`,
	v3c_no_place: 'এই ঘটনার মানচিত্রে এখনও কোনো অবস্থান নেই',
	v3c_open_event: 'ঘটনাটি খুলুন',
	v3c_row_withheld: 'নাগরিকদের দেখানো হয় না',
	v3c_facts_used: 'যে তথ্য ব্যবহার হয়েছে',
	v3c_f_kind: 'ঘটনার ধরন',
	v3c_f_road: 'রাস্তার অংশ',
	v3c_f_hold: 'হোল্ড',
	v3c_f_when: 'কখন থেকে',
	v3c_f_alt: 'বিকল্প পথ',
	v3c_f_unknown: 'জানানো হয়নি',
	v3c_sheet_aria: 'খসড়ার লগ ও ডিসপ্যাচ থ্রেড',
	v3c_close: 'বন্ধ করুন',
	v3c_copy_lang: (name: unknown) => `${s(name)} খসড়া কপি করুন`,
	v3c_copied_inline: 'কপি হয়েছে',
	v3c_tpl_hint: 'এই ধরনের ঘটনায় নাগরিকেরা যা পড়বেন',
	v3c_withheld_pick: 'খসড়া দেখতে অন্য প্রাপক বেছে নিন',
};
