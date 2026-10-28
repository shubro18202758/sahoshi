"""Egress safety: an allow-list of exact source hosts, a loopback-only oracle, robots.txt, bounded bodies.

Policies (OSINT SPEC §4 "offline / no secrets"; plan R7 says compose cannot filter by domain, so this module is the
egress control):

1. **Sources** — :data:`ALLOWED_HOSTS` is an allow-list of exact host names. Every request is checked twice before
   any connection: by :func:`check_egress_url` (scheme ``https``, no credentials, default port, exact host) and
   again by :class:`AllowListTransport`, which wraps the real transport, so even a direct ``client.get`` cannot
   reach another host. Redirects are never followed automatically: :func:`fetch` follows at most five, each one
   only to an allow-listed host, and refuses anything else before connecting.
2. **The one client** — :func:`make_source_client` builds the single ``httpx.AsyncClient`` the connectors share,
   with ``trust_env=False`` (no proxy, netrc or certificate override from the environment) and a user-agent that
   names the project and no person.
3. **The oracle** — :func:`check_oracle_url` accepts only a loopback base URL (``127.0.0.1``, ``localhost`` or
   ``::1``; the emulator's internal-endpoint rule), and :class:`LoopbackTransport` enforces it per request.
4. **Bodies** — :func:`fetch` reads raw bytes up to a per-call cap and decodes ``gzip``/``deflate`` itself with a
   bounded decompressor, so neither a huge body nor a compression bomb can exhaust the box's memory.
5. **robots.txt** — :class:`RobotsCache` (stdlib ``urllib.robotparser``, fetched through the same client, cached
   24 h) decides for the official page scrapers; a disallowed path (or a robots.txt answered 401/403) disables
   that connector (:data:`ROBOTS_DISALLOWS`, "robots.txt disallows"; its cached page is not served either).
   Unreachable robots (5xx, network) means complete disallow (RFC 9309 §2.3.1.4): nothing is crawled, and it is
   reported as a failure ("robots.txt unreachable"), so the page fetched earlier, while allowed, may be served.
   That verdict is cached only 30 minutes, then robots.txt is fetched again.

Nothing here logs a URL path or a body: errors name the host at most.
"""

from __future__ import annotations

import time
import urllib.robotparser
import zlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

import httpx

__all__ = [
    "ALLOWED_HOSTS",
    "LOOPBACK_HOSTS",
    "ROBOTS_DISALLOWS",
    "ROBOTS_TOKEN",
    "AllowListTransport",
    "EgressRefused",
    "FetchError",
    "FetchResult",
    "LoopbackTransport",
    "RobotsCache",
    "check_egress_url",
    "check_oracle_url",
    "fetch",
    "make_oracle_client",
    "make_source_client",
]

#: Exact source hosts (OS-2 brief; the Kolkata sources table in this service's README). No wildcard, no suffix
#: match. Each was checked on 2026-10-28 with the service's own user agent: it answered and its robots.txt allows the
#: path (``www.kmcgov.in`` serves no robots.txt: a 404, so no restriction, RFC 9309 §2.3.1.3). Deliberately absent:
#: the West Bengal Disaster Management department (``wbdmd.gov.in``) and Kolkata Police / Kolkata Traffic Police
#: (``kolkatapolice.gov.in``, ``kolkatatrafficpolice.gov.in``): their hosts refused the connection, so nothing they
#: serve was verified, and the ``wbsdma`` and ``kolkata_police_scrape`` connectors stay disabled until it is. Outlets
#: whose feeds refuse or no longer exist (The Telegraph, Anandabazar, Ei Samay, The Statesman, Zee 24 Ghanta) are
#: not listed either.
ALLOWED_HOSTS: frozenset[str] = frozenset(
    {
        "data.gdeltproject.org",
        "api.gdeltproject.org",
        "news.google.com",
        "sachet.ndma.gov.in",  # NDMA SACHET CAP (the all-India RSS, filtered to West Bengal)
        "cap-sources.s3.amazonaws.com",  # IMD CAP alerts, the WMO Alert Hub mirror (in-imd-en)
        "www.reddit.com",
        "index.commoncrawl.org",
        "data.commoncrawl.org",
        "www.kmcgov.in",  # Kolkata Municipal Corporation portal
        # news_rss: the outlets' own RSS feeds (Kolkata and West Bengal sections)
        "timesofindia.indiatimes.com",
        "www.millenniumpost.in",
        "www.sangbadpratidin.in",
        "bengali.abplive.com",
    }
)

#: The oracle runs on the same box: loopback only (the emulator's internal-endpoint rule).
LOOPBACK_HOSTS: frozenset[str] = frozenset({"127.0.0.1", "localhost", "::1"})

#: The robots.txt product token (matched by ``urllib.robotparser`` against ``User-agent:`` lines).
ROBOTS_TOKEN = "sahoshi-osint-ingress"
#: The reason (prefix) of every verdict in which the site itself disallows the fetch (the connector is disabled).
ROBOTS_DISALLOWS = "robots.txt disallows"

_REDIRECTS = frozenset({301, 302, 303, 307, 308})


class EgressRefused(Exception):
    """A request to a host or URL outside the egress policy. Raised before any connection is opened."""


class FetchError(Exception):
    """A fetch that failed for a reason worth reporting (status, size, encoding, redirects). Never carries a body."""


def _host_of(url: httpx.URL) -> str:
    return (url.host or "").lower().rstrip(".")


def check_egress_url(url: str | httpx.URL) -> httpx.URL:
    """The URL as an ``httpx.URL`` when it is allowed; else :class:`EgressRefused` (nothing is connected)."""
    try:
        u = url if isinstance(url, httpx.URL) else httpx.URL(str(url).strip())
    except (httpx.InvalidURL, TypeError, ValueError) as exc:
        raise EgressRefused("egress refused: not a valid URL") from exc
    host = _host_of(u)
    if u.scheme != "https":
        raise EgressRefused(f"egress refused: https only ({u.scheme or 'no scheme'}://{host[:64]})")
    if u.userinfo:
        raise EgressRefused(f"egress refused: credentials in URL ({host[:64]})")
    if host not in ALLOWED_HOSTS:
        raise EgressRefused(f"egress refused: host not allow-listed ({host[:64] or 'none'})")
    if u.port not in (None, 443):
        raise EgressRefused(f"egress refused: non-default port ({host[:64]}:{u.port})")
    return u


def check_oracle_url(url: str) -> str:
    """Normalise and check the oracle base URL: http(s), a loopback host, no credentials, query or path.

    Returns ``scheme://host:port`` (IPv6 bracketed). Raises ``ValueError`` otherwise.
    """
    if not isinstance(url, str) or not url.strip():
        raise ValueError("oracle URL must be a non-empty string")
    try:
        u = httpx.URL(url.strip())
    except (httpx.InvalidURL, TypeError, ValueError) as exc:
        raise ValueError("oracle URL is not a valid URL") from exc
    if u.scheme not in ("http", "https"):
        raise ValueError("oracle URL must be http or https")
    host = _host_of(u)
    if host not in LOOPBACK_HOSTS:
        raise ValueError(f"oracle URL must be loopback (127.0.0.1, localhost or ::1), not {host[:64] or 'empty'}")
    if u.userinfo:
        raise ValueError("oracle URL must not carry credentials")
    if u.query or u.fragment or u.path not in ("", "/"):
        raise ValueError("oracle URL is a base URL: no path, query or fragment")
    port = u.port or (443 if u.scheme == "https" else 80)
    shown = f"[{host}]" if ":" in host else host
    return f"{u.scheme}://{shown}:{port}"


class AllowListTransport(httpx.AsyncBaseTransport):
    """Refuses any request whose URL fails :func:`check_egress_url`, before delegating (defence in depth)."""

    def __init__(self, inner: httpx.AsyncBaseTransport) -> None:
        self._inner = inner

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        check_egress_url(request.url)
        return await self._inner.handle_async_request(request)

    async def aclose(self) -> None:
        await self._inner.aclose()


class LoopbackTransport(httpx.AsyncBaseTransport):
    """Refuses any request that does not go to a loopback host (the oracle client)."""

    def __init__(self, inner: httpx.AsyncBaseTransport) -> None:
        self._inner = inner

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if _host_of(request.url) not in LOOPBACK_HOSTS:
            raise EgressRefused(f"egress refused: oracle requests are loopback only ({_host_of(request.url)[:64]})")
        return await self._inner.handle_async_request(request)

    async def aclose(self) -> None:
        await self._inner.aclose()


def make_source_client(
    *,
    user_agent: str,
    timeout: float = 25.0,
    transport: httpx.AsyncBaseTransport | None = None,
) -> httpx.AsyncClient:
    """The one egress client: allow-listed hosts only, ``trust_env=False``, no automatic redirects."""
    inner = transport or httpx.AsyncHTTPTransport(retries=0, trust_env=False)
    return httpx.AsyncClient(
        transport=AllowListTransport(inner),
        trust_env=False,
        follow_redirects=False,
        headers={"User-Agent": user_agent, "Accept-Encoding": "gzip"},
        timeout=httpx.Timeout(timeout, connect=min(10.0, timeout)),
        limits=httpx.Limits(max_connections=4, max_keepalive_connections=2),
    )


def make_oracle_client(
    oracle_url: str,
    *,
    user_agent: str,
    timeout: float = 30.0,
    transport: httpx.AsyncBaseTransport | None = None,
) -> httpx.AsyncClient:
    """The oracle client: a checked loopback base URL, ``trust_env=False`` (a proxy must never see the posts)."""
    base = check_oracle_url(oracle_url)
    inner = transport or httpx.AsyncHTTPTransport(retries=0, trust_env=False)
    return httpx.AsyncClient(
        base_url=base,
        transport=LoopbackTransport(inner),
        trust_env=False,
        follow_redirects=False,
        headers={"User-Agent": user_agent},
        timeout=httpx.Timeout(timeout, connect=2.0),
    )


@dataclass(frozen=True)
class FetchResult:
    """A fetched response: the final status, the decoded body (bounded) and the headers that matter."""

    status: int
    content: bytes
    url: str
    headers: Mapping[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


def _decode(body: bytes, encoding: str | None, max_bytes: int) -> bytes:
    enc = (encoding or "identity").strip().lower()
    if enc in ("", "identity"):
        return body
    if "," in enc:
        raise FetchError("unsupported content-encoding (stacked)")
    if enc in ("gzip", "x-gzip"):
        wbits = 16 + zlib.MAX_WBITS
    elif enc == "deflate":
        wbits = zlib.MAX_WBITS if body[:1] == b"\x78" else -zlib.MAX_WBITS
    else:
        raise FetchError(f"unsupported content-encoding ({enc[:16]})")
    try:
        d = zlib.decompressobj(wbits)
        out = d.decompress(body, max_bytes + 1)
    except zlib.error as exc:
        raise FetchError("corrupt compressed body") from exc
    if len(out) > max_bytes or d.unconsumed_tail:
        raise FetchError(f"decoded body exceeds {max_bytes} bytes")
    return out


async def _read_capped(resp: httpx.Response, max_bytes: int) -> bytes:
    if resp.is_stream_consumed:  # an in-memory response (a transport that already read it): bound it all the same
        if len(resp.content) > max_bytes:
            raise FetchError(f"body exceeds {max_bytes} bytes")
        return resp.content
    chunks: list[bytes] = []
    total = 0
    async for chunk in resp.aiter_raw():
        total += len(chunk)
        if total > max_bytes:
            raise FetchError(f"body exceeds {max_bytes} bytes")
        chunks.append(chunk)
    return _decode(b"".join(chunks), resp.headers.get("content-encoding"), max_bytes)


async def fetch(
    client: httpx.AsyncClient,
    url: str,
    *,
    max_bytes: int,
    headers: Mapping[str, str] | None = None,
    max_redirects: int = 5,
) -> FetchResult:
    """GET ``url`` through the egress policy. Redirects only to allow-listed hosts; the body is capped.

    Raises :class:`EgressRefused` (policy), :class:`FetchError` (size, encoding, redirects) or an ``httpx``
    transport error. Any status is returned; the caller decides what a 4xx/5xx means.
    """
    current = check_egress_url(url)
    for _hop in range(max_redirects + 1):
        request = client.build_request("GET", current, headers=dict(headers or {}))
        resp = await client.send(request, stream=True)
        try:
            if resp.status_code in _REDIRECTS:
                location = resp.headers.get("location")
                if not location:
                    raise FetchError(f"HTTP {resp.status_code} redirect without a Location")
                try:
                    nxt = current.join(location)
                except (httpx.InvalidURL, ValueError) as exc:
                    raise EgressRefused("egress refused: invalid redirect target") from exc
                try:
                    current = check_egress_url(nxt)
                except EgressRefused as exc:
                    raise EgressRefused(
                        f"egress refused: redirect to a host off the allow-list ({_host_of(nxt)[:64] or 'none'})"
                    ) from exc
                continue
            body = await _read_capped(resp, max_bytes)
            keep = {k: v for k, v in resp.headers.items() if k.lower() in ("content-type", "last-modified", "etag")}
            return FetchResult(status=resp.status_code, content=body, url=str(current), headers=keep)
        finally:
            await resp.aclose()
    raise FetchError(f"more than {max_redirects} redirects")


@dataclass
class _Robots:
    expires: float
    parser: urllib.robotparser.RobotFileParser | None
    verdict: bool | None  # a blanket allow (True) / disallow (False), else consult the parser
    reason: str | None


class RobotsCache:
    """robots.txt per origin, fetched through the egress client. A real answer (rules, a 4xx) is cached ``ttl_sec``
    (24 h); an unreachable one (5xx, a network or size failure) only ``fail_ttl_sec`` (30 min), so a transient
    failure at boot (no egress yet at a venue) does not block a scraper for a day."""

    def __init__(
        self,
        *,
        ttl_sec: float = 86400.0,
        fail_ttl_sec: float = 1800.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = ttl_sec
        self._fail_ttl = min(fail_ttl_sec, ttl_sec)
        self._clock = clock
        self._entries: dict[str, _Robots] = {}

    def forget(self) -> None:
        self._entries.clear()

    async def _load(self, client: httpx.AsyncClient, origin: str) -> _Robots:
        now = self._clock()
        expires, retry_at = now + self._ttl, now + self._fail_ttl
        try:
            res = await fetch(client, origin + "/robots.txt", max_bytes=512 * 1024)
        except EgressRefused:
            raise
        except (FetchError, httpx.HTTPError):
            return _Robots(retry_at, None, False, "robots.txt unreachable")
        if res.status in (401, 403):
            return _Robots(expires, None, False, f"{ROBOTS_DISALLOWS} (HTTP {res.status})")
        if 400 <= res.status < 500:
            return _Robots(expires, None, True, None)  # unavailable: no restriction (RFC 9309 §2.3.1.3)
        if res.status >= 300:
            return _Robots(retry_at, None, False, f"robots.txt unreachable (HTTP {res.status})")
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(res.content.decode("utf-8", "replace").splitlines())
        return _Robots(expires, rp, None, None)

    async def allowed(self, client: httpx.AsyncClient, url: str) -> tuple[bool, str | None]:
        """``(allowed, reason)`` for ``url``; the reason is set when it is not allowed."""
        u = check_egress_url(url)
        origin = f"https://{_host_of(u)}"
        entry = self._entries.get(origin)
        if entry is None or entry.expires <= self._clock():
            entry = await self._load(client, origin)
            self._entries[origin] = entry
        if entry.verdict is not None:
            return entry.verdict, (None if entry.verdict else (entry.reason or ROBOTS_DISALLOWS))
        assert entry.parser is not None
        if entry.parser.can_fetch(ROBOTS_TOKEN, str(u)):
            return True, None
        return False, ROBOTS_DISALLOWS
