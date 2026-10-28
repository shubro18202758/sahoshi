"""Text-to-speech for public advisories (Bengali, English, Hindi).

Backend: Svara-TTS v1 (Apache-2.0), an Orpheus-style model that writes SNAC
audio codes which the SNAC 24 kHz codec (MIT) turns into a waveform. Indic
Parler-TTS was the first choice; its weights are gated and were not granted
to this deployment (README "Models").

Svara takes a speaker id ("Bengali (Female)") plus an end-of-utterance style
tag. The house voice is the female speaker of the requested language with
the ``<clear>`` tag, which reads like a calm, steady announcement. Sampling
is seeded from the text hash, so one text always gives one waveform and the
on-disk cache is exact.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import tempfile
import threading
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from .audio import encode_wav
from .runtime import LazyModel

__all__ = [
    "Speech",
    "TTSBackend",
    "SvaraTTS",
    "SvaraLlamaTTS",
    "TTSCache",
    "split_sentences",
    "speaker_for",
    "LANG_NAMES",
    "PROMPT_FORMAT",
    "prompt_ids",
]

LANG_NAMES = {"bn": "Bengali", "en": "English (Indian)", "hi": "Hindi"}

# Svara-TTS token layout (Orpheus convention on the Llama-3.2 tokenizer).
_TOKENISER_LEN = 128256
START_OF_SPEECH = _TOKENISER_LEN + 1
END_OF_SPEECH = _TOKENISER_LEN + 2
START_OF_HUMAN = _TOKENISER_LEN + 3
END_OF_HUMAN = _TOKENISER_LEN + 4
START_OF_AI = _TOKENISER_LEN + 5
END_OF_AI = _TOKENISER_LEN + 6
AUDIO_TOKENS_START = _TOKENISER_LEN + 10
BOS = 128000
END_OF_TURN = 128009
SAMPLE_RATE = 24_000

_SENT_RE = re.compile(r"(?<=[।!?\.\n])\s+")


@dataclass(frozen=True)
class Speech:
    wav: bytes
    sample_rate: int
    seconds: float
    model: str
    voice: str
    cached: bool
    synth_seconds: float


class TTSBackend(Protocol):
    model_id: str

    def synthesize(self, text: str, lang: str, voice: str) -> tuple[np.ndarray, int]: ...

    def status(self) -> dict: ...

    def maybe_unload_idle(self) -> bool: ...


def speaker_for(lang: str, voice: str) -> str:
    gender = "Male" if voice == "male" else "Female"
    return f"{LANG_NAMES[lang]} ({gender})"


def split_sentences(text: str, max_chars: int = 220) -> list[str]:
    """Sentence-ish chunks (the model reads one chunk per generation)."""
    parts = [p.strip() for p in _SENT_RE.split(text.strip()) if p.strip()]
    out: list[str] = []
    for p in parts:
        while len(p) > max_chars:  # long run-on: break at the last comma/space
            cut = max(p.rfind(",", 0, max_chars), p.rfind("，", 0, max_chars), p.rfind(" ", 0, max_chars))
            cut = cut if cut > max_chars // 3 else max_chars
            out.append(p[:cut + 1].strip())
            p = p[cut + 1:].strip()
        if p:
            out.append(p)
    return out


# Bumped whenever the prompt layout changes, so cached audio is regenerated.
PROMPT_FORMAT = "orpheus-human-turn/2"


def prompt_ids(tok, text: str, speaker: str, style_tag: str = "") -> list[int]:
    """One human turn, as the model card's own demo builds it:

        <start-of-human> <bos> "Bengali (Female): text <clear>" <eot> <end-of-human>

    The model then writes <start-of-ai><start-of-speech> and the audio codes
    itself. (An earlier layout that pre-filled <start-of-ai><start-of-speech>
    and an <|audio|> marker made the model read the speaker label aloud —
    "Bengali …" — at the start of about one utterance in three.)
    """
    body = f"{speaker}: {text}"
    if style_tag:
        body = f"{body} {style_tag}"
    ids = tok(body, add_special_tokens=False).input_ids
    return [START_OF_HUMAN, BOS, *ids, END_OF_TURN, END_OF_HUMAN]


def codes_from_tokens(tokens: list[int]) -> list[int]:
    """Generated ids → raw SNAC codes (0..4095), whole 7-code frames only.

    Everything up to the last <start-of-speech> is dropped first.
    """
    if START_OF_SPEECH in tokens:
        tokens = tokens[len(tokens) - tokens[::-1].index(START_OF_SPEECH):]
    out: list[int] = []
    for t in tokens:
        if t == END_OF_SPEECH or t == END_OF_AI:
            break
        if t < AUDIO_TOKENS_START:
            continue
        code = t - AUDIO_TOKENS_START - (len(out) % 7) * 4096
        if 0 <= code < 4096:
            out.append(code)
    return out[: (len(out) // 7) * 7]


def redistribute(codes: list[int]) -> tuple[list[int], list[int], list[int]]:
    """Interleaved frames [c0,c1,c2,c3,c4,c5,c6] → SNAC's three code layers."""
    l0, l1, l2 = [], [], []
    for i in range(len(codes) // 7):
        f = codes[7 * i: 7 * i + 7]
        l0.append(f[0])
        l1 += [f[1], f[4]]
        l2 += [f[2], f[3], f[5], f[6]]
    return l0, l1, l2


class SvaraTTS:
    def __init__(self, model_id: str, codec_id: str, *, device: str = "cuda",
                 style_tag: str = "<clear>", seed: int = 1847,
                 min_free_gib: float = 12.0, idle_unload_s: float = 600) -> None:
        self.model_id = model_id
        self.codec_id = codec_id
        self.device = device
        self.style_tag = style_tag
        self.seed = seed
        self._run_lock = threading.Lock()
        self._lazy = LazyModel(
            f"tts:{model_id}", self._load, need_gib=8.0,
            min_free_gib=min_free_gib, idle_unload_s=idle_unload_s,
        )

    def _load(self):
        import torch
        from snac import SNAC
        from transformers import AutoModelForCausalLM, AutoTokenizer

        dtype = torch.bfloat16 if self.device.startswith("cuda") else torch.float32
        tok = AutoTokenizer.from_pretrained(self.model_id)
        model = AutoModelForCausalLM.from_pretrained(self.model_id, dtype=dtype).to(self.device).eval()
        codec = SNAC.from_pretrained(self.codec_id).eval().to(self.device)
        return tok, model, codec

    def status(self) -> dict:
        return {"model": self.model_id, "codec": self.codec_id, **self._lazy.status()}

    def maybe_unload_idle(self) -> bool:
        return self._lazy.maybe_unload_idle()

    def unload(self) -> bool:
        return self._lazy.unload()

    def _prompt_ids(self, tok, text: str, speaker: str) -> list[int]:
        return prompt_ids(tok, text, speaker, self.style_tag)

    def synthesize(self, text: str, lang: str, voice: str) -> tuple[np.ndarray, int]:
        import torch

        tok, model, codec = self._lazy.get()
        speaker = speaker_for(lang, voice)
        pieces: list[np.ndarray] = []
        gap = np.zeros(int(0.22 * SAMPLE_RATE), dtype=np.float32)
        with self._run_lock, torch.inference_mode():
            for sent in split_sentences(text):
                seed = self.seed ^ int(hashlib.sha256(f"{speaker}|{sent}".encode()).hexdigest()[:8], 16)
                torch.manual_seed(seed)
                ids = torch.tensor([self._prompt_ids(tok, sent, speaker)], device=self.device)
                # ~82 codes per second of speech; cap by text length (Bengali
                # reads at roughly 12-16 characters a second).
                budget = int(min(2400, max(280, len(sent) * 16)))
                out = model.generate(
                    ids,
                    attention_mask=torch.ones_like(ids),
                    max_new_tokens=budget,
                    do_sample=True,
                    temperature=0.6,
                    top_p=0.9,
                    repetition_penalty=1.1,
                    eos_token_id=END_OF_SPEECH,
                    pad_token_id=END_OF_AI,
                )
                gen = out[0, ids.shape[1]:].tolist()
                codes = codes_from_tokens(gen)
                if len(codes) < 7:
                    continue
                l0, l1, l2 = redistribute(codes)
                layers = [torch.tensor(l, dtype=torch.int32, device=self.device).unsqueeze(0)
                          for l in (l0, l1, l2)]
                wav = codec.decode(layers).squeeze().float().cpu().numpy()
                if pieces:
                    pieces.append(gap)
                pieces.append(wav.astype(np.float32))
        self._lazy.touch()
        if not pieces:
            raise RuntimeError("the TTS model produced no audio for this text")
        audio = np.concatenate(pieces)
        peak = float(np.max(np.abs(audio))) or 1.0
        return (audio / max(peak, 1.0) * 0.95).astype(np.float32), SAMPLE_RATE


class SvaraLlamaTTS:
    """Svara-TTS from a GGUF in llama.cpp; SNAC decoding stays in torch.

    Same prompt, same sampling, same output as :class:`SvaraTTS`, about three
    times faster on the GB10. The GGUF is a Q8_0 conversion of the
    published weights (``scripts/convert_svara_gguf.sh``).
    """

    def __init__(self, gguf: Path, tokenizer_id: str, codec_id: str, *, server_bin: Path,
                 port: int, manage: bool = True, url: str | None = None, device: str = "cuda",
                 style_tag: str = "<clear>", seed: int = 1847, min_free_gib: float = 12.0,
                 idle_unload_s: float = 600) -> None:
        from .llama import LlamaServer

        self.model_id = f"{tokenizer_id} (Q8_0 GGUF, llama.cpp)"
        self.tokenizer_id = tokenizer_id
        self.codec_id = codec_id
        self.device = device
        self.style_tag = style_tag
        self.seed = seed
        # stop on <end-of-speech>: the converted vocab marks <|eot_id|> as EOS
        self.server = LlamaServer(
            server_bin, gguf, port, ctx=4096, manage=manage, url=url,
            extra_args=("--override-kv", f"tokenizer.ggml.eos_token_id=int:{END_OF_SPEECH}"),
        )
        self._run_lock = threading.Lock()
        self._lazy = LazyModel(
            f"tts:{self.model_id}", self._load, need_gib=5.0,
            min_free_gib=min_free_gib, idle_unload_s=idle_unload_s,
        )

    def _load(self):
        from snac import SNAC
        from transformers import AutoTokenizer

        tok = AutoTokenizer.from_pretrained(self.tokenizer_id)
        codec = SNAC.from_pretrained(self.codec_id).eval().to(self.device)
        self.server.start()
        return tok, codec

    def status(self) -> dict:
        return {"model": self.model_id, "codec": self.codec_id, "backend": "llama.cpp",
                "server_running": self.server.running if self.server.manage else None,
                **self._lazy.status()}

    def maybe_unload_idle(self) -> bool:
        if self._lazy.maybe_unload_idle():
            self.server.stop()
            return True
        return False

    def unload(self) -> bool:
        self.server.stop()
        return self._lazy.unload()

    def synthesize(self, text: str, lang: str, voice: str) -> tuple[np.ndarray, int]:
        import torch

        tok, codec = self._lazy.get()
        if self.server.manage and not self.server.running:
            self.server.start()  # restarted after a crash or an external kill
        speaker = speaker_for(lang, voice)
        pieces: list[np.ndarray] = []
        gap = np.zeros(int(0.22 * SAMPLE_RATE), dtype=np.float32)
        with self._run_lock:
            for sent in split_sentences(text):
                seed = self.seed ^ int(hashlib.sha256(f"{speaker}|{sent}".encode()).hexdigest()[:8], 16)
                body = {
                    "prompt": prompt_ids(tok, sent, speaker, self.style_tag),
                    "n_predict": int(min(2400, max(280, len(sent) * 16))),
                    "temperature": 0.6, "top_p": 0.9, "repeat_penalty": 1.1,
                    "seed": seed, "return_tokens": True, "cache_prompt": False,
                }
                codes = codes_from_tokens(self.server.completion(body).get("tokens", []))
                if len(codes) < 7:
                    continue
                l0, l1, l2 = redistribute(codes)
                with torch.inference_mode():
                    layers = [torch.tensor(x, dtype=torch.int32, device=self.device).unsqueeze(0)
                              for x in (l0, l1, l2)]
                    wav = codec.decode(layers).squeeze().float().cpu().numpy()
                if pieces:
                    pieces.append(gap)
                pieces.append(wav.astype(np.float32))
        self._lazy.touch()
        if not pieces:
            raise RuntimeError("the TTS model produced no audio for this text")
        audio = np.concatenate(pieces)
        peak = float(np.max(np.abs(audio))) or 1.0
        return (audio / max(peak, 1.0) * 0.95).astype(np.float32), SAMPLE_RATE


class TTSCache:
    """wav files keyed by sha256(model | voice | style | lang | text)."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    @staticmethod
    def key(model: str, lang: str, voice: str, style: str, text: str) -> str:
        h = hashlib.sha256()
        for part in (model, lang, voice, style, text):
            h.update(part.encode("utf-8"))
            h.update(b"\x1f")
        return h.hexdigest()

    def _path(self, key: str) -> Path:
        return self.root / key[:2] / f"{key}.wav"

    def get(self, key: str) -> bytes | None:
        p = self._path(key)
        try:
            return p.read_bytes()
        except OSError:
            return None

    def put(self, key: str, data: bytes) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".part")
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, p)


def speak(backend: TTSBackend, cache: TTSCache, text: str, lang: str, voice: str,
          style: str) -> Speech:
    key = TTSCache.key(f"{backend.model_id}|{PROMPT_FORMAT}", lang, voice, style, text)
    hit = cache.get(key)
    if hit is not None:
        try:
            with wave.open(io.BytesIO(hit), "rb") as w:
                sr, n = w.getframerate(), w.getnframes()
            return Speech(hit, sr, round(n / sr, 2), backend.model_id, voice, True, 0.0)
        except (wave.Error, EOFError):
            pass  # a damaged cache file is regenerated below
    t0 = time.perf_counter()
    audio, sr = backend.synthesize(text, lang, voice)
    wav = encode_wav(audio, sr)
    cache.put(key, wav)
    return Speech(wav, sr, round(audio.size / sr, 2), backend.model_id, voice, False,
                  round(time.perf_counter() - t0, 3))
