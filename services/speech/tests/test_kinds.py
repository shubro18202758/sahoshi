"""Kind and severity rules (Bengali, English, romanised)."""

from __future__ import annotations

import pytest

from speech_service.kinds import KINDS, classify


@pytest.mark.parametrize("text,kind", [
    ("গড়িয়াহাট মোড়ে হাঁটু জল, বাস আটকে আছে", "waterlogging"),
    ("Knee-deep water at Gariahat, buses stuck", "waterlogging"),
    ("Gariahat more e hatu jol", "waterlogging"),
    ("শিয়ালদহ স্টেশনের সামনে প্রচণ্ড যানজট", "jam"),
    ("Massive traffic jam on the Bypass", "jam"),
    ("রুবি মোড়ে দুটো গাড়ির ধাক্কা", "accident"),
    ("Collision between a taxi and a bus at Exide", "accident"),
    ("উল্টোডাঙা মোড়ে গাছ পড়ে রাস্তা বন্ধ", "tree_fall"),
    ("Fallen tree across both lanes", "tree_fall"),
    ("মৌলালির কাছে রাস্তা অবরোধ চলছে", "blockade"),
    ("ধর্মতলায় মিছিল চলছে", "procession"),
    ("Immersion procession at Babughat", "procession"),
    ("বাগবাজারে আগুন লেগেছে", "fire"),
    ("পার্ক স্ট্রিটে বিদ্যুতের তার ছিঁড়ে পড়ে আছে", "live_wire"),
    ("Live wire hanging over the road at Hazra", "live_wire"),
    ("হাওড়া ব্রিজে একটা বাস খারাপ হয়ে গেছে", "other"),
])
def test_kind(text: str, kind: str) -> None:
    c = classify(text)
    assert c.kind == kind, c
    assert c.kind in KINDS
    if kind != "other":
        assert c.kind_cues, "the officer sees which words decided the label"


def test_jam_is_a_symptom_when_a_cause_is_reported() -> None:
    assert classify("জল জমে প্রচণ্ড যানজট").kind == "waterlogging"
    assert classify("গাছ পড়ে যানজট").kind == "tree_fall"


def test_pronoun_tar_is_not_a_live_wire() -> None:
    # "তার" is also "his/her"; only wire phrases count
    assert classify("তার বাড়ি এখানে").kind == "other"


def test_words_inside_place_names_do_not_fire() -> None:
    # "পুড়ে" (burnt) folds to the tail of "খিদিরপুরে" (in Kidderpore)
    c = classify("খিদিরপুরে কন্টেনার লরির জন্য বিশাল জ্যাম")
    assert c.kind == "jam"
    assert "fire" not in c.scores


def test_single_weak_word_is_not_a_label() -> None:
    assert classify("রাস্তায় জল").kind == "other"


@pytest.mark.parametrize("text,severity", [
    ("কালীঘাটে গোড়ালি জল", "low"),
    ("গড়িয়াহাট মোড়ে হাঁটু জল, বাস আটকে আছে", "medium"),
    ("ঠনঠনিয়ায় কোমর জল", "high"),
    ("রুবি মোড়ে দুর্ঘটনা, একজন আহত", "high"),
    ("ধর্মতলায় মিছিল", "low"),
    ("ধর্মতলায় মিছিল, রাস্তা বন্ধ", "medium"),
    ("বাগবাজারে আগুন", "high"),
    ("একটু ধোঁয়া, সামান্য আগুন", "high"),  # fire never drops below high
    ("Minor jam near Exide", "low"),
])
def test_severity(text: str, severity: str) -> None:
    assert classify(text).severity == severity


@pytest.mark.parametrize("text,kind", [
    ("রাস্তায় জল নেই, কিন্তু প্রচণ্ড যানজট", "jam"),
    ("No water on the road, heavy traffic jam", "jam"),
    ("জল জমেনি", "other"),
    ("road not blocked, slow traffic", "other"),
])
def test_negated_cues_do_not_count(text: str, kind: str) -> None:
    assert classify(text).kind == kind


@pytest.mark.parametrize("text,kind", [
    ("শিয়াল দহ স্টেশনের সামনে প্রচণ্ড যাঞ্জট", "jam"),   # ASR spelling of যানজট
    ("মোড়ে যান জোট", "jam"),                            # split into two words
    ("বাবু ঘাটে শোভা যাত্রা", "procession"),
])
def test_asr_misspelt_strong_cues_still_count_and_say_so(text: str, kind: str) -> None:
    c = classify(text)
    assert c.kind == kind
    assert any(cue.endswith("(≈)") for cue in c.kind_cues)


def test_fuzzy_cues_do_not_invent_hazards() -> None:
    assert classify("অফিস ছুটির পর গাড়ি নড়ছে না").kind == "jam"  # not "ছেঁড়া তার"
    assert classify("জল জমেনি").kind == "other"
