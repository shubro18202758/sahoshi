"""The sources added on 29 Oct 2026, offline: keyed air (CPCB/data.gov.in, WAQI, OpenAQ), NASA FIRMS, Mapillary,
the port's tide notices over the pinned connection and the Kolkata Traffic Police advisories. No socket is opened:
every exchange is an ``httpx.MockTransport``; keys are fake values set in the test's environment only."""

from __future__ import annotations

import hashlib
import json
import ssl
import time
from pathlib import Path

import httpx
import pytest
from conftest import NOW

from cityfeeds import tls
from cityfeeds.config import Settings
from cityfeeds.fetch import Fetcher, load_fixture
from cityfeeds.fires import KMA_BBOX, parse_csv
from cityfeeds.keys import KEYED, redact
from cityfeeds.notices import ktp_advisories
from cityfeeds.service import CityFeeds

FX = Path(__file__).resolve().parent / "fixtures"
FAKE = {"DATA_GOV_IN_API_KEY": "fake-dgi-key-0001", "WAQI_TOKEN": "fake-waqi-token-0002",
        "OPENAQ_API_KEY": "fake-openaq-key-0003", "FIRMS_MAP_KEY": "fakefirmskey0004",
        "MAPILLARY_TOKEN": "MLY|fake|token0005"}
KEYED_HOSTS = {"api.data.gov.in", "api.waqi.info", "api.openaq.org", "graph.mapillary.com"}


def _j(name: str):
    return json.loads((FX / name).read_text(encoding="utf-8"))


class Upstream:
    """Answers like each service would; records every request."""

    def __init__(self, port_status: int = 404, port_page: str = "No Such URL.") -> None:
        self.requests: list[httpx.Request] = []
        self.port_status, self.port_page = port_status, port_page
        self.fail: set[str] = set()

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.requests.append(req)
        host, path = req.url.host, req.url.path
        if host in self.fail:
            return httpx.Response(403, json={"status": "error", "data": "Invalid key"})
        if host == "air-quality-api.open-meteo.com":
            return httpx.Response(200, json=load_fixture("air.json"))
        if host == "api.data.gov.in":
            city = req.url.params.get("filters[city]")
            return httpx.Response(200, json=_j("cpcb_kolkata.json" if city == "Kolkata" else "cpcb_howrah.json"))
        if host == "api.waqi.info":
            return httpx.Response(200, json=_j("waqi_bounds.json"))
        if host == "api.openaq.org":
            if path == "/v3/locations":
                return httpx.Response(200, json=_j("openaq_locations.json"))
            if path == "/v3/locations/5001/latest":
                return httpx.Response(200, json=_j("openaq_latest_5001.json"))
        if host == "firms.modaps.eosdis.nasa.gov":
            modis = "MODIS" in path
            return httpx.Response(200, text=(FX / ("firms_modis.csv" if modis else "firms_area.csv")).read_text())
        if host == "graph.mapillary.com":
            return httpx.Response(200, json=_j("mapillary_images.json"))
        if host == "smp.smportkolkata.in":
            return httpx.Response(self.port_status, text=self.port_page)
        if host == "kolkatatrafficpolice.gov.in":
            return httpx.Response(200, text=load_fixture("ktp_home.html"))
        return httpx.Response(404, text="no route in the test double")

    def to(self, host: str) -> list[httpx.Request]:
        return [r for r in self.requests if r.url.host == host]


@pytest.fixture
def upstream() -> Upstream:
    return Upstream()


@pytest.fixture
def live(upstream, monkeypatch):
    for env in FAKE:
        monkeypatch.delenv(env, raising=False)
    cf = CityFeeds(Settings(offline=False), fetcher=Fetcher(transport=httpx.MockTransport(upstream)), clock=lambda: NOW)
    yield cf


def _keys(monkeypatch, *envs: str) -> None:
    for e in envs:
        monkeypatch.setenv(e, FAKE[e])


def _no_key_anywhere(obj) -> None:
    text = json.dumps(obj, ensure_ascii=False, default=str)
    for v in FAKE.values():
        assert v not in text


# ── without keys: no call, and every keyed source says what it needs ─────────────────────────────────────────────


async def test_without_keys_nothing_keyed_is_called_and_each_says_what_it_needs(live, upstream):
    a = await live.air()
    ks = live.keyed_sources()
    assert {k: v["state"] for k, v in ks.items()} == {
        "waqi": "needs WAQI_TOKEN", "openaq": "needs OPENAQ_API_KEY", "cpcb": "needs DATA_GOV_IN_API_KEY",
        "firms": "not read yet (public files, no key; FIRMS_MAP_KEY optional)", "mapillary": "needs MAPILLARY_TOKEN"}
    assert all(v["signup"].startswith("https://") for v in ks.values())
    assert ks["firms"]["without_key"] and "public" in ks["firms"]["without_key"]
    assert a["label"] == "MODELLED" and a["observed"]["label"] == "NONE" and a["observed"]["city_naqi"] is None
    assert {p["state"] for p in a["observed"]["providers"].values()} == {
        "needs DATA_GOV_IN_API_KEY", "needs WAQI_TOKEN", "needs OPENAQ_API_KEY"}
    assert all(s["observed"] is None for s in a["stations"])
    img = await live.street_image(22.5646, 88.3512)
    assert img["state"] == "needs MAPILLARY_TOKEN" and img["image"] is None
    assert not KEYED_HOSTS & {r.url.host for r in upstream.requests}
    s = await live.summary()
    assert s["keyed_sources"]["cpcb"] == "needs DATA_GOV_IN_API_KEY" and s["chips"]["air"]["observed"] is None
    assert s["chips"]["air"]["label"] == "MODELLED"  # unchanged contract
    await live.f.aclose()


# ── observed air ──────────────────────────────────────────────────────────────────────────────────────────────────


async def test_cpcb_observed_values_sit_beside_the_modelled_ones(live, upstream, monkeypatch):
    _keys(monkeypatch, "DATA_GOV_IN_API_KEY")
    a = await live.air()
    vm = next(s for s in a["stations"] if s["id"] == "victoria_memorial")
    o = vm["observed"]["cpcb"]
    assert o["label"] == "OBSERVED" and o["upstream_name"] == "Victoria, Kolkata - WBPCB"
    assert o["pm25"] == 74 and o["pm10"] == 118 and o["naqi"]["band"] == "moderate" and o["at_tz"] == "IST"
    assert vm["naqi"]["label"] == "INDICATIVE" and a["label"] == "MODELLED"  # the modelled values stay as they are
    gh = next(s for s in a["stations"] if s["id"] == "ghusuri")["observed"]["cpcb"]
    assert gh["pm25"] == 101 and gh["naqi"]["band"] == "poor"  # the pollutant_avg spelling is read too
    city = a["observed"]["city_naqi"]
    assert city["site"] == "ghusuri" and city["label"] == "OBSERVED" and city["sub_label"] == "INDICATIVE"
    assert a["observed"]["providers"]["cpcb"]["state"] == "live"
    sent = upstream.to("api.data.gov.in")
    assert {r.url.params["filters[city]"] for r in sent} == {"Kolkata", "Howrah"}
    s = await live.summary()
    assert s["chips"]["air"]["observed"]["aqi"] == city["aqi"] and s["keyed_sources"]["cpcb"] == "live"
    _no_key_anywhere(s)
    _no_key_anywhere(a)
    await live.f.aclose()


async def test_waqi_and_openaq_are_matched_to_the_sites(live, upstream, monkeypatch):
    _keys(monkeypatch, "WAQI_TOKEN", "OPENAQ_API_KEY")
    a = await live.air()
    by = {s["id"]: s["observed"] for s in a["stations"]}
    assert by["victoria_memorial"]["waqi"]["waqi_aqi"] == 152 and by["victoria_memorial"]["waqi"]["scale"].startswith("US EPA")
    assert by["rabindra_sarobar"]["waqi"]["waqi_aqi"] == 88
    assert by["rabindra_bharati"] is None  # WAQI's "-" is no value, never a zero
    fw = by["fort_william"]["openaq"]
    assert fw["pm25_latest"] == 63.4 and fw["pm10_latest"] == 101.2 and "no AQI" in fw["averaging"]
    assert a["observed"]["city_naqi"] is None  # WAQI and OpenAQ never stand in for the National AQI
    oq = upstream.to("api.openaq.org")
    assert oq and all(r.headers["x-api-key"] == FAKE["OPENAQ_API_KEY"] for r in oq)
    assert all(FAKE["OPENAQ_API_KEY"] not in str(r.url) for r in oq)  # a header, never the URL
    _no_key_anywhere(a)
    await live.f.aclose()


async def test_a_refused_key_is_reported_without_the_key(live, upstream, monkeypatch):
    _keys(monkeypatch, "WAQI_TOKEN")
    upstream.fail.add("api.waqi.info")
    a = await live.air()
    st = a["observed"]["providers"]["waqi"]["state"]
    assert st.startswith("error: ") and "403" in st
    assert live.keyed_sources()["waqi"]["state"].startswith("error: ")
    _no_key_anywhere(a)
    _no_key_anywhere(live.f.status())
    await live.f.aclose()


def test_redact_scrubs_keys_and_query_strings(monkeypatch):
    _keys(monkeypatch, "WAQI_TOKEN", "FIRMS_MAP_KEY")
    msg = ("Client error '403' for url 'https://api.waqi.info/v2/map/bounds?latlng=1&token=fake-waqi-token-0002' "
           "and https://firms.modaps.eosdis.nasa.gov/api/area/csv/fakefirmskey0004/VIIRS_SNPP_NRT/1,2,3,4/2")
    out = redact(msg)
    assert "fake-waqi-token-0002" not in out and "fakefirmskey0004" not in out
    assert "<FIRMS_MAP_KEY>" in out and "?…" in out


# ── NASA FIRMS ────────────────────────────────────────────────────────────────────────────────────────────────────


def test_firms_rows_are_kept_to_the_metro_box():
    rows = parse_csv((FX / "firms_area.csv").read_text(), "VIIRS S-NPP")
    assert len(rows) == 2 and all(KMA_BBOX[0] <= r["lat"] <= KMA_BBOX[2] for r in rows)
    assert rows[0]["at"] == "2026-10-28T07:45:00+00:00" and rows[0]["frp_mw"] == 4.6 and rows[1]["daynight"] == "N"


async def test_firms_is_live_without_a_key_from_the_public_files(live, upstream):
    f = await live.fires()
    assert f["label"] == "LIVE" and f["route"].startswith("public") and f["window_h"] == 24
    assert set(f["files"].values()) == {"read"}
    assert f["count"] == 3 * 2 + 1  # three VIIRS files with two in-box rows each, one MODIS row
    for feat in f["features"]:
        p = feat["properties"]
        assert p["kind"] == "hotspot" and "not a confirmed fire" in p["note"] and feat["geometry"]["type"] == "Point"
        assert not {"name", "person", "owner"} & set(p)
    paths = [r.url.path for r in upstream.to("firms.modaps.eosdis.nasa.gov")]
    assert all(p.startswith("/data/active_fire/") and p.endswith("_South_Asia_24h.csv") for p in paths)
    assert f["key"]["state"] == "live (public files, no key; FIRMS_MAP_KEY optional)"
    await live.f.aclose()


async def test_firms_uses_the_area_api_with_a_key_and_never_shows_it(live, upstream, monkeypatch):
    _keys(monkeypatch, "FIRMS_MAP_KEY")
    f = await live.fires()
    paths = [r.url.path for r in upstream.to("firms.modaps.eosdis.nasa.gov")]
    assert paths and all(p.startswith(f"/api/area/csv/{FAKE['FIRMS_MAP_KEY']}/") and p.endswith("/2") for p in paths)
    assert f["route"].startswith("FIRMS area API") and f["window_h"] == 48 and f["key"]["state"] == "live"
    _no_key_anywhere(f)
    await live.f.aclose()


# ── Mapillary ─────────────────────────────────────────────────────────────────────────────────────────────────────


async def test_mapillary_returns_the_nearest_still_with_its_licence(live, upstream, monkeypatch):
    _keys(monkeypatch, "MAPILLARY_TOKEN")
    r = await live.street_image(22.5646, 88.3512)
    im = r["image"]
    assert r["state"] == "live" and im["id"] == "333" and im["distance_m"] < 15  # the panorama is skipped
    assert im["label"] == "Reference photo · not live" and "CC BY-SA 4.0" in im["attribution"]
    assert im["page_url"] == "https://www.mapillary.com/app/?pKey=333" and im["captured_at"].startswith("2024-07-03")
    sent = upstream.to("graph.mapillary.com")
    assert len(sent) == 1 and sent[0].headers["authorization"] == f"OAuth {FAKE['MAPILLARY_TOKEN']}"
    assert "access_token" not in str(sent[0].url) and "creator" not in sent[0].url.params["fields"]
    again = await live.street_image(22.5646, 88.3512)
    assert again["cached"] is True and len(upstream.to("graph.mapillary.com")) == 1
    assert live.keyed_sources()["mapillary"]["state"] == "live"
    _no_key_anywhere(r)
    await live.f.aclose()


# ── the port's tide notices (pinned) and the traffic police advisories ────────────────────────────────────────────


async def test_the_port_answer_is_reported_as_it_is(live, upstream):
    t = await live.tide_table()
    p = t["published"]
    assert p["label"] == "UNAVAILABLE" and p["status"] == 404 and '"No Such URL."' in p["result"]
    assert "pinned certificate" in p["result"] and t["modelled"]["label"] == "MODELLED"
    assert t["port_feed"]["mode"] == "LIVE"
    await live.f.aclose()


async def test_a_port_page_with_notices_is_linked_never_parsed_into_heights(monkeypatch):
    page = ('<ul><li><a href="/smpk/en/showfile.php?lid=9001">Tide Table 2027 (Garden Reach)</a></li>'
            '<!-- <li><a href="/old.pdf">Tide Table 2019</a></li> -->'
            '<li><a href="/smpk/en/feedback/">Feedback</a></li></ul>')
    up = Upstream(port_status=200, port_page=page)
    cf = CityFeeds(Settings(offline=False), fetcher=Fetcher(transport=httpx.MockTransport(up)), clock=lambda: NOW)
    t = await cf.tide_table()
    p = t["published"]
    assert p["label"] == "LINKED" and p["highs_lows"] == []
    assert [n["title"] for n in p["notices"]] == ["Tide Table 2027 (Garden Reach)"]
    s = await cf.summary()
    assert s["chips"]["tide"]["band"] == "published_linked" and s["chips"]["tide"]["detail"]["published"] == "LINKED"
    await cf.f.aclose()


def test_traffic_police_advisories_are_current_and_never_the_menu():
    items = ktp_advisories(load_fixture("ktp_home.html"))
    titles = [i["title"] for i in items]
    assert "Notification for Traffic Diversion at Picnic Garden Road under Tiljala Traffic Guard." in titles
    assert any("Kona Expressway" in t for t in titles)
    assert not any(t.startswith(("Traffic Enforcement Policy", "Mandatory", "Traffic Restrictions")) for t in titles)
    assert all(i["link"].startswith("https://kolkatatrafficpolice.gov.in/") and i["label"] == "LIVE" for i in items)
    withdrawn = '<!-- <a href="/TA_old.pdf">Traffic advisory in connection with closure of an old flyover.</a> -->'
    assert ktp_advisories(withdrawn) == []


# ── TLS: the two narrow exceptions ────────────────────────────────────────────────────────────────────────────────


def test_the_port_pin_is_the_recorded_certificate():
    der = ssl.PEM_cert_to_DER_cert((FX / "smp_leaf.pem").read_text())
    assert hashlib.sha256(der).hexdigest() == tls.PORT_CERT_SHA256
    assert tls.pinned_ok(der, {}) is True
    other = b"another certificate"
    expired = {"notBefore": "Oct 18 10:48:48 2025 GMT", "notAfter": "Oct 17 06:34:12 2026 GMT"}
    assert tls.pinned_ok(other, expired) is False  # expired and not the pinned one: refused
    valid = {"notBefore": "Oct 18 00:00:00 2026 GMT", "notAfter": "Oct 18 00:00:00 2027 GMT"}
    assert tls.pinned_ok(other, valid, now=time.mktime((2026, 10, 29, 0, 0, 0, 0, 0, 0))) is True  # renewed
    assert tls.pinned_ok(None, None) is False


def test_the_exceptions_keep_verification_on():
    port, police = tls.port_context(), tls.police_context()
    for ctx in (port, police):
        assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname is True
    assert port.verify_flags & 0x200000  # dates not checked, for the pinned host only
    assert police.options & ssl.OP_LEGACY_SERVER_CONNECT and not port.options & ssl.OP_LEGACY_SERVER_CONNECT
    assert not police.verify_flags & 0x200000
    assert tls.PORT_HOST == "smp.smportkolkata.in" and tls.POLICE_HOST == "kolkatatrafficpolice.gov.in"


def test_every_keyed_source_names_its_env_var_and_signup():
    assert {k.env for k in KEYED.values()} == set(FAKE)
    for k in KEYED.values():
        assert k.signup.startswith("https://") and k.what
