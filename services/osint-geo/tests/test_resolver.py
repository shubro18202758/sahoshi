"""GazetteerResolver on the canonical synthetic fixtures (osint_common.testing) and on hand-made synthetic Kolkata
signals, in English, Bengali, Hindi and mixed text.

Every signal here is synthetic: fictional publishers (``*.example``), no real person, redacted placeholders only.
"""

from __future__ import annotations

import json
import re
import threading
import time

import pytest

from osint_common import ethics, testing
from osint_common.pipeline import GeoResolver
from osint_common.types import Geocode, RawOsintSignal
from osint_geo import resolver as resolver_mod
from osint_geo import translit
from osint_geo.gazetteer import Gazetteer, norm
from osint_geo.resolver import (
    CONTEXT_FORMS,
    DISTRICT_HOWRAH,
    DISTRICT_KOLKATA,
    DISTRICT_NORTH_24_PARGANAS,
    DISTRICT_WITHOUT_POINT,
    STATE_WEST_BENGAL,
    GazetteerResolver,
)

from _synthetic import make_signal

EM_BYPASS = "Eastern Metropolitan Bypass"
#: a city-scoped source (source locality 1.0): the fictional community on the fictional social host
LOCAL = {"source": "reddit_rss", "publisher": "social-a.example/r/example_city"}
SACHET = {"source": "sachet_cap", "publisher": "sachet.ndma.gov.in"}
#: a state-wide SACHET alert: state-level evidence only
WB = {**SACHET, "admin_codes": ["LGD:WEST_BENGAL"], "place_names": ["West Bengal"]}
#: GDELT's events export: a West Bengal ActionGeo with the state code
GDELT_IN28 = {"source": "gdelt_events", "publisher": None, "admin_codes": ["GDELT_ADM1:IN28"]}
#: another West Bengal city's ActionGeo_FullName (OS-2's GDELT hint)
SILIGURI = ["Siliguri, West Bengal, India"]


@pytest.fixture(scope="module")
def resolver() -> GazetteerResolver:
    return GazetteerResolver()


def _resolve(resolver: GazetteerResolver, title: str, text: str | None = None, **kwargs) -> Geocode | None:
    return resolver.resolve(make_signal(title, f"{title}. Details are awaited." if text is None else text, **kwargs))


# ----------------------------------------------------------------------------------------------- the protocol
def test_implements_the_geo_resolver_protocol(resolver):
    assert isinstance(resolver, GeoResolver)


# ----------------------------------------------------------------------------------------------- EM Bypass
def test_em_bypass_replica_resolves_to_segment_1035_near_kasba(resolver):
    first = testing.em_bypass_signals()[0]
    g = resolver.resolve(first)
    want = testing.em_bypass_geocode()
    assert isinstance(g, Geocode)
    assert g.model_dump() == want.model_dump()
    assert g.signal_id == first.signal_id == want.signal_id
    # EM Bypass has four segments (1035-1038): the reading nearest Kasba (coherence) is 1035, Ruby to Science City
    assert (g.toponym, g.feature_type, g.segment_id, g.junction_id) == (EM_BYPASS, "road", 1035, None)
    assert g.snapped_to is None and g.residual_m == 0.0 and g.method == "gazetteer_exact"
    assert g.confidence == 0.68 and g.bucket == "medium"
    assert not g.area_level and g.area_scope is None
    assert g.alternatives == ["Kasba"]


def test_every_em_bypass_report_lands_on_segment_1035(resolver):
    for s in testing.em_bypass_signals():
        g = resolver.resolve(s)
        assert g is not None and g.segment_id == 1035 and g.toponym == EM_BYPASS, (s.title, g)


def test_a_road_toponym_is_on_the_network(resolver):
    g = resolver.resolve(testing.em_bypass_signals()[1])
    assert g is not None and g.feature_type == "road" and g.toponym == EM_BYPASS
    assert g.segment_id == 1035 and g.residual_m == 0.0 and g.snapped_to is None


# ----------------------------------------------------------------------------------------------- Gariahat
def test_gariahat_robbery_replica_is_junction_23(resolver):
    g = resolver.resolve(testing.gariahat_robbery_signal())
    assert g is not None
    assert (g.toponym, g.feature_type, g.junction_id, g.segment_id) == ("Gariahat crossing", "junction", 23, None)
    assert g.residual_m == 0.0 and g.snapped_to is None
    assert g.confidence == pytest.approx(0.718, abs=0.001) and g.bucket == "medium"


# ----------------------------------------------------------------------------------------------- area levels (R28)
def test_sachet_district_alert_is_district_level(resolver):
    g = resolver.resolve(testing.sachet_district_signal())
    assert g is not None
    assert g.area_level and g.area_scope == "district" and g.method == "area_fallback" and g.feature_type == "admin"
    assert (g.lon, g.lat) == (DISTRICT_KOLKATA.lon, DISTRICT_KOLKATA.lat)
    assert g.confidence <= 0.4 and g.bucket == "low"
    assert g.segment_id is None and g.junction_id is None and g.snapped_to is None and g.residual_m is None
    assert g.toponym == "Kolkata (district)"


def test_sachet_state_nowcast_is_state_level_without_a_point(resolver):
    g = resolver.resolve(testing.sachet_state_signal())
    assert g is not None
    assert g.area_level and g.area_scope == "state" and g.method == "area_fallback"
    assert g.lon is None and g.lat is None
    assert g.confidence == STATE_WEST_BENGAL.confidence <= 0.25 and g.toponym == STATE_WEST_BENGAL.toponym
    assert g.toponym == "West Bengal (state)" and g.segment_id is None and g.junction_id is None


def test_the_howrah_district_has_its_own_point(resolver):
    g = _resolve(resolver, "Heavy rain warning for the district", admin_codes=["LGD:HOWRAH"], **SACHET)
    assert g is not None and g.toponym == "Howrah (district)" and g.area_scope == "district"
    assert (g.lon, g.lat) == (DISTRICT_HOWRAH.lon, DISTRICT_HOWRAH.lat) and g.confidence == 0.4


@pytest.mark.parametrize("hint", ["Howrah", "হাওড়া", "हावड़ा", "howrah"])
def test_a_hint_that_is_only_a_district_name_is_the_district(resolver, hint):
    # a CAP alert's area "Howrah" names the district: it scopes the signal but is never the "Howrah (city)" area pin
    # (which a 0.737 medium geocode made of a 0.40 district alert)
    s = make_signal("Heavy rain warning for Howrah district", admin_codes=["LGD:HOWRAH"], place_names=[hint], **SACHET)
    g = resolver.resolve(s)
    assert g is not None and g.toponym == "Howrah (district)" and g.area_scope == "district" and g.confidence == 0.4
    assert resolver.city_scoped(s) and resolver.explain(s)["mentions"] == []
    # a news item whose only hint is the district's name is no place at all
    assert resolver.resolve(make_signal("Road caves in", "Road caves in.", source="news_rss",
                                        place_names=[hint])) is None
    # the text naming the area still reads it
    g = _resolve(resolver, "Waterlogging in Howrah", admin_codes=["LGD:HOWRAH"], place_names=[hint], **SACHET)
    assert g is not None and g.toponym == "Howrah (city)"


@pytest.mark.parametrize("code", ["LGD:NORTH_24_PARGANAS", "LGD:SOUTH_24_PARGANAS"])
def test_a_24_parganas_alert_never_borrows_a_point(resolver, code):
    # the 24 Parganas hold Salt Lake, New Town, Behala and Garia, but also the Sundarbans: a district with no point.
    # C-T's district geocode carries a point, so until it accepts one without, such an alert is None (never an
    # exception, never a city point)
    s = make_signal("Heavy rain warning for the district", admin_codes=[code], **SACHET)
    g = resolver.resolve(s)
    if DISTRICT_WITHOUT_POINT:
        assert g is not None and g.area_scope == "district" and g.lon is None and g.confidence == 0.3
    else:
        assert g is None
    assert DISTRICT_NORTH_24_PARGANAS.lon is None
    # with the state code too, the alert is at least state level
    both = make_signal("Heavy rain warning for the district", admin_codes=[code, "LGD:WEST_BENGAL"], **SACHET)
    g = resolver.resolve(both)
    assert g is not None and g.lon is None and g.area_scope == ("district" if DISTRICT_WITHOUT_POINT else "state")


def test_the_district_contract_probe_reads_the_point_rule_only():
    # DISTRICT_WITHOUT_POINT says whether C-T accepts a district geocode with no point; the same probe with a point
    # is a valid geocode, so a False answer can only come from that rule
    fields = {"signal_id": "0" * 40, "toponym": "probe", "feature_type": "admin", "method": "area_fallback",
              "confidence": 0.30, "bucket": "low", "area_level": True, "area_scope": "district"}
    assert Geocode(lon=88.36, lat=22.57, **fields).area_scope == "district"
    try:
        Geocode(lon=None, lat=None, **fields)
        accepted = True
    except ValueError:
        accepted = False
    assert accepted is DISTRICT_WITHOUT_POINT


def test_the_city_districts_come_first(resolver):
    s = make_signal("Heavy rain warning", admin_codes=["LGD:NORTH_24_PARGANAS", "LGD:KOLKATA"], **SACHET)
    g = resolver.resolve(s)
    assert g is not None and g.toponym == "Kolkata (district)"


def test_gdelt_another_state_alone_is_none(resolver):
    s = make_signal("Clashes reported, details awaited", source="gdelt_events", publisher=None,
                    admin_codes=["GDELT_ADM1:IN07"])
    assert resolver.resolve(s) is None


def test_gdelt_in28_alone_is_state_level(resolver):
    s = make_signal("Protest reported, details awaited", **GDELT_IN28)
    g = resolver.resolve(s)
    assert g is not None and g.area_scope == "state" and g.lon is None and g.confidence <= 0.25


@pytest.mark.parametrize(
    ("fullname", "level"),
    [
        ("Kolkata, West Bengal, India", DISTRICT_KOLKATA),
        ("Calcutta, West Bengal, India", DISTRICT_KOLKATA),  # the GNS spelling a GDELT FullName may carry
        ("Howrah, West Bengal, India", DISTRICT_HOWRAH),  # the district's centroid, never the city's area pin
    ],
)
def test_a_gdelt_fullname_naming_a_city_district_is_that_district(resolver, fullname, level):
    s = make_signal("Protest reported, details awaited", place_names=[fullname], **GDELT_IN28)
    g = resolver.resolve(s)
    assert g is not None and g.toponym == level.toponym and g.area_scope == "district" and g.confidence <= 0.4
    assert (g.lon, g.lat) == (level.lon, level.lat)


def test_another_district_code_is_none(resolver):
    s = make_signal("Heavy rain warning for the district", admin_codes=["LGD:DARJEELING"], **SACHET)
    assert resolver.resolve(s) is None


@pytest.mark.parametrize("source", ["sachet_cap", "imd", "wbsdma", "kmc_scrape", "kolkata_police_scrape"])
def test_every_official_source_uses_the_area_fallback(resolver, source):
    s = make_signal("Heavy rain warning", source=source, publisher=None, admin_codes=["LGD:KOLKATA"])
    g = resolver.resolve(s)
    assert g is not None and g.toponym == "Kolkata (district)"


def test_only_official_and_gdelt_sources_use_the_area_fallback(resolver):
    # a news or social payload carrying an admin code is not an official area: no city centroid for it
    for kwargs in ({"source": "google_news_rss"}, {"source": "news_rss"}, LOCAL):
        s = make_signal("Rain all evening, roads slow", admin_codes=["LGD:KOLKATA"], **kwargs)
        assert resolver.resolve(s) is None, kwargs


def test_a_finer_toponym_beats_the_area_code(resolver):
    s = make_signal("Waterlogging warning", "Waterlogging likely near Thanthania during the next 3 hours.",
                    admin_codes=["LGD:KOLKATA"], **SACHET)
    g = resolver.resolve(s)
    assert g is not None and not g.area_level and g.toponym == "Thanthania" and g.segment_id == 1058


# ----------------------------------------------------------------------------------------------- honest None
@pytest.mark.parametrize(
    "title",
    [
        "Markets close higher on festive demand",
        "Weather to stay dry through the weekend, says forecaster",
        "Cricket: home side wins the series 3-1",
        "শেয়ারবাজারে সূচক বাড়ল",
        "बाजार में तेजी",
        "",
    ],
)
def test_unresolvable_text_is_none(resolver, title):
    s = make_signal(title or "No place named here", "Nothing in this report names a place in the city.")
    assert resolver.resolve(s) is None


@pytest.mark.parametrize(
    "title", ["Kolkata: traffic slow in the evening", "Calcutta sees slow traffic", "কলকাতায় সন্ধ্যায় যানজট",
              "कोलकाता में शाम को जाम"]
)
def test_a_city_name_alone_is_never_a_point(resolver, title):
    assert resolver.resolve(make_signal(title, f"{title}.", place_names=["Kolkata"])) is None
    assert resolver.resolve(make_signal(title, f"{title}.")) is None


# ------------------------------------------------------------------------------- "airport" is not a junction alias
@pytest.mark.parametrize(
    "title",
    [
        "Flights delayed at Delhi airport after fog",
        "Mumbai airport runway closed for repairs",
        "Bomb threat email sent to an airport",
    ],
)
def test_another_citys_airport_is_none(resolver, title):
    assert resolver.resolve(make_signal(title, f"{title}. Passengers were told to check their flight status.")) is None


def test_the_airport_word_never_gives_the_airport_junctions(resolver):
    g = _resolve(resolver, "Fire at the airport in Kolkata")
    assert g is None or g.junction_id not in (38, 49)
    assert resolver.gazetteer.lookup("airport") == ()


@pytest.mark.parametrize(
    ("title", "language"),
    [("Smoke seen near Kolkata airport", "en"), ("Smoke seen near Dum Dum airport", "en"),
     ("দমদম বিমানবন্দরে ধোঁয়া", "bn"), ("कोलकाता हवाई अड्डा पर धुआं", "hi")],
)
def test_the_airport_by_its_own_names(resolver, title, language):
    # the City Pack's airport, pre-linked to junction 49 (the terminal forecourt)
    g = _resolve(resolver, title, language=language)
    assert g is not None and g.toponym == "Kolkata Airport" and g.feature_type == "landmark"
    assert g.junction_id == 49 and g.segment_id is None


def test_the_airport_gate_junction_by_its_own_name(resolver):
    g = _resolve(resolver, "Jam at Kolkata Airport VIP Road gate")
    assert g is not None and g.junction_id == 38 and g.feature_type == "junction"


# ----------------------------------------------------------------------- the context gate (common words, namesakes)
ELSEWHERE = [
    ("Rally at Ramlila Maidan in Delhi", "en"),
    ("रामलीला मैदान में रैली", "hi"),  # the Hindi word for any field
    ("Protest at Azad Maidan in Mumbai", "en"),
    ("Kite festival at the maidan in Pune", "en"),
    ("Fire at Science City in Kapurthala", "en"),
    ("साइंस सिटी में आग", "hi"),
    ("Jam on MG Road in Bengaluru", "en"),
    ("Waterlogging on Park Street in Bengaluru", "en"),
    ("Salt Lake City, Utah: snow storm", "en"),
    ("Saltlake City snow storm", "en"),
    ("Shooting in Newtown, Connecticut", "en"),
    ("Fire at New Market in Bhopal", "en"),
    ("न्यू मार्केट में आग", "hi"),
    ("Jam on VIP Road in Guwahati", "en"),
    ("Jam on VIP Rd in Guwahati", "en"),
    ("Red Road closed for a parade in Guwahati", "en"),
    ("Strand Rd closed in Mumbai", "en"),
    ("Accident on GT Road in Ludhiana", "en"),
    ("Accident on Grand Trunk Road near Panipat", "en"),
    ("Fire at the medical college in Patna", "en"),
    ("Fire at medical college hospital in Patna", "en"),  # the fuzzy stage never reaches a longer form either
    ("Eco Park reopens in Patna", "en"),
    ("Tea stall fire on Central Avenue, Nagpur", "en"),
    ("Garia waterlogged after heavy rain", "en"),  # a word part and a town name elsewhere: needs the city
    ("Accident near the Sciense City in Kapurthala", "en"),
    ("Fire at New Markt in Bhopal", "en"),  # fuzzy matching never reaches a gated form either
]


@pytest.mark.parametrize(("title", "language"), ELSEWHERE)
def test_context_forms_from_elsewhere_are_none(resolver, title, language):
    # a national outlet that names no Kolkata word: these words mean something else there; one mention and two, and
    # with a next sentence starting "More" (never read as "... more", a crossing)
    for text in (f"{title}. More details are awaited.", title):
        assert resolver.resolve(make_signal(title, text, language=language)) is None, (title, text)


@pytest.mark.parametrize(
    ("title", "kwargs", "toponym"),
    [
        ("Waterlogging on Park Street, Kolkata", {}, "Mother Teresa Sarani (Park Street)"),  # the text names the city
        ("Water main burst on Park Street, 700016", {}, "Mother Teresa Sarani (Park Street)"),  # a Kolkata PIN
        ("Rally on the Maidan", {"place_names": ["Kolkata"]}, "Maidan"),  # a hint naming the city
        ("Crowd at Science City", LOCAL, "Science City"),  # a city-scoped source
        ("New Market closed for repairs", {"source": "kmc_scrape", "publisher": None}, "New Market"),
        ("Fire at the medical college", {"source": "kolkata_police_scrape", "publisher": None},
         "Kolkata Medical College"),
        ("Jam on Park Street", {"source": "news_rss", "category_hint": ["area:kolkata"]},
         "Mother Teresa Sarani (Park Street)"),  # a connector's city area hint
        ("Garia waterlogged after heavy rain, Kolkata", {}, "Garia"),
        ("কলকাতায় নিউ মার্কেটে আগুন", {"language": "bn"}, "New Market"),  # a Bengali case ending on both words
        ("कोलकाता के मैदान में रैली", {"language": "hi"}, "Maidan"),
        ("গড়িয়ায় জল জমেছে", {**LOCAL, "language": "bn"}, "Garia"),
    ],
)
def test_context_forms_count_in_a_signal_about_the_city(resolver, title, kwargs, toponym):
    g = _resolve(resolver, title, **kwargs)
    assert g is not None and g.toponym == toponym and g.method == "gazetteer_exact", (title, g)


@pytest.mark.parametrize(
    ("title", "toponym"),
    [
        ("Fire at Kolkata Medical College", "Kolkata Medical College"),
        ("Fire near NRS Medical College", "NRS Medical College"),
        ("Signal down at Park Street crossing", "Park Street crossing"),
        ("Theft reported at Park Street police station", "Park Street Police Station"),
        ("Crowd at Salt Lake Stadium", "Salt Lake Stadium (EM Bypass)"),
        ("Jam on the Salt Lake Bypass", "Salt Lake Bypass"),
        ("Book fair at Central Park Mela Ground (Salt Lake)", "Central Park Mela Ground (Salt Lake)"),
        ("Jam on EM Bypass after a breakdown", EM_BYPASS),
        ("Crowd at Kolkata Maidan", "Maidan"),
    ],
)
def test_the_longer_forms_that_carry_the_place_are_never_gated(resolver, title, toponym):
    g = _resolve(resolver, title)  # a national outlet
    assert g is not None and g.toponym == toponym, (title, g)


def test_the_gate_covers_the_bengali_and_hindi_spellings(resolver):
    assert {"ময়দান", "मैदान", "সায়েন্স সিটি", "साइंस सिटी", "নিউ মার্কেট", "न्यू मार्केट", "মেডিক্যাল কলেজ",
            "मेडिकल कॉलेज", "পার্ক স্ট্রিট", "पार्क स्ट्रीट", "সল্টলেক", "साल्टलेक", "নিউ টাউন", "न्यूटाउन",
            "গড়িয়া", "গরিয়া", "गरिया", "বাইপাস", "জিটি রোড", "এমজি রোড", "ভিআইপি রোড"} <= resolver.context_forms
    elsewhere = make_signal("শিলিগুড়িতে সায়েন্স সিটিতে ভিড়", "শিলিগুড়িতে সায়েন্স সিটিতে ভিড়।", language="bn")
    assert resolver.resolve(elsewhere) is None
    here = make_signal("কলকাতার সায়েন্স সিটিতে ভিড়", "কলকাতার সায়েন্স সিটিতে ভিড়।", language="bn")
    g = resolver.resolve(here)
    assert g is not None and g.junction_id == 30
    # the longer names that carry the place are never gated, in any script
    for form in ("ইএম বাইপাস", "পার্ক স্ট্রিট মোড়", "পার্ক স্ট্রিট থানা", "এনআরএস মেডিক্যাল কলেজ",
                 "कोलकाता मेडिकल कॉलेज", "নিউ মার্কেট থানা"):
        assert resolver.gazetteer.lookup(form) and norm(form) not in resolver.context_forms, form


@pytest.mark.parametrize(("latin", "variants"), [("new town", ["newtown"]), ("salt lake", ["saltlake"]),
                                                 ("vip road", ["v i p road", "vip rd"]), ("strand road", ["strand rd"]),
                                                 ("diamond harbour road", ["diamond harbor road"]),
                                                 ("garia", ["gariya"])])
def test_the_gate_covers_the_latin_variants(resolver, latin, variants):
    assert latin in resolver.context_forms
    for v in variants:
        assert resolver.gazetteer.lookup(v) == resolver.gazetteer.lookup(latin) and v in resolver.context_forms, v


def test_every_context_form_is_a_gazetteer_form_and_gated(resolver):
    for form in CONTEXT_FORMS:
        assert resolver.gazetteer.lookup(form), form
        assert norm(form) in resolver.context_forms, form
    # the state's name in the free text never opens the gate: Siliguri has a Science City too
    s = make_signal("Science City crowd in Siliguri, West Bengal", "Science City crowd in Siliguri, West Bengal.")
    assert resolver.resolve(s) is None
    assert resolver.explain(s)["context_open"] is False


def test_every_bare_route_code_is_gated(resolver):
    # a highway runs on through other towns and states: NH-12 through the districts of West Bengal (review r2)
    codes = {f for f in resolver.gazetteer.forms if re.fullmatch(r"(?:nh|ne|sh)\d+", f)}
    assert codes == {"nh12"}
    assert codes <= resolver.context_forms


def test_a_script_spelling_known_only_word_by_word_is_gated_too(resolver):
    # the gate reads a script form through to_latin when translit lists no whole-name spelling of it ("মেডিকেল কলেজ
    # হাসপাতাল" → "medical college hospital"); inject one into the Medical College entry
    form = norm("মেডিকেল কলেজ হাসপাতাল")
    assert form not in translit.script_aliases("medical college hospital")
    assert translit.to_latin(form) == "medical college hospital"
    doc = json.loads(resolver.gazetteer.path.read_text(encoding="utf-8"))
    entry = next(e for e in doc["entries"] if e["gaz_id"] == 202)  # Kolkata Medical College
    entry["surface_forms"] = sorted({*entry["surface_forms"], form})
    other = GazetteerResolver(gazetteer=Gazetteer.from_document(doc), network=resolver.network)
    assert form in other.context_forms
    elsewhere = make_signal("পাটনার মেডিকেল কলেজ হাসপাতালে আগুন", "পাটনার মেডিকেল কলেজ হাসপাতালে আগুন।", language="bn")
    assert other.resolve(elsewhere) is None
    here = make_signal("কলকাতার মেডিকেল কলেজ হাসপাতালে আগুন", "কলকাতার মেডিকেল কলেজ হাসপাতালে আগুন।", language="bn")
    g = other.resolve(here)
    assert g is not None and g.toponym == "Kolkata Medical College"


# ------------------------------------------------- the gate opens on CITY-level evidence only (review r2, R28)
@pytest.mark.parametrize(
    ("title", "kwargs"),
    [
        ("Jam on MG Road in Siliguri", {"source": "gdelt_doc", "publisher": None, "place_names": SILIGURI}),
        ("Fire near the medical college in Burdwan", {"source": "gdelt_doc", "publisher": None,
                                                      "place_names": SILIGURI}),
        # a GDELT DOC article whose URL names only the state (OS-2's _url_place_hints)
        ("Science City crowd in Siliguri", {"source": "gdelt_doc", "publisher": None, "place_names": ["west bengal"]}),
        ("New Market fire in Siliguri", {"source": "gdelt_doc", "publisher": None, "place_names": ["bengal"]}),
        ("Jam on Park Street", {"source": "news_rss", "category_hint": ["area:west_bengal"]}),
        # SACHET for another district: R28 says None
        ("Heavy rain likely; medical college on alert in Darjeeling",
         {**SACHET, "admin_codes": ["LGD:DARJEELING"], "place_names": ["Darjeeling"]}),
    ],
)
def test_state_or_other_city_evidence_never_opens_the_gate(resolver, title, kwargs):
    s = make_signal(title, f"{title}. Details are awaited.", **kwargs)
    assert resolver.resolve(s) is None, title
    ex = resolver.explain(s)
    assert ex["city_scoped"] is False and ex["context_open"] is False and ex["mentions"] == []


@pytest.mark.parametrize(
    ("title", "kwargs"),
    [
        ("Jam on MG Road in Siliguri", {**GDELT_IN28, "place_names": SILIGURI}),
        ("Fire near the medical college in Burdwan", {**GDELT_IN28, "place_names": SILIGURI}),
        ("Science City crowd in Siliguri", {"source": "gdelt_doc", "publisher": None,
                                            "admin_codes": ["GDELT_ADM1:IN28"]}),
        ("Heavy rain alert: waterlogging on Park Street in Siliguri", WB),
        ("Thunderstorm warning for Bankura; medical college on alert", WB),
        ("Crowd advisory near New Market in Siliguri", {"source": "wbsdma", "publisher": None,
                                                        "admin_codes": ["LGD:WEST_BENGAL"]}),
        ("Fog advisory for GT Road in Bardhaman", {"source": "imd", "publisher": None,
                                                   "admin_codes": ["LGD:WEST_BENGAL"]}),
    ],
)
def test_a_state_level_signal_naming_another_citys_place_stays_state_level(resolver, title, kwargs):
    s = make_signal(title, f"{title}. Stay indoors.", **kwargs)
    g = resolver.resolve(s)
    assert g is not None and g.area_scope == "state" and g.toponym == "West Bengal (state)", (title, g)
    assert g.lon is None and g.lat is None and g.confidence <= 0.25
    ex = resolver.explain(s)
    assert ex["city_scoped"] is False and ex["context_open"] is False
    assert resolver.source_locality(s) == 1.0  # the confidence term keeps the source's scope (the PoC's)


@pytest.mark.parametrize(
    ("title", "kwargs", "toponym"),
    [
        ("Heavy rain likely; medical college on alert",
         {**SACHET, "admin_codes": ["LGD:KOLKATA"], "place_names": ["Kolkata"]}, "Kolkata Medical College"),
        ("Protest outside the medical college", {**GDELT_IN28, "place_names": ["Kolkata, West Bengal, India"]},
         "Kolkata Medical College"),
        ("Protest outside the medical college", {**GDELT_IN28, "place_names": ["Calcutta, West Bengal, India"]},
         "Kolkata Medical College"),
        ("Fire at the medical college", {"source": "gdelt_doc", "publisher": None,
                                         "place_names": ["kolkata", "west bengal"]}, "Kolkata Medical College"),
        ("Water supply cut near New Market", {"source": "kmc_scrape", "publisher": None,
                                              "admin_codes": ["LGD:KOLKATA"]}, "New Market"),
        ("Diversion on Red Road tonight", {"source": "kolkata_police_scrape", "publisher": None},
         "Indira Gandhi Sarani (Red Road)"),
        ("Jam on GT Road", {"admin_codes": ["LGD:HOWRAH"], **SACHET}, "Grand Trunk Road"),
        ("Jam on Park Street", LOCAL, "Mother Teresa Sarani (Park Street)"),
    ],
)
def test_city_level_evidence_opens_the_gate(resolver, title, kwargs, toponym):
    s = make_signal(title, f"{title}. Details are awaited.", **kwargs)
    g = resolver.resolve(s)
    assert g is not None and g.toponym == toponym and not g.area_level, (title, g)
    ex = resolver.explain(s)
    assert ex["city_scoped"] is True and ex["context_open"] is True


def test_city_scoped_reads_city_level_metadata_only(resolver):
    city = [
        make_signal("Rain all evening", **LOCAL),
        make_signal("Rain all evening", source="kmc_scrape", publisher=None),
        make_signal("Rain all evening", source="kolkata_police_scrape", publisher=None),
        make_signal("Rain all evening", place_names=["Kolkata, West Bengal, India"]),
        make_signal("Rain all evening", place_names=["Calcutta"]),
        make_signal("Rain all evening", place_names=["Bidhannagar"]),
        make_signal("Rain all evening", admin_codes=["LGD:KOLKATA"]),
        make_signal("Rain all evening", admin_codes=["LGD:HOWRAH"]),
        make_signal("Rain all evening", category_hint=["area:kolkata"]),
        make_signal("Rain all evening", category_hint=["area:howrah"]),
        make_signal("Water main burst near the school, 700007"),
    ]
    state = [
        make_signal("Rain all evening", **SACHET),
        make_signal("Rain all evening", source="wbsdma", publisher=None),
        make_signal("Rain all evening", source="imd", publisher=None),
        make_signal("Rain all evening", place_names=["West Bengal"]),
        make_signal("Rain all evening", place_names=SILIGURI),
        make_signal("Rain all evening", admin_codes=["LGD:WEST_BENGAL"]),
        make_signal("Rain all evening", admin_codes=["GDELT_ADM1:IN28"]),
        make_signal("Rain all evening", admin_codes=["LGD:NORTH_24_PARGANAS"]),
        make_signal("Rain all evening", admin_codes=["LGD:SOUTH_24_PARGANAS"]),
        make_signal("Rain all evening", category_hint=["area:west_bengal"]),
        make_signal("Rain all evening", category_hint=["area:north_24_parganas"]),
    ]
    for s in city:
        assert resolver.city_scoped(s) and resolver.source_locality(s) == 1.0, (s.raw_geo_hint, s.category_hint)
    for s in state:  # full source locality (the confidence term), but not in the city
        assert not resolver.city_scoped(s) and resolver.state_scoped(s), (s.raw_geo_hint, s.category_hint)
        assert resolver.source_locality(s) == 1.0
    plain = make_signal("Kolkata: rain all evening")  # a national outlet naming the city in its text
    assert not resolver.city_scoped(plain) and resolver.source_locality(plain) == 0.3
    howrah_pin = make_signal("Water main burst near the school, 711101")  # a Howrah PIN is not a Kolkata PIN
    assert not resolver.city_scoped(howrah_pin)


# ---------------------------------------------------------- namesakes of other cities and states (review r2)
@pytest.mark.parametrize(
    "title",
    [
        "Truck overturns on NH-12 near Farakka",
        "Bus accident on NH 12 in Malda district",
        "Accident on NH12 near Krishnanagar",
        "Red Road parade rehearsal in Guwahati",
        "Lake Market traders protest in Bhubaneswar",
        "Jodhpur Park renovation work begins in Rajasthan",
        "Fair held at Chitpur village",
        "Salt lake dries up in Rajasthan",
        "Science City opens a new gallery in Lucknow",
        "Diamond Harbor Road closed for repairs",
        "Eastern bypass jammed in Siliguri",
    ],
)
def test_namesakes_from_elsewhere_are_none(resolver, title):
    # a national outlet whose text names no Kolkata word, one mention and two
    for text in (f"{title}. More details are awaited.", title):
        assert resolver.resolve(make_signal(title, text)) is None, (title, text)


@pytest.mark.parametrize(
    ("title", "kwargs", "want"),
    [
        ("Truck overturns on NH-12, Kolkata", {}, {"segment_id": 1028}),
        ("Waterlogging on Strand Road, Kolkata", {}, {"feature_type": "road"}),
        ("Rally on Red Road, Kolkata", {}, {"segment_id": 1013}),
        ("Jam on VIP Road, Kolkata", {}, {"toponym": "VIP Road (Kazi Nazrul Islam Avenue)"}),
        ("Science City crowd, Kolkata", {}, {"junction_id": 30}),
        ("Water main burst near New Market, 700087", {}, {"toponym": "New Market", "segment_id": 1017}),
        ("Jam at New Town", LOCAL, {"toponym": "New Town", "segment_id": None}),
        ("Waterlogging in Salt Lake", LOCAL, {"toponym": "Salt Lake (Bidhannagar)"}),
        ("Book fair crowd at Central Park Mela Ground", LOCAL, {"toponym": "Central Park Mela Ground (Salt Lake)"}),
        ("Fire at Jodhpur Park, Kolkata", {}, {"toponym": "Jodhpur Park"}),
        ("Crowd at Eco Park", LOCAL, {"toponym": "Eco Park"}),
    ],
)
def test_namesakes_count_in_a_signal_placed_in_the_city(resolver, title, kwargs, want):
    g = _resolve(resolver, title, **kwargs)
    assert g is not None, title
    for key, value in want.items():
        assert getattr(g, key) == value, (title, key, getattr(g, key))


# ------------------------------------------------------------- "Howrah": the trains, the district (review r2)
@pytest.mark.parametrize(
    ("title", "language"),
    [
        ("Howrah Mail delayed by four hours", "en"),
        ("Howrah Express derailed near Nagpur", "en"),
        ("Howrah Rajdhani cancelled", "en"),
        ("हावड़ा एक्सप्रेस देरी से चल रही है", "hi"),
        ("হাওড়া মেল দেরিতে চলছে", "bn"),
        ("Heavy rain in Howrah district", "en"),
        ("Heavy rain in Howrah, West Bengal", "en"),
    ],
)
def test_the_howrah_trains_and_district_are_not_the_city_area(resolver, title, language):
    assert _resolve(resolver, title, language=language) is None, title
    assert _resolve(resolver, title, language=language, **LOCAL) is None, title


def test_the_howrah_district_alert_is_the_district(resolver):
    g = _resolve(resolver, "Heavy rain in Howrah district", admin_codes=["LGD:HOWRAH"], **SACHET)
    assert g is not None and g.toponym == "Howrah (district)" and g.area_scope == "district"


@pytest.mark.parametrize(
    ("title", "want"),
    [
        ("Water logging in Howrah after rain", {"toponym": "Howrah (city)", "segment_id": None}),
        ("Jam on Howrah Bridge", {"segment_id": 1001}),
        ("Crowd at Howrah Station", {"junction_id": 2}),
        ("হাওড়া স্টেশনে ভিড়", {"junction_id": 2}),
        ("हावड़ा ब्रिज पर जाम", {"junction_id": 3}),
    ],
)
def test_the_howrah_places_still_resolve(resolver, title, want):
    g = _resolve(resolver, title)
    assert g is not None, title
    for key, value in want.items():
        assert getattr(g, key) == value, (title, key, getattr(g, key))


# --------------------------------- the state gate: a state-level alert names districts and towns (review r3)
#: an alert listing Howrah, Behala or Dum Dum among districts and blocks, in each script
STATE_ALERTS = [
    ("Heavy rain likely in Howrah, Hooghly and Nadia", "en"),
    ("হাওড়া, হুগলি ও নদিয়ায় ভারী বৃষ্টির সম্ভাবনা", "bn"),
    ("हावड़ा, हुगली और नदिया में भारी बारिश", "hi"),
    ("Thunderstorm likely over Behala and Budge Budge blocks", "en"),
    ("বেহালা ও বজবজে বজ্রবিদ্যুৎ সহ বৃষ্টি", "bn"),
    ("Heavy rain in Behela and Budge Budge", "en"),
    ("Waterlogging likely at Dum Dum and Barasat", "en"),
    ("দমদমে ভারী বৃষ্টি", "bn"),
]


@pytest.mark.parametrize(
    "kwargs",
    [
        WB,
        {"source": "wbsdma", "publisher": None, "admin_codes": ["LGD:WEST_BENGAL"], "place_names": ["West Bengal"]},
        {"source": "imd", "publisher": None, "admin_codes": ["LGD:WEST_BENGAL"]},
        {**GDELT_IN28, "place_names": ["Hooghly, West Bengal, India"]},
        {**GDELT_IN28, "place_names": ["West Bengal, India"]},
    ],
    ids=["sachet-lgd-wb", "wbsdma-lgd-wb", "imd-lgd-wb", "gdelt-in28-hooghly", "gdelt-in28-wb"],
)
@pytest.mark.parametrize(("title", "language"), STATE_ALERTS)
def test_a_state_level_alert_naming_a_district_or_block_stays_state_level(resolver, title, language, kwargs):
    # "Howrah" in a state-wide alert is the district (it is no city word there either), "Behala" and "Dum Dum" the
    # blocks: never the city's area pin with a point
    s = make_signal(title, f"{title}.", language=language, **kwargs)
    g = resolver.resolve(s)
    assert g is not None and g.toponym == "West Bengal (state)", (title, g)
    assert g.area_level and g.area_scope == "state" and g.method == "area_fallback" and g.feature_type == "admin"
    assert g.lon is None and g.lat is None and g.confidence == 0.25
    assert g.segment_id is None and g.junction_id is None
    ex = resolver.explain(s)
    assert ex["state_scoped"] is True and ex["city_scoped"] is False and ex["context_open"] is False
    assert ex["mentions"] == []


def test_a_24_parganas_alert_naming_a_block_is_no_city_pin(resolver):
    s = make_signal("Waterlogging likely at Dum Dum and Barasat", admin_codes=["LGD:NORTH_24_PARGANAS"], **SACHET)
    g = resolver.resolve(s)
    assert g is None or (g.area_scope == "district" and g.lon is None)
    assert resolver.explain(s)["mentions"] == []


def test_the_state_gate_covers_every_spelling(resolver):
    assert set(resolver_mod.STATE_GATED_FORMS) == {"howrah", "howrah city", "behala", "dum dum"}
    assert resolver.state_forms == {
        "howrah", "howrah city", "হাওড়া", "हावड़ा", "হাওড়া শহর", "behala", "behalaa", "behela", "বেহালা", "बेहाला",
        "dum dum", "dumdum", "দমদম", "দম দম", "दमदम", "दम दम",
    }
    # the longer names that carry the place are never state-gated
    for form in ("howrah station", "howrah bridge", "behala chowrasta", "behala police station", "dum dum airport",
                 "হাওড়া স্টেশন", "বেহালা চৌরাস্তা", "হাওড়া ব্রিজ কলকাতা প্রান্ত"):
        assert resolver.gazetteer.lookup(form) and form not in resolver.state_forms, form


@pytest.mark.parametrize(
    ("title", "kwargs", "language"),
    [
        # the district code is city-level evidence: the neighbourhood
        ("Waterlogging in Behala", {**SACHET, "admin_codes": ["LGD:KOLKATA"], "place_names": ["Kolkata"]}, "en"),
        ("Waterlogging in Behala", {**SACHET, "admin_codes": ["LGD:KOLKATA"]}, "en"),
        # a state alert whose text names the city: the city word is city-level evidence
        ("Waterlogging in Behala, Kolkata", WB, "en"),
        ("কলকাতার বেহালায় জল জমেছে", WB, "bn"),
        # GDELT's FullName naming the city
        ("Waterlogging in Behala", {**GDELT_IN28, "place_names": ["Kolkata, West Bengal, India"]}, "en"),
        # a national outlet with no state evidence keeps the form, and so does a city-scoped source
        ("Waterlogging in Behala", {}, "en"),
        ("Waterlogging in Behala", LOCAL, "en"),
    ],
)
def test_city_level_evidence_or_none_keeps_the_behala_neighbourhood(resolver, title, kwargs, language):
    s = make_signal(title, f"{title}.", language=language, **kwargs)
    g = resolver.resolve(s)
    assert g is not None and g.toponym == "Behala" and g.feature_type == "neighbourhood", (title, kwargs, g)
    # an area (F-HONEST OSINT-3): its point, never a segment
    assert g.segment_id is None and g.junction_id is None and g.snapped_to is None and g.residual_m is None
    assert g.lon is not None and g.lat is not None


def test_the_howrah_district_code_keeps_the_howrah_area(resolver):
    g = _resolve(resolver, "Waterlogging in Howrah", admin_codes=["LGD:HOWRAH"], **SACHET)
    assert g is not None and g.toponym == "Howrah (city)" and g.feature_type == "neighbourhood"


# ---------------------------------------------------------------------------- the geo hints read (review r2)
def test_only_the_first_hints_are_read(resolver):
    assert (resolver_mod.MAX_HINTS, resolver_mod.MAX_HINT_CHARS) == (8, 200)
    filler = [f"filler {i}" for i in range(8)]
    s = make_signal("Road blocked after a fall of trees", "Traffic diverted.", place_names=[*filler, "Thanthania"])
    assert resolver.resolve(s) is None  # the ninth hint is not read
    s = make_signal("Road blocked after a fall of trees", "Traffic diverted.", place_names=[*filler, "Kolkata"])
    assert resolver.source_locality(s) == 0.3 and not resolver.city_scoped(s)
    cut = make_signal("Road blocked after a fall of trees", "Traffic diverted.",
                      place_names=["x" * 200 + " Thanthania"])
    assert resolver.resolve(cut) is None  # past the hint's 200th character
    within = make_signal("Road blocked after a fall of trees", "Traffic diverted.",
                         place_names=[*filler[:-1], "Thanthania"])
    g = resolver.resolve(within)
    assert g is not None and g.toponym == "Thanthania"


def test_a_maximal_hostile_signal_stays_cheap(resolver):
    # 64 hints of 1000 characters of near-miss names: no exact form, so the fuzzy stage scans what is read
    words = ["edenn", "gardns", "rabindraa", "sadann", "santoshh", "mitraa", "squre", "colege", "sqaree", "moree"]
    blob = " ".join(words[i % len(words)] for i in range(400))
    s = make_signal(blob[:1000], blob[:4000], place_names=[blob[:1000]] * 64, **LOCAL)
    t0 = time.perf_counter()
    resolver.resolve(s)
    assert time.perf_counter() - t0 < 1.0


def test_the_operator_lookup_is_about_the_city(resolver):
    # GET /osint/gazetteer/resolve: an operator's query is local, so the gate is open
    top = resolver.resolve_text("maidan")
    assert top and top[0]["canonical_name"] == "Maidan"


# ----------------------------------------------------------------------------------- generator aliases (review r1)
@pytest.mark.parametrize(
    ("title", "segment_id"),
    [("Jam on Bijon Setu", 1034), ("Accident near Parama Circle", 1036), ("Jam on Vidyasagar Setu", 1003)],
)
def test_a_bridge_or_circle_the_road_runs_over_names_the_road(resolver, title, segment_id):
    g = _resolve(resolver, title)
    assert g is not None and g.feature_type == "road" and g.segment_id == segment_id, (title, g)


# ------------------------------------------------------------------------------------ social, grammar, scripts
def test_social_post_resolves_to_the_road_it_names(resolver):
    s = testing.social_single_signal()  # "Road closed for metro work near Taratala on Diamond Harbour Road"
    g = resolver.resolve(s)
    assert g is not None and g.feature_type == "road" and g.segment_id == 1049
    assert "Taratala" in g.alternatives
    # r/<community> is a city-scoped source: full locality, and the gate is open for "Diamond Harbour Road"
    assert resolver.source_locality(s) == 1.0 and resolver.city_scoped(s)


@pytest.mark.parametrize(
    ("title", "junction_id"),
    [("Car fire near Gariahat mor", 23), ("Car fire near Hazra mor", 18), ("Jam at Park Circus xing", 17),
     ("Jam near Majerhat setu", 26)],
)
def test_more_and_setu_are_rewritten_to_the_junction(resolver, title, junction_id):
    g = _resolve(resolver, title)
    assert g is not None and g.junction_id == junction_id and g.method == "grammar", (title, g)
    # the bare area word would also read as the neighbourhood: the rewrite is unambiguous
    assert "Gariahat" not in g.alternatives


@pytest.mark.parametrize(
    ("title", "language", "want"),
    [
        ("বেহালায় একটি দোকানে আগুন", "bn", {"toponym": "Behala"}),
        ("বেহালার রাস্তাতে জল জমেছে", "bn", {"toponym": "Behala"}),
        ("গড়িয়াহাটের দোকানে আগুন", "bn", {"toponym": "Gariahat"}),
        ("উল্টোডাঙার রাস্তায় জল", "bn", {"toponym": "Ultadanga"}),
        ("শিয়ালদায় ভিড়", "bn", {"toponym": "Sealdah Station"}),
        ("রুবি মোড়ের কাছে দুর্ঘটনা", "bn", {"junction_id": 29}),
        ("গড়িয়াহাটের মোড়ে দুর্ঘটনা", "bn", {"junction_id": 23}),
        ("পার্ক সার্কাসের মোড়ে যানজট", "bn", {"junction_id": 17}),
        ("ঠনঠনিয়ায় বিধান সরণিতে জল জমে", "bn", {"toponym": "Thanthania", "segment_id": 1058}),
        ("কালীঘাটের মন্দিরে ভিড়", "bn", {"toponym": "Kalighat Temple"}),
        ("बेहाला में दुकान में आग", "hi", {"toponym": "Behala"}),
        ("हाजरा मोड़ पर जाम", "hi", {"junction_id": 18}),
        ("सियालदह स्टेशन पर भीड़", "hi", {"toponym": "Sealdah Station"}),
        ("कोलकाता में पार्क स्ट्रीट पर जलभराव", "hi", {"toponym": "Mother Teresa Sarani (Park Street)"}),
    ],
)
def test_bengali_and_hindi_text(resolver, title, language, want):
    g = _resolve(resolver, title, f"{title}।", language=language)
    assert g is not None, title
    for key, value in want.items():
        assert getattr(g, key) == value, (title, key, getattr(g, key))
    if g.feature_type == "neighbourhood":  # an area, never a segment
        assert g.segment_id is None and g.junction_id is None


@pytest.mark.parametrize(
    ("title", "want"),
    [
        ("Kolkata e Park Street-e jol jomeche", {"toponym": "Mother Teresa Sarani (Park Street)"}),
        ("Gariahat-e bhir, Park Circus more-e jam", {"junction_id": 17}),
        ("জ্যাম near Gariahat more", {"junction_id": 23}),
        ("ইএম বাইপাসে কসবার কাছে দুর্ঘটনা", {"segment_id": 1035}),
        ("EM বাইপাসে দুর্ঘটনা", {"segment_id": 1035}),
        ("Waterlogging at ঠনঠনিয়া kalibari", {"toponym": "Thanthania"}),
    ],
)
def test_mixed_bengali_and_english_text(resolver, title, want):
    g = _resolve(resolver, title)
    assert g is not None, title
    for key, value in want.items():
        assert getattr(g, key) == value, (title, key, getattr(g, key))


@pytest.mark.parametrize(
    ("title", "toponym"),
    [
        ("Waterlogging near Gariahaat", "Gariahat"),
        ("Waterlogging near Goriahat", "Gariahat"),
        ("Crowd at Shealdah station", "Sealdah Station"),
        ("Crowd at Sealdaha", "Sealdah Station"),
        ("Waterlogging in Behalaa", "Behala"),
        ("Waterlogging in Behela", "Behala"),
        ("Jam at Tollyganj", "Tollygunge"),
        ("Jam at Tollygunj", "Tollygunge"),
        ("Waterlogging in Bidhannagar", "Salt Lake (Bidhannagar)"),
        ("Bidhan Nagar waterlogged", "Salt Lake (Bidhannagar)"),
        ("Waterlogging in Salt Lake", "Salt Lake (Bidhannagar)"),  # "Salt Lake" is gated: the hint names the city
        ("Jam at Ultodanga", "Ultadanga"),
        ("Waterlogging at Mukundpur", "Mukundapur"),
        ("Jam at Khidirpur", "Kidderpore"),
        ("Jam near Bhowanipur", "Bhowanipore"),
        ("Rain at Kalighaat", "Kalighat"),
    ],
)
def test_romanised_variants_and_misspellings(resolver, title, toponym):
    g = _resolve(resolver, title, place_names=["Kolkata"])
    assert g is not None and g.toponym == toponym, (title, g)
    assert g.method == "gazetteer_exact" and g.junction_id is None  # an area word, never the junction


@pytest.mark.parametrize(
    "text",
    [
        "বেহালায় আগুন",  # "য়" as one code point (U+09DF)
        "বেহালায় আগুন",  # "য" + nukta
    ],
)
def test_both_spellings_of_the_bengali_ya_ending(resolver, text):
    assert [m.form for m in resolver.mentions(text, city=True)] == ["বেহালা"]


def test_the_bengali_case_endings_of_city_and_road_words(resolver):
    # "কলকাতায়" (in Kolkata) names the city and opens the gate; "শহরের" (of the city) and "রাস্তাতে" (on the road)
    # name no place
    assert resolver.names_city(resolver.tokens("কলকাতায় জল জমেছে"))
    assert resolver.mentions("শহরের রাস্তাতে জল জমেছে") == []
    assert [m.form for m in resolver.mentions("কলকাতায় পার্ক স্ট্রিটে জল জমেছে")] == ["পার্ক স্ট্রিট"]
    assert resolver.mentions("পার্ক স্ট্রিটে জল জমেছে") == []  # no city word: the gated form is no mention


def test_a_landmark_near_a_junction_still_snaps_to_a_segment(resolver):
    # Rabindra Sadan's point is 37 m from Exide crossing (junction 13): a landmark keeps its own name and snaps
    g = _resolve(resolver, "Crowd outside Rabindra Sadan", **LOCAL)
    assert g is not None and g.feature_type == "landmark" and g.toponym == "Rabindra Sadan"
    assert g.segment_id == 1028 and g.junction_id is None and g.snapped_to == "AJC Bose Road Flyover"


def test_place_name_hints_are_read(resolver):
    s = make_signal("Road blocked after a fall of trees", "Traffic diverted after trees fell.",
                    place_names=["Thanthania"])
    g = resolver.resolve(s)
    assert g is not None and g.toponym == "Thanthania"


# ------------------------------------------------------------------- sentence ends and "more than" (English words)
@pytest.mark.parametrize(
    ("title", "text", "toponym", "language"),
    [
        ("Fire at Gariahat", "Fire at Gariahat. More details awaited.", "Gariahat", "en"),
        ("Crowd at Sealdah", "Crowd at Sealdah. More trains cancelled.", "Sealdah Station", "en"),
        ("Rain at Park Circus", "Rain at Park Circus! More rain expected.", "Park Circus", "en"),
        ("আগুন লাগল গড়িয়াহাটে", "আগুন লাগল গড়িয়াহাটে। মোড়ের কাছে ভিড়।", "Gariahat", "bn"),
        ("Waterlogging at Gariahat", "Waterlogging at Gariahat more than knee deep.", "Gariahat", "en"),
        ("Park Circus jam", "Park Circus more than an hour jammed.", "Park Circus", "en"),
    ],
)
def test_a_crossing_is_never_read_across_a_sentence_end_or_from_more_than(resolver, title, text, toponym, language):
    # "Gariahat. More ..." and "Gariahat more than ..." name the neighbourhood, never "Gariahat more" (junction 23)
    g = resolver.resolve(make_signal(title, text, language=language))
    assert g is not None and g.toponym == toponym and g.junction_id is None, (text, g)


def test_a_crossing_named_more_still_resolves(resolver):
    for text in ("Jam at Gariahat more since morning.", "Jam at Gariahat more. Details awaited."):
        g = resolver.resolve(make_signal("Jam", text))
        assert g is not None and g.junction_id == 23, text


def test_abbreviations_and_initials_never_end_a_sentence(resolver):
    g = _resolve(resolver, "Waterlogging on Dr. Suresh Sarkar Road")
    assert g is not None and g.toponym == "Dr Suresh Sarkar Road"
    g = _resolve(resolver, "Crash near A.J.C. Bose Road")
    assert g is not None and g.feature_type == "road" and "Bose Road" in g.toponym
    assert resolver.tokens("Gariahat. More") == ["gariahat", resolver_mod.SENTENCE_BREAK, "more"]
    assert resolver_mod.SENTENCE_BREAK not in resolver.tokens("Jam near A.J.C. Bose Rd. flyover")


# ----------------------------------------------------------------------------------------------- confidence inputs
def test_source_locality(resolver):
    assert resolver.source_locality(testing.em_bypass_signals()[0]) == 0.3  # a national aggregator, no hint
    assert resolver.source_locality(testing.sachet_district_signal()) == 1.0
    hinted = make_signal("Rain at Behala", place_names=["Kolkata"])
    assert resolver.source_locality(hinted) == 1.0
    pinned = make_signal("Water main burst", "A water main burst near the school, 700007.")
    assert resolver.source_locality(pinned) == 1.0
    # the city's name in the free text is not locality (national outlets name it in passing)
    assert resolver.source_locality(make_signal("Kolkata: rain at Behala")) == 0.3


def test_repeated_mentions_never_inflate_confidence(resolver):
    once = make_signal("Fire near Eden Gardens", "Fire brigade called.")
    twice = make_signal("Fire near Eden Gardens", "Fire near Eden Gardens, fire brigade called.", n=2)
    g1, g2 = resolver.resolve(once), resolver.resolve(twice)
    assert g1 is not None and g2 is not None and g1.toponym == g2.toponym == "Eden Gardens"
    assert g2.confidence <= g1.confidence


def test_confidence_and_bucket_agree(resolver):
    for s in [*testing.em_bypass_signals(), testing.gariahat_robbery_signal(), testing.social_single_signal()]:
        g = resolver.resolve(s)
        assert g is not None
        assert g.bucket == ("high" if g.confidence >= 0.75 else "medium" if g.confidence >= 0.5 else "low")


# ----------------------------------------------------------------------------------------------- determinism, threads
def _all_fixture_signals() -> list[RawOsintSignal]:
    return [
        *testing.em_bypass_signals(),
        testing.gariahat_robbery_signal(),
        testing.sachet_district_signal(),
        testing.sachet_state_signal(),
        testing.social_single_signal(),
    ]


def test_deterministic_across_resolvers(resolver):
    other = GazetteerResolver()
    for s in _all_fixture_signals():
        a, b, c = resolver.resolve(s), resolver.resolve(s), other.resolve(s)
        assert (a and a.model_dump()) == (b and b.model_dump()) == (c and c.model_dump())


def test_thread_safe_after_load(resolver):
    signals = _all_fixture_signals()
    want = [g and g.model_dump() for g in (resolver.resolve(s) for s in signals)]
    errors: list[BaseException] = []
    results: list[list] = []

    def work() -> None:
        try:
            for _ in range(20):
                results.append([g and g.model_dump() for g in (resolver.resolve(s) for s in signals)])
        except BaseException as exc:  # pragma: no cover - reported below
            errors.append(exc)

    threads = [threading.Thread(target=work) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert all(r == want for r in results) and len(results) == 160


def test_a_mapping_is_validated_as_a_raw_signal(resolver):
    s = testing.gariahat_robbery_signal()
    g = resolver.resolve(s.model_dump(mode="json"))
    assert g is not None and g.junction_id == 23
    bad = s.model_dump(mode="json")
    bad["author"] = "someone"  # a person key never gets through
    with pytest.raises(ValueError, match="forbidden_key"):
        resolver.resolve(bad)


def test_geocodes_name_places_never_persons(resolver):
    for s in _all_fixture_signals():
        g = resolver.resolve(s)
        if g is not None:
            dumped = g.model_dump(mode="json")
            ethics.assert_no_person_keys(dumped)
            assert set(dumped) == set(Geocode.model_fields)


def test_explain_reports_forms_never_the_text(resolver):
    s = testing.em_bypass_signals()[0]
    ex = resolver.explain(s)
    assert ex["geocode"]["toponym"] == EM_BYPASS and ex["locality"] == 0.3
    assert {m["form"] for m in ex["mentions"]} >= {"em bypass", "kasba"}
    assert s.title not in repr(ex) and "speeding" not in repr(ex)


def test_default_resolver_is_shared():
    assert resolver_mod.default_resolver() is resolver_mod.default_resolver()


def test_a_hostile_text_stays_cheap(resolver):
    # a 4000-character text that repeats a two-segment name: coherence runs over the distinct points, not pairs
    body = ("park street " * 400)[:3990]
    s = make_signal("Park Street, Kolkata", body)  # the city named: the context gate is open
    t0 = time.perf_counter()
    g = resolver.resolve(s)
    assert time.perf_counter() - t0 < 1.0
    assert g is not None and g.feature_type == "road" and g.segment_id in (1026, 1027)
    # the same text from elsewhere is no mention at all, just as fast
    t0 = time.perf_counter()
    assert resolver.resolve(make_signal("Park Street", body)) is None
    assert time.perf_counter() - t0 < 1.0


# ---------------------------------------------------------------------------- F-HONEST OSINT-1 / OSINT-3
def test_an_area_mention_is_never_pinned_on_the_junction_named_after_it(resolver):
    # "Gariahat" alone is the neighbourhood; the junction is "Gariahat crossing" (OSINT-1)
    g = _resolve(resolver, "Gold looted from a shop in Gariahat; traders protest")
    assert g is not None and g.toponym == "Gariahat" and g.feature_type == "neighbourhood"
    assert g.junction_id is None and g.segment_id is None and g.residual_m is None
    # the junction's own name still pins the junction
    g = _resolve(resolver, "Robbery at Gariahat crossing")
    assert g is not None and g.junction_id == 23


@pytest.mark.parametrize(
    ("word", "toponym"),
    [("Tollygunge", "Tollygunge"), ("Kalighat", "Kalighat"), ("Ultadanga", "Ultadanga"),
     ("Kidderpore", "Kidderpore"), ("Taratala", "Taratala"), ("Baguiati", "Baguiati"), ("Lake Town", "Lake Town"),
     ("Bagbazar", "Bagbazar"), ("Behala", "Behala"), ("Sealdah", "Sealdah Station"), ("Moulali", None)],
)
def test_a_bare_area_word_is_the_area_never_the_junction_named_after_it(resolver, word, toponym):
    g = _resolve(resolver, f"Water supply cut in {word} today")
    if toponym is None:  # Moulali has no area entry: the junction is named "Moulali" itself
        assert g is not None and g.junction_id == 15
        return
    assert g is not None and g.toponym == toponym and g.junction_id is None, (word, g)


def test_a_landmark_beyond_900_m_keeps_no_segment_and_no_snap_credit(resolver):
    for title, toponym in (("Crowd at Ruby General Hospital", "Ruby General Hospital"),
                           ("Crowd at Dakshineswar temple", "Dakshineswar Kali Temple")):
        g = _resolve(resolver, title)
        assert g is not None and g.toponym == toponym
        assert g.segment_id is None and g.snapped_to is None and g.residual_m is None
