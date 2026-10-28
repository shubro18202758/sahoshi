from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from hydro.tide import GATE_CLOSE_LEVEL_M, LABEL, TideModel

IST = ZoneInfo("Asia/Kolkata")


def _ex(model, start, hours):
    return [(e.kind, e.at.astimezone(IST), e.level_m) for e in model.extremes(start, hours)]


def _minutes(a, b):
    return abs((a - b).total_seconds()) / 60


def test_garden_reach_matches_published_predictions_28_oct_2026():
    """tide-forecast.com, Garden Reach 28 Oct 2026 (IST): HW 02:26 5.79 m, LW 09:56 1.98 m, HW 14:42 5.39 m,
    LW 22:04 2.01 m. The model is approximate: within 30 min and 0.3 m."""
    m = TideModel("garden_reach", freshet=False)
    got = _ex(m, datetime(2026, 10, 28, 0, 0, tzinfo=IST), 24)
    want = [("high", (2, 26), 5.79), ("low", (9, 56), 1.98), ("high", (14, 42), 5.39), ("low", (22, 4), 2.01)]
    assert [g[0] for g in got] == [w[0] for w in want]
    for (k, t, lv), (wk, (hh, mm), wl) in zip(got, want):
        assert _minutes(t, datetime(2026, 10, 28, hh, mm, tzinfo=IST)) <= 30, (k, t)
        assert abs(lv - wl) <= 0.3


def test_diamond_harbour_cited_constants_phase_convention():
    """The cited Diamond Harbour constants read as Greenwich phases put high water within an hour of the
    published prediction (12:04 IST on 28 Oct 2026) — the check on the phase-convention inference."""
    m = TideModel("diamond_harbour", freshet=False)
    highs = [t for k, t, _ in _ex(m, datetime(2026, 10, 28, 6, 0, tzinfo=IST), 12) if k == "high"]
    assert highs and _minutes(highs[0], datetime(2026, 10, 28, 12, 4, tzinfo=IST)) <= 60


def test_flood_shorter_than_ebb():
    m = TideModel("garden_reach", freshet=False)
    ex = m.extremes(datetime(2026, 10, 28, 0, 0, tzinfo=IST), 26)
    floods = [(b.at - a.at).total_seconds() / 3600 for a, b in zip(ex, ex[1:]) if a.kind == "low"]
    ebbs = [(b.at - a.at).total_seconds() / 3600 for a, b in zip(ex, ex[1:]) if a.kind == "high"]
    assert all(4.5 <= f <= 5.8 for f in floods) and all(6.4 <= e <= 7.6 for e in ebbs)


def test_gate_closure_on_23_sep_2025_covers_the_reported_closure():
    """Reported: lock gate closed 00:30–04:00 IST; high tide around 13:30 IST (Mayor, 23 Sep 2025)."""
    m = TideModel("garden_reach")
    t = datetime(2025, 9, 22, 20, 0, tzinfo=IST)
    closed = [t + timedelta(minutes=15 * i) for i in range(80) if m.gate_closed(t + timedelta(minutes=15 * i))]
    night = [c for c in closed if c.hour < 8]
    assert night[0] <= datetime(2025, 9, 23, 0, 45, tzinfo=IST)
    assert night[-1] >= datetime(2025, 9, 23, 3, 45, tzinfo=IST)
    highs = [e.at.astimezone(IST) for e in m.extremes(datetime(2025, 9, 23, 9, 0, tzinfo=IST), 8) if e.kind == "high"]
    assert highs and _minutes(highs[0], datetime(2025, 9, 23, 13, 30, tzinfo=IST)) <= 60


def test_freshet_raises_monsoon_levels_and_labels():
    t = datetime(2025, 9, 23, 2, 0, tzinfo=IST)
    assert TideModel("garden_reach").level(t) > TideModel("garden_reach", freshet=False).level(t) + 0.5
    assert LABEL == "MODELLED (approximate)" and GATE_CLOSE_LEVEL_M == 5.0
    s = TideModel().series(t, 2, 15)
    assert len(s) == 9
