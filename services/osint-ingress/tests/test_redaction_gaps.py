"""F-HONEST OSINT-2 and OSINT-6: the redaction gaps the audit proved (``probes/osint_redaction_probe.txt``).

Names with no cue word, Indic-script names, and a poster's age and sex shorthand all survived parse-time redaction
while ``ethics.find_pii`` still answered ``[]``. The probes below keep the audit's shapes, written for Kolkata
(English, Bengali and Hindi); every name is invented, none is a real person's.
"""

from __future__ import annotations

import pytest

from osint_common import ethics
from osint_ingress.connectors._redact import TOKEN_WITHHELD, redact_persons

#: (text, name words that must be gone): the audit probe's leak shapes, written for Kolkata (fictional names).
AUDIT_LEAKS = [
    ("Biker Subrata Mondal dies after truck hits him on EM Bypass", ["Subrata", "Mondal"]),
    ("Subrata Mondal dies after truck hits him on EM Bypass", ["Subrata", "Mondal"]),
    ("Hit-and-run: Paresh Saha, a resident of Behala, succumbs", ["Paresh", "Saha"]),
    ("Police arrest Mehul Dutta for chain snatching in Gariahat", ["Mehul", "Dutta"]),
    ("Accused Bapi alias Bhulu held for robbery", ["Bapi", "Bhulu"]),
    ("Septuagenarian Haripada Mitra robbed at Salt Lake", ["Haripada", "Mitra"]),
    ("Doctor couple Nirav and Priya Sen robbed at gunpoint near Ballygunge", ["Nirav", "Priya", "Sen"]),
    ("রমেশ মণ্ডল (৪৫)-এর দুর্ঘটনায় মৃত্যু", ["রমেশ", "মণ্ডল", "৪৫"]),
    ("শ্রী বিজয় দাস গড়িয়াহাটে আহত", ["বিজয়", "দাস"]),  # an honorific: the given name may be an ordinary word
    ("অভিযুক্ত রমেশ মণ্ডলকে গ্রেপ্তার করেছে পুলিশ", ["রমেশ", "মণ্ডল"]),
    ("৩৫ বছরের সুব্রত সাহা বেহালায় দুর্ঘটনায় আহত", ["সুব্রত", "সাহা", "৩৫"]),
    ("কোলকাতায় শ্যামলবাবুর দোকানে চুরি", ["শ্যামল"]),
    ("कोलकाता में रमेश मंडल की हत्या", ["रमेश", "मंडल"]),
    ("Where is Kalpita's body? 11 days on, sewer search continues", ["Kalpita"]),  # the stored-victim shape
]


def _kept(word: str, text: str) -> bool:
    import re

    if word.isascii():
        return re.search(rf"(?<![A-Za-z0-9]){re.escape(word)}(?![A-Za-z0-9])", text) is not None
    return word in text


@pytest.mark.parametrize("tier", ["news_regional", "aggregator", "news_wire", "social_unverified", "official"])
@pytest.mark.parametrize(("text", "names"), AUDIT_LEAKS)
def test_the_audit_leaks_are_redacted_in_every_tier(protect, tier, text, names):
    out, n = redact_persons(text, tier, protect)
    assert n > 0 and not [w for w in names if _kept(w, out)], out
    assert ethics.find_pii(out) == [] and ethics.find_unredactable(out) == []


@pytest.mark.parametrize(
    ("text", "kept"),
    [
        ("Biker Subrata Mondal dies after truck hits him on EM Bypass", ["Biker", "EM Bypass"]),
        ("Hit-and-run: Paresh Saha, a resident of Behala, succumbs", ["Behala"]),
        ("Truck overturns on AJC Bose Road near Park Circus", ["AJC Bose Road", "Park Circus"]),
        ("Fixture Kiosk Opens At Riverfront", ["Fixture Kiosk Opens At Riverfront"]),  # a Title-Case headline
        ("Youth Association rally near Esplanade", ["Youth Association"]),  # an organisation after a role noun
        ("Ghosh family meeting at Deshapriya Park", ["Ghosh family"]),  # a surname alone is not a person
    ],
)
def test_places_organisations_and_headlines_survive(protect, text, kept):
    out, _ = redact_persons(text, "news_regional", protect)
    assert all(k in out for k in kept), out


def test_indic_words_are_withheld_but_gazetteer_places_and_common_words_stay(protect):
    out, n = redact_persons("গড়িয়াহাটে আগুন: রমেশ সাহা সহ তিন জন আহত", "news_regional", protect)
    assert out == f"গড়িয়াহাটে আগুন: {TOKEN_WITHHELD} সহ তিন জন আহত" and n == 1
    out, _ = redact_persons("হাওড়া ব্রিজে যানজট, শিয়ালদহে জল জমা", "aggregator", protect)
    assert TOKEN_WITHHELD not in out  # places (with a case ending) and common words only
    out, _ = redact_persons("हावड़ा ब्रिज पर टक्कर, सियालदह में जाम", "aggregator", protect)
    assert TOKEN_WITHHELD not in out
    # the Devanagari name in a half-Latin title (the shape of a stored int3c case) goes with the Latin one
    out, _ = redact_persons("फिक्टस डमीवाला के खिलाफ केस; case on Accused Fictus Dummyvala", "aggregator", protect)
    assert "फिक्टस" not in out and "डमीवाला" not in out and "Dummyvala" not in out


def test_indic_suffixes_are_the_geo_scanners(protect):
    from osint_geo import translit

    assert set(ethics.INDIC_SUFFIXES) == set(translit.BN_SUFFIXES)


@pytest.mark.parametrize(
    ("text", "marker"),
    [
        ("IT'S SO BORINGGGG IN WEEEKEND HERE F(28)", "F(28)"),
        ("Any other 22M second-gen imitation jewelry wholesalers here?", "22M"),
        ("27/F, is the Thanthania stretch flooded?", "27/F"),
        ("(24F) looking for a flatmate in Salt Lake", "24F"),
        ("M/30 here, moved to New Town last month", "M/30"),
        ("26 M, looking for a cycling group", "26 M"),
    ],
)
def test_a_posters_age_and_sex_shorthand_is_redacted(protect, text, marker):
    out, n = redact_persons(text, "social_unverified", protect)
    assert marker not in out and "[AGE]" in out and n >= 1, out


@pytest.mark.parametrize("text", ["Flat for Rs 22M in Ballygunge", "Flat for Rs. 22M in Ballygunge", "Budget ₹22M"])
def test_amounts_are_not_age_markers(protect, text):
    # known over-redaction, accepted: a bare "15M" or "M25" in a post reads as an age marker (the poster's own
    # "22M" cannot be told apart from it without context)
    out, _ = redact_persons(text, "social_unverified", protect)
    assert "[AGE]" not in out, out
