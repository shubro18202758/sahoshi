from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pytest

from forecast.config import Settings
from forecast.models import QuantileForecast, SeasonalNaive, SeriesInput
from forecast.network import load_network

#: a fixed origin inside the SIMULATED history (a Wednesday evening, IST 18:00)
ORIGIN = datetime(2026, 10, 28, 12, 30, tzinfo=UTC)


class RampModel:
    """A deterministic stand-in for the foundation model: the median ramps from the last value by +0.03 a
    step; a ±0.05 band."""

    name = "ramp-test-model"
    licence = "test"

    def __init__(self) -> None:
        self.calls = 0

    def predict(self, inputs: list[SeriesInput], horizon: int) -> list[QuantileForecast]:
        self.calls += 1
        out = []
        for i in inputs:
            p50 = float(i.target[-1]) + 0.03 * np.arange(1, horizon + 1)
            out.append(QuantileForecast(p50 - 0.05, p50, p50 + 0.05))
        return out


class BrokenModel:
    name = "broken"
    licence = "test"

    def predict(self, inputs, horizon):
        raise RuntimeError("weights not available")


@pytest.fixture(scope="session")
def net():
    return load_network(None)


@pytest.fixture
def settings():
    return Settings(data_source="synthetic", contender="", backtest_days=1, backtest_stride_hours=12,
                    context_days=7)


@pytest.fixture
def naive():
    return SeasonalNaive()
