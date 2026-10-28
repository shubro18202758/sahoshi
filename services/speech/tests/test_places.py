"""Place matching across Bengali script, romanised Bengali and English."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_service.places import ALIASES, Gazetteer, fold_bn, load_gazetteer, skeleton


@pytest.mark.parametrize("bn,en", [
    ("গড়িয়াহাট", "Gariahat"), ("এসপ্ল্যানেড", "Esplanade"), ("ধর্মতলা", "Dharmatala"),
    ("শিয়ালদহ", "Sealdah"), ("চিংড়িঘাটা", "Chingrighata"), ("হাজরা", "Hazra"),
    ("শ্যামবাজার", "Shyambazar"), ("উল্টোডাঙা", "Ultadanga"), ("পার্ক সার্কাস", "Park Circus"),
    ("সায়েন্স সিটি", "Science City"), ("খিদিরপুর", "Kidderpore"),
])
def test_skeleton_is_the_same_in_both_scripts(bn: str, en: str) -> None:
    assert skeleton(bn) == skeleton(en)


def test_fold_bn_merges_asr_spelling_variants() -> None:
    assert fold_bn("গড়িয়াহাট") == fold_bn("গরিয়াহাট")
    assert fold_bn("কালীঘাট") == fold_bn("কালিঘাট")
    assert fold_bn("হাঁটু") == fold_bn("হাটু")
    assert fold_bn("সেক্টর ৫") == "সেক্টর 5"


def test_aliases_point_at_real_landmark_ids(gaz: Gazetteer) -> None:
    ids = {p.id for p in gaz.places}
    assert set(ALIASES) <= ids


@pytest.mark.parametrize("text,pid", [
    ("গড়িয়াহাট মোড়ে হাঁটু জল, বাস আটকে আছে", "gariahat"),
    ("গরিয়াহাট মোরে জল জমেছে", "gariahat"),                 # ASR spelling
    ("Gariahat more e hatu jol, bus atke ache", "gariahat"),  # romanised
    ("Knee-deep water at Gariahat crossing", "gariahat"),     # English
    ("ধর্মতলায় মিছিল", "esplanade"),                          # everyday name
    ("ডালহৌসিতে যানজট", "bbd_bag"),
    ("যুবভারতীর সামনে ভিড়", "salt_lake_stadium"),
    ("শিয়ালদা স্টেশনের সামনে যানজট", "sealdah"),
    ("উল্টাডাঙ্গার কাছে গাছ পড়েছে", "ultadanga"),
    ("সেক্টর ফাইভে জ্যাম", "sector_v"),
    ("Sector 5 e jam", "sector_v"),
    ("হাওড়া ব্রিজে বাস খারাপ", "howrah_bridge"),
    ("হাওড়া স্টেশনের সামনে ভিড়", "howrah_station"),
    ("পার্ক সার্কাস সাত মাথার মোড়ে জল", "park_circus"),
    ("পার্ক স্ট্রিটে তার ছিঁড়ে পড়েছে", "park_street"),
    ("ঠনঠনিয়ায় কোমর জল", "thanthania"),
    ("Accident near Ruby crossing on the Bypass", "ruby"),
])
def test_match(gaz: Gazetteer, text: str, pid: str) -> None:
    m, cands = gaz.match(text)
    assert m is not None, (text, [(c.place.id, c.score) for c in cands])
    assert m.place.id == pid
    d = m.as_dict()
    assert set(d) >= {"id", "name_en", "name_bn", "lat", "lon", "match_score"}
    assert 0.8 <= d["match_score"] <= 1.0


@pytest.mark.parametrize("text", [
    "বৃষ্টি হচ্ছে, রাস্তায় জল",          # no place named
    "তার বাড়ি এখানে",
    "Heavy rain everywhere since morning",
])
def test_no_place_is_asserted_when_none_is_named(gaz: Gazetteer, text: str) -> None:
    m, _ = gaz.match(text)
    assert m is None


def test_candidates_are_offered_below_threshold(gaz: Gazetteer) -> None:
    m, cands = gaz.match("বরিয়াহাটে জল")  # one consonant off
    assert cands, "the officer gets candidates to pick from"
    assert cands[0].place.id == "gariahat" or m is None


def _write_city(tmp: Path, gazetteer: object) -> Path:
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "landmarks.json").write_text(json.dumps({"landmarks": [
        {"id": "gariahat", "kind": "junction", "lat": 22.519, "lon": 88.366, "en": "Gariahat crossing",
         "bn": "গড়িয়াহাট মোড়", "hi": "गड़ियाहाट क्रॉसिंग"}]}, ensure_ascii=False), encoding="utf-8")
    (tmp / "gazetteer.json").write_text(json.dumps(gazetteer, ensure_ascii=False), encoding="utf-8")
    return tmp


@pytest.mark.parametrize("doc", [
    {"entries": [{"id": "ps_jadavpur", "name_en": "Jadavpur Police Station", "name_bn": "যাদবপুর থানা",
                  "lat": 22.4986, "lon": 88.3713}]},
    [{"id": "ps_jadavpur", "en": "Jadavpur Police Station", "bn": "যাদবপুর থানা",
      "lat": 22.4986, "lon": 88.3713}],
    {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {
        "id": "ps_jadavpur", "name_en": "Jadavpur Police Station", "name_bn": "যাদবপুর থানা"},
        "geometry": {"type": "Point", "coordinates": [88.3713, 22.4986]}}]},
    {"police_stations": [{"id": "ps_jadavpur", "names": {"en": "Jadavpur Police Station",
                                                         "bn": "যাদবপুর থানা"},
                          "lat": 22.4986, "lng": 88.3713}]},
])
def test_gazetteer_json_shapes_are_read(tmp_path: Path, doc: object) -> None:
    g = load_gazetteer(_write_city(tmp_path / "c", doc))
    assert len(g) == 2
    m, _ = g.match("যাদবপুর থানার সামনে জল জমেছে")
    assert m is not None and m.place.id == "ps_jadavpur"
    assert m.place.source == "gazetteer"
    assert abs(m.place.lat - 22.4986) < 1e-6 and abs(m.place.lon - 88.3713) < 1e-6


def test_landmark_wins_over_gazetteer_with_the_same_id(tmp_path: Path) -> None:
    g = load_gazetteer(_write_city(tmp_path / "c", [
        {"id": "gariahat", "en": "Somewhere else", "bn": "অন্য জায়গা", "lat": 1, "lon": 1},
        {"id": "no_coords", "en": "Nowhere"}]))
    assert len(g) == 1
    assert g.by_id("gariahat").lat == pytest.approx(22.519)


def test_broken_gazetteer_is_ignored(tmp_path: Path) -> None:
    d = _write_city(tmp_path / "c", [])
    (d / "gazetteer.json").write_text("{not json", encoding="utf-8")
    assert len(load_gazetteer(d)) == 1


def test_a_split_name_is_not_taken_for_its_first_half(gaz: Gazetteer) -> None:
    """The ASR wrote "গড়িয়াহাট" as "গড়িয়া হাট"; with Garia in the gazetteer
    the first half alone matched Garia exactly. The longer name wins, and
    Garia said on its own is still Garia."""
    from speech_service.places import Place

    garia = Place("garia", "Garia", "গড়িয়া", 22.463, 88.39, source="gazetteer")
    g = Gazetteer([*gaz.places, garia])
    m, cands = g.match("গড়িয়া হাট মোড়ে হাঁটু জল বাস আটকে আছে")
    assert m is not None and m.place.id == "gariahat"
    assert "garia" in [c.place.id for c in cands]
    m2, _ = g.match("গড়িয়া স্টেশনের কাছে জল জমেছে")
    assert m2 is not None and m2.place.id == "garia"


def test_a_stray_word_does_not_promote_a_longer_name(gaz: Gazetteer) -> None:
    from speech_service.places import Place

    ps = Place("ps_sector_v", "Sector V Police Station", "সেক্টর ফাইভ থানা", 22.577, 88.43,
               kind="police_station", source="gazetteer")
    g = Gazetteer([*gaz.places, ps])
    m, _ = g.match("সেক্টর ফাইভ এ অফিস ছুটির পর গাড়ি নড়ছে না প্রচণ্ড যানজট")
    assert m is not None and m.place.id == "sector_v"
