"""Heat: temperature, humidity and apparent temperature (Open-Meteo), a heat index, and IMD's heatwave test.

**Points.** IMD's two Kolkata observatories, Alipore (22.5361 N, 88.3311 E) and Dum Dum (22.6531 N, 88.4467 E,
the airport). The values are Open-Meteo's forecast API (a blend of weather models; LIVE feed, MODELLED values).

**Heat index.** The US National Weather Service's Rothfusz regression with its two adjustments, from 2-m air
temperature and relative humidity (NWS WPC, "The Heat Index Equation",
https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml), with the NWS bands: caution 27–32 °C, extreme caution
32–41 °C, danger 41–54 °C, extreme danger ≥ 54 °C. It is a body-comfort measure in the shade; full sun adds up to
about 8 °C.

**IMD heatwave (plains).** IMD declares a heatwave at a plains station when the maximum temperature is at least
40 °C AND its departure from normal is 4.5–6.4 °C (severe: > 6.4 °C), or when the maximum is at least 45 °C
(severe: ≥ 47 °C) whatever the normal. Source: India Meteorological Department, *FAQ on Heat Wave*
(https://internal.imd.gov.in/section/nhac/dynamic/FAQ_heat_wave.pdf). Here the test runs on the FORECAST daily
maximum against the Alipore 1991–2020 monthly mean maximum (IMD normals as tabulated in Wikipedia, "Climate of
Kolkata") — so the result is MODELLED, never an IMD declaration.

**Season.** Kolkata's heat season is pre-monsoon, April–June: the traffic-duty advisory is drafted then (or any
time the heat index reaches "danger" or the heatwave test passes).
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

__all__ = ["POINTS", "ALIPORE_NORMAL_MAX", "heat_index_c", "hi_band", "imd_heatwave", "fetch_heat", "heat_view",
           "IMD_SOURCE", "HI_SOURCE"]

POINTS = [
    {"id": "alipore", "en": "Alipore (IMD observatory)", "bn": "আলিপুর (আবহাওয়া দপ্তর)", "lat": 22.5361, "lon": 88.3311},
    {"id": "dum_dum", "en": "Dum Dum (airport)", "bn": "দমদম (বিমানবন্দর)", "lat": 22.6531, "lon": 88.4467},
]

#: Kolkata (Alipore) mean daily maximum °C, 1991–2020 normals (IMD, as tabulated in Wikipedia "Climate of Kolkata")
ALIPORE_NORMAL_MAX = {1: 25.5, 2: 29.4, 3: 33.7, 4: 35.4, 5: 35.5, 6: 34.1, 7: 32.5, 8: 32.3, 9: 32.6, 10: 32.3,
                      11: 30.2, 12: 26.7}

IMD_SOURCE = {"publisher": "India Meteorological Department", "document": "FAQ on Heat Wave (criteria for plains)",
              "url": "https://internal.imd.gov.in/section/nhac/dynamic/FAQ_heat_wave.pdf",
              "normals": "Alipore 1991–2020 mean daily maximum (IMD; tabulated in Wikipedia, Climate of Kolkata)"}
HI_SOURCE = {"publisher": "US National Weather Service, Weather Prediction Center",
             "document": "The Heat Index Equation (Rothfusz regression with adjustments)",
             "url": "https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml"}

HI_BANDS = [(27.0, "normal"), (32.0, "caution"), (41.0, "extreme_caution"), (54.0, "danger"), (math.inf, "extreme_danger")]


def heat_index_c(t_c: float | None, rh: float | None) -> float | None:
    if t_c is None or rh is None:
        return None
    t = t_c * 9 / 5 + 32
    simple = 0.5 * (t + 61.0 + (t - 68.0) * 1.2 + rh * 0.094)
    if (simple + t) / 2 < 80:
        hi = simple
    else:
        hi = (-42.379 + 2.04901523 * t + 10.14333127 * rh - 0.22475541 * t * rh - 0.00683783 * t * t
              - 0.05481717 * rh * rh + 0.00122874 * t * t * rh + 0.00085282 * t * rh * rh
              - 0.00000199 * t * t * rh * rh)
        if rh < 13 and 80 <= t <= 112:
            hi -= ((13 - rh) / 4) * math.sqrt((17 - abs(t - 95)) / 17)
        elif rh > 85 and 80 <= t <= 87:
            hi += ((rh - 85) / 10) * ((87 - t) / 5)
    return round((hi - 32) * 5 / 9, 1)


def hi_band(hi: float | None) -> str | None:
    if hi is None:
        return None
    for top, name in HI_BANDS:
        if hi < top:
            return name
    return "extreme_danger"


def imd_heatwave(tmax: float | None, month: int) -> dict[str, Any] | None:
    """IMD's plains test on a (forecast) daily maximum: none · heatwave · severe, with the departure used."""
    if tmax is None:
        return None
    normal = ALIPORE_NORMAL_MAX[month]
    dep = round(tmax - normal, 1)
    level = "none"
    if tmax >= 47:
        level = "severe"
    elif tmax >= 45:
        level = "heatwave"
    elif tmax >= 40:
        if dep > 6.4:
            level = "severe"
        elif dep >= 4.5:
            level = "heatwave"
    return {"tmax": round(tmax, 1), "normal_max": normal, "departure": dep, "level": level, "label": "MODELLED"}


async def fetch_heat(client: httpx.AsyncClient, url: str) -> Any:
    params = {
        "latitude": ",".join(f"{p['lat']:.4f}" for p in POINTS),
        "longitude": ",".join(f"{p['lon']:.4f}" for p in POINTS),
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature",
        "hourly": "temperature_2m,relative_humidity_2m,apparent_temperature",
        "daily": "temperature_2m_max,apparent_temperature_max",
        "forecast_days": 3, "timezone": "Asia/Kolkata",
    }
    r = await client.get(url, params=params)
    r.raise_for_status()
    body = r.json()
    locs = body if isinstance(body, list) else [body]
    if len(locs) != len(POINTS):
        raise ValueError(f"expected {len(POINTS)} locations, got {len(locs)}")
    return locs


def heat_view(locs: list[dict] | None, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    ist_month = (now + timedelta(hours=5, minutes=30)).month
    points = []
    for p, loc in zip(POINTS, locs or []):
        cur = loc.get("current") or {}
        h = loc.get("hourly") or {}
        d = loc.get("daily") or {}
        t, rh = cur.get("temperature_2m"), cur.get("relative_humidity_2m")
        hi = heat_index_c(t, rh)
        # the hottest heat index in the next 48 h (hourly, local time)
        peak = None
        for tt, a, b in zip(h.get("time", []), h.get("temperature_2m", []), h.get("relative_humidity_2m", [])):
            v = heat_index_c(a, b)
            if v is not None and (peak is None or v > peak["heat_index"]):
                peak = {"at_ist": tt, "heat_index": v, "temp": a, "rh": b}
        days = []
        for day, tmax, amax in zip(d.get("time", []), d.get("temperature_2m_max", []), d.get("apparent_temperature_max", [])):
            month = int(day[5:7]) if day else ist_month
            days.append({"date": day, "tmax": tmax, "apparent_max": amax, "imd": imd_heatwave(tmax, month)})
        points.append({"id": p["id"], "name": p["en"], "name_bn": p["bn"], "lat": p["lat"], "lon": p["lon"],
                       "now": {"at_ist": cur.get("time"), "temp": t, "rh": rh, "apparent": cur.get("apparent_temperature"),
                               "heat_index": hi, "band": hi_band(hi)},
                       "peak_48h": peak, "days": days})
    hot = max((p for p in points if p["now"]["heat_index"] is not None), key=lambda p: p["now"]["heat_index"], default=None)
    peak = max((p["peak_48h"] | {"point": p["id"]} for p in points if p["peak_48h"]), key=lambda x: x["heat_index"], default=None)
    hw_days = [{"point": p["id"], **dd} for p in points for dd in p["days"] if dd["imd"] and dd["imd"]["level"] != "none"]
    month_ist = int(points[0]["days"][0]["date"][5:7]) if points and points[0]["days"] else ist_month
    return {
        "label": "MODELLED", "feed_label": "LIVE",
        "what": "Open-Meteo forecast API at IMD's Alipore and Dum Dum observatories; heat index (NWS) and the IMD "
                "plains heatwave test on the forecast maximum",
        "season": "pre-monsoon heat season (April–June)" if month_ist in (4, 5, 6) else "outside the April–June heat season",
        "in_season": month_ist in (4, 5, 6),
        "points": points,
        "city": ({"heat_index": hot["now"]["heat_index"], "band": hot["now"]["band"], "temp": hot["now"]["temp"],
                  "rh": hot["now"]["rh"], "apparent": hot["now"]["apparent"], "point": hot["id"]} if hot else None),
        "peak_48h": peak,
        "imd_heatwave_days": hw_days,
        "sources": {"heat_index": HI_SOURCE, "imd": IMD_SOURCE},
    }
