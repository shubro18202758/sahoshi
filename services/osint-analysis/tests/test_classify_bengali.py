"""classify() on Bengali and Hindi text, as it reaches the classifier: AFTER the ingress redaction.

Every headline here is synthetic (written for this file; no real person's name). Each is classified twice: as
written, and as ingress leaves it, where every Bengali or Devanagari word that is neither a gazetteer place nor an
ordinary word of ``osint_common.ethics.INDIC_COMMON_WORDS`` is ``[WITHHELD]`` (no Indic NER runs at parse, so an
unknown word may be a name). :func:`redact` applies exactly the spans ingress applies. The class must be the same
both ways: every cue word the lexicon relies on survives the redaction (a test below pins that too).
"""

from __future__ import annotations

import random
import unicodedata

import pytest

from analysis_fixtures import make_signal
from osint_common import ethics, kinds
from osint_analysis import classify as C
from osint_analysis.fusion import content_tokens

#: The token ingress writes for a withheld Indic word or run of words (``osint_ingress.connectors._redact``).
WITHHELD = "[WITHHELD]"


def redact(text: str) -> str:
    """The text as ingress leaves it: each run of unreadable Indic words becomes ``[WITHHELD]``."""
    out = text
    for span in reversed(ethics.unredactable_spans(text)):
        out = out[: span.start] + WITHHELD + out[span.end :]
    return out


def bn(title: str, **kw):
    """A Bengali report from a fictional outlet's own feed (``news_rss``)."""
    sig = make_signal("news_rss", title=title, publisher=kw.pop("publisher", "news-bn-a.example"), **kw)
    return sig.model_copy(update={"language": "bn"})


def both(title: str):
    """The classification of a headline as written and as redacted."""
    return C.classify(bn(title)), C.classify(bn(redact(title)))


#: (headline, class, subtype): one or more real-style headlines per class.
HEADLINES = [
    # waterlogging: জল জমা / জমেছে / জলমগ্ন / জলবন্দি / হাঁটুজল / কোমর সমান জল / জল থইথই / ভারী বৃষ্টি
    ("ঠনঠনিয়ায় বিধান সরণিতে জল জমে যান চলাচল ব্যাহত", "urban_flooding", "waterlogging"),
    ("টানা বৃষ্টিতে জলমগ্ন বেহালা, জলবন্দি বহু পরিবার", "urban_flooding", "waterlogging"),
    ("উল্টোডাঙায় হাঁটুজল, ভোগান্তি নিত্যযাত্রীদের", "urban_flooding", "waterlogging"),
    ("জোয়ারের জন্য নিকাশি আটকে, পার্ক সার্কাসে জল জমেছে", "urban_flooding", "waterlogging"),
    ("ভারী বৃষ্টিতে কলেজ স্ট্রিটে কোমর সমান জল", "urban_flooding", "waterlogging"),
    ("মুষলধারে বৃষ্টি, শহরের একাধিক রাস্তায় জল থইথই", "urban_flooding", "waterlogging"),
    ("ঠনঠনিয়ায় জলযন্ত্রণা, নাকাল পথচারীরা", "urban_flooding", "waterlogging"),
    # road accidents: দুর্ঘটনা, and with a vehicle in the clause ধাক্কা / সংঘর্ষ / উল্টে / পিষে / চাপা
    ("ইএম বাইপাসে কসবার কাছে লরির ধাক্কায় তিনটি গাড়ি ক্ষতিগ্রস্ত, আহত তিন", "road_accident", "collision"),
    ("গড়িয়াহাট মোড়ে বাস ও অটোর মুখোমুখি সংঘর্ষ", "road_accident", "collision"),
    ("শিয়ালদহের কাছে বাস উল্টে আহত ১২", "road_accident", "collision"),
    ("লরির চাকায় পিষে মৃত্যু সাইকেল আরোহীর", "road_accident", "collision"),
    ("রুবি মোড়ে পথ দুর্ঘটনায় আহত দুই", "road_accident", "collision"),
    ("বেপরোয়া বাসের চাপায় মৃত্যু পথচারীর", "road_accident", "collision"),
    # a clash between groups (no vehicle), a mob beating after a crash (the conflict row comes first, as in English)
    ("দুই গোষ্ঠীর সংঘর্ষে উত্তেজনা, এলাকায় পুলিশ মোতায়েন", "public_conflict", "affray"),
    ("দুর্ঘটনার পর চালককে গণধোলাই, ইএম বাইপাসে উত্তেজনা", "public_conflict", "affray"),
    ("পার্কিং নিয়ে বচসা থেকে হাতাহাতি", "public_conflict", "affray"),
    ("চালকের সঙ্গে যাত্রীদের সংঘর্ষ", "public_conflict", "affray"),  # a driver is not a vehicle
    # fire: আগুন / অগ্নিকাণ্ড / দমকল, and a fire accident whose first word ingress withholds
    ("বড়বাজারে গুদামে ভয়াবহ অগ্নিকাণ্ড, ঘটনাস্থলে দমকলের ১৫টি ইঞ্জিন", "fire", "structure_fire"),
    ("বাগবাজারে বহুতলে আগুন, আতঙ্ক এলাকায়", "fire", "structure_fire"),
    ("অগ্নি দুর্ঘটনা বড়বাজারে, দমকলের দশটি ইঞ্জিন ঘটনাস্থলে", "fire", "structure_fire"),
    # building collapse, road cave-in
    ("পুরনো বাড়ির একাংশ ভেঙে পড়ল বউবাজারে, আহত দুই", "infra_failure", "collapse"),
    ("তারাতলায় রাস্তায় ধস, যান চলাচল ঘুরপথে", "infra_failure", "collapse"),
    ("বাড়ির ছাদের চাঙড় ভেঙে আহত বৃদ্ধা", "infra_failure", "collapse"),
    # a fallen tree, a live wire
    ("ঝড়ে গাছ উপড়ে পড়ল রাসবিহারী অ্যাভিনিউতে, যান চলাচল বন্ধ", "hazard", "fallen_tree"),
    ("কালবৈশাখীর দাপটে শহরে একাধিক গাছ ভেঙে পড়ল", "hazard", "fallen_tree"),
    ("আমহার্স্ট স্ট্রিটে তার ছিঁড়ে রাস্তায়, আতঙ্ক", "hazard", "live_wire"),
    ("বাতিস্তম্ভে বিদ্যুৎস্পৃষ্ট হয়ে মৃত্যু পথচারীর", "hazard", "live_wire"),
    # a rally, a Puja crowd, a book fair
    ("ধর্মতলায় সমাবেশ, পুলিশের কড়া নজরদারি", "public_gathering", "mass_gathering"),
    ("অষ্টমীর রাতে প্যান্ডেলে উপচে পড়া ভিড়", "public_gathering", "mass_gathering"),
    ("বইমেলায় জনসমুদ্র, বাড়তি বাস", "public_gathering", "mass_gathering"),
    ("ভিড়ের চাপে পিষে আহত তিন", "public_gathering", "mass_gathering"),  # a crowd crush is no road accident
    # a procession (the situation on the road, whoever marches), an immersion, the Puja carnival
    ("এসপ্ল্যানেডে মিছিলের জেরে যানজট", "procession", "procession"),
    ("বাবুঘাটে প্রতিমা বিসর্জন ঘিরে কড়া নিরাপত্তা", "procession", "procession"),
    ("রেড রোডে পুজো কার্নিভাল, একাধিক রাস্তা বন্ধ", "procession", "procession"),
    # a road or rail blockade, a bandh (written with a visible hasant)
    ("দাবি আদায়ে পথ অবরোধ, যানজট", "unrest", "protest"),
    ("শিয়ালদহে রেল অবরোধ, ব্যাহত ট্রেন চলাচল", "unrest", "protest"),
    ("সারাদিন বন্‌ধে শুনশান শহর", "unrest", "protest"),
    # a closure, metro or repair work, a detour
    ("মেট্রোর কাজের জন্য মহাত্মা গান্ধী রোড বন্ধ থাকবে", "road_closure", "closure"),
    ("সেতু মেরামতির কাজে মাঝেরহাটে যান নিয়ন্ত্রণ", "road_closure", "closure"),
    ("উড়ালপুল বন্ধ, যান চলাচল ঘুরপথে", "road_closure", "closure"),
    # cyclone, lightning, a depression and stormy wind
    ("ঘূর্ণিঝড়ের সতর্কতা, উপকূলে প্রবল বৃষ্টির পূর্বাভাস", "weather_hazard", "storm"),
    ("বজ্রপাতে মৃত্যু দুই কৃষকের", "weather_hazard", "storm"),
    ("বঙ্গোপসাগরে নিম্নচাপ, ঝোড়ো হাওয়ার সম্ভাবনা", "weather_hazard", "storm"),
    # reported crime: a dacoity, a snatching, a robbery at gunpoint (a situation for response, never crime_incident)
    ("গড়িয়াহাটে সোনার দোকানে ডাকাতি", "reported_crime", "daylight_robbery"),
    ("সল্টলেকে মহিলার হার ছিনতাই", "reported_crime", "daylight_robbery"),
    ("বন্দুক দেখিয়ে এটিএম লুট", "reported_crime", "daylight_robbery"),
]

#: Headlines whose cue word is used another way: never the class that word would suggest.
NEGATIVES = [
    ("পার্ক সার্কাসের মোড়ে যানজট", "general_news"),  # a jam alone is a consequence, read from the traffic feeds
    ("শেয়ার বাজারে বড় ধাক্কা", "general_news"),  # a setback
    ("দলের হার, বড় ধাক্কা", "general_news"),
    ("বাজারে আগুন দাম সবজির", "general_news"),  # prices on fire
    ("পেঁয়াজের দামে আগুন", "general_news"),
    ("আগুন ঝরানো বোলিং, ম্যাচ জিতল দল", "general_news"),  # a fiery spell
    ("বিধানসভায় ঝড় তুলল বিরোধীরা", "general_news"),  # raised a storm
    ("সমালোচনার ঝড় সোশ্যাল মিডিয়ায়", "general_news"),  # a storm of criticism
    ("রানের ঝড় ইডেনে", "general_news"),  # a storm of runs
    ("জমা জলে মশার লার্ভা, ডেঙ্গি নিয়ে সতর্কতা", "general_news"),  # a dengue notice
    ("জল জমা রুখতে নতুন পাম্প বসাল পুরসভা", "general_news"),  # a plan to prevent it
    ("এবার পুজোয় জল জমেনি শহরে", "general_news"),  # did not collect
    ("ভারী বৃষ্টির সম্ভাবনা নেই আজ", "general_news"),  # not likely
    ("বেআইনি বাড়ি ভেঙে ফেলল পুরসভা", "general_news"),  # a demolition
    ("ভোট লুটের অভিযোগ", "general_news"),  # an electoral claim, never a robbery situation
    ("নিয়ম বিসর্জন দিয়ে নির্মাণ", "general_news"),  # rules abandoned
    ("মেট্রোয় আজ ভিড় কম", "general_news"),  # a thin crowd
    ("কাজলের দাম বাড়ল", "general_news"),  # "জল" is never read inside "কাজল"
    ("রাস্তা বন্ধ নয়, চলছে যান", "general_news"),
    ("কলকাতায় আজ আবহাওয়া মনোরম", "general_news"),
    ("পুরসভার নতুন অ্যাপ চালু", "general_news"),
]

HINDI = [
    ("कोलकाता में जलभराव, कई सड़कें बंद", "urban_flooding"),
    ("ट्रक की टक्कर से बाइक सवार की मौत", "road_accident"),
    ("गोदाम में भीषण आग, दमकल मौके पर", "fire"),
    ("आंधी से पेड़ गिरा, यातायात ठप", "hazard"),
    ("चक्रवात की चेतावनी", "weather_hazard"),
    ("धर्मतला में रैली, भारी भीड़", "public_gathering"),
    ("जुलूस के कारण जाम", "procession"),
    ("धरना प्रदर्शन से रास्ता बंद", "unrest"),
    ("चुनाव में कड़ी टक्कर", "general_news"),  # a close contest
    ("कीमतों में आग", "general_news"),  # prices on fire
]


@pytest.mark.parametrize(("title", "event_class", "subtype"), HEADLINES)
def test_bengali_headlines_classify_as_written_and_after_redaction(title, event_class, subtype):
    raw, redacted = both(title)
    for got in (raw, redacted):
        assert (got.event_class, got.subtype) == (event_class, subtype), (title, redact(title), got.matched_terms)
        assert got.matched_terms and all(len(t) <= 64 for t in got.matched_terms)
        assert got.sahoshi_event_kind not in C.FORBIDDEN_OSINT_KINDS


def test_the_table_really_meets_the_redaction():
    # most headlines lose some words at ingress, and still classify (the test above)
    withheld = [t for t, _, _ in HEADLINES if WITHHELD in redact(t)]
    assert len(withheld) >= len(HEADLINES) // 3
    assert {cls for _, cls, _ in HEADLINES} == kinds.EVENT_CLASSES  # every event class has Bengali cues


@pytest.mark.parametrize(("title", "event_class"), NEGATIVES)
def test_bengali_precision_guards(title, event_class):
    raw, redacted = both(title)
    assert raw.event_class == event_class, (title, raw.matched_terms)
    assert redacted.event_class == event_class, (redact(title), redacted.matched_terms)


@pytest.mark.parametrize(("title", "event_class"), HINDI)
def test_hindi_headlines(title, event_class):
    raw, redacted = both(title)
    assert raw.event_class == event_class, (title, raw.matched_terms)
    assert redacted.event_class == event_class, (redact(title), redacted.matched_terms)


def test_every_indic_cue_word_survives_the_ingress_redaction():
    """Each word of each Bengali or Hindi keyword (and of the CAP terms and the guards' vocabularies) is kept at
    ingress, so the classifier sees it. The only exceptions are words that are also common given names (never added
    to the common words): their keywords match unredacted text only."""
    name_like = {C.normalize_text(w) for w in ("বিদ্যুৎ", "বিদ্যুতের", "অগ্নি", "अग्नि", "প্রতিমা", "বন্যা")}
    words: set[str] = set()
    for kw in [k for row in C.CLASS_LEXICON for k in row.keywords] + list(C.CAP_FLOOD_TERMS) + [
        t for _, terms in C.CAP_SUBTYPES for t in terms
    ]:
        if C.is_indic(kw):
            for slot in C.indic_slots(kw):
                words.update(slot)
    for vocabulary in (C.VEHICLE_WORDS, C._PRICE_WORDS, C._SPITTING_FIRE, C._FIGURATIVE_STORM_OF, C._SOCIAL_MEDIA,
                       C._DENGUE, C._PREVENT, C._VOTE, C._THIN, C._PUJA, C._NEGATORS):
        words.update(w for w in vocabulary if C.is_indic(w))
    assert len(words) > 250
    withheld = sorted(w for w in words if ethics.unredactable_spans(w))
    assert set(withheld) == name_like, withheld
    for w in name_like:  # and those stay withheld: they double as names
        assert ethics._indic_key(w) not in ethics.INDIC_COMMON_WORDS


@pytest.mark.parametrize(
    ("text", "keyword"),
    [
        ("রাস্তায় জলে ডুবে গাড়ি", "জমা জল"),  # no
        ("বাসের ধাক্কায়", "ধাক্কা"),  # a case ending
        ("দুর্ঘটনায় আহত", "দুর্ঘটনা"),
        ("মিছিলের জেরে", "মিছিল"),
        ("ঝড়ের দাপট", "ঝড়"),
        ("দুর্ঘটনাগুলো", "দুর্ঘটনা"),
        ("दुर्घटनाओं में", "दुर्घटना"),  # a Hindi plural
        ("গাছের ডাল ভেঙে পড়ল", "গাছ … পড়ে/পড়ল/পড়লো/পড়েছে/পড়া/ভেঙে/উপড়ে"),  # one word between
        ("জল-যন্ত্রণা", "জলযন্ত্রণা"),  # no: a hyphenated spelling is two words
    ],
)
def test_indic_words_match_with_their_case_endings_and_slots(text, keyword):
    expected = keyword not in ("জমা জল", "জলযন্ত্রণা")
    assert C.keyword_matches(keyword, text) is expected


def test_an_indic_keyword_is_a_whole_word():
    assert not C.keyword_matches("জল জমা/জমে/জমেছে/জমল/জমছে/জমেছিল/জমতে", "কাজল জমে")  # "জল" inside "কাজল"
    assert not C.keyword_matches("আগুন", "আগুনপাখি")  # a word that merely starts with the cue
    assert not C.keyword_matches("মিছিল", "সমিছিল")
    assert not C.keyword_matches("গাছ … পড়ে/পড়ল/পড়লো/পড়েছে/পড়া/ভেঙে/উপড়ে", "গাছ লাগিয়ে বই পড়ে")  # two between
    assert C.keyword_matches("গাছ … পড়ে/পড়ল/পড়লো/পড়েছে/পড়া/ভেঙে/উপড়ে", "গাছ পড়ে")
    assert C.keyword_forms("মিছিল") == ("মিছিল",)  # an Indic keyword has no English forms


def test_a_shared_word_reads_its_context_per_row():
    clash, collision = "দুই গোষ্ঠীর সংঘর্ষ", "দুই বাসের সংঘর্ষ"
    assert C.keyword_matches("সংঘর্ষ", clash, "public_conflict") and not C.keyword_matches("সংঘর্ষ", clash,
                                                                                           "road_accident")
    assert C.keyword_matches("সংঘর্ষ", collision, "road_accident")
    assert not C.keyword_matches("সংঘর্ষ", collision, "public_conflict")


def test_matched_terms_name_the_cue_never_another_word_of_the_text():
    got = C.classify(bn("বাড়ির [WITHHELD] ভেঙে পড়ল বউবাজারে"))
    assert got.matched_terms == ["বাড়ি … ভেঙে"]  # the gap word is shown as "…"
    got = C.classify(bn("ঠনঠনিয়ায় বিধান সরণিতে জল জমে যান চলাচল ব্যাহত"))
    assert got.matched_terms == ["জল জমে"]


def test_a_dropped_non_joiner_never_turns_a_bandh_into_a_closure():
    assert C.normalize_text("বন্‌ধ") == C.normalize_text("বনধ") != C.normalize_text("বন্ধ")
    assert C.classify(bn("রাস্তা বন্ধ")).event_class == "road_closure"
    assert C.classify(bn("বন্‌ধ পালন")).event_class == "unrest"


@pytest.mark.parametrize(
    ("title", "cap_event", "event_class", "subtype"),
    [
        ("কলকাতা জেলায় ভারী বৃষ্টির সতর্কতা", None, "urban_flooding", "waterlogging"),
        ("নিচু এলাকায় জল জমতে পারে, সতর্ক থাকুন", None, "urban_flooding", "waterlogging"),
        ("कोलकाता में भारी बारिश की चेतावनी", None, "urban_flooding", "waterlogging"),
        ("বজ্রবিদ্যুৎ সহ বৃষ্টির সতর্কতা", None, "weather_hazard", "thunderstorm"),
        ("কালবৈশাখীর সতর্কতা, দমকা হাওয়া", None, "weather_hazard", "thunderstorm"),
        ("বঙ্গোপসাগরে ঘূর্ণিঝড়, উপকূলে সতর্কতা", None, "weather_hazard", "cyclone"),
        ("তাপপ্রবাহের সতর্কতা", None, "weather_hazard", "heat"),
        ("ভোরে ঘন কুয়াশার সম্ভাবনা", None, "weather_hazard", "fog"),
        ("হালকা থেকে মাঝারি বৃষ্টির সম্ভাবনা", None, "weather_hazard", "rain"),
        ("কলকাতা জেলার জন্য সতর্কবার্তা", None, "weather_hazard", "weather_advisory"),
    ],
)
def test_the_sachet_rule_reads_bengali_and_hindi_alerts(title, cap_event, event_class, subtype):
    alert = make_signal("sachet_cap", title=title, publisher="sachet.ndma.gov.in", admin_codes=["LGD:KOLKATA"])
    alert = alert.model_copy(update={"language": "bn", "raw": {"cap_identifier": "synthetic.cap.bn"}})
    got = C.classify(alert)
    assert (got.event_class, got.subtype) == (event_class, subtype), title


def test_fusion_tokens_read_bengali_words_whole_and_drop_the_withheld_token():
    a = bn("ঠনঠনিয়ায় জল জমেছে, [WITHHELD] নাকাল")
    b = bn("ঠনঠনিয়া এলাকায় জলে ডুবে রাস্তা", publisher="news-bn-b.example")
    ta, tb = content_tokens(a), content_tokens(b)
    assert "withheld" not in ta
    assert C.normalize_text("ঠনঠনিয়া") in ta & tb and C.normalize_text("জল") in ta & tb  # case endings stripped
    assert all(unicodedata.category(t[-1])[0] in "LMN" for t in ta)  # never a fragment cut at a vowel sign
    assert "3" in content_tokens(bn("আহত ৩")) and "3" in content_tokens(bn("তিনটি গাড়ি"))  # digits, number words


def test_fuzz_bengali_and_hindi_titles_never_yield_crime_incident():
    rng = random.Random(20261028)
    vocab = [w for row in C.CLASS_LEXICON for k in row.keywords if C.is_indic(k) for slot in C.indic_slots(k)
             for w in slot] + ["ডাকাতি", "চুরি", "পুলিশ", "গাড়ি", "ধাওয়া", "পিছু", "নজরদারি", WITHHELD, "কলকাতা"]
    for _ in range(300):
        title = " ".join(rng.choice(vocab) for _ in range(rng.randint(2, 10)))
        source = rng.choice(["news_rss", "google_news_rss", "reddit_rss", "sachet_cap"])
        publisher = {"news_rss": "news-bn-a.example", "google_news_rss": "news-a.example",
                     "reddit_rss": "social-a.example/r/example_city", "sachet_cap": "sachet.ndma.gov.in"}[source]
        got = C.classify(make_signal(source, title=title, publisher=publisher))
        assert got.sahoshi_event_kind not in ("crime_incident", "vehicle_pursuit"), title
        assert got.event_class in kinds.EVENT_CLASS_NAMES


def test_every_guard_belongs_to_a_keyword_it_guards():
    keywords = {k for row in C.CLASS_LEXICON for k in row.keywords} | set(C.CAP_FLOOD_TERMS)
    assert set(C.CONTEXT_RULES) <= keywords  # a renamed keyword never silently loses its guard
    for event_class, keyword in C.CLASS_CONTEXT_RULES:
        assert keyword in C.default_row(event_class).keywords or any(
            row.event_class == event_class and keyword in row.keywords for row in C.CLASS_LEXICON
        )
