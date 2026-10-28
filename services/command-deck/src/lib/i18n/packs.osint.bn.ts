/**
 * packs.osint — the BN strings (FIX-E-PERF2): the ONE copy that runs. The
 * server render, vite dev and the node tests import it from ./packs.osint.ts; the
 * production browser fetches it as its own chunk (lib/i18n/load.ts). Values
 * are byte-identical to the pre-split module (tests/perf2.unit.mjs pins the
 * key count and a content hash per module and language).
 */

type Fn = (...args: unknown[]) => string;
type OsintPack = Record<string, string | Fn>;
export const bn: OsintPack = {
	kind_reported_crime: 'রিপোর্ট হওয়া অপরাধ',
	kind_public_disorder: 'জনশৃঙ্খলায় বিঘ্ন',
	kind_road_accident: 'পথ দুর্ঘটনা',
	kind_hazard: 'বিপদ',
	kind_flooding: 'জল জমা',
	kind_infra_failure: 'পরিকাঠামো বিভ্রাট',

	os_group_situation: 'পরিস্থিতি',
	os_group_verification: 'যাচাই',
	os_group_location: 'অবস্থান',
	os_group_sources: 'উৎস',
	os_group_live: 'বর্তমান অবস্থা',
	os_group_place: 'স্থান',

	os_class: 'শ্রেণি',
	os_subtype: 'উপধরন',
	os_correlated: 'সম্পর্কিত শ্রেণি',
	os_summary: 'সারসংক্ষেপ',
	os_event_kind_reported_crime: 'রিপোর্ট হওয়া অপরাধ',
	os_event_kind_public_disorder: 'জনশৃঙ্খলায় বিঘ্ন',
	os_event_kind_road_accident: 'পথ দুর্ঘটনা',
	os_event_kind_hazard: 'বিপদ',
	os_event_kind_flooding: 'জল জমা',
	os_event_kind_infra_failure: 'পরিকাঠামো বিভ্রাট',
	os_event_kind_other: 'করিডরের ঘটনা',

	os_independent_publishers: 'স্বাধীন সংবাদমাধ্যম',
	os_cross_type: 'অন্য ধরনের উৎসের সমর্থন',
	os_yes: 'হ্যাঁ',
	os_no: 'না',

	os_toponym: 'স্থান',
	os_road: 'রাস্তা',
	os_junction: 'জংশন',
	os_geocode: 'অবস্থান মেলানোর নিশ্চয়তা',
	os_bucket_high: 'বেশি',
	os_bucket_medium: 'মাঝারি',
	os_bucket_low: 'কম',
	os_area_note: 'জেলা-স্তরের রিপোর্ট: রাস্তার নির্দিষ্ট অবস্থান নয়',

	os_source_link_withheld: 'উৎসের লিংক রাখা হয়নি (এতে কোনো ব্যক্তির নাম থাকতে পারে)',
	os_context_official: 'জেলায় সতর্কতা জারি',
	os_context_report: 'জেলা-স্তরের রিপোর্ট চালু',
	os_fig_context_official: 'জেলায় সতর্কতা জারি',
	os_fig_context_report: 'জেলা-স্তরের রিপোর্ট চালু',
	os_fetch_cached: 'ক্যাশ করা নমুনা',
	os_tier_official: 'সরকারি',
	os_tier_aggregator: 'সংবাদ সংকলক',
	os_tier_news_regional: 'আঞ্চলিক সংবাদ',
	os_tier_news_national: 'জাতীয় সংবাদ',
	os_tier_social_unverified: 'সোশ্যাল, যাচাই হয়নি',

	os_pick_reported: 'রিপোর্ট হয়েছে',
	os_pick_credibility: 'বিশ্বাসযোগ্যতা',
	os_pick_street: 'ব্যবস্থা নেওয়ার জন্য রিপোর্ট হওয়া একটি পরিস্থিতি।',
	os_pick_district: 'জেলা-স্তরের রিপোর্ট, জেলার রেফারেন্স বিন্দুতে দেখানো। রিপোর্টটি পুরো জেলার, এই জায়গার নয়।',
	os_pick_area_ring: 'জেলার রেফারেন্স বিন্দু ঘিরে একটি চিহ্ন-বলয়, রিপোর্টের এলাকা নয়।',
	os_pick_never_people: 'রিপোর্ট হওয়া পরিস্থিতি স্থান নিয়ে, কখনও মানুষ নিয়ে নয়।',
	os_layer_held_one: 'একক পোস্টের সোশ্যাল রিপোর্ট গোটা শহরে আটকে রাখা (কখনও দেখানো হয় না)',
	os_layer_down: 'সিটি ফিউশন পরিষেবা পাওয়া যাচ্ছে না — রিপোর্ট হওয়া পরিস্থিতি দেখানো হচ্ছে না',
	os_layer_on_canvas: (n: unknown) => `মানচিত্রে ${n}টি রিপোর্ট হওয়া পরিস্থিতি`,
	os_layer_area: (n: unknown) => `${n}টি এলাকা-স্তরের`,
	os_layer_waiting: (n: unknown) => `${n}টি সিদ্ধান্তের অপেক্ষায়`,
	os_layer_unmapped: (n: unknown) => `${n}টির অবস্থান-বিন্দু নেই`,
	os_pick_at: (place: unknown) => `${place}-এ`,
	os_layer_held_many: 'একক পোস্টের সোশ্যাল রিপোর্টগুলি গোটা শহরে আটকে রাখা (কখনও দেখানো হয় না)',

	os_attach: 'অবস্থা',
	os_attach_novel: 'নতুন পরিস্থিতি (প্রথম রিপোর্ট)',
	os_corroborates: 'একটি লাইভ বিষয়কে সমর্থন করে',
	os_promoted_to: 'করিডরের ঘটনায় উন্নীত',

	os_place_name: 'নাম',
	os_place_type: 'স্থানের ধরন',
	os_surface_forms: 'অন্য নাম',
	os_place_reports: 'যুক্ত রিপোর্ট',

	os_rule_note: 'ব্যবস্থা নেওয়ার জন্য রিপোর্ট হওয়া পরিস্থিতি। সাহসী কখনও মানুষ শনাক্ত করে না।',

	os_act_search_around: 'স্থানের আশেপাশে খুঁজুন',
	os_act_sources: 'উৎসের তালিকা খুলুন',

	os_state_surfaced: 'সামনে এসেছে',
};
