from datetime import UTC, datetime, timedelta

import numpy as np

from forecast.calendar import puja_day
from forecast.synthetic import LABEL, SyntheticCity, align

END = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)


def test_deterministic_regardless_of_window(net):
    sim = SyntheticCity(net, seed=7)
    a = sim.history(1027, END - timedelta(days=3), END)
    b = sim.history(1027, END - timedelta(days=1), END)
    assert np.allclose(a.vc[-96:], b.vc[-96:])
    assert a.label == LABEL == "SIMULATED"
    c = SyntheticCity(net, seed=8).history(1027, END - timedelta(days=1), END)
    assert not np.allclose(c.vc, b.vc)


def test_shapes_bounds_and_covariates(net):
    sim = SyntheticCity(net)
    hs = sim.histories([1001, 1027, 1051], END - timedelta(days=2), END)
    for h in hs.values():
        assert h.n == 2 * 96 + 1
        assert np.all((h.vc >= 0.03) & (h.vc <= 1.8))
        assert np.all(h.speed > 0) and np.all(h.speed <= h.free_flow_kmh + 1e-9)
        assert set(h.covariates()) == {"rain_mm_h", "gate_closed", "event"}
        assert set(np.unique(h.gate_closed)) <= {0.0, 1.0}
        assert h.time_at(h.n - 1) == align(END)


def test_office_peak_above_night(net):
    sim = SyntheticCity(net)
    h = sim.history(1018, datetime(2026, 10, 26, 18, 30, tzinfo=UTC), datetime(2026, 10, 27, 18, 15, tzinfo=UTC))
    ist_hour = [(h.time_at(i) + timedelta(minutes=330)).hour for i in range(h.n)]
    night = np.mean([v for v, hr in zip(h.vc, ist_hour) if 2 <= hr < 5])
    peak = np.mean([v for v, hr in zip(h.vc, ist_hour) if 17 <= hr < 20])
    assert peak > night + 0.3


def test_puja_nights_load_pandal_roads(net):
    assert puja_day(datetime(2026, 10, 19).date()) == 2
    assert puja_day(datetime(2026, 10, 17).date()) == 1
    assert puja_day(datetime(2026, 10, 25).date()) == 0
    sim = SyntheticCity(net)
    # Bagbazar Street (1060) sits by the Bagbazar / Kumartuli pandals: 22:00 IST on Ashtami vs a week later
    t_puja = datetime(2026, 10, 19, 16, 30, tzinfo=UTC)
    t_norm = datetime(2026, 10, 26, 16, 30, tzinfo=UTC)
    hp = sim.history(1060, t_puja - timedelta(hours=2), t_puja)
    hn = sim.history(1060, t_norm - timedelta(hours=2), t_norm)
    assert hp.vc[-8:].mean() > hn.vc[-8:].mean() + 0.1
    assert hp.event[-1] == 1.0 and hn.event[-1] == 0.0


def test_rain_raises_vc(net):
    sim = SyntheticCity(net)
    start, end = END - timedelta(hours=6), END
    n = 25
    dry = sim.history(1030, start, end, rain=np.zeros(n), gates=np.zeros(n))
    wet = sim.history(1030, start, end, rain=np.full(n, 40.0), gates=np.ones(n))
    assert np.all(wet.vc >= dry.vc - 1e-9)
    assert wet.vc.mean() > dry.vc.mean() + 0.05
