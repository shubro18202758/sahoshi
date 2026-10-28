"""Which part of West Bengal an official alert names: a Kolkata-area district, the state, or neither.

The official feeds Sahoshi reads cover more than the city: NDMA SACHET publishes one all-India CAP RSS (the West
Bengal file is not published under a known name), and IMD's CAP feed covers every state. :func:`match_area` reads
an alert's own text (title, description, CAP headline and ``areaDesc``) and answers:

* the **metro districts** it names, as ``osint_common.kinds.AREA_DISTRICTS`` codes (``LGD:KOLKATA``,
  ``LGD:HOWRAH``, ``LGD:NORTH_24_PARGANAS``, ``LGD:SOUTH_24_PARGANAS``), matched on the spellings listed there;
* whether it is a **West Bengal** alert at all: a metro district, the state's name, or any other district of the
  state (:data:`WB_OTHER_DISTRICTS`, English and Bengali spellings). Such an alert that names no metro district
  is state-level (``kinds.AREA_STATE_CODE``, ``LGD:WEST_BENGAL``): a nowcast for Bankura or Purba Medinipur is
  not a Kolkata location, and the analysis holds it as outside the city;
* anything else (an Odisha, Andhra Pradesh or Andaman and Nicobar alert, all of which reach the all-India feed,
  some issued by IMD's Kolkata office) is **outside the area** and is not emitted.

Matching runs on a normal form: NFKC (so "ড়" written as one code point or as "ড" + nukta is the same letter, as
``AREA_DISTRICTS`` asks), lower case, Bengali and Devanagari digits as ASCII digits, hyphens as spaces, Unicode
format characters (ZWJ, ZWNJ) dropped, whitespace collapsed. A Latin-script name matches as a whole word; an
Indic-script name matches at the start of a word, so a case ending stays attached ("কলকাতায়", in Kolkata). IMD's
Bengali nowcasts join two districts of one name ("উত্তর ও দক্ষিণ ২৪ পরগনা", "North and South 24 Parganas");
:func:`normal_form` writes both out first, so each one is read.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import lru_cache

from osint_common.kinds import AREA_DISTRICTS, AREA_STATE_CODE

__all__ = [
    "AreaMatch",
    "DISTRICT_NAMES",
    "WB_OTHER_DISTRICTS",
    "WB_STATE_NAMES",
    "area_hint",
    "match_area",
    "normal_form",
]

#: The English name a district code is shown with (``RawGeoHint.place_names``).
DISTRICT_NAMES: dict[str, str] = {
    "LGD:KOLKATA": "Kolkata",
    "LGD:HOWRAH": "Howrah",
    "LGD:NORTH_24_PARGANAS": "North 24 Parganas",
    "LGD:SOUTH_24_PARGANAS": "South 24 Parganas",
}

#: The state's own names. Never a bare "Bengal": "Bay of Bengal" names the sea, not the state.
WB_STATE_NAMES: tuple[str, ...] = (
    "west bengal", "gangetic west bengal", "sub himalayan west bengal", "পশ্চিমবঙ্গ", "পশ্চিমবাংলা",
    "পশ্চিম বাংলা", "पश्चिम बंगाल",
)

#: The other districts of West Bengal (everything outside the four metro districts), English spellings in use
#: (IMD, NDMA and news) and Bengali ones. Bengali alerts join two districts of one name ("পূর্ব ও পশ্চিম
#: মেদিনীপুর"), so the shared stems (মেদিনীপুর, বর্ধমান, দিনাজপুর) are listed on their own: either half is a
#: West Bengal district. Used only to tell a West Bengal alert from another state's, never as a location.
WB_OTHER_DISTRICTS: tuple[str, ...] = (
    "alipurduar", "alipurduars", "bankura", "birbhum", "cooch behar", "coochbehar", "koch bihar", "darjeeling",
    "darjiling", "dakshin dinajpur", "uttar dinajpur", "dinajpur", "hooghly", "hugli", "jalpaiguri", "jhargram",
    "kalimpong", "malda", "maldah", "murshidabad", "nadia", "purba bardhaman", "paschim bardhaman", "bardhaman",
    "burdwan", "purba medinipur", "paschim medinipur", "medinipur", "midnapore", "midnapur", "purulia",
    "আলিপুরদুয়ার", "বাঁকুড়া", "বীরভূম", "কোচবিহার", "দার্জিলিং", "দিনাজপুর", "হুগলি", "হুগলী", "জলপাইগুড়ি",
    "ঝাড়গ্রাম", "কালিম্পং", "মালদা", "মালদহ", "মুর্শিদাবাদ", "নদিয়া", "নদীয়া", "বর্ধমান", "মেদিনীপুর",
    "পুরুলিয়া",
)

#: Short forms in IMD's English bulletins ("N 24 Pgs", "S 24 Pgs") for the two Parganas districts.
_EXTRA_SPELLINGS: dict[str, tuple[str, ...]] = {
    "LGD:NORTH_24_PARGANAS": ("n 24 pgs", "north 24 pgs", "n 24 parganas", "উত্তর ২৪ পরগণা"),
    "LGD:SOUTH_24_PARGANAS": ("s 24 pgs", "south 24 pgs", "s 24 parganas", "দক্ষিণ ২৪ পরগণা"),
}

_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯०१२३४५६७८९", "01234567890123456789")
_WS = re.compile(r"\s+")
#: "উত্তর ও দক্ষিণ ২৪ পরগনা" (after digit folding: "উত্তর ও দক্ষিণ 24 পরগনা"), either order, "ও"/"এবং"/","
_BN_PAIR = re.compile(
    r"(উত্তর|দক্ষিণ)\s*(?:ও|এবং|আর|,)\s*(উত্তর|দক্ষিণ)\s*(24|চব্বিশ)\s*(পরগনা|পরগণা)"
)
#: "north and south 24 parganas" / "south & north 24 pgs"
_EN_PAIR = re.compile(r"\b(north|south)\s*(?:and|&|,)\s*(north|south)\s*(24|twenty four)\s*(parganas|pgs)\b")


def normal_form(text: str) -> str:
    """The matching form of ``text`` (module docstring): NFKC, lower case, ASCII digits, joined pairs written out."""
    s = unicodedata.normalize("NFKC", text or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Cf").lower().translate(_DIGITS)
    s = _WS.sub(" ", s.replace("-", " ")).strip()
    s = _BN_PAIR.sub(lambda m: f"{m[1]} {m[3]} {m[4]} ও {m[2]} {m[3]} {m[4]}", s)
    return _EN_PAIR.sub(lambda m: f"{m[1]} {m[3]} {m[4]} and {m[2]} {m[3]} {m[4]}", s)


def _pattern(names: Iterable[str]) -> re.Pattern[str] | None:
    parts: list[str] = []
    for name in sorted({normal_form(n) for n in names if n}, key=len, reverse=True):
        body = r"\s+".join(re.escape(w) for w in name.split())
        if name.isascii():
            parts.append(rf"(?<![a-z0-9]){body}(?![a-z0-9])")
        else:
            # an Indic name starts a word; a case ending may follow it ("কলকাতায়", "হাওড়ার")
            parts.append(rf"(?<![ऀ-ൿ]){body}")
    return re.compile("|".join(parts)) if parts else None


@lru_cache(maxsize=1)
def _patterns() -> tuple[tuple[tuple[str, re.Pattern[str]], ...], re.Pattern[str]]:
    districts = []
    for code, names in AREA_DISTRICTS.items():
        rx = _pattern((*names, *_EXTRA_SPELLINGS.get(code, ())))
        if rx is not None:
            districts.append((code, rx))
    state = _pattern((*WB_STATE_NAMES, *WB_OTHER_DISTRICTS))
    assert state is not None
    return tuple(districts), state


@dataclass(frozen=True)
class AreaMatch:
    """What :func:`match_area` found. ``districts`` keep ``AREA_DISTRICTS`` order."""

    districts: tuple[str, ...] = ()
    west_bengal: bool = False
    #: the English names of the districts (``RawGeoHint.place_names``), or ``("West Bengal",)`` at state level
    place_names: tuple[str, ...] = field(default=())

    @property
    def in_area(self) -> bool:
        """A West Bengal alert (a metro district or the state): emitted. Otherwise outside the area: not emitted."""
        return self.west_bengal

    @property
    def admin_codes(self) -> list[str]:
        """The metro district codes it names, else the state code."""
        return list(self.districts) if self.districts else [AREA_STATE_CODE]


def match_area(*texts: str | None) -> AreaMatch:
    """Read the alert's texts (module docstring). Never raises."""
    hay = normal_form(" \n ".join(t for t in texts if t))
    if not hay:
        return AreaMatch()
    district_rxs, state_rx = _patterns()
    districts = tuple(code for code, rx in district_rxs if rx.search(hay))
    west_bengal = bool(districts) or state_rx.search(hay) is not None
    names = tuple(DISTRICT_NAMES[c] for c in districts) if districts else (("West Bengal",) if west_bengal else ())
    return AreaMatch(districts=districts, west_bengal=west_bengal, place_names=names)


def area_hint(match: AreaMatch) -> list[str]:
    """``area:<district>`` for each metro district (``area:kolkata``, ``area:north_24_parganas``), else
    ``area:west_bengal``; nothing outside the area."""
    if match.districts:
        return [f"area:{c.removeprefix('LGD:').lower()}" for c in match.districts]
    return ["area:west_bengal"] if match.west_bengal else []
