"""The road-state model call: prompt, output schema, llama-server client.

The model answers through llama-server's OpenAI-compatible chat endpoint
with a JSON schema (grammar-constrained decoding), so the only free text it
can return is the short ``rationale`` — which then goes through
:func:`vision_service.ethics.scrub`.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import logging
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any, Protocol

import httpx

from .config import Settings

__all__ = [
    "STATES",
    "DEPTH_BANDS",
    "SYSTEM_PROMPT",
    "USER_PROMPT",
    "OUTPUT_SCHEMA",
    "RoadStateModel",
    "LlamaVisionModel",
    "LlamaServerManager",
    "ModelUnavailable",
]

log = logging.getLogger("vision.model")

STATES = ("waterlogged", "blocked", "tree_fall", "stalled_vehicle", "crash_debris", "congested",
          "clear", "unknown")
# Water depth, judged against vehicle wheels and kerbs (never against people).
DEPTH_BANDS = ("none", "below_kerb", "up_to_wheel_hub", "above_wheel_hub", "unknown")

SYSTEM_PROMPT = (
    "You are a road-condition classifier for a city traffic control room. You look at one "
    "camera still and report ONLY the condition of the road surface and the vehicles on it.\n"
    "Rules you must follow:\n"
    "1. Describe roads, water, trees, debris, barriers and vehicles only.\n"
    "2. Never describe, count or mention people: no persons, pedestrians, crowds, faces, "
    "bodies, clothing, gender, age, ethnicity, religion or identity. Treat people in the "
    "image as if they were not there.\n"
    "3. Never read or repeat number plates, signs with names, or any text that identifies "
    "a person or vehicle.\n"
    "4. Judge water depth against wheels and kerbs only.\n"
    "5. If the image does not show a road, answer state \"unknown\".\n"
    "Answer with the JSON object requested, nothing else."
)

USER_PROMPT = (
    "Classify the road state in this camera still.\n"
    "state — one of:\n"
    "  waterlogged: standing or flowing water covers the carriageway (including a flooded underpass);\n"
    "  blocked: the carriageway is closed or obstructed by barricades, construction or objects;\n"
    "  tree_fall: a fallen tree or large branches lie on or across the road;\n"
    "  stalled_vehicle: a broken-down or stopped bus/truck/car occupies the carriageway;\n"
    "  crash_debris: wreckage or debris from a collision is on the road;\n"
    "  congested: dense, queued, slow traffic with no other obstruction visible;\n"
    "  clear: the road is open and traffic is light or moderate;\n"
    "  unknown: the image does not let you decide.\n"
    "confidence — 0.0 to 1.0.\n"
    "vehicles_estimate — rough counts of visible cars (including taxis), buses (including "
    "trucks and vans), two_wheelers and autos (auto-rickshaws and e-rickshaws).\n"
    "water_depth_band — none | below_kerb | up_to_wheel_hub | above_wheel_hub | unknown.\n"
    "rationale — at most 25 words about the road and vehicles only."
)

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "state": {"type": "string", "enum": list(STATES)},
        "confidence": {"type": "number"},
        "vehicles_estimate": {
            "type": "object",
            "properties": {k: {"type": "integer"} for k in ("cars", "buses", "two_wheelers", "autos")},
            "required": ["cars", "buses", "two_wheelers", "autos"],
            "additionalProperties": False,
        },
        "water_depth_band": {"type": "string", "enum": list(DEPTH_BANDS)},
        "rationale": {"type": "string", "maxLength": 220},
    },
    "required": ["state", "confidence", "vehicles_estimate", "water_depth_band", "rationale"],
    "additionalProperties": False,
}


class ModelUnavailable(RuntimeError):
    """The vision model cannot run right now (memory, weights, server)."""


class RoadStateModel(Protocol):
    name: str

    async def classify(self, image_jpeg: bytes, question: str | None = None) -> dict[str, Any]: ...

    def status(self) -> dict[str, Any]: ...

    async def maybe_stop_idle(self) -> bool: ...

    async def aclose(self) -> None: ...


def _mem_available_gib() -> float | None:
    try:
        with open("/proc/meminfo", encoding="ascii") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / (1024 * 1024)
    except OSError:
        return None
    return None


class LlamaServerManager:
    """Starts and stops one llama-server child process for the VL model."""

    def __init__(self, s: Settings) -> None:
        self.s = s
        self._proc: subprocess.Popen[bytes] | None = None
        self._lock = asyncio.Lock()
        self.started_at: float | None = None
        self.start_seconds: float | None = None
        self.last_error: str | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.s.llm_port}"

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def _cmd(self) -> list[str]:
        s = self.s
        return [
            str(s.llama_server_bin), "-m", str(s.model_path), "--mmproj", str(s.mmproj_path),
            "--host", "127.0.0.1", "--port", str(s.llm_port), "-c", str(s.ctx_size),
            "-ngl", str(s.gpu_layers), "-np", "1", "--jinja", "--no-webui",
        ]

    async def ensure(self) -> str:
        async with self._lock:
            if self.running:
                return self.url
            for p in (self.s.llama_server_bin, self.s.model_path, self.s.mmproj_path):
                if not Path(p).exists():
                    self.last_error = f"missing: {p}"
                    raise ModelUnavailable(self.last_error)
            free = _mem_available_gib()
            if free is not None and free - self.s.need_gib < self.s.min_free_gib:
                self.last_error = (f"refused to start the vision model: {free:.1f} GiB available, "
                                   f"needs ~{self.s.need_gib:.0f} GiB plus a "
                                   f"{self.s.min_free_gib:.0f} GiB floor")
                raise ModelUnavailable(self.last_error)
            t0 = time.perf_counter()
            log.info("starting llama-server on :%s", self.s.llm_port)
            self._proc = subprocess.Popen(  # noqa: S603 - fixed argv from config
                self._cmd(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            deadline = time.monotonic() + self.s.llm_start_timeout_s
            async with httpx.AsyncClient(timeout=5.0) as c:
                while time.monotonic() < deadline:
                    if self._proc.poll() is not None:
                        self.last_error = f"llama-server exited with {self._proc.returncode}"
                        self._proc = None
                        raise ModelUnavailable(self.last_error)
                    with contextlib.suppress(httpx.HTTPError):
                        r = await c.get(self.url + "/health")
                        if r.status_code == 200:
                            self.start_seconds = round(time.perf_counter() - t0, 1)
                            self.started_at = time.time()
                            self.last_error = None
                            return self.url
                    await asyncio.sleep(1.0)
            await self.stop()
            self.last_error = "llama-server did not become healthy in time"
            raise ModelUnavailable(self.last_error)

    async def stop(self) -> bool:
        proc, self._proc = self._proc, None
        if proc is None or proc.poll() is not None:
            return False
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGTERM)
        for _ in range(50):
            if proc.poll() is not None:
                break
            await asyncio.sleep(0.2)
        else:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
        log.info("stopped llama-server")
        return True


class LlamaVisionModel:
    """Qwen3-VL through llama-server's /v1/chat/completions."""

    def __init__(self, s: Settings) -> None:
        self.s = s
        self.name = s.model_name
        self.manager = LlamaServerManager(s) if s.llm_manage else None
        self._last_used = 0.0
        self._busy = 0

    async def _base_url(self) -> str:
        if self.manager is not None:
            return await self.manager.ensure()
        return self.s.llm_url.rstrip("/")

    def _payload(self, image_jpeg: bytes, question: str | None) -> dict[str, Any]:
        b64 = base64.b64encode(image_jpeg).decode("ascii")
        text = USER_PROMPT
        if question:
            text += ("\nThe operator also asks (answer only about the road and vehicles, inside "
                     "the rationale): " + question[:300])
        return {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": text},
                ]},
            ],
            "temperature": 0.0,
            "max_tokens": 300,
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": "road_state", "schema": OUTPUT_SCHEMA}},
        }

    async def classify(self, image_jpeg: bytes, question: str | None = None) -> dict[str, Any]:
        self._busy += 1
        try:
            base = await self._base_url()
            async with httpx.AsyncClient(timeout=self.s.llm_request_timeout_s) as c:
                try:
                    r = await c.post(base + "/v1/chat/completions",
                                     json=self._payload(image_jpeg, question))
                except httpx.HTTPError as exc:
                    raise ModelUnavailable(f"vision model unreachable: {exc}") from exc
            if r.status_code != 200:
                raise ModelUnavailable(f"vision model error {r.status_code}: {r.text[:200]}")
            body = r.json()
            content = body["choices"][0]["message"].get("content") or ""
            try:
                out = json.loads(content)
            except ValueError as exc:
                raise ModelUnavailable("vision model returned no JSON") from exc
            out["_usage"] = body.get("usage", {})
            out["_timings"] = body.get("timings", {})
            return out
        finally:
            self._busy -= 1
            self._last_used = time.monotonic()

    def status(self) -> dict[str, Any]:
        m = self.manager
        return {
            "model": self.name,
            "managed": m is not None,
            "running": m.running if m else None,
            "url": m.url if m else self.s.llm_url,
            "start_seconds": m.start_seconds if m else None,
            "last_error": m.last_error if m else None,
        }

    async def maybe_stop_idle(self) -> bool:
        if self.manager is None or not self.manager.running or self._busy:
            return False
        if time.monotonic() - self._last_used < self.s.idle_unload_s:
            return False
        return await self.manager.stop()

    async def aclose(self) -> None:
        if self.manager is not None:
            await self.manager.stop()
