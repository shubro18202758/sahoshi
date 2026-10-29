"""What an OSINT item may be about: roads, crowds, weather, hazards, closures and services. Nothing else.

Events are about PLACES and ROAD SITUATIONS, never persons, never crime incidents, and nothing political. This
module is the deterministic scope gate every stage shares (no model, no network, no state):

* :func:`screen` reads a signal's (already redacted) title and text and answers one :class:`Screen`:

  - ``reason="crime"`` — a person-crime report (a theft, a robbery, an assault, an arrest, a case, a death that is
    not a road accident): dropped;
  - ``reason="conflict"`` — a clash between groups, a riot, vandalism, bombs, stone-pelting: dropped;
  - ``reason="political"`` — elections, polls, votes, candidates, party workers, political framing: dropped,
    UNLESS the item is a procession, rally or gathering that bears on a road (a road, traffic, a blockade, a
    diversion …): then it is KEPT as a crowd or closure situation, with every political term replaced by
    ``[WITHHELD]`` (``masked`` counts them), so only the place and the road impact remain;
  - ``reason=None`` — in scope (the title and text come back unchanged unless political terms were withheld).

* :func:`screen_class` refuses the classifier classes that are out of scope whatever the wording:
  ``reported_crime`` (crime), ``public_conflict`` (conflict) and ``unrest`` (political: protests, bandhs, strikes,
  gheraos). The other classes (road accidents, fires, flooding, infrastructure failures, hazards, public
  gatherings, processions, road closures, weather) are the scope.

The cue lists are English, Bengali and Hindi words. They name kinds of situation only: no person, and no party or
organisation name (party names are never written in Sahoshi; generic political words carry the rule). Bengali and
Devanagari cues match as substrings (they inflect by suffix: ভোটের, ভোট-পরবর্তী); Latin cues match whole words.
A cue list is a floor, not a guarantee: an unforeseen wording can pass, which is why the classifier's classes are
screened again after classification (:func:`screen_class`) and the oracle re-screens what it stores.

Callers count each reason and log the counts only; the text of a dropped item is never logged or stored.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

__all__ = [
    "OUT_OF_SCOPE_CLASSES",
    "PARTY_HASHES",
    "REASONS",
    "WITHHELD",
    "Screen",
    "screen",
    "screen_class",
]

#: The token that replaces a political term in a kept item (the redactor's own withheld token).
WITHHELD = "[WITHHELD]"

#: The drop reasons, in the order they are tested.
REASONS: tuple[str, ...] = ("crime", "conflict", "political")

#: Classifier classes that are out of scope, with their reason.
OUT_OF_SCOPE_CLASSES: dict[str, str] = {
    "reported_crime": "crime",
    "public_conflict": "conflict",
    "unrest": "political",
}

# ── cue lists ─────────────────────────────────────────────────────────────────────────────────────────────────────

_CRIME_LATIN = (
    r"murder(?:ed|s)?", r"robbery", r"robbed", r"robbers?", r"theft", r"thie(?:f|ves)", r"stolen",
    r"snatch(?:ing|ed|er|ers)?", r"loot(?:ed|ing)?", r"dacoity", r"burglary", r"burglars?", r"rape[ds]?",
    r"molest(?:ed|ation)?", r"assault(?:ed)?", r"stabb(?:ed|ing)", r"shot\s+dead", r"arrest(?:ed|s)?",
    r"abduct(?:ed|ion)?", r"kidnap(?:ped|ping)?", r"extortion", r"fraud", r"scam", r"smuggl(?:ing|ed|ers?)",
    r"drug\s+(?:peddl\w*|racket|seizure|haul)", r"accused", r"chargesheet", r"custody", r"suicide",
    r"dead\s+body", r"lynch(?:ed|ing)?", r"fir\s+(?:lodged|filed|registered)", r"police\s+case",
)
_CRIME_INDIC = (
    # Bengali: murder, killing, snatching, dacoity, theft, loot, rape, molestation, arrest (two spellings),
    # abduction, fraud, extortion, a (court/police) case, accused, suicide, drugs, smuggling, hacked, dead body
    "খুন", "হত্যা", "ছিনতাই", "ডাকাতি", "চুরি", "লুট", "ধর্ষণ", "শ্লীলতাহানি", "গ্রেফতার", "গ্রেপ্তার",
    "অপহরণ", "প্রতারণা", "তোলাবাজি", "মামলা", "অভিযুক্ত", "আত্মহত্যা", "মাদক", "পাচার", "কুপিয়ে", "মৃতদেহ",
    # Hindi: murder, loot, theft, dacoity, rape, molestation, arrest, abduction, cheating, fraud, suicide,
    # smuggling, accused
    "हत्या", "लूट", "चोरी", "डकैती", "बलात्कार", "छेड़छाड़", "गिरफ्तार", "अपहरण", "ठगी", "धोखाधड़ी",
    "आत्महत्या", "तस्करी", "आरोपी",
)
_CONFLICT_LATIN = (
    r"clash(?:es|ed)?", r"scuffles?", r"brawls?", r"riots?", r"rioting", r"mobs?", r"violence", r"violent",
    r"stone[- ]?pelting", r"pelted\s+stones", r"bomb(?:s|ing|ed|ings)?", r"crude\s+bombs?", r"lathi[- ]?charge[d]?",
    r"tear\s+gas", r"communal", r"vandal(?:ism|ised|ized)", r"ransack(?:ed)?", r"group\s+fight", r"turf\s+war",
)
_CONFLICT_INDIC = (
    # Bengali: fight, scuffle, violence/unrest, attack, bomb, stone-pelting, vandalism, baton charge, tear gas,
    # communal, riot (সংঘর্ষ, "clash" and also "collision", is read in context: see _BN_CLASH)
    "মারপিট", "হাতাহাতি", "অশান্তি", "হামলা", "বোমা", "ইটবৃষ্টি", "ভাঙচুর", "লাঠিচার্জ",
    "কাঁদানে গ্যাস", "সাম্প্রদায়িক", "দাঙ্গা",
    # Hindi: clash, fight, violence, riot, stone-pelting, bombing, vandalism, baton charge, communal, attack
    "झड़प", "मारपीट", "हिंसा", "दंगा", "पथराव", "बमबाजी", "तोड़फोड़", "लाठीचार्ज", "सांप्रदायिक", "हमला",
)
_POLITICAL_LATIN = (
    r"elections?", r"electoral", r"pre-?polls?", r"post-?polls?", r"by-?polls?", r"polls?", r"polling",
    r"votes?", r"voters?", r"voting", r"ballots?", r"evms?", r"candidates?", r"manifesto", r"mlas?",
    r"councillors?", r"political", r"politics", r"party\s+(?:workers?|supporters?|office|flags?|activists?)",
    r"(?:ruling|opposition)\s+party", r"lok\s+sabha", r"vidhan\s+sabha", r"assembly\s+(?:polls?|elections?|seat)",
)
_POLITICAL_INDIC = (
    # Bengali: vote, election, by-election, voter, candidate, political, politics, MLA, MP, councillor,
    # party (adj.), party workers, workers-supporters, manifesto (two spellings)
    "ভোট", "নির্বাচন", "উপনির্বাচন", "ভোটার", "প্রার্থী", "রাজনৈতিক", "রাজনীতি", "বিধায়ক", "সাংসদ", "কাউন্সিলর",
    "দলীয়", "দলের কর্মী", "কর্মী-সমর্থক", "ইস্তাহার", "ইস্তেহার",
    # Hindi: election, electoral, by-election, polling, voter, vote, candidate (two words), political, politics,
    # MLA, MP, party worker
    "चुनाव", "चुनावी", "उपचुनाव", "मतदान", "मतदाता", "वोट", "प्रत्याशी", "उम्मीदवार", "राजनीतिक", "राजनीति",
    "विधायक", "सांसद", "पार्टी कार्यकर्ता",
)
#: সংঘর্ষ means a clash between groups AND a collision of vehicles: it is a conflict cue only when the text names no
#: vehicle and no accident (two trains, a bus and a lorry: a collision, in scope).
_BN_CLASH = "সংঘর্ষ"
_BN_COLLISION_CONTEXT = re.compile(
    "|".join(("দুর্ঘটনা", "ট্রেন", "বাস", "লরি", "ট্রাক", "গাড়ি", "অটো", "ট্যাক্সি", "বাইক", "ট্রাম", "টোটো", "ডাম্পার"))
)
#: The item bears on a road: a road, traffic, a jam, a blockade, a diversion, a closure, a bridge, a crossing.
_ROAD_LATIN = (
    r"roads?", r"traffic", r"jams?", r"congestion", r"block(?:ed|ade|s)?", r"diver(?:ted|sion|sions)",
    r"closed", r"closures?", r"snarls?", r"gridlock", r"routes?", r"bridge", r"flyover", r"crossing",
    r"junction", r"lanes?", r"street", r"avenue", r"sarani", r"bypass",
)
_ROAD_INDIC = (
    "রাস্তা", "যানজট", "যান চলাচল", "ট্রাফিক", "অবরোধ", "বন্ধ", "ডাইভারশন", "মোড়", "সেতু", "উড়ালপুল", "সরণি",
    "सड़क", "जाम", "यातायात", "ट्रैफिक", "रास्ता", "बंद", "डायवर्जन", "पुल",
)
#: The item is a procession, rally or gathering (what may stay as a crowd or closure situation).
_GATHERING_LATIN = (
    r"rall(?:y|ies)", r"processions?", r"march(?:es)?", r"gatherings?", r"meetings?", r"sabha", r"crowds?",
    r"road\s*show", r"padayatra",
)
_GATHERING_INDIC = (
    "মিছিল", "শোভাযাত্রা", "সমাবেশ", "সভা", "জমায়েত", "ভিড়", "পদযাত্রা",
    "जुलूस", "रैली", "सभा", "भीड़", "पदयात्रा", "शोभायात्रा",
)


#: Party and alliance names, as the first 16 hex digits of the sha256 of the lower-cased name (English, Bengali,
#: Hindi spellings). Sahoshi never writes a party name, so the names are not in the code: a token (or a two-token
#: phrase), lower-cased and with a Bengali or Hindi case ending removed, is hashed and compared. 33 entries.
PARTY_HASHES: frozenset[str] = frozenset(
    {
        "04659f8c11a191a5", "05bf04e1b9d2031b", "0cf6c2d4d5bab184", "1ce13fddac42678d", "27abb1b53f5c1b18",
        "2aa06032916689ee", "37da2aaa62ddb81e", "3b03a55dae38bfc9", "3db20e1df89a35ea", "3e56afe2f7d17f99",
        "5d2ada361b47f841", "6d4bff5a3b571fdf", "76ccd86e21024ff1", "7994a6e44c8b9435", "8812dc09d23c42a4",
        "8a3133f3b53bc0ce", "93080e35013dc52a", "964d239474dadebf", "9a97a5ed5d7edc5b", "a20b7e8771ab206a",
        "b762ee284fc2ae29", "b89c226c1ec0c733", "b97418704ea22e11", "bb43fd4e43cb8440", "bca574d78d6318f3",
        "c5bd916598d5e4b6", "c7a5346f8a6b1c63", "c9c61db581934f1d", "ca6e3462ca9f9424", "cbfe0ad179dd2d1c",
        "d57e2be3f83f4fb9", "f8a3576739752bfe", "fa8dc1631474db6e",
    }
)
#: A token: a run of anything but white space and punctuation (Bengali and Devanagari vowel signs stay inside).
_TOKEN = re.compile(r"[^\s.,;:!?'\"“”‘’()\[\]{}|/\\—–-]+")
#: Case endings removed before a token is hashed (Bengali possessive/plural/objective, Hindi oblique).
_SUFFIXES: tuple[str, ...] = ("দের", "েরা", "ের", "এর", "কে", "রা", "র", "ों", "ने", "का", "की", "के", "'s")


def _digest(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _party_spans(text: str) -> list[tuple[int, int]]:
    """The spans of party names in ``text`` (single tokens and two-token phrases)."""
    toks = [(m.start(), m.end(), m.group(0).lower()) for m in _TOKEN.finditer(text)]
    spans: list[tuple[int, int]] = []

    def forms(tok: str) -> set[str]:
        out = {tok}
        for suf in _SUFFIXES:
            if tok.endswith(suf) and len(tok) > len(suf) + 1:
                out.add(tok[: -len(suf)])
        return out

    i = 0
    while i < len(toks):
        s, e, tok = toks[i]
        if i + 1 < len(toks):
            s2, e2, tok2 = toks[i + 1]
            if any(_digest(f"{tok} {f}") in PARTY_HASHES for f in forms(tok2)):
                spans.append((s, e2))
                i += 2
                continue
        if any(_digest(f) in PARTY_HASHES for f in forms(tok)):
            spans.append((s, e))
        i += 1
    return spans


def _latin(words: tuple[str, ...]) -> re.Pattern[str]:
    return re.compile(r"(?<![\w-])(?:" + "|".join(words) + r")(?![\w-])", re.IGNORECASE)


def _indic(words: tuple[str, ...]) -> re.Pattern[str]:
    return re.compile("|".join(re.escape(w) for w in sorted(words, key=len, reverse=True)))


_CRIME = (_latin(_CRIME_LATIN), _indic(_CRIME_INDIC))
_CONFLICT = (_latin(_CONFLICT_LATIN), _indic(_CONFLICT_INDIC))
_POLITICAL = (_latin(_POLITICAL_LATIN), _indic(_POLITICAL_INDIC))
_ROAD = (_latin(_ROAD_LATIN), _indic(_ROAD_INDIC))
_GATHERING = (_latin(_GATHERING_LATIN), _indic(_GATHERING_INDIC))


def _hit(pats: tuple[re.Pattern[str], re.Pattern[str]], text: str) -> bool:
    return any(p.search(text) for p in pats)


def _political(text: str) -> bool:
    return _hit(_POLITICAL, text) or bool(_party_spans(text))


def _mask(pats: tuple[re.Pattern[str], re.Pattern[str]], text: str) -> tuple[str, int]:
    spans = _party_spans(text)
    n = len(spans)
    for s, e in reversed(spans):
        text = text[:s] + WITHHELD + text[e:]
    for p in pats:
        text, k = p.subn(WITHHELD, text)
        n += k
    if n:
        # "[WITHHELD]-[WITHHELD]" / "[WITHHELD] [WITHHELD]" read as one withheld span
        text = re.sub(r"\[WITHHELD\](?:[\s-]*\[WITHHELD\])+", WITHHELD, text)
    return text, n


@dataclass(frozen=True)
class Screen:
    """One item's scope verdict. ``reason`` None: in scope; ``title``/``text`` are what may be kept."""

    reason: str | None
    title: str
    text: str
    #: political terms withheld from a kept item
    masked: int = 0


def screen(title: str | None, text: str | None = None) -> Screen:
    """The scope verdict for one item's title and text (see the module docstring). Pure."""
    t, x = title or "", text or ""
    both = f"{t}\n{x}"
    if _hit(_CRIME, both):
        return Screen("crime", t, x)
    if _hit(_CONFLICT, both) or (_BN_CLASH in both and not _BN_COLLISION_CONTEXT.search(both)):
        return Screen("conflict", t, x)
    if _political(both):
        if not (_hit(_ROAD, both) and _hit(_GATHERING, both)):
            return Screen("political", t, x)
        t2, n1 = _mask(_POLITICAL, t)
        x2, n2 = _mask(_POLITICAL, x)
        return Screen(None, t2, x2, n1 + n2)
    return Screen(None, t, x)


def screen_class(event_class: str | None) -> str | None:
    """The drop reason of an out-of-scope classifier class, else None."""
    return OUT_OF_SCOPE_CLASSES.get(event_class or "")
