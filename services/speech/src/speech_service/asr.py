"""Bengali speech-to-text.

The production backend is a Whisper-family checkpoint run with
``transformers`` on the GPU (see README "Models" for the choice and the
licence). The backend interface is deliberately small so tests can swap in a
fake and a later model (IndicConformer, once its gated weights are granted)
can drop in without touching the API.

The audio array passed in is the only copy of the speech; nothing here keeps
it, logs it or writes it anywhere.
"""

from __future__ import annotations

import math
import re
import threading
import time
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from .audio import TARGET_SR
from .runtime import LazyModel

__all__ = ["Transcript", "ASRBackend", "WhisperASR", "RoutedASR", "SUPPORTED_LANGS"]

SUPPORTED_LANGS = ("bn", "en", "hi")
_CHUNK_S = 30.0
# Some fine-tuned checkpoints ship a tokenizer that does not mark Whisper's
# control tokens as special, so they survive skip_special_tokens.
_CONTROL_RE = re.compile(r"<\|[^|>]{1,20}\|>")


@dataclass(frozen=True)
class Transcript:
    text: str
    language: str
    confidence: float
    model: str
    seconds: float


class ASRBackend(Protocol):
    model_id: str

    def transcribe(self, samples: np.ndarray, lang: str | None) -> Transcript: ...

    def status(self) -> dict: ...

    def maybe_unload_idle(self) -> bool: ...


def _complete_generation_config(model, tok) -> None:
    """Some fine-tuned checkpoints ship a pre-2023 generation config without
    the language/task tables, and then ``generate(language=…)`` refuses to
    run. Rebuild the tables from the checkpoint's own tokenizer."""
    gc = model.generation_config
    if getattr(gc, "lang_to_id", None) and getattr(gc, "task_to_id", None):
        return
    unk = tok.unk_token_id
    langs = {}
    specials = list(getattr(tok, "added_tokens_encoder", {}) or {})
    for t in specials:
        if len(t) <= 9 and t.startswith("<|") and t.endswith("|>") and t[2:-2].isalpha() \
                and t[2:-2].islower() and t[2:-2] not in ("transcribe", "translate", "nocaptions"):
            langs[t] = tok.convert_tokens_to_ids(t)
    for code in SUPPORTED_LANGS:  # make sure ours are there even if the list above is short
        tid = tok.convert_tokens_to_ids(f"<|{code}|>")
        if tid is not None and tid != unk:
            langs[f"<|{code}|>"] = tid
    gc.lang_to_id = langs
    gc.task_to_id = {k: tok.convert_tokens_to_ids(f"<|{k}|>") for k in ("transcribe", "translate")}
    gc.is_multilingual = True
    nts = tok.convert_tokens_to_ids("<|notimestamps|>")
    if nts is not None and nts != unk:
        gc.no_timestamps_token_id = nts


class WhisperASR:
    """Whisper (transformers) with the language forced when it is known.

    Confidence is the geometric-mean token probability of the decoded
    sequence (exp of the mean log-probability), a calibrated-enough signal
    for "ask the officer to check this one" — not an accuracy estimate.
    """

    def __init__(self, model_id: str, *, device: str = "cuda", beams: int = 1,
                 min_free_gib: float = 12.0, idle_unload_s: float = 600) -> None:
        self.model_id = model_id
        self.device = device
        self.beams = beams
        self._run_lock = threading.Lock()
        self._lazy = LazyModel(
            f"asr:{model_id}", self._load, need_gib=4.0,
            min_free_gib=min_free_gib, idle_unload_s=idle_unload_s,
        )

    # -- lifecycle -------------------------------------------------------------
    def _load(self):
        import torch
        from transformers import WhisperForConditionalGeneration, WhisperProcessor

        dtype = torch.float16 if self.device.startswith("cuda") else torch.float32
        proc = WhisperProcessor.from_pretrained(self.model_id)
        model = WhisperForConditionalGeneration.from_pretrained(self.model_id, dtype=dtype)
        model = model.to(self.device).eval()
        _complete_generation_config(model, proc.tokenizer)
        return proc, model, dtype

    def status(self) -> dict:
        return {"model": self.model_id, **self._lazy.status()}

    def maybe_unload_idle(self) -> bool:
        return self._lazy.maybe_unload_idle()

    def unload(self) -> bool:
        return self._lazy.unload()

    # -- inference -------------------------------------------------------------
    def transcribe(self, samples: np.ndarray, lang: str | None) -> Transcript:
        import torch

        proc, model, dtype = self._lazy.get()
        t0 = time.perf_counter()
        texts: list[str] = []
        logps: list[float] = []
        detected = lang
        step = int(_CHUNK_S * TARGET_SR)
        with self._run_lock, torch.inference_mode():
            for start in range(0, max(1, samples.size), step):
                chunk = samples[start:start + step]
                if chunk.size < int(0.2 * TARGET_SR):
                    continue
                feats = proc(chunk, sampling_rate=TARGET_SR, return_tensors="pt").input_features
                feats = feats.to(self.device, dtype=dtype)
                if detected is None:
                    detected = self._detect(model, proc, feats)
                gen = model.generate(
                    feats,
                    language=detected,
                    task="transcribe",
                    num_beams=self.beams,
                    max_new_tokens=220,
                    return_dict_in_generate=True,
                    output_scores=True,
                )
                seq = gen.sequences
                text = proc.batch_decode(seq, skip_special_tokens=True)[0]
                texts.append(_CONTROL_RE.sub("", text).strip())
                try:
                    trans = model.compute_transition_scores(
                        seq, gen.scores, beam_indices=getattr(gen, "beam_indices", None),
                        normalize_logits=True,
                    )
                    vals = trans[0].float().cpu().numpy()
                    vals = vals[np.isfinite(vals)]
                    logps.extend(vals.tolist())
                except Exception:  # scores are a nicety; never fail the transcript
                    pass
        self._lazy.touch()
        conf = float(math.exp(sum(logps) / len(logps))) if logps else 0.0
        return Transcript(
            text=" ".join(t for t in texts if t).strip(),
            language=detected or "bn",
            confidence=round(conf, 3),
            model=self.model_id,
            seconds=round(time.perf_counter() - t0, 3),
        )

    def detect(self, samples: np.ndarray) -> str:
        """Spoken language of the first 30 s: bn, en or hi (anything else → bn)."""
        import torch

        proc, model, dtype = self._lazy.get()
        chunk = samples[: int(_CHUNK_S * TARGET_SR)]
        with self._run_lock, torch.inference_mode():
            feats = proc(chunk, sampling_rate=TARGET_SR, return_tensors="pt").input_features
            code = self._detect(model, proc, feats.to(self.device, dtype=dtype))
        self._lazy.touch()
        return code

    @staticmethod
    def _detect(model, proc, feats) -> str:
        """Pick bn/en/hi by Whisper's language-id head; anything else → bn."""
        try:
            tok = proc.tokenizer
            ids = model.detect_language(feats)
            code = tok.decode(ids[0]).strip("<|>") if hasattr(ids, "__len__") else "bn"
        except Exception:
            return "bn"
        return code if code in SUPPORTED_LANGS else "bn"


class RoutedASR:
    """Bengali to the Bengali checkpoint; English and Hindi to a multilingual one.

    The Bengali fine-tune is far better on Bengali (see the evaluation) but has
    lost the other languages: given English speech it writes it out in Bengali
    letters. ``lang="auto"`` asks the multilingual model which language it is
    and routes accordingly. Each model loads only when its language is used.
    """

    def __init__(self, bengali: WhisperASR, multilingual: WhisperASR) -> None:
        self.bn = bengali
        self.multi = multilingual
        self.model_id = bengali.model_id

    def transcribe(self, samples: np.ndarray, lang: str | None) -> Transcript:
        if lang is None:
            lang = self.multi.detect(samples)
        backend = self.bn if lang == "bn" else self.multi
        return backend.transcribe(samples, lang)

    def status(self) -> dict:
        return {"model": self.bn.model_id, "bn": self.bn.status(), "en_hi": self.multi.status()}

    def maybe_unload_idle(self) -> bool:
        a = self.bn.maybe_unload_idle()
        b = self.multi.maybe_unload_idle()
        return a or b

    def unload(self) -> bool:
        a = self.bn.unload()
        b = self.multi.unload()
        return a or b
