"""F-HONEST OSINT-2: Indic-script words no redactor can read for names are found (``ethics.unredactable_spans``).

``find_pii`` reads Latin-script cue patterns only, so a Bengali or Devanagari name passed it as clean (the audit
stored "<Hindi name> के खिलाफ ..." beside its own redacted Latin copy). The names below are fictional.
"""

from __future__ import annotations

import unicodedata

import pytest

from osint_common import ethics


def _apply(text: str) -> str:
    out = text
    for s in reversed(ethics.unredactable_spans(text)):
        out = out[: s.start] + "[W]" + out[s.end :]
    return out


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("কসবায় ফিক্টস ডামিওয়ালার মৃত্যু", "কসবায় [W] মৃত্যু"),  # a place with a case ending, a name, a common word
        ("बेहाला में फिक्टस डमीवाला की हत्या", "बेहाला में [W] की हत्या"),
        ("বেহালায় আগুন", "বেহালায় আগুন"),  # a gazetteer place with a case ending, and a common word
        ("ঠনঠনিয়ায় জল জমে যান চলাচল ব্যাহত", "ঠনঠনিয়ায় জল জমে যান চলাচল ব্যাহত"),  # the low-lying spot, in Bengali
        ("পার্ক সার্কাস সাত মাথার মোড়ে যানজট", "পার্ক সার্কাস সাত মাথার মোড়ে যানজট"),  # a multi-word place phrase
        ("ইএম বাইপাসে দুর্ঘটনা, তিন জন আহত", "ইএম বাইপাসে দুর্ঘটনা, তিন জন আহত"),
        ("ঘূর্ণিঝড়ের প্রভাবে কলকাতায় টানা বৃষ্টি", "ঘূর্ণিঝড়ের প্রভাবে কলকাতায় টানা বৃষ্টি"),
        ("ওসি কে. ডি. ফিক্টসদাস জানান", "[W]. [W]. [W] জানান"),  # initials are a name part, whatever they spell
        ("Plain ASCII text with no script", "Plain ASCII text with no script"),
    ],
)
def test_unknown_indic_words_are_found_and_places_kept(text, expected):
    assert _apply(text) == expected


def test_the_two_spellings_of_ya_with_nukta_read_alike():
    """"য়" is written as one code point (U+09DF) or as "য" + nukta; NFKC makes them one form, so a place with a
    case ending in either spelling is kept."""
    composed = "বেহালায় আগুন"
    decomposed = "বেহালায় আগুন"
    assert unicodedata.normalize("NFKC", composed) == unicodedata.normalize("NFKC", decomposed)
    assert _apply(composed) == composed and _apply(decomposed) == decomposed


def test_find_pii_does_not_see_indic_names_and_find_unredactable_does():
    text = "কলকাতায় ফিক্টস ডামিওয়ালার মৃত্যু"
    assert ethics.find_pii(text) == []  # the documented limit of find_pii: Latin cue patterns only
    assert ethics.find_unredactable(text) == ["script:indic"]
    assert ethics.find_unredactable("কলকাতায় দুর্ঘটনা") == []
    assert ethics.find_unredactable("कोलकाता में हादसा") == []
    assert ethics.find_unredactable(None) == [] and ethics.find_unredactable("") == []


def test_a_multi_word_place_keeps_its_words_only_where_the_whole_phrase_occurs():
    # "মুখার্জি" (a surname) is a word of the gazetteer phrase "শ্যামাপ্রসাদ মুখার্জি রোড": alone it is withheld
    assert _apply("ফিক্টস মুখার্জি") == "[W]"


def test_common_words_hold_no_name():
    for word in (
        "কিরণ", "किरण", "আশা", "आशा", "বিজয়", "विजय", "দীপক", "दीपक", "রাজ", "रमेश", "রমেশ", "মুখার্জি", "দাস",
        "शाह", "বন্যা", "বিদ্যুৎ", "প্রবল", "সন্ধ্যা", "প্রতিমা", "গঙ্গা", "ঠাকুর",
    ):
        assert ethics._indic_key(word) not in ethics.INDIC_COMMON_WORDS, word


def test_suffixes_are_bengali_case_endings():
    """The case endings are Bengali's (locative, genitive, objective, plural, classifier, emphatic), longest first,
    and hold no letter of the old Gujarati tables."""
    suffixes = ethics.INDIC_SUFFIXES
    assert [len(s) for s in suffixes] == sorted((len(s) for s in suffixes), reverse=True)
    for s in ("য়", "তে", "র", "ের", "কে", "দের", "রা", "টি"):
        assert unicodedata.normalize("NFKC", s) in suffixes
    assert not any("઀" <= ch <= "૿" for s in suffixes for ch in s)
    assert not any("઀" <= ch <= "૿" for w in ethics.INDIC_COMMON_WORDS for ch in w)
