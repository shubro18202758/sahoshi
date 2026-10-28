/**
 * packs.map — the BN strings (FIX-E-PERF2): the ONE copy that runs. The
 * server render, vite dev and the node tests import it from ./packs.map.ts; the
 * production browser fetches it as its own chunk (lib/i18n/load.ts). Values
 * are byte-identical to the pre-split module (tests/perf2.unit.mjs pins the
 * key count and a content hash per module and language).
 * ./packs.map.ts keeps a never-registered text mirror of this block for
 * two AST-reading tests; tests/perf2.unit.mjs pins both copies.
 */

import type { MapKey } from './packs.map';
type Fn = (...args: unknown[]) => string;
type Pack = Record<string, string | ((...args: unknown[]) => string)>;

export const bn: Record<MapKey, string | Fn> = {
	ge_imagery_photoreal: 'বাস্তবধর্মী 3D · Google',
	ge_imagery_photoreal_loading: 'বাস্তবধর্মী 3D · লোড হচ্ছে',
	ge_imagery_ion: 'ion আকাশচিত্র · 3D ভূখণ্ড',
	ge_imagery_osm: 'OSM · ডার্ক',
	ge_imagery_osm_fallback: 'OSM ডার্ক (বিকল্প)',
	ge_imagery_offline: 'অফলাইন রেখাচিত্র মোড',

	map_toolbar: 'মানচিত্রের টুল',
	map_tool_select: 'বেছে নিন',
	map_tool_shape: 'আকৃতির ভেতরে বেছে নিন',
	map_tool_shape_menu: 'আকৃতির বিকল্প',
	map_tool_shape_select: 'আকৃতির ভেতরে বেছে নিন',
	map_tool_shape_filter: 'আকৃতি দিয়ে ফিল্টার করুন',
	map_tool_shape_clear: 'আকৃতির ফিল্টার সরিয়ে দিন',
	map_tool_shape_hint: 'মানচিত্রে বিন্দুগুলোয় ক্লিক করুন, তারপর আকৃতি বন্ধ করতে ডাবল-ক্লিক করুন',
	map_tool_search_around: 'বেছে নেওয়া জিনিসের আশপাশে খুঁজুন',
	map_tool_search_around_none: 'আগে একটি জিনিস বেছে নিন',
	map_tool_measure: 'দূরত্ব মাপুন',
	map_tool_measure_hint: 'মানচিত্রে বিন্দুগুলোয় ক্লিক করুন; শেষ করতে ডাবল-ক্লিক বা Esc',
	map_tool_layers: 'স্তর',
	map_tool_legend: 'চিহ্ন-পরিচিতি',
	map_tool_follow: 'বেছে নেওয়া জিনিস অনুসরণ করুন',
	map_tool_follow_none: 'অনুসরণ করতে কিছু একটা বেছে নিন',
	map_tool_following: (name) => (name != null && name !== '' ? `অনুসরণ চলছে: ${String(name)}` : 'বেছে নেওয়া জিনিসের অনুসরণ চলছে'),
	map_follow_no_position: (name) =>
		name != null && name !== ''
			? `মানচিত্রে ${String(name)}-এর কোনো অবস্থান নেই, তাই অনুসরণ করা যাচ্ছে না`
			: 'মানচিত্রে বেছে নেওয়া জিনিসের কোনো অবস্থান নেই, তাই অনুসরণ করা যাচ্ছে না',
	map_tool_tour: 'গাইডেড ট্যুর',
	map_tool_tour_stop: 'গাইডেড ট্যুর থামান',
	map_tool_exit: 'মানচিত্র মোড থেকে বেরিয়ে যান',
	map_mode_live: 'লাইভ',
	map_mode_window: 'লাইভ নয়',
	map_mode_replay: (run) => (run != null ? `রিপ্লে · রান ${String(run)}` : 'রিপ্লে'),
	map_mode_live_tip: 'লাইভ চলছে। সময়সীমা বেছে নিতে বা রিপ্লে চালাতে টাইমলাইন খুলুন।',
	map_mode_window_tip: 'একটি সময়সীমা বেছে নেওয়া আছে। লাইভে ফিরতে টাইমলাইন খুলুন।',
	map_mode_replay_tip: 'রেকর্ড করা একটি টেপ নিজের সময়-অক্ষে চলছে।',

	// FIX-E-LOOKUP: the view word (দৃশ্য) appears once per string; the filter is a ভিজ্যুয়াল ফিল্টার
	map_tool_thermal: 'থার্মাল-ধাঁচের দৃশ্য',
	map_tool_thermal_tip: 'থার্মাল-ধাঁচের দৃশ্য — শুধু একটি ভিজ্যুয়াল ফিল্টার, কোনো থার্মাল সেন্সর নেই',
	map_thermal_on: 'থার্মাল-ধাঁচের দৃশ্য (ভিজ্যুয়াল ফিল্টার)',
	map_flir_note: 'ভিজ্যুয়াল ফিল্টার, কোনো থার্মাল সেন্সর নেই',
	map_flir_off: 'স্বাভাবিক রং',
	map_flir_whot: 'থার্মাল ধাঁচ, সাদা গরম',
	map_flir_bhot: 'থার্মাল ধাঁচ, কালো গরম',
	map_flir_iron: 'থার্মাল ধাঁচ, আয়রনবো',
	map_pal_raw: 'স্বাভাবিক রং',
	map_pal_whot: 'সাদা গরম',
	map_pal_bhot: 'কালো গরম',
	map_pal_iron: 'আয়রনবো',

	map_zoom_in: 'জুম ইন',
	map_zoom_out: 'জুম আউট',
	map_reset_north: 'আবার উত্তরমুখী করুন',
	map_rule_note: 'শুধু গাড়ি · জরিমানার জন্য নাম-নথিভুক্ত অফিসার লাগে',
	map_rule_note_short: 'শুধু গাড়ি',
	map_imagery_not_live: 'লাইভ ছবি নয়',
	map_scale: 'স্কেল',
	map_cursor: 'অবস্থান',

	map_layers_title: 'স্তর',
	map_basemap_title: 'মূল মানচিত্র',
	map_basemap_photoreal: 'বাস্তবধর্মী',
	map_basemap_streets: 'রাস্তা',
	map_basemap_dark: 'ডার্ক',
	map_basemap_needs_key: 'এর জন্য এই ডেকে Cesium ion অ্যাক্সেস কী লাগবে',
	map_group_traffic: 'ট্রাফিক',
	map_group_enforcement: 'আইন প্রয়োগ',
	map_group_response: 'জরুরি সাড়া',
	map_group_corridors: 'করিডর',
	map_group_intelligence: 'রিপোর্ট হওয়া ঘটনা',
	map_layer_flow: 'ট্রাফিক প্রবাহ',
	map_layer_signals: 'জংশন ও সিগন্যাল',
	map_layer_anomalies: 'ফিডের অসংগতি',
	map_layer_traces: 'নজরতালিকার গাড়ি',
	map_layer_enforcement: 'সিদ্ধান্তের অপেক্ষায়',
	map_layer_cameras: 'ANPR ক্যামেরা',
	map_layer_units: 'ইউনিট',
	map_layer_dispatch: 'ডিসপ্যাচ',
	map_layer_events: 'ঘটনা ও পথ',
	map_layer_convoy: 'কনভয়',
	map_layer_photoreal: 'বাস্তবধর্মী 3D শহর',
	map_layer_paused: 'রিপ্লে চলার সময় থামানো',
	map_layer_feed_down: 'ফিডে সমস্যা',

	map_legend_title: 'চিহ্ন-পরিচিতি',
	map_legend_flow: 'ট্রাফিক প্রবাহ: ফাঁকা → জ্যাম',
	map_legend_flow_simulated: 'ট্রাফিক প্রবাহ (সিমুলেটেড): ফাঁকা → জ্যাম',
	map_legend_markers: 'মার্কার',
	map_legend_alert: 'নজরতালিকার গাড়ি ও তার রিডিং',
	map_legend_decision: 'একটি সিদ্ধান্ত অপেক্ষমাণ',
	map_legend_selected: 'বেছে নেওয়া',
	map_legend_neutral: 'অন্যান্য জিনিস: চিহ্ন দেখে ধরন বুঝুন',
	map_legend_cluster: 'একই জায়গার মার্কার',
	map_legend_route: 'কনভয় ও তার পথ',
	map_legend_event: 'করিডরের ঘটনা',
	map_legend_close: 'চিহ্ন-পরিচিতি বন্ধ করুন',

	map_cluster_list: (n) => `এখানে ${String(n)}টি জিনিস`,
	map_cluster_spread: 'ছড়িয়ে দেখতে ক্লিক করুন',

	map_proposal_head: (label) => `মানচিত্রে প্রস্তাব · ${String(label)}`,
	map_proposal_tier: (tier) => `${String(tier)} পর্যায়`,
	map_proposal_note: 'আপনি প্রয়োগ না করা পর্যন্ত কিছুই বদলাবে না',

	map_replay_banner: (run) => (run != null ? `রিপ্লে · রান ${String(run)}` : 'রিপ্লে'),
	map_replay_emulated: 'এমুলেটেড',
	map_live_paused: 'লাইভ স্তর থামানো আছে',
	map_live_paused_hint: 'টেপ চলার সময় লাইভ স্তরগুলো থেমে থাকে। ইনবক্স আর লাইভ স্ট্রিপ লাইভই থাকে।',

	map_measure_total: (km) => `দূরত্ব ${String(km)}`,
	map_shape_selected: (n) => `আকৃতির ভেতরে ${String(n)}টি বেছে নেওয়া হয়েছে`,
	map_shape_filtered: (n) => `আকৃতির ভেতরে ${String(n)}টি দেখানো হচ্ছে`,
};
