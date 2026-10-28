/**
 * packs.agent — the BN strings (FIX-E-PERF2): the ONE copy that runs. The
 * server render, vite dev and the node tests import it from ./packs.agent.ts; the
 * production browser fetches it as its own chunk (lib/i18n/load.ts). Values
 * are byte-identical to the pre-split module (tests/perf2.unit.mjs pins the
 * key count and a content hash per module and language).
 * ./packs.agent.ts keeps a never-registered text mirror of this block for
 * two AST-reading tests; tests/perf2.unit.mjs pins both copies.
 */

type Pack = Record<string, string | ((...args: unknown[]) => string)>;

export const bn: Pack = {
	agent_suggests: 'এআই-এর প্রস্তাব',
	agent_apply: 'প্রয়োগ করুন',
	agent_dismiss: 'সরিয়ে দিন',
	agent_applied: 'প্রয়োগ হয়েছে',
	agent_dismissed: 'সরানো হয়েছে',
	agent_ack_failed: 'এখানে প্রয়োগ হয়েছে — অডিটের প্রাপ্তিস্বীকৃতি ব্রেনে পৌঁছায়নি',
	agent_proposal: 'এটি শুধু প্রস্তাব — কোনো মানুষ প্রয়োগ না করা পর্যন্ত কিছুই কার্যকর হয় না',
	agent_from: (tier) => `এজেন্টের কাছ থেকে (${tier} স্তর)`,
	agent_more: (n) => `আরও +${n}`,
	agent_open_map: 'মানচিত্রে খুলুন',
	agent_queue_note: 'এআই-এর প্রস্তাবগুলি সিটি কমান্ড ক্যানভাসে অপেক্ষা করে',
	agent_verb_canvas_fly_to: 'সেখানে যান',
	agent_verb_canvas_track_entity: 'ট্র্যাক করুন',
	agent_verb_canvas_highlight: 'হাইলাইট করুন',
	agent_verb_canvas_annotate: 'নোট',
	agent_verb_canvas_set_sensor: 'থার্মাল-ধাঁচের দৃশ্য',
	agent_verb_canvas_toggle_layer: 'স্তর',
	agent_note_label: 'এআই নোট',

	chat_suggest_title: 'চেষ্টা করে দেখুন',
	chat_suggest_traffic: 'এই করিডরে লাইভ ট্রাফিক',
	chat_suggest_interception: 'ইন্টারসেপশন পরিকল্পনা',
	chat_suggest_closures: 'রাস্তা বন্ধের অবস্থা',
	chat_suggest_map: 'মানচিত্রে দেখান',
	chat_suggest_stolen: 'চুরি যাওয়া গাড়িটি মানচিত্রে দেখান',
	chat_suggest_events: 'কোন কোন ঘটনা চলছে?',
	chat_suggest_units: 'ইউনিটগুলি কোথায়?',
	chat_cited: 'উল্লেখিত',
	chat_directives: 'মানচিত্রে প্রস্তাবিত',
	chat_open_city: 'সিটি কমান্ডে খুলুন',

	pal_title: 'কমান্ড প্যালেট',
	// FIX-E-LOOKUP: the example names the thermal-style view and its palette in words, not a sensor mode
	pal_placeholder: 'fly to a plate or junction, show police units near Esplanade, layer cameras off, থার্মাল-ধাঁচের দৃশ্য: আয়রনবো, ask …',
	pal_hint: '⌘K বা Ctrl + K · ↑↓ দিয়ে বেছে নিন, Enter চালায়, Esc বন্ধ করে',
	pal_fly: 'সেখানে যান',
	pal_units: 'ইউনিট দেখান',
	pal_layer: 'স্তর',
	pal_sensor: 'থার্মাল-ধাঁচের দৃশ্য',
	pal_ask: 'এজেন্টকে জিজ্ঞাসা করুন',
	pal_no_match: 'কোনো গাড়ি, জংশন, রাস্তা বা অন্য কিছু মেলেনি',
	pal_vehicles_only: 'শুধু গাড়ি (ANPR নম্বর প্লেট) — কোনো ব্যক্তিকে খোঁজার ব্যবস্থা নেই',
	pal_sent: 'এজেন্টকে পাঠানো হয়েছে — তার প্রস্তাব এই ক্যানভাসেই আসবে',
	pal_units_near: (n, road) => `${road}-এর কাছে ${n}টি ইউনিট`,
	pal_none_near: (road) => `এই মুহূর্তে ${road}-এর কাছে কোনো ইউনিট নেই`,
	pal_unknown_road: 'নেটওয়ার্কে এই নামে কোনো রাস্তা নেই',

	dossier_explain: 'এটি বুঝিয়ে দিন',
	dossier_explaining: 'বোঝানো হচ্ছে…',
	dossier_explain_cancel: 'বাতিল',
	dossier_explain_masked: 'নম্বর প্লেট আড়াল করা — নাম-নথিভুক্ত ডিউটি অফিসার সেগুলি দেখতে পান',
	dossier_explain_failed: 'এজেন্ট উত্তর দেয়নি',
	dossier_explain_by: 'এজেন্টের উত্তর',
	dossier_test: 'পরীক্ষা',
	dossier_session_officer: 'সাইন-ইন করা ডিউটি অফিসার',

	canvas_live_paused: 'লাইভ থেমে আছে',
	canvas_live_paused_hint: 'ক্যানভাসে রিপ্লে চলছে — LIVE চাপলে লাইভ স্তরগুলি আবার চলবে',
	canvas_ama_title:
		'সক্রিয় যাত্রা-অভিযোজন — পরিস্থিতি → হিস্টেরেসিস → নীতির ন্যূনতম সীমা → টুইন শ্যাডো-যাচাই (ফেল-ক্লোজড) → অডিট-সহ সংরক্ষণ। বয়স = ব্যান্ডের সবচেয়ে নতুন রিডিংয়ের পর কতটা সময় গেছে (ঘটনার সর্বশেষ পরিস্থিতি-রিডিং, বা শহরের ব্যান্ডের সর্বশেষ ইঞ্জিন মূল্যায়ন) — ব্যান্ড কতক্ষণ টিকে আছে তা নয়। STALE = 10 মিনিট ধরে কোনো নতুন রিডিং নেই।',
};
