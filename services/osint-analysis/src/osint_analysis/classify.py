"""Classify a signal into a fine situation class and a Sahoshi kind (OSINT SPEC §1.6, §2.1; GEOSPATIAL_AND_DSS §A10).

Events are about PLACES and SITUATIONS, never persons. Reported crime enters only from REPORTED TEXT, as a
situation for RESPONSE (``reported_crime`` or ``public_disorder``), and OSINT never emits ``crime_incident``
(ANPR/watchlist origin) or ``vehicle_pursuit`` (human-initiated): :func:`_final_check` raises on either, whatever
a row, an exemplar or a future edit says, and :class:`~osint_common.types.Classification` refuses both again.

Kolkata reads its news in English, Bengali and Hindi, so every row carries English, Bengali and (where cheap)
Hindi cues. The rules, in order:

1. **The SACHET rule.** An official CAP alert (``sachet_cap``; ``imd`` alerts reach Sahoshi the same way) is a
   flood situation (``urban_flooding`` / ``waterlogging`` / ``flooding``) when it carries a flood word (English,
   Bengali or Hindi: "heavy rain", "ভারী বৃষ্টি", "জল জমতে", "भारी बारिश"), and an honest ``weather_hazard`` /
   ``hazard`` otherwise, whose subtype names the alert's own event (:func:`cap_subtype`: ``rain``,
   ``thunderstorm``, ``heat``, ... from ``cap_event`` or the text, else ``weather_advisory``): a light-rain
   nowcast is neither a flood nor a storm.
2. **The lexicon**, :data:`CLASS_LEXICON`, in its order, first matching row wins; ``matched_terms`` lists every
   keyword of that row found in the title and text. The English rows are the proof-of-concept's lexicon (a
   fallen tree and a live wire, which it had no row for, are two ``hazard`` rows of their own; a ``parade`` is a
   procession). The text is read through :func:`normalize_text` (NFKC, format characters dropped, poster handles
   stripped, whitespace collapsed, lower-cased), and an English keyword matches a WHOLE word
   (:func:`keyword_forms`):

   * the keyword itself or a regular inflection of its last word: ``-s``, ``-es``, ``-ed``, ``-d``, ``-ing``, a
     final ``y`` as ``-ies``/``-ied``, a doubled final consonant (``mobs``, ``mobbed``, ``crashes``, ``looted``,
     ``robberies``), so ``mob`` never matches "mobile", ``strike`` never "striker", ``toxic`` never "toxicology";
   * the derived words of :data:`DERIVED_FORMS`, each with its plural: the agent nouns ("protesters", "looters",
     "chain snatchers", "brawlers", "marchers") and a few derived nouns ("gas leakage", "oil spillage");
   * a noun of :data:`NOUN_KEYWORDS` takes a plural only (``concerts``, never "concerted"; ``fairs``, never
     "fairly");
   * a stem of :data:`STEM_KEYWORDS` matches any continuation (``waterlogged``, ``inundation``, ``flooded``,
     ``heavy rainfall``, ``electrocuted``) except the listed ones ("floodlights" are not a flood);
   * two context rules (:data:`CONTEXT_RULES`): the month ("by March", "March 15") is not a ``march``, and a
     "lightning strike" is weather, not a ``strike``.

   **Bengali and Hindi keywords** (any keyword in an Indic script) are written as words separated by spaces, and
   match whole words of the text (a Bengali vowel sign is part of its word, so "জল" is never read inside
   "কাজল"):

   * ``a/b/c`` is one word slot with alternatives ("জল জমা/জমে/জমেছে": water collected, collects, has collected);
   * every word also matches with a case ending (:data:`INDIC_ENDINGS`: ``osint_common.ethics.INDIC_SUFFIXES``,
     "রাস্তায়", "গাছের", "দুর্ঘটনায়", "বৃষ্টিতে", and the Hindi plural endings, "दुर्घटनाओं"), unless it ends in
     ``=``; verb forms are listed, never guessed, so a negative perfect ("জমেনি": did not collect) is not a form;
   * ``…`` between two slots allows one other word between them ("গাছের ডাল ভেঙে": a tree's branch broke);
   * a match followed, within its clause, by a negation ("না", "নেই", "নয়", "নি", "नहीं", or a negative
     perfect such as "হয়নি") is no cue: "ভারী বৃষ্টির সম্ভাবনা নেই" (no heavy rain likely) is not a flood;
   * precision guards for the ambiguous words (:data:`CONTEXT_RULES`, :data:`CLASS_CONTEXT_RULES`): "ধাক্কা" (a
     knock, also a setback), "উল্টে" (overturned, also "in turn"), "পিষে" and "চাপা" (crushed, run over) and
     "टक्कर" are a road accident only with a vehicle in their clause (a crowd crush is a crowd, "বড় ধাক্কা" a
     setback); "সংঘর্ষ" is a collision with a vehicle in its clause and a clash between groups otherwise;
     "দুর্ঘটনা" in a fire report without any vehicle ("অগ্নি দুর্ঘটনা") is the fire's; "আগুন"/"आग" next to a price
     ("আগুন দাম", "দামে আগুন": prices on fire) or spitting fire ("আগুন ঝরানো বোলিং") is no fire; "ঝড়" raised by
     someone ("ঝড় তুলল"), of criticism, debate or runs ("সমালোচনার ঝড়", "রানের ঝড়") or on social media is no
     storm; standing water in a dengue report ("জমা জলে মশার লার্ভা") or a plan to stop it ("জল জমা রুখতে") is no
     waterlogging; a "ভোট লুট" claim is
     not a robbery; a building "ভেঙে ফেলা" (demolished) has not collapsed; "ভিড় কম" (thin crowd) is no gathering;
     "বিসর্জন" (immersion) is a procession only in a Puja report ("নিয়ম বিসর্জন": rules abandoned).

   Every Bengali and Hindi cue word is an ordinary word of ``osint_common.ethics.INDIC_COMMON_WORDS``, so it
   survives the ingress redaction, which withholds every other Indic word as ``[WITHHELD]`` (a test pins it).
   A traffic jam ("যানজট", "জ্যাম", "जाम") or a disruption ("যান চলাচল ব্যাহত") is a CONSEQUENCE, not a class: as
   in English ("traffic jam"), it classifies by its cause ("জল জমে যানজট" is waterlogging, "মিছিলের জেরে যানজট" a
   procession) and alone it is ``general_news`` (congestion is read from the live traffic feeds, not from news).
   A procession or a rally is classified as the SITUATION on the road, never by who marches or why.

   **Poster handles are never a cue** (ethics rule 2: a handle is never stored, shown, tracked or scored).
   :func:`strip_handles` removes Reddit's ``submitted by /u/<name> [link] [comments]`` trailer, any other
   ``/u/<name>``, ``u/<name>`` or ``reddit.com/user/<name>``, and the ``[link]``/``[comments]`` boilerplate inside
   :func:`normalize_text`, so a handle never classifies a post ("/u/crash-test-kid" is not a road accident), never
   adds a similarity token (two posts by one poster are not more alike than two posts by two posters) and never
   reaches an embedder.
3. **Zero-shot fallback** (optional, off without an :class:`~osint_common.pipeline.Embedder`): a lexicon miss
   from an official or news tier is compared with one exemplar sentence per class; the nearest class wins when
   its cosine is at least :data:`ZERO_SHOT_MIN_COSINE` and leads the runner-up by :data:`ZERO_SHOT_MIN_MARGIN`.
   ``matched_terms`` is then ``["zero-shot"]``, so the provenance of the class stays visible. Social posts are
   never zero-shot classified: a social signal gets an event class only from an explicit lexicon cue.
4. Otherwise ``general_news``: not an event, never surfaced.

``sahoshi_incident_kind`` stays inside ``traffic.incidents.incident_kind`` as relaxed by migration 021, which added
``robbery``, ``road_rage`` and ``public_disorder`` for exactly these rows (the PoC used ``other`` and ``protest``
because the CHECK did not allow them yet).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from types import MappingProxyType
from typing import NamedTuple

import numpy as np

from osint_common import ethics
from osint_common.pipeline import Embedder
from osint_common.types import Classification, RawOsintSignal

__all__ = [
    "CAP_FLOOD_TERMS",
    "CAP_SOURCES",
    "CAP_SUBTYPES",
    "CLASS_CONTEXT_RULES",
    "CLASS_LABELS",
    "CLASS_LEXICON",
    "CONTEXT_RULES",
    "DERIVED_FORMS",
    "FORBIDDEN_OSINT_KINDS",
    "INDIC_ENDINGS",
    "NOUN_KEYWORDS",
    "STEM_KEYWORDS",
    "VEHICLE_WORDS",
    "WORD_RE",
    "LexiconRow",
    "ZERO_SHOT_EXEMPLARS",
    "ZERO_SHOT_MIN_COSINE",
    "ZERO_SHOT_MIN_MARGIN",
    "ZERO_SHOT_TERM",
    "ZERO_SHOT_TIERS",
    "cap_subtype",
    "classify",
    "classify_with_vectors",
    "default_row",
    "exemplar_texts",
    "indic_slots",
    "is_indic",
    "keyword_forms",
    "keyword_matches",
    "lexicon_classify",
    "normalize_text",
    "similarity_text",
    "strip_handles",
    "zero_shot",
    "zero_shot_eligible",
]


class LexiconRow(NamedTuple):
    """One classifier row: the class, its fine subtype, the Sahoshi kinds it maps to, and its cue keywords."""

    event_class: str
    subtype: str
    sahoshi_event_kind: str
    sahoshi_incident_kind: str
    keywords: tuple[str, ...]


#: Two Bengali keywords with a guard of their own (:data:`CONTEXT_RULES`), named once for the row and the rule.
_WATER_COLLECTED = "জল জমা/জমে/জমেছে/জমল/জমছে/জমেছিল/জমতে"
_COLLAPSE = "বাড়ি/ভবন/ছাদ/দেওয়াল/পাঁচিল/বারান্দা/কার্নিশ/চাঙড়/সেতু/ব্রিজ/উড়ালপুল/ফ্লাইওভার … ভেঙে/ধসে"
_CAP_WATER = "জল জমা/জমে/জমেছে/জমতে"

#: The lexicon; first match wins. The English keywords of the first thirteen rows are the proof-of-concept's
#: ``CLASS_LEXICON``, in its order (only the incident kinds of the first three rows changed: migration 021 added
#: ``robbery``, ``road_rage`` and ``public_disorder`` to ``traffic.incidents`` for them). Each row then carries its
#: Bengali and Hindi cues (see "Bengali and Hindi keywords" in the module docstring).
CLASS_LEXICON: tuple[LexiconRow, ...] = (
    LexiconRow(
        "reported_crime",
        "daylight_robbery",
        "reported_crime",
        "robbery",
        (
            "robbery", "robbed", "loot", "looted", "chain snatch", "snatching", "dacoity", "mugging", "burglary",
            "heist", "gunpoint", "theft at", "atm break",
            # snatching, dacoity, loot (never a "ভোট লুট" claim), at gunpoint, a shop/house/flat/ATM theft
            "ছিনতাই", "ডাকাতি", "লুট", "বন্দুক দেখিয়ে", "দোকান/বাড়ি/ফ্ল্যাট/এটিএম … চুরি",
            "लूट", "डकैती",
        ),
    ),
    LexiconRow(
        "reported_crime",
        "road_rage",
        "reported_crime",
        "road_rage",
        ("road rage", "beaten on road", "attacked motorist", "thrashed", "assault after"),
    ),
    LexiconRow(
        "public_conflict",
        "affray",
        "public_disorder",
        "public_disorder",
        (
            "clash", "brawl", "scuffle", "stone pelting", "stone-pelting", "mob", "beaten by mob", "communal tension",
            "group fight", "violence erupted", "locals thrash",
            # a fight, a scuffle, a clash between groups (no vehicle in its clause), stone pelting, a mob beating
            "মারামারি", "হাতাহাতি", "সংঘর্ষ", "ইটবৃষ্টি", "গণপিটুনি", "গণধোলাই",
            "पथराव", "झड़प",
        ),
    ),
    LexiconRow(
        "road_accident",
        "collision",
        "road_accident",
        "accident",
        (
            "accident", "road accident", "crash", "collision", "hit-and-run", "hit and run", "overturned", "rammed",
            "mishap", "vehicles collided", "truck overturn", "hits three", "hits 3", "multi-vehicle", "multi vehicle",
            # accident (not a fire's), and with a vehicle in the clause: hit, collision, overturned, crushed, run over
            "দুর্ঘটনা", "ধাক্কা", "সংঘর্ষ", "উল্টে", "পিষে", "চাপা",
            "दुर्घटना", "हादसा", "टक्कर",
        ),
    ),
    LexiconRow(
        "fire",
        "structure_fire",
        "hazard",
        "other",
        (
            "fire broke", "fire breaks", "blaze", "gutted", "fire at", "massive fire", "caught fire", "fire brigade",
            "flames",
            # fire (never prices or a fiery spell), blaze, fire accident, the fire brigade, burnt to ashes
            "আগুন", "অগ্নিকাণ্ড", "অগ্নিদুর্ঘটনা", "অগ্নি দুর্ঘটনা", "দমকল", "পুড়ে ছাই",
            "आग", "अग्निकांड", "अग्नि दुर्घटना",
        ),
    ),
    LexiconRow(
        "urban_flooding",
        "waterlogging",
        "flooding",
        "weather",
        (
            "waterlog", "water-log", "water logg", "flood", "inundat", "submerg", "knee-deep", "heavy rain",
            "downpour", "rain fury", "deluge",
            # water collected / collects / has collected / may collect, standing water (never a dengue report),
            # waterlogged, water-locked, waterlogging misery, flooded, flood, flood-hit, awash, knee- or waist-deep,
            # heavy, very heavy, pouring and incessant rain
            _WATER_COLLECTED, "জমা জল", "জলমগ্ন", "জলবন্দি", "জলযন্ত্রণা", "প্লাবিত", "বন্যা",
            "বানভাসি", "জল থইথই", "হাঁটুজল", "হাঁটু/কোমর … জল", "ভারী/অতিভারী/মুষলধারে/টানা বৃষ্টি",
            "जलभराव", "जलजमाव", "बाढ़", "भारी/मूसलाधार बारिश",
        ),
    ),
    LexiconRow(
        "infra_failure",
        "collapse",
        "infra_failure",
        "route_blockage",
        (
            "bridge collapse", "building collapse", "wall collapse", "slab collapse", "road caved", "cave-in",
            "gas leak", "power outage", "transformer blast",
            # a house, building, roof, wall, bridge or flyover broke or caved in (never a demolition), plaster
            # chunks fell, the road caved in, a gas leak, a power cut, a burst pipe, a transformer blast
            _COLLAPSE, "রাস্তা/সড়ক/মাটি … ধস", "গ্যাস লিক", "লোডশেডিং", "বিদ্যুৎহীন", "বিদ্যুৎ বিভ্রাট", "পাইপ ফেটে",
            "ট্রান্সফর্মার … বিস্ফোরণ/ফেটে",
            "पुल/इमारत/दीवार/मकान … गिरा/गिरी/गिरे/ढहा/ढही",
        ),
    ),
    LexiconRow(
        "hazard",
        "spill",
        "hazard",
        "other",
        (
            "chemical spill", "gas leak", "hazardous", "toxic", "oil spill", "leakage",
            "বিষাক্ত", "রাসায়নিক … লিক/ছড়িয়ে",
        ),
    ),
    LexiconRow(
        "hazard",
        "fallen_tree",
        "hazard",
        "route_blockage",
        (
            "fallen tree", "tree fell", "trees fell", "tree fall", "tree uprooted", "trees uprooted", "uprooted tree",
            # a tree (or its branch) fell, broke or was uprooted onto the road
            "গাছ … পড়ে/পড়ল/পড়লো/পড়েছে/পড়া/ভেঙে/উপড়ে", "উপড়ে পড়া গাছ",
            "पेड़ … गिरा/गिरी/गिरे/गिरने/उखड़ा/उखड़े",
        ),
    ),
    LexiconRow(
        "hazard",
        "live_wire",
        "hazard",
        "other",
        (
            "live wire", "snapped wire", "wire snapped", "electrocut",
            # electrocuted, a snapped or torn wire, a live (high-tension, current-carrying) wire
            "বিদ্যুৎস্পৃষ্ট", "তড়িদাহত", "তার ছিঁড়ে", "ছেঁড়া তার", "বিদ্যুতের/হাইটেনশন/বিদ্যুৎবাহী তার",
            "करंट लगने/लगा/लगी",
        ),
    ),
    LexiconRow(
        "public_gathering",
        "mass_gathering",
        "mass_gathering",
        "crowd_surge",
        (
            "rally", "gathering", "huge crowd", "mela", "fair", "concert", "festival crowd", "jam packed",
            "devotees",
            # a rally, a gathering, a crowd (never a thin one), a sea of people, a fair, visitors and pilgrims
            "সমাবেশ", "জমায়েত", "ভিড়", "জনসমুদ্র", "মেলা", "বইমেলা", "দর্শনার্থী", "পুণ্যার্থী", "র্যালি",
            "रैली", "भीड़", "मेला",
        ),
    ),
    LexiconRow(
        "procession",
        "procession",
        "procession",
        "other",
        (
            "procession", "yatra", "rath yatra", "shobha yatra", "march", "parade",
            # a procession or march, Rath Yatra, a padayatra, a Puja immersion, the Puja carnival, a parade
            "মিছিল", "শোভাযাত্রা", "রথযাত্রা", "পদযাত্রা", "বিসর্জন", "ভাসান", "কার্নিভাল", "প্যারেড",
            "जुलूस", "शोभायात्रा", "रथयात्रा",
        ),
    ),
    LexiconRow(
        "unrest",
        "protest",
        "public_disorder",
        "protest",
        (
            "protest", "agitation", "demonstration", "bandh", "dharna", "strike", "gherao",
            # a road or rail blockade, a protest, a strike, a bandh, a gherao, a hunger strike
            "অবরোধ", "বিক্ষোভ", "ধর্মঘট", "বনধ", "ঘেরাও", "অনশন",
            "धरना", "चक्का जाम", "हड़ताल",
        ),
    ),
    LexiconRow(
        "road_closure",
        "closure",
        "work_zone",
        "route_blockage",
        (
            "road closed", "diversion", "roadblock", "traffic diverted", "lane closure", "metro work", "dug up",
            "route changed", "closed for",
            # a road, bridge or flyover closed, traffic stopped or barred, a detour, diverted, an alternative route,
            # metro or repair work, the road dug up
            "রাস্তা/সড়ক/রোড/সরণি/লেন/সেতু/ব্রিজ/উড়ালপুল/ফ্লাইওভার বন্ধ", "যান চলাচল বন্ধ/নিষিদ্ধ", "ঘুরপথে",
            "ঘুরিয়ে দেওয়া", "বিকল্প পথ", "মেট্রো/মেরামতি কাজ", "খোঁড়াখুঁড়ি",
            "रास्ता/सड़क बंद",
        ),
    ),
    LexiconRow(
        "weather_hazard",
        "storm",
        "hazard",
        "weather",
        (
            "thunderstorm", "lightning", "cyclone", "heatwave", "heat wave", "cold wave", "rainfall warning",
            "weather warning", "squall",
            # cyclone, storm (never a figurative one), storm and rain, nor'wester, depression, lightning,
            # a thunderbolt fell, gusty or stormy wind, heat wave, cold wave, hail
            "ঘূর্ণিঝড়", "ঝড়", "ঝড়বৃষ্টি", "কালবৈশাখী", "নিম্নচাপ", "বজ্রপাত", "বজ্রবিদ্যুৎ", "বাজ পড়ে/পড়ল/পড়েছে",
            "দমকা/ঝোড়ো হাওয়া", "তাপপ্রবাহ", "শৈত্যপ্রবাহ", "শিলাবৃষ্টি",
            "चक्रवात", "आंधी", "आकाशीय बिजली", "बिजली गिरने/गिरी/गिरा",
        ),
    ),
)

#: Official CAP alert feeds the SACHET rule classifies (IMD and WBSDMA alerts reach Sahoshi through SACHET).
CAP_SOURCES: frozenset[str] = frozenset({"sachet_cap", "imd"})
#: The flood words of a CAP alert: the proof-of-concept's English ones, and the Bengali and Hindi words of the same
#: warnings ("ভারী বৃষ্টির সতর্কতা", "নিচু এলাকায় জল জমতে পারে", "भारी बारिश की चेतावनी").
CAP_FLOOD_TERMS: tuple[str, ...] = (
    "flood", "waterlog", "inundat", "heavy rain", "very heavy", "extremely heavy", "submerg",
    "ভারী/অতিভারী বৃষ্টি", "অতিভারী", _CAP_WATER, "জলমগ্ন", "প্লাবিত", "বন্যা",
    "भारी बारिश", "बाढ़", "जलभराव",
)
_CAP_FLOOD = LexiconRow("urban_flooding", "waterlogging", "flooding", "weather", CAP_FLOOD_TERMS)
_CAP_WEATHER = LexiconRow("weather_hazard", "weather_advisory", "hazard", "weather", ())
#: The subtype of a non-flood CAP alert, from its ``<event>`` (``raw.cap_event``) first, else its text: first match
#: wins, most severe first (F-HONEST OSINT-7: every such alert used to be "storm", a light-rain nowcast included).
#: Nothing matched: ``weather_advisory``. Bengali and Hindi alert words sit with their English event.
CAP_SUBTYPES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("cyclone", ("cyclone", "cyclonic", "depression", "ঘূর্ণিঝড়", "নিম্নচাপ", "चक्रवात")),
    (
        "thunderstorm",
        (
            "thunderstorm", "thunder", "lightning", "squall", "hailstorm", "hail",
            "বজ্রপাত", "বজ্রবিদ্যুৎ", "কালবৈশাখী", "ঝড়বৃষ্টি", "শিলাবৃষ্টি", "ঝড়", "বাজ", "आकाशीय बिजली",
        ),
    ),
    ("dust_storm", ("dust storm", "duststorm", "dust raising", "आंधी")),
    ("heat", ("heat wave", "heatwave", "heat", "hot and humid", "warm night", "তাপপ্রবাহ")),
    ("cold", ("cold wave", "coldwave", "cold day", "frost", "শৈত্যপ্রবাহ")),
    ("fog", ("fog", "কুয়াশা", "कोहरा")),
    ("strong_wind", ("strong wind", "gusty wind", "high wind", "surface wind", "দমকা/ঝোড়ো হাওয়া")),
    ("rain", ("rain", "rainfall", "drizzle", "shower", "বৃষ্টি", "বর্ষণ", "बारिश")),
)


def cap_subtype(signal: RawOsintSignal) -> str:
    """A non-flood CAP alert's honest subtype (:data:`CAP_SUBTYPES`): its ``cap_event`` first, else its text."""
    event = signal.raw.get("cap_event") if isinstance(signal.raw.get("cap_event"), str) else None
    for hay in (event, f"{signal.title} {signal.text}"):
        if not hay:
            continue
        low = normalize_text(hay)
        for sub, patterns in _CAP_SUBTYPE_RES:
            if any(rx.search(low) for rx in patterns):
                return sub
    return "weather_advisory"

#: Never from OSINT: ``crime_incident`` is ANPR/watchlist origin, a pursuit is human-initiated.
FORBIDDEN_OSINT_KINDS: frozenset[str] = frozenset({"crime_incident", "vehicle_pursuit"})

#: Sentence-case labels for the situation label ``"<class label> · <place>"`` (C-T).
CLASS_LABELS: Mapping[str, str] = MappingProxyType(
    {
        "reported_crime": "Reported crime",
        "public_conflict": "Public conflict",
        "road_accident": "Road accident",
        "fire": "Fire",
        "urban_flooding": "Urban flooding",
        "infra_failure": "Infrastructure failure",
        "hazard": "Hazard",
        "public_gathering": "Public gathering",
        "procession": "Procession",
        "unrest": "Unrest",
        "road_closure": "Road closure",
        "weather_hazard": "Weather hazard",
        "general_news": "General news",
    }
)

#: One neutral exemplar per class for the zero-shot fallback: situations at places, no person, no name.
ZERO_SHOT_EXEMPLARS: Mapping[str, str] = MappingProxyType(
    {
        "reported_crime": "A robbery or theft was reported at a shop or on a street in the city.",
        "public_conflict": "A clash broke out between groups at a junction and stones were pelted.",
        "road_accident": "A road accident: vehicles collided on the highway and people were injured.",
        "fire": "A fire broke out in a building and fire tenders were called to the spot.",
        "urban_flooding": "Heavy rain left roads waterlogged and underpasses flooded.",
        "infra_failure": "A bridge, wall or building collapsed, or a major power outage hit the area.",
        "hazard": "A chemical spill or a gas leak was reported at an industrial site.",
        "public_gathering": "A huge crowd gathered for a festival, a fair or a rally.",
        "procession": "A religious procession moved along the main road.",
        "unrest": "A protest, a bandh or a demonstration was held in the city.",
        "road_closure": "The road was closed and traffic was diverted for construction work.",
        "weather_hazard": "A thunderstorm, lightning or heat wave warning was issued for the area.",
    }
)
_EXEMPLAR_CLASSES: tuple[str, ...] = tuple(ZERO_SHOT_EXEMPLARS)
_EXEMPLAR_TEXTS: tuple[str, ...] = tuple(ZERO_SHOT_EXEMPLARS.values())
#: The nearest exemplar must be at least this close (cosine of unit vectors) ...
ZERO_SHOT_MIN_COSINE = 0.55
#: ... and lead the runner-up by at least this much, or the signal stays ``general_news``. Both are starting
#: values, not calibrated against bge-m3 in this WP (the embedding host is live-only, and today's service has no
#: read-only ``/embed`` route); the fallback is off unless an embedder is passed.
ZERO_SHOT_MIN_MARGIN = 0.03
#: The tiers whose lexicon misses may be zero-shot classified (never ``social_unverified``).
ZERO_SHOT_TIERS: frozenset[str] = frozenset({"official", "news_wire", "news_regional", "aggregator", "archive"})
ZERO_SHOT_TERM = "zero-shot"

_WS = re.compile(r"\s+")
_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})

#: A Reddit account name (3-20 characters today; any length is taken, so a long one is never left half-stripped).
_HANDLE_NAME = r"[A-Za-z0-9_-]{3,}"
#: A poster handle as it is written: a profile link (``reddit.com/user/<name>``, ``…/u/<name>``, with or without
#: the scheme and a subdomain), ``/u/<name>`` or a bare ``u/<name>`` (never inside a word or a path: "menu/item"
#: and "u/s 302", Indian legal shorthand for "under section", are left alone).
_HANDLE_PATTERN = (
    r"(?:(?:https?://)?(?:[\w-]+\.)*reddit\.com/(?:u|user)/" + _HANDLE_NAME + r"/?"
    r"|(?<![\w/])/?u/" + _HANDLE_NAME + r")"
)
_BOILERPLATE_PATTERN = r"\[(?:link|comments)\]"
_HANDLE = re.compile(_HANDLE_PATTERN, re.IGNORECASE)
_BOILERPLATE = re.compile(_BOILERPLATE_PATTERN, re.IGNORECASE)
#: Reddit's RSS trailer "submitted by /u/<name> [link] [comments]" (or with ``[PERSON]`` where parse redacted the
#: name), with the separator before it. "submitted by" alone is taken only when a handle, ``[PERSON]``, the
#: boilerplate or the end of the text follows it: "a petition submitted by March 15" is left alone.
_TRAILER = re.compile(
    r"(?:\s*[,;:|–—-])?\s*\bsubmitted\s+by\s*(?:(?:" + _HANDLE_PATTERN + r"|\[person\])(?:\s*"
    + _BOILERPLATE_PATTERN + r")*|(?:" + _BOILERPLATE_PATTERN + r"\s*)+|$)",
    re.IGNORECASE,
)


def strip_handles(text: str, replacement: str = " ") -> str:
    """A text without poster handles (ethics rule 2): the ``submitted by <handle> [link] [comments]`` trailer and
    the ``[link]``/``[comments]`` boilerplate are dropped, and every other handle becomes ``replacement`` (a space
    for the analysis view, ``[PERSON]`` for a text that leaves the pipeline). The one helper both views use; an
    unchanged text is returned as it was, a changed one without the spaces left at its ends."""
    out = _TRAILER.sub(" ", text)
    out = _HANDLE.sub(replacement, out)
    out = _BOILERPLATE.sub(" ", out)
    return text if out == text else out.strip()


def normalize_text(text: str | None) -> str:
    """NFKC, format characters (zero-width, soft hyphen) dropped, curly quotes straightened, poster handles stripped
    (:func:`strip_handles`), whitespace collapsed, lower-cased: the one text view every classifier, similarity and
    embedder rule reads. A Bengali spelling that a dropped zero-width non-joiner would merge into another word
    keeps its own form first (:data:`_INDIC_SPELLINGS`: "বন্‌ধ", a bandh, is not "বন্ধ", closed)."""
    s = unicodedata.normalize("NFKC", text or "")
    for written, kept in _INDIC_SPELLINGS:
        s = s.replace(written, kept)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Cf").translate(_QUOTES)
    return _WS.sub(" ", strip_handles(s)).strip().lower()


#: Bengali spellings that differ from another word only by a zero-width non-joiner: "বন্‌ধ" (a bandh, written with
#: a visible hasant) would read as "বন্ধ" (closed) once format characters are dropped; it is kept as "বনধ".
_INDIC_SPELLINGS: tuple[tuple[str, str], ...] = (("বন্\u200cধ", "বনধ"),)


#: Stems: the keyword matches at the start of a word, whatever follows ("waterlogged", "inundation", "submerged",
#: "flooded", "heavy rainfall", "electrocuted", "electrocution") — except the continuations listed with it
#: ("floodlights", "floodlit").
STEM_KEYWORDS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "waterlog": (),
        "water-log": (),
        "water logg": (),
        "inundat": (),
        "submerg": (),
        "flood": ("light", "lit"),
        "heavy rain": (),
        "electrocut": (),
    }
)
#: Nouns (and an adjective) whose verb-like endings are other words: a plural only ("concerts", never "concerted";
#: "fairs", never "fairing").
NOUN_KEYWORDS: frozenset[str] = frozenset({"concert", "fair", "mela", "toxic"})
#: Derived words a keyword also matches, each with its plural (``-s``/``-es``). They are the words the PoC's plain
#: substring test caught and a whole-word rule would miss, found by testing every keyword against a dictionary:
#: the agent nouns ("protesters block the highway", "looters target a shop", "chain snatchers strike again") and a
#: few derived nouns ("gas leakage" keeps the PoC's first match, infra_failure). Deliberately absent, because the
#: substring test was wrong there: "striker(s)" (a footballer), "mobile"/"mobster" (``mob``), "accidental" (an
#: "accidental fire" is a fire), "blazer", "Protestant", "protestations", "metro workers" (not a work zone),
#: "toxicology".
DERIVED_FORMS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "loot": ("looter",),
        "chain snatch": ("chain snatcher",),
        "snatching": ("snatcher",),
        "brawl": ("brawler",),
        "gas leak": ("gas leakage",),
        "chemical spill": ("chemical spillage",),
        "oil spill": ("oil spillage",),
        "rally": ("rallyist",),
        "procession": ("processional",),
        "march": ("marcher",),
        "protest": ("protester", "protestor"),
    }
)

_ENDINGS = ("", "s", "es", "ed", "d", "ing")
_PLURAL_ENDINGS = ("", "s", "es")
_VOWELS = frozenset("aeiou")
_PREVIOUS_WORD = re.compile(r"(\w+)\W*$")
_LEADING_NUMBER = re.compile(r"[\s,\-]*\d")
#: Words before "march" that make it the month ("by March", "in March", "mid-March", "end of March").
_MONTH_CUES: frozenset[str] = frozenset(
    {
        "in", "by", "since", "until", "till", "from", "of", "this", "next", "last", "early", "mid", "late", "end",
        "before", "after", "during", "through", "throughout",
    }
)
#: Words before "strike" that make it something other than a labour strike.
_NOT_A_STRIKE: frozenset[str] = frozenset({"lightning", "air"})


def _previous_word(hay: str, start: int) -> str:
    found = _PREVIOUS_WORD.search(hay[max(0, start - 48) : start])
    return found.group(1) if found else ""


def _not_the_month(hay: str, m: re.Match[str]) -> bool:
    """``march`` is a march unless it is the month: an inflected form ("marched") always is the verb; the bare word
    is the month after a month cue ("by March") or before a day or a year ("March 15", "March 2027")."""
    if m.group(0) != "march":
        return True
    if _previous_word(hay, m.start()) in _MONTH_CUES:
        return False
    return _LEADING_NUMBER.match(hay, m.end()) is None


def _not_a_lightning_strike(hay: str, m: re.Match[str]) -> bool:
    """A "lightning strike" (or an "air strike") is not a labour strike."""
    return _previous_word(hay, m.start()) not in _NOT_A_STRIKE


def _doubles(word: str) -> bool:
    """A last syllable consonant-vowel-consonant doubles its consonant before ``-ed``/``-ing`` ("mob" → "mobbed")."""
    return (
        len(word) >= 2
        and word[-1].isalpha()
        and word[-1] not in _VOWELS
        and word[-1] not in "wxy"
        and word[-2] in _VOWELS
        and (len(word) < 3 or word[-3] not in _VOWELS)
    )


# ── Bengali and Hindi keywords ───────────────────────────────────────────────────────────────────────────────────


def _indic_class(lo: int = 0x0900, hi: int = 0x0D7F) -> str:
    """The letters and marks (categories L* and M*) of the Indic blocks, Devanagari through Malayalam (the range
    ``osint_common.ethics`` reads), as the body of a regex character class. Python's ``\\w`` does not match a
    vowel sign or a virama, so a Bengali word is never a run of ``\\w``."""
    cps = [c for c in range(lo, hi + 1) if unicodedata.category(chr(c))[0] in "LM"]
    runs: list[tuple[int, int]] = []
    for c in cps:
        if runs and runs[-1][1] == c - 1:
            runs[-1] = (runs[-1][0], c)
        else:
            runs.append((c, c))
    return "".join(chr(a) if a == b else f"{chr(a)}-{chr(b)}" for a, b in runs)


_INDIC_LM = _indic_class()
#: A word character of any script: ``\\w`` or an Indic letter or mark.
_ANY_WORD = rf"[\w{_INDIC_LM}]"
#: A word in any script (Latin, Bengali, Devanagari), vowel signs included: the tokens similarity reads.
WORD_RE = re.compile(rf"{_ANY_WORD}+")
#: Hindi plural and oblique endings ("दुर्घटनाओं", "जुलूसों") next to the Bengali case endings of ``ethics``.
_HINDI_ENDINGS = ("ों", "ें", "ओं", "एं", "े")
#: The endings an Indic keyword word also matches with, longest first (see the module docstring).
INDIC_ENDINGS: tuple[str, ...] = tuple(
    sorted({unicodedata.normalize("NFKC", e) for e in (*ethics.INDIC_SUFFIXES, *_HINDI_ENDINGS)}, key=len,
           reverse=True)
)
_ENDING_GROUP = "(?:" + "|".join(re.escape(e) for e in INDIC_ENDINGS) + ")?"
#: Between two words of a keyword: white space, or a hyphen or dash ("জল-যন্ত্রণা").
_SEP = r"(?:\s*[-‐‑–—]\s*|\s+)"
#: A clause ends at these marks (the Bengali and Devanagari danda included); a gap word never crosses one.
_CLAUSE_MARKS = "।॥.,;:!?|"
_GAP = rf"{_SEP}(?:[^\s{re.escape(_CLAUSE_MARKS)}]+{_SEP})?"
_GAP_TOKEN = "…"
_CLAUSE_END = re.compile(rf"[{re.escape(_CLAUSE_MARKS)}]")


def is_indic(keyword: str) -> bool:
    """Whether a keyword is written in an Indic script (it then follows the Bengali and Hindi rules)."""
    return any("\u0900" <= ch <= "\u0d7f" for ch in keyword)


def indic_slots(keyword: str) -> list[tuple[str, ...]]:
    """The word slots of an Indic keyword, each its alternatives (``=`` and ``…`` dropped): the words the keyword is
    made of, every one of which must survive the ingress redaction."""
    return [
        tuple(normalize_text(alt.rstrip("=")) for alt in slot.split("/"))
        for slot in keyword.split()
        if slot != _GAP_TOKEN
    ]


def _indic_slot_re(slot: str) -> str:
    alts = []
    for alt in slot.split("/"):
        exact = alt.endswith("=")
        alts.append(re.escape(normalize_text(alt.rstrip("="))) + ("" if exact else _ENDING_GROUP))
    return "(?:" + "|".join(alts) + ")"


def _indic_keyword_re(keyword: str) -> re.Pattern[str]:
    """A whole-word match of an Indic keyword (see the module docstring); each slot is a group, so the term a match
    records names the alternative that matched (:func:`_term`)."""
    body, joiner = "", _SEP
    for slot in keyword.split():
        if slot == _GAP_TOKEN:
            joiner = _GAP
            continue
        body += (joiner if body else "") + "(" + _indic_slot_re(slot) + ")"
        joiner = _SEP
    return re.compile(rf"(?<!{_ANY_WORD}){body}(?!{_ANY_WORD})")


def _term(keyword: str, m: re.Match[str]) -> str:
    """The matched term a classification records: an English keyword itself; for an Indic keyword, the alternative
    each slot matched, without its case ending ("বাড়ি … ভেঙে" for "বাড়ির একাংশ ভেঙে"): short, and never a word of
    the text that is not a cue (a gap word is shown as "…")."""
    if not is_indic(keyword):
        return keyword
    words: list[str] = []
    group = 0
    for slot in keyword.split():
        if slot == _GAP_TOKEN:
            words.append(_GAP_TOKEN)
            continue
        group += 1
        got = m.group(group)
        alts = [normalize_text(alt.rstrip("=")) for alt in slot.split("/")]
        words.append(max((a for a in alts if got.startswith(a)), key=len, default=alts[0]))
    return " ".join(words)


def _norm_set(words: str) -> frozenset[str]:
    return frozenset(normalize_text(w) for w in words.split())


def _stems(word: str) -> set[str]:
    """A word and its stem before each Indic ending it carries ("লরির" → "লরি")."""
    out = {word}
    for e in INDIC_ENDINGS:
        if word.endswith(e) and len(word) > len(e) + 1:
            out.add(word[: -len(e)])
    return out


def _words_before(hay: str, start: int, n: int) -> list[str]:
    """Up to ``n`` words before ``start``, in the same clause."""
    head = hay[max(0, start - 200) : start]
    cuts = list(_CLAUSE_END.finditer(head))
    if cuts:
        head = head[cuts[-1].end() :]
    return head.split()[-n:]


def _words_after(hay: str, end: int, n: int) -> list[str]:
    """Up to ``n`` words after ``end``, in the same clause."""
    tail = hay[end : end + 200]
    cut = _CLAUSE_END.search(tail)
    if cut:
        tail = tail[: cut.start()]
    return tail.split()[:n]


def _any_in(words: Sequence[str], vocabulary: frozenset[str]) -> bool:
    return any(not _stems(w).isdisjoint(vocabulary) for w in words)


#: Words that negate the cue before them within its clause.
_NEGATORS = _norm_set("না নেই নি নয় নহে नहीं नही न")
#: A Bengali negative perfect ("হয়নি", "জমেনি", "ঘটেনি": has not happened, collected, occurred).
_NEGATIVE_PERFECT = tuple(normalize_text(e) for e in ("েনি", "য়নি"))


def _negated(hay: str, m: re.Match[str]) -> bool:
    """Whether one of the two words after an Indic cue, in its clause, negates it."""
    return any(w in _NEGATORS or w.endswith(_NEGATIVE_PERFECT) for w in _words_after(hay, m.end(), 2))


#: Vehicles (Bengali, Hindi, English): "ধাক্কা", "সংঘর্ষ", "উল্টে", "পিষে", "চাপা" and "टक्कर" are a road accident
#: only with one of these in their clause. A driver or "traffic" (যান) is not a vehicle here: "চালকের সঙ্গে
#: যাত্রীদের সংঘর্ষ" is a clash.
VEHICLE_WORDS: frozenset[str] = _norm_set(
    """
    বাস মিনিবাস লরি ট্রাক গাড়ি ট্যাক্সি অটো টোটো বাইক মোটরবাইক স্কুটার স্কুটি সাইকেল ট্রাম অ্যাম্বুলেন্স ডাম্পার
    ট্রেলার ট্যাঙ্কার ম্যাটাডোর ভ্যান চাকা
    ट्रक कार बस बाइक ऑटो गाड़ी स्कूटी टैंकर डंपर ट्रेलर
    car cars bus buses truck trucks lorry lorries bike bikes motorbike scooter auto taxi tram ambulance van
    tanker dumper vehicle vehicles
    """
)
_PRICE_WORDS = _norm_set("দাম দর মূল্য মূল্যবৃদ্ধি বাজারদর कीमत कीमतें कीमतों दाम महंगाई")
_SPITTING_FIRE = _norm_set("ঝরানো ঝরাল ঝরাচ্ছে ঝরিয়ে")
_FIGURATIVE_STORM_OF = _norm_set("সমালোচনা বিতর্ক প্রতিবাদ নিন্দা প্রশ্ন জল্পনা আলোচনা প্রশংসা রান ছক্কা ব্যাট")
_SOCIAL_MEDIA = _norm_set("ভাইরাল সোশ্যাল মিডিয়া নেটমাধ্যম নেটপাড়া")
_RAISED = tuple(normalize_text(p) for p in ("তুল", "তোল"))
_DENGUE = _norm_set("ডেঙ্গি ডেঙ্গু মশা লার্ভা ম্যালেরিয়া")
_PREVENT = _norm_set("রুখতে আটকাতে ঠেকাতে রোধে রোধ মোকাবিলা")
_VOTE = _norm_set("ভোট")
_DEMOLISHED = tuple(normalize_text(p) for p in ("ফেল", "দেওয়া", "দিল", "দেয়"))
_THIN = _norm_set("কম ফাঁকা")
_PUJA = _norm_set("পুজো পূজা দুর্গাপুজো দুর্গাপূজা প্যান্ডেল মণ্ডপ দশমী ঘাট প্রতিমা শোভাযাত্রা কার্নিভাল")
_GHAT = normalize_text("ঘাট")
_FIRE_ACCIDENT_BEFORE = _norm_set("অগ্নি अग्नि")


def _hay_words(hay: str) -> list[str]:
    return WORD_RE.findall(hay)


def _vehicle_near(hay: str, m: re.Match[str]) -> bool:
    """A vehicle within four words before or three after, in the clause ("লরির ধাক্কায়", "বাস উল্টে")."""
    return _any_in(_words_before(hay, m.start(), 4) + _words_after(hay, m.end(), 3), VEHICLE_WORDS)


def _no_vehicle_near(hay: str, m: re.Match[str]) -> bool:
    """A clash between groups: no vehicle in the clause (else it is a collision)."""
    return not _vehicle_near(hay, m)


def _not_a_fire_accident(hay: str, m: re.Match[str]) -> bool:
    """"দুর্ঘটনা" is not a road accident after "অগ্নি" (fire), nor in a report that a fire cue matches and that
    names no vehicle at all ("[WITHHELD] দুর্ঘটনা, দমকলের দশটি ইঞ্জিন"): that accident is the fire."""
    if _any_in(_words_before(hay, m.start(), 1), _FIRE_ACCIDENT_BEFORE):
        return False
    if _any_in(_hay_words(hay), VEHICLE_WORDS):
        return True
    return not any(_matches(kw, rx, hay, "fire") for row, patterns in _COMPILED if row.event_class == "fire"
                   for kw, rx in patterns)


def _not_figurative_fire(hay: str, m: re.Match[str]) -> bool:
    """No price within three words ("আগুন দাম", "সবজির দামে আগুন", "कीमतों में आग") and not spitting fire."""
    near = _words_before(hay, m.start(), 3) + _words_after(hay, m.end(), 3)
    return not _any_in(near, _PRICE_WORDS) and not _any_in(_words_after(hay, m.end(), 1), _SPITTING_FIRE)


def _not_figurative_storm(hay: str, m: re.Match[str]) -> bool:
    """Not raised by someone ("ঝড় তুলল"), not a storm of criticism, debate, praise or runs, not on social media."""
    after = _words_after(hay, m.end(), 1)
    if after and after[0].startswith(_RAISED):
        return False
    if _any_in(_words_before(hay, m.start(), 1), _FIGURATIVE_STORM_OF):
        return False
    clause = _words_before(hay, m.start(), 6) + _words_after(hay, m.end(), 6)
    return not _any_in(clause, _SOCIAL_MEDIA)


def _not_dengue_water(hay: str, m: re.Match[str]) -> bool:
    """Standing water in a dengue or mosquito report is a health notice, not waterlogging; nor is a plan to prevent
    it ("জল জমা রুখতে নতুন পাম্প": new pumps to stop waterlogging)."""
    return not _any_in(_hay_words(hay), _DENGUE) and not _any_in(_words_after(hay, m.end(), 1), _PREVENT)


def _not_a_vote_claim(hay: str, m: re.Match[str]) -> bool:
    """"ভোট লুট" is an electoral claim, never a robbery situation."""
    return not _any_in(_words_before(hay, m.start(), 1), _VOTE)


def _not_a_demolition(hay: str, m: re.Match[str]) -> bool:
    """"ভেঙে ফেলা"/"ভেঙে দেওয়া" is a demolition (an authority's work), not a collapse."""
    after = _words_after(hay, m.end(), 1)
    return not (after and after[0].startswith(_DEMOLISHED))


def _crowd_not_thin(hay: str, m: re.Match[str]) -> bool:
    """"ভিড় কম" (a thin crowd) is no gathering."""
    return not _any_in(_words_after(hay, m.end(), 1), _THIN)


def _puja_immersion(hay: str, m: re.Match[str]) -> bool:
    """"বিসর্জন" is an immersion procession only in a Puja report or at a ghat ("বাবুঘাটে"); "নিয়ম বিসর্জন" is
    rules abandoned."""
    words = _hay_words(hay)
    return _any_in(words, _PUJA) or any(st.endswith(_GHAT) for w in words for st in _stems(w))


#: Keywords that also need their context (each occurrence is checked; one good occurrence is a match): the two
#: English rules, and the Bengali and Hindi precision guards of the module docstring.
CONTEXT_RULES: Mapping[str, Callable[[str, re.Match[str]], bool]] = MappingProxyType(
    {
        "march": _not_the_month,
        "strike": _not_a_lightning_strike,
        "ধাক্কা": _vehicle_near,
        "উল্টে": _vehicle_near,
        "পিষে": _vehicle_near,
        "চাপা": _vehicle_near,
        "टक्कर": _vehicle_near,
        "দুর্ঘটনা": _not_a_fire_accident,
        "दुर्घटना": _not_a_fire_accident,
        "আগুন": _not_figurative_fire,
        "आग": _not_figurative_fire,
        "ঝড়": _not_figurative_storm,
        _WATER_COLLECTED: _not_dengue_water,
        _CAP_WATER: _not_dengue_water,
        "জমা জল": _not_dengue_water,
        "লুট": _not_a_vote_claim,
        _COLLAPSE: _not_a_demolition,
        "ভিড়": _crowd_not_thin,
        "বিসর্জন": _puja_immersion,
    }
)
#: A keyword two rows share reads its context per row: "সংঘর্ষ" is a clash between groups (public_conflict) with no
#: vehicle in its clause, and a collision (road_accident) with one.
CLASS_CONTEXT_RULES: Mapping[tuple[str, str], Callable[[str, re.Match[str]], bool]] = MappingProxyType(
    {
        ("public_conflict", "সংঘর্ষ"): _no_vehicle_near,
        ("road_accident", "সংঘর্ষ"): _vehicle_near,
    }
)


def keyword_forms(keyword: str) -> tuple[str, ...]:
    """The whole-word forms a (non-stem) keyword matches: itself, the regular inflections of its last word and its
    :data:`DERIVED_FORMS` with their plurals (see the module docstring), longest first. A keyword ending in a digit
    or a sign matches only itself; an Indic keyword is matched by its pattern (:func:`indic_slots`) and has no
    word list here."""
    k = normalize_text(keyword)
    if not k or not k[-1].isalpha() or is_indic(k):
        return (k,)
    noun = keyword in NOUN_KEYWORDS
    forms = {k + e for e in (_PLURAL_ENDINGS if noun else _ENDINGS)}
    last = k.rsplit(" ", 1)[-1]
    if len(last) >= 2 and last[-1] == "y" and last[-2] not in _VOWELS:
        forms.add(k[:-1] + "ies")
        if not noun:
            forms.add(k[:-1] + "ied")
    if not noun and _doubles(last):
        forms.update({k + k[-1] + "ed", k + k[-1] + "ing"})
    for derived in DERIVED_FORMS.get(keyword, ()):
        forms.update(normalize_text(derived) + e for e in _PLURAL_ENDINGS)
    return tuple(sorted(forms, key=lambda f: (-len(f), f)))


def _keyword_re(keyword: str) -> re.Pattern[str]:
    """A whole-word match of the keyword's forms; a stem matches the start of a word (bar its exclusions); an Indic
    keyword its slots (:func:`_indic_keyword_re`)."""
    if is_indic(keyword):
        return _indic_keyword_re(keyword)
    k = normalize_text(keyword)
    if keyword in STEM_KEYWORDS:
        never = "".join(f"(?!{re.escape(x)})" for x in STEM_KEYWORDS[keyword])
        return re.compile(r"(?<!\w)" + re.escape(k) + never)
    return re.compile(r"(?<!\w)(?:" + "|".join(re.escape(f) for f in keyword_forms(keyword)) + r")(?!\w)")


def _first_match(keyword: str, rx: re.Pattern[str], hay: str, event_class: str | None = None) -> re.Match[str] | None:
    """The first occurrence of a keyword that passes its context rule (the row's own first, else the keyword's)
    and, for an Indic keyword, is not negated; ``None`` when there is none."""
    rule = CLASS_CONTEXT_RULES.get((event_class, keyword)) if event_class else None
    rule = rule or CONTEXT_RULES.get(keyword)
    indic = is_indic(keyword)
    if rule is None and not indic:
        return rx.search(hay)
    return next(
        (m for m in rx.finditer(hay) if not (indic and _negated(hay, m)) and (rule is None or rule(hay, m))), None
    )


def _matches(keyword: str, rx: re.Pattern[str], hay: str, event_class: str | None = None) -> bool:
    return _first_match(keyword, rx, hay, event_class) is not None


_COMPILED: tuple[tuple[LexiconRow, tuple[tuple[str, re.Pattern[str]], ...]], ...] = tuple(
    (row, tuple((kw, _keyword_re(kw)) for kw in row.keywords)) for row in CLASS_LEXICON
)
_CAP_FLOOD_RES: tuple[tuple[str, re.Pattern[str]], ...] = tuple((t, _keyword_re(t)) for t in CAP_FLOOD_TERMS)
_CAP_SUBTYPE_RES: tuple[tuple[str, tuple[re.Pattern[str], ...]], ...] = tuple(
    (
        sub,
        tuple(
            _keyword_re(t) if is_indic(t) else re.compile(rf"(?<![a-z]){re.escape(t)}(?:s|y)?(?![a-z])")
            for t in terms
        ),
    )
    for sub, terms in CAP_SUBTYPES
)


def keyword_matches(keyword: str, text: str, event_class: str | None = None) -> bool:
    """Whether one lexicon keyword matches ``text`` under the rules above (the text is normalised here); a keyword
    two rows share reads the context of ``event_class``'s row."""
    return _matches(keyword, _keyword_re(keyword), normalize_text(text), event_class)


def _final_check(sahoshi_event_kind: str | None) -> None:
    """The last gate of every classification: OSINT never emits crime_incident (nor vehicle_pursuit)."""
    if sahoshi_event_kind in FORBIDDEN_OSINT_KINDS:
        raise ValueError(
            f"OSINT must never emit {sahoshi_event_kind}: crime_incident is ANPR/watchlist origin and a pursuit is "
            "human-initiated; a reported crime is reported_crime (or public_disorder) for RESPONSE"
        )


def _from_row(row: LexiconRow, matched: Sequence[str]) -> Classification:
    _final_check(row.sahoshi_event_kind)
    return Classification(
        event_class=row.event_class,  # type: ignore[arg-type]
        subtype=row.subtype,
        sahoshi_event_kind=row.sahoshi_event_kind,  # type: ignore[arg-type]
        sahoshi_incident_kind=row.sahoshi_incident_kind,  # type: ignore[arg-type]
        matched_terms=list(matched)[:64],
    )


def default_row(event_class: str) -> LexiconRow | None:
    """The first lexicon row of a class: its subtype and kinds are the class's defaults (zero-shot)."""
    for row in CLASS_LEXICON:
        if row.event_class == event_class:
            return row
    return None


def lexicon_classify(signal: RawOsintSignal) -> Classification:
    """Rules 1, 2 and 4 of the module docstring: the SACHET rule, then the lexicon, else ``general_news``."""
    hay = normalize_text(f"{signal.title} {signal.text}")
    if signal.source in CAP_SOURCES:
        if any(_matches(term, rx, hay) for term, rx in _CAP_FLOOD_RES):
            return _from_row(_CAP_FLOOD, ["CAP:flood"])
        return _from_row(_CAP_WEATHER._replace(subtype=cap_subtype(signal)), ["CAP:weather"])
    for row, patterns in _COMPILED:
        found = [(kw, m) for kw, rx in patterns if (m := _first_match(kw, rx, hay, row.event_class)) is not None]
        if found:
            return _from_row(row, [_term(kw, m) for kw, m in found])
    return Classification(event_class="general_news")


def similarity_text(signal: RawOsintSignal, limit: int = 1000) -> str:
    """The text an embedder sees for a signal: its (already redacted) title and text, normalised (no poster handle,
    no Reddit boilerplate) and bounded."""
    title = normalize_text(signal.title)
    text = normalize_text(signal.text)
    body = text if text.startswith(title) else f"{title}. {text}"
    return body[:limit]


def zero_shot_eligible(signal: RawOsintSignal) -> bool:
    """Only official and news tiers are zero-shot classified; never a social post, never a CAP alert."""
    return signal.source_tier in ZERO_SHOT_TIERS and signal.source not in CAP_SOURCES


def zero_shot(vector: np.ndarray, exemplars: np.ndarray) -> tuple[str, float] | None:
    """The nearest exemplar class of a unit vector, or ``None`` when it is not close or not clearly ahead."""
    if exemplars.shape[0] != len(_EXEMPLAR_CLASSES) or vector.shape[-1] != exemplars.shape[-1]:
        return None
    sims = exemplars @ vector
    order = np.argsort(-sims, kind="stable")
    best = float(sims[order[0]])
    second = float(sims[order[1]]) if len(order) > 1 else -1.0
    if best < ZERO_SHOT_MIN_COSINE or best - second < ZERO_SHOT_MIN_MARGIN:
        return None
    return _EXEMPLAR_CLASSES[int(order[0])], best


def _zero_shot_classification(vector: np.ndarray, exemplars: np.ndarray) -> Classification | None:
    found = zero_shot(vector, exemplars)
    if found is None:
        return None
    row = default_row(found[0])
    if row is None:  # pragma: no cover - every exemplar class has a lexicon row (tests pin it)
        return None
    return _from_row(row, [ZERO_SHOT_TERM])


def classify_with_vectors(
    signal: RawOsintSignal, vector: np.ndarray | None = None, exemplars: np.ndarray | None = None
) -> Classification:
    """:func:`classify` with the embeddings already computed (the pipeline embeds everything in one call)."""
    found = lexicon_classify(signal)
    if found.event_class != "general_news" or vector is None or exemplars is None:
        return found
    if not zero_shot_eligible(signal):
        return found
    return _zero_shot_classification(vector, exemplars) or found


def exemplar_texts() -> tuple[str, ...]:
    """The zero-shot exemplar sentences, in :data:`ZERO_SHOT_EXEMPLARS` order."""
    return _EXEMPLAR_TEXTS


def classify(signal: RawOsintSignal, *, embedder: Embedder | None = None) -> Classification:
    """``classify(signal) -> Classification``: never ``crime_incident`` (the contract of OS-4).

    With an ``embedder``, a lexicon miss from an official or news tier gets the zero-shot fallback; an embedder
    that fails (``None`` or an exception) leaves the lexicon's answer.
    """
    found = lexicon_classify(signal)
    if found.event_class != "general_news" or embedder is None or not zero_shot_eligible(signal):
        return found
    from osint_analysis.embed import unit_vectors  # local: embed imports httpx, kept off the lexicon path

    vectors = unit_vectors(embedder, [similarity_text(signal), *_EXEMPLAR_TEXTS])
    if vectors is None:
        return found
    return _zero_shot_classification(vectors[0], vectors[1:]) or found
