"""Kolkata calendar facts the synthetic history and the event covariate use.

Durga Puja dates are the West Bengal government's holiday notifications (Finance Dept.):
2025 — No. 4712-F(P2), 22 Nov 2024 (Saptami 29 Sep … Dashami 2 Oct);
2026 — No. 4188-F(P2), 27 Nov 2025 (Saptami 18 Oct … Dashami 21 Oct). Mirrored at
https://wbxpress.com/holiday-list-west-bengal-government-employees-2025/ and …-2026/.

The traffic rhythm itself (office peaks, Puja nights) is a MODELLED pattern for the SIMULATED history,
not a measurement.
"""

from __future__ import annotations

from datetime import date

__all__ = ["PUJA_NIGHTS", "puja_night", "puja_day"]

#: Shashthi … Dashami, per the notifications above
PUJA_NIGHTS: dict[int, tuple[date, date]] = {
    2025: (date(2025, 9, 28), date(2025, 10, 2)),
    2026: (date(2026, 10, 17), date(2026, 10, 21)),
}


def puja_day(d: date) -> int:
    """0 outside Puja; 1 Shashthi/Dashami; 2 Saptami–Navami (the heaviest nights)."""
    w = PUJA_NIGHTS.get(d.year)
    if not w or not (w[0] <= d <= w[1]):
        return 0
    return 1 if d in (w[0], w[1]) else 2


def puja_night(d: date) -> int:
    return puja_day(d)
