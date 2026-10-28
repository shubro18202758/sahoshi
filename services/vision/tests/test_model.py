"""Prompt, schema and llama-server lifecycle (no model is started here)."""

from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path

import pytest

from vision_service import model as model_mod
from vision_service.config import Settings
from vision_service.model import (
    DEPTH_BANDS,
    OUTPUT_SCHEMA,
    STATES,
    SYSTEM_PROMPT,
    LlamaServerManager,
    LlamaVisionModel,
    ModelUnavailable,
)


def test_system_prompt_restricts_to_roads_and_vehicles() -> None:
    p = SYSTEM_PROMPT.lower()
    assert "road" in p and "vehicles" in p
    for word in ("people", "faces", "clothing", "gender", "age", "ethnicity", "identity"):
        assert word in p, word
    assert "number plates" in p


def test_schema_only_allows_known_states_and_bands() -> None:
    props = OUTPUT_SCHEMA["properties"]
    assert props["state"]["enum"] == list(STATES)
    assert props["water_depth_band"]["enum"] == list(DEPTH_BANDS)
    assert OUTPUT_SCHEMA["additionalProperties"] is False
    assert set(props["vehicles_estimate"]["required"]) == {"cars", "buses", "two_wheelers", "autos"}
    # depth is judged against vehicles, never against a human body
    assert not any(w in " ".join(DEPTH_BANDS) for w in ("knee", "waist", "ankle", "chest"))


def test_payload_carries_image_prompt_and_schema() -> None:
    m = LlamaVisionModel(Settings(llm_manage=False))
    p = m._payload(b"\xff\xd8\xffJPEG", "Is the road open?")
    assert p["messages"][0] == {"role": "system", "content": SYSTEM_PROMPT}
    parts = p["messages"][1]["content"]
    url = parts[0]["image_url"]["url"]
    assert url.startswith("data:image/jpeg;base64,")
    assert base64.b64decode(url.split(",", 1)[1]) == b"\xff\xd8\xffJPEG"
    assert "Is the road open?" in parts[1]["text"]
    assert p["temperature"] == 0.0
    assert p["response_format"]["json_schema"]["schema"] == OUTPUT_SCHEMA


def test_manager_binds_loopback_and_loads_projector(tmp_path: Path) -> None:
    s = Settings(llm_port=9999)
    cmd = LlamaServerManager(s)._cmd()
    assert cmd[cmd.index("--host") + 1] == "127.0.0.1"
    assert cmd[cmd.index("--port") + 1] == "9999"
    assert "--mmproj" in cmd


def _files(tmp_path: Path) -> Settings:
    for n in ("llama-server", "m.gguf", "mm.gguf"):
        (tmp_path / n).write_bytes(b"x")
    return Settings(llama_server_bin=tmp_path / "llama-server", model_path=tmp_path / "m.gguf",
                    mmproj_path=tmp_path / "mm.gguf", need_gib=8, min_free_gib=12)


def test_manager_refuses_to_start_when_memory_is_low(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(model_mod, "_mem_available_gib", lambda: 15.0)
    started = []
    monkeypatch.setattr(model_mod.subprocess, "Popen", lambda *a, **k: started.append(a))
    mgr = LlamaServerManager(_files(tmp_path))
    with pytest.raises(ModelUnavailable, match="15.0 GiB available"):
        asyncio.run(mgr.ensure())
    assert started == []


def test_manager_reports_missing_weights(tmp_path: Path) -> None:
    s = Settings(model_path=tmp_path / "absent.gguf")
    with pytest.raises(ModelUnavailable, match="missing"):
        asyncio.run(LlamaServerManager(s).ensure())


def test_classify_parses_llama_server_json(monkeypatch) -> None:
    content = json.dumps({"state": "clear", "confidence": 0.9, "vehicles_estimate":
                          {"cars": 1, "buses": 0, "two_wheelers": 0, "autos": 0},
                          "water_depth_band": "none", "rationale": "Open road."})

    class Resp:
        status_code = 200
        text = ""

        def json(self):
            return {"choices": [{"message": {"content": content}}],
                    "timings": {"prompt_ms": 700.0, "predicted_ms": 2000.0}}

    class Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json):
            assert url.endswith("/v1/chat/completions")
            return Resp()

    monkeypatch.setattr(model_mod.httpx, "AsyncClient", Client)
    m = LlamaVisionModel(Settings(llm_manage=False, llm_url="http://127.0.0.1:1"))
    out = asyncio.run(m.classify(b"\xff\xd8\xff"))
    assert out["state"] == "clear"
    assert out["_timings"]["predicted_ms"] == 2000.0
