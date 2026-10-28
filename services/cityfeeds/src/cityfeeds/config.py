"""Configuration — every value overridable by environment (prefix ``SAHOSHI_FEEDS_``), none secret.

Production port 8199 (``infra/systemd/sahoshi-feeds.service``, loopback only); ``PORT`` / ``HOST`` override.

The open feeds need no key. Five free services need a personal key, read from the environment by its own name
(``WAQI_TOKEN``, ``OPENAQ_API_KEY``, ``DATA_GOV_IN_API_KEY``, ``FIRMS_MAP_KEY``, ``MAPILLARY_TOKEN``; see
``keys.py``): without it that source makes no call and says ``needs <ENV_VAR>``. Each feed has its own polite schedule (``FEEDS`` in ``fetch.py``: a cache
age, a minimum interval between calls and a daily cap). ``offline=1`` never calls out: every feed answers from
the recorded fixtures in ``src/cityfeeds/fixtures/`` and says so (label ``RECORDED``), which is what the tests
and an air-gapped box use.
"""

from __future__ import annotations

import os

from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["Settings", "get_settings"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SAHOSHI_FEEDS_", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8199
    deck_origins: tuple[str, ...] = ("http://127.0.0.1:5373", "http://localhost:5373")

    #: no outbound call at all: the recorded fixtures answer, labelled RECORDED
    offline: bool = False
    http_timeout_sec: float = 20.0
    #: multiply every feed's cache age (tests use 0; a slow link may use 2)
    cache_scale: float = 1.0

    open_meteo_air_url: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
    open_meteo_forecast_url: str = "https://api.open-meteo.com/v1/forecast"
    gdacs_list_url: str = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
    gdacs_geometry_url: str = "https://www.gdacs.org/gdacsapi/api/polygons/getgeometry"
    usgs_url: str = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    cwc_base_url: str = "https://ffs.india-water.gov.in/iam/api"
    kmc_portal_url: str = "https://www.kmcgov.in/KMCPortal/jsp/KMCPortalHome1.jsp"
    ktp_url: str = "https://kolkatatrafficpolice.gov.in/"
    port_tide_url: str = "https://smp.smportkolkata.in/smpk/en/tidal-notices/"
    #: the hydro service's modelled tide (compared with a published table when one is available)
    hydro_url: str = "http://127.0.0.1:8197"

    #: quakes within this radius of the city centre
    quake_radius_km: float = 500.0
    #: a cyclone or flood event is "regional" inside this box (Bay of Bengal and the land around it)
    region_south: float = 5.0
    region_west: float = 78.0
    region_north: float = 28.0
    region_east: float = 100.0


def get_settings() -> Settings:
    s = Settings()
    if os.environ.get("PORT"):
        s.port = int(os.environ["PORT"])
    if os.environ.get("HOST"):
        s.host = os.environ["HOST"]
    return s
