"""City-feed PROPOSALS — never actions. A named officer approves each one; if no one answers, nothing changes.

The shape is the platform's decision-support vocabulary, the same as services/hydro and services/forecast:
``state: proposed``, actions as ``CoaAction`` (verb, target_urn, params, requires_officer, reversible),
``recommendation.decision: await_officer`` and a ``human_gate`` naming the deciding role with no officer and no
decision time.

* **air health advisory** (city National AQI band Moderate or worse now, or Poor or worse in the next 48 h; on a
  firecracker night — Kali Puja and Diwali — Moderate within 48 h is enough and the text names the smoke) — a
  public advisory draft in বাংলা, English and हिंदी from CPCB's band health statements, plus (Poor or worse) a
  note for traffic duty: masks at the busiest junction posts and shorter turns;
* **heat duty-shift advisory** (heat index "danger" ≥ 41 °C within 48 h, an IMD-criteria heatwave day in the
  forecast, or "extreme caution" ≥ 32 °C in the April–June season) — shorter turns at exposed junction posts
  through 11:00–16:00 IST, water and shade, and a citizen advisory in three languages (NDMA heat-wave guidelines
  2019 recommend moving outdoor work out of the hottest hours);
* **cyclone pre-positioning** (an active GDACS cyclone with Kolkata inside a wind buffer, its track within 300 km,
  or an Orange/Red alert within 600 km) — tree-cutting teams staged at the arterials' junctions, ahead of the
  tree-falls Amphan (2020) and Remal (2024) caused; after landfall, staged reopening road by road. The officer
  decides where and when.

When no trigger holds, the endpoint says why, with the threshold, instead of drafting anything.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

__all__ = ["GATE", "air_advisory", "heat_shift", "cyclone_preposition", "ARTERIALS", "HEAT_POSTS", "FESTIVAL_NIGHTS",
           "festival_near"]

GATE = {"state": "proposed", "required_role": "duty_officer", "officer": None, "decided_at": None}

ORDER = ["good", "satisfactory", "moderate", "poor", "very_poor", "severe"]

#: (segment ids, road name, staging junction id, junction name) — cities/kolkata/network.json
ARTERIALS: list[tuple[list[int], str, int, str]] = [
    ([1035, 1036, 1037, 1038], "Eastern Metropolitan Bypass", 29, "Ruby crossing"),
    ([1023, 1024, 1025], "Acharya Jagadish Chandra Bose Road", 17, "Park Circus seven-point crossing"),
    ([1013], "Indira Gandhi Sarani (Red Road)", 9, "Red Road, north end"),
    ([1016, 1017, 1018], "Jawaharlal Nehru Road (Chowringhee)", 7, "Esplanade"),
    ([1032, 1033], "Rash Behari Avenue", 20, "Rashbehari crossing"),
    ([1048, 1049, 1050], "Diamond Harbour Road", 27, "Taratala"),
    ([1039, 1040, 1041, 1042, 1043], "VIP Road (Kazi Nazrul Islam Avenue)", 35, "VIP Road, Kestopur"),
    ([1014], "Kidderpore Road", 10, "Red Road, south end"),
]

#: exposed junction posts for the heat advisory (junction id, name) — cities/kolkata/network.json
HEAT_POSTS: list[tuple[int, str]] = [(7, "Esplanade"), (12, "Park Street crossing"), (41, "Shyambazar five-point crossing"),
                                     (33, "Ultadanga"), (23, "Gariahat crossing"), (29, "Ruby crossing"),
                                     (3, "Howrah Bridge, Kolkata end"), (16, "Sealdah")]

NDMA_HEAT = {"publisher": "National Disaster Management Authority",
             "document": "Guidelines for Preparation of Action Plan: Prevention and Management of Heat Wave (2019)",
             "url": "https://ndma.gov.in/sites/default/files/PDF/Guidelines/heatwaveguidelines.pdf"}


def _base(pid: str, kind: str, subject: str, at: datetime, summary: str, actions: list[dict],
          labels: list[str]) -> dict[str, Any]:
    return {"proposal_id": pid, "kind": kind, "subject_urn": subject, "state": "proposed",
            "generated_at": at.isoformat(), "summary": summary, "actions": actions,
            "recommendation": {"decision": "await_officer"}, "human_gate": dict(GATE), "labels": labels}


AIR_TEXT = {
    "moderate": {
        "en": "People with asthma, lung or heart disease, children and older adults: keep long outdoor exertion short.",
        "bn": "হাঁপানি, ফুসফুস বা হৃদরোগ আছে এমন মানুষ, শিশু ও বয়স্করা বাইরে দীর্ঘ পরিশ্রম কম করুন।",
        "hi": "दमा, फेफड़े या हृदय रोग वाले लोग, बच्चे और बुज़ुर्ग बाहर लंबी मेहनत कम करें।",
    },
    "poor": {
        "en": "Everyone: cut down long or heavy outdoor exertion; people with asthma, lung or heart disease should avoid it. "
              "Keep windows shut in the evening smog hours.",
        "bn": "সবাই বাইরে দীর্ঘ বা ভারী পরিশ্রম কমান; হাঁপানি, ফুসফুস বা হৃদরোগ থাকলে তা এড়িয়ে চলুন। "
              "সন্ধ্যার ধোঁয়াশার সময় জানলা বন্ধ রাখুন।",
        "hi": "सभी लोग बाहर लंबी या भारी मेहनत कम करें; दमा, फेफड़े या हृदय रोग वाले इससे बचें। "
              "शाम के स्मॉग के समय खिड़कियाँ बंद रखें।",
    },
    "very_poor": {
        "en": "Avoid outdoor exertion. Children, older adults and people with lung or heart disease should stay indoors; "
              "wear a well-fitted N95 mask if you must go out.",
        "bn": "বাইরে পরিশ্রম এড়িয়ে চলুন। শিশু, বয়স্ক এবং ফুসফুস বা হৃদরোগ আছে এমন মানুষ ঘরে থাকুন; "
              "বেরোতেই হলে ঠিকমতো আঁটা এন৯৫ মাস্ক পরুন।",
        "hi": "बाहर मेहनत से बचें। बच्चे, बुज़ुर्ग और फेफड़े या हृदय रोग वाले घर में रहें; "
              "बाहर जाना ही पड़े तो ठीक से लगा N95 मास्क पहनें।",
    },
}
AIR_TEXT["severe"] = AIR_TEXT["very_poor"]


#: Firecracker nights (IST dates). Kali Puja falls on the Amavasya of Kartik, the same night as Diwali in 2026
#: (8 Nov 2026; Haindavam and Hindutone festival calendars). The advisory is drafted from Moderate within 48 h on
#: the night itself and the nights either side, and its text names the smoke after dark.
FESTIVAL_NIGHTS: dict[str, dict[str, str]] = {
    "2026-11-08": {"en": "Kali Puja and Diwali", "bn": "কালীপুজো ও দীপাবলি", "hi": "काली पूजा और दीपावली"},
}

FESTIVAL_TEXT = {
    "en": "{name} night: firecracker smoke makes the air worse after dark. Keep children and older people indoors in the evening.",
    "bn": "{name}র রাতে বাজির ধোঁয়ায় সন্ধ্যার পর বাতাস আরও খারাপ হয়। শিশু ও বয়স্কদের সন্ধ্যায় ঘরে রাখুন।",
    "hi": "{name} की रात पटाखों के धुएँ से अंधेरा होने के बाद हवा और खराब होती है। बच्चों और बुज़ुर्गों को शाम को घर में रखें।",
}


def festival_near(at: datetime) -> dict[str, str] | None:
    """The firecracker night within a day of ``at`` (IST), if any."""
    ist = (at + timedelta(hours=5, minutes=30)).date()
    for d in (ist, ist + timedelta(days=1), ist - timedelta(days=1)):
        if d.isoformat() in FESTIVAL_NIGHTS:
            return FESTIVAL_NIGHTS[d.isoformat()] | {"date": d.isoformat()}
    return None


def air_advisory(air: dict, at: datetime, labels: list[str]) -> dict[str, Any] | dict[str, str]:
    city = air.get("city")
    nxt = (air.get("next_48h_worst") or {}).get("naqi")
    now_i = ORDER.index(city["band"]) if city else -1
    nxt_i = ORDER.index(nxt["band"]) if nxt else -1
    fest = festival_near(at)
    if fest and max(now_i, nxt_i) >= ORDER.index("moderate"):
        pass  # a firecracker night: draft from Moderate, now or within 48 h
    elif now_i < ORDER.index("moderate") and nxt_i < ORDER.index("poor"):
        return {"none": f"no air advisory: the city's indicative National AQI is "
                        f"{city['band_en'] if city else 'unknown'} (a draft starts at Moderate now or Poor within 48 h)"}
    use_next = nxt_i > now_i
    band = ORDER[max(now_i, nxt_i)]
    aqi = (nxt if use_next else city)["aqi"]
    when_en = "in the next 48 hours" if use_next else "today"
    when_bn = "আগামী ৪৮ ঘণ্টায়" if use_next else "আজ"
    when_hi = "अगले 48 घंटों में" if use_next else "आज"
    names = {b: (city or {}).get(f"band_{b}") for b in ("en", "bn", "hi")}
    if use_next:
        names = {"en": nxt["band_en"], "bn": nxt["band_bn"], "hi": nxt["band_hi"]}
    t = AIR_TEXT[band if band in AIR_TEXT else "moderate"]
    en = (f"Air quality advisory (draft): Kolkata's air is {names['en'].lower()} {when_en} "
          f"(indicative National AQI {aqi}, modelled). {t['en']} Emergency: 112; ambulance (108).")
    bn = (f"বায়ুর মান নিয়ে পরামর্শ (খসড়া): {when_bn} কলকাতার বাতাস {names['bn']} "
          f"(আনুমানিক জাতীয় বায়ু মান সূচক {aqi}, মডেল-ভিত্তিক)। {t['bn']} জরুরি প্রয়োজনে 112; অ্যাম্বুলেন্স (108)।")
    hi = (f"वायु गुणवत्ता सलाह (मसौदा): {when_hi} कोलकाता की हवा {names['hi']} है "
          f"(अनुमानित राष्ट्रीय वायु गुणवत्ता सूचकांक {aqi}, मॉडल-आधारित)। {t['hi']} आपात स्थिति: 112; एम्बुलेंस (108)।")
    if fest:
        en = en.replace(" Emergency:", " " + FESTIVAL_TEXT["en"].format(name=fest["en"]) + " Emergency:")
        bn = bn.replace(" জরুরি প্রয়োজনে", " " + FESTIVAL_TEXT["bn"].format(name=fest["bn"]) + " জরুরি প্রয়োজনে")
        hi = hi.replace(" आपात स्थिति:", " " + FESTIVAL_TEXT["hi"].format(name=fest["hi"]) + " आपात स्थिति:")
    stamp = at.strftime("%Y%m%dT%H%MZ")
    actions = [{"verb": "advisory", "target_urn": "place:kolkata",
                "params": {"text_en": en, "text_bn": bn, "text_hi": hi, "band": band, "aqi": aqi,
                           "channel": "public advisory (after officer approval)"},
                "requires_officer": True, "reversible": True}]
    if ORDER.index(band) >= ORDER.index("poor"):
        actions.append({"verb": "advisory", "target_urn": "agency:kp_traffic",
                        "params": {"to_agency": "kp_traffic",
                                   "note": "Masks (N95) for officers at the busiest junction posts; shorter turns "
                                           "during the evening smog hours.",
                                   "posts": [{"junction_id": j, "name": n} for j, n in HEAT_POSTS]},
                        "requires_officer": True, "reversible": True})
    p = _base(f"cf-air-{stamp}", "air_health_advisory_draft", "place:kolkata", at,
              f"Air health advisory draft (বাংলা, English, हिंदी): {names['en']} {when_en}, indicative AQI {aqi}.",
              actions, labels)
    p["text"] = {"en": en, "bn": bn, "hi": hi}
    p["basis"] = {"band": band, "aqi": aqi, "from": "next_48h" if use_next else "now", "festival": fest,
                  "health": "CPCB National AQI band health statement", "source": air.get("naqi_source")}
    return p


def heat_shift(heat: dict, at: datetime, labels: list[str]) -> dict[str, Any] | dict[str, str]:
    peak = heat.get("peak_48h") or {}
    hi = peak.get("heat_index")
    hw = heat.get("imd_heatwave_days") or []
    in_season = heat.get("in_season")
    trigger = None
    if hw:
        trigger = f"IMD-criteria heatwave forecast ({hw[0]['date']}, max {hw[0]['imd']['tmax']} °C, " \
                  f"{hw[0]['imd']['departure']:+.1f} °C from normal; modelled)"
    elif hi is not None and hi >= 41:
        trigger = f"heat index {hi} °C (danger) at {peak.get('at_ist', '')[11:16]} IST"
    elif in_season and hi is not None and hi >= 32:
        trigger = f"heat index {hi} °C (extreme caution) in the April–June heat season"
    if not trigger:
        return {"none": f"no heat advisory: the 48-hour peak heat index is {hi} °C "
                        f"({'in' if in_season else 'outside'} the April–June season; a draft starts at 41 °C, "
                        "at 32 °C in season, or on an IMD-criteria heatwave day)"}
    posts = [{"junction_id": j, "name": n} for j, n in HEAT_POSTS]
    en = ("Heat advisory (draft): it will be very hot this afternoon. Drink water often, stay in the shade between "
          "11 am and 4 pm, and check on older neighbours. Emergency: 112; ambulance (108).")
    bn = ("গরম নিয়ে পরামর্শ (খসড়া): আজ দুপুরে খুব গরম থাকবে। বারবার জল খান, বেলা 11টা থেকে বিকেল 4টে ছায়ায় থাকুন "
          "এবং বয়স্ক প্রতিবেশীদের খোঁজ নিন। জরুরি প্রয়োজনে 112; অ্যাম্বুলেন্স (108)।")
    hi_t = ("गर्मी की सलाह (मसौदा): आज दोपहर बहुत गर्मी रहेगी। बार-बार पानी पिएँ, सुबह 11 से शाम 4 बजे तक छाँव में रहें "
            "और बुज़ुर्ग पड़ोसियों का हालचाल लें। आपात स्थिति: 112; एम्बुलेंस (108)।")
    stamp = at.strftime("%Y%m%dT%H%MZ")
    actions = [
        {"verb": "duty_roster", "target_urn": "agency:kp_traffic",
         "params": {"to_agency": "kp_traffic", "window_ist": ["11:00", "16:00"], "turn_max_min": 120,
                    "posts": posts, "provisions": ["drinking water and ORS at each post", "shade (umbrella or canopy)"],
                    "why": trigger, "basis": NDMA_HEAT},
         "requires_officer": True, "reversible": True},
        {"verb": "advisory", "target_urn": "place:kolkata",
         "params": {"text_en": en, "text_bn": bn, "text_hi": hi_t, "channel": "public advisory (after officer approval)"},
         "requires_officer": True, "reversible": True},
    ]
    p = _base(f"cf-heat-{stamp}", "heat_duty_shift_advisory", "agency:kp_traffic", at,
              f"Heat: shorter turns (≤ 2 h) at {len(posts)} exposed junction posts through 11:00–16:00 IST; {trigger}.",
              actions, labels)
    p["text"] = {"en": en, "bn": bn, "hi": hi_t}
    return p


def cyclone_preposition(cyc: dict, at: datetime, labels: list[str]) -> dict[str, Any] | dict[str, str]:
    n = cyc.get("nearest")
    if not n:
        return {"none": "no cyclone proposal: no active cyclone in the Bay of Bengal region (GDACS)"}
    closest = (n.get("closest_approach") or {}).get("distance_km")
    inside = n.get("kolkata_in_wind_buffer_kmh")
    level = n.get("alertlevel")
    trigger = None
    if inside:
        trigger = f"Kolkata inside the {inside} km/h wind buffer of {n['name']}"
    elif closest is not None and closest <= 300:
        trigger = f"{n['name']}'s track passes within {closest} km of Kolkata"
    elif level in ("orange", "red") and n["distance_km"] <= 600:
        trigger = f"{n['name']} ({level} alert) is {n['distance_km']} km {n['bearing']} of Kolkata"
    if not trigger:
        return {"none": f"no cyclone proposal: {n['name']} ({level} alert) is {n['distance_km']} km {n['bearing']} of "
                        f"Kolkata and its track comes no closer than {closest} km (a draft starts inside a wind buffer, "
                        "within 300 km, or for an Orange/Red alert within 600 km)"}
    stamp = at.strftime("%Y%m%dT%H%MZ")
    actions = [{"verb": "preposition", "target_urn": f"segment:{segs[0]}",
                "params": {"team": "tree-cutting team (KMC parks, WBSDMA, power utility for wires)", "road": road,
                           "segment_ids": segs, "stage_at_junction": j, "stage_at": jname,
                           "then": "after landfall, reopen road by road once cleared and the wires are checked"},
                "requires_officer": True, "reversible": True} for segs, road, j, jname in ARTERIALS]
    p = _base(f"cf-cyclone-{n['eventid']}-{stamp}", "cyclone_preposition", f"gdacs:TC:{n['eventid']}", at,
              f"Cyclone {n['name']}: {trigger}. Propose staging tree-cutting teams on {len(ARTERIALS)} arterials "
              "before landfall; the officer decides where and when.", actions, labels)
    p["situation"] = {"name": n["name"], "alertlevel": level, "distance_km": n["distance_km"], "bearing": n["bearing"],
                      "closest_approach_km": closest, "in_wind_buffer_kmh": inside}
    return p
