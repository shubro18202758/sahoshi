"""The 30-phrase evaluation set: the report rules on the reference text.

This is the upper bound for the audio round-trip (no ASR errors). It must
stay perfect: a rule change that breaks a phrase here is a regression.
"""

from __future__ import annotations

from speech_service.places import Gazetteer
from speech_service.report import build_report


def test_thirty_kolkata_phrases(phrases: list[dict], gaz: Gazetteer) -> None:
    assert len(phrases) == 30
    ids = {p.id for p in gaz.places}
    misses = []
    for p in phrases:
        assert p["place"] in ids
        rep = build_report(p["text"], gaz, source="field-text", language="bn")
        got = (rep["place"] or {}).get("id")
        if got != p["place"] or rep["kind"] != p["kind"]:
            misses.append((p["id"], got, rep["kind"]))
        assert rep["verification_state"] == "UNVERIFIED-FIELD"
    assert misses == []
