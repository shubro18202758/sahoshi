"""Official sources: NDMA SACHET CAP, IMD's CAP feed, and the KMC, WBSDMA and Kolkata Police pages. Official
inputs are authoritative and cooperative: Sahoshi feeds the city's channels, it never second-guesses them.

SACHET (``sachet_cap``):

* the **all-India** CAP RSS, every 5 min (no West Bengal file is published under a known name: the state file
  names tried answer 404); ``OFFICIAL-VERIFIED``, credibility 0.95, public domain (``SOURCE_PRIORS``). On
  2026-10-28 the feed answered 403 to the service's user agent in the morning and 200 at 17:00 IST: a refusal is a
  failure like any other, so the newest cached copy is served (``cached-sample``) until it answers again;
* every item is read through :func:`~._area.match_area` (title, description, and the CAP headline and
  ``areaDesc`` when the detail is cached): an alert naming a metro district keeps that level (plan R28:
  ``LGD:KOLKATA``, ``LGD:HOWRAH``, ``LGD:NORTH_24_PARGANAS``, ``LGD:SOUTH_24_PARGANAS``); a West Bengal alert
  naming none of them is the **state** (``LGD:WEST_BENGAL``: the state-wide nowcasts that name Bankura or Purba
  Medinipur are not Kolkata locations, and OS-3/OS-4 hold them as outside the city); every other alert (another
  state's, Andaman and Nicobar's) is not emitted (counted ``outside_area``);
* IMD's Kolkata office writes its West Bengal nowcasts in Bengali: an item's ``language`` follows its script
  (:func:`~.base.script_language`), whatever the feed's ``<language>`` says;
* ``fetch`` also caches the full CAP 1.2 XML of up to ten new **West Bengal** alerts per cycle (best effort; a
  failure leaves the RSS-only signal; other states' alerts are never requested); ``parse`` reads it, when cached,
  for the expiry, severity, urgency, certainty, LGD district codes and the polygon URL. Every XML document goes
  through ``defusedxml``. The RSS ``author`` (an NDMA control-room mailbox) and the CAP ``sender``, ``contact``,
  ``addresses`` and ``note`` are never read;
* official URLs are kept (identifier-only paths, ``FetchXMLFile?identifier=...``).

IMD (``imd``): IMD's own CAP alerts as the WMO Alert Hub mirrors them (``in-imd-en``: the public RSS and, on the same
host, each alert's CAP 1.2 XML). The same area rule as SACHET; up to ten CAP details per cycle, from that host only.
The feed was live and empty on 2026-10-28.

Official pages (``kmc_scrape``, ``wbsdma``, ``kolkata_police_scrape``; hourly, best effort): stdlib
``html.parser`` only, robots.txt honoured (a disallowed path disables the connector: "robots.txt disallows",
raised as :class:`~.base.ConnectorDisabled`, so the cached page is NOT served in its place; an unreachable
robots.txt is a failure like any other), and a failure degrades to the cached page. Each notice-like same-site
link becomes one signal; paperwork links (tenders, forms, payments) are not notices. KMC's portal answers (no
robots.txt: a 404, so no restriction; its server offers RSA key exchange only, see ``safe_http.TLS_COMPAT``).

Kolkata Traffic Police (``kolkata_police_scrape``, enabled 2026-10-29): the home page of
``kolkatatrafficpolice.gov.in`` lists the department's current traffic advisories (PDF links: diversions,
closures). Its server lacks RFC 5746 secure renegotiation, which OpenSSL 3 refuses by default; that was the
"refused connection" of 2026-10-28. With the narrow ``TLS_COMPAT`` allowance its GeoTrust certificate and host
name verify as usual, and robots.txt answers 404 (no restriction). Only links whose text reads as an advisory
(advisory, diversion, closure, restriction, notification, circulation) are kept: the page's navigation (traffic-sign
charts, wardens, awards) is not a notice. Advisories commented out of the page's HTML are never read.

WBSDMA stays **disabled in code**: the West Bengal Disaster Management department's host (``wbdmd.gov.in``)
answers plain HTTP on port 443 (no TLS) and 503 over http (checked 2026-10-29), so nothing it serves can be
verified; it is not on the egress allow-list and nothing may be labelled ``OFFICIAL-VERIFIED`` from it.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import urllib.parse
from collections import Counter
from html.parser import HTMLParser
from typing import Any, ClassVar

import httpx

from osint_common.kinds import AREA_STATE_CODE
from osint_common.types import RawOsintSignal
from osint_ingress.cache import Cache, CacheEntry
from osint_ingress.connectors._area import AreaMatch, area_hint, match_area
from osint_ingress.connectors.base import (
    Connector,
    ConnectorDisabled,
    ConnectorError,
    Draft,
    build_signals,
    canonical_url,
    parse_xml,
    script_language,
    strip_html,
    url_sha256,
)
from osint_ingress.safe_http import ROBOTS_DISALLOWS, EgressRefused, FetchError, RobotsCache, fetch, network_reason

__all__ = [
    "CAP_URL",
    "IMD_HOST",
    "IMD_RSS_URL",
    "RSS_URL",
    "Imd",
    "KmcPage",
    "OfficialPage",
    "PolicePage",
    "Sachet",
    "WbsdmaPage",
    "cap_fields",
]

RSS_URL = "https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml"
CAP_URL = "https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier={identifier}"
SACHET_HOST = "sachet.ndma.gov.in"
IMD_HOST = "cap-sources.s3.amazonaws.com"
IMD_RSS_URL = f"https://{IMD_HOST}/in-imd-en/rss.xml"
#: The CAP alerts the IMD feed links to live beside it, under this prefix; nothing else is requested.
IMD_CAP_PREFIX = f"https://{IMD_HOST}/in-imd-en/"
#: IMD's issuing domain: the publisher of an ``imd`` signal (the mirror only re-serves IMD's alert).
IMD_PUBLISHER = "mausam.imd.gov.in"
_CAP = "{urn:oasis:names:tc:emergency:cap:1.2}"
_GUID = re.compile(r"^\d{6,32}$")
_CAP_ID = re.compile(r"[?&]identifier=([A-Za-z0-9_.\-]{1,64})")
_LGD_CODE = re.compile(r"^\d{1,6}$")
MAX_CAP_DETAILS_PER_CYCLE = 10


def _official_url(url: str | None, host: str) -> str | None:
    """``url`` when it is an https URL on ``host`` (an official identifier URL), else ``None``."""
    c = canonical_url(url)
    if not c or not c.startswith(f"https://{host}/"):
        return None
    return c


def cap_fields(data: bytes) -> dict[str, Any]:
    """The CAP 1.2 fields Sahoshi uses, from one alert (``defusedxml``). ``{}`` when it is not a CAP alert."""
    root = parse_xml(data)
    if root.tag != f"{_CAP}alert":
        return {}

    def t(el: Any, name: str) -> str:
        return ((el.findtext(_CAP + name) if el is not None else None) or "").strip()

    info = root.find(_CAP + "info")
    areas = info.findall(_CAP + "area") if info is not None else []
    lgd: list[str] = []
    polygon = None
    for area in areas:
        for gc in area.findall(_CAP + "geocode"):
            if t(gc, "valueName") == "LGD District Code" and _LGD_CODE.match(t(gc, "value")):
                lgd.append(t(gc, "value"))
    if info is not None:
        for p in info.findall(_CAP + "parameter"):
            if t(p, "valueName") == "Polygon URL":
                polygon = _official_url(t(p, "value"), SACHET_HOST)
    return {
        "identifier": t(root, "identifier"),
        "sent": t(root, "sent"),
        "status": t(root, "status"),
        "msg_type": t(root, "msgType"),
        "scope": t(root, "scope"),
        "category": t(info, "category"),
        "event": t(info, "event"),
        "urgency": t(info, "urgency"),
        "severity": t(info, "severity"),
        "certainty": t(info, "certainty"),
        "effective": t(info, "effective"),
        "onset": t(info, "onset"),
        "expires": t(info, "expires"),
        "headline": t(info, "headline"),
        "description": t(info, "description"),
        "area_desc": "; ".join(d for d in (t(a, "areaDesc") for a in areas) if d)[:1000],
        "lgd_codes": lgd,
        "polygon_url": polygon,
    }


def _cap_draft(
    *,
    source_id: str,
    title: str,
    desc: str,
    pub: str,
    url: str | None,
    publisher: str,
    category: str,
    cap: dict[str, Any],
    area: AreaMatch,
    extra_hints: tuple[str, ...] = (),
) -> Draft:
    """One CAP alert (RSS item plus its cached detail) as a draft, at the level its area names."""
    text = title + (". " + desc if desc else "")
    extra = cap.get("description") or ""
    if extra and extra not in text:
        text = f"{text}. {extra}"
    cap_category = cap.get("category") or category
    polygon = cap.get("polygon_url")
    return Draft(
        source_id=source_id,
        title=title,
        text=text[:1000],
        published_at=pub or cap.get("sent"),
        valid_until=cap.get("expires"),
        url=url,
        publisher=publisher,
        language=script_language(title or text),
        place_names=list(area.place_names),
        admin_codes=area.admin_codes,
        polygon_url=polygon,
        geo_confidence=0.3 if area.districts else 0.1,
        category_hint=[
            h
            for h in ("CAP", f"CAP:{cap_category}" if cap_category else "", *area_hint(area),
                      f"CAP_EVENT:{cap['event']}" if cap.get("event") else "", *extra_hints)
            if h
        ],
        raw={
            "cap_identifier": cap.get("identifier") or source_id,
            "cap_category": cap_category or None,
            "cap_sent": cap.get("sent") or None,
            "cap_status": cap.get("status") or None,
            "cap_msg_type": cap.get("msg_type") or None,
            "cap_scope": cap.get("scope") or None,
            "cap_event": cap.get("event") or None,
            "cap_urgency": cap.get("urgency") or None,
            "cap_severity": cap.get("severity") or None,
            "cap_certainty": cap.get("certainty") or None,
            "cap_effective": cap.get("effective") or None,
            "cap_onset": cap.get("onset") or None,
            "cap_expires": cap.get("expires") or None,
            "cap_area_code": ",".join(cap.get("lgd_codes") or [])[:512] or None,
            "cap_polygon_id": (m.group(1) if polygon and (m := _CAP_ID.search(polygon)) else None),
        },
    )


def _detail(conn: Connector, entry: CacheEntry, blob: str) -> dict[str, Any]:
    path = entry.blob_path(blob)
    if path is None:
        return {}
    try:
        return cap_fields(path.read_bytes())
    except ConnectorError:
        conn.last_dropped["cap_detail_refused"] += 1
        return {}


def _item_text(item: Any) -> tuple[str, str, str, str, str, str]:
    """``(title, guid, link, pubDate, description text, category)`` of an RSS item (never its ``author``)."""
    return (
        (item.findtext("title") or "").strip(),
        (item.findtext("guid") or "").strip(),
        (item.findtext("link") or "").strip(),
        (item.findtext("pubDate") or "").strip(),
        strip_html(item.findtext("description") or ""),
        (item.findtext("category") or "").strip(),
    )


class Sachet(Connector):
    """NDMA SACHET CAP alerts (the all-India RSS, kept to West Bengal; plus the CAP detail of new ones)."""

    name = "sachet_cap"
    default_cadence_sec = 300
    max_bytes = 4 * 1024 * 1024
    #: polite spacing between CAP detail requests (seconds)
    detail_spacing_sec: float = 0.5

    async def fetch(self, client: httpx.AsyncClient, cache: Cache) -> CacheEntry | None:
        res = await fetch(client, RSS_URL, max_bytes=self.max_bytes)
        if not res.ok:
            raise ConnectorError(f"HTTP {res.status}")
        root = parse_xml(res.content)
        ids: list[str] = []
        for item in root.iter("item"):
            title, gid, _link, _pub, desc, _cat = _item_text(item)
            # only West Bengal alerts are worth a detail request: the rest of India is never asked for
            if _GUID.match(gid) and match_area(title, desc).in_area:
                ids.append(gid)
        fetched = 0
        for gid in ids:
            blob = f"cap-{gid}.xml"
            if cache.blob_path(self.name, blob) is not None:
                continue
            if fetched >= MAX_CAP_DETAILS_PER_CYCLE:
                break
            fetched += 1
            try:
                if fetched > 1 and self.detail_spacing_sec:
                    await asyncio.sleep(self.detail_spacing_sec)
                cres = await fetch(client, CAP_URL.format(identifier=gid), max_bytes=512 * 1024)
                if cres.ok and cap_fields(cres.content):
                    cache.put_blob(self.name, blob, cres.content)
            except (FetchError, ConnectorError, EgressRefused, httpx.HTTPError):
                # the CAP detail is an enrichment: the RSS alert still stands without it (also when one detail
                # URL redirects off the allow-list: that request is refused, the rest of the fetch goes on)
                continue
        blobs = [f"cap-{g}.xml" for g in ids if cache.blob_path(self.name, f"cap-{g}.xml") is not None]
        return cache.put(self.name, res.content, "xml", blobs=blobs)

    def parse(self, entry: CacheEntry, protect: frozenset[str]) -> list[RawOsintSignal]:
        self.last_dropped = Counter()
        root = parse_xml(entry.read_bytes(self.max_bytes))
        drafts: list[Draft] = []
        for item in root.iter("item"):
            title, guid, link, pub, desc, category = _item_text(item)
            cap = _detail(self, entry, f"cap-{guid}.xml") if _GUID.match(guid) else {}
            area = match_area(title, desc, cap.get("headline"), cap.get("area_desc"))
            if not area.in_area:
                self.last_dropped["outside_area"] += 1
                continue
            source_id = guid or (f"url-sha256:{url_sha256(link)}" if url_sha256(link) else "")
            if not source_id or not title:
                continue
            drafts.append(_cap_draft(source_id=source_id, title=title, desc=desc, pub=pub,
                                     url=_official_url(link, SACHET_HOST), publisher=SACHET_HOST,
                                     category=category, cap=cap, area=area))
        return build_signals(self.name, drafts, entry, protect, dropped=self.last_dropped)


class Imd(Connector):
    """IMD CAP alerts from the WMO Alert Hub mirror (``in-imd-en``), kept to West Bengal."""

    name = "imd"
    default_cadence_sec = 600
    max_bytes = 4 * 1024 * 1024
    detail_spacing_sec: float = 0.5

    @staticmethod
    def _blob(link: str) -> str | None:
        """The detail's blob name (``cap-<sha256 prefix>.xml``) for a CAP link on the mirror, else ``None``."""
        url = _official_url(link, IMD_HOST)
        if not url or not url.startswith(IMD_CAP_PREFIX):
            return None
        return f"cap-{hashlib.sha256(url.encode('utf-8')).hexdigest()[:32]}.xml"

    async def fetch(self, client: httpx.AsyncClient, cache: Cache) -> CacheEntry | None:
        res = await fetch(client, IMD_RSS_URL, max_bytes=self.max_bytes)
        if not res.ok:
            raise ConnectorError(f"HTTP {res.status}")
        root = parse_xml(res.content)
        wanted: list[tuple[str, str]] = []
        for item in root.iter("item"):
            _title, _gid, link, _pub, _desc, _cat = _item_text(item)
            blob = self._blob(link)
            # the area is read from the detail too (the RSS title may name only the event): each new detail is
            # requested once, within the per-cycle cap, and only from the mirror's own CAP prefix
            if blob is not None:
                wanted.append((blob, _official_url(link, IMD_HOST) or ""))
        fetched = 0
        for blob, url in wanted:
            if cache.blob_path(self.name, blob) is not None:
                continue
            if fetched >= MAX_CAP_DETAILS_PER_CYCLE:
                break
            fetched += 1
            try:
                if fetched > 1 and self.detail_spacing_sec:
                    await asyncio.sleep(self.detail_spacing_sec)
                cres = await fetch(client, url, max_bytes=512 * 1024)
                if cres.ok and cap_fields(cres.content):
                    cache.put_blob(self.name, blob, cres.content)
            except (FetchError, ConnectorError, EgressRefused, httpx.HTTPError):
                continue
        blobs = [b for b, _u in wanted if cache.blob_path(self.name, b) is not None]
        return cache.put(self.name, res.content, "xml", blobs=list(dict.fromkeys(blobs)))

    def parse(self, entry: CacheEntry, protect: frozenset[str]) -> list[RawOsintSignal]:
        self.last_dropped = Counter()
        root = parse_xml(entry.read_bytes(self.max_bytes))
        drafts: list[Draft] = []
        for item in root.iter("item"):
            title, guid, link, pub, desc, category = _item_text(item)
            blob = self._blob(link)
            cap = _detail(self, entry, blob) if blob else {}
            area = match_area(title, desc, cap.get("headline"), cap.get("area_desc"), cap.get("description"))
            if not area.in_area:
                self.last_dropped["outside_area"] += 1
                continue
            url = _official_url(link, IMD_HOST)
            ident = cap.get("identifier") or guid
            source_id = (ident if ident and len(ident) <= 256 and "://" not in ident
                         else (f"url-sha256:{url_sha256(url)}" if url else ""))
            headline = title or cap.get("headline") or ""
            if not source_id or not headline:
                continue
            drafts.append(_cap_draft(source_id=source_id, title=headline, desc=desc, pub=pub, url=url,
                                     publisher=IMD_PUBLISHER, category=category, cap=cap, area=area,
                                     extra_hints=("mirror:wmo_alert_hub",)))
        return build_signals(self.name, drafts, entry, protect, dropped=self.last_dropped)


# ── official page scrapers ────────────────────────────────────────────────────────────────────────────────────

_NOTICE_PATH = re.compile(
    r"(press|news|notice|advisor|circular|release|update|announce|traffic|monsoon|alert|warning|bulletin|\.pdf$)",
    re.IGNORECASE,
)
_NOTICE_WORDS = re.compile(
    r"\b(press|notice|advisory|circular|release|traffic|diversion|closure|closed|monsoon|rain|flood|waterlog\w*|"
    r"alert|warning|cyclone|heat\s?wave|fire|accident|emergency|helpline|control room|road|bridge|metro|drainage|"
    r"pumping|tide|tram)\b",
    re.IGNORECASE,
)
_SKIP_EXT = re.compile(r"\.(?:jpe?g|png|gif|svg|webp|css|js|ico|woff2?|ttf|mp4|zip|exe)$", re.IGNORECASE)
#: Notice links that are paperwork, never a situation at a place (tenders, forms, payments, recruitment).
_NOT_A_NOTICE = re.compile(
    r"\b(tenders?|forms?|payments?|pay|receipts?|recruitment|results?|login|dashboard|certificates?)\b",
    re.IGNORECASE,
)


class _Anchors(HTMLParser):
    """Collects ``(href, visible text)`` of every anchor and the page's ``<html lang>``."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.items: list[tuple[str, str]] = []
        self.lang = ""
        self._href: str | None = None
        self._text: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "html" and a.get("lang"):
            self.lang = str(a["lang"])[:16]
        elif tag in ("script", "style", "noscript", "template"):
            self._skip += 1
        elif tag == "a":
            self._flush()
            self._href = (a.get("href") or "").strip()
            self._text = []

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "noscript", "template") and self._skip:
            self._skip -= 1
        elif tag == "a":
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._href is not None and not self._skip:
            self._text.append(data)

    def _flush(self) -> None:
        if self._href is not None and len(self.items) < 2000:
            self.items.append((self._href, re.sub(r"\s+", " ", "".join(self._text)).strip()))
        self._href = None
        self._text = []

    def close(self) -> None:
        super().close()
        self._flush()


class OfficialPage(Connector):
    """A government page whose notice links become signals (best effort; robots.txt honoured)."""

    default_cadence_sec = 3600
    max_bytes = 5 * 1024 * 1024
    page_url: ClassVar[str]
    host: ClassVar[str]
    #: the area this office covers: ``kolkata`` (the district) or ``west_bengal`` (the state)
    area: ClassVar[str]
    #: when set, a link is kept only if its visible text matches (a page whose navigation would otherwise pass)
    notice_text: ClassVar[re.Pattern[str] | None] = None
    #: when set, a link whose text matches is dropped (notices about persons, staff or parties, never a place)
    exclude_text: ClassVar[re.Pattern[str] | None] = None
    #: the shortest link text that can be a notice (a menu entry is shorter than a notice's title)
    min_text: ClassVar[int] = 12

    def __init__(self, robots: RobotsCache | None = None) -> None:
        super().__init__()
        self.robots = robots or RobotsCache()

    async def fetch(self, client: httpx.AsyncClient, cache: Cache) -> CacheEntry | None:
        if not self.enabled:
            return None
        allowed, reason = await self.robots.allowed(client, self.page_url)
        if not allowed:
            reason = reason or ROBOTS_DISALLOWS
            if reason.startswith(ROBOTS_DISALLOWS):
                raise ConnectorDisabled(reason)  # the site says no: disabled, and its cache is not served
            raise ConnectorError(reason)  # robots.txt unreachable: a failure (the cached page may be served)
        try:
            res = await fetch(client, self.page_url, max_bytes=self.max_bytes)
        except httpx.ConnectError as exc:
            raise ConnectorError(network_reason(exc)) from exc
        if not res.ok:
            raise ConnectorError(f"HTTP {res.status}")
        ctype = res.headers.get("content-type", "text/html").lower()
        if "html" not in ctype:
            raise ConnectorError("not an HTML page")
        return cache.put(self.name, res.content, "html")

    def parse(self, entry: CacheEntry, protect: frozenset[str]) -> list[RawOsintSignal]:
        self.last_dropped = Counter()
        data = entry.read_bytes(self.max_bytes)
        try:
            html = data.decode("utf-8")
        except UnicodeDecodeError:
            html = data.decode("latin-1")  # KMC's portal is served as ISO-8859-1
        anchors = _Anchors()
        try:
            anchors.feed(html)
            anchors.close()
        except Exception as exc:  # noqa: BLE001 - html.parser is lenient; a hard failure means an unusable page
            raise ConnectorError("page could not be parsed") from exc
        district = self.area == "kolkata"
        drafts: list[Draft] = []
        for href, text in anchors.items:
            if not self.min_text <= len(text) <= 300 or not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            url = canonical_url(urllib.parse.urljoin(self.page_url, href))
            if not url or not url.startswith(f"https://{self.host}/") or _SKIP_EXT.search(url.split("?")[0]):
                continue
            if not (_NOTICE_PATH.search(urllib.parse.urlsplit(url).path) or _NOTICE_WORDS.search(text)):
                continue
            if self.notice_text is not None and not self.notice_text.search(text):
                self.last_dropped["not_an_advisory" if self.name == "kolkata_police_scrape" else "not_about_a_place"] += 1
                continue
            if self.exclude_text is not None and self.exclude_text.search(text):
                self.last_dropped["about_persons"] += 1
                continue
            if _NOT_A_NOTICE.search(text):
                self.last_dropped["paperwork_link"] += 1
                continue
            digest = url_sha256(url + "\n" + text)
            drafts.append(
                Draft(
                    source_id=f"url-sha256:{digest}",
                    title=text,
                    text=text,
                    url=url,
                    publisher=self.host.removeprefix("www."),
                    language=script_language(text, anchors.lang or "en"),
                    place_names=["Kolkata"] if district else ["West Bengal"],
                    admin_codes=["LGD:KOLKATA"] if district else [AREA_STATE_CODE],
                    geo_confidence=0.3 if district else 0.1,
                    category_hint=["page:notice", f"area:{self.area}"],
                    raw={"page_hash": entry.sha256, "page_url_domain": self.host},
                )
            )
        return build_signals(self.name, drafts, entry, protect, dropped=self.last_dropped)


#: a KMC notice about a PLACE: roads, drains, water, works, markets, air, fire, festivals at places (the cityfeeds
#: notices whitelist, widened by the portal's own seasonal notices: puja immersions, vending zones, dengue)
_KMC_PLACE = re.compile(
    r"\b(roads?|parking|traffic|drain\w*|desilt\w*|waterlog\w*|monsoon|rain\w*|flood\w*|water supply|"
    r"construction|bridge|flyover|aqi|air quality|trees?|park|ghat|market|pond|canal|pumping|sewer\w*|streets?|"
    r"lane|puja|immersion\w*|vending|fire|dengue|cyclone|heat\s?wave)\b",
    re.IGNORECASE,
)
#: notices about persons, staff, hearings or parties, never a place (the cityfeeds PERSON_WORDS, widened)
_KMC_PERSONS = re.compile(
    r"\b(hearing|ex-gratia|deaths?|disabilit\w*|harassment|mutation|appointment|recruit\w*|candidate|"
    r"vaccination|tender|mayor|councillor|personal|personnel|political|compensation|judgement|appeal)\b",
    re.IGNORECASE,
)


class KmcPage(OfficialPage):
    """Kolkata Municipal Corporation: the portal's home page (the site root only forwards to it by script). Only
    notices about places and roads are kept (``_KMC_PLACE``), never one about persons, staff or parties
    (``_KMC_PERSONS``): the portal's menu, HR circulars and hearing lists are not situations at a place."""

    name = "kmc_scrape"
    page_url = "https://www.kmcgov.in/KMCPortal/jsp/KMCPortalHome1.jsp"
    host = "www.kmcgov.in"
    area = "kolkata"
    notice_text = _KMC_PLACE
    exclude_text = _KMC_PERSONS


class WbsdmaPage(OfficialPage):
    """West Bengal disaster management (WBSDMA alerts that reach SACHET arrive through ``sachet_cap``): disabled
    until its host answers and is verified (module docstring)."""

    name = "wbsdma"
    page_url = "https://wbdmd.gov.in/"
    host = "wbdmd.gov.in"
    area = "west_bengal"
    disabled_reason = (
        "disabled: host unverified (wbdmd.gov.in answers plain HTTP on port 443, no TLS, and 503 over http, "
        "checked 2026-10-29; verify the department's https host and allow-list it before enabling)"
    )


#: an advisory, in the department's own words (the Kolkata Traffic Police home page's notice list)
_ADVISORY = re.compile(
    r"\b(advisor\w*|diversion|divert\w*|closure|closed|restriction\w*|notification|circulation|"
    r"traffic arrangement\w*|regulat\w+)\b",
    re.IGNORECASE,
)


class PolicePage(OfficialPage):
    """Kolkata Traffic Police: the current traffic advisories on the department's home page (module docstring)."""

    name = "kolkata_police_scrape"
    page_url = "https://kolkatatrafficpolice.gov.in/"
    host = "kolkatatrafficpolice.gov.in"
    area = "kolkata"
    notice_text = _ADVISORY
    #: an advisory's title is a sentence; the menu's "Traffic Restrictions" is not
    min_text = 30
