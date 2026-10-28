"""OBSERVED air quality at the Kolkata and Howrah monitoring stations, from three free keyed services.

The air layer's own values (``air.py``) are the CAMS model's, labelled MODELLED. When any of the services below has
its key, the stations' own measurements are added beside them, labelled OBSERVED, matched to the ten sites in
``air.STATIONS`` by distance (within :data:`MATCH_KM`) or by name. Without a key a service makes no call and says
``needs <ENV_VAR>``; the modelled values stay as they are, labelled MODELLED.

* **CPCB via data.gov.in** (``DATA_GOV_IN_API_KEY``; resource ``3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69``, "Real time
  Air Quality Index from various locations"). One row per station and pollutant with ``avg_value`` (the CPCB
  bulletin's average), ``min_value``, ``max_value`` and ``last_update`` (IST). PM2.5 and PM10 averages give the
  National AQI here with the same breakpoints as ``air.naqi`` (still only two pollutants, so INDICATIVE).
* **WAQI** (``WAQI_TOKEN``; ``/v2/map/bounds``): the World Air Quality Index project's AQI per station, on the US
  EPA scale WAQI publishes. Shown as WAQI's number, never as the National AQI.
* **OpenAQ v3** (``OPENAQ_API_KEY``, sent as the ``X-API-Key`` header): the stations in the box
  (``/v3/locations?bbox=``) and each one's latest PM2.5 and PM10 (``/v3/locations/{id}/latest``): hourly
  concentrations, not 24-hour means, so no AQI is computed from them.

Every value is the station's own reported number with its time; nothing is interpolated or invented.
"""

from __future__ import annotations

import re
from typing import Any

import httpx

from cityfeeds.air import STATIONS, naqi
from cityfeeds.geo import haversine_km

__all__ = ["CPCB_URL", "WAQI_URL", "OPENAQ_URL", "MATCH_KM", "BOX", "fetch_cpcb", "fetch_waqi", "fetch_openaq",
           "parse_cpcb", "parse_waqi", "parse_openaq", "match_stations"]

CPCB_URL = "https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
WAQI_URL = "https://api.waqi.info/v2/map/bounds"
OPENAQ_URL = "https://api.openaq.org/v3"
#: an upstream station within this distance of a site is that site (the sites' own coordinates are ±1 km)
MATCH_KM = 2.0
#: (south, west, north, east) around Kolkata and Howrah
BOX = (22.40, 88.20, 22.75, 88.55)
_MAX_OPENAQ_LOCATIONS = 20


def _num(x: Any) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None  # NaN → None


def _norm(s: str) -> str:
    return re.sub(r"[^a-z]", "", s.lower())


#: words in an upstream station name that identify a site (CPCB writes "Victoria, Kolkata - WBPCB")
_NAME_KEYS = {
    "victoria_memorial": ("victoria",), "rabindra_bharati": ("rabindrabharati",), "ballygunge": ("ballygunge",),
    "fort_william": ("fortwilliam",), "jadavpur": ("jadavpur",), "bidhannagar": ("bidhannagar", "saltlake"),
    "rabindra_sarobar": ("rabindrasarobar",), "ghusuri": ("ghusuri",), "padmapukur": ("padmapukur",),
    "belur_math": ("belurmath",),
}


def _site_for(name: str, lat: float | None, lon: float | None) -> tuple[str | None, float | None]:
    """The site an upstream station is (by name first, then by distance), with the distance when known."""
    n = _norm(name or "")
    by_name = next((sid for sid, keys in _NAME_KEYS.items() if any(k in n for k in keys)), None)
    dist = {s["id"]: haversine_km(lat, lon, s["lat"], s["lon"]) for s in STATIONS} if (
        lat is not None and lon is not None) else {}
    if by_name:
        return by_name, (round(dist[by_name], 2) if by_name in dist else None)
    if dist:
        sid = min(dist, key=dist.get)
        if dist[sid] <= MATCH_KM:
            return sid, round(dist[sid], 2)
    return None, None


# ── CPCB (data.gov.in) ──────────────────────────────────────────────────────────────────────────────────────────


async def fetch_cpcb(client: httpx.AsyncClient, api_key: str) -> dict[str, Any]:
    out: list[dict[str, Any]] = []
    for city in ("Kolkata", "Howrah"):
        r = await client.get(CPCB_URL, params={"api-key": api_key, "format": "json", "limit": 500,
                                               "filters[city]": city})
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code} from data.gov.in")
        body = r.json()
        if not isinstance(body, dict) or not isinstance(body.get("records"), list):
            raise RuntimeError("data.gov.in answered without records")
        out += body["records"]
    return {"records": out}


def parse_cpcb(raw: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Per site: the CPCB station's pollutant averages, its time and the indicative National AQI from PM."""
    by_station: dict[str, dict[str, Any]] = {}
    for rec in (raw or {}).get("records") or []:
        if not isinstance(rec, dict):
            continue
        name = str(rec.get("station") or "")
        st = by_station.setdefault(name, {"name": name, "lat": _num(rec.get("latitude")),
                                          "lon": _num(rec.get("longitude")), "at": rec.get("last_update"),
                                          "pollutants": {}})
        pid = str(rec.get("pollutant_id") or "").upper().replace(".", "")
        # the resource has used both spellings: avg_value / pollutant_avg (min, max likewise)
        st["pollutants"][pid] = {k: _num(rec.get(f"{k}_value", rec.get(f"pollutant_{k}"))) for k in ("avg", "min", "max")}
    sites: dict[str, dict[str, Any]] = {}
    for st in by_station.values():
        sid, dist = _site_for(st["name"], st["lat"], st["lon"])
        if sid is None:
            continue
        pm25 = (st["pollutants"].get("PM25") or {}).get("avg")
        pm10 = (st["pollutants"].get("PM10") or {}).get("avg")
        sites[sid] = {"provider": "cpcb", "label": "OBSERVED", "upstream_name": st["name"], "distance_km": dist,
                      "at": st["at"], "at_tz": "IST", "pm25": pm25, "pm10": pm10,
                      "pollutants": st["pollutants"], "naqi": naqi(pm25, pm10),
                      "source": "CPCB CAAQMS via data.gov.in (station averages as CPCB publishes them)"}
    return sites


# ── WAQI ────────────────────────────────────────────────────────────────────────────────────────────────────────


async def fetch_waqi(client: httpx.AsyncClient, token: str) -> dict[str, Any]:
    s, w, n, e = BOX
    r = await client.get(WAQI_URL, params={"latlng": f"{s},{w},{n},{e}", "networks": "all", "token": token})
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code} from WAQI")
    body = r.json()
    if not isinstance(body, dict) or body.get("status") != "ok":
        raise RuntimeError(f"WAQI: {str((body or {}).get('data') if isinstance(body, dict) else body)[:60]}")
    return body


def parse_waqi(raw: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    sites: dict[str, dict[str, Any]] = {}
    for st in (raw or {}).get("data") or []:
        if not isinstance(st, dict):
            continue
        aqi = _num(st.get("aqi"))  # WAQI writes "-" for a station with no current value
        info = st.get("station") or {}
        sid, dist = _site_for(str(info.get("name") or ""), _num(st.get("lat")), _num(st.get("lon")))
        if sid is None or aqi is None:
            continue
        sites[sid] = {"provider": "waqi", "label": "OBSERVED", "upstream_name": str(info.get("name") or "")[:120],
                      "distance_km": dist, "at": info.get("time"), "waqi_aqi": int(aqi), "scale": "US EPA (WAQI)",
                      "source": "World Air Quality Index project (aqicn.org), from the CPCB/WBPCB station"}
    return sites


# ── OpenAQ v3 ───────────────────────────────────────────────────────────────────────────────────────────────────


async def fetch_openaq(client: httpx.AsyncClient, api_key: str) -> dict[str, Any]:
    h = {"X-API-Key": api_key}
    s, w, n, e = BOX
    r = await client.get(f"{OPENAQ_URL}/locations", params={"bbox": f"{w},{s},{e},{n}", "limit": 100}, headers=h)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code} from OpenAQ")
    locs = [loc for loc in (r.json().get("results") or []) if isinstance(loc, dict)]
    wanted = []
    for loc in locs:
        c = loc.get("coordinates") or {}
        sid, _d = _site_for(str(loc.get("name") or ""), _num(c.get("latitude")), _num(c.get("longitude")))
        if sid is not None:
            wanted.append(loc)
    latest = {}
    for loc in wanted[:_MAX_OPENAQ_LOCATIONS]:
        lr = await client.get(f"{OPENAQ_URL}/locations/{int(loc['id'])}/latest", headers=h)
        if lr.status_code == 200:
            latest[str(loc["id"])] = lr.json().get("results") or []
    return {"locations": wanted, "latest": latest}


def parse_openaq(raw: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    sites: dict[str, dict[str, Any]] = {}
    for loc in (raw or {}).get("locations") or []:
        c = loc.get("coordinates") or {}
        sid, dist = _site_for(str(loc.get("name") or ""), _num(c.get("latitude")), _num(c.get("longitude")))
        if sid is None:
            continue
        # sensor id → parameter name (pm25, pm10, …) from the location's own sensor list
        params = {str(s.get("id")): str((s.get("parameter") or {}).get("name") or "")
                  for s in loc.get("sensors") or [] if isinstance(s, dict)}
        vals: dict[str, Any] = {}
        at = None
        for m in (raw or {}).get("latest", {}).get(str(loc.get("id")), []):
            p = params.get(str(m.get("sensorsId")))
            if p in ("pm25", "pm10") and _num(m.get("value")) is not None:
                vals[p] = round(float(m["value"]), 1)
                t = (m.get("datetime") or {}).get("utc")
                at = max(at, t) if (at and t) else (t or at)
        if not vals:
            continue
        sites[sid] = {"provider": "openaq", "label": "OBSERVED", "upstream_name": str(loc.get("name") or "")[:120],
                      "distance_km": dist, "at": at, "at_tz": "UTC", "pm25_latest": vals.get("pm25"),
                      "pm10_latest": vals.get("pm10"), "averaging": "latest hourly value (no AQI computed)",
                      "source": "OpenAQ v3, from the CPCB/WBPCB station"}
    return sites


def match_stations(per_provider: dict[str, dict[str, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    """Site id → {provider: observation}, for the sites at least one provider observed."""
    out: dict[str, dict[str, Any]] = {}
    for prov, sites in per_provider.items():
        for sid, obs in sites.items():
            out.setdefault(sid, {})[prov] = obs
    return out
