from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session")
def labels() -> list[dict]:
    return json.loads((FIXTURES / "labels.json").read_text(encoding="utf-8"))["images"]


@pytest.fixture(scope="session")
def jpeg_bytes() -> bytes:
    return (FIXTURES / "jam_esplanade.jpg").read_bytes()
