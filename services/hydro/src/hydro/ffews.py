"""KMC FFEWS adapter — pump-station state. **EMULATED until access is granted.**

KMC is building a city-level Flood Forecasting & Early Warning System (ADB-funded) with sensors in canals,
pumping stations and traffic junctions. Sahoshi has no access to it. ``FfewsAdapter`` is the interface a
real feed will implement; ``EmulatedFfews`` is the stand-in used until then, and everything it returns
says ``EMULATED`` — station names are real KMC drainage pumping stations (WB Irrigation & Waterways
Dept., "Kolkata Metropolis Drainage", and Millennium Post reports), but their *state* is invented.

Station coordinates are APPROXIMATE (placed by hand near the named locality, ±0.5–1 km) and only decide
which segments a station serves (nearest station within ``CATCHMENT_M``). Capacities (cusecs) are the
I&W department's published figures where listed.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from hydro.network import haversine_m

__all__ = ["PumpStation", "PumpState", "FfewsAdapter", "EmulatedFfews", "STATIONS", "LABEL", "CATCHMENT_M"]

LABEL = "EMULATED"
CATCHMENT_M = 3500.0
SOURCE_URL = "https://iwd.wb.gov.in/Kolkata_Metropolis_Drainage"


@dataclass(frozen=True)
class PumpStation:
    id: str
    name: str
    lat: float
    lon: float
    capacity_cusec: float | None
    source: str


#: KMC drainage pumping stations named in public sources (capacities from the I&W list where given)
STATIONS: list[PumpStation] = [
    PumpStation("ballygunge", "Ballygunge drainage pumping station", 22.5300, 88.3830, 1233, SOURCE_URL),
    PumpStation("palmer_bazar", "Palmer Bazar (Palmer Bridge) pumping station", 22.5560, 88.3820, 1184,
                SOURCE_URL),
    PumpStation("dhapa_lock", "Dhapa Lock pumping station", 22.5480, 88.4020, 480, SOURCE_URL),
    PumpStation("ultadanga", "Ultadanga pumping station", 22.5910, 88.3920, 440, SOURCE_URL),
    PumpStation("mominpur", "Mominpur pumping station", 22.5270, 88.3220, 142, SOURCE_URL),
    PumpStation("manicktala", "Manicktala pumping station", 22.5850, 88.3790, 97, SOURCE_URL),
    PumpStation("topsia", "Topsia pumping station", 22.5400, 88.3900, 65, SOURCE_URL),
    PumpStation("chetla_lock", "Chetla Lock pumping station", 22.5180, 88.3360, 24, SOURCE_URL),
    PumpStation("jodhpur_park", "Jodhpur Park pumping station", 22.5090, 88.3640, 20.64, SOURCE_URL),
    PumpStation("thanthania", "Thanthania pumping station (Hrishikesh Park)", 22.5790, 88.3660, None,
                "https://obeta.ttef.in/west-bengal/hope-for-relief-from-waterlogging-foundation-stone-of-"
                "drainage-pumping-station-in-thanthania/cid/2029829"),
    PumpStation("kalighat", "Kalighat pumping station", 22.5200, 88.3460, None,
                "https://www.millenniumpost.in/bengal/keep-demolition-teams-ready-for-night-shifts-in-wake-of-"
                "heavy-rain-forecast-kmc-takes-foolproof-measures-613618"),
    PumpStation("behala_flyover", "Behala Flyover pumping station", 22.4980, 88.3180, None,
                "https://www.millenniumpost.in/bengal/keep-demolition-teams-ready-for-night-shifts-in-wake-of-"
                "heavy-rain-forecast-kmc-takes-foolproof-measures-613618"),
]


@dataclass
class PumpState:
    station: PumpStation
    pumps_total: int
    pumps_running: int
    pumps_available: int
    sump_level_pct: float | None
    observed_at: datetime
    label: str

    @property
    def availability(self) -> float:
        return self.pumps_available / self.pumps_total if self.pumps_total else 0.0

    def as_dict(self) -> dict:
        s = self.station
        return {"id": s.id, "name": s.name, "lat": s.lat, "lon": s.lon, "location": "approximate",
                "capacity_cusec": s.capacity_cusec, "pumps_total": self.pumps_total,
                "pumps_available": self.pumps_available, "pumps_running": self.pumps_running,
                "availability": round(self.availability, 2), "sump_level_pct": self.sump_level_pct,
                "observed_at": self.observed_at.isoformat(), "label": self.label, "source": s.source}


class FfewsAdapter(Protocol):
    label: str

    def states(self, at: datetime, rain_mm_h: float = 0.0) -> list[PumpState]: ...


class EmulatedFfews:
    """Deterministic stand-in: each station has a fixed pump count; one pump at a station is down for
    maintenance on a rotating, seeded schedule; in rain every available pump runs. EMULATED."""

    label = LABEL

    def __init__(self, seed: int = 1690) -> None:
        self.seed = seed

    def _h(self, *parts: object) -> int:
        return int.from_bytes(hashlib.blake2b("|".join(map(str, parts)).encode(), digest_size=4).digest(), "little")

    def states(self, at: datetime, rain_mm_h: float = 0.0) -> list[PumpState]:
        at = at.astimezone(UTC)
        day = at.date().isoformat()
        out = []
        for st in STATIONS:
            total = 4 + self._h(self.seed, st.id) % 9  # 4..12 pumps (invented)
            down = 1 if self._h(self.seed, st.id, day) % 5 == 0 else 0
            avail = total - down
            running = avail if rain_mm_h > 2.0 else min(avail, 1 + self._h(self.seed, st.id, at.hour) % 2)
            sump = round(min(100.0, 20.0 + 6.0 * rain_mm_h), 1)
            out.append(PumpState(st, total, running, avail, sump, at, LABEL))
        return out


def station_for(lat: float, lon: float) -> tuple[PumpStation | None, float]:
    best, bd = None, float("inf")
    for st in STATIONS:
        d = haversine_m(lat, lon, st.lat, st.lon)
        if d < bd:
            best, bd = st, d
    return (best, bd) if bd <= CATCHMENT_M else (None, bd)
