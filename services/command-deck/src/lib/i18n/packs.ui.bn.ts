/**
 * packs.ui — the BN strings (FIX-E-PERF2): the ONE copy that runs. The
 * server render, vite dev and the node tests import it from ./packs.ui.ts; the
 * production browser fetches it as its own chunk (lib/i18n/load.ts). Values
 * are byte-identical to the pre-split module (tests/perf2.unit.mjs pins the
 * key count and a content hash per module and language).
 */

import type { UiKey } from './packs.ui';
type Fn = (...args: unknown[]) => string;
export const bn: Record<UiKey, string | Fn> = {
	ui_close: 'বন্ধ করুন',
	ui_dismiss: 'সরিয়ে দিন',
	ui_remove: 'বাদ দিন',
	ui_clear: 'মুছে ফেলুন',
	ui_cancel: 'বাতিল',
	ui_confirm: 'নিশ্চিত করুন',
	ui_loading: 'লোড হচ্ছে',
	ui_more: 'আরও',
	ui_err_404_title: 'পেজ পাওয়া যায়নি',
	ui_err_404_body: 'এই ঠিকানায় কোনো পেজ নেই। বার থেকে একটি মডিউল খুলুন, অথবা করিডর ওয়ার্কস্পেসে যান।',
	ui_err_title: 'এই পেজটি দেখানো গেল না',
	ui_err_body: 'লোড করার সময় সমস্যা হয়েছে। পেজটি আবার লোড করুন, অথবা করিডর ওয়ার্কস্পেসে যান।',
	ui_err_home: 'করিডর ওয়ার্কস্পেস খুলুন',
	ui_expand: 'বড় করুন',
	ui_collapse: 'ছোট করুন',
	ui_show_details: 'বিস্তারিত দেখান',
	ui_hide_details: 'বিস্তারিত লুকান',
	ui_sort_asc: 'ঊর্ধ্বক্রমে সাজানো',
	ui_sort_desc: 'নিম্নক্রমে সাজানো',
	ui_sort_by: (col: unknown) => `${String(col)} অনুযায়ী সাজান`,
	ui_table_empty: 'দেখানোর মতো কিছু নেই',
	ui_location: 'অবস্থান',
	ui_notifications: 'বিজ্ঞপ্তি',
	ui_resize: 'আকার বদলান',
	ui_trend: 'প্রবণতা',

	ui_masked: 'আড়াল করা',
	ui_masked_tip: 'ডিউটি অফিসারের নাম নথিভুক্ত না হওয়া পর্যন্ত রেজিস্ট্রেশন নম্বর আড়াল থাকবে।',

	ui_prov_emulated: 'এমুলেটেড',
	ui_prov_simulated: 'সিমুলেটেড',
	ui_prov_test: 'পরীক্ষা',
	ui_prov_osint: 'ওপেন-সোর্স',
	ui_prov_emulated_tip: 'সিনারিও এমুলেটর থেকে। মাঠ থেকে পাওয়া রিডিং নয়।',
	ui_prov_simulated_tip: 'সিমুলেটেড ট্রাফিক ফিড: কৃত্রিম পর্যবেক্ষণ।',
	ui_prov_test_tip: 'মহড়া বা পরীক্ষার ডেটা।',
	ui_prov_osint_tip: 'ওপেন-সোর্স থেকে। যাচাইয়ের অবস্থা এখনও জানা নেই।',
	ui_prov_unknown: 'অজানা উৎস',
	ui_prov_unknown_tip: 'এই সারির উৎস এই কনসোল চেনে না।',
	ui_verif_unverified: 'যাচাই-না-হওয়া OSINT',
	ui_verif_news: 'সংবাদে প্রকাশিত',
	ui_verif_official: 'সরকারি, যাচাই করা',
	ui_verif_confirmed: 'অফিসার নিশ্চিত করেছেন',
	ui_verif_unverified_tip: 'ওপেন-সোর্স রিপোর্ট, সংবাদ বা সরকারি উৎসে সমর্থিত নয়।',
	ui_verif_news_tip: 'সংবাদমাধ্যমে প্রকাশিত। কোনো সরকারি উৎস যাচাই করেনি।',
	ui_verif_official_tip: 'সরকারি উৎস থেকে জারি, যেমন জনসাধারণের জন্য সতর্কতা।',
	ui_verif_confirmed_tip: 'নাম-নথিভুক্ত একজন অফিসার নিশ্চিত করেছেন।',

	ui_eye_show: 'দেখান',
	ui_eye_hide: 'লুকান',
	ui_eye_none: 'এখন কিছু নেই',

	ui_time_ist: 'IST',
	ui_time_hint: 'IST, 24-ঘণ্টার ঘড়ি',
	ui_time_invalid: 'সময় hh:mm আকারে লিখুন',
	ui_time_invalid_s: 'সময় hh:mm:ss আকারে লিখুন',

	ui_now: 'এখন',
	ui_ago: (x: unknown) => `${String(x)} আগে`,
	ui_in: (x: unknown) => `${String(x)} পরে`,
	ui_unit_s: 'সেকেন্ড',
	ui_unit_min: 'মিনিট',
	ui_unit_h: 'ঘণ্টা',
	ui_unit_d: 'দিন',

	ui_hotkeys_title: 'কিবোর্ড শর্টকাট',
	ui_hk_global: 'সাধারণ',
	ui_hk_docks: 'প্যানেল',
	ui_hk_lists: 'তালিকা ও টেবিল',
	ui_hk_omnibar: 'অবজেক্ট ও কমান্ড খুঁজুন',
	ui_hk_search: 'খোঁজার ঘরে যান',
	ui_hk_help: 'শর্টকাট দেখান',
	ui_hk_escape: 'বন্ধ করুন, তারপর মুছে ফেলুন',
	ui_hk_left_dock: 'বাঁ দিকের প্যানেল দেখান বা লুকান',
	ui_hk_right_dock: 'ডান দিকের প্যানেল দেখান বা লুকান',
	ui_hk_timeline: 'টাইমলাইন দেখান বা লুকান',
	ui_hk_next: 'পরের আইটেম',
	ui_hk_prev: 'আগের আইটেম',
	ui_hk_open: 'আইটেমটি খুলুন',
	ui_hk_rule: 'কিবোর্ডের একটি বোতাম চেপে কখনও অনুমোদন, আড়াল সরানো, জরিমানা, ডিসপ্যাচ বা প্রকাশ হয় না।',

	ui_fig_report: (n: unknown) => `${n}টি রিপোর্ট`,
	ui_fig_reports: (n: unknown) => `${n}টি রিপোর্ট`,
	ui_fig_context_note: 'জেলা সতর্কতা জারি আছে'
};
