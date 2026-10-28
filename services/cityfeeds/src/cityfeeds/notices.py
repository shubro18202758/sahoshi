"""Civic notices about places and roads, from public pages that allow it.

Checked from this box on 28 Oct 2026:

* **Kolkata Traffic Police** (kolkatatrafficpolice.gov.in): the home page lists the department's current traffic
  advisories (PDF links: diversions, closures). Its server lacks RFC 5746 secure renegotiation, which OpenSSL 3
  refuses by default; ``tls.py`` allows exactly that for this host (its GeoTrust certificate and host name are
  verified as usual). ``/robots.txt`` answers 404 (no crawl rules); one read every 6 hours. Only links whose text
  reads as an advisory (advisory, diversion, closure, restriction, notification, circulation) are kept, never the
  page's menu, and advisories commented out of the page's HTML (withdrawn) are never read. Label: LIVE.
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

__all__ = ["fetch_notices", "notices_view", "ktp_advisories", "KTP_URL", "PLACE_WORDS", "PERSON_WORDS"]

KTP_URL = "https://kolkatatrafficpolice.gov.in/"
KTP_ADVISORY = re.compile(r"\b(advisor\w*|diversion|divert\w*|closure|closed|restriction\w*|notification|"
                          r"circulation|traffic arrangement\w*)\b", re.I)

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


def ktp_advisories(page: str | None, base_url: str = KTP_URL) -> list[dict[str, Any]]:
    """The Traffic Police home page's current advisories (title and link), never its menu or withdrawn ones."""
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    live = re.sub(r"<!--.*?-->", "", page or "", flags=re.S)  # a commented-out advisory is withdrawn
    for m in re.finditer(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', live, re.S | re.I):
        href, text = m.group(1).strip(), " ".join(html.unescape(re.sub(r"<[^>]+>", " ", m.group(2))).split())
        if len(text) < 30 or not KTP_ADVISORY.search(text) or PERSON_WORDS.search(text):
            continue
        link = urljoin(base_url, href.replace(" ", "%20"))
        key = f"{link}\n{text}"  # two advisories may share one PDF
        if not link.startswith(base_url) or key in seen:
            continue
        seen.add(key)
        items.append({"title": text[:200], "link": link, "date": _date(href), "publisher": "Kolkata Traffic Police",
                      "label": "LIVE"})
    return items[:20]


def notices_view(page: str | None, base_url: str, since: str = "2025-01-01", ktp_page: str | None = None,
                 ktp_error: str | None = None) -> dict[str, Any]:
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
    ktp = ktp_advisories(ktp_page) if ktp_page else []
    return {
        "label": "LIVE" if (page or ktp_page) else "UNAVAILABLE",
        "what": "KMC public-portal notices about places and roads, and the Kolkata Traffic Police's current traffic "
                "advisories (titles and links only)",
        "items": items[:20] + ktp,
        "sources": [
            {"publisher": "Kolkata Municipal Corporation", "url": base_url, "robots": "no robots.txt (404): no crawl rules",
             "status": "read" if page else "no answer"},
            {"publisher": "Kolkata Traffic Police", "url": KTP_URL, "robots": "no robots.txt (404): no crawl rules",
             "tls": "legacy TLS server: renegotiation allowance for this host only; certificate verified",
             "status": (f"read: {len(ktp)} current advisor{'y' if len(ktp) == 1 else 'ies'}" if ktp_page
                        else f"no answer: {ktp_error or 'not read yet'}")},
        ],
    }
