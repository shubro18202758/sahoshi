"""The X19 gazetteer of Kolkata: format, places only (no field outside the list), the ODbL notice, the City Pack
(ids, order, spellings), the protect-set, the normaliser (Bengali and Devanagari), the longest-match index with
Bengali case endings, the path rules, and the generator (deterministic, --check, lint)."""

from __future__ import annotations

import copy
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from osint_common import ethics
from osint_geo import gazetteer as gz
from osint_geo import translit
from osint_geo.gazetteer import ENTRY_FIELDS, LICENCE, META_FIELDS, Gazetteer, load, norm

REPO = Path(__file__).resolve().parents[3]
GAZ_JSON = REPO / "scripts" / "data" / "osint_gazetteer.json"
NETWORK_JSON = REPO / "scripts" / "data" / "osm_network.json"
PACK_JSON = REPO / "cities" / "kolkata" / "gazetteer.json"
CITY_JSON = REPO / "cities" / "kolkata" / "city.json"
GENERATOR = REPO / "scripts" / "gen_osint_gazetteer.py"
#: the first pack place's gaz_id: 49 junctions and 65 road segments come first
FIRST_PLACE = 115


def _generator():
    spec = importlib.util.spec_from_file_location("gen_osint_gazetteer", GENERATOR)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def doc() -> dict:
    return json.loads(GAZ_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def pack() -> dict:
    return json.loads(PACK_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def gaz() -> Gazetteer:
    return load()


# ------------------------------------------------------------------------------------------------- X19 format
def test_x19_format(doc):
    assert set(doc) == {"meta", "entries"}
    assert set(doc["meta"]) == set(META_FIELDS)
    assert doc["meta"]["entries"] == len(doc["entries"]) == 277
    for e in doc["entries"]:
        assert list(e) == list(ENTRY_FIELDS), e.get("gaz_id")
        assert e["feature_type"] in gz.FEATURE_TYPES
        assert isinstance(e["surface_forms"], list) and all(isinstance(f, str) for f in e["surface_forms"])
    assert [e["gaz_id"] for e in doc["entries"]] == list(range(1, 278))
    counts = {t: sum(1 for e in doc["entries"] if e["feature_type"] == t) for t in gz.FEATURE_TYPES}
    assert counts == {"road": 65, "junction": 49, "neighbourhood": 72, "landmark": 64, "admin": 0, "poi": 27}
    assert "Kolkata" in doc["meta"]["source"]


def test_odbl_notice(doc, gaz):
    assert doc["meta"]["licence"] == LICENCE == "© OpenStreetMap contributors, ODbL 1.0"
    assert gaz.meta["licence"] == LICENCE
    assert "OpenStreetMap" in doc["meta"]["source"]


def test_ids_are_the_network_of_record_then_the_city_pack(doc, pack):
    net = json.loads(NETWORK_JSON.read_text(encoding="utf-8"))
    junctions = [e for e in doc["entries"] if e["feature_type"] == "junction"]
    roads = [e for e in doc["entries"] if e["feature_type"] == "road"]
    assert [e["gaz_id"] for e in junctions] == list(range(1, 50))
    assert [e["junction_id"] for e in junctions] == [j["junction_id"] for j in net["junctions"]]
    assert [e["canonical_name"] for e in junctions] == [j["name"] for j in net["junctions"]]
    assert [e["gaz_id"] for e in roads] == list(range(50, FIRST_PLACE))
    assert [e["segment_id"] for e in roads] == [s["segment_id"] for s in net["segments"]] == list(range(1001, 1066))
    assert [e["canonical_name"] for e in roads] == [s["road_name"] for s in net["segments"]]
    # the pack's places follow in pack order, so their gaz_ids stay stable while new places are appended
    places = [e for e in doc["entries"] if e["feature_type"] not in ("junction", "road")]
    assert [e["gaz_id"] for e in places] == list(range(FIRST_PLACE, FIRST_PLACE + len(pack["places"])))
    for e, p in zip(places, pack["places"], strict=True):
        assert e["canonical_name"] == p["en"], p["id"]
        assert e["feature_type"] == ("neighbourhood" if p["anchor"] == "area" else p["feature_type"]), p["id"]
        anchor = p["anchor"]
        want = (int(anchor[1:]) if anchor[0] == "J" else None, int(anchor[1:]) if anchor[0] == "S" else None)
        assert (e["junction_id"], e["segment_id"]) == want, p["id"]
        assert e["source"].startswith("city_pack."), p["id"]


@pytest.mark.parametrize(
    ("gaz_id", "pack_id"),
    [(115, "behala"), (118, "kasba"), (119, "garia"), (120, "ultadanga_area"), (121, "mukundapur"),
     (122, "park_circus_area"), (127, "amherst_street"), (128, "gariahat_area"), (161, "maidan"),
     (184, "thanthania"), (185, "sealdah"), (186, "airport"), (202, "medical_college"), (232, "bagbazar_pandal"),
     (263, "ps_park_street"), (277, "ps_beleghata")],
)
def test_the_pack_ids_other_streams_use_are_stable(doc, pack, gaz_id, pack_id):
    # a pack place's gaz_id is its position: existing places keep their ids and order, new ones are appended
    assert pack["places"][gaz_id - FIRST_PLACE]["id"] == pack_id
    assert doc["entries"][gaz_id - 1]["canonical_name"] == pack["places"][gaz_id - FIRST_PLACE]["en"]


def test_points_are_in_the_city(doc):
    bbox = json.loads(CITY_JSON.read_text(encoding="utf-8"))["bbox"]
    for e in doc["entries"]:
        assert bbox["west"] <= e["lon"] <= bbox["east"] and bbox["south"] <= e["lat"] <= bbox["north"], (
            e["canonical_name"])


def test_the_city_pack_rows(pack):
    assert pack["schema"] == "sahoshi.gazetteer/1" and pack["city"] == "kolkata"
    assert "OpenStreetMap" in pack["attribution"] and "ODbL" in pack["attribution"]
    ids = [p["id"] for p in pack["places"]]
    assert len(ids) == len(set(ids))
    for p in pack["places"]:
        assert p["en"].strip() and p["bn"].strip() and p["hi"].strip(), p["id"]
        assert translit.is_indic(p["bn"]) and translit.is_indic(p["hi"]), p["id"]
        assert re.fullmatch(r"area|snap|J\d+|S\d+", p["anchor"]), p["id"]
        assert 0.0 <= p["importance"] <= 1.0 and isinstance(p.get("low_lying"), bool), p["id"]
        # a hand row's point is approximate and says so; the others come from landmarks.json or the OSM extract
        assert p["source"] == "hand" or p["source"] == "landmarks.json" or p["source"].startswith("osm:"), p["id"]


def test_the_low_lying_spots_are_flagged(pack):
    low = {p["id"] for p in pack["places"] if p["low_lying"]}
    assert {"thanthania", "amherst_street", "park_circus_area", "kalighat_area", "behala", "kasba", "garia",
            "ultadanga_area", "mukundapur"} <= low


# ------------------------------------------------------------------------------------------------- places only
def test_places_only_no_person_key(doc):
    ethics.assert_no_person_keys(doc)
    for e in doc["entries"]:
        assert not any(ethics.is_forbidden_key(k) for k in e if k != "surface_forms")


@pytest.mark.parametrize("extra", ["victim", "author", "notes", "person_name", "reporter", "owner"])
def test_a_key_outside_the_x19_list_is_refused(doc, extra):
    bad = copy.deepcopy(doc)
    bad["entries"][5][extra] = "x"
    with pytest.raises(ValueError, match="outside the X19 field list"):
        Gazetteer.from_document(bad)


def test_a_meta_or_top_level_key_outside_the_list_is_refused(doc):
    bad = copy.deepcopy(doc)
    bad["meta"]["uploader"] = "x"
    with pytest.raises(ValueError, match="X19"):
        Gazetteer.from_document(bad)
    bad = copy.deepcopy(doc)
    bad["people"] = []
    with pytest.raises(ValueError, match="top-level"):
        Gazetteer.from_document(bad)


@pytest.mark.parametrize(
    "field,value",
    [
        ("gaz_id", True),
        ("gaz_id", 0),
        ("feature_type", "person"),
        ("lon", 200.0),
        ("lat", float("nan")),
        ("importance", 1.5),
        ("surface_forms", "gariahat"),
        ("surface_forms", [1, 2]),
        ("canonical_name", ""),
        ("canonical_name", "Gariahat\x00"),
        ("canonical_name", "Gariahat‮"),  # a bidi override: display spoofing
        ("lang_primary", "Bengali"),
        ("junction_id", -3),
    ],
)
def test_bad_values_are_refused(doc, field, value):
    bad = copy.deepcopy(doc)
    bad["entries"][0][field] = value
    with pytest.raises(ValueError):
        Gazetteer.from_document(bad)


def test_missing_fields_and_wrong_counts_are_refused(doc):
    bad = copy.deepcopy(doc)
    del bad["entries"][3]["importance"]
    with pytest.raises(ValueError, match="lacks"):
        Gazetteer.from_document(bad)
    bad = copy.deepcopy(doc)
    bad["meta"]["entries"] = 276
    with pytest.raises(ValueError, match="meta.entries"):
        Gazetteer.from_document(bad)
    bad = copy.deepcopy(doc)
    bad["entries"][1]["gaz_id"] = 1
    with pytest.raises(ValueError, match="duplicate"):
        Gazetteer.from_document(bad)
    bad = copy.deepcopy(doc)
    bad["entries"][60]["segment_id"] = None  # a road without its segment
    with pytest.raises(ValueError, match="segment_id"):
        Gazetteer.from_document(bad)
    bad = copy.deepcopy(doc)
    bad["entries"][10]["junction_id"] = None  # a junction without its id
    with pytest.raises(ValueError, match="junction_id"):
        Gazetteer.from_document(bad)


# ------------------------------------------------------------------------------------------------- protect-set
def test_protect_set_holds_every_canonical_name_and_form(doc, gaz):
    assert isinstance(gaz.protect_set, frozenset)
    for e in doc["entries"]:
        assert norm(e["canonical_name"]) in gaz.protect_set
        for f in e["surface_forms"]:
            assert f in gaz.protect_set
    for part in ("em bypass", "gariahat crossing", "gariahat", "park street", "red road", "thanthania", "sealdah",
                 "kasba", "kolkata police hq", "বেহালা", "গড়িয়াহাট মোড়", "बेहाला"):
        assert part in gaz.protect_set, part


def test_protect_set_never_holds_a_bare_person_name(gaz):
    # a sub-phrase of a place named after a person would protect that person's name: none is added
    for name in ("jawaharlal nehru", "shyama prasad mukherjee", "ashutosh mukherjee", "jagadish chandra bose",
                 "indira gandhi", "mother teresa", "khudiram bose", "karl marx", "surendra nath banerjee",
                 "kazi nazrul islam", "deshapran sashmal", "rani rashmoni", "rash behari", "rashbehari",
                 "harish mukherjee", "surya sen", "sarat bose", "radha gobinda kar", "santosh mitra",
                 "subhas chandra bose", "rabindranath", "vivekananda", "vidyasagar", "bidhan", "gandhi", "nehru",
                 "indira", "lenin"):
        assert name not in gaz.protect_set, name


# ------------------------------------------------------------------------------------------------- forms
def test_every_form_is_normal_matchable_and_not_generic(doc):
    for e in doc["entries"]:
        assert e["surface_forms"] == sorted(set(e["surface_forms"])), e["gaz_id"]
        for f in e["surface_forms"]:
            assert norm(f) == f, (e["gaz_id"], f)
            assert len(f) >= gz.MIN_FORM_CHARS
            assert not all(t in gz.GENERIC_STOPWORDS for t in f.split(" ")), (e["gaz_id"], f)


def test_every_pack_spelling_is_carried(doc, pack):
    gen = _generator()
    for p in pack["places"]:
        e = doc["entries"][FIRST_PLACE - 1 + pack["places"].index(p)]
        forms = set(e["surface_forms"])
        for raw in (p["en"], gen._base(p["en"]), p["bn"], p["hi"], *p.get("aka", []), *p.get("aka_bn", []),
                    *p.get("aka_hi", [])):
            n = norm(raw)
            if gen._good(n):
                assert n in forms, (p["id"], raw)


def test_no_bare_first_word_of_a_junction_name_is_its_alias(doc, gaz):
    # in Kolkata the first word of a junction's name is a surname ("Hazra"), a person's name ("Rashbehari"), a
    # company ("Exide") or an area ("Gariahat"): the generator adds none of them
    for e in doc["entries"]:
        if e["feature_type"] != "junction":
            continue
        words = norm(re.sub(r"\s*\(.*?\)\s*", " ", e["canonical_name"])).split(" ")
        if len(words) > 1:
            assert words[0] not in e["surface_forms"], (e["gaz_id"], words[0])
    for word in ("hazra", "rashbehari", "exide", "ruby", "mullickbazar", "deshapriya", "girish", "central"):
        assert all(gaz.by_id[g].feature_type != "junction" for g in gaz.lookup(word)), word
    # the junctions' own names still reach them
    for name, jid in (("hazra crossing", 18), ("rashbehari crossing", 20), ("exide crossing", 13),
                      ("ruby crossing", 29), ("ruby more", 29), ("mullickbazar crossing", 14)):
        assert [gaz.by_id[g].junction_id for g in gaz.lookup(name)] == [jid], name


@pytest.mark.parametrize(
    ("word", "gaz_id"),
    [
        ("gariahat", 128), ("গড়িয়াহাট", 128), ("गड़ियाहाट", 128), ("gariahaat", 128), ("kalighat", 117),
        ("কালীঘাট", 117), ("tollygunge", 116), ("tollyganj", 116), ("ultadanga", 120), ("উল্টোডাঙা", 120),
        ("park circus", 122), ("পার্ক সার্কাস", 122), ("sealdah", 185), ("shealdah", 185), ("শিয়ালদহ", 185),
        ("सियालदह", 185), ("shyambazar", 134), ("maniktala", 138), ("ballygunge", 130), ("kidderpore", 133),
        ("taratala", 144), ("behala", 115), ("lake town", 154), ("baguiati", 155), ("kestopur", 156),
        ("bagbazar", 135), ("howrah", 158),
    ],
)
def test_an_area_word_is_never_a_junction_alias(gaz, word, gaz_id):
    # F-HONEST OSINT-1: a bare area word reaches the area (or the station) only, in every script, never the junction
    # named after it ("Gariahat" alone is the neighbourhood; "Gariahat crossing" is junction 23)
    assert gaz.lookup(word) == (gaz_id,), word


def test_the_junctions_own_names_still_reach_them(gaz):
    for name, jid in (("gariahat crossing", 23), ("gariahat more", 23), ("গড়িয়াহাট মোড়", 23),
                      ("kalighat crossing", 19), ("tollygunge phari", 21), ("টালিগঞ্জ ফাঁড়ি", 21),
                      ("ultadanga crossing", 33), ("park circus crossing", 17), ("পার্ক সার্কাসের মোড়", 17),
                      ("sealdah crossing", 16), ("shyambazar five point crossing", 41), ("maniktala crossing", 42),
                      ("ballygunge phari", 24), ("kidderpore crossing", 25), ("behala chowrasta", 28),
                      ("lake town vip road", 34), ("baguiati vip road", 36), ("bagbazar rabindra sarani crossing", 47)):
        assert [gaz.by_id[g].junction_id for g in gaz.lookup(name)] == [jid], name


def test_the_lint_refuses_an_area_word_on_a_junction_and_a_person_phrase(doc):
    gen = _generator()
    assert gen.lint(doc) == []
    bad = copy.deepcopy(doc)
    junction = next(e for e in bad["entries"] if e["junction_id"] == 23 and e["feature_type"] == "junction")
    junction["surface_forms"] = sorted([*junction["surface_forms"], "gariahat"])
    assert any("junction form shared with a pack place: 'gariahat'" in p for p in gen.lint(bad))
    bad = copy.deepcopy(doc)
    for jid in (13, 18):
        j = next(e for e in bad["entries"] if e["junction_id"] == jid and e["feature_type"] == "junction")
        j["surface_forms"] = sorted([*j["surface_forms"], "hazra"])
    assert any("bare junction form shared with another junction: 'hazra'" in p for p in gen.lint(bad))
    # a multi-word phrase with no place-type word (a person's name) is never a form
    bad = copy.deepcopy(doc)
    road = next(e for e in bad["entries"] if e["segment_id"] == 1032 and e["feature_type"] == "road")
    road["surface_forms"] = sorted([*road["surface_forms"], "rash behari"])
    assert any("phrase without a place-type word: 'rash behari'" in p for p in gen.lint(bad))


def test_the_osm_names_along_a_segment(gaz):
    gen = _generator()
    assert {"bridge", "setu", "circle", "crossing"} <= gen.POINT_WORDS
    # a bridge or circle on the segment is point-like: an alias at any length
    assert [gaz.by_id[g].segment_id for g in gaz.lookup("bijon setu")] == [1034]
    assert [gaz.by_id[g].segment_id for g in gaz.lookup("parama circle")] == [1036]
    # a few metres of another road where it touches the segment is not its alias: Strand Road's 33 m on Howrah
    # Bridge (segment 1001) leaves "strand road" to the Strand Road segments
    strand = {gaz.by_id[g].segment_id for g in gaz.lookup("strand road")}
    assert 1001 not in strand and strand == {1004, 1005, 1006, 1061}
    # an OSM crossing named like a junction stays the junction's alone
    assert gaz.lookup("ruby crossing") == (29,)


def test_generator_lint_is_clean_and_phrases_are_places(doc):
    gen = _generator()
    assert gen.lint(doc) == []
    multi = {gen._phrase(f) for e in doc["entries"] for f in e["surface_forms"]} - {""}
    assert len([p for p in multi if " " in p]) > 300


def test_bengali_and_hindi_aliases(gaz, pack):
    assert gaz.lookup("বেহালা") == gaz.lookup("बेहाला") == gaz.lookup("behala") == (115,)
    assert 23 in gaz.lookup("গড়িয়াহাট মোড়")  # junction 23, from osm_network.json's name_bn
    # every pack place carries its Bengali and its Hindi name
    for i, p in enumerate(pack["places"]):
        assert FIRST_PLACE + i in gaz.lookup(p["bn"]) and FIRST_PLACE + i in gaz.lookup(p["hi"]), p["id"]
    # common Bengali words are never a place on their own
    for word in ("শহর", "রাস্তা", "মোড়", "থানা", "জল", "কলকাতা", "পুজো"):
        assert gaz.lookup(word) == (), word


def test_the_gated_forms_carry_their_script_spellings(gaz):
    # translit's tables give a gated Latin form its Bengali and Devanagari spellings (the resolver gates them all)
    for latin in ("maidan", "science city", "new market", "medical college", "new town", "salt lake", "garia",
                  "dum dum"):
        carried = [s for s in translit.script_aliases(latin) if gaz.lookup(s)]
        assert len(carried) >= 2 and all(gaz.lookup(s) == gaz.lookup(latin) for s in carried), latin
    assert translit.latin_variants("new town") == ("newtown",)
    assert translit.latin_variants("vip road") == ("v i p road", "vip rd")
    assert "behela" in translit.latin_variants("behala")


# ------------------------------------------------------------------------------------------------- normaliser
@pytest.mark.parametrize(
    "raw,want",
    [
        ("A.J.C. Bose Road", "a j c bose road"),
        ("  EM   Bypass ", "em bypass"),
        ("NH-12", "nh12"),
        ("NH 16", "nh16"),
        ("Diamond Harbour Road SH-1", "diamond harbour road sh1"),
        ("Rāsbihārī Avenue", "rasbihari avenue"),
        ("Tollygunge’s", "tollygunge s"),
        ("Sector-V, Salt Lake", "sector v salt lake"),
        ("Strand Road (Howrah Bridge–Babughat)", "strand road howrah bridge babughat"),
        ("গড়িয়াহাট মোড় (রাসবিহারী অ্যাভিনিউ - গড়িয়াহাট রোড)",
         "গড়িয়াহাট মোড় রাসবিহারী অ্যাভিনিউ গড়িয়াহাট রোড"),
        ("গড়িয়া‍হাট", "গড়িয়াহাট"),  # a zero-width joiner never splits a word
        # a precomposed nukta letter (ড় U+09DC, য় U+09DF) decomposes (NFKC): one form for both spellings
        ("গড়িয়াহাট", "গড়িয়াহাট"),
        ("বেহালায়", "বেহালায়"),
        ("हावड़ा ब्रिज", "हावड़ा ब्रिज"),
        ("ＥＭ　Ｂｙｐａｓｓ", "em bypass"),
        (None, ""),
    ],
)
def test_norm(raw, want):
    assert norm(raw) == want
    assert norm(norm(raw)) == norm(raw)


def test_translit_is_in_step_with_norm():
    for s in ("A.J.C. Bose Road", "গড়িয়াহাট মোড় (রাসবিহারী অ্যাভিনিউ)", "हावड़ा", "Park Circus"):
        assert translit._n(s) == norm(s)
    assert translit.to_latin("গড়িয়াহাট মোড়") == "gariahat crossing"
    assert translit.to_latin("পার্ক সার্কাস মোড়") == "park circus crossing"
    assert translit.to_latin("हाजरा मोड़") == "hazra crossing"
    assert translit.to_latin("অজানা জায়গা") is None  # a partial transliteration is never guessed
    assert len(translit.BN_LATIN_SEED) == 11


def test_bengali_case_endings_are_the_ethics_lexicon_s():
    # one list for the scanner and the redactor (osint_common.ethics.INDIC_SUFFIXES): a lockstep
    assert translit.BN_SUFFIXES == ethics.INDIC_SUFFIXES
    assert list(translit.BN_SUFFIXES) == sorted(translit.BN_SUFFIXES, key=len, reverse=True)
    assert not any("઀" <= ch <= "૿" for s in translit.BN_SUFFIXES for ch in s)  # Bengali endings only


# ------------------------------------------------------------------------------------------------- longest match
def test_longest_match_prefers_the_longer_form(gaz):
    hits = gaz.match("Crash on Rash Behari Avenue Connector")
    assert [h.form for h in hits] == ["rash behari avenue connector"]
    hits = gaz.match("Crash on Gariahat Road near Rash Behari Avenue")
    assert sorted((h.start, h.form) for h in hits) == [(2, "gariahat road"), (5, "rash behari avenue")]
    # the selection order is the PoC's: longer covered text first
    assert [h.form for h in hits] == ["rash behari avenue", "gariahat road"]


def test_every_occurrence_is_a_mention(gaz):
    hits = gaz.match("Gariahat crossing ... Gariahat crossing ... gariahat crossing")
    assert [h.form for h in hits] == ["gariahat crossing"] * 3


@pytest.mark.parametrize(
    ("text", "forms"),
    [
        ("বেহালার রাস্তাতে কসবায়", ["বেহালা", "কসবা"]),  # -র (of Behala), -তে (on), -য় (in Kasba)
        ("টালিগঞ্জের উল্টোডাঙাতেই শিয়ালদায়", ["টালিগঞ্জ", "উল্টোডাঙা", "শিয়ালদা"]),  # -ের, -তেই, -য়
        ("গড়িয়াহাটের দোকানে", ["গড়িয়াহাট"]),  # a word the junction alias "গড়িয়াহাটের মোড়" also carries
        ("শহরের রাস্তাতে", []),  # "of the city", "on the road": no place stem
        ("কলকাতায়", []),  # the city's name is no place (it opens the context gate instead)
    ],
)
def test_bengali_case_endings_are_read(gaz, text, forms):
    assert [h.form for h in sorted(gaz.match(text))] == forms


def test_an_inflected_alias_word_stays_whole_only_inside_its_form(gaz):
    assert gaz.tokens("গড়িয়াহাটের মোড়ে") == ["গড়িয়াহাটের", "মোড়"]  # the junction alias "গড়িয়াহাটের মোড়"
    assert gaz.tokens("গড়িয়াহাটের দোকানে")[0] == "গড়িয়াহাট"
    # both spellings of "য়" (one code point, or "য" + nukta) read the same
    assert gaz.tokens("বেহালায়") == gaz.tokens("বেহালায়") == ["বেহালা"]


def test_tokens_never_match_inside_a_word(gaz):
    assert gaz.match("Behalapur") == [] and gaz.match("Kasbapara") == [] and gaz.match("Gariahatwala") == []


# ------------------------------------------------------------------------------------------------- path rules
def test_path_rules_and_cache(tmp_path, monkeypatch):
    assert load() is load() and load().path is not None and load().path.name == "osint_gazetteer.json"
    custom = tmp_path / "g.json"
    custom.write_text(GAZ_JSON.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setenv(gz.GAZETTEER_ENV, str(custom))
    assert load().path == custom
    monkeypatch.setenv(gz.GAZETTEER_ENV, str(tmp_path / "missing.json"))
    with pytest.raises(FileNotFoundError):
        load()
    with pytest.raises(FileNotFoundError):
        load(tmp_path / "nope.json")
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"meta": {}, "entries": [{"gaz_id": 1}]}), encoding="utf-8")
    with pytest.raises(ValueError):
        load(bad)


def test_entries_read_as_objects_and_mappings(gaz):
    e = gaz.by_id[184]
    assert e.canonical_name == e["canonical_name"] == "Thanthania"
    assert dict(e)["gaz_id"] == 184 and e.get("nope", 1) == 1 and e.segment_id == 1058
    assert json.loads(json.dumps(e.as_dict()))["surface_forms"] == list(e.surface_forms)
    with pytest.raises(KeyError):
        e["victim"]


# ------------------------------------------------------------------------------------------------- generator
def test_generator_is_deterministic_and_matches_the_committed_file():
    gen = _generator()
    a, b = gen.render(gen.build()), gen.render(gen.build())
    assert a == b == GAZ_JSON.read_text(encoding="utf-8")


def test_generator_check_exit_codes(tmp_path):
    ok = subprocess.run([sys.executable, str(GENERATOR), "--check"], capture_output=True, text=True, cwd=REPO)
    assert ok.returncode == 0, ok.stderr
    stale = tmp_path / "stale.json"
    stale.write_text(GAZ_JSON.read_text(encoding="utf-8").replace('"gariahat"', '"gariahet"', 1), encoding="utf-8")
    bad = subprocess.run([sys.executable, str(GENERATOR), "--check", "--out", str(stale)], capture_output=True,
                         text=True, cwd=REPO)
    assert bad.returncode == 1 and "DIFFERS" in bad.stderr


def test_overpass_review_is_offline_and_writes_nothing(doc):
    gen = _generator()
    response = {"elements": [
        {"type": "node", "lat": 22.48, "lon": 88.33, "tags": {"place": "suburb", "name": "Haridevpur"}},
        {"type": "node", "lat": 22.52, "lon": 88.36, "tags": {"place": "suburb", "name": "Gariahat"}},
        {"type": "node", "lat": 22.5, "lon": 88.3, "tags": {"place": "neighbourhood"}},
    ]}
    lines = gen.overpass_review(response, doc)
    assert len(lines) == 1 and "Haridevpur" in lines[0]
    query = gen.overpass_query()
    assert "suburb|neighbourhood|quarter" in query and "22.45,88.2,22.7,88.5" in query


def test_every_junction_keeps_its_bengali_name_unless_a_pack_place_carries_it(doc):
    # F-HONEST OSINT-1: "শিয়ালদহ" alone is the station, "টালিগঞ্জ" the neighbourhood, never the junction pin
    net = json.loads(NETWORK_JSON.read_text(encoding="utf-8"))
    forms = {e["junction_id"]: set(e["surface_forms"]) for e in doc["entries"] if e["feature_type"] == "junction"}
    place_forms = {f for e in doc["entries"] if e["feature_type"] not in ("junction", "road")
                   for f in e["surface_forms"]}
    dropped = []
    for j in net["junctions"]:
        bn = norm(j["name_bn"])
        if bn in forms[j["junction_id"]]:
            continue
        assert bn in place_forms, j["junction_id"]
        dropped.append(j["junction_id"])
    assert dropped == [16, 21, 25, 33]


def test_generator_check_needs_the_standard_library_only():
    # osint_geo.gazetteer, translit and geom import nothing outside the stdlib: --check runs on any Python 3.12
    code = (
        "import runpy, sys\n"
        "for m in ('numpy', 'pyproj', 'shapely', 'pydantic'): sys.modules[m] = None\n"
        f"sys.argv = [{str(GENERATOR)!r}, '--check']\n"
        f"runpy.run_path({str(GENERATOR)!r}, run_name='__main__')\n"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, r.stderr
    assert "gazetteer OK" in r.stdout


def test_no_form_reads_as_a_person(doc):
    for e in doc["entries"]:
        for text in (e["canonical_name"], *e["surface_forms"]):
            assert ethics.find_pii(text) == [], (e["gaz_id"], text)


def test_the_seed_notice_credits_the_gazetteer():
    # F-DEPLOY D-16: the gazetteer carries OSM-derived names and points, so it sits in the seed NOTICE's ODbL table
    notice = (REPO / "services" / "corridor-store" / "seed" / "NOTICE.md").read_text(encoding="utf-8")
    rows = [line for line in notice.splitlines() if line.startswith("| `scripts/data/osint_gazetteer.json`")]
    assert len(rows) == 1 and "ODbL" in rows[0]
