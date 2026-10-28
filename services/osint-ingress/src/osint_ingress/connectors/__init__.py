"""The connectors: one per ``RawOsintSignal.source``, each with ``fetch(client, cache)`` and
``parse(entry, protect)``.

=========================== ======================== ===================================================
source                      module                   endpoint (egress allow-list)
=========================== ======================== ===================================================
``sachet_cap``              :mod:`.official`         sachet.ndma.gov.in (all-India CAP RSS, kept to West
                                                     Bengal, + CAP 1.2 detail)
``imd``                     :mod:`.official`         cap-sources.s3.amazonaws.com (IMD CAP, WMO Alert Hub
                                                     mirror, kept to West Bengal)
``google_news_rss``         :mod:`.google_news`      news.google.com (RSS search, English and Bengali)
``news_rss``                :mod:`.news_rss`         the outlets' own feeds (TOI Kolkata, Millennium Post,
                                                     Sangbad Pratidin, ABP Ananda)
``gdelt_events``            :mod:`.gdelt`            data.gdeltproject.org (lastupdate.txt + export zip)
``gdelt_doc``               :mod:`.gdelt`            api.gdeltproject.org (DOC 2.0 ArtList, >= 5 s spacing)
``reddit_rss``              :mod:`.reddit`           www.reddit.com (r/kolkata Atom)
``kmc_scrape``              :mod:`.official`         www.kmcgov.in (portal page, robots.txt)
``wbsdma``                  :mod:`.official`         disabled: host unverified (wbdmd.gov.in does not answer)
``kolkata_police_scrape``   :mod:`.official`         disabled: host unverified (police hosts do not answer)
``common_crawl``            :mod:`.common_crawl`     index.commoncrawl.org + data.commoncrawl.org (backfill)
=========================== ======================== ===================================================
"""

from __future__ import annotations

from osint_ingress.connectors.base import Connector, ConnectorError
from osint_ingress.connectors.common_crawl import CommonCrawl
from osint_ingress.connectors.gdelt import GdeltBulk, GdeltDoc
from osint_ingress.connectors.google_news import GoogleNews
from osint_ingress.connectors.news_rss import NewsRss
from osint_ingress.connectors.official import Imd, KmcPage, PolicePage, Sachet, WbsdmaPage
from osint_ingress.connectors.reddit import Reddit
from osint_ingress.safe_http import RobotsCache

__all__ = ["Connector", "ConnectorError", "build_connectors"]


def build_connectors(*, robots: RobotsCache | None = None) -> dict[str, Connector]:
    """Every connector, keyed by source name, in the order a cycle runs them (official first)."""
    robots = robots or RobotsCache()
    conns: list[Connector] = [
        Sachet(),
        Imd(),
        GoogleNews(),
        NewsRss(robots),
        GdeltBulk(),
        GdeltDoc(),
        Reddit(),
        KmcPage(robots),
        WbsdmaPage(robots),
        PolicePage(robots),
        CommonCrawl(),
    ]
    return {c.name: c for c in conns}
