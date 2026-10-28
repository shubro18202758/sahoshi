"""Lazy model lifecycle shared by the ASR and TTS backends.

A model loads on its first request, stays warm while it is used and is
dropped after ``idle_unload_s`` seconds without a call. Before a load the
host's MemAvailable is checked (``/proc/meminfo``): below ``min_free_gib``
the load is refused with :class:`ModelUnavailable`, which the API turns into
a 503. The box is shared with other model servers and a memory guard, so a
refused load is the correct outcome, not an error to retry in a loop.
"""

from __future__ import annotations

import gc
import logging
import threading
import time
from typing import Any, Callable

__all__ = [
    "ModelUnavailable",
    "ModelNotProvisioned",
    "LazyModel",
    "mem_available_gib",
    "hf_page",
    "not_provisioned",
]

log = logging.getLogger("speech.runtime")


class ModelUnavailable(RuntimeError):
    """The model cannot be loaded right now (memory, missing weights)."""


class ModelNotProvisioned(ModelUnavailable):
    """The model cannot load until an operator acts: its gated weights were
    not granted or not downloaded, or a runtime package is missing. Unlike a
    memory refusal this does not clear by waiting, so a fallback backend may
    take over (see ``asr.FallbackASR`` / ``tts.FallbackTTS``)."""


def hf_page(repo: str) -> str:
    return f"https://huggingface.co/{repo}"


# Substrings of the errors transformers / huggingface_hub raise (older
# transformers wrap them in a plain OSError) when a repo is gated and not
# granted, or absent from the local cache in offline mode.
_GATED_HINTS = ("gated", "401 client error", "403 client error", "restricted",
                "awaiting a review", "not in the authorized list")
_NOT_CACHED_HINTS = (
    "offline", "couldn't connect", "cannot find the requested files", "not a local folder",
    "does not appear to have a file", "local_files_only", "no such file",
)


def not_provisioned(repo: str, exc: BaseException, *, gated: bool) -> ModelNotProvisioned | None:
    """Turn a load error into a clear :class:`ModelNotProvisioned`, or return
    ``None`` when it is something else (a CUDA error, a bug) that should stay
    loud. Never echoes a token: only the exception's type and message."""
    name = type(exc).__name__
    msg = str(exc)
    low = msg.lower()
    gate = f"gated: request access at {hf_page(repo)}" if gated else f"see {hf_page(repo)}"
    if isinstance(exc, ImportError):
        return ModelNotProvisioned(f"{repo}: a runtime package is missing ({msg[:160]}); {gate}")
    if name in ("GatedRepoError", "RepositoryNotFoundError") or (
            name == "HfHubHTTPError" and ("401" in msg or "403" in msg)) or (
            isinstance(exc, (OSError, ValueError)) and any(h in low for h in _GATED_HINTS)):
        return ModelNotProvisioned(
            f"{gate} with the deployment's Hugging Face account; the account has not been "
            f"granted access yet ({name})")
    if name in ("LocalEntryNotFoundError", "OfflineModeIsEnabled", "EntryNotFoundError") or (
            isinstance(exc, (OSError, ValueError)) and any(h in low for h in _NOT_CACHED_HINTS)):
        return ModelNotProvisioned(
            f"{repo}: weights are not in the local Hugging Face cache ({name}); {gate}, "
            f"then download them with scripts/fetch_gated_models.sh")
    return None


def mem_available_gib() -> float | None:
    try:
        with open("/proc/meminfo", encoding="ascii") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / (1024 * 1024)
    except OSError:
        return None
    return None


class LazyModel:
    """Holds one loaded object (or nothing) behind a lock."""

    def __init__(
        self,
        name: str,
        loader: Callable[[], Any],
        *,
        need_gib: float,
        min_free_gib: float,
        idle_unload_s: float,
        mem_probe: Callable[[], float | None] = mem_available_gib,
    ) -> None:
        self.name = name
        self._loader = loader
        self._need = need_gib
        self._min_free = min_free_gib
        self._idle = idle_unload_s
        self._probe = mem_probe
        self._obj: Any = None
        self._lock = threading.RLock()
        self._last_used = 0.0
        self.load_seconds: float | None = None
        self.last_error: str | None = None

    @property
    def loaded(self) -> bool:
        return self._obj is not None

    def get(self) -> Any:
        with self._lock:
            if self._obj is None:
                free = self._probe()
                if free is not None and free - self._need < self._min_free:
                    self.last_error = (
                        f"refused to load {self.name}: {free:.1f} GiB available, "
                        f"needs ~{self._need:.1f} GiB plus a {self._min_free:.0f} GiB floor"
                    )
                    raise ModelUnavailable(self.last_error)
                t0 = time.perf_counter()
                try:
                    self._obj = self._loader()
                except ModelUnavailable as exc:
                    self.last_error = str(exc)[:400]
                    raise
                except Exception as exc:  # weights missing, CUDA error, …
                    self.last_error = f"{type(exc).__name__}: {exc}"[:400]
                    log.exception("load failed: %s", self.name)
                    raise ModelUnavailable(self.last_error) from exc
                self.load_seconds = round(time.perf_counter() - t0, 2)
                self.last_error = None
                log.info("loaded %s in %.1fs", self.name, self.load_seconds)
            self._last_used = time.monotonic()
            return self._obj

    def touch(self) -> None:
        self._last_used = time.monotonic()

    def unload(self) -> bool:
        with self._lock:
            if self._obj is None:
                return False
            self._obj = None
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:  # torch absent in the offline test venv
            pass
        log.info("unloaded %s", self.name)
        return True

    def maybe_unload_idle(self) -> bool:
        if self._obj is None or self._idle <= 0:
            return False
        if time.monotonic() - self._last_used < self._idle:
            return False
        with self._lock:  # re-check under the lock: a request may be running
            if time.monotonic() - self._last_used < self._idle:
                return False
            return self.unload()

    def status(self) -> dict[str, Any]:
        return {
            "loaded": self.loaded,
            "load_seconds": self.load_seconds,
            "last_error": self.last_error,
        }
