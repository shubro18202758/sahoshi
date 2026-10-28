"""ASR helpers that need no model."""

from __future__ import annotations

from types import SimpleNamespace

from speech_service.asr import _CONTROL_RE, _complete_generation_config


class _Tok:
    unk_token_id = 0
    ids = {"<|en|>": 50259, "<|hi|>": 50276, "<|bn|>": 50302, "<|transcribe|>": 50359,
           "<|translate|>": 50358, "<|notimestamps|>": 50363}
    added_tokens_encoder = dict(ids)

    def convert_tokens_to_ids(self, t):
        return self.ids.get(t, 0)


def test_old_generation_configs_get_language_tables() -> None:
    model = SimpleNamespace(generation_config=SimpleNamespace())
    _complete_generation_config(model, _Tok())
    gc = model.generation_config
    assert gc.lang_to_id == {"<|en|>": 50259, "<|hi|>": 50276, "<|bn|>": 50302}
    assert gc.task_to_id == {"transcribe": 50359, "translate": 50358}
    assert gc.no_timestamps_token_id == 50363 and gc.is_multilingual


def test_complete_configs_are_left_alone() -> None:
    gc = SimpleNamespace(lang_to_id={"<|bn|>": 1}, task_to_id={"transcribe": 2})
    _complete_generation_config(SimpleNamespace(generation_config=gc), _Tok())
    assert gc.lang_to_id == {"<|bn|>": 1}


def test_leaked_control_tokens_are_stripped() -> None:
    raw = "<|startoftranscript|><|bn|><|transcribe|><|notimestamps|>বাস আটকে আছে।"
    assert _CONTROL_RE.sub("", raw) == "বাস আটকে আছে।"


def test_routing_by_language() -> None:
    import numpy as np

    from speech_service.asr import RoutedASR, Transcript

    class B:
        def __init__(self, name, detected="bn"):
            self.model_id, self.detected, self.calls = name, detected, []

        def transcribe(self, x, lang):
            self.calls.append(lang)
            return Transcript("t", lang, 0.9, self.model_id, 0.0)

        def detect(self, x):
            return self.detected

    bn, multi = B("bn-model"), B("multi-model", detected="hi")
    r = RoutedASR(bn, multi)
    x = np.zeros(16000, dtype=np.float32)
    assert r.transcribe(x, "bn").model == "bn-model"
    assert r.transcribe(x, "en").model == "multi-model"
    assert r.transcribe(x, None).language == "hi"  # auto: detected by the multilingual model
    multi.detected = "bn"
    assert r.transcribe(x, None).model == "bn-model"
    assert bn.calls == ["bn", "bn"] and multi.calls == ["en", "hi"]
