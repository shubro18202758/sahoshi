/**
 * Map chrome string pack (EN / HI / BN) — the canvas's toolbar, navigation,
 * readout, LayerTree, legend, map proposals and replay banner (SPEC §5.3,
 * chrome="v2"), plus the honest imagery chip's words (`ge_imagery_*`, moved
 * here from gods-eye/layers/basemap.ts and converted to sentence case with
 * their test, basemap.unit.mjs).
 *
 * Every new key starts with `map_`. EN is sentence case, no ALL-CAPS word
 * outside the acronym allowlist, at most one " · " per string, titles at
 * most 32 characters (tests/copy-lint.mjs; targets file
 * style-lint.targets/s3.json). Operational names stay Latin in every
 * language (OSM, Google, ion, 3D), like the deck's other codes. Registered
 * additively through registerPack(); the core packs stay untouched.
 *
 * Copy describes only what the system does (SPEC §9.1): FLIR is a
 * thermal-STYLE rendering of the visible scene, no thermal sensor exists;
 * a map proposal moves nothing until a person applies it.
 */
import { registerPack } from './strings';
import { langChunks } from './load';

type Fn = (...args: unknown[]) => string;
type MapPack = Record<string, string | Fn>;

const en = {
	// honest imagery chip (legacy chrome) and the base-map note (v2)
	ge_imagery_photoreal: 'Photoreal 3D · Google',
	ge_imagery_photoreal_loading: 'Photoreal 3D · loading',
	ge_imagery_ion: 'Ion aerial · 3D terrain',
	ge_imagery_osm: 'OSM · dark',
	ge_imagery_osm_fallback: 'OSM dark (fallback)',
	ge_imagery_offline: 'Offline schematic mode',

	// toolbar
	map_toolbar: 'Map tools',
	map_tool_select: 'Select',
	map_tool_shape: 'Select within a shape',
	map_tool_shape_menu: 'Shape options',
	map_tool_shape_select: 'Select within shape',
	map_tool_shape_filter: 'Filter to shape',
	map_tool_shape_clear: 'Clear the shape filter',
	map_tool_shape_hint: 'Click points on the map, then double-click to close the shape',
	map_tool_search_around: 'Search around the selection',
	map_tool_search_around_none: 'Select an object first',
	map_tool_measure: 'Measure distance',
	map_tool_measure_hint: 'Click points on the map; double-click or Esc to finish',
	map_tool_layers: 'Layers',
	map_tool_legend: 'Legend',
	map_tool_follow: 'Follow the selection',
	map_tool_follow_none: 'Select something to follow',
	map_tool_following: (name) => (name != null && name !== '' ? `Following ${String(name)}` : 'Following the selection'),
	map_follow_no_position: (name) =>
		name != null && name !== '' ? `${String(name)} has no position on the map to follow` : 'The selection has no position on the map to follow',
	map_tool_tour: 'Guided tour',
	map_tool_tour_stop: 'Stop the guided tour',
	map_tool_exit: 'Exit map mode',
	map_mode_live: 'Live',
	map_mode_window: 'Not live',
	map_mode_replay: (run) => (run != null ? `Replay · run ${String(run)}` : 'Replay'),
	map_mode_live_tip: 'Live. Open the timeline to set a window or play a replay.',
	map_mode_window_tip: 'A time window is set. Open the timeline to return to live.',
	map_mode_replay_tip: 'A recorded tape is playing on its own time axis.',

	// the thermal-STYLE view: a toolbar button of its own (SPEC §16.5,
	// confirmed the other way 2026-10-25 — one click away, never a sensor)
	map_tool_thermal: 'Thermal-style view',
	map_tool_thermal_tip: 'Thermal-style view — a visual filter, no thermal sensor',
	map_thermal_on: 'Thermal-style view (visual filter)',
	map_flir_note: 'Visual filter, no thermal sensor',
	map_flir_off: 'Normal colours',
	map_flir_whot: 'Thermal style, white hot',
	map_flir_bhot: 'Thermal style, black hot',
	map_flir_iron: 'Thermal style, ironbow',
	// FIX-E-LOOKUP: the palettes in words (the omnibar's sensor command names
	// the picked palette through these — never the raw flir-* id)
	map_pal_raw: 'normal colours',
	map_pal_whot: 'white hot',
	map_pal_bhot: 'black hot',
	map_pal_iron: 'ironbow',

	// navigation and readout
	map_zoom_in: 'Zoom in',
	map_zoom_out: 'Zoom out',
	map_reset_north: 'Reset north',
	map_rule_note: 'Vehicles only · penalties need a named officer',
	map_rule_note_short: 'Vehicles only',
	map_imagery_not_live: 'not a live image',
	map_scale: 'Scale',
	map_cursor: 'Position',

	// LayerTree
	map_layers_title: 'Layers',
	map_basemap_title: 'Base map',
	map_basemap_photoreal: 'Photoreal',
	map_basemap_streets: 'Streets',
	map_basemap_dark: 'Dark',
	map_basemap_needs_key: 'Needs the Cesium ion key on this deck',
	map_group_traffic: 'Traffic',
	map_group_enforcement: 'Enforcement',
	map_group_response: 'Response',
	map_group_corridors: 'Corridors',
	map_group_intelligence: 'Reported events',
	map_layer_flow: 'Traffic flow',
	map_layer_signals: 'Junctions and signals',
	map_layer_anomalies: 'Feed anomalies',
	map_layer_traces: 'Watchlisted vehicles',
	map_layer_enforcement: 'Decisions waiting',
	map_layer_cameras: 'ANPR cameras',
	map_layer_units: 'Units',
	map_layer_dispatch: 'Dispatches',
	map_layer_events: 'Events and routes',
	map_layer_convoy: 'Convoy',
	map_layer_photoreal: 'Photoreal 3D city',
	map_layer_paused: 'Paused while the replay plays',
	map_layer_feed_down: 'Feed problem',

	// legend
	map_legend_title: 'Legend',
	map_legend_flow: 'Traffic flow: free → jammed',
	map_legend_flow_simulated: 'Traffic flow (simulated): free → jammed',
	map_legend_markers: 'Markers',
	map_legend_alert: 'Watchlisted vehicle and its reads',
	map_legend_decision: 'A decision is waiting',
	map_legend_selected: 'Selected',
	map_legend_neutral: 'Other objects: type by glyph',
	map_legend_cluster: 'Co-located markers',
	map_legend_route: 'Convoy and its route',
	map_legend_event: 'Corridor events',
	map_legend_close: 'Close the legend',

	// clusters and labels
	map_cluster_list: (n) => `${String(n)} objects here`,
	map_cluster_spread: 'Click to spread them out',

	// map proposals (the home of map proposals, SPEC §5.4)
	map_proposal_head: (label) => `Proposed on the map · ${String(label)}`,
	map_proposal_tier: (tier) => `${String(tier)} tier`,
	map_proposal_note: 'Nothing moves until you apply it',

	// replay banner (SPEC §7.3, §9: a replay names its provenance — an
	// emulator tape is an emulated recording; a live capture is never so
	// labelled)
	map_replay_banner: (run) => (run != null ? `Replay · run ${String(run)}` : 'Replay'),
	map_replay_emulated: 'Emulated',
	map_live_paused: 'live layers paused',
	map_live_paused_hint: 'The live layers stand down while the tape plays. The inbox and the live strip stay live.',

	// shape and measure results
	map_measure_total: (km) => `Distance ${String(km)}`,
	map_shape_selected: (n) => `${String(n)} selected in the shape`,
	map_shape_filtered: (n) => `${String(n)} shown inside the shape`,
} satisfies MapPack;

export type MapKey = keyof typeof en;

const hi: Record<MapKey, string | Fn> = {
	ge_imagery_photoreal: 'यथार्थ 3D शहर · Google',
	ge_imagery_photoreal_loading: 'यथार्थ 3D · लोड हो रहा है',
	ge_imagery_ion: 'ion हवाई चित्र · 3D भू-भाग',
	ge_imagery_osm: 'OSM · डार्क',
	ge_imagery_osm_fallback: 'OSM डार्क (वैकल्पिक)',
	ge_imagery_offline: 'ऑफ़लाइन योजनाबद्ध मोड',

	map_toolbar: 'मानचित्र उपकरण',
	map_tool_select: 'चुनें',
	map_tool_shape: 'आकृति के भीतर चुनें',
	map_tool_shape_menu: 'आकृति विकल्प',
	map_tool_shape_select: 'आकृति के भीतर चुनें',
	map_tool_shape_filter: 'आकृति तक सीमित करें',
	map_tool_shape_clear: 'आकृति फ़िल्टर हटाएँ',
	map_tool_shape_hint: 'मानचित्र पर बिंदु चुनें, फिर आकृति बंद करने के लिए डबल-क्लिक करें',
	map_tool_search_around: 'चयन के आसपास खोजें',
	map_tool_search_around_none: 'पहले कोई वस्तु चुनें',
	map_tool_measure: 'दूरी मापें',
	map_tool_measure_hint: 'मानचित्र पर बिंदु चुनें; समाप्त करने के लिए डबल-क्लिक या Esc',
	map_tool_layers: 'परतें',
	map_tool_legend: 'संकेत-सूची',
	map_tool_follow: 'चयन का अनुसरण करें',
	map_tool_follow_none: 'अनुसरण के लिए कुछ चुनें',
	map_tool_following: (name) => (name != null && name !== '' ? `${String(name)} का अनुसरण` : 'चयन का अनुसरण'),
	map_follow_no_position: (name) =>
		name != null && name !== ''
			? `${String(name)} की मानचित्र पर कोई स्थिति नहीं है, अनुसरण संभव नहीं`
			: 'चयन की मानचित्र पर कोई स्थिति नहीं है, अनुसरण संभव नहीं',
	map_tool_tour: 'निर्देशित भ्रमण',
	map_tool_tour_stop: 'निर्देशित भ्रमण रोकें',
	map_tool_exit: 'मानचित्र मोड से बाहर',
	map_mode_live: 'लाइव',
	map_mode_window: 'लाइव नहीं',
	map_mode_replay: (run) => (run != null ? `रीप्ले · रन ${String(run)}` : 'रीप्ले'),
	map_mode_live_tip: 'लाइव। समय-सीमा या रीप्ले के लिए टाइमलाइन खोलें।',
	map_mode_window_tip: 'समय-सीमा लगी है। लाइव पर लौटने के लिए टाइमलाइन खोलें।',
	map_mode_replay_tip: 'एक रिकॉर्ड की गई टेप अपनी समय-अक्ष पर चल रही है।',

	// FIX-E-LOOKUP: "दृश्य … (दृश्य फ़िल्टर)" नहीं — दृश्य शब्द एक बार; फ़िल्टर विज़ुअल फ़िल्टर
	map_tool_thermal: 'थर्मल-शैली दृश्य',
	map_tool_thermal_tip: 'थर्मल-शैली दृश्य — केवल एक विज़ुअल फ़िल्टर, कोई थर्मल सेंसर नहीं',
	map_thermal_on: 'थर्मल-शैली दृश्य (विज़ुअल फ़िल्टर)',
	map_flir_note: 'विज़ुअल फ़िल्टर, कोई थर्मल सेंसर नहीं',
	map_flir_off: 'सामान्य रंग',
	map_flir_whot: 'थर्मल शैली, सफ़ेद गर्म',
	map_flir_bhot: 'थर्मल शैली, काला गर्म',
	map_flir_iron: 'थर्मल शैली, आयरनबो',
	map_pal_raw: 'सामान्य रंग',
	map_pal_whot: 'सफ़ेद गर्म',
	map_pal_bhot: 'काला गर्म',
	map_pal_iron: 'आयरनबो',

	map_zoom_in: 'ज़ूम इन',
	map_zoom_out: 'ज़ूम आउट',
	map_reset_north: 'उत्तर दिशा पर लौटें',
	map_rule_note: 'केवल वाहन · दंड के लिए नामित अधिकारी आवश्यक',
	map_rule_note_short: 'केवल वाहन',
	map_imagery_not_live: 'लाइव तस्वीर नहीं',
	map_scale: 'पैमाना',
	map_cursor: 'स्थिति',

	map_layers_title: 'परतें',
	map_basemap_title: 'आधार मानचित्र',
	map_basemap_photoreal: 'यथार्थ',
	map_basemap_streets: 'सड़कें',
	map_basemap_dark: 'डार्क',
	map_basemap_needs_key: 'इस डेक पर Cesium ion कुंजी आवश्यक है',
	map_group_traffic: 'यातायात',
	map_group_enforcement: 'प्रवर्तन',
	map_group_response: 'प्रतिक्रिया',
	map_group_corridors: 'कॉरिडोर',
	map_group_intelligence: 'रिपोर्ट की गई घटनाएँ',
	map_layer_flow: 'यातायात प्रवाह',
	map_layer_signals: 'जंक्शन और सिग्नल',
	map_layer_anomalies: 'फ़ीड विसंगतियाँ',
	map_layer_traces: 'निगरानी सूची के वाहन',
	map_layer_enforcement: 'निर्णय प्रतीक्षित',
	map_layer_cameras: 'ANPR कैमरे',
	map_layer_units: 'इकाइयाँ',
	map_layer_dispatch: 'प्रेषण',
	map_layer_events: 'घटनाएँ और मार्ग',
	map_layer_convoy: 'काफ़िला',
	map_layer_photoreal: 'यथार्थ 3D शहर',
	map_layer_paused: 'रीप्ले चलते समय रुका हुआ',
	map_layer_feed_down: 'फ़ीड में समस्या',

	map_legend_title: 'संकेत-सूची',
	map_legend_flow: 'यातायात प्रवाह: मुक्त → जाम',
	map_legend_flow_simulated: 'यातायात प्रवाह (सिम्युलेटेड): मुक्त → जाम',
	map_legend_markers: 'चिह्न',
	map_legend_alert: 'निगरानी सूची का वाहन और उसकी रीडिंग',
	map_legend_decision: 'एक निर्णय प्रतीक्षित है',
	map_legend_selected: 'चयनित',
	map_legend_neutral: 'अन्य वस्तुएँ: प्रकार चिह्न से',
	map_legend_cluster: 'एक ही स्थान के चिह्न',
	map_legend_route: 'काफ़िला और उसका मार्ग',
	map_legend_event: 'कॉरिडोर घटनाएँ',
	map_legend_close: 'संकेत-सूची बंद करें',

	map_cluster_list: (n) => `यहाँ ${String(n)} वस्तुएँ`,
	map_cluster_spread: 'फैलाने के लिए क्लिक करें',

	map_proposal_head: (label) => `मानचित्र पर प्रस्ताव · ${String(label)}`,
	map_proposal_tier: (tier) => `${String(tier)} स्तर`,
	map_proposal_note: 'लागू करने तक कुछ नहीं बदलता',

	map_replay_banner: (run) => (run != null ? `रीप्ले · रन ${String(run)}` : 'रीप्ले'),
	map_replay_emulated: 'इम्यूलेटेड',
	map_live_paused: 'लाइव परतें रुकी हुई',
	map_live_paused_hint: 'टेप चलते समय लाइव परतें रुकती हैं। इनबॉक्स और लाइव पट्टी लाइव रहती हैं।',

	map_measure_total: (km) => `दूरी ${String(km)}`,
	map_shape_selected: (n) => `आकृति में ${String(n)} चयनित`,
	map_shape_filtered: (n) => `आकृति के भीतर ${String(n)} दिखाए गए`,
};

const bn: Record<MapKey, string | Fn> = {
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

registerPack('en', en);

/**
 * Register one language chunk (lib/i18n/load.ts's landing site; additive,
 * first registration wins — the core's documented semantics).
 */
export function adopt(code: 'hi' | 'bn', pack: Record<string, string | Fn>): void {
	registerPack(code, pack);
}

/*
 * Language chunks (FIX-E-PERF2): the HI and BN strings that RUN live ONLY in
 * ./packs.map.hi.ts and ./packs.map.bn.ts. The server render and every non-production
 * run (vite dev, the node test harness) register both before this module
 * finishes evaluating (SSR paints the persisted language). The production
 * browser registers the loader instead and awaits the document's language
 * before this module finishes evaluating — hydration waits for it, so a cold
 * HI/BN load never flashes English — and the other language loads on the
 * first switch (lib/i18n/load.ts). The prod client build folds the condition
 * to its else branch.
 */
if (process.env.NODE_ENV !== 'production' || import.meta.env.SSR !== false) {
	adopt('hi', (await import('./packs.map.hi')).hi);
	adopt('bn', (await import('./packs.map.bn')).bn);
} else {
	await langChunks('packs.map', (code) =>
		code === 'hi' ? import('./packs.map.hi').then((c) => adopt('hi', c.hi)) : import('./packs.map.bn').then((c) => adopt('bn', c.bn)),
	);
}

/*
 * TEXT MIRROR — not a source, never registered, never shipped. The `hi` and
 * `bn` literals above are a byte-identical copy of ./packs.map.hi.ts and
 * ./packs.map.bn.ts kept ONLY because two tests outside this work package
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

/** Every key of the pack (tests check HI and BN cover each one). */
export const MAP_PACK_KEYS: readonly MapKey[] = Object.keys(en) as MapKey[];
