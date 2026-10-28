"""City-feeds HTTP surface (production :8199, loopback). Every route is a read; nothing here writes city state.

    GET /health                 service, per-feed schedule and usage, labels
    GET /feeds/summary          the god's-eye chips: air · heat · cyclone · river · quake · tide (value, band, label,
                                source, as-of)
    GET /feeds/air              ten WBPCB/CPCB sites: now, 24-h PM means, indicative National AQI, 48-h forecast;
                                the health-advisory PROPOSAL (বাংলা · English · हिंदी)
    GET /feeds/heat             Alipore and Dum Dum: heat index, IMD heatwave test; the duty-shift PROPOSAL
    GET /feeds/cyclones         GeoJSON: GDACS tracks, positions, wind buffers, cones, flood points; the
                                pre-positioning PROPOSAL
    GET /feeds/river            CWC observed levels at the DVC / lower-Damodar / Hooghly stations; DVC news mentions
    GET /feeds/quakes           GeoJSON: USGS events within 500 km, last 365 days
    GET /feeds/tide-table       the port's published tide notices (read live over the pinned connection; what the
                                port answered, honestly) and the hydro model's high and low waters
    GET /feeds/notices          KMC notices about places and roads; the Kolkata Traffic Police's current advisories
    GET /feeds/fires            GeoJSON: NASA FIRMS hotspots in the Kolkata Metropolitan Area (places, not people)
    GET /feeds/street-image     ?lat=&lon= the nearest public Mapillary photo (CC BY-SA 4.0), or "needs
                                MAPILLARY_TOKEN"; never calls the vision model
    GET /feeds/proposals        every drafted proposal, and why the others were not drafted

``?force=1`` refreshes past the cache (still inside the rate limits); the deck's public gate refuses it.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import structlog
import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from cityfeeds import __version__
from cityfeeds.config import Settings, get_settings
from cityfeeds.service import CityFeeds

logger = structlog.get_logger(__name__)

__all__ = ["create_app", "main"]

LABELS = {
    "air": "LIVE feed (Open-Meteo); values MODELLED (CAMS); National AQI INDICATIVE; OBSERVED station values beside "
           "them when a keyed provider (DATA_GOV_IN_API_KEY, WAQI_TOKEN, OPENAQ_API_KEY) is configured",
    "heat": "LIVE feed (Open-Meteo); values MODELLED; IMD heatwave test MODELLED on the forecast",
    "cyclones": "LIVE (GDACS); distances MODELLED",
    "river": "LIVE (CWC observed levels); DVC news mentions AGGREGATE",
    "quakes": "LIVE (USGS)",
    "tide_table": "PUBLISHED: the port's Tidal Notices page read LIVE (pinned certificate) and reported as it "
                  "answers; hydro tide MODELLED",
    "notices": "LIVE (KMC public portal; Kolkata Traffic Police advisories)",
    "fires": "LIVE (NASA FIRMS public files; the area API with FIRMS_MAP_KEY); satellite thermal anomalies, not "
             "confirmed fires",
    "street_image": "Reference photo · not live (Mapillary, CC BY-SA 4.0) with MAPILLARY_TOKEN",
}


def create_app(settings: Settings | None = None, feeds: CityFeeds | None = None) -> FastAPI:
    s = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.feeds = feeds or CityFeeds(s)
        warm = asyncio.create_task(app.state.feeds.keep_fresh())
        try:
            yield
        finally:
            warm.cancel()
            await app.state.feeds.f.aclose()

    app = FastAPI(title="Sahoshi city feeds", version=__version__, lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=list(s.deck_origins), allow_methods=["GET"], allow_headers=["*"])

    def cf() -> CityFeeds:
        return app.state.feeds

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "service": "cityfeeds", "version": __version__, "city": "kolkata",
                "offline": s.offline, "labels": LABELS, "fetcher": cf().f.status(),
                "keyed_sources": cf().keyed_sources()}

    @app.get("/feeds/summary")
    async def summary() -> dict:
        return await cf().summary()

    @app.get("/feeds/air")
    async def air(force: bool = Query(default=False)) -> dict:
        return await cf().air(force)

    @app.get("/feeds/heat")
    async def heat(force: bool = Query(default=False)) -> dict:
        return await cf().heat(force)

    @app.get("/feeds/cyclones")
    async def cyclones(force: bool = Query(default=False)) -> dict:
        return await cf().cyclones(force)

    @app.get("/feeds/river")
    async def river(force: bool = Query(default=False)) -> dict:
        return await cf().river(force)

    @app.get("/feeds/quakes")
    async def quakes(force: bool = Query(default=False)) -> dict:
        return await cf().quakes(force)

    @app.get("/feeds/tide-table")
    async def tide_table(force: bool = Query(default=False)) -> dict:
        return await cf().tide_table(force)

    @app.get("/feeds/notices")
    async def notices(force: bool = Query(default=False)) -> dict:
        return await cf().notices(force)

    @app.get("/feeds/fires")
    async def fires(force: bool = Query(default=False)) -> dict:
        return await cf().fires(force)

    @app.get("/feeds/street-image")
    async def street_image(lat: float = Query(ge=22.0, le=23.5), lon: float = Query(ge=87.8, le=89.0)) -> dict:
        return await cf().street_image(lat, lon)

    @app.get("/feeds/proposals")
    async def proposals() -> dict:
        return await cf().proposals()

    return app


def main() -> None:
    s = get_settings()
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(20))
    logger.info("cityfeeds.starting", host=s.host, port=s.port, offline=s.offline)
    uvicorn.run(create_app(s), host=s.host, port=s.port, log_level="info")
