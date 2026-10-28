/**
 * Agentic God's-eye string pack (en/hi/bn) — the AI-suggests chip and its
 * canvas bus, the agent console's suggestion / citation / directive chips,
 * the command palette (⌘K) and the dossier's "Explain this". Registered
 * additively via registerPack(); the core packs and strings*.ts stay frozen.
 *
 * Import side-effect: every surface that renders these keys imports this
 * module (GodsEyeCanvas, CommandPalette, ChatConsole).
 *
 * Operational codes stay English inside the strings (URNs, layer ids,
 * sensor modes, plate marks): the brain and the canvas speak them.
 */
import { registerPack } from './strings';
import { langChunks } from './load';

type Pack = Record<string, string | ((...args: unknown[]) => string)>;

const en: Pack = {
	agent_suggests: 'AI suggests',
	agent_apply: 'Apply',
	agent_dismiss: 'Dismiss',
	agent_applied: 'applied',
	agent_dismissed: 'dismissed',
	agent_ack_failed: 'applied here — the audit ack did not reach the brain',
	agent_proposal: 'a proposal — nothing moves until a human applies it',
	agent_from: (tier) => `from the agent (${tier} tier)`,
	agent_more: (n) => `+${n} more`,
	agent_open_map: 'Open on map',
	agent_queue_note: 'AI suggestions wait on the City command canvas',
	agent_verb_canvas_fly_to: 'fly to',
	agent_verb_canvas_track_entity: 'track',
	agent_verb_canvas_highlight: 'highlight',
	agent_verb_canvas_annotate: 'note',
	// FIX-E-LOOKUP audit E: the chip names the visual filter, never a sensor
	// (the thermal honesty sweep pins every language)
	agent_verb_canvas_set_sensor: 'thermal-style view',
	agent_verb_canvas_toggle_layer: 'layer',
	agent_note_label: 'AI note',

	chat_suggest_title: 'Try',
	chat_suggest_traffic: 'Live traffic on this corridor',
	chat_suggest_interception: 'Interception plan',
	chat_suggest_closures: 'Closure status',
	chat_suggest_map: 'Show it on the map',
	chat_suggest_stolen: 'Show the stolen vehicle on the map',
	chat_suggest_events: 'Which events are active?',
	chat_suggest_units: 'Where are the units?',
	chat_cited: 'Cited',
	chat_directives: 'Proposed on the map',
	chat_open_city: 'Open in City command',

	pal_title: 'Command palette',
	// FIX-E-LOOKUP: the example names the thermal-STYLE VIEW and its palette in
	// words — never "sensor flir-iron" (a visual filter is not a sensor)
	pal_placeholder: 'fly to a plate or junction, show police units near Esplanade, layer cameras off, thermal-style view: ironbow, ask …',
	pal_hint: '⌘K or Ctrl+K · ↑↓ choose, Enter runs, Esc closes',
	pal_fly: 'Fly to',
	pal_units: 'Show units',
	pal_layer: 'Layer',
	pal_sensor: 'Thermal-style view',
	pal_ask: 'Ask the agent',
	pal_no_match: 'No vehicle, junction, road or entity matches',
	pal_vehicles_only: 'Vehicles only (ANPR plates) — there is no person search',
	pal_sent: 'Sent to the agent — its suggestions arrive on this canvas',
	pal_units_near: (n, road) => `${n} unit(s) near ${road}`,
	pal_none_near: (road) => `no units near ${road} right now`,
	pal_unknown_road: 'no road by that name on the network',

	dossier_explain: 'Explain this',
	dossier_explaining: 'Explaining…',
	dossier_explain_cancel: 'Cancel',
	dossier_explain_masked: 'plates masked — a named duty officer sees them',
	dossier_explain_failed: 'the agent did not answer',
	dossier_explain_by: 'agent answer',
	dossier_test: 'Test',
	dossier_session_officer: 'signed-in duty officer',

	canvas_live_paused: 'Live paused',
	canvas_live_paused_hint: 'a replay owns the canvas — live layers resume on Live',
	// the AMA chip's TOOLTIP (GodsEyeCanvas title=…), not a section title: the `_title` suffix trips copy-lint's
	// 32-character title rule, so it needs the orchestrator's exemption (requested); the explanation stays whole
	canvas_ama_title:
		'Active movement adaptation — situation → hysteresis → policy floors → twin shadow-eval (fail-closed) → audited persistence. Age = time since the newest band reading (the event’s latest situation reading, or the city band’s latest engine evaluation) — not how long the band has held. Stale = no new reading for 10 min.',
};

const hi: Pack = {
	agent_suggests: 'AI का सुझाव',
	agent_apply: 'लागू करें',
	agent_dismiss: 'खारिज करें',
	agent_applied: 'लागू किया',
	agent_dismissed: 'खारिज किया',
	agent_ack_failed: 'यहाँ लागू किया — ऑडिट पावती ब्रेन तक नहीं पहुँची',
	agent_proposal: 'केवल प्रस्ताव — मानव के लागू करने तक कुछ नहीं हिलता',
	agent_from: (tier) => `एजेंट से (${tier} स्तर)`,
	agent_more: (n) => `+${n} और`,
	agent_open_map: 'मानचित्र पर खोलें',
	agent_queue_note: 'AI सुझाव सिटी कमांड कैनवास पर प्रतीक्षा करते हैं',
	agent_verb_canvas_fly_to: 'यहाँ जाएँ',
	agent_verb_canvas_track_entity: 'ट्रैक करें',
	agent_verb_canvas_highlight: 'हाइलाइट करें',
	agent_verb_canvas_annotate: 'नोट',
	agent_verb_canvas_set_sensor: 'थर्मल-शैली दृश्य',
	agent_verb_canvas_toggle_layer: 'परत',
	agent_note_label: 'AI नोट',

	chat_suggest_title: 'आज़माएँ',
	chat_suggest_traffic: 'इस कॉरिडोर पर लाइव ट्रैफ़िक',
	chat_suggest_interception: 'इंटरसेप्शन योजना',
	chat_suggest_closures: 'बंद मार्गों की स्थिति',
	chat_suggest_map: 'मानचित्र पर दिखाएँ',
	chat_suggest_stolen: 'चोरी का वाहन मानचित्र पर दिखाएँ',
	chat_suggest_events: 'कौन-सी घटनाएँ सक्रिय हैं?',
	chat_suggest_units: 'यूनिट कहाँ हैं?',
	chat_cited: 'संदर्भ',
	chat_directives: 'मानचित्र पर प्रस्तावित',
	chat_open_city: 'सिटी कमांड में खोलें',

	pal_title: 'कमांड पैलेट',
	// FIX-E-LOOKUP: उदाहरण थर्मल-शैली दृश्य और उसके पैलेट का नाम बोलता है — कोई सेंसर नहीं
	pal_placeholder: 'fly to a plate or junction · show police units near Esplanade · layer cameras off · थर्मल-शैली दृश्य: आयरनबो · ask …',
	pal_hint: '⌘K / Ctrl+K · ↑↓ चुनें · Enter चलाएँ · Esc बंद करें',
	pal_fly: 'यहाँ जाएँ',
	pal_units: 'यूनिट दिखाएँ',
	pal_layer: 'परत',
	pal_sensor: 'थर्मल-शैली दृश्य',
	pal_ask: 'एजेंट से पूछें',
	pal_no_match: 'कोई वाहन, जंक्शन, सड़क या इकाई मेल नहीं खाती',
	pal_vehicles_only: 'केवल वाहन (ANPR नंबर प्लेट) — किसी व्यक्ति की खोज नहीं होती',
	pal_sent: 'एजेंट को भेजा — उसके सुझाव इसी कैनवास पर आएँगे',
	pal_units_near: (n, road) => `${road} के पास ${n} यूनिट`,
	pal_none_near: (road) => `अभी ${road} के पास कोई यूनिट नहीं`,
	pal_unknown_road: 'नेटवर्क पर इस नाम की कोई सड़क नहीं',

	dossier_explain: 'इसे समझाएँ',
	dossier_explaining: 'समझा रहा है…',
	dossier_explain_cancel: 'रद्द करें',
	dossier_explain_masked: 'प्लेट छिपी हैं — नामित ड्यूटी अधिकारी उन्हें देखते हैं',
	dossier_explain_failed: 'एजेंट ने उत्तर नहीं दिया',
	dossier_explain_by: 'एजेंट का उत्तर',
	dossier_test: 'परीक्षण',
	dossier_session_officer: 'साइन-इन ड्यूटी अधिकारी',

	canvas_live_paused: 'लाइव रुका',
	canvas_live_paused_hint: 'रीप्ले कैनवास पर है — LIVE पर लाइव परतें फिर चलेंगी',
	canvas_ama_title:
		'सक्रिय मूवमेंट अनुकूलन — स्थिति → हिस्टेरिसिस → नीति सीमाएँ → ट्विन शैडो-जाँच (फ़ेल-क्लोज़्ड) → ऑडिटेड भंडारण। आयु = बैंड की सबसे नई रीडिंग के बाद का समय (घटना की ताज़ा स्थिति रीडिंग, या शहर बैंड का ताज़ा इंजन मूल्यांकन) — बैंड कितनी देर से टिका है, वह नहीं। STALE = 10 मिनट से कोई नई रीडिंग नहीं।',
};

const bn: Pack = {
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

registerPack('en', en);

/** The EN, HI and BN packs (tests assert en/hi/bn parity); HI and BN land through adopt(). */
export const AGENT_PACKS: Record<string, Pack> = { en };

/**
 * Register one language chunk (lib/i18n/load.ts's landing site; additive,
 * first registration wins — the core's documented semantics).
 */
export function adopt(code: 'hi' | 'bn', pack: Pack): void {
	AGENT_PACKS[code] = pack;
	registerPack(code, pack);
}

/*
 * Language chunks (FIX-E-PERF2): the HI and BN strings that RUN live ONLY in
 * ./packs.agent.hi.ts and ./packs.agent.bn.ts. The server render and every non-production
 * run (vite dev, the node test harness) register both before this module
 * finishes evaluating (SSR paints the persisted language). The production
 * browser registers the loader instead and awaits the document's language
 * before this module finishes evaluating — hydration waits for it, so a cold
 * HI/BN load never flashes English — and the other language loads on the
 * first switch (lib/i18n/load.ts). The prod client build folds the condition
 * to its else branch.
 */
if (process.env.NODE_ENV !== 'production' || import.meta.env.SSR !== false) {
	adopt('hi', (await import('./packs.agent.hi')).hi);
	adopt('bn', (await import('./packs.agent.bn')).bn);
} else {
	await langChunks('packs.agent', (code) =>
		code === 'hi' ? import('./packs.agent.hi').then((c) => adopt('hi', c.hi)) : import('./packs.agent.bn').then((c) => adopt('bn', c.bn)),
	);
}

/*
 * TEXT MIRROR — not a source, never registered, never shipped. The `hi` and
 * `bn` literals above are a byte-identical copy of ./packs.agent.hi.ts and
 * ./packs.agent.bn.ts kept ONLY because two tests outside this work package
 * (tests/thermal-toolbar.unit.mjs, tests/omnibar-lookup.unit.mjs) read the
 * HI/BN strings as TypeScript AST off `registerPack('hi'|'bn', …)` calls in
 * THIS file. This function is never called (every bundle drops it and the
 * literals with it); tests/perf2.unit.mjs pins this copy and the shipped
 * copy, each on its own, to the reviewed golden, so the two can never drift.
 * Delete it once those tests read the per-language modules (FIX-E-PERF2
 * report, blocked request).
 */
function astTextMirror(): void {
	registerPack('hi', hi);
	registerPack('bn', bn);
}

/** Every key this pack defines (tests assert en/hi/bn parity). */
export const AGENT_PACK_KEYS: readonly string[] = Object.keys(en);
