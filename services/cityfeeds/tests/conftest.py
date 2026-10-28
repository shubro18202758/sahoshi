from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from cityfeeds.api import create_app
from cityfeeds.config import Settings
from cityfeeds.service import CityFeeds

#: the fixtures were recorded on 28 Oct 2026 around 15:30 UTC (21:00 IST)
NOW = datetime(2026, 10, 28, 15, 50, tzinfo=UTC)


@pytest.fixture
def feeds() -> CityFeeds:
    return CityFeeds(Settings(offline=True), clock=lambda: NOW)


@pytest.fixture
def client(feeds):
    app = create_app(Settings(offline=True), feeds=feeds)
    with TestClient(app) as c:
        yield c
