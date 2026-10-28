"""The regex place grammar: relational, feature and PIN spans, clause boundaries, and the rewrite hits (Kolkata's
place words: "more"/"মোড়" for a crossing, "setu" for a bridge, "rd", "st", "thana"/"ps")."""

from __future__ import annotations

from osint_geo.gazetteer import load
from osint_geo.grammar import PIN_RE, SYNONYMS, feature_hits, find_spans, lookup_keys, pin_codes
from osint_geo.resolver import SENTENCE_BREAK


def _spans(text: str, kind: str):
    return [s for s in find_spans(text) if s.kind == kind]


def test_relational_spans():
    rel = _spans("Accident near Ruby Hospital on Tuesday; jam opp. New Market", "relational")
    assert [s.head for s in rel] == ["ruby hospital", "new market"]
    assert rel[0].surface == "Ruby Hospital" and rel[0].keys == ("ruby hospital",)


def test_a_relational_span_never_crosses_a_clause():
    rel = _spans("Seen near Gariahat - The Daily Example", "relational")
    assert [s.head for s in rel] == ["gariahat"]
    rel = _spans("He was near. Behala was quiet", "relational")
    assert rel == []


def test_abbreviations_keep_the_clause():
    # the initials' full stops keep the clause (a relational name is four words at most)
    rel = _spans("Crash near A.J.C. Bose Road flyover", "relational")
    assert rel and rel[0].head == "a j c bose"
    rel = _spans("Jam near Dr. Suresh Sarkar Road", "relational")
    assert rel and rel[0].head == "dr suresh sarkar road"


def test_feature_spans_carry_every_rewrite():
    feat = _spans("Car fire near Gariahat more", "feature")
    assert len(feat) == 1
    span = feat[0]
    assert span.head == "gariahat" and span.feature == "crossing"
    assert "gariahat crossing" in span.keys and "gariahat more" in span.keys
    feat = _spans("Shops shut at Bijon setu and on Park St.", "feature")
    keys = [k for s in feat for k in s.keys]
    assert "bijon bridge" in keys and "park street" in keys
    feat = _spans("Complaint lodged at Tollygunge thana", "feature")
    assert feat and "tollygunge police station" in feat[0].keys


def test_kolkata_place_words_are_synonyms():
    for word, generic in (("more", "crossing"), ("mor", "crossing"), ("setu", "bridge"), ("rd", "road"),
                          ("st", "street"), ("ave", "avenue"), ("thana", "police station"), ("ps", "police station"),
                          ("মোড়", "crossing"), ("সেতু", "bridge"), ("থানা", "police station"), ("मोड़", "crossing"),
                          ("थाना", "police station")):
        assert generic in SYNONYMS[tuple(word.split(" "))], word


def test_feature_heads_stop_at_cue_words():
    feat = _spans("traffic near gariahat more", "feature")
    assert feat and all("near" not in k for k in feat[0].keys)


def test_bengali_feature_span_is_transliterated():
    feat = _spans("রুবি মোড় থেকে বাস ঘুরিয়ে দেওয়া হয়েছে", "feature")
    assert feat and "ruby crossing" in feat[0].keys and "রুবি মোড়" in feat[0].keys
    feat = _spans("पार्क सर्कस मोड़ पर जाम", "feature")
    assert feat and "park circus crossing" in feat[0].keys


def test_lookup_keys():
    assert lookup_keys("Gariahat", "more") == ("gariahat more", "gariahat crossing")
    assert lookup_keys("Ultadanga", "fly over") == ("ultadanga fly over", "ultadanga flyover")
    assert lookup_keys("Bijon", "setu") == ("bijon setu", "bijon bridge")
    assert lookup_keys("রুবি", "মোড়") == ("রুবি মোড়", "রুবি crossing", "ruby মোড়", "ruby crossing")
    assert lookup_keys("", "crossing") == ()


def test_pin_codes():
    assert pin_codes("Water main burst, Ballygunge 700019. Call 1800-700019-99") == ["700019"]
    assert pin_codes("Kolkata-700016, or Kolkata 700 091") == ["700016", "700091"]
    assert pin_codes("ref 7000199 or 17000 19 or 700209") == []
    assert PIN_RE.fullmatch("700156") is not None
    # a Howrah PIN (711xxx) or another city's PIN is not a Kolkata PIN
    assert PIN_RE.fullmatch("711101") is None and PIN_RE.fullmatch("380009") is None
    pins = _spans("near the school, 700007.", "pin")
    assert [p.head for p in pins] == ["700007"]


def test_feature_hits_rewrite_against_the_index():
    gaz = load()
    toks = gaz.tokens("jam at hazra mor and park circus xing")
    hits = feature_hits(toks, gaz)
    assert {h.form for h in hits} == {"hazra crossing", "park circus crossing"}
    assert all(h.via == "grammar" for h in hits)
    hazra = next(h for h in hits if h.form == "hazra crossing")
    assert toks[hazra.start : hazra.end] == ["hazra", "mor"]


def test_feature_hits_read_bengali_case_endings():
    gaz = load()
    # "রুবি মোড়ের" (of Ruby crossing): the scanner reads the stem "মোড়", the rewrite the junction's Latin form
    toks = gaz.tokens("রুবি মোড়ের কাছে দুর্ঘটনা")
    assert toks[:2] == ["রুবি", "মোড়"]
    assert [h.form for h in feature_hits(toks, gaz)] == ["ruby crossing"]


def test_feature_hits_never_cross_a_sentence_break():
    # the resolver puts SENTENCE_BREAK between sentences; a head transliterated across it ("গড়িয়াহাট ." → "gariahat")
    # would make "গড়িয়াহাটে। মোড়ের ..." the crossing
    gaz = load()
    toks = [*gaz.tokens("আগুন লাগল গড়িয়াহাটে"), SENTENCE_BREAK, *gaz.tokens("মোড়ের কাছে ভিড়")]
    assert feature_hits(toks, gaz) == []
    toks = [*gaz.tokens("fire at gariahat"), SENTENCE_BREAK, *gaz.tokens("more shops shut")]
    assert feature_hits(toks, gaz) == []


def test_feature_hits_need_a_real_form():
    gaz = load()
    assert feature_hits(gaz.tokens("the old gate"), gaz) == []
    assert feature_hits(gaz.tokens("unknown place more"), gaz) == []


def test_no_spans_in_plain_text():
    assert find_spans("") == [] and find_spans("nothing here at all") == []
