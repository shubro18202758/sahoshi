"""What kind of road problem is the field report about, and how bad is it?

Rule based and explainable on purpose: an officer sees exactly which words
decided the label (``kind_cues`` / ``severity_cues``). Keywords are Bengali
(compared after the same spelling folding the place matcher uses), English
and common romanised Bengali.

Kinds: waterlogging | jam | accident | tree_fall | blockade | procession |
fire | live_wire | other.

A jam is usually a symptom. When a cause (water, a fallen tree, an accident
…) is also reported, the cause names the report and the jam only raises the
severity.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from difflib import SequenceMatcher

from .places import _bn_skeleton_word, _words, fold_bn

__all__ = ["KINDS", "SEVERITIES", "Classification", "classify"]

KINDS = (
    "waterlogging", "jam", "accident", "tree_fall", "blockade", "procession",
    "fire", "live_wire", "other",
)
SEVERITIES = ("low", "medium", "high")

# Tie-break order (most safety-critical first).
_PRIORITY = ("live_wire", "fire", "accident", "tree_fall", "waterlogging", "blockade",
             "procession", "jam")

# (term, weight). Bengali terms are matched as substrings of the folded text
# (they carry case endings); Latin terms are matched on word boundaries.
_TERMS: dict[str, list[tuple[str, int]]] = {
    "waterlogging": [
        ("জল জম", 3), ("জলজম", 3), ("জলমগ্ন", 3), ("জলে ডুব", 3), ("হাঁটু জল", 3), ("হাঁটুজল", 3),
        ("কোমর জল", 3), ("গোড়ালি জল", 3), ("বুক জল", 3), ("জল উঠে", 2), ("জল দাঁড়িয়ে", 2),
        ("জলবন্দি", 3), ("বন্যা", 2), ("ডুবে গেছে", 2), ("নিকাশি", 1), ("জল", 1), ("জলে", 1),
        ("waterlogging", 3), ("waterlogged", 3), ("water-logged", 3), ("water logging", 3),
        ("flooded", 3), ("flooding", 3), ("flood", 2), ("knee-deep", 3), ("knee deep", 3),
        ("waist-deep", 3), ("waist deep", 3), ("ankle-deep", 3), ("ankle deep", 3),
        ("inundated", 3), ("submerged", 3), ("standing water", 2), ("water", 1),
        ("jol jome", 3), ("jol jomeche", 3), ("hatu jol", 3), ("hantu jol", 3), ("komor jol", 3),
        ("jol", 1),
    ],
    "jam": [
        ("যানজট", 3), ("জ্যাম", 3), ("গাড়ি আটকে", 2), ("গাড়ির লম্বা লাইন", 3), ("লম্বা লাইন", 2),
        ("গাড়ি চলছে না", 2), ("গাড়ি নড়ছে না", 2), ("ধীর গতি", 1), ("ধীরে চলছে", 1),
        ("যান চলাচল ব্যাহত", 2), ("আটকে", 1), ("traffic jam", 3), ("jam", 3), ("jammed", 3),
        ("gridlock", 3), ("congestion", 3), ("congested", 3), ("standstill", 2), ("tailback", 2),
        ("backed up", 2), ("slow moving", 1), ("slow-moving", 1), ("stuck", 1), ("queue", 1),
        ("atke ache", 1), ("jaanjot", 3), ("janjot", 3),
    ],
    "accident": [
        ("দুর্ঘটনা", 3), ("অ্যাক্সিডেন্ট", 3), ("এক্সিডেন্ট", 3), ("সংঘর্ষ", 3), ("ধাক্কা", 2),
        ("উল্টে গেছে", 3), ("উল্টে", 2), ("পিষে", 2), ("accident", 3), ("collision", 3),
        ("collided", 3), ("crash", 3), ("crashed", 3), ("overturned", 3), ("pile-up", 3),
        ("hit by", 2), ("rammed", 2), ("dhakka", 2), ("ulte geche", 3),
    ],
    "tree_fall": [
        ("গাছ পড়ে", 3), ("গাছ ভেঙে", 3), ("গাছ উপড়ে", 3), ("উপড়ে পড়েছে", 3), ("গাছ পড়েছে", 3),
        ("ডাল ভেঙে", 2), ("গাছের ডাল", 2), ("গাছ", 1), ("tree fell", 3), ("fallen tree", 3),
        ("tree fall", 3), ("tree down", 3), ("uprooted", 3), ("tree has fallen", 3),
        ("branch", 1), ("tree", 1), ("gach poreche", 3), ("gach pore", 3), ("gach", 1),
    ],
    "blockade": [
        ("অবরোধ", 3), ("পথ অবরোধ", 3), ("রাস্তা অবরোধ", 3), ("ব্যারিকেড", 2), ("রাস্তা বন্ধ", 2),
        ("রাস্তা আটকে", 2), ("ধর্না", 2), ("blockade", 3), ("roadblock", 2), ("road block", 2),
        ("blocked", 2), ("barricade", 2), ("barricaded", 2), ("road closed", 2), ("sit-in", 2),
        ("oborodh", 3), ("aborodh", 3), ("rasta bondho", 2),
    ],
    "procession": [
        ("মিছিল", 3), ("শোভাযাত্রা", 3), ("র‍্যালি", 3), ("র্যালি", 3), ("বিসর্জন", 3),
        ("ভাসান", 3), ("নিরঞ্জন", 2), ("প্রতিমা", 1), ("procession", 3), ("rally", 3),
        ("immersion", 3), ("parade", 2), ("march", 1), ("michil", 3), ("bhasan", 3),
    ],
    "fire": [
        ("আগুন", 3), ("অগ্নিকাণ্ড", 3), ("দমকল", 2), ("ধোঁয়া", 2), ("পুড়ে", 2), ("fire", 3),
        ("blaze", 3), ("burning", 2), ("smoke", 2), ("agun", 3),
    ],
    "live_wire": [
        ("বিদ্যুতের তার", 3), ("বিদ্যুৎবাহী তার", 3), ("তার ছিঁড়ে", 3), ("ছেঁড়া তার", 3),
        ("খোলা তার", 3), ("তার পড়ে", 3), ("বিদ্যুৎস্পৃষ্ট", 3), ("কারেন্টের তার", 3), ("কারেন্ট", 2),
        ("ল্যাম্পপোস্ট", 2), ("live wire", 3), ("electric wire", 3), ("power line", 3),
        ("power cable", 3), ("snapped wire", 3), ("electrocuted", 3), ("electrocution", 3),
        ("lamp post", 2), ("lamppost", 2), ("current er tar", 3),
    ],
}

# Severity cues: (term, level). The highest level found wins; a low cue only
# lowers a default when nothing points higher.
_SEVERITY_CUES: list[tuple[str, str]] = [
    ("কোমর", "high"), ("বুক জল", "high"), ("গুরুতর", "high"), ("আহত", "high"), ("মৃত", "high"),
    ("পুরো রাস্তা বন্ধ", "high"), ("সম্পূর্ণ বন্ধ", "high"), ("অ্যাম্বুলেন্স আটকে", "high"),
    ("গাড়ি ডুবে", "high"), ("waist", "high"), ("chest", "high"), ("injured", "high"),
    ("serious", "high"), ("completely blocked", "high"), ("fully blocked", "high"),
    ("ambulance stuck", "high"), ("ambulance is stuck", "high"), ("submerged", "high"),
    ("হাঁটু", "medium"), ("বাস আটকে", "medium"), ("গাড়ি আটকে", "medium"), ("রাস্তা বন্ধ", "medium"),
    ("এক লেন", "medium"), ("প্রচণ্ড", "medium"), ("ভীষণ", "medium"), ("heavy", "medium"),
    ("massive", "medium"), ("huge", "medium"), ("অনেকক্ষণ", "medium"), ("knee", "medium"), ("bus stuck", "medium"),
    ("buses stuck", "medium"), ("one lane", "medium"), ("blocked", "medium"),
    ("গোড়ালি", "low"), ("সামান্য", "low"), ("একটু", "low"), ("ধীরে", "low"), ("ankle", "low"),
    ("slight", "low"), ("minor", "low"), ("slow", "low"),
]

_BASE = {
    "fire": "high", "live_wire": "high", "accident": "medium", "tree_fall": "medium",
    "waterlogging": "medium", "blockade": "medium", "procession": "low", "jam": "low",
    "other": "low",
}
_FLOOR = {"fire": "high", "live_wire": "high"}  # never reported below this

_LEVEL = {s: i for i, s in enumerate(SEVERITIES)}


def _is_latin(term: str) -> bool:
    return all(ord(c) < 0x0980 for c in term)


def _fold(text: str) -> str:
    return " ".join(fold_bn(text).lower().split())


_BN_NEG = re.compile(r"^\S*\s*(?:\S+\s+)?(?:নেই|নাই|নয়|নয়|নি)(?:$|[\s,।.!?])")
_EN_NEG = re.compile(r"(?:\bno|\bnot|\bwithout|\bzero)\s+(?:\w+\s+)?$")


def _hits(text_folded: str, term: str) -> bool | None:
    """True: present and not negated. False: present but only negated ("জল
    নেই", "no water", "not blocked"). None: absent."""
    if _is_latin(term):
        pat = rf"(?<![a-z]){re.escape(term)}(?![a-z])"
    else:
        # Bengali endings are suffixes, so a term must start a word (otherwise
        # "পুড়ে" = burnt would fire inside "খিদিরপুরে" = in Kidderpore).
        pat = rf"(?:^|(?<=[^\u0980-\u09ff])){re.escape(fold_bn(term))}"
    seen = False
    for m in re.finditer(pat, text_folded):
        seen = True
        before, after = text_folded[: m.start()], text_folded[m.end():]
        if _EN_NEG.search(before) or _BN_NEG.search(after):
            continue
        return True
    return False if seen else None


_NEG_WORDS = {fold_bn(w) for w in ("নেই", "নাই", "না", "নয়")}


def _fuzzy_hit(words: list[str], term: str) -> bool:
    """ASR-tolerant match for a strong Bengali cue ("যাঞ্জট", "যান জোট" for
    "যানজট"; "হাটপূজল" for "হাঁটু জল"): consonant skeletons of one- and
    two-word windows against the term's, same first consonant, ratio ≥ 0.85."""
    target = "".join(_bn_skeleton_word(w) for w in term.split())
    if len(target) < 4:
        return False
    for n in (1, 2):
        for i in range(len(words) - n + 1):
            win = words[i:i + n]
            nxt = words[i + n] if i + n < len(words) else ""
            if fold_bn(win[-1]).endswith(("নি", "না")) or fold_bn(nxt) in _NEG_WORDS:
                continue  # "জমেনি", "… নেই": negated
            cand = "".join(_bn_skeleton_word(w) for w in win)
            if len(cand) < 4 or cand[0] != target[0]:
                continue
            if cand == target or (len(target) >= 6
                                  and SequenceMatcher(None, cand, target).ratio() >= 0.85):
                return True
    return False


@dataclass(frozen=True)
class Classification:
    kind: str
    kind_cues: tuple[str, ...]
    severity: str
    severity_cues: tuple[str, ...]
    scores: dict[str, int]


def classify(text: str) -> Classification:
    t = _fold(text)
    scores: dict[str, int] = {}
    cues: dict[str, list[str]] = {}
    words = [w for w in _words(text) if any("\u0980" <= c <= "\u09ff" for c in w)]
    for kind, terms in _TERMS.items():
        found: list[str] = []
        total = 0
        for term, w in sorted(terms, key=lambda x: -len(x[0])):
            if any(fold_bn(term) in fold_bn(f) for f in found):
                continue
            hit = _hits(t, term)
            if hit:
                found.append(term)
                total += w
            elif hit is None and w >= 2 and not _is_latin(term) and _fuzzy_hit(words, term):
                found.append(term + " (≈)")  # close spelling, shown as such
                total += w - 1
        if total:
            scores[kind] = total
            cues[kind] = found
    jam = scores.get("jam", 0)
    if jam and any(scores.get(k, 0) >= 2 for k in _PRIORITY if k != "jam"):
        scores["jam"] = jam // 2  # a symptom of the reported cause
    if not scores or max(scores.values()) < 2:
        # a single weak word ("জল", "tree") is not enough to label the report
        kind = "other"
    else:
        best = max(scores.values())
        kind = next(k for k in _PRIORITY if scores.get(k, 0) == best)

    level = _BASE[kind]
    sev_found: list[str] = []
    top_cue = None
    for term, lv in _SEVERITY_CUES:
        if _hits(t, term):
            sev_found.append(term)
            if top_cue is None or _LEVEL[lv] > _LEVEL[top_cue]:
                top_cue = lv
    if top_cue == "high":
        level = "high"
    elif top_cue == "medium":
        level = SEVERITIES[max(_LEVEL[level], _LEVEL["medium"])]
    elif top_cue == "low" and kind not in _FLOOR:
        level = "low"
    if kind in ("waterlogging", "tree_fall", "accident", "blockade") and "jam" in cues \
            and level == "low":
        level = "medium"  # the cause is already stopping traffic
    if kind in _FLOOR:
        level = SEVERITIES[max(_LEVEL[level], _LEVEL[_FLOOR[kind]])]
    return Classification(
        kind=kind,
        kind_cues=tuple(cues.get(kind, ())),
        severity=level,
        severity_cues=tuple(sev_found),
        scores=dict(scores),
    )
