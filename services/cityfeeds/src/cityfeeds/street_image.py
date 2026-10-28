"""A public street-level photograph near a junction (Mapillary), for the road-state feature's stills.

With ``MAPILLARY_TOKEN`` (free: https://www.mapillary.com/dashboard/developers, a client token) the Mapillary Graph
API is asked for the images within about 60 m of a point (``/images?bbox=…``); the nearest one is returned with
its thumbnail URL, capture time, compass angle and the attribution its licence requires. Without the token no call
is made and the answer says ``needs MAPILLARY_TOKEN``.

* **Licence.** Mapillary images are CC BY-SA 4.0. The attribution returned is "© Mapillary contributors, CC BY-SA
  4.0" with the image's own page on mapillary.com, where the contributor is credited; the contributor's user name
  is not fetched (places, not people).
* **Privacy.** Mapillary blurs faces and number plates before it publishes an image. Sahoshi stores nothing: the
  answer is a link to Mapillary's own thumbnail.
* **Honest label.** A Mapillary image is a past photograph, labelled "Reference photo · not live" with its capture
  date. This module never calls the vision model; the road-state feature decides what to do with the still.
* **Polite.** Lookups are cached per point (rounded to ~100 m) for 24 hours, at most 500 calls a day.
"""

from __future__ import annotations

import math
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from cityfeeds.geo import haversine_km

__all__ = ["GRAPH_URL", "StreetImages", "parse_images"]

GRAPH_URL = "https://graph.mapillary.com/images"
_FIELDS = "id,thumb_1024_url,thumb_256_url,captured_at,compass_angle,computed_geometry,geometry,is_pano"
_HALF_SIDE_M = 60.0
_TTL_SEC = 24 * 3600
_MAX_PER_DAY = 500
_MAX_CACHE = 500


def _bbox(lat: float, lon: float, half_m: float = _HALF_SIDE_M) -> str:
    dlat = half_m / 111_320.0
    dlon = half_m / (111_320.0 * max(0.1, math.cos(math.radians(lat))))
    return f"{lon - dlon:.6f},{lat - dlat:.6f},{lon + dlon:.6f},{lat + dlat:.6f}"


def parse_images(body: dict[str, Any] | None, lat: float, lon: float) -> dict[str, Any] | None:
    """The nearest non-panoramic image (a panorama does not show one approach), as the public answer."""
    best = None
    for im in (body or {}).get("data") or []:
        if not isinstance(im, dict) or im.get("is_pano") or not im.get("thumb_1024_url"):
            continue
        g = im.get("computed_geometry") or im.get("geometry") or {}
        try:
            ilon, ilat = float(g["coordinates"][0]), float(g["coordinates"][1])
        except (KeyError, IndexError, TypeError, ValueError):
            continue
        d = haversine_km(lat, lon, ilat, ilon) * 1000
        if best is None or d < best[0]:
            best = (d, im, ilat, ilon)
    if best is None:
        return None
    d, im, ilat, ilon = best
    cap = im.get("captured_at")
    captured = datetime.fromtimestamp(cap / 1000, UTC).isoformat() if isinstance(cap, (int, float)) else None
    iid = str(im.get("id"))
    return {
        "id": iid, "thumb_url": im.get("thumb_1024_url"), "thumb_small_url": im.get("thumb_256_url"),
        "captured_at": captured, "compass_angle": im.get("compass_angle"),
        "lat": round(ilat, 6), "lon": round(ilon, 6), "distance_m": round(d),
        "page_url": f"https://www.mapillary.com/app/?pKey={iid}",
        "label": "Reference photo · not live",
        "attribution": "© Mapillary contributors, CC BY-SA 4.0 (faces and number plates blurred by Mapillary)",
        "licence": "CC BY-SA 4.0", "licence_url": "https://creativecommons.org/licenses/by-sa/4.0/",
    }


class StreetImages:
    """Per-point cache in front of the Graph API (module docstring)."""

    def __init__(self, clock=time.time) -> None:
        self._cache: dict[tuple[float, float], tuple[float, dict[str, Any] | None]] = {}
        self._clock = clock
        self._day = ""
        self._calls = 0

    async def near(self, client: httpx.AsyncClient, token: str, lat: float, lon: float) -> dict[str, Any]:
        k = (round(lat, 3), round(lon, 3))
        now = self._clock()
        hit = self._cache.get(k)
        if hit and now - hit[0] < _TTL_SEC:
            return {"image": hit[1], "cached": True}
        day = datetime.fromtimestamp(now, UTC).date().isoformat()
        if day != self._day:
            self._day, self._calls = day, 0
        if self._calls >= _MAX_PER_DAY:
            raise RuntimeError(f"daily cap reached ({_MAX_PER_DAY} Mapillary lookups)")
        self._calls += 1
        r = await client.get(GRAPH_URL, params={"bbox": _bbox(lat, lon), "fields": _FIELDS, "limit": 20},
                             headers={"Authorization": f"OAuth {token}"})
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code} from Mapillary")
        img = parse_images(r.json(), lat, lon)
        if len(self._cache) >= _MAX_CACHE:
            self._cache.pop(next(iter(self._cache)))
        self._cache[k] = (now, img)
        return {"image": img, "cached": False}
