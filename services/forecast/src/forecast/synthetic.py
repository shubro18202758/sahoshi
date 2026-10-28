"""Deterministic SIMULATED Kolkata traffic history (V/C, speed and covariates per segment, 15-min steps).

Everything here is labelled ``SIMULATED``: it exists so the forecaster, the baseline and the backtest can
run offline and reproducibly when the platform has no (or too little) recorded traffic. It is a
*modelled rhythm*, not a measurement:

* **office peaks** — weekday demand ramps to a late-morning peak (10:00–11:00 IST) and a longer evening
  peak (17:30–19:30); Saturday is lighter with a shopping evening, Sunday lighter still; inbound roads
  (towards Esplanade / BBD Bag) load in the morning, outbound ones in the evening;
* **Durga Puja nights** — on the official Shashthi–Dashami dates (``calendar.py``) roads near the big
  pandals (Bagbazar, Kumartuli, College Square, Santosh Mitra Square, Deshapriya Park, Ekdalia …) load
  heavily from 17:00 to 04:00 and office peaks thin out; the event covariate is 1 there;
* **rain** — storm cells with a monsoon-shaped monthly frequency cut capacity and a little demand;
  where a segment is low-lying, accumulated rain while the Hooghly gates are closed (the tide model,
  ``tide.py``) cuts capacity further — the waterlogging-at-high-tide effect;
* **events** — a few SIMULATED Eden Gardens match-egress windows load the roads around the stadium;
* **incidents** — rare breakdowns that no covariate announces (forecast error the models must live with);
* AR(1) noise.

Determinism: every random draw is seeded by (seed, segment, IST day) or (seed, IST day), so the value at a
given instant does not depend on the window asked for.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

import numpy as np

from forecast.bpr import speed_from_vc
from forecast.calendar import puja_day
from forecast.network import Network, Segment, haversine_m
from forecast.tide import TideModel

__all__ = ["History", "SyntheticCity", "LABEL", "align"]

LABEL = "SIMULATED"
_IST_MIN = 330
_CENTRE = (22.5680, 88.3510)  # Esplanade / BBD Bag
#: pandal landmarks (cities/kolkata/landmarks.json ids, approximate coordinates)
_PANDALS = {
    "bagbazar": (22.6040, 88.3660), "kumartuli": (22.5990, 88.3610),
    "santosh_mitra_square": (22.5620, 88.3640), "college_square": (22.5750, 88.3640),
    "deshapriya_park": (22.5150, 88.3530), "ekdalia": (22.5160, 88.3700),
}
_EDEN = (22.5646, 88.3433)

_WEEKDAY = np.array([0.18, 0.12, 0.10, 0.10, 0.12, 0.18, 0.30, 0.45, 0.62, 0.78, 0.86, 0.80,
                     0.70, 0.68, 0.68, 0.70, 0.76, 0.85, 0.90, 0.86, 0.72, 0.55, 0.40, 0.28])
_SATURDAY = np.array([0.22, 0.15, 0.12, 0.10, 0.11, 0.15, 0.24, 0.36, 0.50, 0.62, 0.68, 0.70,
                      0.66, 0.64, 0.64, 0.68, 0.74, 0.82, 0.86, 0.84, 0.74, 0.58, 0.44, 0.32])
_SUNDAY = np.array([0.24, 0.16, 0.12, 0.10, 0.10, 0.12, 0.18, 0.26, 0.36, 0.46, 0.52, 0.56,
                    0.56, 0.54, 0.54, 0.58, 0.64, 0.72, 0.76, 0.74, 0.64, 0.50, 0.38, 0.30])
_STORMS_PER_DAY = {1: 0.05, 2: 0.05, 3: 0.2, 4: 0.25, 5: 0.5, 6: 1.2, 7: 1.5, 8: 1.5, 9: 1.2,
                   10: 0.5, 11: 0.15, 12: 0.05}
_CLASS_SCALE = {"motorway": 0.86, "trunk": 0.92, "primary": 0.95, "secondary": 0.9, "tertiary": 0.8}


def align(t: datetime, step_min: int = 15) -> datetime:
    t = t.astimezone(UTC).replace(second=0, microsecond=0)
    return t - timedelta(minutes=t.minute % step_min)


def _rng(*parts: object) -> np.random.Generator:
    h = hashlib.blake2b("|".join(map(str, parts)).encode(), digest_size=8).digest()
    return np.random.default_rng(int.from_bytes(h, "little"))


@dataclass
class History:
    segment_id: int
    start: datetime  # UTC, step-aligned; times[i] = start + i·step
    step_min: int
    vc: np.ndarray
    speed: np.ndarray
    rain_mm_h: np.ndarray
    gate_closed: np.ndarray
    event: np.ndarray
    free_flow_kmh: float
    label: str
    source: str
    notes: list[str] = field(default_factory=list)

    @property
    def n(self) -> int:
        return int(self.vc.shape[0])

    def time_at(self, i: int) -> datetime:
        return self.start + timedelta(minutes=self.step_min * i)

    @property
    def end(self) -> datetime:
        """The time of the last step."""
        return self.time_at(self.n - 1)

    def covariates(self) -> dict[str, np.ndarray]:
        return {"rain_mm_h": self.rain_mm_h, "gate_closed": self.gate_closed, "event": self.event}

    def slice(self, i0: int, i1: int) -> "History":
        return History(self.segment_id, self.time_at(i0), self.step_min, self.vc[i0:i1], self.speed[i0:i1],
                       self.rain_mm_h[i0:i1], self.gate_closed[i0:i1], self.event[i0:i1],
                       self.free_flow_kmh, self.label, self.source, list(self.notes))


class SyntheticCity:
    """The SIMULATED world for one network and seed."""

    def __init__(self, network: Network, seed: int = 1690, step_min: int = 15) -> None:
        self.net = network
        self.seed = seed
        self.step = step_min
        self.tide = TideModel("garden_reach")
        self._seg_params = {sid: self._params(s) for sid, s in network.segments.items()}

    # ── per-segment constants ─────────────────────────────────────────────
    def _params(self, s: Segment) -> dict:
        r = _rng(self.seed, "seg", s.segment_id)
        lat, lon = s.midpoint
        fj, tj = self.net.junctions.get(s.from_junction), self.net.junctions.get(s.to_junction)
        inbound = 0.0
        if fj and tj:
            d_from = haversine_m(fj.lat, fj.lon, *_CENTRE)
            d_to = haversine_m(tj.lat, tj.lon, *_CENTRE)
            inbound = float(np.clip((d_from - d_to) / 2000.0, -1.0, 1.0))
        pandal_m = min(haversine_m(lat, lon, *p) for p in _PANDALS.values())
        return {
            "scale": _CLASS_SCALE.get(s.road_class, 0.9) * float(r.uniform(0.86, 1.12)),
            "inbound": inbound,
            "low_lying": float(r.beta(2.0, 3.0)),
            "ff": s.speed_limit_kmh * float(r.uniform(0.92, 1.05)),
            "pandal": float(np.clip(1.0 - pandal_m / 1500.0, 0.0, 1.0)),
            "eden": haversine_m(lat, lon, *_EDEN) < 1800.0,
            "rain_mult": float(r.uniform(0.75, 1.25)),
        }

    # ── city-wide drivers (shared by all segments) ────────────────────────
    def _times(self, start: datetime, n: int) -> np.ndarray:
        base = int(start.timestamp() // 60)
        return base + self.step * np.arange(n)  # epoch minutes, UTC

    @staticmethod
    def _ist_days(minutes: np.ndarray) -> list[date]:
        ist = minutes + _IST_MIN
        return [date.fromordinal(date(1970, 1, 1).toordinal() + int(d)) for d in (ist // 1440)]

    def _storms(self, d: date) -> list[tuple[float, float, float, int]]:
        """(start minute-of-day IST, duration min, peak mm/h, id) for one IST day."""
        r = _rng(self.seed, "storm", d.isoformat())
        k = r.poisson(_STORMS_PER_DAY[d.month])
        hours = np.arange(24)
        w = np.where((hours >= 12) & (hours <= 23), 3.0, 1.0)
        w /= w.sum()
        out = []
        for i in range(k):
            h = r.choice(hours, p=w)
            out.append((float(h * 60 + r.uniform(0, 60)), float(r.uniform(60, 240)),
                        float(np.clip(r.lognormal(np.log(14.0), 0.7), 3.0, 80.0)), i))
        return out

    def city_rain(self, start: datetime, n: int) -> np.ndarray:
        """City-scale rain intensity (mm/h) at each step, before the per-segment multiplier."""
        mins = self._times(start, n)
        out = np.zeros(n)
        ist = mins + _IST_MIN
        for d in sorted({*self._ist_days(mins), *[x - timedelta(days=1) for x in self._ist_days(mins[:1])]}):
            day0 = (d.toordinal() - date(1970, 1, 1).toordinal()) * 1440
            for st, dur, peak, _ in self._storms(d):
                t = ist - (day0 + st)
                m = (t >= 0) & (t <= dur)
                # triangular hyetograph, peak at 35 % of the storm
                tp = 0.35 * dur
                out[m] += np.where(t[m] <= tp, peak * t[m] / tp, peak * (dur - t[m]) / (dur - tp))
        return out

    def gate_closed(self, start: datetime, n: int) -> np.ndarray:
        return np.array([1.0 if self.tide.gate_closed(start + timedelta(minutes=self.step * i)) else 0.0
                         for i in range(n)])

    # ── one segment ───────────────────────────────────────────────────────
    def history(self, sid: int, start: datetime, end: datetime, *, rain: np.ndarray | None = None,
                gates: np.ndarray | None = None) -> History:
        start = align(start, self.step)
        n = int((align(end, self.step) - start).total_seconds() // (60 * self.step)) + 1
        p = self._seg_params[sid]
        mins = self._times(start, n)
        ist = mins + _IST_MIN
        tod = (ist % 1440) / 60.0
        days = self._ist_days(mins)
        rain_city = self.city_rain(start, n) if rain is None else rain
        rain = rain_city * p["rain_mult"]
        gates = self.gate_closed(start, n) if gates is None else gates

        # demand profile by day type (linear interpolation between hourly knots)
        h0 = np.floor(tod).astype(int) % 24
        frac = tod - np.floor(tod)
        dow = np.array([d.weekday() for d in days])
        pj = np.array([puja_day(d) for d in days])
        prof = np.empty(n)
        for table, mask in ((_WEEKDAY, dow < 5), (_SATURDAY, dow == 5), (_SUNDAY, dow == 6)):
            prof[mask] = (table[h0] * (1 - frac) + table[(h0 + 1) % 24] * frac)[mask]
        morning = np.exp(-0.5 * ((tod - 10.0) / 1.8) ** 2)
        evening = np.exp(-0.5 * ((tod - 18.5) / 2.0) ** 2)
        direction = 1.0 + 0.12 * p["inbound"] * (morning - evening)
        demand = prof * direction * p["scale"]
        # Puja: offices thin out by day, pandal roads load at night (17:00–04:00)
        night = (tod >= 17.0) | (tod < 4.0)
        puja_level = np.where(tod < 4.0, np.array([puja_day(d - timedelta(days=1)) for d in days]), pj)
        demand = np.where((pj == 2) & ~night, demand * 0.78, demand)
        puja_load = np.where(night, puja_level * (0.05 + 0.17 * p["pandal"]), 0.0)
        demand = demand + puja_load
        demand = demand * (1.0 - np.minimum(0.15, 0.003 * rain))

        # capacity: rain, then waterlogging where low-lying while the gates are shut
        k = int(60 // self.step) * 3
        rain_3h = np.convolve(rain, np.ones(k) * self.step / 60.0, mode="full")[:n]
        waterlog = p["low_lying"] * np.minimum(0.35, 0.004 * rain_3h) * np.where(gates > 0, 1.6, 1.0)
        cap = 1.0 - np.minimum(0.4, 0.010 * rain) - waterlog
        vc = demand / np.maximum(cap, 0.35)

        # events (SIMULATED): Eden Gardens egress on a few evenings; Puja nights on pandal roads
        event = np.zeros(n)
        if p["eden"]:
            for d in sorted(set(days)):
                r = _rng(self.seed, "eden", d.isoformat())
                if r.random() < 0.12:
                    day0 = (d.toordinal() - date(1970, 1, 1).toordinal()) * 1440
                    t = ist - (day0 + 21 * 60 + 30)
                    m = (t >= 0) & (t <= 120)
                    event[m] = 1.0
                    vc[m] += 0.32 * np.exp(-t[m] / 70.0)
        event = np.maximum(event, ((puja_level >= 1) & night & (p["pandal"] > 0.2)).astype(float))

        # incidents (unannounced) and AR(1) noise, both seeded per IST day
        noise = np.zeros(n)
        for d in sorted(set(days)):
            idx = np.array([i for i, x in enumerate(days) if x == d])
            r = _rng(self.seed, "noise", sid, d.isoformat())
            e = r.normal(0.0, 0.028, size=96)
            z = np.empty(96)
            z[0] = e[0] / np.sqrt(1 - 0.85 ** 2)
            for i in range(1, 96):
                z[i] = 0.85 * z[i - 1] + e[i]
            pos = ((ist[idx] % 1440) // self.step).astype(int)
            noise[idx] = z[pos]
            for _ in range(r.poisson(0.15)):
                st, dur, amp = r.uniform(360, 1320), r.uniform(30, 90), r.uniform(0.15, 0.35)
                t = (ist[idx] % 1440) - st
                m = (t >= 0) & (t <= dur)
                noise[idx[m]] += amp
        vc = np.clip(vc + noise, 0.03, 1.8)
        speed = speed_from_vc(vc, p["ff"])
        return History(sid, start, self.step, vc, speed, rain, gates, event, p["ff"], LABEL,
                       f"synthetic Kolkata history (seed {self.seed})")

    def histories(self, sids: list[int], start: datetime, end: datetime) -> dict[int, History]:
        start = align(start, self.step)
        n = int((align(end, self.step) - start).total_seconds() // (60 * self.step)) + 1
        rain = self.city_rain(start, n)
        gates = self.gate_closed(start, n)
        return {sid: self.history(sid, start, end, rain=rain, gates=gates) for sid in sids}
