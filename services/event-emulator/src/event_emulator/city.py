"""Kolkata, as the emulator needs it: one place for the city's constants.

Names, ids and formats follow the Kolkata city pack (``cities/kolkata/
city.json`` and ``landmarks.json``): the emulator never invents a place,
an agency or a plate format of its own.  ``tests/test_city.py`` checks the
copies below against the pack whenever the repository is present.

Everything the emulator produces is EMULATED (a feed stand-in) or
SIMULATED (a scenario); the few numbers here that model the city (the tide
phase, the Puja calendar) say so where they are defined.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

__all__ = [
    "IST",
    "UNIT_ROLES",
    "UnitRole",
    "unit_label",
    "unit_role",
    "CITY_ID",
    "CITY_NAME",
    "FALLBACK_ANCHOR",
    "M_PER_DEG_LAT",
    "M_PER_DEG_LON",
    "PLATE_STATE",
    "PLATE_RTO_CODES",
    "PLATE_MARKER",
    "emulated_plate",
    "STOLEN_FIR_PLATE",
    "EARMARK_EXERCISE_PLATE",
    "STOLEN_FIR_REF",
    "PATROL_AGENCY",
    "PATROL_AGENCY_LABEL",
    "PATROL_UNIT_PREFIX",
    "PLACES",
    "place_name",
    "PUJA_NIGHTS",
    "puja_night_of",
    "is_monsoon",
    "M2_PERIOD_SEC",
    "tide_index",
]

#: India Standard Time: a fixed offset, no DST (no tz database needed).
IST = timezone(timedelta(hours=5, minutes=30))

CITY_ID = "kolkata"
CITY_NAME = {"en": "Kolkata", "bn": "কলকাতা", "hi": "कोलकाता"}

#: (lon, lat) of Esplanade (landmarks.json ``esplanade``): where an
#: anchor-less tape places its reads, deterministic on every host.
FALLBACK_ANCHOR = (88.3512, 22.5646)

#: Metres per degree on Kolkata's latitude belt: 111 320 m per degree of
#: latitude; longitude shrinks by cos(22.5726 deg) = 0.9234 (a fixed
#: factor, so every host computes identical positions).
M_PER_DEG_LAT = 111320.0
M_PER_DEG_LON = 111320.0 * 0.9234

# ── number plates (city.json ``plates``) ────────────────────────────────────

#: West Bengal marks: ``WB NN X[X] NNNN``.  The emulator writes them compact
#: (``WB02EM1234``, the form the oracle normalises every read to).
PLATE_STATE = "WB"
#: Plausible office codes only (WB-01..WB-08, WB-11/12).  The emulator never
#: infers an office, a district or an owner from a code.
PLATE_RTO_CODES = ("01", "02", "03", "04", "05", "06", "07", "08", "11", "12")
#: Every emulated plate carries the EM series right after the office code,
#: so a synthetic mark is self-labelling wherever it surfaces (``plate[4:6]``).
PLATE_MARKER = "EM"


def emulated_plate(rto: str, number: int) -> str:
    """An emulated WB mark: ``WB`` + office code + ``EM`` + 4 digits."""
    if rto not in PLATE_RTO_CODES:
        raise ValueError(f"office code {rto!r} is not one the emulator uses")
    return f"{PLATE_STATE}{rto}{PLATE_MARKER}{int(number) % 10000:04d}"


#: The demo plate a stolen-vehicle FIR names (the watchlist sweep's premise:
#: its stolen-FIR earmark is ensured at t0 as a labelled EMULATED
#: precondition, so its reads are evidence-only sightings, never a fine).
STOLEN_FIR_PLATE = "WB06EM9001"
#: The demo plate an operator earmark exercise names: its reads hit only once
#: a named duty officer has earmarked it.  The emulator never does.
EARMARK_EXERCISE_PLATE = "WB02EM4321"
#: The (emulated) FIR the sweep's premise names: a scenario reference, not a
#: real case.
STOLEN_FIR_REF = "FIR 4401/2026, Hare Street PS"

# ── agencies (city.json ``agencies``) ───────────────────────────────────────

#: Emulated patrol beats are Kolkata Traffic Police units: the C-A agency
#: code ``traffic`` (the oracle's closed agency registry).
PATROL_AGENCY = "traffic"
PATROL_AGENCY_LABEL = "Kolkata Traffic Police"
#: Unit ids carry the EM marker like every emulated plate.
PATROL_UNIT_PREFIX = "KTP-EM"


@dataclass(frozen=True)
class UnitRole:
    """What a living-city field unit is, from its id prefix (C-A agency code,
    label prefix, C-A status while it rides its beat, beat speed).  Speeds
    are MODELLED urban averages, not measurements."""

    agency: str
    label: str
    status: str
    speed_kmh: float
    beat_word: str


#: The living city's emulated field units by unit-id prefix (longest prefix
#: first).  Agencies are the oracle's closed C-A registry; statuses its
#: closed vocabulary ('available' is an ambulance (108) on a standby
#: circuit, not on a call).  Every id carries the EM marker.
UNIT_ROLES: tuple[tuple[str, UnitRole], ...] = (
    ("KP-EM-PCR", UnitRole("police", "Kolkata Police PCR", "patrol", 22.0, "beat")),
    ("108-EM-LC", UnitRole("ambulance", "Ambulance (108)", "available", 24.0, "standby circuit")),
    (PATROL_UNIT_PREFIX, UnitRole(PATROL_AGENCY, PATROL_AGENCY_LABEL, "patrol", 18.0, "beat")),
)


def unit_role(unit_id: str) -> UnitRole:
    """The role of a living-city unit id (ValueError on an unknown prefix)."""
    for prefix, role in UNIT_ROLES:
        if unit_id.startswith(prefix):
            return role
    raise ValueError(f"no living-city role for unit id {unit_id!r}")


def unit_label(unit_id: str, beat: str) -> str:
    """The unit's C-A label: '<agency> <id> · <beat> beat' (traffic and
    police) or '<agency> <id> · standby circuit, <roads>' (ambulance)."""
    role = unit_role(unit_id)
    if role.beat_word == "beat":
        return f"{role.label} {unit_id} · {beat} beat"
    return f"{role.label} {unit_id} · {role.beat_word}, {beat}"

# ── places (landmarks.json, verbatim) ───────────────────────────────────────

#: The landmarks the scenarios and the living city name, copied verbatim
#: from ``cities/kolkata/landmarks.json`` (id -> en / bn).
PLACES: dict[str, dict[str, str]] = {
    "esplanade": {"en": "Esplanade", "bn": "এসপ্ল্যানেড"},
    "bbd_bag": {"en": "BBD Bag", "bn": "বিবাদী বাগ"},
    "howrah_bridge": {"en": "Howrah Bridge", "bn": "হাওড়া ব্রিজ"},
    "vidyasagar_setu": {"en": "Vidyasagar Setu", "bn": "বিদ্যাসাগর সেতু"},
    "howrah_station": {"en": "Howrah Station", "bn": "হাওড়া স্টেশন"},
    "sealdah": {"en": "Sealdah", "bn": "শিয়ালদহ"},
    "park_street": {"en": "Park Street crossing", "bn": "পার্ক স্ট্রিট মোড়"},
    "exide": {"en": "Exide crossing", "bn": "এক্সাইড মোড়"},
    "hazra": {"en": "Hazra crossing", "bn": "হাজরা মোড়"},
    "rashbehari": {"en": "Rashbehari crossing", "bn": "রাসবিহারী মোড়"},
    "gariahat": {"en": "Gariahat crossing", "bn": "গড়িয়াহাট মোড়"},
    "ruby": {"en": "Ruby crossing", "bn": "রুবি মোড়"},
    "park_circus": {"en": "Park Circus seven-point crossing", "bn": "পার্ক সার্কাস সাত মাথার মোড়"},
    "moulali": {"en": "Moulali", "bn": "মৌলালি"},
    "chingrighata": {"en": "Chingrighata", "bn": "চিংড়িঘাটা"},
    "ultadanga": {"en": "Ultadanga", "bn": "উল্টোডাঙা"},
    "shyambazar": {"en": "Shyambazar five-point crossing", "bn": "শ্যামবাজার পাঁচ মাথার মোড়"},
    "kalighat": {"en": "Kalighat", "bn": "কালীঘাট"},
    "tollygunge": {"en": "Tollygunge", "bn": "টালিগঞ্জ"},
    "behala_chowrasta": {"en": "Behala Chowrasta", "bn": "বেহালা চৌরাস্তা"},
    "taratala": {"en": "Taratala", "bn": "তারাতলা"},
    "majerhat": {"en": "Majerhat bridge", "bn": "মাঝেরহাট সেতু"},
    "kidderpore": {"en": "Kidderpore", "bn": "খিদিরপুর"},
    "red_road": {"en": "Red Road", "bn": "রেড রোড"},
    "nabanna": {"en": "Nabanna", "bn": "নবান্ন"},
    "airport": {"en": "Kolkata Airport", "bn": "কলকাতা বিমানবন্দর"},
    "kestopur": {"en": "VIP Road, Kestopur", "bn": "ভিআইপি রোড, কেষ্টপুর"},
    "sector_v": {"en": "Sector V, Salt Lake", "bn": "সেক্টর ফাইভ, সল্টলেক"},
    "biswa_bangla_sarani": {"en": "Biswa Bangla Sarani, New Town",
                            "bn": "বিশ্ব বাংলা সরণি, নিউ টাউন"},
    "science_city": {"en": "Science City", "bn": "সায়েন্স সিটি"},
    "eden_gardens": {"en": "Eden Gardens", "bn": "ইডেন গার্ডেন্স"},
    "salt_lake_stadium": {"en": "Salt Lake Stadium", "bn": "যুবভারতী ক্রীড়াঙ্গন"},
    "victoria_memorial": {"en": "Victoria Memorial", "bn": "ভিক্টোরিয়া মেমোরিয়াল"},
    "babughat": {"en": "Babughat", "bn": "বাবুঘাট"},
    "prinsep_ghat": {"en": "Prinsep Ghat", "bn": "প্রিন্সেপ ঘাট"},
    "lalbazar": {"en": "Lalbazar (Kolkata Police HQ)", "bn": "লালবাজার (কলকাতা পুলিশ সদর)"},
    "sskm": {"en": "SSKM Hospital", "bn": "এসএসকেএম হাসপাতাল"},
    "medical_college": {"en": "Kolkata Medical College", "bn": "কলকাতা মেডিকেল কলেজ"},
    "nrs": {"en": "NRS Medical College", "bn": "এনআরএস মেডিকেল কলেজ"},
    "bagbazar": {"en": "Bagbazar Sarbojanin", "bn": "বাগবাজার সর্বজনীন"},
    "kumartuli": {"en": "Kumartuli Park", "bn": "কুমোরটুলি পার্ক"},
    "santosh_mitra_square": {"en": "Santosh Mitra Square", "bn": "সন্তোষ মিত্র স্কোয়্যার"},
    "college_square": {"en": "College Square", "bn": "কলেজ স্কোয়্যার"},
    "deshapriya_park": {"en": "Deshapriya Park", "bn": "দেশপ্রিয় পার্ক"},
    "ekdalia": {"en": "Ekdalia Evergreen", "bn": "একডালিয়া এভারগ্রিন"},
    "garden_reach": {"en": "Garden Reach (tide)", "bn": "গার্ডেন রিচ (জোয়ার)"},
    "ballygunge": {"en": "Ballygunge Phari", "bn": "বালিগঞ্জ ফাঁড়ি"},
    "thanthania": {"en": "Thanthania (low-lying)", "bn": "ঠনঠনিয়া (নিচু এলাকা)"},
}


def place_name(place_id: str, lang: str = "en") -> str:
    """A landmark's canonical name (``KeyError`` for an unknown id: the
    emulator never names a place the city pack does not)."""
    return PLACES[place_id][lang]


# ── the city's calendar ─────────────────────────────────────────────────────

#: Durga Puja nights (Saptami, Ashtami, Navami) by year.  The almanac
#: (panjika) sets them each year; 2025 is the observed calendar, 2026 is
#: an APPROXIMATION from the lunar calendar (±1 day) — confirm against the
#: year's panjika, or override with EMULATOR_PUJA_NIGHTS.  A Puja night runs
#: 18:00 to 04:00 the next morning.
PUJA_NIGHTS: dict[int, tuple[date, ...]] = {
    2025: (date(2025, 9, 29), date(2025, 9, 30), date(2025, 10, 1)),
    2026: (date(2026, 10, 17), date(2026, 10, 18), date(2026, 10, 19)),
}

#: Puja crowds peak from 18:00 into the small hours.
PUJA_NIGHT_START_H = 18.0
PUJA_NIGHT_END_H = 4.0


def puja_night_of(d: date, hour: float, nights: tuple[date, ...] | None = None) -> date | None:
    """The Puja night (its evening's date) that IST ``d`` at ``hour`` falls
    in, or None.  ``nights`` overrides the calendar (the config's list)."""
    pool = nights if nights is not None else PUJA_NIGHTS.get(d.year, ()) + PUJA_NIGHTS.get(
        d.year - 1, ())
    if hour >= PUJA_NIGHT_START_H and d in pool:
        return d
    prev = d - timedelta(days=1)
    if hour < PUJA_NIGHT_END_H and prev in pool:
        return prev
    return None


def is_monsoon(d: date) -> bool:
    """Kolkata's south-west monsoon months: June to September."""
    return 6 <= d.month <= 9


#: The Hooghly is tidal at Kolkata: at high water the outfalls close and the
#: pumps work against the river, so rain then waterlogs worse.  The emulator
#: uses a MODELLED semidiurnal phase (the M2 period, 12 h 25 min) from a fixed
#: reference high water; it is not the Garden Reach tide table (the hydro
#: service carries the real tide model).
M2_PERIOD_SEC = 44712.0
_TIDE_REFERENCE_HW = datetime(2026, 1, 1, 6, 0, tzinfo=IST)


def tide_index(t: datetime) -> float:
    """MODELLED tide phase at ``t``: 1.0 at high water, 0.0 at low water."""
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    phase = ((t - _TIDE_REFERENCE_HW).total_seconds() % M2_PERIOD_SEC) / M2_PERIOD_SEC
    return round(0.5 * (1.0 + math.cos(2.0 * math.pi * phase)), 4)
