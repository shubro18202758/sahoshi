"""Configuration for the vision service (environment prefix ``VISION_``).

The service binds loopback (production port 8196). The vision-language model
runs in a llama.cpp ``llama-server`` with the Qwen3-VL projector loaded:

* ``VISION_LLM_MANAGE=1`` (default): the service starts its own
  llama-server on ``VISION_LLM_PORT`` at the first request, after checking
  MemAvailable, and stops it after ``VISION_IDLE_UNLOAD_S`` idle seconds.
* ``VISION_LLM_MANAGE=0``: it talks to an already-running server at
  ``VISION_LLM_URL`` (the compose layout, where the host runs the model).

Weights live in ``/home/sandy050405/models/qwen3-vl-8b/`` on the GB10 host.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["Settings", "get_settings"]

_MODELS = Path.home() / "models" / "qwen3-vl-8b"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VISION_", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8196
    deck_origins: str = ""

    # llama-server (Qwen3-VL-8B-Instruct GGUF + mmproj)
    llm_manage: bool = True
    llm_url: str = "http://127.0.0.1:8201"
    llm_port: int = 8201
    llama_server_bin: Path = Path.home() / "llama.cpp" / "build" / "bin" / "llama-server"
    model_path: Path = _MODELS / "Qwen3VL-8B-Instruct-Q4_K_M.gguf"
    mmproj_path: Path = _MODELS / "mmproj-Qwen3VL-8B-Instruct-F16.gguf"
    model_name: str = "Qwen3-VL-8B-Instruct (Q4_K_M GGUF, llama.cpp)"
    ctx_size: int = 8192
    gpu_layers: int = 99
    llm_start_timeout_s: float = 240.0
    llm_request_timeout_s: float = 180.0

    idle_unload_s: int = 600
    # Q4_K_M weights + F16 projector + KV cache ≈ 7.5 GiB; keep a floor on top
    need_gib: float = 8.0
    min_free_gib: float = 12.0

    max_image_bytes: int = 12 * 1024 * 1024
    max_side: int = 1024


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
