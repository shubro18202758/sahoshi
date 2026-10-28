"""Configuration from the environment (no secrets are read or needed).

SAHOSHI_TWIN_HOST        bind address (default 127.0.0.1: loopback only)
SAHOSHI_TWIN_PORT        port (default 8198, the Sahoshi twin port)
SAHOSHI_TWIN_NETWORK     network JSON (default: the City Pack's network.json)
SAHOSHI_TWIN_ORACLE_URL  traffic-oracle base URL for read-only GETs of the
                         live state (default http://127.0.0.1:8191; empty = off)
SAHOSHI_TWIN_LLM_URL     local OpenAI-compatible LLM (default http://127.0.0.1:8084)
SAHOSHI_TWIN_LLM         1/0: use the LLM for rationales (default 1)
SAHOSHI_TWIN_LLM_MODEL   optional model name sent to the LLM
"""

from __future__ import annotations

import os
from dataclasses import dataclass

_TRUTHY = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8198
    network_path: str | None = None
    oracle_url: str | None = "http://127.0.0.1:8191"
    llm_url: str | None = "http://127.0.0.1:8084"
    llm_enabled: bool = True
    llm_model: str | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        e = os.environ.get
        return cls(
            host=e("SAHOSHI_TWIN_HOST", "127.0.0.1"),
            port=int(e("SAHOSHI_TWIN_PORT", "8198")),
            network_path=e("SAHOSHI_TWIN_NETWORK") or None,
            oracle_url=e("SAHOSHI_TWIN_ORACLE_URL", "http://127.0.0.1:8191") or None,
            llm_url=e("SAHOSHI_TWIN_LLM_URL", "http://127.0.0.1:8084") or None,
            llm_enabled=e("SAHOSHI_TWIN_LLM", "1").strip().lower() in _TRUTHY,
            llm_model=e("SAHOSHI_TWIN_LLM_MODEL") or None,
        )
