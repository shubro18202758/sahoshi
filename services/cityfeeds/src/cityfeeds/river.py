"""Damodar (DVC) and South Bengal rivers: CWC observed water levels (LIVE) and a news signal (aggregate).

**Why.** Releases from the Damodar Valley Corporation's reservoirs (Maithon, Panchet) through the Durgapur barrage
flood the lower Damodar, Mundeshwari and Rupnarayan — Howrah, Hooghly and Paschim Medinipur — and close roads on
the Howrah approaches. It is a West Bengal problem with its own news vocabulary ("DVC released … cusecs").

**Machine-readable source.** The Central Water Commission's flood-forecasting site (ffs.india-water.gov.in) is an
Angular app over an open JSON API; its robots.txt disallows nothing. Per station:

* ``/iam/api/layer-station/<code>`` — name, latitude, longitude, reservoir flag;
* ``/iam/api/flood-forecast-static/<code>`` — warning level, danger level, highest flood level (and date), FRL;
* ``/iam/api/new-entry-data/specification/sorted-page`` — the latest observations, datatype ``HHS`` = the
  hourly water level in metres.

The stations are CWC's own codes for the DVC system and the lower Damodar / Hooghly (``STATIONS``). This is the
ONLY official, machine-readable input here; it is labelled LIVE (CWC observed). CWC publishes no DVC release
volume through it — the release figure lives in DVC's press notes and the news.

**News signal.** The reviewed Kolkata outlets the platform's OSINT connector uses (Times of India Kolkata, Sangbad
Pratidin, ABP Ananda Kolkata; Millennium Post when it answers) are read at most once per 30 minutes and the items
of the last 72 hours that mention a DVC release (English: DVC, Damodar, cusec, barrage release; Bengali: ডিভিসি,
দামোদর, কিউসেক, জল ছাড়) are COUNTED. Only the count, the outlet and the link are kept (events, not people).
Label: AGGREGATE (news mentions, not a measurement).
"""

from __future__ import annotations

import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from cityfeeds.geo import KOLKATA, haversine_km

__all__ = ["STATIONS", "NEWS_FEEDS", "fetch_river", "fetch_news", "river_view", "count_mentions", "DVC_TERMS"]

#: CWC station codes (exact, some end in a tab as stored by CWC), with the river and why each matters
STATIONS: list[dict[str, str]] = [
    {"code": "005-DDASL\t", "river": "Barakar (DVC)", "role": "Maithon reservoir (DVC)"},
    {"code": "008-DDASL\t", "river": "Damodar (DVC)", "role": "Tenughat reservoir, upper Damodar"},
    {"code": "046-DDASL", "river": "Damodar", "role": "Damodar railway bridge, below Panchet"},
    {"code": "013-DDASL\t", "river": "Damodar", "role": "Durgapur barrage (DVC releases pass here)"},
    {"code": "014-DDASL\t", "river": "Damodar", "role": "Jamalpur, lower Damodar (Purba Bardhaman)"},
    {"code": "015-DDASL\t", "river": "Mundeshwari", "role": "Harinkhola (Hooghly district; floods Howrah's west)"},
    {"code": "050-DDASL", "river": "Shilabati", "role": "Ghatal (Paschim Medinipur)"},
    {"code": "013-LGD3BEH", "river": "Bhagirathi-Hooghly", "role": "Kalna, the Hooghly upstream of Kolkata"},
]

NEWS_FEEDS = [
    ("toi_kolkata", "https://timesofindia.indiatimes.com/rssfeeds/-2128830821.cms", "timesofindia.indiatimes.com", "en"),
    ("millenniumpost_bengal", "https://www.millenniumpost.in/feed", "millenniumpost.in", "en"),
    ("sangbadpratidin_kolkata", "https://www.sangbadpratidin.in/feed/", "sangbadpratidin.in", "bn"),
    ("abp_ananda_kolkata", "https://bengali.abplive.com/news/kolkata/feed", "bengali.abplive.com", "bn"),
]

DVC_TERMS = re.compile(r"\bDVC\b|Damodar Valley|\bcusecs?\b|Durgapur barrage|Maithon|Panchet|ডিভিসি|দামোদর|কিউসেক|"
                       r"মাইথন|পাঞ্চেত|দুর্গাপুর ব্যারেজ", re.I)
_DOCTYPE = re.compile(r"<!DOCTYPE[^>[]*(\[[^]]*\])?>", re.I | re.S)


def _sorted_page(code: str, n: int = 40) -> dict[str, str]:
    spec = {"where": {"expression": {"valueIsRelationField": False, "fieldName": "id.stationCode", "operator": "eq",
                                     "value": code}}}
    return {"sort-criteria": json.dumps({"sortOrderDtos": [{"sortDirection": "DESC", "field": "id.dataTime"}]}),
            "page-number": "0", "page-size": str(n), "specification": json.dumps(spec)}


async def fetch_river(client: httpx.AsyncClient, base: str, static_cache: dict[str, Any]) -> dict[str, Any]:
    """One refresh: the latest observations per station; station metadata and thresholds once per process."""
    out: dict[str, Any] = {"stations": {}, "errors": {}}
    for st in STATIONS:
        code = st["code"]
        try:
            if code not in static_cache:
                q = urllib.parse.quote(code, safe="")
                meta = (await client.get(f"{base}/layer-station/{q}")).json()
                stat = (await client.get(f"{base}/flood-forecast-static/{q}")).json()
                static_cache[code] = {"meta": meta, "static": stat}
            r = await client.get(f"{base}/new-entry-data/specification/sorted-page", params=_sorted_page(code))
            r.raise_for_status()
            out["stations"][code] = {**static_cache[code], "obs": r.json()}
        except Exception as exc:  # noqa: BLE001 — one station down never hides the others
            out["errors"][code] = f"{type(exc).__name__}: {exc}"[:160]
    if not out["stations"]:
        raise RuntimeError(f"CWC: no station answered ({len(out['errors'])} errors)")
    return out


def _items(xml_text: str) -> list[dict[str, str]]:
    root = ET.fromstring(_DOCTYPE.sub("", xml_text))
    items = []
    for it in root.iter("item"):
        def tx(tag: str) -> str:
            el = it.find(tag)
            return (el.text or "").strip() if el is not None else ""
        items.append({"title": tx("title"), "link": tx("link"), "description": tx("description"), "pubDate": tx("pubDate")})
    return items


async def fetch_news(client: httpx.AsyncClient) -> dict[str, Any]:
    out: dict[str, Any] = {"feeds": {}, "errors": {}}
    for fid, url, publisher, lang in NEWS_FEEDS:
        try:
            r = await client.get(url)
            r.raise_for_status()
            out["feeds"][fid] = {"publisher": publisher, "lang": lang, "items": _items(r.text)}
        except Exception as exc:  # noqa: BLE001
            out["errors"][fid] = f"{type(exc).__name__}: {exc}"[:160]
    if not out["feeds"]:
        raise RuntimeError("no news feed answered")
    return out


def count_mentions(news: dict | None, now: datetime, hours: int = 72) -> dict[str, Any]:
    """Aggregate only: how many recent items mention a DVC release, per outlet, with their links."""
    total = 0
    scanned = 0
    per: dict[str, int] = {}
    links: list[dict[str, str]] = []
    for fid, f in (news or {}).get("feeds", {}).items():
        for it in f.get("items", []):
            try:
                at = parsedate_to_datetime(it["pubDate"]) if it.get("pubDate") else None
            except Exception:  # noqa: BLE001
                at = None
            if at is not None and at.tzinfo is None:
                at = at.replace(tzinfo=UTC)
            if at is not None and at < now - timedelta(hours=hours):
                continue
            scanned += 1
            if DVC_TERMS.search(f"{it.get('title', '')} {it.get('description', '')}"):
                total += 1
                per[f["publisher"]] = per.get(f["publisher"], 0) + 1
                if len(links) < 8:
                    links.append({"publisher": f["publisher"], "link": it.get("link", ""),
                                  "at": at.isoformat() if at else None})
    return {"label": "AGGREGATE", "window_h": hours, "items_scanned": scanned, "mentions": total, "by_outlet": per,
            "links": links, "outlets_read": sorted((news or {}).get("feeds", {}).keys()),
            "outlets_down": sorted((news or {}).get("errors", {}).keys()),
            "terms": "DVC, Damodar Valley, cusec(s), Durgapur barrage, Maithon, Panchet; ডিভিসি, দামোদর, কিউসেক, মাইথন, পাঞ্চেত"}


def _level_series(obs: list[dict]) -> list[tuple[str, float]]:
    return [(o["id"]["dataTime"], float(o["dataValue"])) for o in obs
            if o.get("id", {}).get("datatypeCode") == "HHS" and o.get("dataValue") is not None]


def river_view(raw: dict | None, news: dict | None, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    klat, klon = KOLKATA
    stations = []
    worst = "normal"
    order = {"normal": 0, "no_threshold": 0, "near_frl": 1, "above_warning": 2, "above_danger": 3}
    for st in STATIONS:
        rec = (raw or {}).get("stations", {}).get(st["code"])
        if not rec:
            stations.append({"code": st["code"].strip(), "river": st["river"], "role": st["role"], "status": "unavailable"})
            continue
        meta, stat = rec.get("meta") or {}, rec.get("static") or {}
        ser = _level_series(rec.get("obs") or [])
        level = ser[0][1] if ser else None
        at = ser[0][0] if ser else None
        trend = None
        if len(ser) >= 2:
            older = next((v for t, v in ser[1:] if t <= (datetime.fromisoformat(ser[0][0]) - timedelta(hours=3)).isoformat()), ser[-1][1])
            d = level - older
            trend = "rising" if d > 0.02 else "falling" if d < -0.02 else "steady"
        wl, dl, frl = stat.get("warningLevel"), stat.get("dangerLevel"), stat.get("frl")
        status = "no_threshold"
        if level is not None:
            if dl is not None and level >= dl:
                status = "above_danger"
            elif wl is not None and level >= wl:
                status = "above_warning"
            elif meta.get("reservoir") and frl is not None and level >= frl - 1.0:
                status = "near_frl"
            elif wl is not None or dl is not None:
                status = "normal"
        if order.get(status, 0) > order.get(worst, 0):
            worst = status
        lat, lon = meta.get("lat"), meta.get("lon")
        stations.append({
            "code": st["code"].strip(), "name": (meta.get("name") or "").strip().title(), "river": st["river"], "role": st["role"],
            "lat": lat, "lon": lon, "distance_km": round(haversine_km(klat, klon, lat, lon)) if lat and lon else None,
            "reservoir": bool(meta.get("reservoir")), "level_m": level, "observed_at_ist": at, "trend": trend,
            "warning_m": wl, "danger_m": dl, "frl_m": frl, "highest_m": stat.get("highestFlowLevel"),
            "highest_date": stat.get("highestFlowLevelDate"),
            "to_warning_m": round(wl - level, 2) if (wl is not None and level is not None) else None,
            "to_danger_m": round(dl - level, 2) if (dl is not None and level is not None) else None,
            "status": status, "label": "LIVE",
        })
    above = [s for s in stations if s["status"] in ("above_warning", "above_danger")]
    return {
        "label": "LIVE", "what": "CWC observed hourly water levels (HHS) at the DVC reservoirs and the lower Damodar, "
                                 "Mundeshwari, Shilabati and Hooghly stations, against CWC's warning and danger levels",
        "status": worst if raw else "unavailable",
        "above_warning": len(above), "stations_read": sum(1 for s in stations if s["status"] != "unavailable"),
        "stations": stations,
        "station_errors": (raw or {}).get("errors", {}),
        "dvc_news": count_mentions(news, now) if news else {"label": "UNAVAILABLE", "mentions": None},
        "release_note": "CWC's open API publishes levels, not DVC release volumes; a release is announced in DVC "
                        "press notes and reported in the news (the mention count above)",
        "sources": {"cwc": {"publisher": "Central Water Commission, Flood Forecasting", "url": "https://ffs.india-water.gov.in/"},
                    "dvc": {"publisher": "Damodar Valley Corporation", "url": "https://www.dvc.gov.in/",
                            "note": "release press notes; no machine-readable feed found"}},
    }
