"""The Kolkata pipeline golden: the canonical synthetic fixtures plus Bengali reports, through the REAL Kolkata
resolver (``osint_geo.resolver.GazetteerResolver`` on the committed gazetteer), classified, fused, correlated,
scored, attached and counted. It replaces the proof-of-concept parity run of the previous city (see the README).

Every signal is synthetic: fictional publishers (``news-*.example``, ``news-bn-*.example``, ``social-a.example``),
texts written here, no real person's name. The Bengali texts reach the pipeline as ingress leaves them: every word
that is neither a gazetteer place nor an ordinary word is ``[WITHHELD]``, and ``pii_redactions`` counts each one.

The golden, in words:

* the EM Bypass case: four collision reports and one mob report near Kasba, one ``affray+collision`` situation on
  segment 1035 (EM Bypass, Ruby crossing to Science City), two news publishers, ``NEWS-REPORTED`` 0.65;
* two Bengali reports of waterlogging at Thanthania from two outlets' own feeds: ONE ``urban_flooding`` situation
  on segment 1058 (Bidhan Sarani), two independent publishers, ``NEWS-REPORTED`` 0.65;
* the Gariahat robbery: ``reported_crime`` at junction 23 (never ``crime_incident``);
* the Kolkata SACHET thunderstorm alert: a district-level ``weather_hazard`` (area, no segment), ``OFFICIAL-VERIFIED``;
* the West Bengal state-wide nowcasts (one English, one Bengali, naming other districts): held as outside the city;
* single social posts (a road closure at Taratala, a Puja crowd at Gariahat, in Bengali): held, aggregate-only;
* a Bengali "thin crowd" item at College Street: ``general_news``, held.
"""

from __future__ import annotations

import json
import random

import pytest

from analysis_fixtures import at, canonical_signals, make_signal
from osint_common import ethics, testing
from osint_common.types import RawOsintSignal
from osint_analysis.pipeline import (
    HELD_NOT_EVENT,
    HELD_SINGLE_SOCIAL,
    HELD_STATE_LEVEL,
    fused_event_id,
    run_pipeline,
)

resolver_module = pytest.importorskip("osint_geo.resolver", reason="the Kolkata resolver (osint-geo) is not importable")

WITHHELD = "[WITHHELD]"
NOW = at(240)


def _redact(text: str) -> tuple[str, int]:
    out, n = text, 0
    for span in reversed(ethics.unredactable_spans(text)):
        out, n = out[: span.start] + WITHHELD + out[span.end :], n + 1
    return out, n


def bengali(source: str, title: str, body: str, publisher: str, minutes: float, **kw) -> RawOsintSignal:
    """A Bengali signal as ingress emits it: title and text redacted, every withheld run counted."""
    t, n_title = _redact(title)
    b, n_text = _redact(f"{title}। {body}")
    sig = make_signal(source, title=t, text=b, publisher=publisher, published_at=at(minutes), pii=n_title + n_text,
                      source_id=f"synthetic:bn-{publisher.split('.')[0]}-{int(minutes)}", **kw)
    return sig.model_copy(update={"language": "bn"})


def thanthania_reports() -> list[RawOsintSignal]:
    """Two independently written Bengali reports of one waterlogging at Thanthania (Bidhan Sarani)."""
    return [
        bengali("news_rss", "ঠনঠনিয়ায় বিধান সরণিতে জল জমে যান চলাচল ব্যাহত",
                "ভোর থেকে টানা বৃষ্টিতে ঠনঠনিয়া কালীবাড়ির সামনে হাঁটুজল, বাস চলছে ধীরে।", "news-bn-a.example", 20),
        bengali("news_rss", "টানা বৃষ্টিতে জলমগ্ন ঠনঠনিয়া, নাকাল নিত্যযাত্রীরা",
                "বিধান সরণিতে জল জমেছে, পাম্প চালিয়েও জল নামেনি বলে পুরসভা সূত্রে খবর।", "news-bn-b.example", 45),
    ]


def bengali_extras() -> list[RawOsintSignal]:
    """A single Bengali social post, a Bengali state-wide nowcast naming other districts, a Bengali chatter item."""
    return [
        bengali("reddit_rss", "গড়িয়াহাটে প্যান্ডেলে উপচে পড়া ভিড়", "সন্ধ্যা থেকে লাইন, হাঁটাই যাচ্ছে না।",
                "social-a.example/r/example_city", 30),
        bengali("sachet_cap", "বাঁকুড়া ও পুরুলিয়া জেলায় বজ্রবিদ্যুৎ সহ বৃষ্টির সতর্কতা",
                "আগামী তিন ঘণ্টায় বজ্রবিদ্যুৎ সহ বৃষ্টির সম্ভাবনা।", "sachet.ndma.gov.in", -30,
                admin_codes=["LGD:WEST_BENGAL"], place_names=["পশ্চিমবঙ্গ"], valid_until=at(150)),
        bengali("news_rss", "কলেজ স্ট্রিটে বইয়ের দোকানে আজ ভিড় কম", "পুজোর পরে বাজার ফাঁকা।", "news-bn-a.example",
                60),
    ]


def golden_signals() -> list[RawOsintSignal]:
    return [*canonical_signals(), *thanthania_reports(), *bengali_extras()]


def run(signals=None):
    return run_pipeline(signals or golden_signals(), resolver=resolver_module.GazetteerResolver(),
                        live=testing.live_state_sealdah_pursuit(), now=NOW)


#: (is_event, class, subtype, toponym, segment, junction, area_level, held_reason, state, credibility,
#: independent publishers, members), in the pipeline's order (surfaced first, then by response priority).
GOLDEN = [
    (True, "road_accident", "affray+collision", "Eastern Metropolitan Bypass", 1035, None, False, None,
     "NEWS-REPORTED", 0.65, 2, 5),
    (True, "urban_flooding", "waterlogging", "Thanthania", 1058, None, False, None, "NEWS-REPORTED", 0.65, 2, 2),
    (True, "reported_crime", "daylight_robbery", "Gariahat crossing", None, 23, False, None, "NEWS-REPORTED", 0.6,
     1, 1),
    (True, "weather_hazard", "thunderstorm", "Kolkata (district)", None, None, True, None, "OFFICIAL-VERIFIED", 0.95,
     1, 1),
    (False, "weather_hazard", "thunderstorm", "West Bengal (state)", None, None, True, HELD_STATE_LEVEL,
     "OFFICIAL-VERIFIED", 0.95, 1, 2),
    (False, "public_gathering", "mass_gathering", "Gariahat", None, None, True, HELD_SINGLE_SOCIAL,
     "UNVERIFIED-OSINT", 0.25, 1, 1),
    (False, "road_closure", "closure", "Diamond Harbour Road (Majerhat bridge, Taratala flyover)", 1049, None, False,
     HELD_SINGLE_SOCIAL, "UNVERIFIED-OSINT", 0.25, 1, 1),
    (False, "general_news", None, "College Street", None, None, True, HELD_NOT_EVENT, "NEWS-REPORTED", 0.6, 1, 1),
]


def _row(r):
    return (r.is_event, r.event_class, r.subtype, r.toponym, r.segment_id, r.junction_id, r.area_level,
            r.held_reason, r.verification_state, r.credibility, r.independent_publishers, r.source_count)


def test_the_resolver_places_each_report_where_the_golden_expects():
    """A change here is the resolver's, not the analysis's: the geocodes the golden is built on."""
    geo = run().geocodes
    em = testing.em_bypass_signals()
    assert {(geo[s.signal_id].feature_type, geo[s.signal_id].segment_id) for s in em} == {("road", 1035)}
    assert geo[testing.gariahat_robbery_signal().signal_id].junction_id == 23
    assert geo[testing.sachet_district_signal().signal_id].area_scope == "district"
    assert geo[testing.sachet_state_signal().signal_id].area_scope == "state"
    for s in thanthania_reports():
        g = geo[s.signal_id]
        assert (g.toponym, g.feature_type, g.segment_id) == ("Thanthania", "landmark", 1058)
    assert all(g is not None for g in geo.values())


def test_the_kolkata_golden():
    result = run()
    assert [_row(r) for r in result.resolved] == GOLDEN
    withheld = sum(s.pii_redactions for s in [*thanthania_reports(), *bengali_extras()])
    assert withheld >= 5  # the Bengali texts really meet the redaction
    assert result.counts.model_dump() == {
        "signals": 14,
        "geotagged": 14,
        "incident_geotagged": 11,  # 5 EM Bypass, 2 Thanthania, the robbery, 3 alerts; not the closure, crowd, chatter
        "fused": 8,
        "surfaced": 4,
        "correlated": 1,
        "cross_type_corroborated": 0,
        "social_held": 2,
        "outside_city_held": 1,
        "pii_redactions": 2 + withheld,  # the canonical [PERSON] and [AGE], and the Bengali [WITHHELD] runs
        "attached_to_live": 0,  # nothing corroborates the Sealdah pursuit: a pursuit is never corroborated
    }
    em = result.resolved[0]
    assert em.correlated_classes == ["road_accident", "public_conflict"] and em.sahoshi_event_kind == "road_accident"
    assert em.label == "Road accident · Eastern Metropolitan Bypass"
    assert em.fused_event_id == fused_event_id(testing.em_bypass_signals())


def test_the_bengali_waterlogging_is_one_situation_at_thanthania():
    result = run()
    a, b = thanthania_reports()
    (flood,) = [r for r in result.resolved if a.signal_id in r.member_signal_ids]
    assert sorted(flood.member_signal_ids) == sorted([a.signal_id, b.signal_id])
    assert (flood.event_class, flood.subtype, flood.sahoshi_event_kind) == ("urban_flooding", "waterlogging",
                                                                           "flooding")
    assert flood.label == "Urban flooding · Thanthania" and flood.segment_id == 1058
    assert flood.summary == a.title  # the primary report's redacted Bengali headline
    assert {s.publisher for s in flood.sources} == {"news-bn-a.example", "news-bn-b.example"}
    assert all(s.url is None for s in flood.sources)  # a news URL can name a person: withheld
    assert flood.fused_event_id == fused_event_id([a])
    # the Kolkata district thunderstorm alert is a different level and class: it never joins the street situation
    assert testing.sachet_district_signal().signal_id not in flood.member_signal_ids


def test_one_outlet_or_one_syndicated_text_is_one_publisher():
    a, b = thanthania_reports()
    same_outlet = b.model_copy(update={"publisher": "news-bn-a.example", "url": None})
    (one,) = [r for r in run([a, same_outlet]).resolved]
    assert one.is_event and one.independent_publishers == 1 and one.credibility == 0.6
    copy = a.model_copy(update={"publisher": "news-bn-b.example", "url": None,
                                "signal_id": "f" * 40, "source_id": "synthetic:bn-copy"})
    (wire,) = [r for r in run([a, copy]).resolved]
    assert wire.source_count == 2 and wire.independent_publishers == 1 and wire.credibility == 0.6


def test_a_single_bengali_social_post_is_held_even_with_a_bengali_news_report_elsewhere():
    result = run()
    post = bengali_extras()[0]
    (held,) = [r for r in result.resolved if post.signal_id in r.member_signal_ids]
    assert not held.is_event and held.held_reason == HELD_SINGLE_SOCIAL and held.credibility <= 0.30
    assert held.attach.novel and held.second_order == []


def test_the_state_wide_nowcasts_are_held_as_outside_the_city():
    result = run()
    english, bengali_nowcast = testing.sachet_state_signal(), bengali_extras()[1]
    (held,) = [r for r in result.resolved if english.signal_id in r.member_signal_ids]
    assert bengali_nowcast.signal_id in held.member_signal_ids  # one aggregate per state and class
    assert held.held_reason == HELD_STATE_LEVEL and held.rep_lon is None and not held.is_event


def test_the_golden_is_the_same_in_any_input_order():
    signals = golden_signals()
    reference = run(signals).model_dump_json()
    rng = random.Random(1028)
    for _ in range(4):
        order = signals[:]
        rng.shuffle(order)
        assert run(order).model_dump_json() == reference


def test_the_golden_output_carries_no_person_and_never_crime_incident():
    result = run()
    dumped = result.model_dump(mode="json")
    ethics.assert_no_person_keys(dumped)
    blob = json.dumps(dumped, ensure_ascii=False)
    assert "crime_incident" not in blob and "vehicle_pursuit" not in blob
    for r in result.resolved:
        assert ethics.find_pii(r.label) == [] and ethics.find_pii(r.summary) == []
        # a Bengali text leaves the pipeline as ingress left it: nothing a redactor could not read
        assert ethics.find_unredactable(r.summary) == []
        assert all(ethics.find_unredactable(s.title) == [] for s in r.sources)
