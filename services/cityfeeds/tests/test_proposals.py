"""Proposals are drafts for a named officer: the shape, the three languages and the triggers."""

from datetime import UTC, datetime

from cityfeeds.proposals import ARTERIALS, air_advisory, cyclone_preposition, heat_shift

AT = datetime(2026, 11, 8, 14, 30, tzinfo=UTC)


def _gate_ok(p):
    assert p["state"] == "proposed" and p["recommendation"]["decision"] == "await_officer"
    assert p["human_gate"] == {"state": "proposed", "required_role": "duty_officer", "officer": None, "decided_at": None}
    assert all(a["requires_officer"] and a["reversible"] for a in p["actions"])


def _air(band, aqi):
    names = {"poor": ("Poor", "খারাপ", "खराब"), "very_poor": ("Very poor", "খুব খারাপ", "बहुत खराब")}[band]
    city = {"aqi": aqi, "band": band, "band_en": names[0], "band_bn": names[1], "band_hi": names[2]}
    return {"city": city, "next_48h_worst": None, "naqi_source": {"url": "https://cpcb.nic.in/National-Air-Quality-Index/"}}


def test_air_advisory_three_languages_and_duty_note():
    p = air_advisory(_air("very_poor", 342), AT, ["LIVE", "MODELLED", "INDICATIVE"])
    _gate_ok(p)
    assert p["text"]["bn"].endswith("।") and p["text"]["hi"].endswith("।") and "(খসড়া)" in p["text"]["bn"]
    assert "342" in p["text"]["en"] and "ambulance (108)" in p["text"]["en"]
    assert any(a["target_urn"] == "agency:kp_traffic" for a in p["actions"])


def test_heat_shift_on_an_imd_heatwave_day():
    heat = {"peak_48h": {"heat_index": 39.0, "at_ist": "2027-05-02T14:00"}, "in_season": True,
            "imd_heatwave_days": [{"point": "alipore", "date": "2027-05-02", "imd": {"tmax": 41.2, "departure": 5.7, "level": "heatwave"}}]}
    p = heat_shift(heat, AT, ["LIVE", "MODELLED"])
    _gate_ok(p)
    roster = p["actions"][0]
    assert roster["verb"] == "duty_roster" and roster["params"]["turn_max_min"] == 120 and len(roster["params"]["posts"]) == 8
    assert p["text"]["bn"].endswith("।")


def test_cyclone_preposition_only_when_close():
    far = {"nearest": {"name": "X", "alertlevel": "red", "distance_km": 972, "bearing": "SW", "eventid": 1,
                       "closest_approach": {"distance_km": 700}, "kolkata_in_wind_buffer_kmh": None}}
    assert "none" in cyclone_preposition(far, AT, [])
    near = {"nearest": {**far["nearest"], "distance_km": 240, "closest_approach": {"distance_km": 40},
                        "kolkata_in_wind_buffer_kmh": 90}}
    p = cyclone_preposition(near, AT, ["LIVE", "MODELLED"])
    _gate_ok(p)
    assert len(p["actions"]) == len(ARTERIALS) and p["situation"]["in_wind_buffer_kmh"] == 90
    assert all(a["verb"] == "preposition" and a["target_urn"].startswith("segment:") for a in p["actions"])


def test_dvc_news_signal_counts_mentions_only():
    from datetime import UTC, datetime

    from cityfeeds.river import count_mentions
    news = {"feeds": {"sp": {"publisher": "sangbadpratidin.in", "items": [
        {"title": "ডিভিসি জল ছাড়ল, প্লাবিত আমতা", "description": "", "link": "https://x/1", "pubDate": "Wed, 28 Oct 2026 10:00:00 +0530"},
        {"title": "DVC releases 1.2 lakh cusecs from Durgapur barrage", "description": "", "link": "https://x/2", "pubDate": "Wed, 28 Oct 2026 09:00:00 +0530"},
        {"title": "Unrelated city news", "description": "", "link": "https://x/3", "pubDate": "Wed, 28 Oct 2026 08:00:00 +0530"},
        {"title": "DVC old item", "description": "", "link": "https://x/4", "pubDate": "Mon, 19 Oct 2026 08:00:00 +0530"},
    ]}}, "errors": {"mp": "403"}}
    r = count_mentions(news, datetime(2026, 10, 28, 12, 0, tzinfo=UTC))
    assert r["label"] == "AGGREGATE" and r["mentions"] == 2 and r["items_scanned"] == 3
    assert r["by_outlet"] == {"sangbadpratidin.in": 2} and r["outlets_down"] == ["mp"]
    assert all(set(x) == {"publisher", "link", "at"} for x in r["links"])  # no headline, no person


def test_kali_puja_night_drafts_from_moderate_and_names_the_smoke():
    from cityfeeds.proposals import festival_near
    air = {"city": {"aqi": 75, "band": "satisfactory", "band_en": "Satisfactory", "band_bn": "সন্তোষজনক", "band_hi": "संतोषजनक"},
           "next_48h_worst": {"naqi": {"aqi": 160, "band": "moderate", "band_en": "Moderate", "band_bn": "মাঝারি", "band_hi": "मध्यम"}},
           "naqi_source": {}}
    ordinary = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
    assert festival_near(ordinary) is None and "none" in air_advisory(air, ordinary, [])
    night = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)  # 17:30 IST, Kali Puja and Diwali
    assert festival_near(night)["date"] == "2026-11-08"
    p = air_advisory(air, night, ["LIVE", "MODELLED", "INDICATIVE"])
    _gate_ok(p)
    assert "firecracker smoke" in p["text"]["en"] and "বাজির ধোঁয়ায়" in p["text"]["bn"] and "पटाखों" in p["text"]["hi"]
    assert p["text"]["bn"].endswith("।") and p["basis"]["festival"]["en"] == "Kali Puja and Diwali"
