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

__all__ = ["ModelUnavailable", "LazyModel", "mem_available_gib"]

log = logging.getLogger("speech.runtime")


class ModelUnavailable(RuntimeError):
    """The model cannot be loaded right now (memory, missing weights)."""


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
                except ModelUnavailable:
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
