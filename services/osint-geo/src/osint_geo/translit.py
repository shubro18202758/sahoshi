"""Bengali and Hindi place words and transliterations for the gazetteer (stdlib only).

Kolkata text mixes English, Bengali, Hindi and Latin transliteration. The gazetteer's full place names in all three
scripts live in the City Pack (``cities/kolkata/gazetteer.json``) and the network (junction names in English and
Bengali); this module holds the reviewable word tables the matcher and the generator need besides them:

* :data:`BN_LATIN_SEED` — Bengali place names → their Latin form (junction and area names);
* :data:`PLACE_SCRIPTS` — for a Latin place word, its Bengali and Devanagari spellings (so a compositional name the
  pack does not list, "গড়িয়াহাট মোড়", reads as "gariahat crossing");
* :data:`LATIN_VARIANTS` — Latin spelling variants seen in local text ("shealdah" for "sealdah").

:data:`GENERIC_BN` and :data:`GENERIC_HI` map the generic place words of both scripts ("মোড়", "চৌরাহা") to the
gazetteer's Latin generic ("crossing"), so :func:`to_latin` can read a compositional name ("রুবি মোড়" → "ruby
crossing"). :data:`BN_SUFFIXES` lists the Bengali case endings written onto a place name ("কলকাতায়", in Kolkata;
"বেহালার", of Behala), which the gazetteer's scanner strips when the stem is a known place word.

Deliberately absent: script spellings of a place whose name is a common word in that script, and any person's name
on its own. Every multi-word Latin variant keeps a place-type word, like every gazetteer phrase.

The module also holds :func:`norm`, the one normal form of the package (``osint_geo.gazetteer`` re-exports it), so
the tables and the matcher can never disagree. Stdlib only, so ``scripts/gen_osint_gazetteer.py`` imports it
without a virtual environment change.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from types import MappingProxyType

__all__ = [
    "GENERIC_BN",
    "GENERIC_HI",
    "BN_LATIN_SEED",
    "BN_SUFFIXES",
    "LATIN_VARIANTS",
    "PLACE_SCRIPTS",
    "is_indic",
    "latin_variants",
    "norm",
    "script_aliases",
    "to_latin",
]


_NON_WORD = re.compile(r"[^\w\u0900-\u097F\u0980-\u09FF ]+")
_SPACES = re.compile(r"\s+")
_ROAD_CODE = re.compile(r"\b(nh|sh|ne)\s(\d{1,4})\b")


def _fold_latin(s: str) -> str:
    """Drop the diacritics of Latin letters ("Vastrāpur" → "Vastrapur"); every other script is left untouched
    (Bengali and Devanagari vowel signs are letters of their word, not decoration)."""
    out: list[str] = []
    for ch in s:
        if "\u00c0" <= ch <= "\u024f" or "\u1e00" <= ch <= "\u1eff":
            base = "".join(c for c in unicodedata.normalize("NFKD", ch) if not unicodedata.combining(c))
            out.append(base or ch)
        else:
            out.append(ch)
    return "".join(out)


def norm(s: object) -> str:
    """The gazetteer's normal form of a text or a surface form (re-exported as ``osint_geo.gazetteer.norm``):
    NFKC, lower case, Unicode format characters removed (a zero-width joiner never splits a word), Latin
    diacritics folded, every run of punctuation one space (Bengali and Devanagari letters and vowel signs kept),
    and a split road code joined ("NH-147" → ``nh147``)."""
    t = unicodedata.normalize("NFKC", "" if s is None else str(s)).lower()
    if not t.isascii():
        t = "".join(ch for ch in t if unicodedata.category(ch) != "Cf")
        t = _fold_latin(t)
    t = _NON_WORD.sub(" ", t).replace("_", " ")
    t = _SPACES.sub(" ", t).strip()
    return _ROAD_CODE.sub(r"\1\2", t)


_n = norm


#: Bengali place names → their Latin form (the network's junction names and the areas they are named after).
BN_LATIN_SEED: Mapping[str, str] = MappingProxyType(
    {
        _n(bn): latin
        for bn, latin in (
            ("বিবাদী বাগ", "bbd bag"),
            ("এসপ্ল্যানেড", "esplanade"),
            ("ধর্মতলা", "dharmatala"),
            ("শিয়ালদহ", "sealdah"),
            ("শিয়ালদা", "sealdah"),
            ("হাওড়া", "howrah"),
            ("কলকাতা", "kolkata"),
            ("সল্টলেক", "salt lake"),
            ("নিউ টাউন", "new town"),
            ("উল্টোডাঙা", "ultadanga"),
            ("উল্টোডাঙ্গা", "ultadanga"),
        )
    }
)

#: Latin place word (as the gazetteer carries it) → (Bengali spellings, Devanagari spellings). Full names of every
#: place are in the City Pack; these are the words a compositional name is made of.
_PLACE_SCRIPTS_SRC: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("gariahat", ("গড়িয়াহাট",), ("गड़ियाहाट", "गरियाहाट")),
    ("ruby", ("রুবি",), ("रूबी",)),
    ("hazra", ("হাজরা",), ("हाज़रा", "हाजरा")),
    ("exide", ("এক্সাইড",), ("एक्साइड",)),
    ("rashbehari", ("রাসবিহারী",), ("रासबिहारी",)),
    ("park street", ("পার্ক স্ট্রিট", "পার্ক স্ট্রীট"), ("पार्क स्ट्रीट",)),
    ("park circus", ("পার্ক সার্কাস",), ("पार्क सर्कस",)),
    ("moulali", ("মৌলালি",), ("मौलाली",)),
    ("sealdah", ("শিয়ালদহ", "শিয়ালদা"), ("सियालदह",)),
    ("shyambazar", ("শ্যামবাজার",), ("श्यामबाज़ार", "श्यामबाजार")),
    ("ultadanga", ("উল্টোডাঙা", "উল্টোডাঙ্গা"), ("उल्टाडांगा",)),
    ("chingrighata", ("চিংড়িঘাটা",), ("चिंगड़ीघाटा",)),
    ("kalighat", ("কালীঘাট", "কালিঘাট"), ("कालीघाट",)),
    ("tollygunge", ("টালিগঞ্জ",), ("टॉलीगंज",)),
    ("behala", ("বেহালা",), ("बेहाला",)),
    ("taratala", ("তারাতলা",), ("तारातला",)),
    ("majerhat", ("মাঝেরহাট",), ("माझेरहाट",)),
    ("kidderpore", ("খিদিরপুর",), ("खिदिरपुर",)),
    ("hastings", ("হেস্টিংস",), ("हेस्टिंग्स",)),
    ("esplanade", ("এসপ্ল্যানেড",), ("एस्प्लेनेड",)),
    ("dharmatala", ("ধর্মতলা",), ("धर्मतला",)),
    ("howrah", ("হাওড়া",), ("हावड़ा",)),
    ("babughat", ("বাবুঘাট",), ("बाबूघाट",)),
    ("ballygunge", ("বালিগঞ্জ",), ("बालीगंज",)),
    ("maniktala", ("মানিকতলা",), ("मानिकतला",)),
    ("girish park", ("গিরিশ পার্ক",), ("गिरीश पार्क",)),
    ("college street", ("কলেজ স্ট্রিট", "কলেজ স্ট্রীট"), ("कॉलेज स्ट्रीट",)),
    ("bagbazar", ("বাগবাজার",), ("बागबाजार",)),
    ("thanthania", ("ঠনঠনিয়া", "ঠনঠনে"), ("ठनठनिया",)),
    ("kasba", ("কসবা",), ("कसबा",)),
    ("garia", ("গড়িয়া", "গরিয়া"), ("गड़िया", "गरिया")),
    ("mukundapur", ("মুকুন্দপুর",), ("मुकुंदपुर",)),
    ("lake town", ("লেক টাউন", "লেকটাউন"), ("लेक टाउन",)),
    ("baguiati", ("বাগুইআটি",), ("बागुईआटी",)),
    ("kestopur", ("কেষ্টপুর",), ("केष्टोपुर",)),
    ("salt lake", ("সল্টলেক", "সল্ট লেক"), ("साल्ट लेक", "साल्टलेक")),
    ("new town", ("নিউ টাউন", "নিউটাউন"), ("न्यू टाउन", "न्यूटाउन")),
    ("sector v", ("সেক্টর ফাইভ",), ("सेक्टर फाइव",)),
    ("em bypass", ("ইএম বাইপাস", "ই এম বাইপাস"), ("ईएम बाईपास",)),
    ("vip road", ("ভিআইপি রোড",), ("वीआईपी रोड",)),
    ("mg road", ("এমজি রোড",), ("एमजी रोड",)),
    ("bidhan sarani", ("বিধান সরণি",), ("बिधान सरणी",)),
    ("amherst street", ("আমহার্স্ট স্ট্রিট",), ("एमहर्स्ट स्ट्रीट",)),
    ("red road", ("রেড রোড",), ("रेड रोड",)),
    ("strand road", ("স্ট্র্যান্ড রোড",), ("स्ट्रैंड रोड",)),
    ("diamond harbour road", ("ডায়মন্ড হারবার রোড",), ("डायमंड हार्बर रोड",)),
    # the script spellings of the resolver's gated forms (resolver.CONTEXT_FORMS and STATE_GATED_FORMS), as the
    # City Pack spells them: the gates read a form's spellings from here, so "रामलीला मैदान" (Delhi) or "न्यू
    # मार्केट" (Bhopal) is gated exactly as "maidan" and "new market" are
    ("maidan", ("ময়দান",), ("मैदान",)),
    ("science city", ("সায়েন্স সিটি",), ("साइंस सिटी",)),
    ("new market", ("নিউ মার্কেট",), ("न्यू मार्केट",)),
    ("central avenue", ("সেন্ট্রাল অ্যাভিনিউ",), ("सेंट्रल एवेन्यू",)),
    ("mahatma gandhi road", ("মহাত্মা গান্ধী রোড",), ("महात्मा गांधी रोड",)),
    ("gt road", ("জিটি রোড",), ("जीटी रोड",)),
    ("grand trunk road", ("গ্র্যান্ড ট্রাঙ্ক রোড",), ()),
    ("medical college", ("মেডিক্যাল কলেজ", "মেডিকেল কলেজ"), ("मेडिकल कॉलेज",)),
    ("medical college hospital", ("মেডিক্যাল কলেজ হাসপাতাল",), ()),
    ("eco park", ("ইকো পার্ক",), ("इको पार्क",)),
    ("central park mela ground", ("সেন্ট্রাল পার্ক মেলা প্রাঙ্গণ",), ("सेंट्रल पार्क मेला ग्राउंड",)),
    ("lake market", ("লেক মার্কেট",), ("लेक मार्केट",)),
    ("new alipore", ("নিউ আলিপুর",), ("न्यू अलीपुर",)),
    ("camac street", ("ক্যামাক স্ট্রিট",), ("कैमक स्ट्रीट",)),
    ("jodhpur park", ("যোধপুর পার্ক",), ("जोधपुर पार्क",)),
    ("chitpur", ("চিৎপুর",), ()),
    ("dum dum", ("দমদম", "দম দম"), ("दमदम", "दम दम")),
    ("howrah city", ("হাওড়া শহর",), ()),
)

PLACE_SCRIPTS: Mapping[str, tuple[tuple[str, ...], tuple[str, ...]]] = MappingProxyType(
    {latin: (tuple(_n(g) for g in bn), tuple(_n(h) for h in hi)) for latin, bn, hi in _PLACE_SCRIPTS_SRC}
)

#: Latin spelling variants seen in Kolkata text, per Latin form the gazetteer carries (the City Pack lists each
#: place's own variants; these are the ones that apply to every name a word appears in).
LATIN_VARIANTS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "gariahat": ("gariahaat", "goriahat"),
        "sealdah": ("shealdah", "sealdaha"),
        "behala": ("behalaa", "behela"),
        "tollygunge": ("tollyganj", "tollygunj"),
        "bidhannagar": ("bidhan nagar",),
        "ballygunge": ("ballygunj",),
        "kidderpore": ("khidirpur",),
        "em bypass": ("e m bypass", "em by pass"),
        # the Latin variants of the resolver's gated forms, so the gates hold for them too ("Newtown, Connecticut",
        # "VIP Rd" in Guwahati, a state alert's "Behela")
        "new town": ("newtown",),
        "salt lake": ("saltlake",),
        "vip road": ("v i p road", "vip rd"),
        "strand road": ("strand rd",),
        "diamond harbour road": ("diamond harbor road",),
        "garia": ("gariya",),
        "dum dum": ("dumdum",),
    }
)

#: Bengali generic place words → the gazetteer's Latin generic.
GENERIC_BN: Mapping[str, str] = MappingProxyType(
    {
        _n(bn): latin
        for bn, latin in (
            ("মোড়", "crossing"),
            ("ক্রসিং", "crossing"),
            ("চৌরাস্তা", "chowrasta"),
            ("ফাঁড়ি", "phari"),
            ("রোড", "road"),
            ("সড়ক", "road"),
            ("স্ট্রিট", "street"),
            ("স্ট্রীট", "street"),
            ("সরণি", "sarani"),
            ("অ্যাভিনিউ", "avenue"),
            ("সেতু", "bridge"),
            ("ব্রিজ", "bridge"),
            ("উড়ালপুল", "flyover"),
            ("ফ্লাইওভার", "flyover"),
            ("বাইপাস", "bypass"),
            ("স্টেশন", "station"),
            ("হাসপাতাল", "hospital"),
            ("মন্দির", "temple"),
            ("পার্ক", "park"),
            ("ঘাট", "ghat"),
            ("মার্কেট", "market"),
            ("থানা", "police station"),
            ("স্টেডিয়াম", "stadium"),
            ("ক্লাব", "club"),
        )
    }
)

#: Hindi (Devanagari) generic place words → the gazetteer's Latin generic.
GENERIC_HI: Mapping[str, str] = MappingProxyType(
    {
        _n(hi): latin
        for hi, latin in (
            ("मोड़", "crossing"),
            ("चौराहा", "crossing"),
            ("क्रॉसिंग", "crossing"),
            ("रोड", "road"),
            ("मार्ग", "road"),
            ("स्ट्रीट", "street"),
            ("सरणी", "sarani"),
            ("एवेन्यू", "avenue"),
            ("सेतु", "bridge"),
            ("पुल", "bridge"),
            ("ब्रिज", "bridge"),
            ("फ्लाईओवर", "flyover"),
            ("बाईपास", "bypass"),
            ("स्टेशन", "station"),
            ("अस्पताल", "hospital"),
            ("मंदिर", "temple"),
            ("पार्क", "park"),
            ("घाट", "ghat"),
            ("थाना", "police station"),
            ("स्टेडियम", "stadium"),
            ("क्लब", "club"),
        )
    }
)

#: Bengali case endings written onto a noun (longest first): "কলকাতায়" (in Kolkata), "বেহালার" (of Behala),
#: "শহরের" (of the city), "রাস্তাতে" (on the road), "পুলিশকে" (to the police). The scanner strips one only when what
#: remains is a gazetteer word. "য়" may be one code point or "য" + nukta; NFKC makes them one form. The same list as
#: ``osint_common.ethics.INDIC_SUFFIXES`` (a lockstep test pins the two equal).
BN_SUFFIXES: tuple[str, ...] = tuple(
    sorted(
        {
            _n(s)
            for s in ("য়ের", "য়ে", "য়", "তেই", "তে", "দের", "গুলো", "গুলি", "টির", "টি", "টা", "কে", "রা", "এর", "ের", "র",
                      "এ", "ে", "েই", "ই")
        },
        key=len,
        reverse=True,
    )
)


def _script_words() -> Mapping[str, str]:
    """Script word or phrase → Latin, for :func:`to_latin`: place names and generics of both scripts, the PoC seed
    winning on a clash."""
    words: dict[str, str] = {}
    for latin, (bn, hi) in PLACE_SCRIPTS.items():
        for s in bn + hi:
            words.setdefault(s, latin)
    for s, latin in (*GENERIC_BN.items(), *GENERIC_HI.items()):
        words.setdefault(s, latin)
    words.update(BN_LATIN_SEED)
    return MappingProxyType(words)


def _aliases() -> Mapping[str, tuple[str, ...]]:
    """Latin form → its Bengali and Devanagari spellings (the place table, then the PoC seed)."""
    out: dict[str, tuple[str, ...]] = {
        latin: tuple(dict.fromkeys(bn + hi)) for latin, (bn, hi) in PLACE_SCRIPTS.items()
    }
    for bn, latin in BN_LATIN_SEED.items():
        out[latin] = tuple(dict.fromkeys((*out.get(latin, ()), bn)))
    return MappingProxyType(out)


_WORDS = _script_words()
_MAX_WORD_TOKENS = max(k.count(" ") + 1 for k in _WORDS)
_ALIASES = _aliases()
_INDIC = re.compile(r"[\u0900-\u097F\u0980-\u09FF]")


def is_indic(s: str) -> bool:
    """True when ``s`` contains a Devanagari or Bengali character."""
    return _INDIC.search(s) is not None


def script_aliases(latin_form: str) -> tuple[str, ...]:
    """The Bengali and Devanagari spellings of a Latin gazetteer form (normalised), or ``()``."""
    return _ALIASES.get(_n(latin_form), ())


def latin_variants(latin_form: str) -> tuple[str, ...]:
    """The Latin spelling variants of a Latin gazetteer form (normalised), or ``()``."""
    return LATIN_VARIANTS.get(_n(latin_form), ())


def to_latin(name: str) -> str | None:
    """A Bengali or Hindi place name → its Latin form: a whole-name lookup, else word by word over the place and
    generic tables ("রুবি মোড়" → "ruby crossing"). ``None`` unless every word is known: a partial transliteration
    would be a guess."""
    key = _n(name or "")
    if not key:
        return None
    if key in _WORDS:
        return _WORDS[key]
    toks = key.split(" ")
    out: list[str] = []
    i = 0
    while i < len(toks):
        for j in range(min(len(toks), i + _MAX_WORD_TOKENS), i, -1):
            latin = _WORDS.get(" ".join(toks[i:j]))
            if latin is not None:
                out.append(latin)
                i = j
                break
        else:
            return None
    return " ".join(out)
