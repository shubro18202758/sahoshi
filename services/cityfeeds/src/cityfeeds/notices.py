"""Civic notices about places and roads, from public pages that allow it.

Checked from this box on 28 Oct 2026:

* **Kolkata Police / Kolkata Traffic Police** (kolkatapolice.gov.in, kolkatatrafficpolice.gov.in): the http sites
  redirect to https, and the https connection does not complete from this box, so neither robots.txt nor the
  advisory pages can be read. DROPPED (the response says so); the platform's news OSINT still carries traffic
  advisories as reported by the outlets.
* **KMC** (www.kmcgov.in): the public portal home lists notices and downloads; ``/robots.txt`` answers 404 (no
  crawl rules), so one polite read every 6 hours is fine. kmc.wb.gov.in (the circulars page) does not answer.

From the KMC portal only notices about PLACES AND ROADS are kept — a whitelist of words (road, parking, traffic,
drain, desilting, waterlogging, monsoon, water supply, construction, bridge, AQI / air quality, tree, park, ghat,
market) — and never anything about a person (no names, no hearings, no individual cases). Each item is the
notice's own title and link, dated when its file name carries a date. Label: LIVE (KMC public page).
"""

from __future__ import annotations

import html
import re
from datetime import date
from typing import Any
from urllib.parse import urljoin

import httpx

__all__ = ["fetch_notices", "notices_view", "PLACE_WORDS", "PERSON_WORDS"]

PLACE_WORDS = re.compile(r"\b(road|roads|parking|traffic|drain\w*|desilt\w*|waterlog\w*|monsoon|water supply|"
                         r"construction|bridge|flyover|aqi|air quality|tree|trees|park|ghat|market|pond|canal|"
                         r"pumping|sewer\w*|street|lane)\b", re.I)
PERSON_WORDS = re.compile(r"\b(hearing|ex-gratia|deaths?|disabilit\w*|harassment|mutation|appointment|recruit\w*|candidate|"
                          r"vaccination|tender|mayor|councillor|personal)\b", re.I)
_DATE_IN_NAME = re.compile(r"(\d{2})_(\d{2})_(\d{4})|(\d{2})(\d{2})(20\d{2})")


def _date(href: str) -> str | None:
    m = _DATE_IN_NAME.search(href)
    if not m:
        return None
    d, mo, y = (m.group(1), m.group(2), m.group(3)) if m.group(1) else (m.group(4), m.group(5), m.group(6))
    try:
        return date(int(y), int(mo), int(d)).isoformat()
    except ValueError:
        return None


async def fetch_notices(client: httpx.AsyncClient, url: str) -> str:
    r = await client.get(url)
    r.raise_for_status()
    return r.text


def notices_view(page: str | None, base_url: str, since: str = "2025-01-01") -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for m in re.finditer(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', page or "", re.S | re.I):
        href, text = m.group(1), " ".join(html.unescape(re.sub(r"<[^>]+>", " ", m.group(2))).split())
        if "/downloads/" not in href.lower() or not text:
            continue
        text = text.split("-->")[0].strip()[:160]
        hay = f"{text} {href}"
        if not PLACE_WORDS.search(hay.replace("_", " ")) or PERSON_WORDS.search(hay.replace("_", " ")):
            continue
        link = urljoin(base_url, href.replace("//downloads", "/downloads"))
        if link in seen:
            continue
        seen.add(link)
        when = _date(href)
        if when is not None and when < since:
            continue
        items.append({"title": text, "link": link, "date": when, "publisher": "KMC", "label": "LIVE"})
    items.sort(key=lambda x: x["date"] or "", reverse=True)
    return {
        "label": "LIVE" if page else "UNAVAILABLE",
        "what": "KMC public-portal notices about places and roads (titles and links only)",
        "items": items[:20],
        "sources": [
            {"publisher": "Kolkata Municipal Corporation", "url": base_url, "robots": "no robots.txt (404): no crawl rules",
             "status": "read" if page else "no answer"},
            {"publisher": "Kolkata Police / Kolkata Traffic Police", "url": "https://kolkatatrafficpolice.gov.in/",
             "status": "dropped: the https site does not answer from this box (checked 28 Oct 2026)"},
        ],
    }
