from datetime import UTC, datetime

import numpy as np

from hydro.ffews import LABEL, STATIONS, EmulatedFfews, station_for
from hydro.model import CLASS_BANDS, C_MIN, classify, simulate


def test_classify_edges():
    assert classify(np.array([0.0, 1.99, 2.0, 9.9, 10.0, 29.9, 30.0, 80.0])).tolist() == [0, 0, 1, 1, 2, 2, 3, 3]
    assert CLASS_BANDS[2] == "10–30 cm"


def test_dry_and_light_rain_stay_dry():
    assert simulate(np.zeros(8), np.zeros(8), 1.0, 0.8).classes.max() == 0
    # rain below the drainage floor never ponds
    assert simulate(np.full(16, C_MIN * 0.9), np.zeros(16), 1.0, 1.0).depth_cm.max() == 0


def test_more_rain_tide_and_pump_loss_make_it_worse():
    r = np.full(8, 40.0)
    base = simulate(r, np.zeros(8), 1.0, 0.5).depth_cm[-1]
    assert simulate(r * 1.5, np.zeros(8), 1.0, 0.5).depth_cm[-1] > base
    assert simulate(r, np.ones(8), 1.0, 0.5).depth_cm[-1] > base          # gates shut at high tide
    assert simulate(r, np.zeros(8), 0.0, 0.5).depth_cm[-1] > base         # pumps down
    assert simulate(r, np.zeros(8), 1.0, 0.9).depth_cm[-1] > base         # more susceptible


def test_elevated_never_ponds_and_water_recedes():
    assert simulate(np.full(8, 90.0), np.ones(8), 0.0, 1.0, elevated=True).depth_cm.max() == 0
    run = simulate(np.r_[np.full(8, 60.0), np.zeros(16)], np.zeros(24), 1.0, 0.5)
    assert run.depth_cm[-1] < run.depth_cm[7]


def test_emulated_ffews_is_labelled_and_deterministic():
    f = EmulatedFfews()
    t = datetime(2026, 10, 28, 12, tzinfo=UTC)
    a, b = f.states(t, 10.0), f.states(t, 10.0)
    assert [x.as_dict() for x in a] == [x.as_dict() for x in b]
    for s in a:
        d = s.as_dict()
        assert d["label"] == LABEL == "EMULATED" and d["location"] == "approximate"
        assert 0 <= s.pumps_running <= s.pumps_available <= s.pumps_total
        assert s.pumps_running == s.pumps_available  # in rain every available pump runs
        assert d["source"].startswith("http")
    assert len(STATIONS) >= 10


def test_station_catchment():
    st, d = station_for(22.5770, 88.3630)
    assert st is not None and st.id == "thanthania" and d < 500
    st, d = station_for(22.69, 88.49)
    assert st is None
