"""PII-Tracer span detection (embedding_service.pii): post-processing, the protected-toponym guard and the lazy
detector, all offline. The model is mocked; the one real-model test is ``slow`` and skips unless torch imports
and the reviewed snapshot is in the local Hugging Face cache.

Every sentence here is SYNTHETIC; the person names are fictional.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

from embedding_service import pii
from embedding_service.pii import (
    DEFAULT_LABELS,
    PLATE_LABEL,
    FakePiiDetector,
    PiiTracerDetector,
    RawSpan,
    ToponymGuard,
    default_protected_names,
    load_gazetteer_names,
    load_landmark_names,
    postprocess,
    snap_to_words,
)

_SRC = Path(__file__).resolve().parents[1] / "src"
_LANDMARKS = Path(__file__).resolve().parents[3] / "cities" / "kolkata" / "landmarks.json"
_GAZETTEER = _LANDMARKS.with_name("gazetteer.json")


def _span(text: str, needle: str, label: str = "private_person", score: float = 0.9) -> RawSpan:
    i = text.index(needle)
    return RawSpan(i, i + len(needle), label, score)


def _texts(text: str, spans: list[dict]) -> list[str]:
    return [text[s["start"] : s["end"]] for s in spans]


@pytest.fixture(scope="module")
def guard() -> ToponymGuard:
    return ToponymGuard()


# ── import hygiene ───────────────────────────────────────────────────────────────────────────────────────────────


def test_module_imports_without_heavy_dependencies():
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]); import embedding_service.pii as p; "
        "p.FakePiiDetector({'x': 'private_person'}).detect(['x']); "
        "bad = [m for m in ('torch', 'transformers', 'huggingface_hub') if m in sys.modules]; "
        "print(','.join(bad)); sys.exit(1 if bad else 0)"
    )
    res = subprocess.run([sys.executable, "-I", "-c", code, str(_SRC)], capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stdout + res.stderr


def test_constructing_the_real_detector_loads_nothing():
    det = PiiTracerDetector(guard=ToponymGuard(()))
    assert not det.loaded
    assert det.model_name == f"{pii.DEFAULT_MODEL_ID}@{pii.DEFAULT_REVISION[:7]}"
    assert det.labels == DEFAULT_LABELS


# ── word snapping ────────────────────────────────────────────────────────────────────────────────────────────────


def test_snap_widens_a_half_bengali_word():
    text = "স্থানীয় বাসিন্দা সুব্রত মণ্ডল জানালেন।"
    i = text.index("সুব্রত") + 1  # the byte-level tokenizer started the span after the first letter
    s, e = snap_to_words(text, i, i + len("ুব্রত"))
    assert text[s:e] == "সুব্রত"


def test_snap_widens_a_half_devanagari_word_and_trims_punctuation():
    text = "ड्राइवर राकेश दास घायल।"
    i = text.index("राकेश")
    s, e = snap_to_words(text, i, i + len("राकेश द"))
    assert text[s:e] == "राकेश दास"
    s, e = snap_to_words(text, text.index("घायल"), len(text))
    assert text[s:e] == "घायल"


def test_snap_on_latin_text():
    text = "Traffic slow on Sarat Bose Road."
    i = text.index("Sarat")
    assert snap_to_words(text, i, i + 3) == (i, i + 5)
    assert snap_to_words(text, 0, 0) == (0, 0)


# ── the protected-toponym guard ──────────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("text", "needle"),
    [
        ("A bus broke down on Sarat Bose Road near the crossing.", "Sarat"),
        ("A bus broke down on Sarat Bose Road near the crossing.", "Sarat Bose"),
        ("Signals failed on Acharya Jagadish Chandra Bose Road.", "Jagadish Chandra Bose"),
        ("Flights at Netaji Subhas Chandra Bose International Airport were late.", "Netaji Subhas Chandra"),
        ("Walkers at Rabindra Sarobar saw a fallen branch.", "Rabindra"),
        ("A show at Rabindra Sadan ends at 9 pm.", "Rabindra Sadan"),
        ("Mother Teresa Sarani is one-way until Friday.", "Mother Teresa"),
        ("Passengers at Masterda Surya Sen metro station were held back.", "Masterda Surya Sen"),
        ("Water stood on Lenin Sarani at high tide.", "Lenin"),  # not in any list: the place-word rule
        ("A fire was reported at Bagha Jatin late on Tuesday.", "Jatin"),  # no place word: the built-in list
        ("A fire was reported at Bagha Jatin late on Tuesday.", "Bagha Jatin"),
        ("শরৎ বসু রোডে বাস বিকল।", "শরৎ বসু"),
        ("বিধান সরণিতে যানজট।", "বিধান"),
        ("রবীন্দ্র সরোবরের কাছে ডাল ভেঙেছে।", "রবীন্দ্র"),
        ("ঝড়ের পরে নেতাজি সুভাষচন্দ্র বসু আন্তর্জাতিক বিমানবন্দরে বিমান দেরিতে ছেড়েছে।", "নেতাজি"),
        ("বাঘাযতীনে আগুন লাগে।", "বাঘাযতীনে"),
        ("शरत बोस रोड पर बस खराब।", "शरत बोस"),
        ("तूफ़ान के बाद नेताजी सुभाष चंद्र बोस अंतरराष्ट्रीय हवाई अड्डे पर उड़ानें देर से चलीं।", "नेताजी सुभाष"),
    ],
)
def test_eponymous_places_are_never_redacted(guard, text, needle):
    assert postprocess(text, [_span(text, needle)], guard=guard) == []


def test_person_next_to_an_eponymous_road_is_kept(guard):
    text = "Driver Subrata Mondal was unhurt after the bus broke down on Sarat Bose Road."
    raw = [_span(text, "Subrata Mondal"), _span(text, "Sarat Bose")]
    assert _texts(text, postprocess(text, raw, guard=guard)) == ["Subrata Mondal"]


def test_a_known_place_ends_a_capitalised_run(guard):
    # "<Given> <Surname> Shyama Prasad Mukherjee Road": the run before "Road" is six capitalised words, but the
    # known place name is only the last four, so the person stays redacted
    text = "Amar neighbour Arnab Biswas Shyama Prasad Mukherjee Road e atke ache."
    raw = [_span(text, "Arnab Biswas Shyama Prasad Mukherjee")]
    assert _texts(text, postprocess(text, raw, guard=guard)) == ["Arnab Biswas"]


def test_lower_case_institution_word_does_not_swallow_a_name(guard):
    text = "Lorry ulte geche, khalashi Raju Naskar hospital e."
    assert _texts(text, postprocess(text, [_span(text, "Raju Naskar")], guard=guard)) == ["Raju Naskar"]
    text = "প্রফুল্লচন্দ্র রোডে লরি উল্টে গেছে, খালাসি রাকেশ যাদব হাসপাতালে।"
    assert _texts(text, postprocess(text, [_span(text, "রাকেশ যাদব")], guard=guard)) == ["রাকেশ যাদব"]


def test_single_word_place_only_drops_an_exact_fragment():
    g = ToponymGuard(["Hazra crossing"])  # variant "Hazra" is a single-word place and a common surname
    text = "Rina Hazra was stuck at Hazra crossing for an hour."
    raw = [_span(text, "Rina Hazra"), RawSpan(text.rindex("Hazra"), text.rindex("Hazra") + 5, "private_person", 0.8)]
    assert _texts(text, postprocess(text, raw, guard=g)) == ["Rina Hazra"]


def test_injected_protected_names_replace_the_default():
    text = "Crowds gathered at Uttam Mancha."
    raw = [_span(text, "Uttam")]
    assert postprocess(text, raw, guard=ToponymGuard(["Uttam Mancha"], place_words=False)) == []
    assert _texts(text, postprocess(text, raw, guard=ToponymGuard((), place_words=False))) == ["Uttam"]
    # the place-word rule alone (capitalised "Mancha") also protects it
    assert postprocess(text, raw, guard=ToponymGuard(())) == []


def test_landmarks_file_is_read_with_variants(tmp_path):
    names = load_landmark_names(_LANDMARKS)
    if _LANDMARKS.is_file():
        assert {"Esplanade", "BBD Bag", "Gariahat", "বিবাদী বাগ", "রাসবিহারী", "Lalbazar"} <= names
        assert "Bagha Jatin" in default_protected_names(_LANDMARKS)
    p = tmp_path / "lm.json"
    p.write_text('{"landmarks": [{"en": "Park Street crossing", "bn": "পার্ক স্ট্রিট মোড়"}, 7, {"en": ""}]}')
    assert load_landmark_names(p) == {"Park Street crossing", "Park Street", "পার্ক স্ট্রিট মোড়", "পার্ক স্ট্রিট"}
    p.write_text("not json")
    assert load_landmark_names(p) == frozenset()
    assert load_landmark_names(tmp_path / "missing.json") == frozenset()


def test_gazetteer_places_and_aliases_are_protected(tmp_path):
    names = load_gazetteer_names(_GAZETTEER)
    if _GAZETTEER.is_file():
        # neighbourhoods that are not landmarks: the model has called "Behala" a person
        assert {"Behala", "বেহালা", "बेहाला"} <= names
        assert {"Behala", "বেহালা"} <= default_protected_names(_LANDMARKS, _GAZETTEER)
        text = "Mrinmoy Shee of Behala reported waterlogging."
        raw = [_span(text, "Mrinmoy Shee"), _span(text, "Behala")]
        assert _texts(text, postprocess(text, raw, guard=ToponymGuard(names))) == ["Mrinmoy Shee"]
    p = tmp_path / "gz.json"
    p.write_text('{"places": [{"en": "Tollygunge", "bn": "টালিগঞ্জ", "aka": ["Tolly"], "aka_bn": [5]}, "x", {}]}')
    assert load_gazetteer_names(p) == {"Tollygunge", "টালিগঞ্জ", "Tolly"}
    p.write_text("[]")
    assert load_gazetteer_names(p) == frozenset()
    assert load_gazetteer_names(tmp_path / "missing.json") == frozenset()


# ── post-processing ──────────────────────────────────────────────────────────────────────────────────────────────


def test_plates_are_relabelled_and_left_out_by_default(guard):
    text = "A car, WB 02 AB 1234, hit the divider."
    raw = [_span(text, "WB 02 AB 1234", "account_number", 0.97)]
    assert postprocess(text, raw, guard=guard) == []
    out = postprocess(text, raw, guard=guard, labels=None)
    assert [(d["label"], text[d["start"] : d["end"]]) for d in out] == [(PLATE_LABEL, "WB 02 AB 1234")]


def test_contacts_survive_the_guard_and_mobiles_are_relabelled(guard):
    text = "Call 98300 41526 or 9830015577, or write to ward87.help@example.in near Sealdah Station."
    raw = [
        _span(text, "98300 41526", "private_phone", 0.99),
        _span(text, "9830015577", "account_number", 0.99),
        _span(text, "ward87.help@example.in", "private_email", 0.99),
    ]
    out = postprocess(text, raw, guard=guard)
    assert [(d["label"], text[d["start"] : d["end"]]) for d in out] == [
        ("private_phone", "98300 41526"),
        ("private_phone", "9830015577"),
        ("private_email", "ward87.help@example.in"),
    ]


def test_short_public_numbers_and_letterless_names_are_dropped(guard):
    text = "Dial 112 or ambulance (108); flights were 40 minutes late."
    raw = [
        _span(text, "112", "private_phone"),
        _span(text, "108", "private_phone"),
        _span(text, "40", "private_person"),
    ]
    assert postprocess(text, raw, guard=guard) == []


def test_score_floor_label_filter_and_merge(guard):
    text = "Mrs Mitali Ghosh said the drains were choked."
    raw = [
        _span(text, "Mrs Mitali", score=0.6),
        _span(text, "Mitali Ghosh", score=0.9),
        _span(text, "drains", "private_address", 0.9),
        _span(text, "choked", score=0.2),
    ]
    out = postprocess(text, raw, guard=guard)
    assert out == [{"start": 0, "end": len("Mrs Mitali Ghosh"), "label": "private_person", "score": 0.9}]
    assert postprocess(text, raw, guard=guard, min_score=0.95) == []
    assert len(postprocess(text, raw, guard=guard, labels=None, min_score=0.0)) == 3


def test_out_of_range_spans_are_ignored(guard):
    assert postprocess("abc", [RawSpan(5, 9, "private_person", 0.9), RawSpan(2, 1, "private_person", 0.9)],
                       guard=guard) == []


# ── detectors ────────────────────────────────────────────────────────────────────────────────────────────────────


def test_fake_detector_runs_the_real_post_processing():
    det = FakePiiDetector({"Subrata Mondal": "private_person", "Sarat Bose": "private_person"})
    texts = ["Driver Subrata Mondal was hurt on Sarat Bose Road.", "", None]  # type: ignore[list-item]
    out = det.detect(texts)
    assert [_texts(t or "", o) for t, o in zip(texts, out, strict=True)] == [["Subrata Mondal"], [], []]
    assert out[0][0]["score"] == 1.0 and det.calls == 1
    assert det.detect([]) == []


def test_detector_rejects_bad_configuration():
    with pytest.raises(ValueError, match="unknown labels"):
        FakePiiDetector(labels=("private_person", "face"))
    with pytest.raises(ValueError, match="min_score"):
        FakePiiDetector(min_score=1.5)


def test_unreviewed_model_code_is_refused_before_any_import(tmp_path):
    (tmp_path / "modeling_pii_masking.py").write_text("import os  # not the reviewed file\n")
    det = PiiTracerDetector(str(tmp_path), revision=None, guard=ToponymGuard(()))
    with pytest.raises(RuntimeError, match="reviewed"):
        det.load()
    assert not det.loaded


def test_raw_spans_chunks_long_texts_and_maps_offsets_back(monkeypatch):
    det = PiiTracerDetector(guard=ToponymGuard(()), batch_size=2)
    det._model = object()  # mocked: no load
    seen: list[str] = []

    def fake_infer(chunks):
        seen.extend(chunks)
        out = []
        for c in chunks:
            i = c.find("Subrata Mondal")
            out.append([RawSpan(i, i + 14, "private_person", 0.9)] if i >= 0 else [])
        return out

    monkeypatch.setattr(det, "_infer", fake_infer)
    long_text = ("rain " * 400) + "driver Subrata Mondal hurt " + ("rain " * 400)
    texts = ["Subrata Mondal was hurt.", "", "   ", long_text]
    raw = det.raw_spans(texts)
    assert len(seen) >= 3 and all(len(c) <= pii.MAX_CHUNK_CHARS for c in seen)
    assert raw[1] == [] and raw[2] == []
    for t, spans in ((texts[0], raw[0]), (long_text, raw[3])):
        assert [t[s.start : s.end] for s in spans] == ["Subrata Mondal"]
    out = det.detect(texts)
    assert [len(o) for o in out] == [1, 0, 0, 1]


# ── the real model (slow) ────────────────────────────────────────────────────────────────────────────────────────


def _real_model_available() -> bool:
    if importlib.util.find_spec("torch") is None or importlib.util.find_spec("transformers") is None:
        return False
    try:
        from huggingface_hub import try_to_load_from_cache
    except ImportError:
        return False
    hit = try_to_load_from_cache(pii.DEFAULT_MODEL_ID, "model.safetensors", revision=pii.DEFAULT_REVISION)
    return isinstance(hit, str) and os.path.isfile(hit)


@pytest.mark.slow
@pytest.mark.skipif(not _real_model_available(), reason="needs torch and the cached PII-Tracer snapshot")
def test_real_model_end_to_end():
    det = PiiTracerDetector(batch_size=4)
    try:
        texts = [
            "A bus broke down on Sarat Bose Road near Deshapriya Park; driver Subrata Mondal was unhurt.",
            "Contact the ward office at 98300 41526 to report a blocked drain on Bidhan Sarani.",
        ]
        out = det.detect(texts)
        assert "Subrata Mondal" in _texts(texts[0], out[0])
        assert not any("Sarat" in x or "Deshapriya" in x for x in _texts(texts[0], out[0]))
        assert _texts(texts[1], out[1]) == ["98300 41526"]
    finally:
        det.unload()
