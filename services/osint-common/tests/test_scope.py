"""osint_common.scope: the deterministic scope gate (roads, crowds, weather, hazards, closures and services only).

Synthetic headlines in English, Bengali and Hindi. No real person, party or organisation is named here: the
party-name check is exercised with a fictional name added to the hash set for the test.
"""

from __future__ import annotations

import hashlib

import pytest

from osint_common import scope


@pytest.mark.parametrize(
    ("title", "reason"),
    [
        ("Daylight robbery at a shop near Gariahat crossing", "crime"),
        ("Two arrested for chain snatching on Rash Behari Avenue", "crime"),
        ("ছিনতাইয়ের অভিযোগে গ্রেফতার", "crime"),
        ("চুরির মামলা", "crime"),
        ("दुकान में चोरी", "crime"),
        ("Clash between two groups at Behala, stones pelted", "conflict"),
        ("দুই গোষ্ঠীর সংঘর্ষে ভাঙচুর", "conflict"),
        ("পাড়ায় দুই গোষ্ঠীর সংঘর্ষ", "conflict"),  # সংঘর্ষ with no vehicle: a clash
        ("बेहाला में झड़प", "conflict"),
        ("Election results: counting at the strong rooms", "political"),
        ("Voters queue at polling booths in Tollygunge", "political"),
        ("উপনির্বাচনে ভোট", "political"),
        ("चुनावी सभा के लिए प्रत्याशी पहुंचे", "political"),
    ],
)
def test_out_of_scope(title, reason):
    v = scope.screen(title)
    assert v.reason == reason and v.masked == 0


@pytest.mark.parametrize(
    "title",
    [
        "Two killed as a bus hits a truck on EM Bypass near Ruby",  # a road accident stays
        "Heavy rain: Thanthania waterlogged, Bidhan Sarani slow",
        "Fire in a Burrabazar godown, fire tenders on MG Road",
        "Durga Puja procession on Strand Road, roads closed till 22:00",
        "Heart attack patient taken by ambulance through a green corridor",  # 'attack' is not a cue
        "Pollution level rises in Kolkata",  # 'poll' is a whole word only
        "জলমগ্ন ঠনঠনিয়া, বিধান সরণিতে যানজট",
        "हावड़ा ब्रिज पर भारी जाम",
        "Thunderstorm warning for Kolkata",
        "দুটি ট্রেনের সংঘর্ষ, দুর্ঘটনায় আহত অনেকে",  # সংঘর্ষ with trains: a collision, not a clash
        "বাস ও লরির সংঘর্ষে ইএম বাইপাসে যানজট",
    ],
)
def test_in_scope_passes_unchanged(title):
    v = scope.screen(title, "")
    assert v.reason is None and v.masked == 0 and v.title == title


@pytest.mark.parametrize(
    ("title", "keeps"),
    [
        ("Political rally of party workers blocks AJC Bose Road, traffic diverted", "blocks AJC Bose Road"),
        ("রাজনৈতিক মিছিলে ধর্মতলায় যানজট", "ধর্মতলায় যানজট"),
        ("राजनीतिक रैली से सड़क जाम", "सड़क जाम"),
    ],
)
def test_a_gathering_on_a_road_keeps_place_and_impact_only(title, keeps):
    v = scope.screen(title)
    assert v.reason is None and v.masked >= 1
    assert keys_absent(v.title) and scope.WITHHELD in v.title and keeps in v.title


def keys_absent(text: str) -> bool:
    return all(w not in text for w in ("Political", "party workers", "রাজনৈতিক", "राजनीतिक"))


def test_a_political_item_without_a_road_or_a_gathering_is_dropped():
    assert scope.screen("Political meeting in a hall").reason == "political"  # a gathering, no road
    assert scope.screen("Political row over the road budget").reason == "political"  # a road, no gathering


def test_party_names_are_matched_by_hash_never_written(monkeypatch):
    fictional = "examplefront"
    digest = hashlib.sha256(fictional.encode()).hexdigest()[:16]
    assert digest not in scope.PARTY_HASHES
    monkeypatch.setattr(scope, "PARTY_HASHES", scope.PARTY_HASHES | {digest})
    assert scope.screen("Examplefront leader visits a pandal").reason == "political"
    v = scope.screen("Examplefront rally blocks Park Street, traffic diverted")
    assert v.reason is None and v.title.startswith(scope.WITHHELD) and "Park Street" in v.title
    # a Bengali case ending is removed before hashing
    bn = "উদাহরণদল"
    monkeypatch.setattr(scope, "PARTY_HASHES", scope.PARTY_HASHES | {hashlib.sha256(bn.encode()).hexdigest()[:16]})
    assert scope.screen(f"{bn}ের মিছিলে রাস্তা বন্ধ").masked == 1


def test_the_hash_set_is_hex_prefixes_only():
    assert len(scope.PARTY_HASHES) == 33
    assert all(len(h) == 16 and int(h, 16) >= 0 for h in scope.PARTY_HASHES)


def test_out_of_scope_classes():
    assert scope.screen_class("reported_crime") == "crime"
    assert scope.screen_class("public_conflict") == "conflict"
    assert scope.screen_class("unrest") == "political"
    for kept in ("road_accident", "fire", "urban_flooding", "infra_failure", "hazard", "public_gathering",
                 "procession", "road_closure", "weather_hazard", "general_news", None):
        assert scope.screen_class(kept) is None


def test_deterministic():
    title = "রাজনৈতিক মিছিলে ধর্মতলায় যানজট"
    assert scope.screen(title) == scope.screen(title)
