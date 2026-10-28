/**
 * packs.corridor — the BN strings (FIX-E-PERF2): the ONE copy that runs. The
 * server render, vite dev and the node tests import it from ./packs.corridor.ts; the
 * production browser fetches it as its own chunk (lib/i18n/load.ts). Values
 * are byte-identical to the pre-split module (tests/perf2.unit.mjs pins the
 * key count and a content hash per module and language).
 */

type Pack = Record<string, string | ((...args: unknown[]) => string)>;

const s = (v: unknown) => String(v ?? '');
const n = (v: unknown) => Number(v);
export const bn: Pack = {
	cor_tab_plan: 'পরিকল্পনা',
	cor_tab_layers: 'স্তর',
	cor_tab_movement: 'যাত্রা',

	cor_plan_section: 'করিডরের পরিকল্পনা',
	cor_plan_from: 'কোথা থেকে',
	cor_plan_to: 'কোথায়',
	cor_plan_class: 'শ্রেণি',
	cor_plan_departure: 'রওনা (IST)',
	cor_plan_label: 'লেবেল',
	cor_label_placeholder: 'যেমন দুর্গাপুজোর পথের মহড়া',
	cor_plan_label_hint: 'টেস্ট বা মহড়ার লেবেল যাত্রার শিরোনাম হিসেবে থাকে — এমন যাত্রাকে কখনও আসল যাত্রা হিসেবে দেখানো হয় না',
	cor_plan_officer: 'ডিউটি অফিসার',
	cor_plan_btn: 'করিডর পরিকল্পনা করুন',
	cor_plan_btn_busy: 'পরিকল্পনা হচ্ছে…',
	cor_plan_none: 'এখনও কোনো পরিকল্পনা নেই — শুরুর জায়গা ও গন্তব্য বেছে নিয়ে পরিকল্পনা করুন।',

	cor_status_approved: 'নিরাপত্তার শর্ত পূরণ',
	cor_status_conditional: 'শর্তসাপেক্ষ',
	cor_status_hold: 'হোল্ড',
	cor_status_no_route: 'কোনো পথ নেই',
	cor_status_unknown: 'পরিকল্পিত',

	cor_waiver: 'এই পরিকল্পনার তালিকাভুক্ত ন্যূনতম লেনের লঙ্ঘনগুলি আমি মেনে নিচ্ছি',
	cor_waiver_stamped: (who: unknown) => `${s(who)} ন্যূনতম লেনের লঙ্ঘনগুলি মেনে নিয়েছেন`,

	cor_hold_replan: (at: unknown) => `${s(at)}-এর পরে আবার পরিকল্পনা করুন`,
	cor_hold_note: 'ডিসাইডার রওনা পিছিয়ে দিয়েছে। এই পরিকল্পনা শুরু করা যাবে না।',

	cor_no_route_note: 'এই দুই জায়গা আর এই শ্রেণির জন্য প্ল্যানার কোনো পথ পায়নি।',
	cor_no_route_next: 'এরপর: অন্য শুরুর জায়গা বা গন্তব্য, কিংবা নিচের সুরক্ষা শ্রেণি বেছে নিয়ে আবার পরিকল্পনা করুন।',

	cor_launch: 'এসকর্ট শুরু করুন',
	cor_launch_starting: 'শুরু হচ্ছে…',
	cor_launch_criteria: (cls: unknown, dest: unknown) => `নাম-নথিভুক্ত ডিউটি অফিসারের দায়িত্বে ${s(cls)} শ্রেণির যাত্রাকে ${s(dest)} পর্যন্ত এসকর্ট করে`,
	cor_launch_locked_waiver: 'আগে ন্যূনতম লেনের লঙ্ঘনগুলি মেনে নিন — পরিকল্পনাটি শর্তসাপেক্ষ।',
	cor_launch_locked_hold: 'ডিসাইডার এই পরিকল্পনা হোল্ডে রেখেছে — পরের কোনো সময়ে রওনার জন্য আবার পরিকল্পনা করুন।',
	cor_launch_locked_officer: 'শুরু করতে ডিউটি অফিসারের নাম দিন।',
	cor_launch_locked_no_plan: 'আগে করিডরের পরিকল্পনা করুন।',
	cor_stop: 'এসকর্ট থামান',
	cor_stopping: 'থামানো হচ্ছে…',
	cor_clear: 'ক্লিয়ার করুন',
	cor_clearing: 'ক্লিয়ার করা হচ্ছে…',
	cor_clear_hint: 'ক্লিয়ারের পরে সব আগের মতো: বন্ধ রাস্তা খোলা, সিগন্যাল প্রোগ্রাম ফেরানো, করিডর ঘটনা বন্ধ',

	cor_cand_primary: 'প্রধান',
	cor_cand_alternate: (k: unknown) => `বিকল্প ${s(k)}`,
	cor_cand_adds: (roads: unknown) => `${s(roads)} যোগ করে`,
	cor_cand_compliant: 'ন্যূনতম লেনের শর্ত পূরণ করে',
	cor_cand_violations: (c: unknown) => `ন্যূনতম লেনের ${n(c)}টি লঙ্ঘন`,
	cor_cand_ai_pick: (conf: unknown) => `সাহসী এআই-এর পছন্দ · নিশ্চয়তা ${s(conf)}`,
	cor_cand_tactical_pick: 'কৌশলগত প্রধান',
	cor_cand_rejected: (c: unknown) => `বাতিল পথ (${n(c)})`,
	cor_cand_adds_none: 'নতুন কোনো রাস্তা যোগ করে না',
	cor_cand_roads: (c: unknown) => `${n(c)}টি রাস্তা`,

	cor_proposal_link: (title: unknown) => `এসকর্ট প্রস্তাব অপেক্ষায়: ${s(title)}`,
	cor_proposal_open: 'যাত্রা ট্যাবে সিদ্ধান্ত নিন',

	cor_hud_escort_live: 'এসকর্ট চলছে',
	cor_hud_planned: 'এসকর্টের পরিকল্পনা হয়েছে',
	cor_hud_completed: 'এসকর্ট সম্পূর্ণ',
	cor_hud_stopped: 'এসকর্ট থামানো হয়েছে',
	cor_hud_failed: 'এসকর্ট ব্যর্থ',
	cor_hud_speed: 'গতি',
	cor_hud_speed_corridor: 'করিডরের গড়',
	cor_hud_progress: 'অগ্রগতি',
	cor_hud_eta: 'ETA',
	cor_hud_eta_planned: 'পরিকল্পিত',
	cor_hud_hold: 'হোল্ড',
	cor_hud_hold_none: 'নেই',
	cor_hud_hold_yes: 'হোল্ড চলছে',
	cor_hud_next_junction: (name: unknown, t: unknown) => `পরের জংশন ${s(name)} · ${s(t)} পরে`,
	cor_hud_awaiting_gps: 'GPS সিগন্যালের অপেক্ষায়',
	cor_hud_destination: 'গন্তব্য',
	cor_hud_min: (m: unknown) => `${n(m)} মিনিট`,
	cor_hud_sec: (v: unknown) => `${n(v)} সেকেন্ড`,
	cor_hud_legacy_brain: 'এই ব্রেন এসকর্ট নিয়ন্ত্রণ আসার আগের সংস্করণ — এটি নিজের লুপ একটানা চালিয়ে সঙ্গে সঙ্গে শেষ করেছে।',
	cor_hud_officer_note: 'ডিউটি অফিসারের নামেই এসকর্টের সিদ্ধান্ত হয়; এআই কখনও নিজে থেকে কিছু প্রয়োগ করে না।',
	cor_hud_nofigures: 'এই কনসোলে কোনো লাইভ হিসাব নেই — যাত্রা ট্যাব খুলুন',

	cor_events_none: 'কোনো লাইভ করিডর ঘটনা নেই',
	cor_events_focus: 'মানচিত্রে দেখান',
	cor_events_focus_locked: 'লক করা',
	cor_events_focus_locating: 'খোঁজা হচ্ছে…',
	cor_events_no_spine: 'ক্যানভাসে কোনো পথরেখা নেই',
	cor_events_no_canvas: 'ক্যানভাস পাওয়া যাচ্ছে না',
	cor_events_test_tip: (label: unknown) => `লেবেল দেওয়া টেস্ট বা মহড়ার যাত্রা — আসল যাত্রা নয়: ${s(label)}`,
	cor_events_promoted: 'ওপেন-সোর্স রিপোর্ট থেকে ঘটনায় তোলা হয়েছে',
	cor_events_test: 'টেস্ট',

	cor_tab_failed: 'এই প্যানেল লোড করা যায়নি।'
};
