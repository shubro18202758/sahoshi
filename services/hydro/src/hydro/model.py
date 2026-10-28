"""The waterlogging nowcast model: rain × tide × pumps × susceptibility → depth-risk class 0–3 per segment.

A conceptual ponding (bucket) model on 15-minute steps, per road segment — MODELLED, with every parameter
here and in docs/ai/hydro.md:

    drainage capacity   C_open = C_MAX − (C_MAX − C_MIN)·S          mm/h, S = susceptibility 0..1
                        C(t)   = C_open · (1 − GATE_CUT·gate(t)) · (PUMP_FLOOR + (1 − PUMP_FLOOR)·a)
    ponded water        W(t+Δ) = max(0, W(t) + (RUNOFF·r(t) − C(t))·Δ)   mm over the catchment
    depth at the road   d = W/10 · (1 + CONCENTRATION·S)               cm

* ``C_MIN`` 6 mm/h — the old network's design ("one-fourth of an inch rainfall per hour", KMC 2015; the
  Mayor in 2019: "capable of draining water when it rains 6 mm in an hour");
* ``C_MAX`` 20 mm/h — the Mayor in Oct 2024: "KMC drainage system can only drain 20 mm of water in an
  hour" (after upgrades; 15 mm/h was reported in 2021);
* ``GATE_CUT`` 0.5 — while the Hooghly gates are shut (tide model) the outfalls cannot discharge by
  gravity and the pumps work against the river: half the capacity (assumption);
* ``PUMP_FLOOR`` 0.6 — with every pump down a catchment keeps 60 % (gravity paths); availability ``a``
  comes from the FFEWS adapter (EMULATED);
* ``RUNOFF`` 0.85 — dense urban runoff coefficient (assumption);
* ``CONCENTRATION`` 2 — a low spot collects up to 3× the catchment-average ponding (assumption).

Elevated segments (bridge decks, flyovers) are reported with depth 0 and say why.

Classes: 0 dry (< 2 cm) · 1 shallow (2–10 cm) · 2 deep (10–30 cm: small cars and two-wheelers stall,
ambulances slow, live-wire danger) · 3 impassable (> 30 cm).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = [
    "C_MIN", "C_MAX", "GATE_CUT", "PUMP_FLOOR", "RUNOFF", "CONCENTRATION",
    "CLASS_EDGES_CM", "CLASS_BANDS", "CLASS_NAMES", "simulate", "classify", "SegmentRun",
]

C_MIN = 6.0
C_MAX = 20.0
GATE_CUT = 0.5
PUMP_FLOOR = 0.6
RUNOFF = 0.85
CONCENTRATION = 2.0
CLASS_EDGES_CM = (2.0, 10.0, 30.0)
CLASS_BANDS = ("0–2 cm", "2–10 cm", "10–30 cm", "> 30 cm")
CLASS_NAMES = ("dry", "shallow", "deep", "impassable")

PARAMS = {"C_MIN_mm_h": C_MIN, "C_MAX_mm_h": C_MAX, "GATE_CUT": GATE_CUT, "PUMP_FLOOR": PUMP_FLOOR,
          "RUNOFF": RUNOFF, "CONCENTRATION": CONCENTRATION, "class_edges_cm": list(CLASS_EDGES_CM)}


@dataclass
class SegmentRun:
    depth_cm: np.ndarray
    water_mm: np.ndarray
    capacity_mm_h: np.ndarray
    classes: np.ndarray


def classify(depth_cm: np.ndarray | float) -> np.ndarray:
    return np.searchsorted(np.array(CLASS_EDGES_CM), np.asarray(depth_cm), side="right")


def simulate(rain_mm_h: np.ndarray, gate_closed: np.ndarray, availability: float, susceptibility: float,
             elevated: bool = False, step_min: int = 15, w0_mm: float = 0.0) -> SegmentRun:
    rain = np.asarray(rain_mm_h, dtype=float)
    gate = np.asarray(gate_closed, dtype=float)
    s = float(np.clip(susceptibility, 0.0, 1.0))
    c_open = C_MAX - (C_MAX - C_MIN) * s
    cap = c_open * (1.0 - GATE_CUT * gate) * (PUMP_FLOOR + (1.0 - PUMP_FLOOR) * float(np.clip(availability, 0, 1)))
    dt = step_min / 60.0
    w = np.empty_like(rain)
    cur = w0_mm
    for i in range(rain.size):
        cur = max(0.0, cur + (RUNOFF * rain[i] - cap[i]) * dt)
        w[i] = cur
    depth = w / 10.0 * (1.0 + CONCENTRATION * s)
    if elevated:
        depth = np.zeros_like(depth)
    return SegmentRun(depth, w, cap, classify(depth))
