"""Lazy load, memory floor and idle unload."""

from __future__ import annotations

import pytest

from speech_service.runtime import LazyModel, ModelUnavailable


def test_loads_once_and_reuses() -> None:
    loads = []
    m = LazyModel("x", lambda: loads.append(1) or object(), need_gib=1, min_free_gib=1,
                  idle_unload_s=60, mem_probe=lambda: 100.0)
    a, b = m.get(), m.get()
    assert a is b and loads == [1] and m.loaded


def test_refuses_below_the_memory_floor() -> None:
    m = LazyModel("tts", object, need_gib=8, min_free_gib=12, idle_unload_s=60,
                  mem_probe=lambda: 15.0)
    with pytest.raises(ModelUnavailable, match="15.0 GiB available"):
        m.get()
    assert not m.loaded and "refused" in m.status()["last_error"]


def test_loader_failure_becomes_unavailable() -> None:
    def boom():
        raise OSError("weights missing")

    m = LazyModel("asr", boom, need_gib=1, min_free_gib=1, idle_unload_s=60, mem_probe=lambda: 99.0)
    with pytest.raises(ModelUnavailable, match="weights missing"):
        m.get()


def test_idle_unload() -> None:
    m = LazyModel("x", object, need_gib=1, min_free_gib=1, idle_unload_s=0.01,
                  mem_probe=lambda: 99.0)
    m.get()
    import time

    time.sleep(0.03)
    assert m.maybe_unload_idle() is True
    assert not m.loaded
    assert m.maybe_unload_idle() is False
