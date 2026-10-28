"""Every route, offline on the fixtures recorded 28 Oct 2026 (no network)."""

import re

CHIPS = {"air", "heat", "cyclone", "river", "quake", "tide"}
LABELS = {"LIVE", "MODELLED", "EMULATED", "UNAVAILABLE"}


def test_health(client):
    h = client.get("/health").json()
    assert h["status"] == "ok" and h["offline"] is True and set(h["fetcher"]["feeds"]) >= {"air", "cyclones", "river"}


def test_summary_chips_are_complete_and_labelled(client):
    s = client.get("/feeds/summary").json()
    assert set(s["chips"]) == CHIPS
    for k, c in s["chips"].items():
        assert c["label"] in LABELS, k
        assert c["source"] and c["mode"] == "RECORDED"
        assert {"value", "band", "as_of"} <= set(c)
    air = s["chips"]["air"]
    assert air["unit"] == "AQI" and air["band"] == "satisfactory" and air["sub_label"] == "INDICATIVE"
    assert s["chips"]["cyclone"]["value"] == "ARNAB-26" and s["chips"]["cyclone"]["band"] == "red"
    assert s["chips"]["river"]["value"] == 0 and s["chips"]["river"]["detail"]["stations_read"] == 8
    assert s["chips"]["tide"]["detail"]["published"] == "UNAVAILABLE"


def test_air_sites_and_bands(client):
    a = client.get("/feeds/air").json()
    assert len(a["stations"]) == 10 and a["label"] == "MODELLED" and a["feed_label"] == "LIVE"
    assert {s["id"] for s in a["stations"]} >= {"victoria_memorial", "ghusuri", "belur_math", "padmapukur"}
    for s in a["stations"]:
        assert s["coord_source"] and s["naqi"]["label"] == "INDICATIVE" and len(s["forecast"]) == 2
    assert a["grid_cells"] >= 1
    assert "not an official CPCB AQI" in a["naqi_label"] and a["naqi_source"]["url"].startswith("https://cpcb.nic.in")
    assert "none" in a["proposal"]  # Satisfactory on the recorded day: no draft, and it says why


def test_heat(client):
    h = client.get("/feeds/heat").json()
    assert [p["id"] for p in h["points"]] == ["alipore", "dum_dum"]
    assert h["in_season"] is False and h["sources"]["imd"]["url"].endswith(".pdf")
    assert "none" in h["proposal"]


def test_cyclones_geojson(client):
    c = client.get("/feeds/cyclones").json()
    assert c["type"] == "FeatureCollection"
    kinds = {f["properties"]["kind"] for f in c["features"]}
    assert {"track", "position", "wind_buffer", "cone"} <= kinds
    for f in c["features"]:
        assert f["geometry"]["type"] in ("Point", "LineString", "Polygon")
    n = c["nearest"]
    assert n["name"] == "ARNAB-26" and 900 < n["distance_km"] < 1100 and n["bearing"] in ("SW", "WSW", "SSW")
    assert n["kolkata_in_wind_buffer_kmh"] is None and "too" not in c["proposal"].get("none", "")


def test_river(client):
    r = client.get("/feeds/river").json()
    assert r["label"] == "LIVE" and len(r["stations"]) == 8
    hk = next(s for s in r["stations"] if s["code"] == "015-DDASL")
    assert hk["warning_m"] == 11.8 and hk["danger_m"] == 12.8 and hk["status"] == "normal"
    assert r["dvc_news"]["label"] == "AGGREGATE" and r["dvc_news"]["mentions"] == 0
    assert "release" in r["release_note"]


def test_quakes(client):
    q = client.get("/feeds/quakes").json()
    assert q["count_30d"] == 0 and q["count_365d"] >= 1
    assert all(f["properties"]["distance_km"] <= 500 for f in q["features"])


def test_tide_table_is_honest(client):
    t = client.get("/feeds/tide-table").json()
    assert t["published"]["label"] == "UNAVAILABLE" and t["published"]["highs_lows"] == []
    assert t["modelled"]["label"] == "MODELLED" and t["modelled"]["highs_lows"]


def test_notices_are_about_places_never_people(client):
    n = client.get("/feeds/notices").json()
    assert n["items"]
    bad = re.compile(r"hearing|death|harassment|mutation|councillor|ex-gratia", re.I)
    for it in n["items"]:
        assert not bad.search(it["title"]) and it["link"].startswith("https://www.kmcgov.in/")
    assert any("dropped" in s["status"] for s in n["sources"])


def test_proposals_route_explains_what_it_did_not_draft(client):
    p = client.get("/feeds/proposals").json()
    assert p["proposals"] == [] and set(p["not_drafted"]) == {"air", "heat", "cyclone"}
