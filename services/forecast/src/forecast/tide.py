"""Hooghly tide model at Garden Reach — MODELLED (approximate).

Why it matters: Kolkata's storm-water outfalls and lock gates on the Hooghly and the Adi Ganga close when
the river is high, so the city drains by pumps alone while the tide is up; rain at high tide waterlogs
faster (KMC/Mayor statements on 23 Sep 2025 and 25 Oct 2024; see docs/ai/hydro.md).

**Constants.** No citable harmonic constants for Garden Reach itself are public (the Survey of India's
Hugli River Tide Tables are not online). The citable set is the *observed* M2/S2/K1/O1 at Diamond
Harbour (88.1733 E, 22.1928 N) from Khan et al. (2021), NHESS 21:2523–2541, Supplement Table S1
(amplitudes in cm, phases in degrees; the phase is taken as the Greenwich (UTC) phase lag g — the
table compares them with FES/GOT/TPXO, which use g; that reading is an inference, checked below).

**Transfer to Garden Reach (the MODELLED part).**

* high water at Garden Reach lags Diamond Harbour by ``GR_LAG_H`` (2 h 38 min: the two stations'
  predicted high waters on 28 Oct 2026, tide-forecast.com) — applied as a phase shift ω·lag;
* amplitudes scaled by ``GR_AMPLITUDE_RATIO`` 0.80 (predicted ranges 3.81 m vs 4.95 m on 28 Oct 2026
  → 0.77; Cunningham 1904, Kidderpore dry-season spring range 12.5 ft ≈ 3.8 m vs the 4.5 m Diamond
  Harbour spring range of these constants → 0.85);
* mean level ``GR_MEAN_LEVEL_M`` 3.7 m above the predictions' datum (the mean of the predicted high and
  low waters, 3.7–3.9 m; port officials' May 2021 full-moon figures 6.01 m / 1.19 m → 3.6 m);
* a monsoon freshet offset by month (``FRESHET_OFFSET_M``) — the Survey of India applies a freshet
  correction to the Hugli tables, and Cunningham (1904) reports rains raising Kidderpore levels by about
  5 ft; the offsets used here are a conservative, labelled assumption;
* shallow-water distortion: the Hooghly floods for about 5 h and ebbs for about 7 h (Sailing-Directions
  text quoted by sea-seek.com). No citable M4 exists, so a single M4 term is FITTED: amplitude
  ``GR_M4_RATIO`` × the Garden Reach M2 amplitude, phase ``2·g(M2) − 90°`` (flood-dominant). Its one
  parameter is set so the modelled high waters land on the third-party predictions (they came ~40 min
  late without it, ~20 min late with it; low waters within ~10 min, levels within 0.15 m on 28 Oct
  2026); the same value then gives a ~5.2 h flood and a ~7.0 h ebb, matching the reported durations —
  an independent check, not a fit.

Nodal corrections (f, u) for M2, K1 and O1 use the standard Doodson/Schureman series; astronomical
arguments use the mean longitudes of the Moon (s), Sun (h), lunar perigee (p) and node (N).

**Outfall closure.** Lock gates are treated as closed while the modelled level is at or above
``GATE_CLOSE_LEVEL_M`` (5.0 m: a port official quoted by The Telegraph — "the gates need to be closed
once the level crosses 5 metres"). On 23 Sep 2025 the model's high waters fall near the reported
closures (00:30–04:00 and about noon–16:00 IST); the test suite checks that.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

__all__ = [
    "CONSTITUENTS_DH",
    "GR_LAG_H",
    "GR_AMPLITUDE_RATIO",
    "GR_MEAN_LEVEL_M",
    "GR_M4_RATIO",
    "GATE_CLOSE_LEVEL_M",
    "FRESHET_OFFSET_M",
    "TideModel",
    "TideExtreme",
    "LABEL",
    "SOURCES",
]

LABEL = "MODELLED (approximate)"

#: name → (amplitude m, Greenwich phase lag g °, speed °/h) at Diamond Harbour — Khan et al. 2021, Table S1
CONSTITUENTS_DH: dict[str, tuple[float, float, float]] = {
    "M2": (1.57, 168.0, 28.9841042),
    "S2": (0.68, 210.0, 30.0000000),
    "K1": (0.15, 285.0, 15.0410686),
    "O1": (0.07, 258.0, 13.9430356),
}

GR_LAG_H = 2.0 + 38.0 / 60.0
GR_AMPLITUDE_RATIO = 0.80
GR_MEAN_LEVEL_M = 3.7
#: fitted M4 amplitude as a fraction of the Garden Reach M2 amplitude (MODELLED; see the module doc)
GR_M4_RATIO = 0.18
GATE_CLOSE_LEVEL_M = 5.0
#: month → metres added to the mean level (monsoon freshet; MODELLED assumption)
FRESHET_OFFSET_M: dict[int, float] = {7: 0.3, 8: 0.6, 9: 0.6, 10: 0.3}

SOURCES: list[dict[str, str]] = [
    {"what": "M2/S2/K1/O1 observed at Diamond Harbour",
     "ref": "Khan et al. (2021), Nat. Hazards Earth Syst. Sci. 21:2523–2541, Supplement Table S1",
     "url": "https://nhess.copernicus.org/articles/21/2523/2021/nhess-21-2523-2021-supplement.pdf"},
    {"what": "Garden Reach vs Diamond Harbour predicted high/low waters (lag, range, mean level)",
     "ref": "tide-forecast.com predictions for 28 Oct 2026 (third-party; datum 'MLLW')",
     "url": "https://www.tide-forecast.com/locations/Calcutta-Garden-Reach-India/tides/latest"},
    {"what": "Gate-closure level ~5 m at Garden Reach",
     "ref": "The Telegraph (Kolkata), port official quoted on Hooghly tide and sluice gates",
     "url": "https://obeta.ttef.in/my-kolkata/news/hooghly-tide-helps-water-drain-out-faster-in-kolkata/cid/1864513"},
    {"what": "Kidderpore spring/neap ranges, dry season and rains",
     "ref": "Cunningham (1904), A Treatise on the Principles and Practice of Dock Engineering",
     "url": "https://tekniskkulturarv.dk/book/c3fb3acc-28e6-490b-8092-5f3a342494c2?page=74"},
]

_J2000 = datetime(2000, 1, 1, 12, tzinfo=UTC)


def _astro(t: datetime) -> tuple[float, float, float, float, float]:
    """(T, s, h, p, N) in degrees at UTC time t; T = hour angle of the mean sun."""
    days = (t - _J2000).total_seconds() / 86400.0
    c = days / 36525.0
    s = 218.3164477 + 481267.88123421 * c
    h = 280.4664567 + 36000.76982779 * c
    p = 83.3532465 + 4069.0137287 * c
    n = 125.0445479 - 1934.1362891 * c
    hours = t.hour + t.minute / 60.0 + t.second / 3600.0 + t.microsecond / 3.6e9
    big_t = 180.0 + 15.0 * hours
    return big_t, s % 360, h % 360, p % 360, n % 360


def _v_f_u(name: str, t: datetime) -> tuple[float, float, float]:
    """Equilibrium argument V (°), nodal factor f and nodal angle u (°) for a constituent."""
    big_t, s, h, _p, n = _astro(t)
    nr = math.radians(n)
    if name == "M2":
        v = 2 * big_t - 2 * s + 2 * h
        f = 1.0004 - 0.0373 * math.cos(nr) + 0.0002 * math.cos(2 * nr)
        u = -2.14 * math.sin(nr)
    elif name == "M4":
        v2, f2, u2 = _v_f_u("M2", t)
        v, f, u = 2 * v2, f2 * f2, 2 * u2
    elif name == "S2":
        v, f, u = 2 * big_t, 1.0, 0.0
    elif name == "K1":
        v = big_t + h - 90.0
        f = 1.0060 + 0.1150 * math.cos(nr) - 0.0088 * math.cos(2 * nr) + 0.0006 * math.cos(3 * nr)
        u = -8.86 * math.sin(nr) + 0.68 * math.sin(2 * nr) - 0.07 * math.sin(3 * nr)
    elif name == "O1":
        v = big_t - 2 * s + h + 90.0
        f = 1.0089 + 0.1871 * math.cos(nr) - 0.0147 * math.cos(2 * nr) + 0.0014 * math.cos(3 * nr)
        u = 10.80 * math.sin(nr) - 1.34 * math.sin(2 * nr) + 0.19 * math.sin(3 * nr)
    else:  # pragma: no cover - only the four constituents are defined
        raise KeyError(name)
    return v % 360.0, f, u


@dataclass(frozen=True)
class TideExtreme:
    kind: str  # "high" | "low"
    at: datetime
    level_m: float


class TideModel:
    """Harmonic tide at a station: Diamond Harbour (``station='diamond_harbour'``, the cited constants)
    or Garden Reach (``station='garden_reach'``, the MODELLED transfer)."""

    def __init__(self, station: str = "garden_reach", freshet: bool = True) -> None:
        if station not in ("garden_reach", "diamond_harbour"):
            raise ValueError(station)
        self.station = station
        self.freshet = freshet
        if station == "garden_reach":
            self.mean_level = GR_MEAN_LEVEL_M
            self.consts = {
                k: (a * GR_AMPLITUDE_RATIO, (g + w * GR_LAG_H) % 360.0, w)
                for k, (a, g, w) in CONSTITUENTS_DH.items()
            }
            a2, g2, w2 = self.consts["M2"]
            self.consts["M4"] = (GR_M4_RATIO * a2, (2 * g2 - 90.0) % 360.0, 2 * w2)
        else:
            # Diamond Harbour's mean level is not used by the city model; low waters ≈ 0.4 m, highs
            # ≈ 5.4 m in the same third-party predictions → 2.9 m (approximate)
            self.mean_level = 2.9
            self.consts = dict(CONSTITUENTS_DH)

    def level(self, t: datetime) -> float:
        if t.tzinfo is None:
            raise ValueError("aware datetime required")
        t = t.astimezone(UTC)
        z = self.mean_level + (FRESHET_OFFSET_M.get(t.astimezone(_IST).month, 0.0) if self.freshet else 0.0)
        for name, (a, g, _w) in self.consts.items():
            v, f, u = _v_f_u(name, t)
            z += f * a * math.cos(math.radians(v + u - g))
        return z

    def series(self, start: datetime, hours: float, step_min: int = 15) -> list[tuple[datetime, float]]:
        n = int(hours * 60 // step_min) + 1
        return [(start + timedelta(minutes=step_min * i), self.level(start + timedelta(minutes=step_min * i)))
                for i in range(n)]

    def gate_closed(self, t: datetime) -> bool:
        return self.level(t) >= GATE_CLOSE_LEVEL_M

    def extremes(self, start: datetime, hours: float) -> list[TideExtreme]:
        """High and low waters in [start, start+hours], found on a 6-min grid and refined."""
        step = timedelta(minutes=6)
        n = int(hours * 10) + 2
        times = [start - step + step * i for i in range(n + 1)]
        vals = [self.level(x) for x in times]
        out: list[TideExtreme] = []
        for i in range(1, len(vals) - 1):
            a, b, c = vals[i - 1], vals[i], vals[i + 1]
            kind = "high" if (b >= a and b > c) else "low" if (b <= a and b < c) else None
            if kind is None:
                continue
            # parabolic refinement
            denom = a - 2 * b + c
            off = 0.5 * (a - c) / denom if denom != 0 else 0.0
            at = times[i] + timedelta(seconds=off * step.total_seconds())
            if start <= at <= start + timedelta(hours=hours):
                out.append(TideExtreme(kind=kind, at=at, level_m=round(self.level(at), 2)))
        return out


_IST = __import__("zoneinfo").ZoneInfo("Asia/Kolkata")
