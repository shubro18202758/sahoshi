"""The Kolkata sources: the West Bengal area filter of the official feeds, the outlets' own RSS feeds (``news_rss``),
IMD's CAP mirror, the script-based language, and the service's own Kolkata constants."""

from __future__ import annotations

import ast
import json
import re
import unicodedata
from pathlib import Path

import httpx
import pytest
from conftest import CAPTURE, HOSTILE, PACKAGE, PAGES, POC_RAW, Recorder, needs_poc

from osint_common.kinds import SOURCE_NAMES
from osint_ingress.cache import Cache
from osint_ingress.config import CONNECTOR_NAMES, USER_AGENT
from osint_ingress.connectors._area import area_hint, match_area
from osint_ingress.connectors.base import CITY_BBOX, KOLKATA_RE, ConnectorError, script_language, url_sha256
from osint_ingress.connectors.news_rss import FEEDS, ITEM_FIELDS, NewsRss, cut_latin_lead
from osint_ingress.connectors.official import Imd, Sachet
from osint_ingress.importer import import_capture
from osint_ingress.safe_http import RobotsCache, make_source_client

REPO = PACKAGE.parents[1]


def _client(handler) -> httpx.AsyncClient:
    return make_source_client(user_agent=USER_AGENT, transport=httpx.MockTransport(handler))


# ── the West Bengal area filter ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("text", "codes"),
    [
        ("Light to moderate rain is very likely over Kolkata in next 3 hours.", ["LGD:KOLKATA"]),
        ("২৭-১০-২০২৬ রাত ৮:৩০ থেকে কলকাতায় বজ্রবিদ্যুৎ সহ বৃষ্টির সম্ভাবনা", ["LGD:KOLKATA"]),
        ("Thunderstorm over Calcutta and Howrah", ["LGD:KOLKATA", "LGD:HOWRAH"]),
        ("হাওড়া ও হুগলির কিছু অংশে বৃষ্টি", ["LGD:HOWRAH"]),
        # IMD's Bengali nowcasts join two districts of one name: both are read
        ("বাঁকুড়া, উত্তর ও দক্ষিণ ২৪ পরগনা জেলার কিছু অংশে বৃষ্টি",
         ["LGD:NORTH_24_PARGANAS", "LGD:SOUTH_24_PARGANAS"]),
        ("Rain over North and South 24 Parganas", ["LGD:NORTH_24_PARGANAS", "LGD:SOUTH_24_PARGANAS"]),
        ("Thunderstorm likely over N 24 Pgs and Nadia", ["LGD:NORTH_24_PARGANAS"]),
        ("দক্ষিণ 24 পরগনা ও পূর্ব মেদিনীপুরে বৃষ্টি", ["LGD:SOUTH_24_PARGANAS"]),
        # other West Bengal districts only: the state level
        ("পূর্ব ও পশ্চিম মেদিনীপুর এবং ঝাড়গ্রামে মাঝারি বজ্রপাত", ["LGD:WEST_BENGAL"]),
        ("Heavy rain over Darjeeling, Kalimpong and Jalpaiguri", ["LGD:WEST_BENGAL"]),
        ("Heat wave conditions over Gangetic West Bengal", ["LGD:WEST_BENGAL"]),
    ],
)
def test_area_levels(text, codes):
    m = match_area(text)
    assert m.in_area and m.admin_codes == codes


@pytest.mark.parametrize(
    "text",
    [
        "Squally weather along and off the Andaman and Nicobar coast",
        "High waves along the Ganjam and Puri coast",
        "A low pressure area over the Bay of Bengal",  # the sea, not the state
        "River Nagavali at Srikakulam above normal",
        "",
    ],
)
def test_other_states_are_outside_the_area(text):
    m = match_area(text)
    assert not m.in_area and m.districts == () and area_hint(m) == []


def test_the_area_match_is_blind_to_the_nukta_encoding():
    composed = "\u09b9\u09be\u0993\u09dc\u09be\u09af\u09bc \u09ac\u09c3\u09b7\u09cd\u099f\u09bf"  # "ড়" as U+09DC
    decomposed = composed.replace("\u09dc", "\u09a1\u09bc")  # "ড" + nukta (the NFC/NFKC form)
    assert composed != decomposed
    assert match_area(composed).districts == match_area(decomposed).districts == ("LGD:HOWRAH",)
    assert unicodedata.normalize("NFKC", composed) == unicodedata.normalize("NFKC", decomposed)


def test_area_hints_name_the_level():
    assert area_hint(match_area("over Kolkata and North 24 Parganas")) == ["area:kolkata", "area:north_24_parganas"]
    assert area_hint(match_area("over Bankura")) == ["area:west_bengal"]


def test_script_language():
    assert script_language("কলকাতায় জল জমা") == "bn"
    assert script_language("Cyclone Update: ঘূর্ণিঝড়") == "bn"  # a mixed headline counts as Bengali
    assert script_language("कोलकाता में जाम") == "hi"
    assert script_language("Jam on EM Bypass") == "en" and script_language("", "bn") == "bn"


# ── SACHET's all-India feed and IMD's mirror ─────────────────────────────────────────────────────────────────


@needs_poc
def test_a_real_sachet_capture_of_another_state_yields_nothing(tmp_path, protect):
    """The PoC's real SACHET capture (another state's alerts), read in place: every item is outside the area."""
    import_capture(POC_RAW, tmp_path / "cache")
    conn = Sachet()
    sigs = conn.parse(Cache(tmp_path / "cache").latest("sachet_cap"), protect)
    assert sigs == [] and conn.last_dropped["outside_area"] == 10


async def test_imd_fetches_details_from_the_mirror_only_and_keeps_west_bengal(tmp_path, protect):
    rss = (PAGES / "imd_rss_synthetic.xml").read_bytes()
    details = {
        "/in-imd-en/2026-10-20-12-00-00-synthetic-0001.xml": (PAGES / "imd_cap_synthetic_0001.xml").read_bytes(),
        "/in-imd-en/2026-10-20-12-05-00-synthetic-0002.xml": (PAGES / "imd_cap_synthetic_0002.xml").read_bytes(),
    }
    rec = Recorder({
        "cap-sources.s3.amazonaws.com/in-imd-en/rss.xml": lambda r: httpx.Response(200, content=rss),
        "cap-sources.s3.amazonaws.com/in-imd-en/2026": lambda r: httpx.Response(200, content=details[r.url.path]),
    })
    conn = Imd()
    conn.detail_spacing_sec = 0
    cache = Cache(tmp_path)
    async with _client(rec) as client:
        entry = await conn.fetch(client, cache)
    assert set(rec.hosts) == {"cap-sources.s3.amazonaws.com"}  # the off-mirror link is never requested
    assert len(entry.blobs) == 2
    sigs = conn.parse(entry, protect)
    assert conn.last_dropped["outside_area"] == 1  # the Odisha alert
    by_id = {s.source_id: s for s in sigs}
    kol = by_id["synthetic-imd-0001"]
    assert kol.raw_geo_hint.admin_codes == ["LGD:KOLKATA", "LGD:HOWRAH"] and kol.source == "imd"
    assert kol.publisher == "mausam.imd.gov.in"
    assert kol.url.startswith("https://cap-sources.s3.amazonaws.com/in-imd-en/")
    assert kol.provenance_label == "OFFICIAL-VERIFIED" and kol.license == "imd_terms" and not kol.redistributable
    assert "CAP_EVENT:Thunderstorm" in kol.category_hint and "mirror:wmo_alert_hub" in kol.category_hint
    assert kol.valid_until is not None or kol.raw["cap_expires"]
    # the off-mirror item names Kolkata in its own text: kept, but its link is not an official URL
    off = by_id["synthetic-0003"]
    assert off.url is None and off.raw_geo_hint.admin_codes == ["LGD:KOLKATA"]
    blob = json.dumps([s.model_dump(mode="json") for s in sigs])
    assert "Contactwala" not in blob and "never be read" not in blob


async def test_an_empty_imd_feed_is_a_good_fetch_with_no_signal(tmp_path, protect):
    empty = (b'<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>'
             b"<link>https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml</link></channel></rss>")
    rec = Recorder({"cap-sources.s3.amazonaws.com/": lambda r: httpx.Response(200, content=empty)})
    async with _client(rec) as client:
        entry = await Imd().fetch(client, Cache(tmp_path))
    assert entry is not None and Imd().parse(entry, protect) == []


# ── news_rss: the outlets' own feeds ─────────────────────────────────────────────────────────────────────────


def test_news_rss_capture_fields(capture_cache, protect):
    conn = NewsRss(RobotsCache())
    sigs = conn.parse(capture_cache.latest("news_rss"), protect)
    assert len(sigs) == 6 and dict(conn.last_dropped) == {"outside_section": 1, "foreign_link": 1}
    assert {s.publisher for s in sigs} == {"news-bn-a.example", "news-bn-b.example", "news-c.example"}
    assert sorted(s.language for s in sigs) == ["bn", "bn", "bn", "bn", "en", "en"]
    for s in sigs:
        assert s.source == "news_rss" and s.source_tier == "news_regional" and s.provenance_label == "SIMULATED"
        assert s.license == "publisher_rss_terms" and s.redistributable is False and s.credibility_prior == 0.60
        assert s.url is None and s.source_id.startswith("url-sha256:")
        assert any(h.startswith("url_sha256:") for h in s.category_hint)
        assert f"domain:{s.publisher}" in s.category_hint and any(h.startswith("feed:") for h in s.category_hint)
        assert set(s.raw) <= {"source_domain", "pub_date"}
        assert "The post " not in s.text  # WordPress's footer is cut
    blob = json.dumps([s.model_dump(mode="json") for s in sigs], ensure_ascii=False)
    # bylines and full text are never read; categories are never emitted
    assert "Reporterwala" not in blob and "never read" not in blob and "মহানগর" not in blob
    # the Bengali headline's English search keyword is cut before redaction
    assert "Kolkata Rain" not in blob
    thanthania = [s for s in sigs if s.source_id == "url-sha256:" + url_sha256(
        "https://news-bn-b.example/kolkata/bidhan-sarani-waterlogged-near-thanthania")]
    assert len(thanthania) == 1 and thanthania[0].title.startswith(("বিধান", "[WITHHELD]"))


def test_a_live_bundle_reads_only_reviewed_feeds(tmp_path, protect):
    """A live entry naming a feed that is not in FEEDS (or inlining its XML) is not read: only a hand-written
    capture may name fictional outlets, and only *.example ones."""
    doc = json.loads((CAPTURE / "news_rss_live.json").read_text(encoding="utf-8"))
    live = Cache(tmp_path / "a").put("news_rss", json.dumps(doc).encode(), "json")
    conn = NewsRss(RobotsCache())
    assert conn.parse(live, protect) == [] and conn.last_dropped["unknown_feed"] == 3
    doc["feeds"][0]["publisher"] = "real-outlet.in"
    synthetic = Cache(tmp_path / "b").put("news_rss", json.dumps(doc).encode(), "json", synthetic=True)
    assert {s.publisher for s in conn.parse(synthetic, protect)} == {"news-bn-b.example", "news-c.example"}
    assert conn.last_dropped["unknown_feed"] == 1


_TOI = """<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
<channel><title>synthetic toi replica</title><language>en-gb</language>
<item><title>Waterlogging at Thanthania after overnight rain</title>
<description><![CDATA[<a href="x"><img src="y"/></a>Traffic crawled on Bidhan Sarani.]]></description>
<link>https://timesofindia.indiatimes.com/city/kolkata/waterlogging-at-thanthania/articleshow/1.cms</link>
<guid>https://timesofindia.indiatimes.com/city/kolkata/waterlogging-at-thanthania/articleshow/1.cms</guid>
<pubDate>Tue, 20 Oct 2026 12:00:00 +0530</pubDate><dc:creator>Synthetic Byline Reporterwala</dc:creator></item>
</channel></rss>"""
_SP = """<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>synthetic sp replica</title>
<language>en-US</language>
<item><title>বিধান সরণিতে জল জমা</title><link>https://www.sangbadpratidin.in/kolkata/bidhan-sarani-x/</link>
<pubDate>Tue, 20 Oct 2026 12:00:00 +0000</pubDate><category><![CDATA[মহানগর]]></category></item>
<item><title>রাজ্যের খবর</title><link>https://www.sangbadpratidin.in/bengal/state-y/</link>
<pubDate>Tue, 20 Oct 2026 11:00:00 +0000</pubDate></item>
<item><title>দেশের খবর</title><link>https://www.sangbadpratidin.in/india/national-z/</link>
<pubDate>Tue, 20 Oct 2026 10:00:00 +0000</pubDate></item>
</channel></rss>"""


async def test_news_rss_fetches_each_feed_honours_robots_and_survives_a_refusal(tmp_path, protect):
    rec = Recorder({
        "timesofindia.indiatimes.com/robots.txt": lambda r: httpx.Response(
            200, text="User-agent: *\nDisallow: /feeds/\n"),
        "timesofindia.indiatimes.com/rssfeeds/": lambda r: httpx.Response(200, text=_TOI),
        "www.millenniumpost.in/robots.txt": lambda r: httpx.Response(404),
        "www.millenniumpost.in/feed": lambda r: httpx.Response(403),
        "www.sangbadpratidin.in/robots.txt": lambda r: httpx.Response(200, text="User-agent: *\nAllow: /\n"),
        "www.sangbadpratidin.in/feed": lambda r: httpx.Response(200, text=_SP),
        "bengali.abplive.com/robots.txt": lambda r: httpx.Response(
            200, text="User-agent: sahoshi-osint-ingress\nDisallow: /\n"),
    })
    conn = NewsRss(RobotsCache())
    cache = Cache(tmp_path)
    async with _client(rec) as client:
        entry = await conn.fetch(client, cache)
    doc = json.loads(entry.read_bytes())
    assert [f["feed"] for f in doc["feeds"]] == ["toi_kolkata", "sangbadpratidin_kolkata"]
    assert {f["feed"]: f["reason"] for f in doc["failed"]} == {
        "millenniumpost_bengal": "HTTP 403", "abp_ananda_kolkata": "robots.txt disallows"}
    assert not any(r.url.host == "bengali.abplive.com" and r.url.path != "/robots.txt" for r in rec.requests)
    assert all(r.headers["user-agent"] == USER_AGENT for r in rec.requests)
    sigs = conn.parse(entry, protect)
    assert conn.last_dropped["outside_section"] == 1  # Sangbad Pratidin's national item
    by_pub = {}
    for s in sigs:
        by_pub.setdefault(s.publisher, []).append(s)
    assert len(by_pub["timesofindia.indiatimes.com"]) == 1 and len(by_pub["sangbadpratidin.in"]) == 2
    assert {s.language for s in by_pub["sangbadpratidin.in"]} == {"bn"}
    assert {s.provenance_label for s in sigs} == {"NEWS-REPORTED"}  # a live fetch is never synthetic
    toi = by_pub["timesofindia.indiatimes.com"][0]
    assert toi.title == "Waterlogging at Thanthania after overnight rain" and "Bidhan Sarani" in toi.text
    assert "Reporterwala" not in json.dumps(toi.model_dump(mode="json"))


async def test_news_rss_fails_only_when_every_feed_fails(tmp_path):
    rec = Recorder({"": lambda r: httpx.Response(404 if r.url.path == "/robots.txt" else 503)})
    async with _client(rec) as client:
        with pytest.raises(ConnectorError, match="every feed failed"):
            await NewsRss(RobotsCache()).fetch(client, Cache(tmp_path))
    assert Cache(tmp_path).latest("news_rss") is None


async def test_a_hostile_feed_is_refused_and_never_cached(tmp_path):
    hostile = (HOSTILE / "xxe.xml").read_bytes()
    rec = Recorder({
        "timesofindia.indiatimes.com/robots.txt": lambda r: httpx.Response(404),
        "timesofindia.indiatimes.com/": lambda r: httpx.Response(200, content=hostile),
        "": lambda r: httpx.Response(404 if r.url.path == "/robots.txt" else 503),
    })
    async with _client(rec) as client:
        with pytest.raises(ConnectorError, match="every feed failed"):
            await NewsRss(RobotsCache()).fetch(client, Cache(tmp_path))
    assert not list(Path(tmp_path).rglob("*.xml"))


def test_cut_latin_lead():
    assert cut_latin_lead("Fictus-Kalpit Meeting : কলকাতায় বৈঠক") == "কলকাতায় বৈঠক"
    assert cut_latin_lead("Cyclone Update: 'নমুনা' আছড়ে পড়েছে") == "নমুনা' আছড়ে পড়েছে"
    assert cut_latin_lead("কলকাতায় জল জমা: যান চলাচল ব্যাহত") == "কলকাতায় জল জমা: যান চলাচল ব্যাহত"
    assert cut_latin_lead("Waterlogging: traffic hit on EM Bypass") == "Waterlogging: traffic hit on EM Bypass"


def test_the_news_rss_parser_never_reads_a_byline():
    assert not {"author", "creator", "dc:creator", "content", "encoded"} & set(ITEM_FIELDS)
    path = PACKAGE / "src" / "osint_ingress" / "connectors" / "news_rss.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docs = {id(n.body[0].value) for n in ast.walk(tree)
            if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef)) and n.body
            and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
    hits = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in docs and re.search(r"creator|author|encoded|purl\.org/dc", n.value)]
    assert not hits, hits


def test_the_reviewed_feeds():
    assert {f.id for f in FEEDS} == {"toi_kolkata", "millenniumpost_bengal", "sangbadpratidin_kolkata",
                                     "abp_ananda_kolkata"}
    assert {f.language for f in FEEDS if f.id in ("sangbadpratidin_kolkata", "abp_ananda_kolkata")} == {"bn"}
    assert all(f.url.startswith("https://") for f in FEEDS)


# ── the service's own constants ──────────────────────────────────────────────────────────────────────────────


def test_city_constants_follow_the_city_pack():
    city = json.loads((REPO / "cities" / "kolkata" / "city.json").read_text(encoding="utf-8"))
    box = city["bbox"]
    assert CITY_BBOX == (box["south"], box["north"], box["west"], box["east"])
    for name in ("Kolkata", "Calcutta, West Bengal, India", "Howrah", "Bidhannagar"):
        assert KOLKATA_RE.search(name)
    assert not KOLKATA_RE.search("Salt Lake City, Utah") and not KOLKATA_RE.search("Mumbai")


def test_connectors_cover_every_source_and_the_user_agent_names_kolkata():
    assert set(CONNECTOR_NAMES) == set(SOURCE_NAMES)
    assert "Kolkata" in USER_AGENT and "sahoshi-osint-ingress/" in USER_AGENT


#: SHA-256 prefixes (16 hex) of the lower-cased words that must not appear in this service: the previous city and
#: state, its capital, the previous product's name, other companies' products and event words (kept as hashes so
#: this test does not write them either).
_BANNED_WORD_HASHES = frozenset({
    "0f31e6ebe465b032",
    "13ed070478ef62c3",
    "1fff55ae51b6ec52",
    "2cfc5335969c9228",
    "74c860f63661b29c",
    "866e67fdbbb6917d",
    "a56f3dbc3053cc78",
    "f5dd232ee6b02958",
})


def test_the_service_names_no_previous_city_or_other_product():
    import hashlib

    files = [*sorted((PACKAGE / "src").rglob("*.py")), *sorted((PACKAGE / "tests").rglob("*.py")),
             *sorted((PACKAGE / "tests" / "fixtures").rglob("*.json")), PACKAGE / "README.md",
             PACKAGE / "pyproject.toml"]
    hits = sorted({
        f"{p.relative_to(PACKAGE)}:{n}"
        for p in files
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        for word in re.findall(r"[A-Za-z]+", line)
        if hashlib.sha256(word.lower().encode()).hexdigest()[:16] in _BANNED_WORD_HASHES
    })
    assert not hits, hits


def test_a_kolkata_section_item_carries_the_city_area_hint():
    """An item filed in an outlet's Kolkata section is city evidence for the geo-resolver (area:kolkata); a Bengal
    section item is state-level (area:west_bengal); any other path gives no hint."""
    from osint_ingress.connectors.news_rss import section_area_hint

    assert section_area_hint("https://timesofindia.indiatimes.com/city/kolkata/x/articleshow/1.cms") == ["area:kolkata"]
    assert section_area_hint("https://www.sangbadpratidin.in/kolkata/x/") == ["area:kolkata"]
    assert section_area_hint("https://www.millenniumpost.in/bengal/x-123") == ["area:west_bengal"]
    assert section_area_hint("https://bengali.abplive.com/district/x") == []
    assert section_area_hint("") == []
