"""``resolve_text`` for ``GET /osint/gazetteer/resolve?q=`` (C-T): ranked, read-only gazetteer lookups of Kolkata
places, in English, Bengali and Hindi."""

from __future__ import annotations

import pytest

from osint_geo.resolver import resolve_text

KEYS = {"gaz_id", "canonical_name", "feature_type", "lon", "lat", "segment_id", "junction_id", "confidence", "method"}
EM_BYPASS = {1035, 1036, 1037, 1038}


def test_the_ct_candidate_shape():
    out = resolve_text("Thanthania")
    assert out and all(set(c) == KEYS for c in out)
    top = out[0]
    assert top["gaz_id"] == 184 and top["canonical_name"] == "Thanthania"
    # a low-lying spot pre-linked to its street (Bidhan Sarani, segment 1058)
    assert top["feature_type"] == "landmark" and top["segment_id"] == 1058 and top["junction_id"] is None
    assert top["method"] == "gazetteer_exact" and 0.0 <= top["confidence"] <= 1.0


def test_junctions_roads_and_grammar():
    assert resolve_text("gariahat crossing")[0]["junction_id"] == 23
    assert resolve_text("গড়িয়াহাট মোড়")[0]["junction_id"] == 23
    em = resolve_text("EM Bypass", limit=10)
    assert {c["segment_id"] for c in em} == EM_BYPASS
    assert all(c["feature_type"] == "road" for c in em)
    top = resolve_text("Hazra mor")[0]
    assert top["junction_id"] == 18 and top["method"] == "grammar"


def test_ranked_best_first_and_only_the_top_has_a_margin():
    out = resolve_text("Ruby crossing, Kasba", limit=5)
    assert [c["feature_type"] for c in out[:2]] == ["junction", "neighbourhood"]
    assert out[0]["junction_id"] == 29 and out[1]["canonical_name"] == "Kasba"
    assert out[0]["confidence"] > out[1]["confidence"]
    # F-HONEST OSINT-1: the bare area word is the neighbourhood alone, never the Gariahat crossing junction
    bare = resolve_text("gariahat", limit=5)
    assert [c["feature_type"] for c in bare] == ["neighbourhood"] and bare[0]["segment_id"] is None
    assert bare[0]["junction_id"] is None


def test_fuzzy_multi_word_only():
    fz = resolve_text("Eden Gardns")
    assert fz and fz[0]["gaz_id"] == 211 and fz[0]["method"] == "gazetteer_fuzzy"
    exact = resolve_text("Eden Gardens")
    assert fz[0]["confidence"] < exact[0]["confidence"]


@pytest.mark.parametrize(
    "q", ["india", "India", "road", "the", "", "zz", "Kolkata", "কলকাতা", "gariah", "Indra", "more", "মোড়", "setu"]
)
def test_no_guess(q):
    assert resolve_text(q) == []


def test_limit_and_query_bounds():
    assert len(resolve_text("em bypass", limit=3)) == 3
    assert resolve_text("em bypass", limit=0) == [] and resolve_text("em bypass", limit=-5) == []
    assert len(resolve_text("em bypass", limit=10_000)) <= 50
    assert resolve_text("x" * 5000) == []


def test_an_operator_query_is_about_the_city():
    # the context gate is open for an operator's lookup: these resolve here although a national outlet's text
    # naming no Kolkata word would not
    assert resolve_text("maidan")[0]["canonical_name"] == "Maidan"
    assert resolve_text("medical college")[0]["canonical_name"] == "Kolkata Medical College"
    assert resolve_text("science city")[0]["junction_id"] == 30
    assert resolve_text("garia")[0]["canonical_name"] == "Garia"
    assert {c["feature_type"] for c in resolve_text("park street", limit=10)} == {"road"}
    assert resolve_text("airport") == []  # never the airport junctions by the common word
    assert resolve_text("kolkata airport")[0]["canonical_name"] == "Kolkata Airport"


@pytest.mark.parametrize(
    "q", ["Rash Behari Avenue", "Rashbehari Avenue", "Rash Behari Ave", "রাসবিহারী অ্যাভিনিউ", "रासबिहारी एवेन्यू"]
)
def test_rash_behari_avenue_by_its_usual_spellings(q):
    out = resolve_text(q, limit=10)
    assert {c["segment_id"] for c in out} == {1032, 1033, 1034}
    assert {c["feature_type"] for c in out} == {"road"}


@pytest.mark.parametrize("q", ["Sealdah", "Shealdah", "শিয়ালদহ", "শিয়ালদা", "सियालदह", "Sealdah stn"])
def test_sealdah_by_its_usual_spellings_is_the_station_never_the_junction(q):
    # F-HONEST OSINT-1: the bare name is the station (a landmark), the junction only by "Sealdah crossing"
    out = resolve_text(q)
    assert [c["canonical_name"] for c in out] == ["Sealdah Station"]
    assert out[0]["junction_id"] is None
    assert resolve_text("Sealdah crossing")[0]["junction_id"] == 16


def test_read_only_and_deterministic():
    a = resolve_text("Lalbazar")
    b = resolve_text("Lalbazar")
    assert a == b and a[0]["canonical_name"] == "Lalbazar (Kolkata Police HQ)"
    a[0]["canonical_name"] = "changed"
    assert resolve_text("Lalbazar")[0]["canonical_name"] == "Lalbazar (Kolkata Police HQ)"
