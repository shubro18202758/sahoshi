"""Real models on the GPU (opt-in: SPEECH_SLOW=1).

    SPEECH_SLOW=1 python -m pytest -m slow tests/test_slow_models.py

Speaks one Kolkata field report with the real TTS, transcribes it with the
real ASR and builds the report: a synthetic round trip, not a recording.
"""

from __future__ import annotations

import os

import pytest

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(os.environ.get("SPEECH_SLOW") != "1", reason="set SPEECH_SLOW=1"),
]


def test_round_trip(gaz) -> None:
    from speech_service.asr import WhisperASR
    from speech_service.audio import TARGET_SR, resample
    from speech_service.config import Settings
    from speech_service.report import build_report
    from speech_service.tts import SvaraTTS

    s = Settings()
    tts = SvaraTTS(s.tts_model, s.tts_codec, min_free_gib=8)
    audio, sr = tts.synthesize("ঠনঠনিয়ায় কোমর জল জমেছে, গাড়ি চলছে না।", "bn", "female")
    tts.unload()
    assert audio.size / sr > 1.0
    asr = WhisperASR(s.asr_model, min_free_gib=8)
    tr = asr.transcribe(resample(audio, sr, TARGET_SR), "bn")
    asr.unload()
    assert tr.text and tr.language == "bn"
    rep = build_report(tr.text, gaz, source="field-voice", language="bn")
    assert rep["kind"] == "waterlogging"
    assert rep["verification_state"] == "UNVERIFIED-FIELD"
