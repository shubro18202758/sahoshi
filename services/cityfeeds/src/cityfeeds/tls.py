"""TLS for the two public hosts that a default client cannot reach, each with a narrow, recorded exception.

Every other host keeps full verification (certifi CA bundle, ``CERT_REQUIRED``, host name checked). The two
exceptions below are per exact host; neither switches a certificate check off for anything else.

1. **Syama Prasad Mookerjee Port, Kolkata** (``smp.smportkolkata.in``, the port's tide notices). Its certificate
   (GoDaddy Secure CA G2, CN ``smp.smportkolkata.in``, SAN ``smp.smportkolkata.in`` and
   ``www.smp.smportkolkata.in``) **expired on 17 Oct 2026 06:34 UTC** and has not been renewed. For this host only:
   the chain is still verified up to a trusted root and the host name is still checked against the certificate,
   but the validity dates are not (OpenSSL ``X509_V_FLAG_NO_CHECK_TIME``), and the connection is then accepted only
   if the presented leaf certificate is **exactly** the one recorded here (its SHA-256 fingerprint, captured on
   29 Oct 2026 with ``openssl s_client -connect smp.smportkolkata.in:443 -servername smp.smportkolkata.in |
   openssl x509 -noout -fingerprint -sha256``), or is currently within its own validity dates (the port renewed
   it, and a normal check would pass). Anything else is refused before the body is read. Reason: the tide table is
   public safety information for a riverside city, the expiry is an administrative lapse, and the pin means no
   other certificate, expired or not, is accepted for the host.
2. **Kolkata Traffic Police** (``kolkatatrafficpolice.gov.in``, the public traffic advisories). The server lacks
   RFC 5746 secure renegotiation, which OpenSSL 3 refuses by default ("unsafe legacy renegotiation disabled"), and
   offers only RSA key-exchange suites. For this host only: ``ssl.OP_LEGACY_SERVER_CONNECT`` and ``RSA+AESGCM``
   are allowed; its GeoTrust certificate and host name are verified as usual. This client never renegotiates and
   only reads public pages.

:func:`default_transport` routes each request to the right context by host; the Fetcher uses it unless a test
passes its own transport.
"""

from __future__ import annotations

import hashlib
import ssl
import time
from collections.abc import Mapping
from typing import Any

import certifi
import httpx

__all__ = ["PORT_HOST", "PORT_CERT_SHA256", "PORT_PIN_REASON", "POLICE_HOST", "PinMismatch", "default_transport",
           "pinned_ok", "port_context", "police_context"]

PORT_HOST = "smp.smportkolkata.in"
#: SHA-256 of the DER leaf certificate the port presented on 29 Oct 2026 (expired 17 Oct 2026 06:34:12 UTC)
PORT_CERT_SHA256 = "ad4e34f4b44489c6d9a8056fe3c583681aba00e0ef4dcf88e3c7c465cb5e3016"
PORT_PIN_REASON = ("the port's certificate expired on 17 Oct 2026; chain and host name verified, dates not, and only "
                   "the pinned certificate (SHA-256 ad4e34f4…5e3016) or a currently valid one is accepted")
POLICE_HOST = "kolkatatrafficpolice.gov.in"

#: OpenSSL X509_V_FLAG_NO_CHECK_TIME (not exported by the ssl module; accepted by SSLContext.verify_flags)
_NO_CHECK_TIME = 0x200000
_COMPAT_CIPHERS = "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:RSA+AESGCM:!aNULL:!eNULL:!MD5:!DSS"


class PinMismatch(httpx.ConnectError):
    """The port presented a certificate that is neither the pinned one nor currently valid."""


def _base() -> ssl.SSLContext:
    ctx = ssl.create_default_context(cafile=certifi.where())
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


def port_context() -> ssl.SSLContext:
    ctx = _base()
    ctx.verify_flags = ctx.verify_flags | _NO_CHECK_TIME
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname
    return ctx


def police_context() -> ssl.SSLContext:
    ctx = _base()
    ctx.set_ciphers(_COMPAT_CIPHERS)
    ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname
    return ctx


def pinned_ok(der: bytes | None, decoded: Mapping[str, Any] | None, now: float | None = None) -> bool:
    """The pin rule: the exact recorded certificate, or one inside its own validity dates."""
    if not der:
        return False
    if hashlib.sha256(der).hexdigest() == PORT_CERT_SHA256:
        return True
    try:
        nb = ssl.cert_time_to_seconds(str((decoded or {})["notBefore"]))
        na = ssl.cert_time_to_seconds(str((decoded or {})["notAfter"]))
    except (KeyError, ValueError):
        return False
    t = time.time() if now is None else now
    return nb <= t <= na


class _PinnedTransport(httpx.AsyncBaseTransport):
    """The port host's transport: after the handshake, the leaf certificate must pass :func:`pinned_ok`."""

    def __init__(self, inner: httpx.AsyncBaseTransport) -> None:
        self._inner = inner

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        resp = await self._inner.handle_async_request(request)
        stream = resp.extensions.get("network_stream")
        so = stream.get_extra_info("ssl_object") if stream is not None else None
        try:
            der = so.getpeercert(True) if so is not None else None
            decoded = so.getpeercert() if so is not None else None
        except (ValueError, AttributeError):
            der, decoded = None, None
        if not pinned_ok(der, decoded):
            await resp.aclose()
            raise PinMismatch(f"{PORT_HOST}: certificate is neither the pinned one nor currently valid")
        return resp

    async def aclose(self) -> None:
        await self._inner.aclose()


class _HostRouter(httpx.AsyncBaseTransport):
    def __init__(self, default: httpx.AsyncBaseTransport, by_host: Mapping[str, httpx.AsyncBaseTransport]) -> None:
        self._default = default
        self._by_host = dict(by_host)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        host = (request.url.host or "").lower().rstrip(".")
        return await self._by_host.get(host, self._default).handle_async_request(request)

    async def aclose(self) -> None:
        for t in (self._default, *self._by_host.values()):
            await t.aclose()


def default_transport() -> httpx.AsyncBaseTransport:
    """Full verification everywhere, plus the two per-host exceptions in the module docstring."""
    return _HostRouter(
        httpx.AsyncHTTPTransport(verify=_base()),
        {
            PORT_HOST: _PinnedTransport(httpx.AsyncHTTPTransport(verify=port_context())),
            POLICE_HOST: httpx.AsyncHTTPTransport(verify=police_context()),
        },
    )
