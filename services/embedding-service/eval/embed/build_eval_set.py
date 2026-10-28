"""Build the embedding eval set (SYNTHETIC) from the repo's own material.

Three of Sahoshi's real retrieval jobs, each in Bengali, English, Hindi and code-mixed (romanised Bengali) text:

* ``memory``  — decision memory: a new situation (a brain state document, or an officer's free text) → the past
  decisions / incidents / scenario runs / after-action notes about the same place and kind of situation. Documents
  use the exact shapes the brain (``convoy_brain.decider._record_decision_memory``: ``TRIGGER: …`` state docs) and
  the embedding service's ``IncidentIngestor`` (incident and scenario-run bodies) write.
* ``sop``     — SOP / advisory retrieval: a question → the paragraph that answers it. Corpus: every paragraph of 25+
  words in ``docs/ai/*.md``, the deck's citizen advisory packs (``strings.citizen{,.bn,.hi}.ts``, the same key in
  three languages) and advisory/proposal texts rendered from the hydro and forecast templates.
* ``osint``   — OSINT dedup/clustering: headlines (Bengali, English, Hindi, romanised) about the same Kolkata event
  must cluster; hard negatives share a place or an event kind. Plus one English cluster taken from the OSINT
  test fixtures (``services/osint-common/tests/fixtures/dss_sg_highway.synthetic.json``, synthetic, another city).

Everything here is SYNTHETIC: invented situations and headlines written for this eval, with real Kolkata place
names (``cities/kolkata/landmarks.json`` spellings). No real person is named; no real statistic is claimed.

Run: ``python build_eval_set.py`` (stdlib only) → ``eval_set.synthetic.json`` next to this file.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
OUT = HERE / "eval_set.synthetic.json"

# ─────────────────────────────────────────────────────────────────────────────
# (a) decision memory
# ─────────────────────────────────────────────────────────────────────────────


def _decision(fam: str, n: int, trigger: str, summary: str, **ctx: object) -> dict:
    """A kind=decision doc exactly as the brain's decision-memory feeder writes it."""
    lines = [f"TRIGGER: {trigger}", summary.strip()] + [f"{k}: {v}" for k, v in ctx.items()]
    return {"id": f"m:{fam}:d{n}", "family": fam, "kind": "decision",
            "title": f"decider {trigger} checkpoint", "body": "\n".join(lines)}


def _incident(fam: str, n: int, kind: str, severity: str, summary: str) -> dict:
    """A kind=incident doc as IncidentIngestor.ingest_live_incident writes it."""
    return {"id": f"m:{fam}:i{n}", "family": fam, "kind": "incident",
            "title": f"Incident {kind} ({severity})", "body": summary}


def _scenario(fam: str, n: int, sc: str, route: str, dvh: float, q: int, clo: int, segs: int, risk: float,
              transit: int) -> dict:
    """A kind=scenario_run doc as IncidentIngestor.ingest_scenario_run writes it."""
    body = (f"Simulation scenario run {sc} on route {route}. Predicted disruption {dvh} vehicle-hours; "
            f"max queue {q} m; average closure {clo} s; segments affected {segs}; complaints risk {risk}; "
            f"convoy transit {transit} s.")
    return {"id": f"m:{fam}:s{n}", "family": fam, "kind": "scenario_run",
            "title": f"Scenario run {sc}: {route}", "body": body}


def _aar(fam: str, n: int, title: str, body: str) -> dict:
    return {"id": f"m:{fam}:a{n}", "family": fam, "kind": "aar", "title": f"After-action: {title}", "body": body}


MEMORY_DOCS: list[dict] = [
    # F1 waterlogging at high tide, central (Thanthania / College Street / Chittaranjan Avenue)
    _decision("tide_central", 1, "waterlogging_alert",
              "Cloudburst over central Kolkata during a high tide on the Hooghly; outfall gates closed. Water rising "
              "at Thanthania and College Street; Chittaranjan Avenue northbound slowing.",
              rain_mm_last_hour=62, tide_m=5.3, gates="closed", risk_class=2,
              ambulance_route="Medical College via Bidhan Sarani"),
    _incident("tide_central", 2, "weather", "high",
              "Waterlogging 20-30 cm at Thanthania crossing and on Bidhan Sarani after heavy rain at high tide; "
              "small vehicles stalled; pumps at Thanthania working against closed outfall gates."),
    _aar("tide_central", 3, "Thanthania waterlogging at high tide",
         "Diversion of Bidhan Sarani traffic to APC Road held for 95 minutes until the tide fell and the gates "
         "reopened. Ambulances to Medical College used Chittaranjan Avenue southbound; one live-wire report was "
         "passed to the power utility."),
    # F2 Durga Puja crowd, north (Bagbazar / Shyambazar / Kumartuli)
    _decision("puja_north", 1, "crowd_density",
              "Saptami night: pandal-hopping crowd at Bagbazar Sarbojanin and Kumartuli Park spilling onto the road; "
              "Shyambazar five-point crossing gridlocked.",
              crowd_level="very high", pandals="Bagbazar, Kumartuli Park", one_way="BT Road southbound only",
              goods_vehicle_ban="active"),
    _scenario("puja_north", 2, "sc-puja-n-07", "Shyambazar - Bagbazar - Kumartuli (Puja night)",
              48.2, 1350, 420, 9, 0.62, 0),
    _aar("puja_north", 3, "Navami night north Kolkata",
         "Metering pedestrians at Bagbazar ghat road and holding vehicles at Shyambazar for 6-minute waves kept "
         "the crowd moving; a 108 ambulance reached RG Kar via a cleared lane on Bhupen Bose Avenue."),
    # F3 Howrah Bridge breakdown
    _incident("howrah_bridge", 1, "route_blockage", "high",
              "A WBTC bus broke down in the eastbound lane of Howrah Bridge at 18:10; queue back to Howrah Station; "
              "Brabourne Road approach slow."),
    _decision("howrah_bridge", 2, "route_blockage",
              "Stalled bus on Howrah Bridge eastbound during the evening peak; tow truck 20 minutes away. Spill-back "
              "onto the Howrah Station bus stand.",
              blocked_lane="eastbound kerb lane", alternate="Vidyasagar Setu", tow_eta_min=20),
    _aar("howrah_bridge", 3, "Howrah Bridge breakdown",
         "Diverting Kolkata-bound goods traffic to Vidyasagar Setu and opening the contraflow lane cleared the "
         "Howrah Bridge queue in 40 minutes after the bus was towed."),
    # F4 VIP movement Nabanna -> airport
    _decision("vip_nabanna", 1, "pre_movement",
              "Protected movement planned from Nabanna to Kolkata Airport at 16:30 via Vidyasagar Setu, AJC Bose "
              "Road flyover, EM Bypass and VIP Road.",
              route_options="primary: Setu-AJC-Bypass-VIP Road; alternate: Howrah Bridge-Central Avenue-VIP Road",
              expected_hold_min=12),
    _scenario("vip_nabanna", 2, "sc-vip-nab-03", "Nabanna - Vidyasagar Setu - EM Bypass - Airport",
              31.4, 980, 210, 14, 0.41, 1980),
    # F5 Eden Gardens egress
    _scenario("eden_egress", 1, "sc-eden-11", "Eden Gardens egress - Red Road - Esplanade",
              22.7, 760, 300, 7, 0.35, 0),
    _decision("eden_egress", 2, "egress_surge",
              "Night match ends at Eden Gardens; 60,000 spectators leaving towards Esplanade, BBD Bag and Babughat "
              "ferry; buses queued on Red Road.",
              crowd_level="high", metro="Esplanade station crowded", exits_metered="yes"),
    # F6 cyclone tree fall
    _incident("cyclone_maidan", 1, "weather", "critical",
              "Cyclone gusts uprooted trees across Red Road and Kidderpore Road near the Maidan; both carriageways "
              "blocked; KMC tree-cutting team called."),
    _decision("cyclone_maidan", 2, "cyclone_recovery",
              "Post-landfall recovery: tree falls on Red Road and Hospital Road; evacuation route to SSKM must be "
              "restored first.",
              blocked_segments=4, priority="SSKM access", crews_available=3),
    # F7 ambulance corridor through Park Circus
    _decision("amb_parkcircus", 1, "ambulance_request",
              "Ambulance (108) requests a green corridor from Park Circus seven-point crossing to SSKM Hospital "
              "through evening traffic on AJC Bose Road.",
              unit_eta_min=14, window_sec=120, junctions=6),
    _aar("amb_parkcircus", 2, "Green corridor Park Circus to SSKM",
         "The window opened 90 seconds ahead of the ambulance at each of six junctions on AJC Bose Road; the unit "
         "reached SSKM in 11 minutes."),
    # F8 signal failure Ultadanga
    _incident("signal_ultadanga", 1, "signal_failure", "medium",
              "Signal controller at Ultadanga crossing dark after a power cut; EM Bypass northbound queue 600 m; "
              "manual control by traffic constables."),
    _decision("signal_ultadanga", 2, "signal_failure",
              "Ultadanga junction signals out; VIP Road and EM Bypass flows conflicting. Propose manual control and "
              "a fixed-time plan once power returns.",
              queue_m=600, constables_on_site=2),
    # F9 Gangasagar transit at Babughat
    _scenario("gangasagar", 1, "sc-sagar-02", "Babughat transit camp - Strand Road - Howrah Station",
              18.9, 640, 180, 6, 0.28, 0),
    _decision("gangasagar", 2, "mass_gathering",
              "Gangasagar pilgrims arriving at Babughat transit camp; buses to Kakdwip loading on Strand Road; "
              "pedestrian surge from Howrah Station.",
              crowd_level="high", buses_waiting=40),
    # F10 Kolkata Marathon
    _scenario("marathon", 1, "sc-marathon-01", "Red Road - Park Street - Chowringhee (Kolkata Marathon)",
              26.1, 820, 3600, 11, 0.47, 0),
    _decision("marathon", 2, "race",
              "Kolkata Marathon morning: Red Road, Park Street and Chowringhee closed until the last runner passes; "
              "church traffic on Park Street to be held.",
              closure_until="10:30", detour="AJC Bose Road"),
    # F11 rally at Esplanade
    _incident("rally_esplanade", 1, "protest", "medium",
              "A large rally at Esplanade (Dharmatala) crossing; Chowringhee and Lenin Sarani closed for 2 hours; "
              "buses diverted."),
    _decision("rally_esplanade", 2, "mass_gathering",
              "Rally assembling at Esplanade; S N Banerjee Road and Lenin Sarani blocked; trams and buses held.",
              expected_duration_min=120, detour="Central Avenue"),
    # F12 Sealdah surge
    _incident("sealdah_surge", 1, "congestion_spike", "high",
              "Local trains cancelled after a technical fault; passenger surge out of Sealdah station onto APC Road "
              "and Moulali; taxis and buses overwhelmed."),
    _decision("sealdah_surge", 2, "egress_surge",
              "Sealdah station crowd spilling onto the road after cancellations; more buses requested from WBTC; "
              "Moulali crossing jammed.",
              crowd_level="high", extra_buses_requested=15),
    # F13 New Year Park Street
    _decision("newyear_parkstreet", 1, "crowd_density",
              "New Year's Eve crowd on Park Street; vehicle entry closed from Chowringhee end; pedestrians only "
              "after 21:00.",
              crowd_level="very high", closure="Park Street, Chowringhee to Camac Street"),
    _aar("newyear_parkstreet", 2, "New Year's Eve Park Street",
         "Closing Park Street to vehicles at 21:00 and routing cars via AJC Bose Road kept ambulance access to "
         "the crowd; the crowd dispersed by 01:30."),
    # F14 Majerhat / Diamond Harbour Road congestion
    _incident("majerhat", 1, "congestion_spike", "medium",
              "Majerhat bridge approach congested from Taratala; Diamond Harbour Road southbound at 8 km/h; school "
              "buses delayed."),
    _decision("majerhat", 2, "congestion",
              "Heavy congestion on Majerhat bridge and Diamond Harbour Road towards Behala Chowrasta; propose more "
              "green for the bridge approach at Taratala.",
              vc_ratio=0.93, speed_kmh=8),
    # F15 waterlogging south (Gariahat / Rashbehari)
    _decision("waterlog_south", 1, "waterlogging_alert",
              "Heavy rain over south Kolkata; water rising at Gariahat crossing and Rashbehari crossing on Rash "
              "Behari Avenue; Ballygunge Phari slowing.",
              rain_mm_last_hour=55, risk_class=3, gates="open"),
    _incident("waterlog_south", 2, "weather", "high",
              "Knee-deep water at Gariahat and Deshapriya Park; buses stalled on Rash Behari Avenue; Ballygunge "
              "pumping station at full capacity."),
    # F16 Sector V evening peak
    _decision("sector_v", 1, "congestion",
              "Evening office peak in Sector V, Salt Lake; IT park exits jammed onto Biswa Bangla Sarani and the "
              "Chingrighata approach.",
              vc_ratio=0.88, speed_kmh=12),
    _scenario("sector_v", 2, "sc-sec5-04", "Sector V - Chingrighata - EM Bypass", 14.3, 520, 0, 5, 0.22, 0),
    # distractors (no query targets them)
    _incident("x_workzone", 1, "other", "low",
              "Road work narrows Biswa Bangla Sarani near New Town bus stand to one lane for a week."),
    _incident("x_kidderpore", 1, "congestion_spike", "low",
              "Port trucks queue at Kidderpore dock gate; Garden Reach Road slow in the morning."),
    _decision("x_behala_school", 1, "congestion",
              "School-hour congestion at Behala Chowrasta; guardians' cars parked on Diamond Harbour Road.",
              vc_ratio=0.71),
    _incident("x_airport_fog", 1, "weather", "low",
              "Morning fog at Kolkata Airport delays departures; VIP Road light traffic."),
    _scenario("x_tolly", 1, "sc-tolly-09", "Tollygunge - Kalighat - Hazra", 9.8, 310, 0, 4, 0.15, 0),
    _decision("x_victoria", 1, "crowd_density",
              "Winter Sunday crowd at Victoria Memorial and the Maidan; parking spilling onto Queens Way.",
              crowd_level="moderate"),
    # hard negatives: the SAME place as a family but a different situation (a model that matches on place
    # names alone ranks these first)
    _decision("x_thanthania_puja", 1, "crowd_density",
              "Kali Puja night crowd at Thanthania Kalibari on Bidhan Sarani; vehicles slowed near College Street.",
              crowd_level="high", rain_mm_last_hour=0),
    _decision("x_howrah_vip", 1, "pre_movement",
              "Protected movement to cross Howrah Bridge at 07:00 towards Howrah Station; 6-minute hold planned.",
              expected_hold_min=6),
    _incident("x_shyambazar_signal", 1, "signal_failure", "medium",
              "Cable cut darkens the signals at Shyambazar five-point crossing; manual control on BT Road."),
    _incident("x_parkcircus_shopping", 1, "congestion_spike", "medium",
              "Festive shopping crowd at Park Circus seven-point crossing; buses slow on AJC Bose Road; no "
              "ambulance request pending."),
    _decision("x_redroad_parade", 1, "ceremonial",
              "Republic Day parade rehearsal on Red Road; Red Road closed 06:00-09:00; Hospital Road diversion.",
              closure_until="09:00"),
    _incident("x_sealdah_rain", 1, "weather", "medium",
              "Water under the Sealdah flyover after a short shower; APC Road southbound slow; trains on time."),
    _decision("x_gariahat_puja", 1, "crowd_density",
              "Ekdalia Evergreen and Singhi Park pandals draw crowds at Gariahat crossing on Rash Behari Avenue; "
              "no rain.", crowd_level="high"),
    _incident("x_ultadanga_water", 1, "weather", "low",
              "Shallow water under the Ultadanga flyover after rain; signals working; EM Bypass moving."),
    _incident("x_setu_toll", 1, "congestion_spike", "low",
              "Toll plaza queue on Vidyasagar Setu towards Kolkata; no movement planned; Nabanna side slow."),
    _incident("x_hazra_tree", 1, "weather", "medium",
              "A tree fell on Hazra Road after a squall; one lane blocked near Kalighat."),
    _incident("x_babughat_ferry", 1, "other", "low",
              "Ferry services from Babughat suspended for two hours for jetty repairs; no crowd."),
    _scenario("x_eden_day", 1, "sc-eden-02", "Eden Gardens - Babughat (day match, light crowd)",
              4.1, 150, 60, 2, 0.08, 0),
]

MEMORY_QUERIES: list[dict] = [
    # F1
    {"lang": "en", "family": "tide_central", "text": "TRIGGER: waterlogging_alert\nHeavy rain at high tide, gates "
     "shut; water rising at Thanthania and College Street. Ambulance route to Medical College at risk."},
    {"lang": "bn", "family": "tide_central", "text": "জোয়ারের সময় ভারী বৃষ্টি, লক গেট বন্ধ। ঠনঠনিয়া আর কলেজ স্ট্রিটে জল "
     "বাড়ছে, মেডিকেল কলেজে অ্যাম্বুলেন্স যাওয়ার পথ ঝুঁকিতে।"},
    {"lang": "hi", "family": "tide_central", "text": "ज्वार के समय भारी बारिश, गेट बंद। ठनठनिया और कॉलेज स्ट्रीट पर जलभराव "
     "बढ़ रहा है, मेडिकल कॉलेज जाने वाली एम्बुलेंस का रास्ता खतरे में।"},
    {"lang": "mixed", "family": "tide_central", "text": "Thanthania te high tide er somoy heavy rain, jol jomche, "
     "Bidhan Sarani slow, ambulance Medical College jabe kivabe?"},
    # F2
    {"lang": "en", "family": "puja_north", "text": "Ashtami night crowds at Bagbazar and Kumartuli pandals spilling "
     "onto the road; Shyambazar crossing jammed."},
    {"lang": "bn", "family": "puja_north", "text": "অষ্টমীর রাতে বাগবাজার আর কুমোরটুলির প্যান্ডেলে উপচে পড়া ভিড়, শ্যামবাজার "
     "পাঁচ মাথার মোড়ে গাড়ি আটকে।"},
    {"lang": "mixed", "family": "puja_north", "text": "Pujor bhir Bagbazar e, Shyambazar more e gari nodche na, "
     "pandal hopping crowd raastay"},
    # F3
    {"lang": "en", "family": "howrah_bridge", "text": "TRIGGER: route_blockage\nTruck broken down on Howrah Bridge "
     "towards Kolkata in the evening rush; queue back to Howrah Station."},
    {"lang": "bn", "family": "howrah_bridge", "text": "সন্ধ্যার ভিড়ে হাওড়া ব্রিজে একটি বাস খারাপ হয়ে দাঁড়িয়ে, হাওড়া "
     "স্টেশন পর্যন্ত লম্বা লাইন।"},
    {"lang": "hi", "family": "howrah_bridge", "text": "शाम के समय हावड़ा ब्रिज पर बस खराब, हावड़ा स्टेशन तक लंबा जाम।"},
    # F4
    {"lang": "en", "family": "vip_nabanna", "text": "TRIGGER: pre_movement\nProtected movement from Nabanna to the "
     "airport this afternoon via Vidyasagar Setu and EM Bypass."},
    {"lang": "bn", "family": "vip_nabanna", "text": "আজ বিকেলে নবান্ন থেকে বিমানবন্দর পর্যন্ত ভিআইপি চলাচল, বিদ্যাসাগর সেতু "
     "আর ই এম বাইপাস হয়ে।"},
    {"lang": "hi", "family": "vip_nabanna", "text": "नबान्न से कोलकाता हवाई अड्डे तक वीआईपी काफ़िला, विद्यासागर सेतु और "
     "ईएम बाईपास से।"},
    # F5
    {"lang": "en", "family": "eden_egress", "text": "Match over at Eden Gardens, crowd heading to Esplanade metro "
     "and Babughat; buses stuck on Red Road."},
    {"lang": "bn", "family": "eden_egress", "text": "ইডেন গার্ডেন্সে খেলা শেষ, দর্শকেরা এসপ্ল্যানেড মেট্রো আর বাবুঘাটের "
     "দিকে যাচ্ছেন।"},
    # F6
    {"lang": "en", "family": "cyclone_maidan", "text": "Cyclone aftermath: fallen trees blocking Red Road near the "
     "Maidan; access to SSKM must be cleared."},
    {"lang": "bn", "family": "cyclone_maidan", "text": "ঘূর্ণিঝড়ের পর রেড রোডে গাছ পড়ে রাস্তা বন্ধ, এসএসকেএম যাওয়ার পথ "
     "খুলতে হবে।"},
    {"lang": "mixed", "family": "cyclone_maidan", "text": "Cyclone e Red Road e gach pore geche, SSKM jawar rasta "
     "block"},
    # F7
    {"lang": "en", "family": "amb_parkcircus", "text": "TRIGGER: ambulance_request\nAmbulance (108) needs a green "
     "corridor from Park Circus to SSKM on AJC Bose Road."},
    {"lang": "bn", "family": "amb_parkcircus", "text": "পার্ক সার্কাস থেকে এসএসকেএম পর্যন্ত অ্যাম্বুলেন্সের জন্য গ্রিন করিডর "
     "দরকার।"},
    {"lang": "hi", "family": "amb_parkcircus", "text": "पार्क सर्कस से एसएसकेएम अस्पताल तक एम्बुलेंस के लिए ग्रीन कॉरिडोर चाहिए।"},
    # F8
    {"lang": "en", "family": "signal_ultadanga", "text": "Traffic lights dead at Ultadanga after a power cut; EM "
     "Bypass queue growing."},
    {"lang": "bn", "family": "signal_ultadanga", "text": "উল্টোডাঙায় বিদ্যুৎ চলে গিয়ে সিগন্যাল বন্ধ, বাইপাসে লাইন বাড়ছে।"},
    # F9
    {"lang": "en", "family": "gangasagar", "text": "Gangasagar pilgrims crowding Babughat transit camp; buses "
     "loading on Strand Road."},
    {"lang": "hi", "family": "gangasagar", "text": "गंगासागर जाने वाले तीर्थयात्रियों की भीड़ बाबूघाट पर, स्ट्रैंड रोड पर बसें।"},
    # F10
    {"lang": "en", "family": "marathon", "text": "Kolkata Marathon this Sunday; Red Road and Park Street closed "
     "until the last runner."},
    {"lang": "bn", "family": "marathon", "text": "রবিবার কলকাতা ম্যারাথন, রেড রোড আর পার্ক স্ট্রিট বন্ধ থাকবে।"},
    # F11
    {"lang": "en", "family": "rally_esplanade", "text": "Big rally at Dharmatala; Chowringhee and Lenin Sarani "
     "closed, buses diverted."},
    {"lang": "bn", "family": "rally_esplanade", "text": "ধর্মতলায় বড় সমাবেশ, চৌরঙ্গি আর লেনিন সরণি বন্ধ।"},
    # F12
    {"lang": "en", "family": "sealdah_surge", "text": "Trains cancelled, huge crowd coming out of Sealdah station "
     "onto APC Road."},
    {"lang": "mixed", "family": "sealdah_surge", "text": "Sealdah te train cancel, station theke bhir beriye "
     "Moulali jam"},
    # F13
    {"lang": "en", "family": "newyear_parkstreet", "text": "New Year's Eve: Park Street packed with people, "
     "close it to vehicles?"},
    {"lang": "bn", "family": "newyear_parkstreet", "text": "বর্ষবরণের রাতে পার্ক স্ট্রিটে প্রচণ্ড ভিড়, গাড়ি বন্ধ করা "
     "হবে কি?"},
    # F14
    {"lang": "en", "family": "majerhat", "text": "Diamond Harbour Road crawling towards Behala; Majerhat bridge "
     "approach backed up from Taratala."},
    {"lang": "hi", "family": "majerhat", "text": "माझेरहाट पुल पर भारी जाम, तारातला से डायमंड हार्बर रोड धीमी।"},
    # F15
    {"lang": "en", "family": "waterlog_south", "text": "Water rising at Gariahat and Rashbehari after a downpour; "
     "buses stalled on Rash Behari Avenue."},
    {"lang": "bn", "family": "waterlog_south", "text": "গড়িয়াহাট আর রাসবিহারী মোড়ে বৃষ্টির জল জমছে, বাস আটকে।"},
    {"lang": "mixed", "family": "waterlog_south", "text": "Gariahat e hatu jol, Rashbehari more e bus atke ache"},
    # F16
    {"lang": "en", "family": "sector_v", "text": "Office rush in Salt Lake Sector V; exits jammed towards "
     "Chingrighata."},
    {"lang": "bn", "family": "sector_v", "text": "সল্টলেক সেক্টর ফাইভে অফিস ছুটির ভিড়, চিংড়িঘাটার দিকে জট।"},
    # harder: alternate names, no exact place string, the situation (not the place) decides
    {"lang": "en", "family": "tide_central", "text": "TRIGGER: waterlogging_alert\nRiver above 5 m, lock gates "
     "shut, cloudburst over the College Street book market area; Central Avenue slowing.\nrisk_class: 2"},
    {"lang": "bn", "family": "tide_central", "text": "গঙ্গায় জোয়ার, লকগেট বন্ধ; বইপাড়ার রাস্তায় হাঁটুজল, সেন্ট্রাল "
     "অ্যাভিনিউ ধীর।"},
    {"lang": "en", "family": "howrah_bridge", "text": "TRIGGER: route_blockage\nBreakdown on Rabindra Setu during "
     "the evening peak; tow vehicle requested; Brabourne Road backing up."},
    {"lang": "en", "family": "rally_esplanade", "text": "TRIGGER: mass_gathering\nA political meeting is filling "
     "Dharmatala; Lenin Sarani and S N Banerjee Road blocked; trams held."},
    {"lang": "hi", "family": "rally_esplanade", "text": "धर्मतल्ला में बड़ी सभा, चौरंगी और लेनिन सरणी बंद, बसें मोड़ी गईं।"},
    {"lang": "en", "family": "amb_parkcircus", "text": "TRIGGER: ambulance_request\nPatient transfer by 108 from "
     "the seven-point crossing to PG Hospital; six signals on the way.\nwindow_sec: 120"},
    {"lang": "bn", "family": "cyclone_maidan", "text": "ঝড়ের পরে ময়দানের দিকে বড় গাছ পড়ে রাস্তা বন্ধ, পিজি "
     "হাসপাতালে পৌঁছনোর পথ আগে খুলতে হবে।"},
    {"lang": "en", "family": "marathon", "text": "TRIGGER: race\nSunday morning road race through Red Road and "
     "Chowringhee; stretch closed until the last runner clears."},
    {"lang": "bn", "family": "waterlog_south", "text": "দক্ষিণ কলকাতায় প্রবল বৃষ্টি, গড়িয়াহাটে জল জমে বাস বন্ধ, "
     "বালিগঞ্জ পাম্পিং স্টেশন পুরো দমে চলছে।"},
    {"lang": "mixed", "family": "signal_ultadanga", "text": "Ultadanga more e current nei, signal bondho, Bypass e "
     "line barche, constable diye manual control"},
    {"lang": "en", "family": "sealdah_surge", "text": "TRIGGER: egress_surge\nTrain cancellations at the station "
     "near Moulali; passengers spilling onto APC Road; WBTC asked for extra buses."},
    {"lang": "en", "family": "puja_north", "text": "TRIGGER: crowd_density\nNavami night in north Kolkata, crowds "
     "between the Bagbazar ghat and the idol-makers' quarter; BT Road one-way in force."},
]

# ─────────────────────────────────────────────────────────────────────────────
# (b) SOP / advisory
# ─────────────────────────────────────────────────────────────────────────────

DOC_FILES = ("hydro", "forecast", "speech", "vision", "twin")
PACK_KEYS = (
    "strip_watch", "strip_hold", "strip_severe", "consequence_procession", "consequence_mass_gathering",
    "consequence_race", "consequence_ceremonial", "consequence_egress_surge", "consequence_work_zone",
    "consequence_vehicle_pursuit", "consequence_unknown", "card_alt_none", "card_alt_unavailable",
    "citizen_feed_offline", "doctrine_note", "driver_deferred_body", "driver_window_unpublished",
    "comms_session_only",
)
PACK_DIR = REPO / "services/command-deck/src/lib/i18n"

# Advisory and proposal texts rendered from services/hydro/src/hydro/proposals.py and
# services/forecast/src/forecast/proposals.py templates (place values chosen for the eval).
RENDERED = {
    "r:hy_adv_en": "Traffic advisory (draft): waterlogging is likely within the next 90 minutes at these places: "
                   "Thanthania, College Street, Chittaranjan Avenue. Please avoid these roads if you can. Do not "
                   "touch electric poles or wires in standing water. Emergency: 112; ambulance (108).",
    "r:hy_adv_bn": "ট্রাফিক পরামর্শ (খসড়া): আগামী 90 মিনিটের মধ্যে এই জায়গাগুলিতে জল জমার আশঙ্কা: ঠনঠনিয়া, কলেজ "
                   "স্ট্রিট, চিত্তরঞ্জন অ্যাভিনিউ। সম্ভব হলে এই পথগুলি এড়িয়ে চলুন। জমা জলে বিদ্যুতের খুঁটি বা তার "
                   "ছোঁবেন না। জরুরি প্রয়োজনে 112; অ্যাম্বুলেন্স (108)।",
    "r:hy_wire": "Live-wire hazard — Thanthania (Bidhan Sarani): waterlogging risk 2 (15–30 cm). Propose asking the "
                 "power utility (CESC / WBSEDCL) to inspect and, where needed, isolate street-light and overhead "
                 "supply along this road.",
    "r:hy_amb": "Ambulance (108) note — Chittaranjan Avenue (Central Avenue): passable for about 35 min more; use "
                "Bidhan Sarani → APC Road.",
    "r:hy_reroute": "College Street (Bidhan Sarani): waterlogging risk 2 (15–30 cm), deep water in about 60 min; "
                    "propose diverting traffic via Mahatma Gandhi Road → APC Road.",
    "r:fc_adv": "Heavy traffic expected near Park Circus seven-point crossing in about 45 minutes. Please plan ahead.",
}

SOP_QUERIES: list[dict] = [
    {"lang": "en", "text": "What water level closes the outfall gates on the Hooghly?", "gold": ["d:hydro:6"]},
    {"lang": "bn", "text": "হুগলির জল কত মিটারে উঠলে লক গেট বন্ধ করা হয়?", "gold": ["d:hydro:6"]},
    {"lang": "hi", "text": "हुगली में पानी कितने मीटर पर पहुँचने पर आउटफ़ॉल गेट बंद होते हैं?", "gold": ["d:hydro:6"]},
    {"lang": "en", "text": "Are the KMC pumping station readings real or emulated?",
     "gold": ["d:hydro:10", "d:hydro:11"]},
    {"lang": "bn", "text": "পাম্পিং স্টেশনের তথ্য কি আসল, না এমুলেটেড?", "gold": ["d:hydro:10", "d:hydro:11"]},
    {"lang": "mixed", "text": "Pumping station gulor data ki real feed theke ase?",
     "gold": ["d:hydro:10", "d:hydro:11"]},
    {"lang": "en", "text": "What proposals does the waterlogging service draft for a flagged road?",
     "gold": ["d:hydro:1", "d:hydro:12", "d:hydro:13"]},
    {"lang": "bn", "text": "জল জমার ঝুঁকি থাকা রাস্তার জন্য কী কী প্রস্তাব তৈরি হয়?",
     "gold": ["d:hydro:1", "d:hydro:12", "d:hydro:13"]},
    {"lang": "en", "text": "How much rain fell in the peak hour on 23 September 2025?", "gold": ["d:hydro:14"]},
    {"lang": "bn", "text": "২০২৫ সালের ২৩ সেপ্টেম্বর সবচেয়ে বেশি বৃষ্টি কোন ঘণ্টায় হয়েছিল?", "gold": ["d:hydro:14"]},
    {"lang": "en", "text": "Why did the gridded rain archive miss the September 2025 storm?",
     "gold": ["d:hydro:16", "d:hydro:17"]},
    {"lang": "en", "text": "Which bridges and flyovers are treated as elevated in the susceptibility score?",
     "gold": ["d:hydro:9"]},
    {"lang": "hi", "text": "जलभराव के हिसाब से कौन से पुल और फ्लाईओवर ऊँचे माने जाते हैं?", "gold": ["d:hydro:9"]},
    {"lang": "en", "text": "Is the Garden Reach tide measured or modelled?",
     "gold": ["d:hydro:2", "d:hydro:3", "d:hydro:4", "d:hydro:5"]},
    {"lang": "en", "text": "When does the corridor forecast raise a pre-emptive diversion proposal?",
     "gold": ["d:forecast:0"]},
    {"lang": "bn", "text": "যানজট হওয়ার আগেই কখন ডাইভারশনের প্রস্তাব দেওয়া হয়?", "gold": ["d:forecast:0"]},
    {"lang": "mixed", "text": "Park Circus e V/C 0.8 cross korle ki diversion propose kora hoy?",
     "gold": ["d:forecast:0", "d:forecast:9"]},
    {"lang": "en", "text": "How accurate is Chronos-2 against the seasonal-naive baseline in the backtest?",
     "gold": ["d:forecast:10", "d:forecast:11"]},
    {"lang": "en", "text": "Is the corridor forecast based on real traffic data?", "gold": ["d:forecast:13"]},
    {"lang": "bn", "text": "যানজটের পূর্বাভাস কি আসল ট্রাফিকের তথ্যের উপর তৈরি?", "gold": ["d:forecast:13"]},
    {"lang": "en", "text": "When is the forecasting model freed from GPU memory?", "gold": ["d:forecast:12"]},
    {"lang": "en", "text": "How is the detour chosen for a forecast diversion?", "gold": ["d:forecast:8"]},
    {"lang": "hi", "text": "सिंथेटिक ट्रैफ़िक इतिहास में सुबह और शाम की भीड़ कब होती है?", "gold": ["d:forecast:6"]},
    {"lang": "bn", "text": "মাঠের অফিসার বাংলায় রিপোর্ট বললে কী হয়?", "gold": ["d:speech:0"]},
    {"lang": "hi", "text": "फ़ील्ड अधिकारी बांग्ला में बोलकर रिपोर्ट दे तो क्या होता है?", "gold": ["d:speech:0"]},
    {"lang": "en", "text": "What word error rate and place accuracy did the Bengali voice reports reach?",
     "gold": ["d:speech:4", "d:speech:2"]},
    {"lang": "mixed", "text": "Bengali voice report e whisper turbo keno nilam na?", "gold": ["d:speech:3"]},
    {"lang": "bn", "text": "ক্যামেরার ছবি থেকে রাস্তার কোন কোন অবস্থা চেনা যায়?", "gold": ["d:vision:0"]},
    {"lang": "en", "text": "How accurate was the camera road-state reader in its evaluation?", "gold": ["d:vision:2"]},
    {"lang": "en", "text": "Why test a signal-timing change in a twin before proposing it?",
     "gold": ["d:twin:0", "d:twin:2"]},
    {"lang": "bn", "text": "সিগন্যালের সময় বদলের প্রস্তাব কখন বাতিল করা হয়?", "gold": ["d:twin:2", "d:twin:3"]},
    {"lang": "en", "text": "Does the language model choose the signal timing?", "gold": ["d:twin:6"]},
    {"lang": "en", "text": "Which baselines are signal proposals compared against?", "gold": ["d:twin:5"]},
    {"lang": "bn", "text": "অ্যাম্বুলেন্স পৌঁছনোর কত আগে গ্রিন করিডর খোলে?", "gold": ["p:doctrine_note"]},
    {"lang": "en", "text": "How early does the green corridor open before an ambulance reaches a junction?",
     "gold": ["p:doctrine_note"]},
    {"lang": "hi", "text": "मैराथन के दौरान सड़क कब तक बंद रहती है?", "gold": ["p:consequence_race"]},
    {"lang": "bn", "text": "স্টেডিয়াম থেকে ভিড় বেরোলে গাড়ি কীভাবে ছাড়া হয়?", "gold": ["p:consequence_egress_surge"]},
    {"lang": "en", "text": "What should I do if there is no signed alternate route?", "gold": ["p:card_alt_none"]},
    {"lang": "bn", "text": "কন্ট্রোল রুম অনুরোধ স্থগিত রাখলে অ্যাম্বুলেন্স চালক কী করবেন?",
     "gold": ["p:driver_deferred_body"]},
    {"lang": "en", "text": "Are the advisory drafts sent out automatically?", "gold": ["p:comms_session_only"]},
    {"lang": "bn", "text": "শোভাযাত্রা যাওয়ার সময় মোড় কি বন্ধ থাকে?", "gold": ["p:consequence_procession"]},
    {"lang": "hi", "text": "रेड रोड परेड के समय ट्रैफ़िक कैसे रोका जाता है?", "gold": ["p:consequence_ceremonial"]},
    {"lang": "mixed", "text": "Road work cholche, ek lane e gari cholbe?", "gold": ["p:consequence_work_zone"]},
    {"lang": "bn", "text": "জমা জলে বিদ্যুতের খুঁটি নিয়ে কী সতর্কতা?",
     "gold": ["r:hy_adv_bn", "r:hy_adv_en", "r:hy_wire", "d:hydro:23"]},
    {"lang": "mixed", "text": "Jol jome thakle electric pole chhuben na, advisory te ki lekha?",
     "gold": ["r:hy_adv_bn", "r:hy_adv_en", "r:hy_wire", "d:hydro:23"]},
    {"lang": "en", "text": "Who is asked to isolate the street-light supply on a waterlogged road?",
     "gold": ["r:hy_wire"]},
    {"lang": "hi", "text": "जलभराव वाली सड़क से एम्बुलेंस कितनी देर और निकल सकती है?",
     "gold": ["r:hy_amb", "d:hydro:13"]},
]

# ─────────────────────────────────────────────────────────────────────────────
# (c) OSINT dedup / clustering (headline sets; same ``event`` = must cluster)
# ─────────────────────────────────────────────────────────────────────────────

OSINT: list[tuple[str, str, str]] = [  # (event, lang, headline)
    ("e01", "en", "Waterlogging at Thanthania after overnight downpour, traffic crawls on Bidhan Sarani"),
    ("e01", "bn", "রাতভর বৃষ্টিতে ঠনঠনিয়ায় জল জমে, বিধান সরণিতে গাড়ির গতি শ্লথ"),
    ("e01", "mixed", "Thanthania te jol joma, Bidhan Sarani te gari cholche na"),
    ("e02", "en", "Bus breaks down on Howrah Bridge, long queues in evening rush"),
    ("e02", "bn", "হাওড়া ব্রিজে বাস বিকল, সন্ধ্যায় দীর্ঘ যানজট"),
    ("e02", "hi", "हावड़ा ब्रिज पर बस खराब, शाम को लंबा जाम"),
    ("e03", "en", "Fire breaks out at a godown near Burrabazar; ten fire tenders rushed"),
    ("e03", "bn", "বড়বাজারের কাছে গুদামে আগুন, ঘটনাস্থলে দমকলের দশটি ইঞ্জিন"),
    ("e04", "en", "Tree uprooted on Red Road after storm, both carriageways blocked"),
    ("e04", "bn", "ঝড়ে রেড রোডে গাছ উপড়ে দুই দিকের রাস্তা বন্ধ"),
    ("e05", "en", "Signal failure at Ultadanga crossing causes long tailback on EM Bypass"),
    ("e05", "bn", "উল্টোডাঙা মোড়ে সিগন্যাল বিকল, বাইপাসে লম্বা যানজট"),
    ("e06", "en", "Local trains cancelled after technical snag; crowds swell at Sealdah station"),
    ("e06", "bn", "যান্ত্রিক ত্রুটিতে লোকাল ট্রেন বাতিল, শিয়ালদহ স্টেশনে উপচে পড়া ভিড়"),
    ("e06", "hi", "तकनीकी खराबी से लोकल ट्रेनें रद्द, सियालदह स्टेशन पर भारी भीड़"),
    ("e07", "en", "Puja crowd: Bagbazar and Kumartuli see record footfall on Saptami night"),
    ("e07", "bn", "সপ্তমীর রাতে বাগবাজার আর কুমোরটুলিতে রেকর্ড ভিড়"),
    ("e08", "en", "Goods vehicles barred from city roads during Durga Puja, says traffic police"),
    ("e08", "bn", "দুর্গাপুজোর কদিন শহরের রাস্তায় পণ্যবাহী গাড়ি ঢুকতে পারবে না, জানাল ট্রাফিক পুলিশ"),
    ("e09", "en", "Majerhat bridge approach jammed as Diamond Harbour Road crawls"),
    ("e09", "bn", "মাঝেরহাট সেতুর মুখে যানজট, ডায়মন্ড হারবার রোডে গাড়ির লম্বা লাইন"),
    ("e10", "en", "Knee-deep water at Gariahat; buses stranded on Rash Behari Avenue"),
    ("e10", "bn", "গড়িয়াহাটে হাঁটুজল, রাসবিহারী অ্যাভিনিউতে আটকে বাস"),
    ("e11", "en", "Kolkata Marathon on Sunday: Red Road, Park Street closed till 10.30 am"),
    ("e11", "bn", "রবিবার কলকাতা ম্যারাথন, সকাল সাড়ে দশটা পর্যন্ত রেড রোড ও পার্ক স্ট্রিট বন্ধ"),
    ("e12", "en", "Gangasagar pilgrims throng Babughat transit camp as Mela nears"),
    ("e12", "bn", "গঙ্গাসাগর মেলার আগে বাবুঘাট ট্রানজিট ক্যাম্পে পুণ্যার্থীদের ভিড়"),
    ("e12", "hi", "गंगासागर मेले से पहले बाबूघाट ट्रांजिट कैंप में तीर्थयात्रियों की भीड़"),
    ("e13", "en", "Metro services hit between Esplanade and Park Street after power disruption"),
    ("e13", "bn", "বিদ্যুৎ বিভ্রাটে এসপ্ল্যানেড-পার্ক স্ট্রিটের মধ্যে মেট্রো পরিষেবা ব্যাহত"),
    ("e14", "en", "Heavy rain at high tide: KMC closes outfall gates, pumps run at full capacity"),
    ("e14", "bn", "জোয়ারের সময় ভারী বৃষ্টি, লকগেট বন্ধ করল পুরসভা, পূর্ণ ক্ষমতায় চলছে পাম্প"),
    ("e15", "en", "Crowds on Park Street for New Year's Eve; vehicles stopped after 9 pm"),
    ("e15", "bn", "বর্ষবরণের রাতে পার্ক স্ট্রিটে জনস্রোত, রাত ন'টার পর গাড়ি বন্ধ"),
    ("e16", "en", "Overturned truck on VIP Road near Kestopur slows airport traffic"),
    ("e16", "bn", "কেষ্টপুরের কাছে ভিআইপি রোডে ট্রাক উল্টে বিমানবন্দরের রাস্তায় যানজট"),
    # hard negatives: same place, different event / same kind, different place
    ("n01", "en", "Howrah Bridge to get new LED lighting, says port trust"),
    ("n02", "en", "Fire at a shop near Gariahat market brought under control"),
    ("n03", "bn", "শিয়ালদহ স্টেশনে নতুন এসকেলেটর চালু"),
    ("n04", "en", "Waterlogging at Behala after heavy rain; Diamond Harbour Road affected"),
    ("n05", "en", "Signal upgrade work at Ultadanga to begin next month"),
    ("n06", "bn", "রেড রোডে প্রজাতন্ত্র দিবসের কুচকাওয়াজের মহড়া"),
    ("n07", "en", "Esplanade bus terminus to be redesigned, KMC approves plan"),
    ("n08", "en", "Tree falls on Hazra Road after squall, one lane blocked"),
    ("n09", "bn", "বাগবাজারে গঙ্গার ঘাট সংস্কারের কাজ শুরু"),
    ("n10", "en", "Truck overturns on Kona Expressway, Howrah traffic hit"),
    ("n11", "en", "Bus breaks down on Vidyasagar Setu, Kidderpore-bound traffic slow"),
    ("n12", "bn", "শ্যামবাজার মোড়ে সিগন্যাল বিকল, বিটি রোডে যানজট"),
    ("n13", "bn", "বড়দিনের সন্ধ্যায় পার্ক স্ট্রিটে ভিড়, আলোকসজ্জা দেখতে মানুষের ঢল"),
    ("n14", "en", "Howrah station crowds swell after local trains cancelled on the Bandel line"),
    ("n15", "hi", "बागबाज़ार के पूजा पंडाल के पास दुकान में आग, कोई घायल नहीं"),
    # OSINT test fixture cluster (services/osint-common/tests/fixtures, synthetic, another city)
    ("f01", "en", "Car crashes into three vehicles near Karnavati Club on SG Highway; 3 injured"),
    ("f01", "en", "Multi-vehicle crash on SG Highway near Prahlad Nagar leaves three injured"),
    ("f01", "en", "SG Highway accident: vehicles collided near Prahlad Nagar, one lane blocked"),
    ("f01", "en", "Three injured after car rammed vehicles on SG Highway near Karnavati Club"),
]


# ─────────────────────────────────────────────────────────────────────────────


def doc_paragraphs() -> list[dict]:
    """Every paragraph of 25+ words in docs/ai/*.md (ids d:<file>:<n>, stable for a given doc revision)."""
    out: list[dict] = []
    for name in DOC_FILES:
        text = (REPO / "docs/ai" / f"{name}.md").read_text(encoding="utf-8")
        head = ""
        n = 0
        for block in re.split(r"\n\s*\n", text):
            b = block.strip()
            if b.startswith("#"):
                head = b.splitlines()[0].lstrip("# ").strip()
                b = "\n".join(b.splitlines()[1:]).strip()
                if not b:
                    continue
            if b.startswith(("```", "|", "<")) or len(b.split()) < 25:
                continue
            out.append({"id": f"d:{name}:{n}", "source": f"docs/ai/{name}.md", "title": head,
                        "body": " ".join(b.split()), "lang": "en"})
            n += 1
    return out


def pack_strings() -> list[dict]:
    """The deck's citizen advisory pack strings: the same key in en / bn / hi (ids p:<key>:<lang>)."""
    out: list[dict] = []
    for lang, suffix in (("en", ""), ("bn", ".bn"), ("hi", ".hi")):
        src = (PACK_DIR / f"strings.citizen{suffix}.ts").read_text(encoding="utf-8")
        for key in PACK_KEYS:
            m = re.search(rf"^\s*{key}:\s*\n?\s*'((?:[^'\\]|\\.)*)'", src, re.M)
            if not m:
                raise SystemExit(f"pack key {key} missing in strings.citizen{suffix}.ts")
            out.append({"id": f"p:{key}:{lang}", "source": f"strings.citizen{suffix}.ts", "title": key,
                        "body": m.group(1).replace("\\'", "'"), "lang": lang})
    return out


def build() -> dict:
    sop_docs = doc_paragraphs() + pack_strings() + [
        {"id": k, "source": "rendered from hydro/forecast proposal templates", "title": "", "body": v,
         "lang": "bn" if k.endswith("_bn") else "en"} for k, v in RENDERED.items()]
    ids = {d["id"] for d in sop_docs}
    sop_queries = []
    for i, q in enumerate(SOP_QUERIES):
        gold: list[str] = []
        for g in q["gold"]:
            if g.startswith("p:"):
                gold += [f"{g}:{lang}" for lang in ("en", "bn", "hi")]
            else:
                gold.append(g)
        missing = [g for g in gold if g not in ids]
        if missing:
            raise SystemExit(f"sop query {i} gold ids missing from the corpus: {missing}")
        sop_queries.append({"id": f"sq{i:02d}", "lang": q["lang"], "text": q["text"], "gold": gold})

    families = {d["family"] for d in MEMORY_DOCS}
    mem_queries = []
    for i, q in enumerate(MEMORY_QUERIES):
        if q["family"] not in families:
            raise SystemExit(f"memory query {i}: unknown family {q['family']}")
        gold = [d["id"] for d in MEMORY_DOCS if d["family"] == q["family"]]
        mem_queries.append({"id": f"mq{i:02d}", "lang": q["lang"], "text": q["text"], "gold": gold})

    osint = [{"id": f"h{i:02d}", "event": ev, "lang": lang, "text": text} for i, (ev, lang, text) in enumerate(OSINT)]
    return {
        "label": "SYNTHETIC",
        "note": ("Invented situations, questions and headlines with real Kolkata place names, written for this "
                 "eval from the repo's own material. Not real events; no real person; no real statistic."),
        "memory": {"docs": MEMORY_DOCS, "queries": mem_queries},
        "sop": {"docs": sop_docs, "queries": sop_queries},
        "osint": {"headlines": osint},
    }


def main() -> None:
    data = build()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    m, s, o = data["memory"], data["sop"], data["osint"]
    langs = lambda qs: {k: sum(1 for q in qs if q["lang"] == k) for k in ("en", "bn", "hi", "mixed")}  # noqa: E731
    print(f"memory: {len(m['docs'])} docs, {len(m['queries'])} queries {langs(m['queries'])}")
    print(f"sop:    {len(s['docs'])} docs, {len(s['queries'])} queries {langs(s['queries'])}")
    events = {h['event'] for h in o['headlines']}
    print(f"osint:  {len(o['headlines'])} headlines, {len(events)} events")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
