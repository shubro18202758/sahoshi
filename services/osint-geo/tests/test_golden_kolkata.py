"""The Kolkata golden set: synthetic headlines in English, Bengali, Hindi and mixed text, each with the geocode the
resolver must give (toponym, feature type, segment or junction, area scope), and the time budget.

It replaces the proof-of-concept parity check, which compared the resolver with another city's real geocodes
(README, "Tests"). Every headline is written for this test:
fictional publishers, no real person's name, no real event. The places are the City Pack's (``cities/kolkata``) and
the network's (``scripts/data/osm_network.json``); a place's name may honour a person (a road, a hospital, a square),
which is a place, never that person. The set covers the low-lying spots that waterlog at high tide (Thanthania,
Amherst Street, Park Circus, Kalighat, Behala, Kasba, Garia, Ultadanga, Mukundapur), bridges, stations, Durga Puja
pandals, police stations, hospitals, junctions, roads, the metro districts, state-level alerts and honest ``None``s.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import pytest

from osint_common import ethics
from osint_geo.resolver import GazetteerResolver

from _synthetic import make_signal

LOCAL = {"source": "reddit_rss", "publisher": "social-a.example/r/example_city"}
SACHET = {"source": "sachet_cap", "publisher": "sachet.ndma.gov.in"}
#: the whole set, title to geocode, cold (a fresh resolver) and warm: the PoC's budget for its 107 signals
TIME_BUDGET_S = 2.0


@dataclass(frozen=True)
class Golden:
    """One synthetic headline and the geocode it must give (``want`` ``None``: the honest ``None``)."""

    gid: str
    category: str
    language: str  # en, bn, hi or mixed
    title: str
    want: dict[str, Any] | None
    signal: dict[str, Any] = field(default_factory=dict)


def _place(toponym: str, feature_type: str, segment_id: int | None = None, junction_id: int | None = None) -> dict:
    return {"toponym": toponym, "feature_type": feature_type, "segment_id": segment_id, "junction_id": junction_id,
            "area_scope": None}


def _area(toponym: str, scope: str) -> dict:
    return {"toponym": toponym, "feature_type": "admin", "segment_id": None, "junction_id": None, "area_scope": scope}


GOLDEN: tuple[Golden, ...] = (
    # ---------------------------------------------- low-lying spots (an area has no road anchor: segment None)
    Golden("G01", "low_lying", "en", "Knee-deep water at Thanthania after overnight rain",
           _place("Thanthania", "landmark", segment_id=1058)),  # pre-linked to Bidhan Sarani
    Golden("G02", "low_lying", "bn", "আমহার্স্ট স্ট্রিটে হাঁটুজল, যান চলাচল বন্ধ",
           _place("Amherst Street", "neighbourhood")),
    Golden("G03", "low_lying", "en", "Park Circus waterlogged at high tide; buses diverted",
           _place("Park Circus", "neighbourhood")),
    Golden("G04", "low_lying", "hi", "कालीघाट में जलभराव, ऑटो सेवा बंद", _place("Kalighat", "neighbourhood")),
    Golden("G05", "low_lying", "bn", "বেহালার রাস্তায় জল জমেছে", _place("Behala", "neighbourhood")),
    Golden("G06", "low_lying", "en", "Waterlogging in Kasba's lanes after the cloudburst",
           _place("Kasba", "neighbourhood")),
    Golden("G07", "low_lying", "en", "Garia waterlogged after heavy rain", _place("Garia", "neighbourhood"), LOCAL),
    Golden("G08", "low_lying", "bn", "উল্টোডাঙায় জল জমে যানজট", _place("Ultadanga", "neighbourhood")),
    Golden("G09", "low_lying", "en", "Mukundapur flooded again; residents wade through water",
           _place("Mukundapur", "neighbourhood")),
    # ---------------------------------------------- bridges
    Golden("G10", "bridge", "en", "Howrah Bridge closed to heavy vehicles for repairs",
           _place("Howrah Bridge (Rabindra Setu)", "road", segment_id=1001)),
    Golden("G11", "bridge", "en", "Vidyasagar Setu toll plaza jam",
           _place("Vidyasagar Setu (NH12, Vidyasagar Flyover)", "road", segment_id=1003)),
    Golden("G12", "bridge", "bn", "মাঝেরহাট সেতুতে যানজট", _place("Majerhat bridge", "junction", junction_id=26)),
    Golden("G13", "bridge", "en", "Crack reported on Tallah bridge", _place("Tallah bridge", "neighbourhood")),
    Golden("G14", "bridge", "en", "Waterlogging at Dhakuria bridge underpass",
           _place("Dhakuria bridge", "neighbourhood")),
    # ---------------------------------------------- stations
    Golden("G15", "station", "en", "Overcrowding at Sealdah station after local trains cancelled",
           _place("Sealdah Station", "landmark", segment_id=1025)),
    Golden("G16", "station", "hi", "हावड़ा स्टेशन पर भारी भीड़",
           _place("Howrah Station (Howrah Bridge, Howrah end)", "junction", junction_id=2)),
    Golden("G17", "station", "en", "Crowd at Kolkata station after a train was cancelled",
           _place("Kolkata Station (Chitpur)", "landmark", segment_id=1062)),
    # ---------------------------------------------- Durga Puja pandals
    Golden("G18", "pandal", "en", "Bagbazar Sarbojanin draws huge Saptami crowds",
           _place("Bagbazar Sarbojanin", "landmark", segment_id=1060)),
    Golden("G19", "pandal", "bn", "সন্তোষ মিত্র স্কোয়্যারে প্যান্ডেলে ভিড়",
           _place("Santosh Mitra Square", "landmark", segment_id=1063)),
    Golden("G20", "pandal", "en", "Long queue at Ekdalia Evergreen pandal on Ashtami",
           _place("Ekdalia Evergreen", "landmark")),  # more than 900 m from every segment anchor: no road anchor
    Golden("G21", "pandal", "en", "Kumartuli Park pandal crowd spills onto the road",
           _place("Kumartuli Park", "landmark", segment_id=1053)),
    # ---------------------------------------------- police stations
    Golden("G22", "police_station", "en", "Complaint filed at Park Street thana",
           _place("Park Street Police Station", "poi", segment_id=1026)),
    Golden("G23", "police_station", "bn", "গড়িয়াহাট থানায় অভিযোগ",
           _place("Gariahat Police Station", "poi", segment_id=1033)),
    Golden("G24", "police_station", "hi", "बहूबाजार थाना के पास जाम",
           _place("Bowbazar Police Station", "poi", segment_id=1051)),
    # ---------------------------------------------- hospitals
    Golden("G25", "hospital", "en", "Ambulances queue outside SSKM Hospital",
           _place("SSKM Hospital", "landmark", segment_id=1028)),
    Golden("G26", "hospital", "en", "NRS hospital emergency ward shifted",
           _place("NRS Medical College", "landmark", segment_id=1025)),
    Golden("G27", "hospital", "bn", "মেডিক্যাল কলেজে আগুন",
           _place("Kolkata Medical College", "landmark", segment_id=1055), LOCAL),
    # ---------------------------------------------- junctions and roads
    Golden("G28", "junction", "en", "Signal failure at Gariahat more, long tailbacks",
           _place("Gariahat crossing", "junction", junction_id=23)),
    Golden("G29", "junction", "bn", "রুবি মোড়ে দুর্ঘটনা, বাইপাসে যানজট",
           _place("Ruby crossing", "junction", junction_id=29)),
    Golden("G30", "road", "en", "Car crashes into divider on EM Bypass near Kasba",
           _place("Eastern Metropolitan Bypass", "road", segment_id=1035)),
    Golden("G31", "road", "mixed", "Kolkata-r Park Street-e bhir, police diversion",
           _place("Mother Teresa Sarani (Park Street)", "road", segment_id=1027)),
    Golden("G32", "road", "mixed", "EM বাইপাসে Kasba-র কাছে দুর্ঘটনা",
           _place("Eastern Metropolitan Bypass", "road", segment_id=1035)),
    Golden("G33", "bridge", "mixed", "Ultadanga flyover-e jam, ঘুরপথে বাস",
           _place("Ultadanga flyover", "neighbourhood")),
    # ---------------------------------------------- the metro districts (R28: the district point, 0.40)
    Golden("G34", "district", "en", "Thunderstorm warning for Kolkata district",
           _area("Kolkata (district)", "district"),
           {**SACHET, "admin_codes": ["LGD:KOLKATA"], "place_names": ["Kolkata"]}),
    Golden("G35", "district", "en", "Heavy rain warning for Howrah district", _area("Howrah (district)", "district"),
           {**SACHET, "admin_codes": ["LGD:HOWRAH"], "place_names": ["Howrah"]}),
    Golden("G36", "district", "en", "Protest march reported", _area("Kolkata (district)", "district"),
           {"source": "gdelt_events", "publisher": None, "admin_codes": ["GDELT_ADM1:IN28"],
            "place_names": ["Kolkata, West Bengal, India"]}),
    # ---------------------------------------------- state-level alerts (no point, 0.25)
    Golden("G37", "state", "en", "Heavy rain likely over Howrah, Hooghly and Nadia",
           _area("West Bengal (state)", "state"),
           {**SACHET, "admin_codes": ["LGD:WEST_BENGAL"], "place_names": ["West Bengal"]}),
    Golden("G38", "state", "bn", "ঘূর্ণিঝড়ের সতর্কবার্তা: উপকূলবর্তী জেলায় ভারী বৃষ্টি",
           _area("West Bengal (state)", "state"),
           {"source": "wbsdma", "publisher": None, "admin_codes": ["LGD:WEST_BENGAL"]}),
    Golden("G39", "state", "hi", "पश्चिम बंगाल के तटीय जिलों में भारी बारिश", _area("West Bengal (state)", "state"),
           {"source": "imd", "publisher": None, "admin_codes": ["LGD:WEST_BENGAL"]}),
    # ---------------------------------------------- honest None: the same words elsewhere
    Golden("G40", "none", "en", "Waterlogging on Park Street in Bengaluru", None),
    Golden("G41", "none", "hi", "रामलीला मैदान में रैली", None),
)


def _signal(g: Golden):
    return make_signal(g.title, f"{g.title}. Details are awaited.", language="bn" if g.language == "mixed" else
                       g.language, **g.signal)


def _shape(geo) -> dict[str, Any] | None:
    if geo is None:
        return None
    return {"toponym": geo.toponym, "feature_type": geo.feature_type, "segment_id": geo.segment_id,
            "junction_id": geo.junction_id, "area_scope": geo.area_scope}


@pytest.fixture(scope="module")
def resolver() -> GazetteerResolver:
    return GazetteerResolver()


@pytest.mark.parametrize("g", GOLDEN, ids=[g.gid for g in GOLDEN])
def test_golden_geocode(resolver, g):
    geo = resolver.resolve(_signal(g))
    assert _shape(geo) == g.want, (g.gid, g.title, geo)
    if geo is None:
        return
    # the honest shape of each kind of answer
    if geo.feature_type == "neighbourhood":  # an area (F-HONEST OSINT-3): its point, never a road anchor
        assert geo.lon is not None and geo.snapped_to is None and geo.residual_m is None
    if geo.feature_type == "admin":  # R28: a district carries its representative point, a state none
        assert geo.area_level and geo.method == "area_fallback"
        assert (geo.lon is None) == (geo.area_scope == "state")
        assert geo.confidence == (0.4 if geo.area_scope == "district" else 0.25) and geo.bucket == "low"
    if geo.junction_id is not None or (geo.feature_type == "road" and geo.segment_id is not None):
        assert geo.residual_m == 0.0 and geo.snapped_to is None
    if geo.feature_type in ("landmark", "poi") and geo.snapped_to is not None:
        assert 0.0 < geo.residual_m <= 900.0


def test_the_golden_set_covers_the_city():
    assert len(GOLDEN) >= 30 and len({g.gid for g in GOLDEN}) == len(GOLDEN)
    assert {g.category for g in GOLDEN} == {"low_lying", "bridge", "station", "pandal", "police_station", "hospital",
                                           "junction", "road", "district", "state", "none"}
    assert {g.language for g in GOLDEN} == {"en", "bn", "hi", "mixed"}
    low = {g.want["toponym"] for g in GOLDEN if g.category == "low_lying" and g.want}
    assert low == {"Thanthania", "Amherst Street", "Park Circus", "Kalighat", "Behala", "Kasba", "Garia", "Ultadanga",
                   "Mukundapur"}
    assert {g.want["area_scope"] for g in GOLDEN if g.want and g.want["area_scope"]} == {"district", "state"}


def test_the_golden_headlines_name_no_person():
    # synthetic text only: the redactor finds nothing to redact in any headline (places are protected, no names)
    for g in GOLDEN:
        assert ethics.find_pii(g.title) == [], g.gid


def test_golden_geocodes_are_places_only(resolver):
    for g in GOLDEN:
        geo = resolver.resolve(_signal(g))
        if geo is not None:
            ethics.assert_no_person_keys(geo.model_dump(mode="json"))


def test_golden_is_deterministic(resolver):
    other = GazetteerResolver()
    for g in GOLDEN:
        s = _signal(g)
        a, b = resolver.resolve(s), other.resolve(s)
        assert (a and a.model_dump()) == (b and b.model_dump()), g.gid


def test_the_golden_set_resolves_well_within_the_time_budget():
    signals = [_signal(g) for g in GOLDEN]
    t0 = time.perf_counter()
    fresh = GazetteerResolver()  # a new resolver over the loaded gazetteer and network: the gates are rebuilt
    cold = [fresh.resolve(s) for s in signals]
    cold_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    for _ in range(5):
        warm = [fresh.resolve(s) for s in signals]
    warm_s = (time.perf_counter() - t0) / 5
    assert [_shape(x) for x in cold] == [_shape(x) for x in warm] == [g.want for g in GOLDEN]
    assert cold_s < TIME_BUDGET_S and warm_s < TIME_BUDGET_S / 4, (cold_s, warm_s)
