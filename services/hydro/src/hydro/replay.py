"""Replay of the 22–23 September 2025 Kolkata deluge — the nowcast model run on the real dates.

What happened (official): IMD RMC Kolkata press release 23.09.2025 — 251.4 mm at Alipore in the 24 h to
08:30 IST; 3-hourly totals 2.5 mm (20:30–23:30), 48.6 mm (23:30–02:30), 185.6 mm (02:30–05:30) and
12.1 mm (05:30–08:30); the highest hourly fall 98 mm between 03:00 and 04:00 IST. Reuters quoted 251.6 mm.
The Mayor said the lock gate was closed from 00:30 to 04:00 and again around the 13:30 high tide.

Two runs, both honest about their rain:

* ``open_meteo_archive`` — the brief's run: Open-Meteo's historical archive (reanalysis / NWP based)
  hourly precipitation at the fixed point set. These gridded products do not resolve this storm: they
  carry tens of millimetres where the gauges measured ~250 mm. The run reports that, and what the model
  makes of it.
* ``imd_gauge_anchored`` — the same model driven by the observed totals: IMD's Alipore 3-hourly totals and
  peak hour (OBSERVED), spread over 15-minute steps with a documented shape (MODELLED), scaled in space by
  KMC's station-wise 24-h totals as reported by the press (OBSERVED as reported; gauge positions
  approximate).

Tide: the Garden Reach model for those dates (MODELLED). Pumps: all available — "All 82 pumping
stations … were operational" (Millennium Post, 24 Sep 2025); the FFEWS adapter stays EMULATED.

The model's flags are compared with places the news reported waterlogged that night (``REPORTED``). News
coverage is incomplete, so a flag with no report is not counted as a false alarm.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

from hydro.model import CLASS_BANDS
from hydro.network import haversine_m
from hydro.nowcast import Hydro
from hydro.rain import POINTS, RainPoint, idw, quarter_series

__all__ = ["EVENTS", "REPORTED", "KMC_GAUGES", "IMD_ALIPORE_3H", "imd_alipore_series", "replay"]

IST = ZoneInfo("Asia/Kolkata")
EVENTS = {"2025-09-23": {"start_ist": datetime(2025, 9, 22, 18, 0, tzinfo=IST),
                         "end_ist": datetime(2025, 9, 23, 14, 0, tzinfo=IST)}}

SRC = {
    "imd": {"publisher": "IMD Regional Meteorological Centre, Kolkata — press release", "date": "2025-09-23",
            "url": "https://internal.imd.gov.in/press_release/20250923_pr_4321.pdf"},
    "reuters": {"publisher": "Reuters via Dawn", "date": "2025-09-24", "url": "https://www.dawn.com/news/1944310"},
    "pti_tribune": {"publisher": "PTI via The Tribune", "date": "2025-09-23",
                    "url": "https://www.tribuneindia.com/news/india/heavy-rain-paralyses-kolkata-5-dead-in-rain-"
                           "related-incidents/amp"},
    "ians": {"publisher": "IANS via Reporter Post", "date": "2025-09-24",
             "url": "https://reporterpost.in/article/nation/40938/kolkata-battles-waterlogging-as-torrential-"
                    "rain-claims-10-lives"},
    "mpost_25": {"publisher": "Millennium Post", "date": "2025-09-25",
                 "url": "https://www.millenniumpost.in/bengal/most-city-streets-cleared-of-water-except-added-"
                        "areas-kmc-628812"},
    "mpost_24": {"publisher": "Millennium Post", "date": "2025-09-24",
                 "url": "https://www.millenniumpost.in/bengal/kmc-drains-flooded-city-on-war-footing-628674"},
    "dte": {"publisher": "Down To Earth", "date": "2025-09-24",
            "url": "https://www.downtoearth.org.in/climate-change/unexpected-interaction-of-atmospheric-"
                   "conditions-not-cloudburst-caused-kolkatas-intense-180mm-rainfall-in-3-hours-says-imd"},
    "newsarena": {"publisher": "News Arena India (KMC station-wise figures)", "date": "2025-09-23",
                  "url": "https://newsarenaindia.com/nation/torrential-rain-disrupts-kolkata-ahead-of-durga-puja-"
                         "5-dead/57263"},
    "mongabay": {"publisher": "Mongabay India", "date": "2025-09-30",
                 "url": "http://india.mongabay.com/2025/09/intense-rainfall-spotlights-the-fault-in-kolkatas-"
                        "aging-clogged-drainage-systems/"},
    "weekendleader": {"publisher": "IANS via The Weekend Leader (Mayor on lock gates)", "date": "2025-09-23",
                      "url": "https://www.theweekendleader.com/Headlines/80522/kolkata-hit-by-cloudburst-7-"
                             "electrocution-deaths-train-and-metro-services-disrupted.html"},
}

#: IMD Alipore 3-hourly totals (IST windows, mm) — OBSERVED
IMD_ALIPORE_3H = [
    ((20, 30), (23, 30), 2.5),
    ((23, 30), (2, 30), 48.6),
    ((2, 30), (5, 30), 185.6),
    ((5, 30), (8, 30), 12.1),
]

#: KMC station-wise 24-h totals as reported (News Arena, 23 Sep 2025); positions APPROXIMATE (±0.5 km)
KMC_GAUGES = [
    ("Garia Kamdahari", 22.4660, 88.3900, 332.0), ("Jodhpur Park", 22.5090, 88.3640, 285.0),
    ("Kalighat", 22.5200, 88.3440, 280.2), ("Topsia", 22.5400, 88.3900, 275.0),
    ("Ballygunge", 22.5300, 88.3830, 264.0), ("Chetla", 22.5180, 88.3360, 262.0),
    ("Chingrighata", 22.5630, 88.4040, 237.0), ("Mominpur", 22.5270, 88.3220, 234.0),
    ("Palmer Bazar", 22.5560, 88.3820, 217.0), ("Dhapa", 22.5480, 88.4020, 212.0),
    ("Ultadanga", 22.5910, 88.3920, 207.0), ("Kudghat", 22.4920, 88.3430, 203.4),
    ("Pagladanga (Tangra)", 22.5530, 88.3950, 201.0), ("Kulia (Tangra)", 22.5560, 88.3880, 196.0),
    ("Thanthania", 22.5770, 88.3620, 195.0),
]
#: Alipore's 24-h figure in the same report (06:30–06:30 window), the denominator for the spatial scale
ALIPORE_REPORTED_24H = 247.5

#: places reported waterlogged that night or the morning after (kind: point within 600 m, or road by name)
REPORTED: list[dict[str, Any]] = [
    {"name": "EM Bypass", "road": "Eastern Metropolitan Bypass", "src": ["pti_tribune", "mpost_25"]},
    {"name": "AJC Bose Road", "road": "Acharya Jagadish Chandra Bose Road", "src": ["pti_tribune"]},
    {"name": "Central Avenue", "road": "Chittaranjan Avenue", "src": ["pti_tribune"]},
    {"name": "Rashbehari Avenue", "road": "Rash Behari Avenue", "src": ["pti_tribune", "ians"]},
    {"name": "Park Circus", "lat": 22.5395, "lon": 88.3690, "src": ["pti_tribune", "ians", "mpost_25"]},
    {"name": "Gariahat", "lat": 22.5190, "lon": 88.3660, "src": ["pti_tribune"]},
    {"name": "Behala", "lat": 22.4950, "lon": 88.3150, "src": ["pti_tribune"]},
    {"name": "College Street", "lat": 22.5745, "lon": 88.3633, "src": ["pti_tribune", "ians", "mongabay"]},
    {"name": "Thanthania", "lat": 22.5770, "lon": 88.3620, "src": ["ians", "mpost_25"]},
    {"name": "Amherst Street", "lat": 22.5790, "lon": 88.3680, "src": ["mpost_25"]},
    {"name": "Ballygunge Phari", "lat": 22.5280, "lon": 88.3650, "src": ["ians", "mpost_25", "dte"]},
    {"name": "Shakespeare Sarani", "lat": 22.5450, "lon": 88.3530, "src": ["mpost_25"]},
    {"name": "Topsia", "lat": 22.5400, "lon": 88.3900, "src": ["mpost_25"]},
    {"name": "Garia", "lat": 22.4660, "lon": 88.3880, "src": ["pti_tribune"]},
    {"name": "Jodhpur Park", "lat": 22.5090, "lon": 88.3640, "src": ["pti_tribune", "mpost_24"]},
    {"name": "Lake Gardens", "lat": 22.5060, "lon": 88.3530, "src": ["pti_tribune"]},
    {"name": "Kankurgachi underpass", "lat": 22.5770, "lon": 88.3940, "src": ["ians"]},
    {"name": "Maddox Square", "lat": 22.5240, "lon": 88.3630, "src": ["dte"]},
    {"name": "Netaji Nagar", "lat": 22.4880, "lon": 88.3680, "src": ["mongabay"]},
    {"name": "Palmer Bazar", "lat": 22.5560, "lon": 88.3820, "src": ["dte"]},
]


def _ist(d: date, hm: tuple[int, int]) -> datetime:
    return datetime(d.year, d.month, d.day, hm[0], hm[1], tzinfo=IST)


def imd_alipore_series(start_utc: datetime, n: int, step_min: int = 15) -> np.ndarray:
    """mm/h at Alipore on the 15-min grid: IMD 3-hourly totals (OBSERVED) with a documented shape
    (MODELLED): the 23:30–02:30 total ramps up (weights 1:2:3 by hour); in 02:30–05:30 the 03:00–04:00 hour
    carries the reported 98 mm, the rest (87.6 mm) is split 02:30–03:00 25 %, 04:00–05:00 55 %,
    05:00–05:30 20 %; the other windows are flat."""
    d0 = date(2025, 9, 22)
    d1 = date(2025, 9, 23)
    pieces: list[tuple[datetime, datetime, float]] = []  # (start, end, mm)
    pieces.append((_ist(d0, (20, 30)), _ist(d0, (23, 30)), 2.5))
    tot = 48.6
    pieces += [(_ist(d0, (23, 30)), _ist(d1, (0, 30)), tot / 6), (_ist(d1, (0, 30)), _ist(d1, (1, 30)), tot * 2 / 6),
               (_ist(d1, (1, 30)), _ist(d1, (2, 30)), tot * 3 / 6)]
    rest = 185.6 - 98.0
    pieces += [(_ist(d1, (2, 30)), _ist(d1, (3, 0)), rest * 0.25), (_ist(d1, (3, 0)), _ist(d1, (4, 0)), 98.0),
               (_ist(d1, (4, 0)), _ist(d1, (5, 0)), rest * 0.55), (_ist(d1, (5, 0)), _ist(d1, (5, 30)), rest * 0.20)]
    pieces.append((_ist(d1, (5, 30)), _ist(d1, (8, 30)), 12.1))
    out = np.zeros(n)
    for i in range(n):
        t_end = start_utc + timedelta(minutes=step_min * i)
        t_mid = t_end - timedelta(minutes=step_min / 2)
        for a, b, mm in pieces:
            if a <= t_mid < b:
                out[i] = mm / ((b - a).total_seconds() / 3600.0)
                break
    return out


def _gauge_scale(lat: float, lon: float) -> float:
    d = np.array([haversine_m(lat, lon, g[1], g[2]) for g in KMC_GAUGES])
    idx = np.argsort(d)[:3]
    w = 1.0 / np.maximum(d[idx], 300.0) ** 2
    vals = np.array([KMC_GAUGES[i][3] for i in idx]) / ALIPORE_REPORTED_24H
    return float(np.sum(vals * w) / w.sum())


def _match(hydro: Hydro, rep: dict) -> list[int]:
    if "road" in rep:
        return [sid for sid, s in hydro.net.segments.items() if s.road_name.split(" (")[0] == rep["road"]]
    best = []
    for sid, s in hydro.net.segments.items():
        if hydro.sus.get(str(sid), {}).get("elevated"):
            continue  # a reported waterlogged place is never a bridge deck or a flyover
        d = min(haversine_m(rep["lat"], rep["lon"], lat, lon) for lon, lat in s.line) if s.line else 1e9
        if d <= 600.0:
            best.append(sid)
    return best


async def replay(hydro: Hydro, event: str = "2025-09-23") -> dict[str, Any]:
    if event not in EVENTS:
        raise KeyError(event)
    ev = EVENTS[event]
    step = hydro.step
    start = ev["start_ist"].astimezone(UTC)
    n = int((ev["end_ist"] - ev["start_ist"]).total_seconds() // (60 * step)) + 1
    times = [start + timedelta(minutes=step * i) for i in range(n)]
    availability = {}  # all pumps available (MPost 24 Sep 2025); EMULATED adapter not consulted

    runs: dict[str, Any] = {}
    # ── run A: Open-Meteo archive ─────────────────────────────────────────
    try:
        arc = await hydro.rain.archive_hourly(POINTS, date(2025, 9, 22), date(2025, 9, 23))
        pts = [RainPoint(p["id"], p["lat"], p["lon"], times, quarter_series(p["times"], p["mm"], start, n, step))
               for p in arc["points"]]
        rain_a = {sid: idw(pts, *hydro.net.segments[sid].midpoint) for sid in hydro.net.segments}
        city_total = float(np.mean([np.sum(p.mm_h) * step / 60 for p in pts]))
        max_total = float(max(np.sum(p.mm_h) * step / 60 for p in pts))
        runs["open_meteo_archive"] = _run(hydro, "open_meteo_archive", times, rain_a, availability, {
            "label": "ARCHIVE (Open-Meteo historical archive, reanalysis/NWP based)",
            "source": hydro.rain.archive_url, "model": arc["model"],
            "grid_cells": sorted({f"{a:.3f},{b:.3f}" for a, b in arc["grid"]}),
            "window_total_mm_city_mean": round(city_total, 1), "window_total_mm_max_point": round(max_total, 1),
            "finding": (f"The archive's gridded rain over the window is {city_total:.0f} mm (city mean; "
                        f"{max_total:.0f} mm at its wettest point) against 248.8 mm measured at Alipore by IMD in "
                        "the same hours: reanalysis/NWP grids do not resolve this storm. The model is driven by "
                        "its rain, so this run shows what a nowcast fed only by such a product would have "
                        "missed — the case for wiring KMC's own rain gauges (FFEWS) into the pilot."),
        })
    except Exception as exc:  # noqa: BLE001
        runs["open_meteo_archive"] = {"error": f"{type(exc).__name__}: {exc}"[:300]}

    # ── run B: IMD gauge-anchored ─────────────────────────────────────────
    alipore = imd_alipore_series(start, n, step)
    rain_b = {sid: alipore * _gauge_scale(*hydro.net.segments[sid].midpoint) for sid in hydro.net.segments}
    runs["imd_gauge_anchored"] = _run(hydro, "imd_gauge_anchored", times, rain_b, availability, {
        "label": "OBSERVED totals (IMD Alipore 3-hourly; KMC station 24-h as reported) · 15-min shape MODELLED",
        "sources": [SRC["imd"], SRC["newsarena"]],
        "alipore_window_total_mm": round(float(np.sum(alipore) * step / 60), 1),
        "alipore_peak_mm_h": round(float(alipore.max()), 1),
    })

    runs["imd_gauge_anchored"]["snapshot"] = _snapshot(hydro, times, rain_b, availability,
                                                       datetime(2025, 9, 23, 2, 0, tzinfo=IST))
    gates = [t for t in times if hydro.tide.gate_closed(t - timedelta(minutes=step / 2))]
    closed_spans = _spans(gates, step)
    return {
        "event": event,
        "title": "Kolkata deluge, 22–23 September 2025",
        "window_ist": [ev["start_ist"].isoformat(), ev["end_ist"].isoformat()],
        "official": {"alipore_24h_mm": 251.4, "to": "2025-09-23T08:30+05:30",
                     "peak_hour": "98 mm, 03:00–04:00 IST", "source": SRC["imd"],
                     "also_reported": {"reuters_mm": 251.6, "source": SRC["reuters"]}},
        "tide": {"label": "MODELLED (approximate)",
                 "gate_closed_ist": [[a.astimezone(IST).isoformat(), b.astimezone(IST).isoformat()]
                                     for a, b in closed_spans],
                 "reported": "lock gate closed 00:30–04:00 IST; high tide around 13:30 IST (Mayor)",
                 "reported_source": SRC["weekendleader"]},
        "pumps": {"assumed_availability": 1.0, "label": "EMULATED adapter not used — all pumps assumed available",
                  "basis": "\"All 82 pumping stations … were operational\" (Millennium Post, 24 Sep 2025)",
                  "source": SRC["mpost_24"]},
        "runs": runs,
        "sources": SRC,
        "honesty": ("News reports name places, not every street, and the network has 65 arterial segments: a "
                    "flag with no report is not called a false alarm, and an off-network report is listed but "
                    "not scored. Gauge positions are approximate."),
    }


def _spans(ts: list[datetime], step: int) -> list[tuple[datetime, datetime]]:
    spans: list[tuple[datetime, datetime]] = []
    for t in ts:
        if spans and (t - spans[-1][1]) <= timedelta(minutes=step):
            spans[-1] = (spans[-1][0], t)
        else:
            spans.append((t, t))
    return spans


def _first(times: list[datetime], cls: np.ndarray, k: int) -> str | None:
    idx = np.nonzero(cls >= k)[0]
    return times[int(idx[0])].astimezone(IST).strftime("%Y-%m-%d %H:%M") if idx.size else None


def _run(hydro: Hydro, name: str, times: list[datetime], rain_for: dict[int, np.ndarray],
         availability: dict[str, float], meta: dict[str, Any]) -> dict[str, Any]:
    core = hydro.run_segments(times, rain_for, availability)
    segs = []
    for sid in sorted(hydro.net.segments):
        st, _a, run = core["runs"][sid]
        peak_i = int(np.argmax(run.depth_cm))
        segs.append({
            "segment_id": sid, "road_name": st["seg"].road_name,
            "place": hydro.net.junction_name(st["seg"].to_junction),
            "rain_total_mm": round(float(np.sum(rain_for[sid]) * hydro.step / 60), 1),
            "peak_class": int(run.classes.max()), "peak_depth_cm": round(float(run.depth_cm[peak_i]), 1),
            "peak_band": CLASS_BANDS[int(run.classes.max())],
            "peak_at_ist": times[peak_i].astimezone(IST).strftime("%Y-%m-%d %H:%M"),
            "first_class1_ist": _first(times, run.classes, 1),
            "first_class2_ist": _first(times, run.classes, 2),
            "first_class3_ist": _first(times, run.classes, 3),
            "elevated": bool(st["sus"].get("elevated", False)),
        })
    by = {s["segment_id"]: s for s in segs}
    checks = []
    for rep in REPORTED:
        m = _match(hydro, rep)
        flagged = [by[s] for s in m if by[s]["peak_class"] >= 2]
        first = sorted(f["first_class2_ist"] for f in flagged if f["first_class2_ist"])
        checks.append({
            "reported": rep["name"], "sources": [SRC[s]["publisher"] + ", " + SRC[s]["date"] for s in rep["src"]],
            "segments": m, "on_network": bool(m),
            "flagged": bool(flagged) if m else None,
            "first_flag_ist": first[0] if first else None,
            "max_class": max((by[s]["peak_class"] for s in m), default=None),
        })
    scored = [c for c in checks if c["on_network"]]
    hits = sum(1 for c in scored if c["flagged"])
    counts = {str(k): sum(1 for s in segs if s["peak_class"] == k) for k in range(4)}
    flagged_ids = [s["segment_id"] for s in segs if s["peak_class"] >= 2]
    return {
        **meta,
        "peak_class_counts": counts,
        "flagged_segments": len(flagged_ids),
        "earliest_flag_ist": min((s["first_class2_ist"] for s in segs if s["first_class2_ist"]), default=None),
        "reported_check": {"on_network": len(scored), "flagged": hits,
                           "hit_rate": round(hits / len(scored), 3) if scored else None,
                           "off_network": [c["reported"] for c in checks if not c["on_network"]],
                           "items": checks},
        "segments": segs,
    }


def _snapshot(hydro: Hydro, times: list[datetime], rain_for: dict[int, np.ndarray], availability: dict[str, float],
              at: datetime) -> dict[str, Any]:
    """What the officer would have seen at ``at`` if the observed rain had been nowcast perfectly: the
    nowcast view (risk within the horizon, lead times) and its proposals. Hindsight, labelled so."""
    core = hydro.run_segments(times, rain_for, availability)
    now_idx = max(i for i, t in enumerate(times) if t <= at)
    end_idx = min(len(times) - 1, now_idx + hydro.horizon // hydro.step)
    results = []
    for sid in sorted(hydro.net.segments):
        st, a, run = core["runs"][sid]
        results.append(hydro._result(sid, st, a, run, times, now_idx, end_idx, rain_for[sid], core["gates"],
                                     "OBSERVED (hindsight)", [], at.astimezone(UTC)))
    flagged = {r["segment_id"] for r in results if r["risk_class"] >= 2}
    props = hydro._proposals(results, flagged, at.astimezone(UTC), ["HINDSIGHT", "MODELLED"])
    leads = sorted(r["lead_time_deep_min"] for r in results if r["segment_id"] in flagged)
    top = sorted((r for r in results if r["segment_id"] in flagged), key=lambda r: (-r["risk_class"], r["lead_time_min"]))
    return {
        "at_ist": at.isoformat(),
        "label": "HINDSIGHT — the observed rain used as if it had been a perfect nowcast",
        "flagged_within_horizon": len(flagged),
        "flagged_now": sum(1 for r in results if r["risk_class_now"] >= 2),
        "lead_time_to_deep_min": {"min": leads[0], "median": leads[len(leads) // 2], "max": leads[-1]} if leads else None,
        "top": [{k: r[k] for k in ("segment_id", "road_name", "place", "risk_class", "expected_depth_band",
                                   "lead_time_min", "lead_time_deep_min")} for r in top[:8]],
        "proposal_counts": {k: sum(1 for p in props if p["kind"] == k) for k in sorted({p["kind"] for p in props})},
        "proposal_examples": [p["summary"] for p in props if p["kind"] != "public_advisory_draft"][:4],
        "advisory_draft": next((p["text"] for p in props if p["kind"] == "public_advisory_draft"), None),
        # the proposals themselves for the eight most urgent roads and the advisory (an officer exercise on
        # the console: HINDSIGHT-labelled, never today's city)
        "proposals": [p for p in props if p["kind"] == "public_advisory_draft"
                      or p.get("subject_urn") in {f"segment:{r['segment_id']}" for r in top[:8]}],
    }
