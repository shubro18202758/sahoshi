"""PII span detection with PII-Tracer: a model check that runs alongside the OSINT rule redactor.

The OSINT ingress redacts person names at parse time with rules (cue words, honorifics, surnames, ages, and every
unknown Indic-script word withheld). Those rules stay primary. This module adds a learned detector the ingress may
consult as defence in depth: it can only ever ADD redactions, and it must never redact a public place, even one
named after a person ("Sarat Bose Road", "Rabindra Sarobar", "Netaji Subhas Chandra Bose International Airport").

Model: ``perplexity-ai/PII-Tracer`` (MIT; a ~600M bidirectional Qwen3 encoder with a 9-category BIOES token head
and a constrained Viterbi decoder). It ships its own model code (``modeling_pii_masking.py``), so it loads with
``trust_remote_code=True``. That file was read before use: it builds the stock ``Qwen3Model``, the two heads and
the decoder, and makes no network call or file write beyond normal loading. :data:`REVIEWED_CODE_SHA256` pins
that exact file and :data:`DEFAULT_REVISION` pins the snapshot; a different file is refused before it can run.
Loading is offline by default (``local_files_only=True``).

What :func:`postprocess` does to the raw model spans, in order:

1. **Word snapping.** The tokenizer is byte-level BPE, so on Bengali and Devanagari text a span can start or end
   inside a word (half a name). Every span is widened to whole words (letters, combining marks, ZWJ/ZWNJ).
2. **Plates and mobiles.** A span that is exactly a vehicle plate (``WB 02 AB 1234``; the model calls it
   ``account_number``) is relabelled ``vehicle_plate``: plates are masked by their own rule, not by name
   redaction. An ``account_number`` that is exactly an Indian mobile number is relabelled ``private_phone``.
3. **Short public numbers and letterless names.** A ``private_phone`` span with fewer than 7 digits (``112``,
   ``108``) is dropped: short codes are public services, never a private contact. A ``private_person`` span with
   no letter ("40" of "40 minutes") is dropped.
4. **Score and label filters.** Spans under ``min_score`` or outside ``labels`` are dropped.
5. **The protected-toponym guard** (:class:`ToponymGuard`). Each span is clipped against the protected place
   regions of its text, and a fragment left with no letter or digit is dropped. The regions are every occurrence
   of a protected multi-word place name (a Bengali or Hindi case ending allowed on its last word) and every run of
   name words that ends in a place word: up to six capitalised words before ``Road``, ``Avenue``, ``Sarani``,
   ``Street``, ``Setu``, ``Sarobar``, ``Lane``, ``metro`` (any case) or ``Park``, ``Bag``, ``Square``, ``Ghat``,
   ``Sadan``, ``Bhavan``, ``Airport``, ``Hospital`` ... (capitalised); up to three words before ``রোড``,
   ``অ্যাভিনিউ``, ``সরণি``, ``স্ট্রিট``, ``সেতু``, ``পার্ক``, ``সরোবর``, ``বাগ``, ``বিমানবন্দর`` ... or ``रोड``,
   ``एवेन्यू``, ``सरणी``, ``सेतु``, ``सरोवर``, ``बाग`` .... When a known place name ends where such a run ends, only
   the known name is taken. A single-word protected name ("Kalighat") removes a fragment only when the fragment is
   exactly that word, so a surname that is also a place word ("Hazra") still leaves the given name redacted. The
   guard only ever removes MODEL spans; the rule redactor's own spans are not this module's business.

The protected names default to the Kolkata landmarks file (``cities/kolkata/landmarks.json``, found by walking up
from this file; absent in an image, the guard still has its place-word rule) plus :data:`KOLKATA_EPONYMOUS_PLACES`,
the public places named after people that carry no place word ("Bagha Jatin", "Masterda Surya Sen"). Callers can
pass their own set.

Heavy imports (torch, transformers, huggingface_hub) happen inside :meth:`PiiTracerDetector._load`, so this module
imports with the standard library alone (the service gate has no torch). :class:`FakePiiDetector` is a
deterministic stand-in for tests.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

__all__ = [
    "DEFAULT_LABELS",
    "DEFAULT_MIN_SCORE",
    "DEFAULT_MODEL_ID",
    "DEFAULT_REVISION",
    "KOLKATA_EPONYMOUS_PLACES",
    "MODEL_LABELS",
    "PLATE_LABEL",
    "REVIEWED_CODE_SHA256",
    "FakePiiDetector",
    "PiiDetector",
    "PiiTracerDetector",
    "RawSpan",
    "ToponymGuard",
    "default_protected_names",
    "load_landmark_names",
    "postprocess",
    "snap_to_words",
]

DEFAULT_MODEL_ID = "perplexity-ai/PII-Tracer"
#: The snapshot whose model code was read (``modeling_pii_masking.py``).
DEFAULT_REVISION = "d25c16f2e57e321f6d2527715c01df9112f956f5"
#: SHA-256 of ``modeling_pii_masking.py`` at :data:`DEFAULT_REVISION`, the file that runs with trust_remote_code.
REVIEWED_CODE_SHA256 = "c43724b9ac105a9b74d44aea7565e4c43ddc9d203f519324baa342be01269869"
_MODEL_CODE_FILE = "modeling_pii_masking.py"

#: The model's nine categories.
MODEL_LABELS: tuple[str, ...] = (
    "private_person",
    "private_email",
    "private_phone",
    "private_address",
    "private_url",
    "private_date",
    "account_number",
    "secret",
    "other_pii",
)
#: Relabelled plate spans (see the module docstring, step 2).
PLATE_LABEL = "vehicle_plate"
#: What :meth:`PiiTracerDetector.detect` returns by default: names and private contacts. Addresses are left out
#: on purpose: the model calls public roads "private_address", and OSINT events are about places.
DEFAULT_LABELS: tuple[str, ...] = ("private_person", "private_email", "private_phone")
#: The span-score floor (the score is the sigmoid of the mean tag logit over the span's tokens).
DEFAULT_MIN_SCORE = 0.5

#: Chunking: texts longer than this are split at whitespace into pieces of at most this many characters, far
#: under the model's 4096-token window, and the spans are mapped back.
MAX_CHUNK_CHARS = 1500
#: A plate written the Indian way (``WB 02 AB 1234``, ``WB-06-K-5678``); the Kolkata format in city.json.
_PLATE_RE = re.compile(r"[A-Z]{2}[ -]?\d{1,2}[ -]?[A-Z]{0,3}[ -]?\d{1,4}")
#: An Indian mobile number (the model sometimes calls one "account_number").
_MOBILE_RE = re.compile(r"(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}")
_MIN_PHONE_DIGITS = 7

#: Public places named after people that carry no place word, so the place-word rule cannot see them. Public
#: toponyms only (metro stations, neighbourhoods), never a person. English, Bengali and Hindi spellings.
KOLKATA_EPONYMOUS_PLACES: tuple[str, ...] = (
    "Bagha Jatin", "Baghajatin", "বাঘাযতীন", "বাঘা যতীন", "बाघा जतिन",
    "Masterda Surya Sen", "মাস্টারদা সূর্য সেন", "मास्टरदा सूर्य सेन",
    "Mahanayak Uttam Kumar", "মহানায়ক উত্তমকুমার", "মহানায়ক উত্তম কুমার", "महानायक उत्तम कुमार",
    "Kavi Nazrul", "কবি নজরুল", "कवि नज़रुल",
    "Kavi Subhash", "কবি সুভাষ", "कवि सुभाष",
    "Shahid Khudiram", "শহিদ ক্ষুদিরাম", "शहीद खुदीराम",
    "Netaji Bhavan", "নেতাজি ভবন", "नेताजी भवन",
    "Rabindra Sadan", "রবীন্দ্র সদন", "रवींद्र सदन",
    "Rabindra Sarobar", "রবীন্দ্র সরোবর", "रवींद्र सरोवर",
    "Netaji Subhas Chandra Bose International Airport", "নেতাজি সুভাষচন্দ্র বসু আন্তর্জাতিক বিমানবন্দর",
    "नेताजी सुभाष चंद्र बोस अंतरराष्ट्रीय हवाई अड्डा",
    "Deshbandhu Park", "দেশবন্ধু পার্ক", "Jatin Das Park", "যতীন দাস পার্ক", "Girish Park", "গিরিশ পার্ক",
    "Acharya Jagadish Chandra Bose Road", "আচার্য জগদীশচন্দ্র বসু রোড", "AJC Bose Road",
    "Kazi Nazrul Islam Avenue", "কাজী নজরুল ইসলাম অ্যাভিনিউ", "काज़ी नज़रुल इस्लाम एवेन्यू",
    "Shyama Prasad Mukherjee Road", "শ্যামাপ্রসাদ মুখার্জি রোড",
    "Rani Rashmoni Avenue", "রানি রাসমণি অ্যাভিনিউ",
    "Mother Teresa Sarani", "মাদার টেরিজা সরণি",
)

# ── place words ──────────────────────────────────────────────────────────────────────────────────────────────────

#: Latin road words that end a road name in any case ("Sarat Bose Road", "Rashbehari avenue").
_LATIN_ROAD_WORDS = ("road", "rd", "avenue", "ave", "sarani", "sarobar", "street", "st", "setu", "lane", "metro")
#: Latin place words that end a place name only when capitalised ("Deshbandhu Park", "Netaji Subhas Chandra Bose
#: International Airport"): written in lower case they follow a name in ordinary speech ("<Name> hospital e").
#: Left out on purpose: "more" (মোড়; an ordinary English word), "place", "row" and "nagar" (also a surname).
_LATIN_PLACE_WORDS = (
    "Park", "Bag", "Square", "Ghat", "Bridge", "Crossing", "Station", "Airport", "Sadan", "Bhavan", "Bhawan",
    "Mancha", "Market", "Bazar", "Bazaar", "Stadium", "Hospital", "College", "Gardens", "Maidan", "Flyover",
    "Chowrasta", "Sarak", "Highway", "Bypass", "Expressway", "Terminus", "Depot",
)
#: Bengali and Hindi road and place words; a case ending may follow (রোডে, সরণিতে, পার্কের). Without capital
#: letters there is no telling a name from the words before it, so institution words that often follow a person
#: ("<name> হাসপাতালে ভর্তি", admitted to hospital) are left out: হাসপাতাল, স্টেশন, কলেজ, বাজার, মোড়, स्टेशन ...
#: (the landmark names still protect "SSKM Hospital", "Howrah Station", "Gariahat crossing").
_INDIC_PLACE_WORDS = (
    # Bengali
    "রোড", "অ্যাভিনিউ", "এভিনিউ", "অ্যাভেনিউ", "সরণি", "সরণী", "স্ট্রিট", "সেতু", "পার্ক", "সরোবর", "বাগ", "লেন",
    "স্কোয়্যার", "স্কোয়ার", "ঘাট", "ব্রিজ", "মেট্রো", "বিমানবন্দর", "সদন", "ভবন", "মঞ্চ", "উড়ালপুল", "বাইপাস",
    # Hindi
    "रोड", "एवेन्यू", "सरणी", "सरणि", "स्ट्रीट", "सेतु", "पार्क", "सरोवर", "बाग", "बाग़", "लेन", "स्क्वायर", "घाट",
    "ब्रिज", "मेट्रो", "हवाई", "सदन", "भवन", "बाईपास",
)
#: Name words before a place word that a region may take (Latin: capitalised words; Indic: any words, fewer).
_LATIN_RUN = 6
_INDIC_RUN = 3

_ZW = "‌‍"


def _is_word_char(ch: str) -> bool:
    return ch.isalnum() or ch in _ZW or unicodedata.category(ch)[0] == "M"


def _is_indic(ch: str) -> bool:
    return "ऀ" <= ch <= "ൿ"


@dataclass(frozen=True)
class RawSpan:
    """One model span before post-processing: ``text[start:end]`` is a ``label`` with ``score`` in [0, 1]."""

    start: int
    end: int
    label: str
    score: float = 1.0


def snap_to_words(text: str, start: int, end: int) -> tuple[int, int]:
    """``(start, end)`` widened to whole words, then trimmed of surrounding spaces and punctuation."""
    start, end = max(0, min(start, len(text))), max(0, min(end, len(text)))
    if start < end:
        if _is_word_char(text[start]):
            while start > 0 and _is_word_char(text[start - 1]):
                start -= 1
        if _is_word_char(text[end - 1]):
            while end < len(text) and _is_word_char(text[end]):
                end += 1
    while start < end and not _is_word_char(text[start]):
        start += 1
    while end > start and not _is_word_char(text[end - 1]):
        end -= 1
    return start, end


# ── the protected-toponym guard ──────────────────────────────────────────────────────────────────────────────────


def _same_word(word: str, name: str) -> bool:
    """``word`` (normalised) is ``name`` or, in an Indic script, ``name`` with a case ending (রোডে, সরোবরের) or in
    its oblique form (अड्डा → अड्डे): at most three more characters, the last character of ``name`` may change."""
    if word == name:
        return True
    if not _is_indic(word[:1]) or len(name) < 2 or len(word) - len(name) > 3:
        return False
    return word.startswith(name) or (len(name) >= 3 and word[: len(name) - 1] == name[:-1])


def _norm_key(s: str) -> str:
    """Comparison form of a name: NFC, Unicode format characters other than ZWJ/ZWNJ removed, case-folded, runs of
    space and punctuation as one space."""
    s = unicodedata.normalize("NFC", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Cf" or c in _ZW).casefold()
    return " ".join(re.sub(r"[^\wऀ-ൿ" + _ZW + r"]+", " ", s).split())


_CROSSING_TAIL = re.compile(
    r"\s+(?:five-point crossing|seven-point crossing|crossing|পাঁচ মাথার মোড়|সাত মাথার মোড়|মোড়|ক্রসিং"
    r"|पाँच-माथा मोड़|सात-माथा मोड़|क्रॉसिंग|मोड़)$"
)


def _name_variants(name: str) -> set[str]:
    """A landmark name and the shorter names it is written as: parts split at "," and parentheses, and the name
    without a trailing crossing word ("Gariahat crossing" → "Gariahat")."""
    out: set[str] = set()
    parts = [name] + [p for p in re.split(r"[(),]", name) if p.strip()]
    for p in parts:
        p = p.strip()
        if not p:
            continue
        out.add(p)
        cut = _CROSSING_TAIL.sub("", p).strip()
        if cut:
            out.add(cut)
    return out


def load_landmark_names(path: str | Path | None = None) -> frozenset[str]:
    """The place names of a landmarks file (``{"landmarks": [{"en":..., "bn":..., "hi":...}]}``) and their
    variants. ``path`` None: ``cities/kolkata/landmarks.json`` found by walking up from this file. Never raises:
    a missing or malformed file gives the empty set (the place-word rule still guards)."""
    p: Path | None
    if path is not None:
        p = Path(path)
    else:
        p = None
        for parent in Path(__file__).resolve().parents:
            cand = parent / "cities" / "kolkata" / "landmarks.json"
            if cand.is_file():
                p = cand
                break
    if p is None or not p.is_file():
        return frozenset()
    try:
        if p.stat().st_size > 4 * 1024 * 1024:
            return frozenset()
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return frozenset()
    out: set[str] = set()
    items = doc.get("landmarks", []) if isinstance(doc, Mapping) else []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, Mapping):
            continue
        for key in ("en", "bn", "hi"):
            v = item.get(key)
            if isinstance(v, str) and v.strip():
                out |= _name_variants(v[:200])
    return frozenset(out)


def default_protected_names(landmarks_path: str | Path | None = None) -> frozenset[str]:
    """Landmark names (:func:`load_landmark_names`) plus :data:`KOLKATA_EPONYMOUS_PLACES`."""
    return load_landmark_names(landmarks_path) | frozenset(KOLKATA_EPONYMOUS_PLACES)


class ToponymGuard:
    """Finds the protected place regions of a text and clips detector spans against them (module docstring)."""

    def __init__(self, protected: Iterable[str] | None = None, *, place_words: bool = True) -> None:
        names = default_protected_names() if protected is None else frozenset(protected)
        self.place_words = place_words
        multi: dict[str, list[str]] = {}
        single: set[str] = set()
        for n in names:
            k = _norm_key(n)
            if not k:
                continue
            if " " in k:
                multi.setdefault(k.split(" ", 1)[0], []).append(k)
            else:
                single.add(k)
        self._multi = {k: sorted(set(v), key=len, reverse=True) for k, v in multi.items()}
        self._single = frozenset(single)
        road = "|".join(sorted(_LATIN_ROAD_WORDS, key=len, reverse=True))
        place = "|".join(sorted(_LATIN_PLACE_WORDS, key=len, reverse=True))
        indic = "|".join(sorted(_INDIC_PLACE_WORDS, key=len, reverse=True))
        cap = r"[A-Z][\w'’.&-]*"
        any_case = rf"(?i:{road}|{place})"
        self._latin_re = re.compile(
            rf"(?<![\w])(?:{cap}\s+){{1,{_LATIN_RUN}}}(?:(?i:{road})|{place})\.?(?![\w])"
            rf"(?:\s+{any_case}(?![\w]))*"
        )
        iw = r"[ऀ-ൿ‌‍]+"
        self._indic_re = re.compile(
            rf"(?<![ऀ-ൿ‌‍])(?:{iw}[ \t]+){{1,{_INDIC_RUN}}}(?:{indic})[ऀ-ൿ‌‍]*"
            rf"(?:[ \t]+(?:{indic})[ऀ-ൿ‌‍]*)*"
        )

    @property
    def size(self) -> int:
        return len(self._single) + sum(len(v) for v in self._multi.values())

    def _words(self, text: str) -> list[tuple[int, int, str]]:
        out: list[tuple[int, int, str]] = []
        i, n = 0, len(text)
        while i < n:
            if not _is_word_char(text[i]):
                i += 1
                continue
            j = i + 1
            while j < n and _is_word_char(text[j]):
                j += 1
            out.append((i, j, _norm_key(text[i:j])))
            i = j
        return out

    def regions(self, text: str) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
        """``(multi_regions, single_word_places)``: character ranges of protected multi-word places and of
        protected single-word places in ``text``."""
        words = self._words(text)
        multi: list[tuple[int, int]] = []
        single: list[tuple[int, int]] = []
        keys = [w[2] for w in words]
        for i, (s, e, k) in enumerate(words):
            if k in self._single:
                single.append((s, e))
            for phrase in self._multi.get(k, ()):
                parts = phrase.split(" ")
                m = len(parts)
                if i + m > len(words):
                    continue
                ok = all(keys[i + t] == parts[t] for t in range(m - 1))
                ok = ok and _same_word(keys[i + m - 1], parts[-1])
                if ok:
                    multi.append((s, words[i + m - 1][1]))
                    break
        # a single-word Indic place with a case ending (কালীঘাটে) is still that place
        indic_single = [x for x in self._single if _is_indic(x[:1])]
        for s, e, k in words:
            if _is_indic(k[:1]) and k not in self._single and any(_same_word(k, x) for x in indic_single):
                single.append((s, e))
        if self.place_words:
            known_ends = {re_: rs for rs, re_ in multi}
            for rx in (self._latin_re, self._indic_re):
                for m in rx.finditer(text):
                    # a known place name that ends where the run ends is the place; the words before it in the
                    # run ("<Given> <Surname> Shyama Prasad Mukherjee Road") are not taken
                    if m.end() in known_ends and known_ends[m.end()] > m.start():
                        continue
                    multi.append((m.start(), m.end()))
        return multi, single

    def clip(self, text: str, start: int, end: int, regions: tuple[list[tuple[int, int]], list[tuple[int, int]]]
             | None = None) -> list[tuple[int, int]]:
        """The parts of ``text[start:end]`` outside every protected region, each trimmed to whole words; a part with
        no letter or digit, or one that is exactly a single-word protected place, is dropped."""
        multi, single = regions if regions is not None else self.regions(text)
        pieces = [(start, end)]
        for rs, re_ in multi:
            nxt: list[tuple[int, int]] = []
            for s, e in pieces:
                if re_ <= s or rs >= e:
                    nxt.append((s, e))
                    continue
                if s < rs:
                    nxt.append((s, rs))
                if re_ < e:
                    nxt.append((re_, e))
            pieces = nxt
        out: list[tuple[int, int]] = []
        singles = set(single)  # a fragment that is exactly a single-word place
        for s, e in pieces:
            s2, e2 = s, e
            while s2 < e2 and not _is_word_char(text[s2]):
                s2 += 1
            while e2 > s2 and not _is_word_char(text[e2 - 1]):
                e2 -= 1
            if e2 <= s2 or not any(c.isalnum() for c in text[s2:e2]):
                continue
            if (s2, e2) in singles:
                continue
            out.append((s2, e2))
        return out


# ── post-processing ──────────────────────────────────────────────────────────────────────────────────────────────


def postprocess(
    text: str,
    raw: Iterable[RawSpan],
    *,
    guard: ToponymGuard | None,
    labels: Iterable[str] | None = DEFAULT_LABELS,
    min_score: float = DEFAULT_MIN_SCORE,
) -> list[dict[str, Any]]:
    """Raw model spans → ``[{"start", "end", "label", "score"}]``, sorted and non-overlapping (module docstring,
    steps 1-5). ``labels`` None keeps every label; ``guard`` None skips the toponym guard (evaluation only)."""
    keep = None if labels is None else frozenset(labels)
    regions = guard.regions(text) if guard is not None else None
    spans: list[tuple[int, int, str, float]] = []
    for r in raw:
        s, e = snap_to_words(text, r.start, r.end)
        if e <= s:
            continue
        label = r.label
        frag = text[s:e]
        if _PLATE_RE.fullmatch(frag) and any(c.isdigit() for c in frag) and any(c.isalpha() for c in frag):
            label = PLATE_LABEL
        elif label == "account_number" and _MOBILE_RE.fullmatch(frag):
            label = "private_phone"
        if label == "private_phone" and sum(c.isdigit() for c in frag) < _MIN_PHONE_DIGITS:
            continue
        if label == "private_person" and not any(c.isalpha() for c in frag):
            continue  # "40 minutes": a name has letters
        if r.score < min_score or (keep is not None and label not in keep):
            continue
        parts = guard.clip(text, s, e, regions) if guard is not None else [(s, e)]
        spans.extend((ps, pe, label, r.score) for ps, pe in parts)
    spans.sort(key=lambda x: (x[0], -x[1]))
    out: list[dict[str, Any]] = []
    for s, e, label, score in spans:
        if out and s < out[-1]["end"]:
            last = out[-1]
            if e > last["end"]:
                last["end"] = e
            last["score"] = max(last["score"], round(score, 4))
            continue
        out.append({"start": s, "end": e, "label": label, "score": round(score, 4)})
    return out


def _chunks(text: str, limit: int = MAX_CHUNK_CHARS) -> list[tuple[int, str]]:
    """``text`` split at whitespace into ``(offset, piece)`` of at most ``limit`` characters."""
    if len(text) <= limit:
        return [(0, text)]
    out: list[tuple[int, str]] = []
    pos = 0
    while pos < len(text):
        end = min(len(text), pos + limit)
        if end < len(text):
            cut = text.rfind(" ", pos + limit // 2, end)
            end = cut if cut > pos else end
        out.append((pos, text[pos:end]))
        pos = end
    return out


# ── detectors ────────────────────────────────────────────────────────────────────────────────────────────────────


class PiiDetector(Protocol):
    """What the ``/pii/spans`` route needs: a name, the labels it returns, and ``detect``."""

    model_name: str
    labels: tuple[str, ...]

    def detect(self, texts: Sequence[str]) -> list[list[dict[str, Any]]]: ...


class _Base:
    model_name = "base"

    def __init__(
        self,
        *,
        labels: Iterable[str] = DEFAULT_LABELS,
        min_score: float = DEFAULT_MIN_SCORE,
        protected_names: Iterable[str] | None = None,
        guard: ToponymGuard | None = None,
    ) -> None:
        self.labels = tuple(labels)
        unknown = set(self.labels) - set(MODEL_LABELS) - {PLATE_LABEL}
        if unknown:
            raise ValueError(f"unknown labels: {sorted(unknown)}")
        if not 0.0 <= float(min_score) <= 1.0:
            raise ValueError("min_score must be within [0, 1]")
        self.min_score = float(min_score)
        self.guard = guard if guard is not None else ToponymGuard(protected_names)

    def raw_spans(self, texts: Sequence[str]) -> list[list[RawSpan]]:
        raise NotImplementedError

    def detect(self, texts: Sequence[str]) -> list[list[dict[str, Any]]]:
        """Spans per text: ``[{"start", "end", "label", "score"}]``, character offsets into each text as given."""
        texts = [t if isinstance(t, str) else "" for t in texts]
        raws = self.raw_spans(texts)
        return [
            postprocess(t, r, guard=self.guard, labels=self.labels, min_score=self.min_score)
            for t, r in zip(texts, raws, strict=True)
        ]


class FakePiiDetector(_Base):
    """Deterministic stand-in: every occurrence of a configured string is a raw span of its label (score 1.0, or
    the configured score), then the real post-processing runs. For tests; never loads a model."""

    model_name = "fake-pii"

    def __init__(self, patterns: Mapping[str, str | tuple[str, float]] | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.patterns: dict[str, tuple[str, float]] = {}
        for k, v in (patterns or {}).items():
            self.patterns[k] = (v, 1.0) if isinstance(v, str) else (v[0], float(v[1]))
        self.calls = 0

    def raw_spans(self, texts: Sequence[str]) -> list[list[RawSpan]]:
        self.calls += 1
        out: list[list[RawSpan]] = []
        for t in texts:
            spans: list[RawSpan] = []
            for needle, (label, score) in self.patterns.items():
                for m in re.finditer(re.escape(needle), t):
                    spans.append(RawSpan(m.start(), m.end(), label, score))
            out.append(spans)
        return out


class PiiTracerDetector(_Base):
    """PII-Tracer on the GPU (or CPU), loaded lazily on the first :meth:`detect` (or :meth:`load`)."""

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        *,
        revision: str | None = DEFAULT_REVISION,
        device: str | None = None,
        batch_size: int = 16,
        local_files_only: bool = True,
        code_sha256: str | None = REVIEWED_CODE_SHA256,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.model_id = model_id
        self.revision = revision
        self.device = device
        self.batch_size = max(1, int(batch_size))
        self.local_files_only = local_files_only
        self.code_sha256 = code_sha256
        self.model_name = f"{model_id}@{(revision or 'local')[:7]}"
        self._model: Any = None
        self._tokenizer: Any = None
        self._lock = threading.Lock()
        self.load_seconds: float | None = None

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def _code_path(self) -> Path:
        local = Path(self.model_id)
        if local.is_dir():
            return local / _MODEL_CODE_FILE
        from huggingface_hub import hf_hub_download  # lazy

        return Path(
            hf_hub_download(
                self.model_id, _MODEL_CODE_FILE, revision=self.revision, local_files_only=self.local_files_only
            )
        )

    def verify_code(self) -> None:
        """Refuse a model code file that is not the reviewed one (before anything imports it)."""
        if self.code_sha256 is None:
            return
        digest = hashlib.sha256(self._code_path().read_bytes()).hexdigest()
        if digest != self.code_sha256:
            raise RuntimeError(
                f"{_MODEL_CODE_FILE} does not match the reviewed file (sha256 {digest[:12]}…); refusing to run it"
            )

    def _load(self) -> None:
        import time

        t0 = time.perf_counter()
        self.verify_code()

        import torch  # lazy: the service gate has no torch
        from transformers import AutoModel

        device = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
        dtype = torch.bfloat16 if device.startswith("cuda") else torch.float32
        model = AutoModel.from_pretrained(
            self.model_id,
            trust_remote_code=True,
            revision=self.revision,
            local_files_only=self.local_files_only,
            dtype=dtype,
        )
        model = model.to(device).eval()
        self._tokenizer = model.tokenizer
        self._model = model
        self.device = device
        self.load_seconds = time.perf_counter() - t0

    def load(self) -> None:
        with self._lock:
            if self._model is None:
                self._load()

    def unload(self) -> None:
        """Drop the model (and free its GPU memory)."""
        with self._lock:
            self._model = None
            self._tokenizer = None
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:  # pragma: no cover
                pass

    def raw_spans(self, texts: Sequence[str]) -> list[list[RawSpan]]:
        self.load()
        pieces: list[tuple[int, int, str]] = []  # (text index, offset, chunk)
        for i, t in enumerate(texts):
            if t and t.strip():
                pieces.extend((i, off, c) for off, c in _chunks(t))
        out: list[list[RawSpan]] = [[] for _ in texts]
        order = sorted(range(len(pieces)), key=lambda k: len(pieces[k][2]))
        with self._lock:
            for b in range(0, len(order), self.batch_size):
                batch = [pieces[k] for k in order[b : b + self.batch_size]]
                for (i, off, _c), spans in zip(batch, self._infer([c for _i, _o, c in batch]), strict=True):
                    out[i].extend(RawSpan(s.start + off, s.end + off, s.label, s.score) for s in spans)
        return out

    def _infer(self, chunks: list[str]) -> list[list[RawSpan]]:
        import torch

        tok = self._tokenizer
        model = self._model
        enc = tok(
            chunks,
            return_offsets_mapping=True,
            return_tensors="pt",
            padding=True,
            padding_side="right",
            truncation=True,
            max_length=int(getattr(model.config, "max_seq_len", 4096)),
        )
        with torch.no_grad():
            res = model(
                input_ids=enc["input_ids"].to(model.device),
                attention_mask=enc["attention_mask"].to(model.device),
            )
        logits = res.logits.float().cpu()
        lengths = enc["attention_mask"].sum(dim=1).tolist()
        out: list[list[RawSpan]] = []
        for row, text in enumerate(chunks):
            n = int(lengths[row])
            if n == 0:
                out.append([])
                continue
            offsets = [tuple(o) for o in enc["offset_mapping"][row][:n].tolist()]
            spans = model.viterbi.decode(logits[row, :n], offsets, text=text)
            out.append([RawSpan(int(s.start), int(s.end), str(s.label), float(s.score)) for s in spans])
        return out
