"""Record the offline fixtures (``src/cityfeeds/fixtures/``) from the live feeds, once, politely.

    PYTHONPATH=src python scripts/record_fixtures.py

Each fixture is the RAW answer the service's fetch function returns (GDACS polygons decimated to keep the file
small), so offline mode and the tests run the same parsing code as production. Re-record only on purpose: the
tests pin values from the recorded day (28 Oct 2026).
"""

from __future__ import annotations

import asyncio
import json
import re
import sys

import httpx

from cityfeeds.air import fetch_air
from cityfeeds.config import Settings
from cityfeeds.cyclones import fetch_cyclones
from cityfeeds.fetch import FIXTURES, USER_AGENT
from cityfeeds.geo import decimate
from cityfeeds.heat import fetch_heat
from cityfeeds.notices import PERSON_WORDS, PLACE_WORDS, fetch_notices
from cityfeeds.quakes import fetch_quakes
from cityfeeds.river import DVC_TERMS, fetch_news, fetch_river
from cityfeeds.tide_table import fetch_hydro_tide


def _slim_gdacs(raw: dict) -> dict:
    for g in raw.get("geometry", {}).values():
        for f in g.get("features", []):
            geom = f.get("geometry") or {}
            if geom.get("type") == "Polygon":
                geom["coordinates"] = [decimate(geom["coordinates"][0], 120)]
            for k in ("htmldescription", "icon", "iconoverall"):
                (f.get("properties") or {}).pop(k, None)
    for f in raw.get("events", {}).get("features", []):
        (f.get("properties") or {}).pop("htmldescription", None)
    return raw


async def main(only: set[str]) -> None:
    s = Settings()
    box = (s.region_south, s.region_west, s.region_north, s.region_east)
    async with httpx.AsyncClient(timeout=60, follow_redirects=True, headers={"user-agent": USER_AGENT}) as c:
        jobs = {
            "air.json": lambda: fetch_air(c, s.open_meteo_air_url),
            "heat.json": lambda: fetch_heat(c, s.open_meteo_forecast_url),
            "gdacs.json": lambda: fetch_cyclones(c, s.gdacs_list_url, s.gdacs_geometry_url, box),
            "cwc.json": lambda: fetch_river(c, s.cwc_base_url, {}),
            "news.json": lambda: fetch_news(c),
            "usgs.json": lambda: fetch_quakes(c, s.usgs_url, s.quake_radius_km),
            "kmc_portal.html": lambda: fetch_notices(c, s.kmc_portal_url),
            "hydro_tide.json": lambda: fetch_hydro_tide(c, s.hydro_url),
        }
        for name, job in jobs.items():
            if only and name not in only:
                continue
            try:
                data = await job()
            except Exception as exc:  # noqa: BLE001
                print(f"{name}: FAILED {type(exc).__name__}: {exc}")
                continue
            if name == "gdacs.json":
                data = _slim_gdacs(data)
            if name == "cwc.json":  # the fields the view reads
                for st in data["stations"].values():
                    st["obs"] = [{"id": o["id"], "dataValue": o["dataValue"]} for o in st["obs"]]
                    st["meta"] = {k: st["meta"].get(k) for k in ("name", "lat", "lon", "reservoir", "stationCode")}
                    st["static"] = {k: st["static"].get(k) for k in ("type", "warningLevel", "dangerLevel",
                                                                     "highestFlowLevel", "highestFlowLevelDate", "frl", "mwl")}
            if name == "kmc_portal.html":  # the download anchors only
                anchors = re.findall(r'<a[^>]*href="[^"]+"[^>]*>.*?</a>', data, re.S | re.I)
                # … and only those the notices filter has an opinion on (a place word, or a person word it must refuse)
                def relevant(a: str) -> bool:
                    hay = a.replace("_", " ")
                    return bool(PLACE_WORDS.search(hay) or PERSON_WORDS.search(hay))
                data = "<!-- KMC portal home, download anchors only -->\n" + "\n".join(
                    a for a in anchors if "/downloads/" in a.lower() and len(a) < 600 and relevant(a))
            if name == "news.json":  # links and dates only (a headline is kept only when it mentions a DVC release)
                for f in data["feeds"].values():
                    f["items"] = [{"title": it["title"] if DVC_TERMS.search(f"{it['title']} {it['description']}") else "",
                                   "description": "", "link": it["link"], "pubDate": it["pubDate"]} for it in f["items"][:40]]
            path = FIXTURES / name
            if name.endswith(".json"):
                path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            else:
                path.write_text(data, encoding="utf-8")
            print(f"{name}: {path.stat().st_size} bytes")


if __name__ == "__main__":
    asyncio.run(main(set(sys.argv[1:])))
