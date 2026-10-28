"""The city-feeds core: one polite fetcher, the per-feed views, the proposals and the god's-eye summary."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from cityfeeds import air_observed as obs
from cityfeeds.air import air_view, fetch_air
from cityfeeds.config import Settings
from cityfeeds.cyclones import cyclones_view, fetch_cyclones
from cityfeeds.fetch import Fetched, Fetcher, load_fixture
from cityfeeds.fires import fetch_fires_area, fetch_fires_public, fires_view
from cityfeeds.heat import fetch_heat, heat_view
from cityfeeds.keys import KEYED, key, keyed_state, redact
from cityfeeds.notices import fetch_notices, notices_view
from cityfeeds.street_image import StreetImages
from cityfeeds.proposals import air_advisory, cyclone_preposition, heat_shift
from cityfeeds.quakes import fetch_quakes, quakes_view
from cityfeeds.river import fetch_news, fetch_river, river_view
from cityfeeds.tide_table import fetch_hydro_tide, fetch_port_notices, tide_table_view

__all__ = ["CityFeeds"]


def _as_of(f: Fetched) -> str | None:
    return f.fetched_at.isoformat() if f.fetched_at else None


class CityFeeds:
    def __init__(self, s: Settings, fetcher: Fetcher | None = None, clock=None) -> None:
        self.s = s
        self.f = fetcher or Fetcher(offline=s.offline, timeout=s.http_timeout_sec, cache_scale=s.cache_scale)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._cwc_static: dict[str, Any] = {}
        self._street = StreetImages()
        self._street_error: str | None = None
        self._street_ok = False

    def now(self) -> datetime:
        return self._clock()

    @property
    def box(self) -> tuple[float, float, float, float]:
        s = self.s
        return (s.region_south, s.region_west, s.region_north, s.region_east)

    # ── raw fetches (cached, rate-limited; offline → recorded fixtures) ──
    async def _air(self, force=False) -> Fetched:
        return await self.f.get("air", lambda c: fetch_air(c, self.s.open_meteo_air_url), lambda: load_fixture("air.json"), force)

    async def _heat(self, force=False) -> Fetched:
        return await self.f.get("heat", lambda c: fetch_heat(c, self.s.open_meteo_forecast_url), lambda: load_fixture("heat.json"), force)

    async def _cyc(self, force=False) -> Fetched:
        return await self.f.get("cyclones", lambda c: fetch_cyclones(c, self.s.gdacs_list_url, self.s.gdacs_geometry_url, self.box),
                                lambda: load_fixture("gdacs.json"), force)

    async def _river(self, force=False) -> Fetched:
        return await self.f.get("river", lambda c: fetch_river(c, self.s.cwc_base_url, self._cwc_static),
                                lambda: load_fixture("cwc.json"), force)

    async def _news(self, force=False) -> Fetched:
        return await self.f.get("news", fetch_news, lambda: load_fixture("news.json"), force)

    async def _quakes(self, force=False) -> Fetched:
        return await self.f.get("quakes", lambda c: fetch_quakes(c, self.s.usgs_url, self.s.quake_radius_km),
                                lambda: load_fixture("usgs.json"), force)

    async def _notices(self, force=False) -> Fetched:
        return await self.f.get("notices", lambda c: fetch_notices(c, self.s.kmc_portal_url),
                                lambda: load_fixture("kmc_portal.html"), force)

    async def _tide(self, force=False) -> Fetched:
        return await self.f.get("hydro_tide", lambda c: fetch_hydro_tide(c, self.s.hydro_url),
                                lambda: load_fixture("hydro_tide.json"), force)

    async def _port(self, force=False) -> Fetched:
        return await self.f.get("port_tide", lambda c: fetch_port_notices(c, self.s.port_tide_url),
                                lambda: load_fixture("port_tidal_notices.json"), force)

    async def _ktp(self, force=False) -> Fetched:
        return await self.f.get("ktp", lambda c: fetch_notices(c, self.s.ktp_url),
                                lambda: load_fixture("ktp_home.html"), force)

    async def _fires(self, force=False) -> Fetched:
        mk = key("firms")
        fetch = (lambda c: fetch_fires_area(c, mk)) if mk else fetch_fires_public
        return await self.f.get("fires", fetch, lambda: load_fixture("firms_kma.json"), force)

    #: keyed air providers: (feed id, keyed source id, fetch, parse)
    _AIR_OBSERVED = (("air_cpcb", "cpcb", obs.fetch_cpcb, obs.parse_cpcb),
                     ("air_waqi", "waqi", obs.fetch_waqi, obs.parse_waqi),
                     ("air_openaq", "openaq", obs.fetch_openaq, obs.parse_openaq))

    async def _observed(self, force=False) -> dict[str, Any]:
        """Each keyed air provider: no key → no call ("needs <ENV>"); offline → no call (no recording exists)."""
        per: dict[str, dict[str, Any]] = {}
        providers: dict[str, Any] = {}
        calls = []
        for feed, src, fetch, parse in self._AIR_OBSERVED:
            k = key(src)
            if k is None or self.s.offline:
                providers[src] = {"state": keyed_state(src) if k is None else "offline: no call",
                                  "env": KEYED[src].env, "signup": KEYED[src].signup}
            else:
                calls.append((src, parse, self.f.get(feed, lambda c, _f=fetch, _k=k: _f(c, _k), lambda: None, force)))
        got = await asyncio.gather(*(c for _s, _p, c in calls))  # the keyed providers in parallel
        for (src, parse, _c), f in zip(calls, got):
            sites = parse(f.data) if f.ok else {}
            per[src] = sites
            providers[src] = {"state": keyed_state(src, error=f.error if not f.ok else None, live=f.ok),
                              "env": KEYED[src].env, "signup": KEYED[src].signup, "sites_matched": len(sites),
                              "fetched_at": _as_of(f), "stale": f.stale,
                              "error": redact(f.error) if f.error else None}
        return {"providers": dict(sorted(providers.items())), "sites": obs.match_stations(per)}

    def keyed_sources(self) -> dict[str, Any]:
        """Every keyed source and its state: ``live`` / ``needs <ENV>`` / ``error: <reason>`` (never the key)."""
        st = self.f.status()["feeds"]
        out: dict[str, Any] = {}
        for sid, ks in KEYED.items():
            feed = {"cpcb": "air_cpcb", "waqi": "air_waqi", "openaq": "air_openaq", "firms": "fires"}.get(sid)
            if sid == "mapillary":
                state = keyed_state(sid, error=self._street_error, live=self._street_ok)
            elif sid == "firms" and key(sid) is None:  # the public files need no key: say so, never "needs"
                fs = st.get("fires") or {}
                if fs.get("cache_age_sec") is not None:
                    state = "live (public files, no key; FIRMS_MAP_KEY optional)"
                elif fs.get("last_error"):
                    state = f"error: {redact(fs['last_error'])}"
                else:
                    state = "not read yet (public files, no key; FIRMS_MAP_KEY optional)"
            elif feed and key(sid) is not None:
                fs = st.get(feed) or {}
                state = keyed_state(sid, error=fs.get("last_error"), live=fs.get("cache_age_sec") is not None)
            else:
                state = keyed_state(sid)
            out[sid] = {"state": state, "env": ks.env, "what": ks.what, "signup": ks.signup,
                        "without_key": ks.without_key}
        return out

    # ── views ──
    def _labels(self, f: Fetched, *extra: str) -> list[str]:
        base = ["RECORDED"] if f.mode == "RECORDED" else ["LIVE"] if f.ok else ["UNAVAILABLE"]
        return base + list(extra)

    async def air(self, force=False) -> dict[str, Any]:
        f, o = await asyncio.gather(self._air(force), self._observed(force))
        now = self.now()
        v = air_view(f.data, now) if f.ok else {"label": "UNAVAILABLE", "stations": [], "city": None, "next_48h_worst": None}
        v["feed"] = f.meta()
        v["proposal"] = air_advisory(v, now, self._labels(f, "MODELLED", "INDICATIVE")) if f.ok else {"none": "air feed unavailable"}
        # OBSERVED beside MODELLED (additive): per site, each keyed provider's own measurement; none without a key
        for st in v.get("stations") or []:
            st["observed"] = o["sites"].get(st["id"])
        cpcb = {sid: x["cpcb"] for sid, x in o["sites"].items() if x.get("cpcb", {}).get("naqi")}
        worst = max(cpcb.items(), key=lambda kv: kv[1]["naqi"]["aqi"], default=None)
        v["observed"] = {
            "label": "OBSERVED" if o["sites"] else "NONE",
            "what": "the stations' own measurements from the keyed services (CPCB via data.gov.in, WAQI, OpenAQ); "
                    "without a key a provider makes no call and the values above stay MODELLED",
            "providers": o["providers"],
            "sites_observed": len(o["sites"]),
            "city_naqi": ({"aqi": worst[1]["naqi"]["aqi"], "band": worst[1]["naqi"]["band"], "site": worst[0],
                           "prominent": worst[1]["naqi"]["prominent"], "at": worst[1]["at"], "label": "OBSERVED",
                           "sub_label": "INDICATIVE",
                           "source": "CPCB CAAQMS station averages via data.gov.in; National AQI bands on PM2.5/PM10"}
                          if worst else None),
        }
        return v

    async def heat(self, force=False) -> dict[str, Any]:
        f = await self._heat(force)
        now = self.now()
        v = heat_view(f.data, now) if f.ok else {"label": "UNAVAILABLE", "points": [], "city": None}
        v["feed"] = f.meta()
        v["proposal"] = heat_shift(v, now, self._labels(f, "MODELLED")) if f.ok else {"none": "heat feed unavailable"}
        return v

    async def cyclones(self, force=False) -> dict[str, Any]:
        f = await self._cyc(force)
        now = self.now()
        v = cyclones_view(f.data, now) if f.ok else {"type": "FeatureCollection", "features": [], "label": "UNAVAILABLE",
                                                     "active": [], "floods": [], "nearest": None}
        v["feed"] = f.meta()
        v["proposal"] = cyclone_preposition(v, now, self._labels(f, "MODELLED")) if f.ok else {"none": "GDACS unavailable"}
        return v

    async def river(self, force=False) -> dict[str, Any]:
        f, n = await asyncio.gather(self._river(force), self._news(force))
        v = river_view(f.data if f.ok else None, n.data if n.ok else None, self.now())
        if not f.ok:
            v["label"] = "UNAVAILABLE"
        v["feed"] = f.meta()
        v["news_feed"] = n.meta()
        return v

    async def quakes(self, force=False) -> dict[str, Any]:
        f = await self._quakes(force)
        v = quakes_view(f.data if f.ok else None, self.s.quake_radius_km, self.now())
        if not f.ok:
            v["label"] = "UNAVAILABLE"
        v["feed"] = f.meta()
        return v

    async def tide_table(self, force=False) -> dict[str, Any]:
        f, p = await asyncio.gather(self._tide(force), self._port(force))
        v = tide_table_view(f.data if f.ok else None, f.error, p.data if p.ok else None, p.error, p.mode, _as_of(p))
        v["feed"] = f.meta()
        v["port_feed"] = p.meta()
        return v

    async def notices(self, force=False) -> dict[str, Any]:
        f, k = await asyncio.gather(self._notices(force), self._ktp(force))
        v = notices_view(f.data if f.ok else None, self.s.kmc_portal_url, ktp_page=k.data if k.ok else None,
                         ktp_error=k.error)
        v["feed"] = f.meta()
        v["ktp_feed"] = k.meta()
        return v

    async def fires(self, force=False) -> dict[str, Any]:
        f = await self._fires(force)
        v = fires_view(f.data if f.ok else None, self.now())
        v["feed"] = f.meta()
        v["key"] = self.keyed_sources()["firms"]
        return v

    async def street_image(self, lat: float, lon: float) -> dict[str, Any]:
        """The nearest public Mapillary photo to a point, or why there is none. Never calls the vision model."""
        base = {"lat": lat, "lon": lon, "source": "Mapillary (CC BY-SA 4.0)", "label": "Reference photo · not live"}
        tok = key("mapillary")
        if tok is None:
            return {**base, "state": keyed_state("mapillary"), "image": None, "signup": KEYED["mapillary"].signup}
        if self.s.offline:
            return {**base, "state": "offline: no call", "image": None}
        try:
            got = await self._street.near(self.f.client, tok, lat, lon)
        except Exception as exc:  # noqa: BLE001 — reported, never raised to the deck
            self._street_error = redact(f"{type(exc).__name__}: {exc}")[:160]
            return {**base, "state": keyed_state("mapillary", error=self._street_error), "image": None}
        self._street_error, self._street_ok = None, True
        return {**base, "state": "live", "image": got["image"], "cached": got["cached"], "searched_m": 60}

    async def proposals(self) -> dict[str, Any]:
        a, h, c = await asyncio.gather(self.air(), self.heat(), self.cyclones())
        out, none = [], {}
        for k, v in (("air", a), ("heat", h), ("cyclone", c)):
            p = v.get("proposal") or {}
            if "proposal_id" in p:
                out.append(p)
            else:
                none[k] = p.get("none")
        return {"proposals": out, "not_drafted": none, "generated_at": self.now().isoformat()}

    async def summary(self) -> dict[str, Any]:
        """One object for the god's-eye chips: value, band, label, source and as-of time per chip."""
        a, h, c, r, q, t = await asyncio.gather(self.air(), self.heat(), self.cyclones(), self.river(), self.quakes(),
                                                self.tide_table())
        chips: dict[str, Any] = {}
        city = a.get("city")
        chips["air"] = {
            "value": city["aqi"] if city else None, "unit": "AQI", "band": city["band"] if city else None,
            "label": "MODELLED" if city else "UNAVAILABLE", "sub_label": "INDICATIVE",
            "source": "Open-Meteo air-quality (CAMS model) · CPCB National AQI bands",
            "as_of": a["feed"]["fetched_at"], "mode": a["feed"]["mode"], "stale": a["feed"]["stale"],
            "detail": {k: city[k] for k in ("worst_site", "worst_site_name", "worst_site_bn", "prominent", "pm25_24h", "pm10_24h",
                                            "band_en", "band_bn", "band_hi")} if city else None,
            "next_48h": (a.get("next_48h_worst") or {}).get("naqi"),
            "proposal": "proposal_id" in (a.get("proposal") or {}),
        }
        hc = h.get("city")
        chips["heat"] = {
            "value": hc["heat_index"] if hc else None, "unit": "°C", "band": hc["band"] if hc else None,
            "label": "MODELLED" if hc else "UNAVAILABLE", "source": "Open-Meteo forecast · NWS heat index · IMD heatwave criteria",
            "as_of": h["feed"]["fetched_at"], "mode": h["feed"]["mode"], "stale": h["feed"]["stale"],
            "detail": {"temp": hc["temp"], "rh": hc["rh"], "apparent": hc["apparent"], "peak_48h": h.get("peak_48h"),
                       "imd_heatwave_days": len(h.get("imd_heatwave_days") or []), "in_season": h.get("in_season")} if hc else None,
            "proposal": "proposal_id" in (h.get("proposal") or {}),
        }
        n = c.get("nearest")
        chips["cyclone"] = {
            "value": n["name"] if n else None, "unit": None, "band": n["alertlevel"] if n else ("none" if c["label"] != "UNAVAILABLE" else None),
            "label": c["label"], "source": "GDACS (EC JRC and UN OCHA)",
            "as_of": c["feed"]["fetched_at"], "mode": c["feed"]["mode"], "stale": c["feed"]["stale"],
            "detail": {"distance_km": n["distance_km"], "bearing": n["bearing"], "closest_km": (n.get("closest_approach") or {}).get("distance_km"),
                       "in_wind_buffer_kmh": n.get("kolkata_in_wind_buffer_kmh"), "severity": n.get("severity"),
                       "active": len(c.get("active") or [])} if n else {"active": 0},
            "proposal": "proposal_id" in (c.get("proposal") or {}),
        }
        key = next((s for s in r["stations"] if s.get("code") == "015-DDASL"), None)
        chips["river"] = {
            "value": r.get("above_warning") if r["label"] != "UNAVAILABLE" else None, "unit": "above warning",
            "band": r.get("status"), "label": r["label"], "source": "CWC flood forecasting (observed levels) · news mentions",
            "as_of": r["feed"]["fetched_at"], "mode": r["feed"]["mode"], "stale": r["feed"]["stale"],
            "detail": {"stations_read": r.get("stations_read"), "dvc_news_mentions_72h": r["dvc_news"].get("mentions"),
                       "key_station": {k: key.get(k) for k in ("name", "level_m", "warning_m", "danger_m", "to_warning_m", "trend")} if key and key.get("level_m") is not None else None},
        }
        chips["quake"] = {
            "value": q.get("count_30d") if q["label"] != "UNAVAILABLE" else None, "unit": "in 30 days",
            "band": ("recent" if q.get("count_30d") else "quiet") if q["label"] != "UNAVAILABLE" else None,
            "label": q["label"], "source": "USGS earthquake catalogue (500 km)",
            "as_of": q["feed"]["fetched_at"], "mode": q["feed"]["mode"], "stale": q["feed"]["stale"],
            "detail": {"latest": q.get("latest"), "count_365d": q.get("count_365d")},
        }
        nxt = next((e for e in t["modelled"]["highs_lows"] if e["kind"] == "high" and e["at"] >= self.now().isoformat()), None)
        pub = t["published"]
        chips["tide"] = {
            "value": nxt["level_m"] if nxt else None, "unit": "m",
            "band": "published_linked" if pub["label"] == "LINKED" else "published_unavailable",
            "label": "MODELLED" if nxt else "UNAVAILABLE",
            "source": "hydro tide model (Garden Reach); port table " + (
                "linked, not parsed" if pub["label"] == "LINKED" else f"not readable ({pub.get('result', '')[:90]})"),
            "as_of": t["feed"]["fetched_at"], "mode": t["feed"]["mode"], "stale": t["feed"]["stale"],
            "detail": {"next_high_at": nxt["at"] if nxt else None, "published": pub["label"],
                       "published_status": pub.get("status"), "published_checked_at": pub.get("checked_at")},
        }
        # additive: OBSERVED air beside the modelled chip (null until a keyed provider answers)
        chips["air"]["observed"] = (a.get("observed") or {}).get("city_naqi")
        return {"generated_at": self.now().isoformat(), "city": "kolkata", "chips": chips,
                "keyed_sources": {k: v["state"] for k, v in self.keyed_sources().items()}}

    async def warm(self) -> None:
        """Fill every cache once at start-up (never in offline mode), so the first deck poll is fast."""
        if self.s.offline:
            return
        try:
            await self.summary()
            await self.notices()
            await self.fires()
        except Exception:  # noqa: BLE001 — a warm-up failure is just a cold cache
            pass

    async def keep_fresh(self, every_sec: float = 60.0) -> None:
        """Touch every feed once a minute: an expired cache starts its own background refresh (inside its limits),
        so a deck request never waits on an upstream."""
        if self.s.offline:
            return
        while True:
            await self.warm()
            await asyncio.sleep(every_sec)
