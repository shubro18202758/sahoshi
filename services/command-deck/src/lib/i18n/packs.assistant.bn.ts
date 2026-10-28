/**
 * packs.assistant — the BN strings (FIX-E-PERF2): the ONE copy that runs. The
 * server render, vite dev and the node tests import it from ./packs.assistant.ts; the
 * production browser fetches it as its own chunk (lib/i18n/load.ts). Values
 * are byte-identical to the pre-split module (tests/perf2.unit.mjs pins the
 * key count and a content hash per module and language).
 */

type Pack = Record<string, string | ((...args: unknown[]) => string)>;

const s = (v: unknown) => String(v ?? '');
export const bn: Pack = {
	asst_tab: 'সহকারী',
	asst_page_title: 'সহকারী',
	asst_page_sub: 'এটি শহরের পরিস্থিতি পড়ে প্রস্তাব দেয়। প্রস্তাবগুলি সেখানেই খোলে যেখানে কোনো মানুষ সেগুলি যাচাই করেন — এখানে কিছুই প্রয়োগ হয় না।',
	asst_actor: 'সাহসী সহকারী · শুধু পড়ার জন্য',
	asst_context_title: 'প্রসঙ্গ',
	asst_context_none: 'কিছু বেছে নেওয়া হয়নি',
	asst_context_hint: 'একটি অবজেক্ট বেছে নিন, সহকারী শুধু সেটি নিয়েই কাজ করবে',
	asst_decisions: 'সিদ্ধান্তের অপেক্ষায়',
	asst_citations: 'উল্লেখিত অবজেক্ট',
	asst_clear: 'কথোপকথন মুছে ফেলুন',

	asst_scope_prefix: 'শুধু',
	asst_scope: (what: unknown) => `শুধু ${s(what)} ও এই দৃশ্য নিয়ে`,
	asst_scope_suffix: 'ও এই দৃশ্য নিয়ে',
	asst_scope_view: 'শুধু এই দৃশ্য নিয়ে',

	asst_steps: 'ধাপ',
	asst_details: 'বিস্তারিত',
	asst_details_tools: 'টুল কল',
	asst_lookups_label: 'লুকআপে কী পাওয়া গেল',
	asst_grounding_removed: (n) => `${String(n)}টি বক্তব্য বাদ দেওয়া হয়েছে: লুকআপে ছিল না`,
	asst_details_model: 'মডেল',
	asst_details_tier: 'স্তর',
	asst_details_session: 'সেশন',
	asst_steps_toggle: 'ধাপগুলি দেখান',
	asst_thoughts_toggle: 'যুক্তি দেখান',

	asst_proposed_map: (what: unknown) => `মানচিত্রে প্রস্তাবিত: ${s(what)}`,
	asst_review_map: 'মানচিত্রে খুলে দেখুন',
	asst_decision_card: 'সিদ্ধান্তের অপেক্ষায়',

	asst_cite_select_map: 'মানচিত্রে বেছে নিন',

	asst_ev_state_planned: 'পরিকল্পিত',
	asst_ev_state_active: 'চলছে',
	asst_ev_state_completed: 'সম্পন্ন',
	asst_ev_state_cancelled: 'বাতিল',
	asst_interrupted: 'থেমে গেছে — উত্তর শেষ হওয়ার আগেই প্যানেল বন্ধ করা হয়েছিল।',

	asst_empty_title: 'সহকারীকে জিজ্ঞাসা করুন',
	asst_sample_note: 'চিহ্নিত নমুনা কথোপকথন, পর্যালোচনার জন্য তৈরি। কোনো মডেল চালানো হয়নি।',

	asst_citizen_hold_one: 'নিচে 1টি এমুলেটেড হোল্ডের তালিকা আছে।',
	asst_citizen_hold_many: (n: unknown) => `নিচে ${n}টি এমুলেটেড হোল্ডের তালিকা আছে।`,

	asst_driver_choose_stretch: 'আগে আপনার অবস্থান বেছে নিন — তারপর করিডরের অনুরোধ করুন।',
};
