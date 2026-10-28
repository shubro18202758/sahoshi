"""Air quality at the Kolkata and Howrah continuous-monitoring sites, and India's National AQI bands.

**Where.** The point set is the ten WBPCB/CPCB continuous ambient air-quality monitoring sites the city is used
to hearing about (CPCB lists them as "<site>, Kolkata - WBPCB" / "<site>, Howrah - WBPCB"). Their surveyed
positions are not published in a machine-readable form this box can reach, so each point is the NAMED SITE'S
public location (the landmark, campus or locality), cited per point in ``STATIONS`` (``coord_source``), good to
about ±1 km. That is far finer than the model grid below, so it changes nothing in the numbers.

**What.** The values are Open-Meteo's air-quality API (``/v1/air-quality``): the CAMS global atmospheric-
composition forecast (ECMWF Copernicus), hourly PM2.5, PM10, NO₂, O₃, US AQI and European AQI, the past 24 h and
the next 48 h. Label: the FEED is live; the VALUES are a model's (MODELLED), not the station's own measurement.
Over India the CAMS grid is coarse (≈ 0.4°), so neighbouring sites often share a value — the response says so.

**National AQI (India).** CPCB's National Air Quality Index (launched 2014): sub-indices by linear interpolation
inside the breakpoint table, on 24-hour averages for PM2.5 and PM10. Source: CPCB, *National Air Quality Index*,
Control of Urban Pollution Series CUPS/82/2014-15, Table 6 (https://cpcb.nic.in/National-Air-Quality-Index/).
Only PM2.5 and PM10 are used here (CPCB needs at least three pollutants, one of them PM, for an official AQI), so
the figure is labelled INDICATIVE: "National AQI bands applied to the modelled 24-h PM means; not a CPCB AQI".
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

__all__ = ["STATIONS", "NAQI_BANDS", "sub_index", "naqi", "band_of", "fetch_air", "air_view", "NAQI_SOURCE"]

NAQI_SOURCE = {
    "publisher": "Central Pollution Control Board (CPCB), National Air Quality Index",
    "document": "Control of Urban Pollution Series CUPS/82/2014-15, Table 6 (breakpoints, 24-h averages)",
    "url": "https://cpcb.nic.in/National-Air-Quality-Index/",
}

#: (id, name EN, name BN, lat, lon, coordinate source). Order: Kolkata sites, then Howrah.
STATIONS: list[dict[str, Any]] = [
    {"id": "victoria_memorial", "en": "Victoria Memorial", "bn": "ভিক্টোরিয়া মেমোরিয়াল", "lat": 22.5448, "lon": 88.3426,
     "coord_source": "landmark (cities/kolkata/landmarks.json; Wikipedia 22°32′41″N 88°20′33″E)"},
    {"id": "rabindra_bharati", "en": "Rabindra Bharati University (B T Road)", "bn": "রবীন্দ্রভারতী বিশ্ববিদ্যালয় (বি টি রোড)",
     "lat": 22.6290, "lon": 88.3795, "coord_source": "campus (Emerald Bower, B T Road; OpenStreetMap), approx."},
    {"id": "ballygunge", "en": "Ballygunge", "bn": "বালিগঞ্জ", "lat": 22.5280, "lon": 88.3650,
     "coord_source": "locality (Ballygunge Phari, cities/kolkata/landmarks.json), approx."},
    {"id": "fort_william", "en": "Fort William", "bn": "ফোর্ট উইলিয়াম", "lat": 22.5553, "lon": 88.3386,
     "coord_source": "landmark (Wikipedia 22°33′19″N 88°20′19″E)"},
    {"id": "jadavpur", "en": "Jadavpur", "bn": "যাদবপুর", "lat": 22.4972, "lon": 88.3719,
     "coord_source": "campus (Jadavpur University; Wikipedia 22°29′50″N 88°22′19″E)"},
    {"id": "bidhannagar", "en": "Bidhannagar (Salt Lake)", "bn": "বিধাননগর (সল্টলেক)", "lat": 22.5850, "lon": 88.4150,
     "coord_source": "locality (Salt Lake, OpenStreetMap), approx."},
    {"id": "rabindra_sarobar", "en": "Rabindra Sarobar", "bn": "রবীন্দ্র সরোবর", "lat": 22.5111, "lon": 88.3611,
     "coord_source": "landmark (Wikipedia 22°30′40″N 88°21′40″E)"},
    {"id": "ghusuri", "en": "Ghusuri, Howrah", "bn": "ঘুসুড়ি, হাওড়া", "lat": 22.6108, "lon": 88.3511,
     "coord_source": "locality (Wikipedia 22°36′39″N 88°21′04″E)"},
    {"id": "padmapukur", "en": "Padmapukur, Howrah", "bn": "পদ্মপুকুর, হাওড়া", "lat": 22.5690, "lon": 88.3180,
     "coord_source": "locality (OpenStreetMap), approx. ±1 km"},
    {"id": "belur_math", "en": "Belur Math, Howrah", "bn": "বেলুড় মঠ, হাওড়া", "lat": 22.6322, "lon": 88.3558,
     "coord_source": "landmark (Wikipedia 22°37′56″N 88°21′21″E)"},
]

#: CPCB National AQI: (band id, EN, BN, HI, AQI lo, AQI hi, PM2.5 lo, hi, PM10 lo, hi) — 24-h µg/m³.
#: The open top band (Severe, "250+" / "430+") is closed at 380 / 510 µg/m³ = AQI 500 for interpolation, as in
#: CPCB's own AQI calculator; anything above reads 500.
NAQI_BANDS: list[dict[str, Any]] = [
    {"id": "good", "en": "Good", "bn": "ভালো", "hi": "अच्छा", "aqi": (0, 50), "pm25": (0, 30), "pm10": (0, 50)},
    {"id": "satisfactory", "en": "Satisfactory", "bn": "সন্তোষজনক", "hi": "संतोषजनक", "aqi": (51, 100),
     "pm25": (31, 60), "pm10": (51, 100)},
    {"id": "moderate", "en": "Moderate", "bn": "মাঝারি", "hi": "मध्यम", "aqi": (101, 200), "pm25": (61, 90),
     "pm10": (101, 250)},
    {"id": "poor", "en": "Poor", "bn": "খারাপ", "hi": "खराब", "aqi": (201, 300), "pm25": (91, 120), "pm10": (251, 350)},
    {"id": "very_poor", "en": "Very poor", "bn": "খুব খারাপ", "hi": "बहुत खराब", "aqi": (301, 400),
     "pm25": (121, 250), "pm10": (351, 430)},
    {"id": "severe", "en": "Severe", "bn": "অতি গুরুতর", "hi": "गंभीर", "aqi": (401, 500), "pm25": (251, 380),
     "pm10": (431, 510)},
]

#: the health message CPCB attaches to each band (paraphrased from the NAQI document's "possible health impacts")
HEALTH = {
    "good": "Minimal impact.",
    "satisfactory": "Minor breathing discomfort to sensitive people.",
    "moderate": "Breathing discomfort to people with lung disease such as asthma, and discomfort to people with "
                "heart disease, children and older adults.",
    "poor": "Breathing discomfort to most people on prolonged exposure.",
    "very_poor": "Respiratory illness on prolonged exposure.",
    "severe": "Affects healthy people and seriously impacts those with existing diseases.",
}


def sub_index(pollutant: str, c: float | None) -> int | None:
    """CPCB sub-index for a 24-h concentration (µg/m³): linear inside the band; ``None`` for no value."""
    if c is None:
        return None
    c = max(0.0, float(c))
    # CPCB's table has integer bounds (30 | 31); a value between two bands belongs to the upper one
    prev_hi_c, prev_hi_i = 0.0, 0
    for b in NAQI_BANDS:
        lo_c, hi_c = b[pollutant]
        lo_i, hi_i = b["aqi"]
        if c <= hi_c:
            if c < lo_c:  # inside the integer gap (e.g. 30.4): interpolate across it
                return round(prev_hi_i + (lo_i - prev_hi_i) * (c - prev_hi_c) / max(lo_c - prev_hi_c, 1e-9))
            return round(lo_i + (hi_i - lo_i) * (c - lo_c) / max(hi_c - lo_c, 1e-9))
        prev_hi_c, prev_hi_i = hi_c, hi_i
    return 500


def band_of(aqi: int | None) -> dict[str, Any] | None:
    if aqi is None:
        return None
    for b in NAQI_BANDS:
        if aqi <= b["aqi"][1]:
            return b
    return NAQI_BANDS[-1]


def naqi(pm25_24h: float | None, pm10_24h: float | None) -> dict[str, Any] | None:
    """The National AQI from the PM sub-indices (the larger one), with its band and the deciding pollutant."""
    s25, s10 = sub_index("pm25", pm25_24h), sub_index("pm10", pm10_24h)
    if s25 is None and s10 is None:
        return None
    if s10 is None or (s25 is not None and s25 >= s10):
        aqi, by = s25, "PM2.5"
    else:
        aqi, by = s10, "PM10"
    b = band_of(aqi)
    return {"aqi": aqi, "band": b["id"], "band_en": b["en"], "band_bn": b["bn"], "band_hi": b["hi"],
            "prominent": by, "sub_index": {"pm25": s25, "pm10": s10}, "health": HEALTH[b["id"]],
            "label": "INDICATIVE"}


async def fetch_air(client: httpx.AsyncClient, url: str) -> Any:
    params = {
        "latitude": ",".join(f"{s['lat']:.4f}" for s in STATIONS),
        "longitude": ",".join(f"{s['lon']:.4f}" for s in STATIONS),
        "current": "pm2_5,pm10,nitrogen_dioxide,ozone,us_aqi,european_aqi",
        "hourly": "pm2_5,pm10,nitrogen_dioxide,ozone,us_aqi,european_aqi",
        "past_hours": 24, "forecast_hours": 48, "timezone": "GMT",
    }
    r = await client.get(url, params=params)
    r.raise_for_status()
    body = r.json()
    locs = body if isinstance(body, list) else [body]
    if len(locs) != len(STATIONS):
        raise ValueError(f"expected {len(STATIONS)} locations, got {len(locs)}")
    return locs


def _mean(xs: list[float | None]) -> float | None:
    v = [float(x) for x in xs if x is not None]
    return round(sum(v) / len(v), 1) if len(v) >= 18 else None  # a 24-h mean needs most of its hours


def _r(x: Any, nd: int = 1) -> float | None:
    return None if x is None else round(float(x), nd)


def air_view(locs: list[dict] | None, now: datetime | None = None) -> dict[str, Any]:
    """Per site: now, the 24-h PM means and their National AQI, and a 48-h forecast of the daily band."""
    now = now or datetime.now(UTC)
    stations: list[dict[str, Any]] = []
    for st, loc in zip(STATIONS, locs or []):
        h = loc.get("hourly") or {}
        times = [datetime.fromisoformat(t).replace(tzinfo=UTC) for t in h.get("time", [])]
        cur = loc.get("current") or {}

        def series(k: str) -> list[float | None]:
            return list(h.get(k) or [None] * len(times))

        pm25, pm10 = series("pm2_5"), series("pm10")
        past = [i for i, t in enumerate(times) if now - timedelta(hours=24) < t <= now]
        m25 = _mean([pm25[i] for i in past])
        m10 = _mean([pm10[i] for i in past])
        idx = naqi(m25, m10)
        # the next 48 h as two forecast days (rolling 24-h windows starting now and in 24 h)
        fut = []
        for d in (0, 1):
            w = [i for i, t in enumerate(times) if now + timedelta(hours=24 * d) < t <= now + timedelta(hours=24 * (d + 1))]
            f = naqi(_mean([pm25[i] for i in w]), _mean([pm10[i] for i in w]))
            fut.append({"window_h": [24 * d, 24 * (d + 1)], "naqi": f})
        hourly = [{"t": t.isoformat(), "pm25": _r(a), "pm10": _r(b)}
                  for t, a, b in zip(times, pm25, pm10) if t > now - timedelta(hours=1)][:48]
        stations.append({
            "id": st["id"], "name": st["en"], "name_bn": st["bn"], "lat": st["lat"], "lon": st["lon"],
            "coord_source": st["coord_source"],
            "grid": {"lat": loc.get("latitude"), "lon": loc.get("longitude")},
            "now": {"at": cur.get("time"), "pm25": _r(cur.get("pm2_5")), "pm10": _r(cur.get("pm10")),
                    "no2": _r(cur.get("nitrogen_dioxide")), "o3": _r(cur.get("ozone")),
                    "us_aqi": cur.get("us_aqi"), "european_aqi": cur.get("european_aqi")},
            "pm25_24h": m25, "pm10_24h": m10, "naqi": idx, "forecast": fut, "hourly": hourly,
        })
    grids = {(s["grid"]["lat"], s["grid"]["lon"]) for s in stations}
    worst = max((s for s in stations if s["naqi"]), key=lambda s: s["naqi"]["aqi"], default=None)
    worst_next = None
    for s in stations:
        for f in s["forecast"]:
            if f["naqi"] and (worst_next is None or f["naqi"]["aqi"] > worst_next["naqi"]["aqi"]):
                worst_next = {"station": s["id"], "name": s["name"], **f}
    return {
        "label": "MODELLED",
        "feed_label": "LIVE",
        "what": "Open-Meteo air-quality API (CAMS global model) at the WBPCB/CPCB monitoring sites; values are "
                "a model's, not the stations' own measurements",
        "naqi_label": "INDICATIVE: CPCB National AQI bands applied to the modelled 24-h PM2.5/PM10 means; "
                      "not an official CPCB AQI",
        "naqi_source": NAQI_SOURCE,
        "grid_note": f"{len(grids)} distinct model grid cell(s) cover the {len(stations)} sites",
        "grid_cells": len(grids),
        "stations": stations,
        "city": ({"aqi": worst["naqi"]["aqi"], "band": worst["naqi"]["band"], "band_en": worst["naqi"]["band_en"],
                  "band_bn": worst["naqi"]["band_bn"], "band_hi": worst["naqi"]["band_hi"],
                  "prominent": worst["naqi"]["prominent"], "worst_site": worst["id"], "worst_site_name": worst["name"],
                  "worst_site_bn": worst["name_bn"], "pm25_24h": worst["pm25_24h"], "pm10_24h": worst["pm10_24h"],
                  "health": worst["naqi"]["health"]} if worst else None),
        "next_48h_worst": worst_next,
        "bands": [{"id": b["id"], "en": b["en"], "bn": b["bn"], "hi": b["hi"], "aqi": list(b["aqi"]),
                   "pm25": list(b["pm25"]), "pm10": list(b["pm10"])} for b in NAQI_BANDS],
    }
