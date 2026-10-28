"""Place matching for field reports: which Kolkata place did the officer name?

Sources, in precedence order:
1. ``cities/kolkata/landmarks.json``: the canonical ids and spellings.
2. ``cities/kolkata/gazetteer.json`` (events stream), when present. Its shape
   is read tolerantly; entries without coordinates are skipped and a
   landmark id always wins over a gazetteer entry with the same id.
3. :data:`ALIASES` below: everyday names officers actually say
   ("ধর্মতলা" for Esplanade, "ডালহৌসি" for BBD Bag, "যুবভারতী" …).

Matching works across scripts. A transcript in Bengali script, a romanised
one ("Gariahat more e hatu jol") or an English one is cut into word windows,
and each window is compared with every name in two ways:

* a light same-script comparison (Bengali spelling variants that ASR mixes
  up — ী/ি, ূ/ু, ড়/র, ণ/ন, শ/ষ/স, chandrabindu — are folded first);
* a cross-script **consonant skeleton**: both scripts are mapped to a loose
  Latin consonant string with vowels dropped (গড়িয়াহাট → ``grht``,
  "Gariahat" → ``grht``). Vowels are what Bengali ASR gets wrong most often
  and what romanisation varies most in, so the skeleton ignores them.

The best window/name pair gives ``match_score`` in [0, 1]. Below the
threshold (0.80 by default) no place is asserted; the top candidates are
still returned for the officer to pick from.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

__all__ = [
    "Place",
    "PlaceMatch",
    "Gazetteer",
    "skeleton",
    "fold_bn",
    "ALIASES",
    "load_gazetteer",
]

log = logging.getLogger("speech.places")

_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

# Everyday names, keyed by landmarks.json id. Spoken forms only; the
# canonical names come from landmarks.json itself.
ALIASES: dict[str, list[str]] = {
    "esplanade": ["ধর্মতলা", "Dharmatala", "Dharmatolla", "এসপ্ল্যানেড মোড়"],
    "bbd_bag": ["ডালহৌসি", "Dalhousie", "বিবাদীবাগ", "B B D Bag"],
    "howrah_bridge": ["রবীন্দ্র সেতু", "Rabindra Setu", "হাওড়া সেতু"],
    "vidyasagar_setu": ["দ্বিতীয় হুগলি সেতু", "Second Hooghly Bridge", "বিদ্যাসাগর ব্রিজ", "Vidyasagar bridge"],
    "howrah_station": ["Howrah station"],
    "sealdah": ["শিয়ালদা", "শেয়ালদা", "শিয়ালদহ স্টেশন", "Sealdah station"],
    "park_street": ["পার্ক স্ট্রিট", "Park Street"],
    "exide": ["এক্সাইড", "Exide more"],
    "hazra": ["হাজরা", "Hazra more"],
    "rashbehari": ["রাসবিহারী", "Rash Behari", "রাসবিহারী অ্যাভিনিউ", "Rashbehari Avenue"],
    "gariahat": ["গড়িয়াহাট", "Gariahat more"],
    "ruby": ["রুবি হাসপাতাল", "Ruby more", "Ruby hospital crossing"],
    "park_circus": ["পার্ক সার্কাস", "Park Circus", "সাত মাথার মোড়"],
    "moulali": ["মৌলালি মোড়", "Moulali crossing"],
    "chingrighata": ["চিংড়িঘাটা মোড়", "Chingrighata crossing"],
    "ultadanga": ["উল্টাডাঙা", "উল্টাডাঙ্গা", "Ultadanga crossing"],
    "shyambazar": ["শ্যামবাজার", "Shyambazar", "শ্যামবাজার মোড়", "পাঁচ মাথার মোড়"],
    "kalighat": ["কালীঘাট মোড়"],
    "tollygunge": ["টলিগঞ্জ", "Tollygunj", "টালিগঞ্জ মোড়"],
    "behala_chowrasta": ["বেহালা", "Behala", "বেহালা চৌরাস্তা মোড়"],
    "taratala": ["তারাতলা মোড়", "Taratala crossing"],
    "majerhat": ["মাঝেরহাট", "মাঝেরহাট ব্রিজ", "Majerhat", "Majerhat flyover"],
    "kidderpore": ["Khidirpur", "খিদিরপুর মোড়"],
    "red_road": ["Red Road"],
    "nabanna": ["Nabanna"],
    "airport": ["বিমানবন্দর", "এয়ারপোর্ট", "দমদম বিমানবন্দর", "Dum Dum airport", "Airport"],
    "kestopur": ["কেষ্টপুর", "Kestopur", "ভিআইপি রোড", "VIP Road"],
    "sector_v": ["সেক্টর ফাইভ", "সেক্টর 5", "Sector 5", "Sector Five", "Sector V"],
    "biswa_bangla_sarani": ["বিশ্ব বাংলা সরণি", "নিউ টাউন", "নিউটাউন", "New Town", "Newtown"],
    "science_city": ["সায়েন্স সিটি মোড়", "Science City crossing"],
    "eden_gardens": ["ইডেন", "Eden"],
    "salt_lake_stadium": ["যুবভারতী", "Yuva Bharati", "Yuba Bharati", "সল্টলেক স্টেডিয়াম", "Salt Lake stadium"],
    "victoria_memorial": ["ভিক্টোরিয়া", "Victoria"],
    "babughat": ["Babu Ghat"],
    "prinsep_ghat": ["প্রিন্সেপ ঘাট", "Prinsep Ghat"],
    "lalbazar": ["লালবাজার", "Lalbazar"],
    "sskm": ["এসএসকেএম", "পিজি হাসপাতাল", "PG hospital", "SSKM"],
    "medical_college": ["মেডিক্যাল কলেজ", "মেডিকেল কলেজ", "Medical College"],
    "nrs": ["এনআরএস", "NRS"],
    "bagbazar": ["বাগবাজার"],
    "kumartuli": ["কুমোরটুলি", "Kumortuli"],
    "santosh_mitra_square": ["সন্তোষ মিত্র স্কোয়ার"],
    "college_square": ["কলেজ স্কোয়ার", "College Square"],
    "deshapriya_park": ["দেশপ্রিয় পার্ক", "Deshapriya Park"],
    "ekdalia": ["একডালিয়া", "Ekdalia"],
    "garden_reach": ["গার্ডেন রিচ", "Garden Reach"],
    "ballygunge": ["বালিগঞ্জ ফাঁড়ি", "বালিগঞ্জ", "Ballygunge"],
    "thanthania": ["ঠনঠনিয়া", "ঠনঠনে", "Thanthania"],
}

# Words that name a kind of place, not a place. A window made only of these
# never matches, and they are dropped from a name to form its short form.
GENERIC = {
    "মোড়", "মোড়ে", "মোড়ের", "মোর", "রাস্তা", "রাস্তায়", "রোড", "রোডে", "ব্রিজ", "ব্রিজে",
    "সেতু", "সেতুর", "স্টেশন", "স্টেশনে", "এলাকা", "এলাকায়", "কাছে", "সামনে", "পাশে",
    "crossing", "junction", "more", "mor", "road", "rd", "bridge", "station", "area", "near",
    "the", "at", "on", "in", "five-point", "seven-point", "point", "ghat",
}

_WORD_RE = re.compile(r"[\wঀ-৿‌‍]+", re.UNICODE)

# --- script folding ----------------------------------------------------------

_NUKTA_PAIRS = {
    "ড়": "ড়",  # ড় (decomposed) → precomposed
    "ঢ়": "ঢ়",  # ঢ়
    "য়": "য়",  # য়
}

_BN_FOLD = str.maketrans({
    "ী": "ি", "ূ": "ু", "ঈ": "ই", "ঊ": "উ", "ণ": "ন", "ষ": "স", "শ": "স",
    "ড়": "র", "ঢ়": "র", "য়": "য", "ঁ": None, "‌": None, "‍": None,
    "ৎ": "ত", "ঙ": "ং", "ঃ": None,
})


def _bn_compose(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    for k, v in _NUKTA_PAIRS.items():
        s = s.replace(k, v)
    return s


def fold_bn(s: str) -> str:
    """Bengali spelling folding used for same-script comparison."""
    return _bn_compose(s).translate(_BN_FOLD).translate(_BN_DIGITS)


_BN_CONS = {
    "ক": "k", "খ": "k", "গ": "g", "ঘ": "g", "ঙ": "n", "চ": "c", "ছ": "c", "জ": "j", "ঝ": "j",
    "ঞ": "n", "ট": "t", "ঠ": "t", "ড": "d", "ঢ": "d", "ণ": "n", "ত": "t", "থ": "t", "দ": "d",
    "ধ": "d", "ন": "n", "প": "p", "ফ": "f", "ব": "b", "ভ": "b", "ম": "m", "য": "j", "র": "r",
    "ল": "l", "শ": "s", "ষ": "s", "স": "s", "হ": "h", "ড়": "r", "ঢ়": "r", "য়": "",
    "ৎ": "t", "ং": "n", "ৰ": "r", "ৱ": "b",
}
_BN_VOWELS = set("অআইঈউঊঋএঐওঔািীুূৃেৈোৌ")
_HASANTA = "্"

_LAT_DIGRAPHS = [
    ("chh", "C"), ("ch", "C"), ("sh", "s"), ("kh", "k"), ("gh", "g"), ("jh", "j"),
    ("th", "t"), ("dh", "d"), ("ph", "f"), ("bh", "b"), ("ng", "n"), ("ck", "k"),
    ("qu", "k"), ("x", "ks"), ("z", "j"), ("q", "k"), ("v", "b"), ("w", ""), ("y", ""),
]


def _bn_skeleton_word(w: str) -> str:
    out: list[str] = []
    prev = ""
    for i, ch in enumerate(w):
        if ch in _BN_VOWELS or ch == _HASANTA or ch == "ঁ" or ch == "ঃ":
            continue
        if ch == "য" and i > 0 and w[i - 1] == _HASANTA:  # য-ফলা: a glide, not a consonant
            continue
        if ch in _BN_CONS:
            c = _BN_CONS[ch]
        elif ch.isdigit():
            c = ch
        else:
            continue
        if c and c != prev:
            out.append(c)
            prev = c
    s = "".join(out)
    if s.endswith("h") and len(s) > 2:  # word-final হ is not pronounced as h
        s = s[:-1]
    return s


def _lat_skeleton_word(w: str) -> str:
    w = w.lower()
    if w.isdigit():
        return w
    # soft c before e/i/y reads as s ("Circus", "Science")
    w = re.sub(r"c(?=[eiy])", "s", w)
    for a, b in _LAT_DIGRAPHS:
        w = w.replace(a, b)
    w = w.replace("c", "k").replace("C", "c")
    out: list[str] = []
    prev = ""
    for ch in w:
        if ch in "aeiou" or not ch.isalnum():
            continue
        if ch != prev:
            out.append(ch)
            prev = ch
    s = "".join(out)
    if s.endswith("h") and len(s) > 2:
        s = s[:-1]
    return s


_SUFFIXES = tuple(_bn_compose(x) for x in ("ের", "এর", "তে", "কে", "র", "য়", "ে", "e", "er"))
_GENERIC_FOLDED = {fold_bn(g).lower() for g in GENERIC}


def _is_bn(w: str) -> bool:
    return any("ঀ" <= ch <= "৿" for ch in w)


def skeleton(text: str) -> str:
    """Cross-script consonant skeleton of a phrase (words joined by ' ')."""
    parts = []
    for w in _WORD_RE.findall(_bn_compose(text).translate(_BN_DIGITS)):
        sk = _bn_skeleton_word(w) if _is_bn(w) else _lat_skeleton_word(w)
        # Bengali "চ" is closer to Latin "c/ch" than to "k": map both scripts'
        # palatal to "c" (done above) and velar k to "k" — nothing else to do.
        if sk:
            parts.append(sk)
    return " ".join(parts)


def _words(text: str) -> list[str]:
    return _WORD_RE.findall(_bn_compose(text).translate(_BN_DIGITS))


def _norm_same_script(text: str) -> str:
    return " ".join(fold_bn(w).lower() for w in _words(text))


# --- data --------------------------------------------------------------------


@dataclass
class Place:
    id: str
    name_en: str
    name_bn: str
    lat: float
    lon: float
    kind: str = ""
    source: str = "landmarks"
    names: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PlaceMatch:
    place: Place
    score: float
    matched_text: str
    matched_name: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.place.id,
            "name_en": self.place.name_en,
            "name_bn": self.place.name_bn,
            "lat": self.place.lat,
            "lon": self.place.lon,
            "match_score": round(self.score, 3),
            "matched_text": self.matched_text,
            "source": self.place.source,
        }


@dataclass(frozen=True)
class _Variant:
    place_idx: int
    name: str
    norm: str
    skel: str
    n_words: int


def _short_form(name: str) -> str | None:
    words = [w for w in _words(name) if w.lower() not in GENERIC]
    short = " ".join(words)
    return short if short and short != " ".join(_words(name)) else None


def _coords(e: dict[str, Any]) -> tuple[float, float] | None:
    for la, lo in (("lat", "lon"), ("lat", "lng"), ("latitude", "longitude")):
        if la in e and lo in e:
            try:
                return float(e[la]), float(e[lo])
            except (TypeError, ValueError):
                return None
    geom = e.get("geometry") or {}
    if isinstance(geom, dict) and geom.get("type") == "Point":
        c = geom.get("coordinates") or []
        if len(c) >= 2:
            return float(c[1]), float(c[0])
    c = e.get("coordinates") or e.get("centroid") or e.get("center")
    if isinstance(c, (list, tuple)) and len(c) >= 2:
        return float(c[1]), float(c[0])  # GeoJSON order [lon, lat]
    if isinstance(c, dict):
        return _coords(c)
    return None


def _entry_names(e: dict[str, Any]) -> tuple[str, str, list[str]]:
    props = e.get("properties") if isinstance(e.get("properties"), dict) else {}
    src = {**props, **e}
    names = src.get("names") if isinstance(src.get("names"), dict) else {}
    en = src.get("name_en") or src.get("en") or names.get("en") or src.get("name") or ""
    bn = src.get("name_bn") or src.get("bn") or names.get("bn") or ""
    extra: list[str] = []
    for k in ("aliases", "alt_names", "alias", "hi", "name_hi"):
        v = src.get(k)
        if isinstance(v, str):
            extra.append(v)
        elif isinstance(v, list):
            extra += [x for x in v if isinstance(x, str)]
        elif isinstance(v, dict):
            for x in v.values():
                extra += [x] if isinstance(x, str) else [y for y in x if isinstance(y, str)] if isinstance(x, list) else []
    if isinstance(names, dict):
        extra += [v for k, v in names.items() if isinstance(v, str) and k not in ("en", "bn")]
    return str(en), str(bn), extra


def _iter_entries(doc: Any) -> Iterable[dict[str, Any]]:
    if isinstance(doc, list):
        for x in doc:
            if isinstance(x, dict):
                if any(k in x for k in ("id", "name", "en", "name_en", "properties")):
                    yield x
                else:
                    yield from _iter_entries(list(x.values()))
            elif isinstance(x, list):
                yield from _iter_entries(x)
    elif isinstance(doc, dict):
        if doc.get("type") == "FeatureCollection":
            yield from _iter_entries(doc.get("features", []))
            return
        for k, v in doc.items():
            if k in ("schema", "note", "notes", "meta", "source", "sources", "licence", "license"):
                continue
            if isinstance(v, (list, dict)):
                yield from _iter_entries(v if isinstance(v, list) else [v] if "id" in v else list(v.values()))


class Gazetteer:
    """Places plus their name variants, indexed for fuzzy lookup."""

    def __init__(self, places: list[Place], threshold: float = 0.80) -> None:
        self.places = places
        self.threshold = threshold
        self._variants: list[_Variant] = []
        for i, p in enumerate(places):
            seen: set[str] = set()
            for n in [p.name_en, p.name_bn, *p.names]:
                for form in (n, _short_form(n) if n else None):
                    if not form:
                        continue
                    norm = _norm_same_script(form)
                    if not norm or norm in seen:
                        continue
                    seen.add(norm)
                    sk = skeleton(form)
                    if len(sk.replace(" ", "")) < 2:
                        continue
                    self._variants.append(_Variant(i, form, norm, sk, len(_words(form))))
        self.max_words = max((v.n_words for v in self._variants), default=1) + 1

    def __len__(self) -> int:
        return len(self.places)

    def by_id(self, pid: str) -> Place | None:
        for p in self.places:
            if p.id == pid:
                return p
        return None

    @staticmethod
    def _windows(words: list[str], max_n: int) -> Iterable[tuple[str, int]]:
        for n in range(1, max_n + 1):
            for i in range(0, len(words) - n + 1):
                win = words[i:i + n]
                # no place name starts with "মোড়", "road", "near" …: a window
                # that does would only borrow letters from its neighbour
                if fold_bn(win[0]).lower() in _GENERIC_FOLDED:
                    continue
                yield " ".join(win), n

    @staticmethod
    def _score(win_norm: str, win_skel: str, v: _Variant) -> float:
        direct = SequenceMatcher(None, win_norm, v.norm).ratio() if win_norm and v.norm else 0.0
        if direct < 1.0 and min(len(win_norm), len(v.norm)) <= 5:
            direct *= 0.9  # one wrong letter in a five-letter word is a different word
        a_parts, b_parts = win_skel.split(), v.skel.split()
        if not a_parts or not b_parts:
            return direct
        if len(a_parts) == len(b_parts):
            # word by word, weighted by the name word's length: "Park Circus"
            # must not match "Park Street" on the shared "Park" alone
            num = den = 0.0
            for x, y in zip(a_parts, b_parts):
                r = SequenceMatcher(None, x, y).ratio()
                if min(len(x), len(y)) <= 2 and x != y:
                    r *= 0.6
                num += r * len(y)
                den += len(y)
            sk = num / den
        else:
            # a name split or merged across words ("গড়িয়া হাট"): compare the
            # joined skeletons, with a discount for the looser alignment
            sk = SequenceMatcher(None, "".join(a_parts), "".join(b_parts)).ratio() * 0.88
        a, b = "".join(a_parts), "".join(b_parts)
        if min(len(a), len(b)) <= 3:
            # very short skeletons collide easily: only an exact skeleton
            # counts, and it is capped below a clean same-script match
            sk = 0.86 if a == b else sk * 0.6
        return max(direct, sk)

    def match(self, text: str, top: int = 3) -> tuple[PlaceMatch | None, list[PlaceMatch]]:
        words = _words(text)
        if not words or not self._variants:
            return None, []
        best: dict[int, PlaceMatch] = {}
        windows = []
        for win, n in self._windows(words, self.max_words):
            # Bengali case endings (-এ, -র, -তে, -য়) ride on the last word:
            # try the window with and without them.
            forms = {win}
            last = words and win.split(" ")[-1]
            for suf in _SUFFIXES:
                if last and last.endswith(suf) and len(last) > len(suf) + 2:
                    forms.add(win[: -len(suf)])
            for f in forms:
                windows.append((f, _norm_same_script(f), skeleton(f), n))
        for v in self._variants:
            for f, wn, ws, n in windows:
                if abs(n - v.n_words) > 1:
                    continue
                if ws[:1] != v.skel[:1] and wn[:1] != v.norm[:1]:
                    continue
                s = self._score(wn, ws, v)
                cur = best.get(v.place_idx)
                if cur is None or s > cur.score or (s == cur.score and len(v.name) > len(cur.matched_name)):
                    best[v.place_idx] = PlaceMatch(self.places[v.place_idx], s, f, v.name)
        ranked = sorted(best.values(), key=lambda m: (-m.score, -len(m.matched_text),
                                                      m.place.source != "landmarks"))
        cands = [m for m in ranked[:top] if m.score >= 0.5]
        top1 = ranked[0] if ranked and ranked[0].score >= self.threshold else None
        return top1, cands


def _landmarks(path: Path) -> list[Place]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for e in doc.get("landmarks", []):
        names = [e.get("hi", "")] + ALIASES.get(e["id"], [])
        out.append(Place(id=e["id"], name_en=e["en"], name_bn=e["bn"], lat=float(e["lat"]),
                         lon=float(e["lon"]), kind=e.get("kind", ""), source="landmarks",
                         names=[n for n in names if n]))
    return out


def _gazetteer_entries(path: Path, taken: set[str]) -> list[Place]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        log.warning("gazetteer unreadable (%s): %s", path, exc)
        return []
    out: list[Place] = []
    for e in _iter_entries(doc):
        pid = str(e.get("id") or (e.get("properties") or {}).get("id") or "")
        if not pid or pid in taken:
            continue
        ll = _coords(e) or _coords(e.get("properties") or {})
        if ll is None:
            continue
        en, bn, extra = _entry_names(e)
        if not (en or bn):
            continue
        taken.add(pid)
        kind = str(e.get("kind") or e.get("type") or (e.get("properties") or {}).get("kind") or "")
        out.append(Place(id=pid, name_en=en or bn, name_bn=bn or en, lat=ll[0], lon=ll[1],
                         kind=kind, source="gazetteer", names=extra + ALIASES.get(pid, [])))
    return out


def load_gazetteer(city_dir: Path, gazetteer_file: str = "gazetteer.json",
                   threshold: float = 0.80) -> Gazetteer:
    city_dir = Path(city_dir)
    places = _landmarks(city_dir / "landmarks.json")
    gz = city_dir / gazetteer_file
    if gz.is_file():
        extra = _gazetteer_entries(gz, {p.id for p in places})
        log.info("gazetteer: %d landmarks + %d gazetteer entries", len(places), len(extra))
        places += extra
    return Gazetteer(places, threshold=threshold)
