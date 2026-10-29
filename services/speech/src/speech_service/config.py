"""Configuration for the speech service (environment prefix ``SPEECH_``).

Everything binds loopback by default. The production port is 8194; a dev run
picks its own port through ``SPEECH_PORT``.

Model ids are config, not code: the ASR and TTS backends load whatever the
environment names, lazily on the first request, and drop the weights again
after ``SPEECH_IDLE_UNLOAD_S`` seconds without a call (the box is shared).
Before a load the service checks MemAvailable and refuses (503) below
``SPEECH_MIN_FREE_GIB``, so it never pushes the host into the memory guard.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["Settings", "get_settings", "default_city_dir"]


def default_city_dir() -> Path:
    """``cities/kolkata`` of the repo checkout, or ``/app/cities/kolkata`` in
    the container (compose mounts the city pack read-only there)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        cand = parent / "cities" / "kolkata"
        if (cand / "landmarks.json").is_file():
            return cand
    return Path("/app/cities/kolkata")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SPEECH_", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8194

    # CORS: the deck reaches the service through its own proxy, so no browser
    # origin is allowed by default. Comma-separated http(s)://host[:port].
    deck_origins: str = ""

    # --- ASR -----------------------------------------------------------------
    # "whisper": the Whisper-family checkpoint ``asr_model`` answers Bengali.
    # "indic_conformer": AI4Bharat IndicConformer (gated on Hugging Face; see
    # docs/ai/speech.md "When access is granted") answers Bengali, and
    # ``asr_model`` takes over automatically while it cannot load.
    asr_backend: str = "whisper"
    # Whisper-family checkpoint (transformers): a whisper-medium fine-tuned on
    # Bengali (Apache-2.0). Chosen by the evaluation in eval/; see README
    # "Models" for the comparison and why not IndicConformer.
    asr_model: str = "bengaliAI/tugstugi_bengaliai-asr_whisper-medium"
    asr_indic_conformer_model: str = "ai4bharat/indic-conformer-600m-multilingual"
    asr_indic_conformer_decoder: str = "rnnt"  # or "ctc"
    # The model runs its own code (trust_remote_code): pin the commit whose
    # model_onnx.py was reviewed. Empty = the repo's main branch. The remote
    # code fetches its ONNX assets from main regardless, so the adapter refuses
    # assets from any commit other than this one.
    asr_indic_conformer_revision: str = ""
    # English and Hindi (and language detection for lang=auto) go to a general
    # multilingual Whisper: the Bengali fine-tune above transcribes them in
    # Bengali letters. MIT; fast; poor at Bengali, so it never gets bn audio.
    asr_multilingual_model: str = "openai/whisper-large-v3-turbo"
    asr_default_lang: str = "bn"
    asr_beams: int = 1

    # --- TTS -----------------------------------------------------------------
    # "auto": the llama.cpp GGUF backend when the GGUF and llama-server exist
    # (about 3x faster on the GB10), else transformers. Or force one of
    # "llama" / "transformers". "indic_parler": AI4Bharat Indic Parler-TTS
    # (gated), with Svara ("auto") taking over while it cannot load.
    tts_backend: str = "auto"
    tts_parler_model: str = "ai4bharat/indic-parler-tts"
    # Pin the commit that was evaluated (the fetch script prints it). Empty =
    # the repo's main branch (offline: whatever commit the cache holds).
    tts_parler_revision: str = ""
    # parler-tts pins transformers 4.46.1, so it runs in its own venv: the
    # python of that venv (empty = load it in this process instead).
    tts_parler_python: str = ""
    # Parler caption; {speaker} becomes the language's recommended voice.
    tts_parler_description: str = (
        "{speaker} speaks in a calm, clear and unhurried voice at a steady, moderate pace, "
        "reading a public traffic advisory. The recording is of very high quality, with the "
        "speaker's voice sounding clear and very close up, and no background noise."
    )
    tts_gguf: Path = Path.home() / ".cache" / "sahoshi" / "svara-gguf" / "svara-tts-v1-q8_0.gguf"
    llama_server_bin: Path = Path.home() / "llama.cpp" / "build" / "bin" / "llama-server"
    tts_llm_port: int = 8202
    tts_llm_manage: bool = True
    tts_llm_url: str = ""
    tts_model: str = "kenpath/svara-tts-v1"
    tts_codec: str = "hubertsiuzdak/snac_24khz"
    # Calm, clear, unhurried public-advisory voice. Svara-TTS takes a speaker
    # id ("Bengali (Female)") and an end-of-utterance style tag; this is the
    # house description of what the service asks it for.
    tts_voice_description: str = (
        "A calm, clear, unhurried female voice reading a public traffic "
        "advisory at a steady pace, close to the microphone, no background noise."
    )
    tts_default_voice: str = "female"
    tts_style_tag: str = "<clear>"
    tts_cache_dir: Path = Path.home() / ".cache" / "sahoshi" / "speech-tts"
    tts_max_chars: int = 600
    tts_seed: int = 1847

    # --- shared --------------------------------------------------------------
    device: str = "cuda"
    idle_unload_s: int = 600
    min_free_gib: float = 12.0
    max_audio_bytes: int = 8 * 1024 * 1024
    max_audio_seconds: float = 60.0
    city_dir: Path = default_city_dir()
    # Gazetteer from the events stream; optional (landmarks.json always loads).
    gazetteer_file: str = "gazetteer.json"
    place_threshold: float = 0.80


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
