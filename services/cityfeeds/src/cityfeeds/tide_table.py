"""The PUBLISHED Hooghly tide table (Garden Reach / Kolkata), read live from the port when it answers.

Syama Prasad Mookerjee Port, Kolkata publishes the river's tidal notices and tables (prepared with the Survey of
India from the port's gauges at Tribeni, Garden Reach, Diamond Harbour and Haldia) on ``smp.smportkolkata.in``.

* **The certificate.** The site's certificate expired on 17 Oct 2026. ``tls.py`` holds the one narrow exception:
  for this host only the chain and host name are verified but not the dates, and only the pinned certificate (or a
  renewed, currently valid one) is accepted. Every other host keeps full verification.
* **The page.** ``GET /smpk/en/tidal-notices/`` (the port's "Port Info → Tidal Notices"), every 6 hours. Checked
  from this box on 29 Oct 2026 over the pinned connection: the site answers **HTTP 404 "No Such URL."** for that
  page and for every other content path under ``/smpk/en/`` (the root shows the web server's test page, 403).
  Its last archived copy (Internet Archive, 13 May 2025) shows an empty notices table filled by script: there was
  no machine-readable table even then.
* **What is shown.** ``published`` says exactly what the port answered and when (``UNAVAILABLE`` with the HTTP
  status and the port's own words; ``LINKED`` when the page answers and lists notices: their titles and links,
  the tables themselves are PDFs and are not parsed, so no published heights are claimed). ``modelled`` is the
  hydro service's high and low waters (``GET /hydro/tide``, Garden Reach transferred from Diamond Harbour
  constants), the reference the city works from. ``compare()`` is ready for a parsed published table: it pairs
  each published high/low water with the nearest modelled one of the same kind and reports the errors.
"""

from __future__ import annotations

import html
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin

import httpx

from cityfeeds.tls import PORT_PIN_REASON

__all__ = ["fetch_hydro_tide", "fetch_port_notices", "port_notices", "tide_table_view", "compare", "PORT_URL",
           "PORT_CHECK"]

PORT_URL = "https://smp.smportkolkata.in/smpk/en/tidal-notices/"
PORT_CHECK = {
    "publisher": "Syama Prasad Mookerjee Port, Kolkata",
    "url": PORT_URL,
    "tls": PORT_PIN_REASON,
    "other_hosts": "kolkataporttrust.gov.in presents another site's certificate (name mismatch); smportkolkata.in "
                   "presents kdsgst.smportkolkata.in's (name mismatch); neither is used",
}
_TIDE_WORDS = re.compile(r"tide|tidal|predicted|high water|low water", re.I)


async def fetch_port_notices(client: httpx.AsyncClient, url: str = PORT_URL) -> dict[str, Any]:
    """One read of the port's Tidal Notices page: its status, the port's own words on an error, and the page.
    A 4xx/5xx is an ANSWER (recorded with its status), not a failure; a connection or pin failure raises."""
    r = await client.get(url)
    body = r.text if r.status_code == 200 else ""
    return {"status": r.status_code, "url": str(r.url), "checked_at": datetime.now(UTC).isoformat(),
            "said": " ".join(re.sub(r"<[^>]+>", " ", r.text[:400]).split())[:80] if r.status_code != 200 else None,
            "page": body[:2_000_000]}


def port_notices(raw: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Tide notices listed on the page (title and link; the tables are PDFs and are not parsed)."""
    out, seen = [], set()
    page = re.sub(r"<!--.*?-->", "", (raw or {}).get("page") or "", flags=re.S)
    for m in re.finditer(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', page, re.S | re.I):
        text = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", m.group(2))).split())[:200]
        link = urljoin((raw or {}).get("url") or PORT_URL, m.group(1))
        if not text or not _TIDE_WORDS.search(f"{text} {m.group(1)}") or link in seen:
            continue
        if not link.startswith("https://smp.smportkolkata.in/") or link.rstrip("/").endswith("tidal-notices"):
            continue
        seen.add(link)
        out.append({"title": text, "link": link, "publisher": "Syama Prasad Mookerjee Port, Kolkata"})
    return out[:20]


async def fetch_hydro_tide(client: httpx.AsyncClient, hydro_url: str) -> Any:
    r = await client.get(f"{hydro_url.rstrip('/')}/hydro/tide", params={"hours": 48})
    r.raise_for_status()
    return r.json()


def compare(published: list[dict], modelled: list[dict]) -> dict[str, Any]:
    """Each published extreme vs the nearest modelled extreme of the same kind: minutes and metres apart."""
    pairs = []
    for p in published:
        pt = datetime.fromisoformat(p["at"])
        same = [m for m in modelled if m["kind"] == p["kind"]]
        if not same:
            continue
        m = min(same, key=lambda m: abs((datetime.fromisoformat(m["at"]) - pt).total_seconds()))
        pairs.append({"kind": p["kind"], "published_at": p["at"], "modelled_at": m["at"],
                      "dt_min": round((datetime.fromisoformat(m["at"]) - pt).total_seconds() / 60),
                      "published_m": p["level_m"], "modelled_m": m["level_m"],
                      "dh_m": round(m["level_m"] - p["level_m"], 2)})
    if not pairs:
        return {"pairs": [], "mean_abs_dt_min": None, "mean_abs_dh_m": None}
    return {"pairs": pairs,
            "mean_abs_dt_min": round(sum(abs(x["dt_min"]) for x in pairs) / len(pairs)),
            "mean_abs_dh_m": round(sum(abs(x["dh_m"]) for x in pairs) / len(pairs), 2)}


def _published(port: dict[str, Any] | None, port_error: str | None, port_mode: str | None,
               port_at: str | None) -> dict[str, Any]:
    base = {**PORT_CHECK, "highs_lows": [], "checked_at": (port or {}).get("checked_at") or port_at,
            "mode": port_mode}
    if port is None:
        return {**base, "label": "UNAVAILABLE", "status": None,
                "result": f"the port's site did not answer: {port_error or 'no answer yet'}"}
    status = port.get("status")
    if status != 200:
        return {**base, "label": "UNAVAILABLE", "status": status,
                "result": f"the port's site answers HTTP {status}" + (f' "{port["said"]}"' if port.get("said") else "")
                          + " for its Tidal Notices page (connection verified with the pinned certificate)"}
    items = port_notices(port)
    if not items:
        return {**base, "label": "UNAVAILABLE", "status": 200,
                "result": "the Tidal Notices page answers but lists no tide notice this service can read "
                          "(its table is filled by script)"}
    return {**base, "label": "LINKED", "status": 200, "notices": items,
            "result": f"{len(items)} tide notice(s) listed by the port; the tables are PDFs and are not parsed, so "
                      "no published heights are shown"}


def tide_table_view(hydro: dict | None, hydro_error: str | None = None, port: dict | None = None,
                    port_error: str | None = None, port_mode: str | None = None,
                    port_at: str | None = None) -> dict[str, Any]:
    extremes = (hydro or {}).get("extremes") or []
    published = _published(port, port_error, port_mode, port_at)
    return {
        "published": published,
        "modelled": {"label": "MODELLED", "source": "Sahoshi hydro service, GET /hydro/tide (Garden Reach, approximate)",
                     "station": (hydro or {}).get("station"), "now": (hydro or {}).get("now"),
                     "highs_lows": extremes, "error": hydro_error},
        "comparison": {"status": "not possible: no published table could be read (" + published["label"] + ")",
                       "method": "nearest modelled extreme of the same kind; minutes and metres apart"},
    }
