"""The gazetteer protect-set: place phrases the redactor never mistakes for a person's name.

Built from the X19 gazetteer ``scripts/data/osint_gazetteer.json`` (``canonical_name`` with its parenthesised
parts, and every ``surface_forms`` entry), normalised exactly as ``osint_common.ethics`` normalises phrases (NFKC,
lower case, every run of non ``[a-z0-9]`` → one space), so the same set can be handed to
``ethics.pii_spans(protect=...)``.

Path: the argument, else ``$OSINT_GAZETTEER_PATH``, else the repo-rooted file (walking up from this module), else
the image path ``/repo/VVIP/scripts/data/osint_gazetteer.json``. A missing or malformed gazetteer gives the empty
set: protection then rests on the generic place words alone, which can only redact MORE, never less.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path

__all__ = ["GAZETTEER_ENV", "default_protect", "gazetteer_path", "load_protect", "norm_phrase"]

GAZETTEER_ENV = "OSINT_GAZETTEER_PATH"
_REPO_PARTS = ("scripts", "data", "osint_gazetteer.json")
_IMAGE_PATH = Path("/repo/VVIP/scripts/data/osint_gazetteer.json")
_MAX_BYTES = 8 * 1024 * 1024


def norm_phrase(s: str) -> str:
    """``"Science City (EM Bypass)"`` → ``"science city em bypass"`` (the ``osint_common.ethics`` rule)."""
    s = unicodedata.normalize("NFKC", str(s)).lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def gazetteer_path(explicit: str | os.PathLike[str] | None = None) -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.is_file() else None
    env = os.environ.get(GAZETTEER_ENV)
    if env:
        p = Path(env)
        return p if p.is_file() else None
    here = Path(__file__).resolve()
    for parent in here.parents:
        cand = parent.joinpath(*_REPO_PARTS)
        if cand.is_file():
            return cand
    return _IMAGE_PATH if _IMAGE_PATH.is_file() else None


def load_protect(path: str | os.PathLike[str] | None = None) -> frozenset[str]:
    """The normalised place phrases of the gazetteer at ``path`` (see :func:`gazetteer_path`); never raises."""
    p = gazetteer_path(path)
    if p is None:
        return frozenset()
    try:
        if p.stat().st_size > _MAX_BYTES:
            return frozenset()
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return frozenset()
    entries = doc.get("entries", []) if isinstance(doc, Mapping) else []
    out: set[str] = set()
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, Mapping):
            continue
        names: list[str] = []
        canon = entry.get("canonical_name")
        if isinstance(canon, str):
            names.append(canon)
            names.extend(part for part in re.split(r"[()]", canon) if part.strip())
        forms = entry.get("surface_forms")
        if isinstance(forms, list):
            names.extend(f for f in forms if isinstance(f, str))
        for name in names:
            phrase = norm_phrase(name[:200])
            if phrase:
                out.add(phrase)
    return frozenset(out)


@lru_cache(maxsize=4)
def default_protect(path: str | None = None) -> frozenset[str]:
    """:func:`load_protect`, cached per path (the gazetteer is read once per process)."""
    return load_protect(path)
