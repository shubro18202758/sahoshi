"""Build the emulator's Kolkata scenario library from the city network.

    python tools/kolkata_library.py --network PATH [--write] [--slim-out PATH]

The scenarios are written here in terms of the city pack's landmark keys
(``cities/kolkata/landmarks.json`` ids, which the network's junctions carry
as ``key``): a route is a walk from crossing to crossing, a cause sits on
the road between two crossings.  This tool resolves every walk against the
network (``scripts/data/osm_network.json`` or the pack's ``network.json``)
into segment ids, checks that each route is a LEGAL directed path (one-ways
driven their own way), times the ambulance windows on the roads' real
lengths, and writes ``src/event_emulator/use_case_library.json``.  When the
network is regenerated with new ids, re-run it: the scenarios follow.

Every scenario is SIMULATED.  Times, speeds, crowd loads and demand figures
are MODELLED assumptions (stated in each description); no number here is a
real-world statistic.  Events are about places, never people: no person is
named, tracked or described.

``--slim-out`` writes the small network snapshot the emulator's tests check
the library, the profiles and the living city's sites against.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
LIBRARY = HERE.parent / "src" / "event_emulator" / "use_case_library.json"
LANDMARKS = HERE.parents[2] / "cities" / "kolkata" / "landmarks.json"

_R_EARTH_M = 6371008.8


# ── the network ─────────────────────────────────────────────────────────────


class Network:
    """Junctions by key, segments with ends, one-way flags and lengths."""

    def __init__(self, doc: dict) -> None:
        self.doc = doc
        marks = {}
        if LANDMARKS.is_file():
            marks = {m["id"]: m for m in
                     json.loads(LANDMARKS.read_text(encoding="utf-8"))["landmarks"]}
        self.key_to_jid: dict[str, int] = {}
        self.jid_to_key: dict[int, str] = {}
        self.jpos: dict[int, tuple[float, float]] = {}
        self.jname: dict[int, tuple[str, str]] = {}
        for j in doc["junctions"]:
            jid = int(j["junction_id"])
            key = j.get("key") or j.get("landmark")
            if key:
                self.key_to_jid[str(key)] = jid
                self.jid_to_key[jid] = str(key)
            mark = marks.get(str(j.get("landmark") or key or ""))
            if "lon" in j and "lat" in j:
                self.jpos[jid] = (float(j["lon"]), float(j["lat"]))
            elif "at" in j:
                self.jpos[jid] = (float(j["at"][1]), float(j["at"][0]))
            elif mark:
                self.jpos[jid] = (float(mark["lon"]), float(mark["lat"]))
            self.jname[jid] = (str(j.get("name") or (mark or {}).get("en") or key or jid),
                               str(j.get("name_bn") or (mark or {}).get("bn") or ""))
        self.segs: dict[int, dict] = {}
        for s in doc["segments"]:
            sid = int(s["segment_id"])
            a = s.get("from_junction")
            b = s.get("to_junction")
            if a is None and "from" in s:
                a = self.key_to_jid[s["from"]]
            if b is None and "to" in s:
                b = self.key_to_jid[s["to"]]
            line = [tuple(map(float, p)) for p in (s.get("line") or [])]
            self.segs[sid] = {
                "id": sid, "name": s.get("road_name", ""), "a": int(a),
                "b": int(b) if b is not None else None,
                "oneway": bool(s.get("oneway")), "line": line,
                "length_m": float(s.get("length_m") or 0.0) or None,
                "limit": s.get("speed_limit_kmh"), "road_class": s.get("road_class"),
            }

    # geometry -------------------------------------------------------------

    @staticmethod
    def dist_m(p: tuple[float, float], q: tuple[float, float]) -> float:
        lat0 = math.radians((p[1] + q[1]) / 2.0)
        dx = math.radians(q[0] - p[0]) * math.cos(lat0) * _R_EARTH_M
        dy = math.radians(q[1] - p[1]) * _R_EARTH_M
        return math.hypot(dx, dy)

    def length_m(self, sid: int) -> float:
        s = self.segs[sid]
        if s["length_m"]:
            return s["length_m"]
        if len(s["line"]) >= 2:
            return sum(self.dist_m(p, q) for p, q in zip(s["line"], s["line"][1:]))
        # draft spec without geometry: the crossings' distance × a detour factor
        return 1.3 * self.dist_m(self.jpos[s["a"]], self.jpos[s["b"]])

    def line(self, sid: int) -> list[list[float]]:
        s = self.segs[sid]
        if len(s["line"]) >= 2:
            return [[round(p[0], 7), round(p[1], 7)] for p in s["line"]]
        a, b = self.jpos[s["a"]], self.jpos[s["b"]]
        return [[round(a[0], 7), round(a[1], 7)], [round(b[0], 7), round(b[1], 7)]]

    # walks ----------------------------------------------------------------

    def jid(self, key: str) -> int:
        try:
            return self.key_to_jid[key]
        except KeyError:
            raise SystemExit(f"ERROR: no junction keyed {key!r} in the network") from None

    def between(self, a: str, b: str, *, directed: bool = True) -> int:
        """The segment that runs from crossing ``a`` to crossing ``b``
        (legal in that direction when ``directed``)."""
        ja, jb = self.jid(a), self.jid(b)
        found = []
        for s in self.segs.values():
            if (s["a"], s["b"]) == (ja, jb):
                found.append(s["id"])
            elif (s["a"], s["b"]) == (jb, ja) and not (directed and s["oneway"]):
                found.append(s["id"])
        if not found:
            raise SystemExit(f"ERROR: no {'legal ' if directed else ''}segment {a} -> {b}")
        return min(found)

    def _moves(self, at: int) -> list[tuple[int, int]]:
        """(segment, next junction) legal from junction ``at``."""
        out = []
        for s in self.segs.values():
            if s["b"] is None:
                continue
            if s["a"] == at:
                out.append((s["id"], s["b"]))
            elif s["b"] == at and not s["oneway"]:
                out.append((s["id"], s["a"]))
        return out

    def shortest(self, a: int, b: int, avoid: set[int]) -> list[int]:
        """Shortest legal drive (metres) from junction ``a`` to ``b``."""
        import heapq

        best = {a: 0.0}
        prev: dict[int, tuple[int, int]] = {}
        heap = [(0.0, a)]
        while heap:
            d, at = heapq.heappop(heap)
            if at == b:
                break
            if d > best.get(at, math.inf):
                continue
            for sid, nxt in self._moves(at):
                if sid in avoid:
                    continue
                nd = d + self.length_m(sid)
                if nd < best.get(nxt, math.inf):
                    best[nxt] = nd
                    prev[nxt] = (sid, at)
                    heapq.heappush(heap, (nd, nxt))
        if b not in best:
            raise SystemExit(f"ERROR: no legal drive {self.jid_to_key.get(a, a)} -> "
                             f"{self.jid_to_key.get(b, b)}")
        out: list[int] = []
        at = b
        while at != a:
            sid, at = prev[at]
            out.append(sid)
        return out[::-1]

    def walk(self, *keys: str) -> list[int]:
        """The legal route through crossings ``keys`` in order: the shortest
        legal drive between each consecutive pair (one-ways their own way),
        never the same segment twice."""
        out: list[int] = []
        for a, b in zip(keys, keys[1:]):
            out += self.shortest(self.jid(a), self.jid(b), set(out))
        if len(set(out)) != len(out):
            raise SystemExit(f"ERROR: walk {keys} uses a segment twice")
        return out

    def near(self, place: str, among: list[int] | None = None) -> int:
        """The segment nearest a landmark (``among`` restricts the choice)."""
        marks = {}
        if LANDMARKS.is_file():
            marks = {m["id"]: m for m in
                     json.loads(LANDMARKS.read_text(encoding="utf-8"))["landmarks"]}
        if place in marks:
            pt = (float(marks[place]["lon"]), float(marks[place]["lat"]))
        else:
            pt = self.jpos[self.jid(place)]
        pool = among if among is not None else list(self.segs)

        def gap(sid: int) -> float:
            line = self.line(sid)
            return min(self._point_seg_m(pt, tuple(p), tuple(q))
                       for p, q in zip(line, line[1:]))
        return min(pool, key=lambda sid: (gap(sid), sid))

    def _point_seg_m(self, p: tuple[float, float], a: tuple[float, float],
                     b: tuple[float, float]) -> float:
        kx = math.cos(math.radians(p[1])) * 111320.0
        ky = 111320.0
        ax, ay = (a[0] - p[0]) * kx, (a[1] - p[1]) * ky
        bx, by = (b[0] - p[0]) * kx, (b[1] - p[1]) * ky
        dx, dy = bx - ax, by - ay
        L = dx * dx + dy * dy
        t = 0.0 if L == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / L))
        return math.hypot(ax + t * dx, ay + t * dy)

    def exit_junction(self, route: list[int]) -> list[int]:
        """The crossings a route passes, in order (its start first)."""
        if len(route) == 1:
            s = self.segs[route[0]]
            return [s["a"], s["b"]]
        first, second = self.segs[route[0]], self.segs[route[1]]
        start = first["a"] if first["b"] in (second["a"], second["b"]) else first["b"]
        out = [start]
        for sid in route:
            s = self.segs[sid]
            nxt = s["b"] if s["a"] == out[-1] else s["a"]
            out.append(nxt)
        return out

    def slim(self) -> dict:
        return {
            "about": ("Slim snapshot of the Kolkata road network the emulator's library, "
                      "profiles and living-city sites are built on (ids, ends, one-way "
                      "flags, names, lengths). GENERATED by tools/kolkata_library.py from "
                      "the city network; the emulator's tests check against it."),
            "junctions": [
                {"junction_id": jid, "key": self.jid_to_key.get(jid),
                 "name": self.jname[jid][0], "name_bn": self.jname[jid][1],
                 "lon": round(self.jpos[jid][0], 6) if jid in self.jpos else None,
                 "lat": round(self.jpos[jid][1], 6) if jid in self.jpos else None,
                 "signal_control": next((bool(j.get("signal_control")) for j in
                                         self.doc["junctions"]
                                         if int(j["junction_id"]) == jid), False)}
                for jid in sorted(self.jname)
            ],
            "segments": [
                {"segment_id": s["id"], "road_name": s["name"], "from_junction": s["a"],
                 "to_junction": s["b"], "oneway": s["oneway"],
                 "length_m": round(self.length_m(s["id"]), 1),
                 "speed_limit_kmh": s["limit"], "road_class": s["road_class"]}
                for s in sorted(self.segs.values(), key=lambda x: x["id"])
            ],
            "signal_programs": sorted(int(k) for k in (self.doc.get("signal_programs") or {})),
            "cameras": [
                {k: c.get(k) for k in ("camera_id", "kind", "junction_id", "segment_id",
                                       "lon", "lat", "heading_deg", "label") if k in c}
                for c in self.doc.get("cameras") or [] if isinstance(c, dict)
                and c.get("camera_id")
            ],
        }


# ── scenario helpers ────────────────────────────────────────────────────────


def ev_windows(net: Network, route: list[int], *, start_sec: float, speed_kmh: float,
               label: str, places: list[str], window_sec: float = 300.0,
               severity: float = 0.9) -> list[dict]:
    """Green-corridor windows for an ambulance (108) or a fire tender, one
    per route segment, each opening when the vehicle (at ``speed_kmh``)
    reaches that segment and held until it has cleared it (its travel time
    on the road's length plus two minutes' margin, never under
    ``window_sec``)."""
    if len(places) != len(route):
        raise SystemExit(f"ERROR: {label!r}: {len(route)} segments but {len(places)} places")
    out: list[dict] = []
    t = float(start_sec)
    for sid, place in zip(route, places):
        travel = net.length_m(sid) / (speed_kmh / 3.6)
        out.append({
            "type": "emergency_vehicle", "segment_id": sid,
            "start_sec": round(t, 1),
            "duration_sec": float(max(window_sec, round(travel + 120.0))),
            "severity": severity, "label": f"{label} — {place}",
        })
        t += travel
    return out


def fe(kind: str, sid: int, start: float, dur: float, sev: float, label: str,
       demand: float | None = None) -> dict:
    doc: dict[str, Any] = {"type": kind, "segment_id": sid, "start_sec": float(start),
                           "duration_sec": float(dur), "severity": sev, "label": label}
    if demand is not None:
        doc["extra_demand_veh_h"] = float(demand)
    return doc


def scenario(**kw: Any) -> dict:
    """One library entry in its canonical key order."""
    order = ("scenario_id", "name", "name_bn", "name_hi", "label", "category",
             "description", "places", "route_segment_ids", "departure_time", "vvip_class",
             "closure_policy", "horizon_min", "n_replications", "seed", "convoy_speed_kmh",
             "weather", "event_overrides", "forced_events", "expected_features",
             "event_kind", "crowd_class", "duration_class", "stolen_fir_ref", "unit_tracks")
    kw.setdefault("label", "SIMULATED")
    cfg = {k: kw[k] for k in order if k in kw}
    extra = set(kw) - set(order)
    if extra:
        raise SystemExit(f"ERROR: unknown scenario keys {sorted(extra)}")
    return {"id": cfg["scenario_id"], "scenarioConfig": cfg}


# ── route helpers ───────────────────────────────────────────────────────────


def first_leg(net: Network, a: str, b: str) -> int:
    """The segment a legal drive from crossing ``a`` towards ``b`` starts on
    (the road joining them when they are neighbours)."""
    return net.shortest(net.jid(a), net.jid(b), set())[0]


def out_of(net: Network, route: list[int], key: str) -> int:
    """The route segment that leaves crossing ``key``."""
    passes = net.exit_junction(route)
    jid = net.jid(key)
    if jid not in passes[:-1]:
        raise SystemExit(f"ERROR: the route {route} does not leave {key}")
    return route[passes.index(jid)]


def into(net: Network, route: list[int], key: str) -> int:
    """The route segment that arrives at crossing ``key``."""
    passes = net.exit_junction(route)
    jid = net.jid(key)
    if jid not in passes[1:]:
        raise SystemExit(f"ERROR: the route {route} does not reach {key}")
    return route[passes.index(jid, 1) - 1]


def named(net: Network, sid: int, *fragments: str) -> int:
    """``sid``, checked to be a road whose OSM name carries one of
    ``fragments`` (a lookup by landmark must land on the road it means)."""
    name = net.segs[sid]["name"]
    if not any(f.lower() in name.lower() for f in fragments):
        raise SystemExit(f"ERROR: segment {sid} is {name!r}, expected one of {fragments}")
    return sid


def road_names(net: Network, route: list[int]) -> str:
    out: list[str] = []
    for sid in route:
        n = net.segs[sid]["name"]
        if not out or out[-1] != n:
            out.append(n)
    return " > ".join(out)


# ── the scenarios ───────────────────────────────────────────────────────────


def build(net: Network) -> list[dict]:  # noqa: PLR0915 - one scenario per block
    W = net.walk
    lib: list[dict] = []

    # (a) VIP movement, Nabanna -> Kolkata Airport (the base case) ─────────
    route = W("nabanna", "vidyasagar_setu", "park_circus", "science_city", "chingrighata",
              "salt_lake_stadium", "ultadanga", "lake_town", "kestopur", "baguiati",
              "chinar_park", "airport", "airport_terminal")
    lib.append(scenario(
        scenario_id="vvip_convoy_base",
        name="VIP Movement — Base Case (Nabanna to Kolkata Airport)",
        name_bn="ভিআইপি যাত্রা — বেস কেস (নবান্ন থেকে কলকাতা বিমানবন্দর)",
        name_hi="वीआईपी यात्रा — बेस केस (नबान्न से कोलकाता हवाई अड्डा)",
        category="baseline",
        description=(
            "SIMULATED BASE CASE. A Z+ protected movement from Nabanna, the state "
            "secretariat on the Howrah side, to Kolkata Airport on a Monday afternoon: "
            "across the Hooghly on Vidyasagar Setu, along the AJC Bose Road flyover to Park "
            "Circus, over the Maa Flyover to Science City, north on EM Bypass past "
            "Chingrighata and Salt Lake Stadium to Ultadanga, then up VIP Road past Lake "
            "Town, Kestopur and Baguiati to the airport and its approach road to the "
            "terminal forecourt. Maximum-protocol closure (180 s "
            "advance, full closure), default event rates, no weather — the reference "
            "movement every other scenario generalises. One planted cause (the profile): a "
            "goods vehicle stalls on EM Bypass ten minutes in. Public-safety logistics only: "
            "no person is named or tracked. The convoy speed (60 km/h) and the timings are "
            "modelled assumptions; the AI proposes the plan and a named officer decides."),
        places=["nabanna", "vidyasagar_setu", "park_circus", "science_city", "chingrighata",
                "salt_lake_stadium", "ultadanga", "kestopur", "airport"],
        route_segment_ids=route,
        departure_time="2026-11-02T15:00:00+05:30",
        vvip_class="Z+",
        closure_policy={"advance_closure_sec": 180, "closure_type": "full_closure"},
        horizon_min=45, n_replications=10, seed=20261102, convoy_speed_kmh=60,
        weather={}, event_overrides={}, forced_events=[],
        expected_features=["zplus_protocol", "secretariat_to_airport", "reference_case"],
        event_kind="protected_movement", crowd_class="LOW", duration_class="minutes",
    ))

    # (b) Durga Puja night — the flagship ──────────────────────────────────
    route = W("howrah_bridge", "bagbazar", "shyambazar", "college_street")
    kumartuli = named(net, out_of(net, route, "howrah_bridge"), "Strand")
    bagbazar_st = named(net, out_of(net, route, "bagbazar"), "Bagbazar")
    hatibagan = named(net, out_of(net, route, "shyambazar"), "Bidhan Sarani")
    college_sq = net.near("college_square")
    santosh = net.near("santosh_mitra_square")
    deshapriya = named(net, first_leg(net, "rashbehari", "deshapriya_park"), "Rash Behari")
    ekdalia = named(net, first_leg(net, "deshapriya_park", "gariahat"), "Rash Behari")
    amb_start, amb_speed = 600.0, 20.0
    evs = ev_windows(net, route, start_sec=amb_start, speed_kmh=amb_speed,
                     label="ambulance (108) green-corridor window",
                     places=["Strand Bank Road past Kumartuli", "Bagbazar Street",
                             "Bidhan Sarani to Kolkata Medical College"])
    lib.append(scenario(
        scenario_id="durga_puja_north",
        name="Durga Puja Night — Pandal Crowds and Ambulance Access",
        name_bn="দুর্গাপুজোর রাত — প্যান্ডেলের ভিড় আর অ্যাম্বুলেন্সের পথ",
        name_hi="दुर्गा पूजा की रात — पंडालों की भीड़ और एम्बुलेंस का रास्ता",
        category="multi_event",
        description=(
            "FLAGSHIP. 21:30 on Maha Ashtami (30 Sep 2025, between Saptami and Navami), the "
            "busiest stretch of a Puja night. In the North Kolkata belt pandal-hoppers spill "
            "off the footpaths around Kumartuli Park and Bagbazar Sarbojanin, along Bidhan "
            "Sarani (Hatibagan), around College Square and Santosh Mitra Square; in the "
            "South belt the crowd around Deshapriya Park and Ekdalia Evergreen fills Rash "
            "Behari Avenue towards Gariahat. Goods vehicles are kept off the pandal belts for "
            "the night (the restriction is modelled as fewer heavy-vehicle breakdowns, "
            "breakdown x0.6) and food stalls load the kerbs (market x2.0). Ten minutes in, "
            "an ambulance (108) on an emergency call asks for a green corridor from the "
            "riverside north of Howrah Bridge up Strand Bank Road past Kumartuli, along "
            "Bagbazar Street to Shyambazar and down Bidhan Sarani to Kolkata Medical "
            "College. Closure policy signal_hold at 45 s: the crowd is regulated, not "
            "stopped. Two Kolkata Traffic Police beats and the ambulance are animated "
            "(EMULATED units). Crowd loads and speeds are modelled assumptions; the AI "
            "proposes each hold and a named officer decides."),
        places=["kumartuli", "bagbazar", "shyambazar", "college_square", "medical_college",
                "santosh_mitra_square", "deshapriya_park", "ekdalia", "gariahat"],
        route_segment_ids=route,
        departure_time="2025-09-30T21:30:00+05:30",
        vvip_class="X",
        closure_policy={"advance_closure_sec": 45, "closure_type": "signal_hold"},
        horizon_min=60, n_replications=12, seed=202509301, convoy_speed_kmh=amb_speed,
        weather={},
        event_overrides={"market": 2.0, "breakdown": 0.6, "ambulance": 1.0},
        forced_events=[
            fe("rally_spillover", bagbazar_st, 0, 3600, 0.95,
               "Bagbazar Sarbojanin — pandal crowd spills onto Bagbazar Street", 950),
            fe("rally_spillover", kumartuli, 300, 3300, 0.85,
               "Kumartuli Park — queues along Strand Bank Road", 800),
            fe("rally_spillover", hatibagan, 0, 3600, 0.85,
               "Bidhan Sarani (Hatibagan) — pandal-hoppers between the North Kolkata pandals",
               850),
            fe("market_spillover", college_sq, 0, 3600, 0.7,
               "College Square — food stalls and queues by the pandal"),
            fe("rally_spillover", santosh, 600, 3000, 0.8,
               "Santosh Mitra Square — crowd overflow towards Sealdah", 800),
            fe("rally_spillover", deshapriya, 0, 3600, 0.95,
               "Deshapriya Park — crowd fills Rash Behari Avenue (South belt)", 950),
            fe("rally_spillover", ekdalia, 900, 2700, 0.85,
               "Ekdalia Evergreen — queues towards Gariahat (South belt)", 850),
            fe("market_spillover", ekdalia, 0, 3600, 0.7,
               "Gariahat — late-night Puja shoppers and stalls"),
            *evs,
        ],
        expected_features=["multi_event_composition", "festival_crowd", "pandal_crowd_spill",
                           "goods_vehicle_restriction", "green_corridor_request",
                           "signal_hold_regulated_passage"],
        event_kind="mass_gathering", crowd_class="EXTREME", duration_class="hours",
        unit_tracks={
            "note": ("Recorded agency-unit positions the City Command REPLAY animates "
                     "(agency_unit frames, one every 20 s of tape time). EMULATED units only "
                     "(EM ids): two Kolkata Traffic Police beats, one in each pandal belt "
                     "(Strand Bank Road - Bagbazar Street in the North, Rash Behari Avenue in "
                     "the South), and the ambulance (108) run up Strand Bank Road, along "
                     "Bagbazar Street and down Bidhan Sarani to Kolkata Medical College, timed "
                     "to the emergency_vehicle windows. Its last frame, at College Street, is "
                     "stationary and reports 'arrived' (the C-A spelling of on_scene). "
                     "Geometry: the run's drawn segment paths from the store when it has "
                     "them, else route_geometry below (the same segments, from the city "
                     "network)."),
            "units": [
                {"unit_id": "KTP-EM-21", "agency": "traffic",
                 "label": "Kolkata Traffic Police KTP-EM-21 · North belt (EMULATED)",
                 "status": "patrol", "mode": "patrol",
                 "segment_ids": [kumartuli, bagbazar_st], "speed_kmh": 12.0, "offset": 0.0},
                {"unit_id": "KTP-EM-22", "agency": "traffic",
                 "label": "Kolkata Traffic Police KTP-EM-22 · South belt (EMULATED)",
                 "status": "patrol", "mode": "patrol",
                 "segment_ids": [deshapriya, ekdalia], "speed_kmh": 12.0, "offset": 0.5},
                {"unit_id": "AMB-EM-108", "agency": "ambulance",
                 "label": "Ambulance (108) AMB-EM-108 · green-corridor run (EMULATED)",
                 "status": "en_route", "arrival_status": "arrived", "mode": "run",
                 "segment_ids": list(route), "speed_kmh": amb_speed, "start_sec": amb_start},
            ],
            "route_geometry": {str(s): net.line(s) for s in
                               sorted({kumartuli, bagbazar_st, deshapriya, ekdalia, *route})},
        },
    ))

    # (c) Cloudburst at high tide ──────────────────────────────────────────
    route = W("lake_town", "ultadanga", "shyambazar", "college_street")
    vip_rd = named(net, out_of(net, route, "lake_town"), "VIP Road")
    ultadanga_rd = named(net, out_of(net, route, "ultadanga"), "Bidhannagar", "Gobinda")
    thanthania = named(net, out_of(net, route, "shyambazar"), "Bidhan Sarani")
    lib.append(scenario(
        scenario_id="cloudburst_high_tide",
        name="Cloudburst at High Tide — Waterlogging, Pumps and Live-Wire Hazard",
        name_bn="জোয়ারের সময় মেঘভাঙা বৃষ্টি — জল জমা, পাম্প আর বিদ্যুতের তারের বিপদ",
        name_hi="ज्वार के समय बादल फटना — जलभराव, पंप और बिजली के तार का ख़तरा",
        category="weather",
        description=(
            "SIMULATED. A monsoon evening (a scenario date, not a forecast): a cloudburst-"
            "class cell (rain modelled at 100 mm/h) breaks over North and Central Kolkata at "
            "17:30 while the Hooghly is at high water (MODELLED tide phase). With the "
            "outfall gates shut against the river the drains cannot empty by gravity and "
            "KMC's pumping stations carry the whole load (pump capacity modelled), so the "
            "water spreads instead of draining: "
            "Thanthania on Bidhan Sarani first, then the Ultadanga approaches, MG Road by "
            "College Street, APC Road at Maniktala, AJC Bose Road at Moulali and Park "
            "Circus. A car stalls in standing water; signals at Ultadanga go dark (a "
            "modelled precautionary power cut). Where water stands around street-light "
            "poles and overhead lines the risk is electrocution: the stack may PROPOSE a "
            "live-wire hazard advisory to the power utility (CESC / WBSEDCL) — a proposal a "
            "named duty officer approves or rejects; nothing is sent by itself. An "
            "ambulance (108) from Lake Town to Kolkata Medical College needs windows "
            "through the water. Rain rate, tide, pump capacity and spread times are "
            "modelled assumptions, not measurements."),
        places=["kestopur", "ultadanga", "shyambazar", "thanthania", "college_square",
                "medical_college", "moulali", "park_circus", "garden_reach"],
        route_segment_ids=route,
        departure_time="2026-08-18T17:30:00+05:30",
        vvip_class="X",
        closure_policy={"advance_closure_sec": 60, "closure_type": "signal_hold"},
        horizon_min=60, n_replications=10, seed=20260818, convoy_speed_kmh=30,
        weather={"monsoon": True, "rain_intensity_mm_h": 100.0},
        event_overrides={"breakdown": 1.8, "waterlogging": 3.0, "signal_fault": 1.5},
        forced_events=[
            fe("waterlogging", thanthania, 300, 3300, 0.85,
               "Thanthania (Bidhan Sarani) — low-lying stretch waterlogged; water around "
               "lamp posts (live-wire risk)"),
            fe("waterlogging", ultadanga_rd, 600, 3000, 0.8,
               "Ultadanga — water collects on Bidhannagar Road"),
            fe("waterlogging", vip_rd, 900, 2700, 0.75,
               "VIP Road at Ultadanga — water on the approach"),
            fe("waterlogging", net.near("college_square"), 900, 2700, 0.75,
               "MG Road by College Street — outfall shut at high tide, pumps lag"),
            fe("waterlogging", first_leg(net, "maniktala", "shyambazar"), 1200, 2400, 0.7,
               "APC Road at Maniktala — water spreading"),
            fe("waterlogging", named(net, first_leg(net, "moulali", "sealdah"), "Bose"),
               1200, 2400, 0.7,
               "AJC Bose Road at Moulali — water spreading"),
            fe("waterlogging", first_leg(net, "mullickbazar", "park_circus"), 1500, 2100, 0.7,
               "Park Circus — water spreading on Mother Teresa Sarani"),
            fe("signal_fault", vip_rd, 1200, 2400, 0.6,
               "Ultadanga signals dark — precautionary power cut in standing water"),
            fe("vehicle_breakdown", ultadanga_rd, 1500, 1800, 0.7,
               "car stalled in standing water at Ultadanga"),
        ],
        expected_features=["cloudburst", "high_tide_outfall_closed", "pump_constraint",
                           "waterlogging_spread", "live_wire_hazard_proposal",
                           "green_corridor_request"],
        event_kind="emergency_evacuation", crowd_class="MEDIUM", duration_class="hours",
    ))

    # (d) Cyclone landfall and recovery ────────────────────────────────────
    route = W("esplanade", "park_street", "exide", "hazra", "rashbehari")
    chowringhee = named(net, into(net, route, "park_street"), "Nehru")
    jln_south = named(net, out_of(net, route, "park_street"), "Nehru")
    ashutosh = named(net, out_of(net, route, "exide"), "Ashutosh")
    spm_rd = named(net, out_of(net, route, "hazra"), "Mukherjee")
    lib.append(scenario(
        scenario_id="cyclone_landfall_recovery",
        name="Cyclone Recovery — Tree-Falls on Arterials, Staged Reopening",
        name_bn="ঘূর্ণিঝড়ের পরে — গাছ পড়ে রাস্তা বন্ধ, ধাপে ধাপে রাস্তা খোলা",
        name_hi="चक्रवात के बाद — पेड़ गिरने से सड़कें बंद, चरणबद्ध तरीके से खुलना",
        category="weather",
        description=(
            "SIMULATED. The morning after a severe cyclone has crossed the coast and passed "
            "over Kolkata (a scenario, not a forecast). Squalls linger (STORM, modelled). "
            "Uprooted trees block the arterials south from Esplanade: Jawaharlal Nehru Road "
            "along the Maidan, Ashutosh Mukherjee Road and SP Mukherjee Road, with Red Road "
            "and Queensway closed alongside. KMC and fire-service crews clear them lane by "
            "lane, so the corridor reopens in stages (each blockage is a lane-loss cause "
            "with its own clearance time). Signals at Exide are dark after the overnight "
            "power cut. An ambulance (108) heads for SSKM Hospital through the cleared "
            "lanes. Clearance times are modelled assumptions; every reopening is an "
            "officer's decision."),
        places=["esplanade", "park_street", "exide", "hazra", "rashbehari", "red_road",
                "victoria_memorial", "sskm"],
        route_segment_ids=route,
        departure_time="2026-05-27T06:30:00+05:30",
        vvip_class="X",
        closure_policy={"advance_closure_sec": 60, "closure_type": "partial_closure"},
        horizon_min=60, n_replications=8, seed=20260527, convoy_speed_kmh=30,
        weather={"monsoon": False, "rain_intensity_mm_h": 12.0},
        event_overrides={"breakdown": 1.5, "signal_fault": 2.5},
        forced_events=[
            fe("vehicle_breakdown", ashutosh, 0, 1200, 0.9,
               "uprooted tree across Ashutosh Mukherjee Road (lane-loss; cleared first)"),
            fe("vehicle_breakdown", chowringhee, 0, 2100, 0.85,
               "uprooted tree on Jawaharlal Nehru Road by the Maidan (cleared second)"),
            fe("vehicle_breakdown", spm_rd, 0, 3000, 0.8,
               "uprooted tree on SP Mukherjee Road (cleared last)"),
            fe("vehicle_breakdown", named(net, first_leg(net, "red_road", "red_road_south"),
                                       "Red Road"), 0, 3600, 0.9,
               "Red Road closed — trees down along the Maidan"),
            fe("vehicle_breakdown", named(net, first_leg(net, "victoria_memorial", "exide"), "Queensway"),
               0, 3600, 0.85, "Queensway closed — trees down"),
            fe("signal_fault", jln_south, 0, 2400, 0.7,
               "signals dark at Exide crossing after the overnight power cut"),
            *ev_windows(net, [jln_south, ashutosh], start_sec=1500, speed_kmh=30,
                        label="ambulance (108) window to SSKM Hospital",
                        places=["Jawaharlal Nehru Road to Exide", "Ashutosh Mukherjee Road"],
                        severity=0.85),
        ],
        expected_features=["cyclone_recovery", "tree_fall_lane_loss", "staged_reopening",
                           "signals_dark", "green_corridor_request"],
        event_kind="work_zone", crowd_class="LOW", duration_class="hours",
    ))

    # (e) Eden Gardens match egress ────────────────────────────────────────
    route = W("red_road", "babughat", "howrah_bridge", "howrah_station")
    gates = named(net, out_of(net, route, "red_road"), "Khudiram")
    strand = named(net, out_of(net, route, "babughat"), "Strand")
    bridge = named(net, out_of(net, route, "howrah_bridge"), "Howrah Bridge")
    to_esplanade = named(net, first_leg(net, "red_road", "esplanade_sn_banerjee"), "Rashmoni")
    lib.append(scenario(
        scenario_id="eden_gardens_egress",
        name="Eden Gardens — Match-Night Egress",
        name_bn="ইডেন গার্ডেন্স — খেলার রাতে দর্শকদের ফেরা",
        name_hi="ईडन गार्डन्स — मैच की रात दर्शकों की वापसी",
        category="event",
        description=(
            "SIMULATED. A full house leaves Eden Gardens after a night match (the crowd "
            "is modelled from a full stadium; no fixture or attendance figure is claimed). "
            "The dispersal wave pours out onto Sahid Khudiram Bose Road and splits: north "
            "along Strand Road past Babughat and over Howrah Bridge to Howrah Station for "
            "the last trains, and east along Rani Rashmoni Avenue to Esplanade and its "
            "Metro station. A stalled app cab blocks a dispersal lane on Strand Road "
            "twenty minutes in. Two ambulance (108) green-corridor requests (the profile) "
            "cut through the wave. Closure policy signal_hold at 60 s; crowd loads are "
            "modelled assumptions."),
        places=["eden_gardens", "red_road", "babughat", "howrah_bridge", "howrah_station",
                "esplanade"],
        route_segment_ids=route,
        departure_time="2026-04-18T22:50:00+05:30",
        vvip_class="X",
        closure_policy={"advance_closure_sec": 60, "closure_type": "signal_hold"},
        horizon_min=60, n_replications=12, seed=20260418, convoy_speed_kmh=40,
        weather={}, event_overrides={},
        forced_events=[
            fe("rally_spillover", gates, 0, 5400, 0.95,
               "Eden Gardens gates — spectators pour onto Sahid Khudiram Bose Road", 1500),
            fe("rally_spillover", strand, 600, 4800, 0.8,
               "spectators walking north on Strand Road towards Howrah", 1000),
            fe("rally_spillover", bridge, 900, 4200, 0.75,
               "the wave crosses Howrah Bridge to Howrah Station", 900),
            fe("rally_spillover", to_esplanade, 600, 4200, 0.7,
               "egress wave towards Esplanade Metro on Rani Rashmoni Avenue", 800),
            fe("vehicle_breakdown", strand, 1200, 1500, 0.7,
               "stalled app cab blocking one dispersal lane on Strand Road"),
        ],
        expected_features=["stadium_egress", "extreme_crowd", "green_corridor_request",
                           "signal_hold_policy"],
        event_kind="egress_surge", crowd_class="EXTREME", duration_class="hours",
    ))
    segments_used["khudiram_bose_road"] = gates
    segments_used["strand_road_babughat"] = strand

    # (f) Howrah Station evening surge + Howrah Bridge breakdown ───────────
    route = W("esplanade", "central_avenue_mg_road", "howrah_bridge", "howrah_station")
    mg_road = named(net, into(net, route, "howrah_bridge"), "Gandhi")
    bridge = named(net, out_of(net, route, "howrah_bridge"), "Howrah Bridge")
    lib.append(scenario(
        scenario_id="howrah_surge_bridge_breakdown",
        name="Howrah Station Evening Surge + Howrah Bridge Breakdown",
        name_bn="হাওড়া স্টেশনে সন্ধ্যার ভিড় আর হাওড়া ব্রিজে বাস বিকল",
        name_hi="हावड़ा स्टेशन पर शाम की भीड़ और हावड़ा ब्रिज पर बस ख़राब",
        category="multi_event",
        description=(
            "SIMULATED. A weekday evening: offices around Esplanade and BBD Bag empty "
            "towards Howrah Station for the suburban trains — up Chittaranjan Avenue, west "
            "along MG Road through Burrabazar and over Howrah Bridge — and the bridge's "
            "footpaths and the station approach fill (commuter load modelled). Ten minutes "
            "in, a bus breaks down mid-span on Howrah Bridge and one lane is lost until the "
            "tow clears it; the queue backs up MG Road through the Burrabazar handcarts, "
            "and one breakdown on one of the city's busiest crossings is felt on both "
            "banks. The scenario has Kolkata Traffic Police at the Kolkata end and Howrah "
            "City Police at the station end. Closure policy signal_hold at 60 s; loads and "
            "the tow time are modelled assumptions."),
        places=["esplanade", "bbd_bag", "howrah_bridge", "howrah_station"],
        route_segment_ids=route,
        departure_time="2026-11-04T18:15:00+05:30",
        vvip_class="X",
        closure_policy={"advance_closure_sec": 60, "closure_type": "signal_hold"},
        horizon_min=60, n_replications=10, seed=20261104, convoy_speed_kmh=30,
        weather={}, event_overrides={"market": 1.5},
        forced_events=[
            fe("rally_spillover", bridge, 0, 4500, 0.85,
               "evening commuter surge onto Howrah Bridge and the station approach", 950),
            fe("vehicle_breakdown", bridge, 600, 1500, 0.85,
               "bus broken down mid-span on Howrah Bridge — one lane lost until the tow"),
            fe("market_spillover", mg_road, 0, 3600, 0.7,
               "Burrabazar handcarts and hawkers on MG Road"),
            fe("rally_spillover", mg_road, 900, 2700, 0.6,
               "queue backing up MG Road from the bridge", 500),
            fe("market_spillover", named(net, first_leg(net, "howrah_bridge", "bbd_bag"),
                                         "Brabourne"), 0, 3600, 0.6,
               "handcarts on Brabourne Road"),
        ],
        expected_features=["station_surge", "bridge_choke_point", "breakdown_cascade",
                           "two_bank_coordination"],
        event_kind="egress_surge", crowd_class="HIGH", duration_class="hours",
    ))

    # (g) Red Road parade ──────────────────────────────────────────────────
    route = W("esplanade", "esplanade_sn_banerjee", "red_road", "red_road_south")
    red_road = named(net, out_of(net, route, "red_road"), "Red Road")
    lib.append(scenario(
        scenario_id="red_road_parade",
        name="Red Road Parade — Republic Day / Independence Day",
        name_bn="রেড রোডের কুচকাওয়াজ — প্রজাতন্ত্র দিবস / স্বাধীনতা দিবস",
        name_hi="रेड रोड परेड — गणतंत्र दिवस / स्वतंत्रता दिवस",
        category="event",
        description=(
            "SIMULATED. The ceremonial parade on Red Road on a national day (Republic Day "
            "26 Jan, Independence Day 15 Aug). The dignitaries' ceremonial movement to the "
            "dais is a Z-class protected movement (no person is named): from Esplanade "
            "along Jawaharlal Nehru Road and the Old Court House Street link to the north "
            "end of Red Road, then down Red Road to the dais. Red Road is held for the "
            "parade and the contingents; spectators and "
            "their parking load Sahid Khudiram Bose Road and Queensway. Full closure at "
            "150 s advance; crowd loads are modelled."),
        places=["esplanade", "red_road", "victoria_memorial", "eden_gardens"],
        route_segment_ids=route,
        departure_time="2027-01-26T08:30:00+05:30",
        vvip_class="Z",
        closure_policy={"advance_closure_sec": 150, "closure_type": "full_closure"},
        horizon_min=60, n_replications=10, seed=20270126, convoy_speed_kmh=30,
        weather={}, event_overrides={},
        forced_events=[
            fe("rally_spillover", red_road, 0, 5400, 0.75,
               "Red Road — parade contingents and the grandstand", 700),
            fe("rally_spillover", named(net, first_leg(net, "red_road", "babughat"), "Khudiram"),
               0, 5400, 0.6, "spectator parking and approach on Sahid Khudiram Bose Road", 500),
            fe("rally_spillover", named(net, first_leg(net, "victoria_memorial", "exide"), "Queensway"),
               600, 4800, 0.5, "spectator approach from the south on Queensway", 400),
        ],
        expected_features=["ceremonial", "z_protocol", "recurring_civic_event"],
        event_kind="ceremonial", crowd_class="HIGH", duration_class="hours",
    ))

    # (h) Gangasagar transit via Babughat ──────────────────────────────────
    route = W("howrah_station", "howrah_bridge", "babughat", "prinsep_ghat", "hastings",
              "kidderpore", "majerhat")
    bridge = named(net, out_of(net, route, "howrah_station"), "Howrah Bridge")
    arrivals = named(net, out_of(net, route, "howrah_bridge"), "Strand")
    camp = named(net, out_of(net, route, "babughat"), "Strand")
    by_prinsep = named(net, out_of(net, route, "prinsep_ghat"), "Strand")
    dh_road = named(net, out_of(net, route, "kidderpore"), "Diamond Harbour")
    lib.append(scenario(
        scenario_id="gangasagar_transit",
        name="Gangasagar Transit — Babughat Camp and the Bus Waves South",
        name_bn="গঙ্গাসাগর যাত্রা — বাবুঘাট ক্যাম্প আর দক্ষিণমুখী বাস",
        name_hi="गंगासागर यात्रा — बाबूघाट कैंप और दक्षिण की ओर बसें",
        category="event",
        description=(
            "SIMULATED. In the days before Makar Sankranti, pilgrims bound for Gangasagar "
            "on Sagar Island arrive at Howrah Station, cross Howrah Bridge and walk or ride "
            "along Strand Road to the transit camp at Babughat on the Hooghly bank, then "
            "leave by bus in waves towards the ferry crossings in the south: past Prinsep "
            "Ghat, through Hastings and Kidderpore and down Diamond Harbour Road over the "
            "Majerhat bridge. A morning wave: arrivals on the bridge and Strand Road, "
            "queues and boarding at the camp, stalls by Prinsep Ghat, and a pilgrim bus "
            "broken down on Diamond Harbour Road. Volumes and timings are modelled "
            "assumptions; signal_hold at 90 s keeps the bus waves moving."),
        places=["howrah_station", "howrah_bridge", "babughat", "prinsep_ghat", "kidderpore",
                "majerhat"],
        route_segment_ids=route,
        departure_time="2027-01-12T06:00:00+05:30",
        vvip_class="X",
        closure_policy={"advance_closure_sec": 90, "closure_type": "signal_hold"},
        horizon_min=60, n_replications=10, seed=20270112, convoy_speed_kmh=35,
        weather={}, event_overrides={},
        forced_events=[
            fe("rally_spillover", camp, 0, 21600, 0.9,
               "Babughat transit camp — pilgrim queues and bus boarding on Strand Road", 1200),
            fe("rally_spillover", arrivals, 0, 14400, 0.75,
               "pilgrims arriving along Strand Road from Howrah", 800),
            fe("rally_spillover", bridge, 0, 10800, 0.6,
               "pilgrims crossing Howrah Bridge from Howrah Station", 600),
            fe("market_spillover", by_prinsep, 0, 10800, 0.6,
               "camp stalls and waiting buses along Strand Road by Prinsep Ghat"),
            fe("vehicle_breakdown", dh_road, 1800, 1200, 0.7,
               "pilgrim bus broken down on Diamond Harbour Road"),
        ],
        expected_features=["pilgrim_transit", "bus_waves", "riverbank_camp",
                           "staged_departures"],
        event_kind="mass_gathering", crowd_class="HIGH", duration_class="multi_day",
    ))

    # (i) Kolkata Marathon ─────────────────────────────────────────────────
    route = W("babughat", "red_road", "red_road_south", "hastings", "prinsep_ghat", "babughat")
    khudiram = named(net, out_of(net, route, "babughat"), "Khudiram")
    red_rd = named(net, out_of(net, route, "red_road"), "Red Road")
    kidderpore_rd = named(net, out_of(net, route, "red_road_south"), "Kidderpore")
    strand_s = named(net, out_of(net, route, "hastings"), "Strand")
    strand_n = named(net, out_of(net, route, "prinsep_ghat"), "Strand")
    lib.append(scenario(
        scenario_id="kolkata_marathon",
        name="Kolkata Marathon — Red Road and Riverside Loop",
        name_bn="কলকাতা ম্যারাথন — রেড রোড আর গঙ্গার ধারের পথ",
        name_hi="कोलकाता मैराथन — रेड रोड और नदी किनारे का रास्ता",
        category="event",
        description=(
            "SIMULATED. A city marathon on a winter Sunday morning on a modelled loop "
            "(not an official route map): the gun at 05:30 by Eden Gardens on Sahid "
            "Khudiram Bose Road, down Red Road along the Maidan, out on Kidderpore Road to "
            "Hastings and back north along the river on Strand Road past Prinsep Ghat to "
            "Babughat. The field and its spectators hold each stretch in turn and the loop "
            "reopens in stages behind the sweep vehicle. Full closure at 60 s advance; the "
            "lead vehicle runs at race pace (12 km/h). Field size and timings are modelled "
            "assumptions."),
        places=["eden_gardens", "red_road", "prinsep_ghat", "babughat",
                "victoria_memorial"],
        route_segment_ids=route,
        departure_time="2026-12-20T05:30:00+05:30",
        vvip_class="X",
        closure_policy={"advance_closure_sec": 60, "closure_type": "full_closure"},
        horizon_min=60, n_replications=10, seed=20261220, convoy_speed_kmh=12,
        weather={}, event_overrides={},
        forced_events=[
            fe("rally_spillover", khudiram, 0, 2400, 0.85,
               "the start by Eden Gardens — runners and spectators (reopens after the sweep)",
               800),
            fe("rally_spillover", red_rd, 300, 2700, 0.8,
               "runners down Red Road along the Maidan", 700),
            fe("rally_spillover", kidderpore_rd, 900, 3000, 0.7,
               "runners on Kidderpore Road", 600),
            fe("rally_spillover", strand_s, 1800, 3600, 0.7,
               "runners north on Strand Road by the river", 600),
            fe("rally_spillover", strand_n, 2400, 3600, 0.75,
               "the run-in past Prinsep Ghat to Babughat", 650),
        ],
        expected_features=["race", "rolling_closure", "staged_reopening"],
        event_kind="race", crowd_class="HIGH", duration_class="hours",
    ))

    # (j) New Year's Eve on Park Street ────────────────────────────────────
    route = W("esplanade_sn_banerjee", "park_street", "mullickbazar", "park_circus")
    chowringhee = named(net, into(net, route, "park_street"), "Nehru")
    park_st = named(net, out_of(net, route, "park_street"), "Park Street")
    mts = named(net, out_of(net, route, "mullickbazar"), "Teresa", "Park Street")
    lib.append(scenario(
        scenario_id="park_street_new_year",
        name="New Year's Eve on Park Street",
        name_bn="পার্ক স্ট্রিটে বর্ষবরণের রাত",
        name_hi="पार्क स्ट्रीट पर नए साल की पूर्वसंध्या",
        category="event",
        description=(
            "SIMULATED. New Year's Eve, 23:15 to 00:15: the lights on Park Street and the "
            "crowds that come to see them. The scenario holds Park Street to vehicles for "
            "the night (an assumption the duty officer can change), the crowd fills Park "
            "Street from Jawaharlal Nehru Road to Mother Teresa Sarani, restaurant queues "
            "and food stalls load the kerbs, and after midnight the wave heads for "
            "Esplanade and Park Street Metro along Jawaharlal Nehru Road. An ambulance "
            "(108) window through the post-midnight dispersal. Crowd loads are modelled."),
        places=["park_street", "esplanade", "park_circus"],
        route_segment_ids=route,
        departure_time="2026-12-31T23:15:00+05:30",
        vvip_class="X",
        closure_policy={"advance_closure_sec": 120, "closure_type": "full_closure"},
        horizon_min=60, n_replications=10, seed=20261231, convoy_speed_kmh=20,
        weather={}, event_overrides={"market": 1.8},
        forced_events=[
            fe("rally_spillover", park_st, 0, 7200, 0.95,
               "Park Street — New Year's Eve crowd under the lights", 1300),
            fe("market_spillover", park_st, 0, 7200, 0.75,
               "restaurant queues and food stalls on Park Street"),
            fe("rally_spillover", mts, 900, 5400, 0.7,
               "crowd overflow on Mother Teresa Sarani", 700),
            fe("rally_spillover", chowringhee, 2700, 3600, 0.8,
               "post-midnight wave towards Esplanade and Park Street Metro", 900),
            fe("emergency_vehicle", chowringhee, 2700, 300, 0.9,
               "ambulance (108) window through the post-midnight dispersal"),
        ],
        expected_features=["festival_crowd", "pedestrianised_street", "midnight_egress",
                           "green_corridor_request"],
        event_kind="mass_gathering", crowd_class="EXTREME", duration_class="hours",
    ))

    # (k) EM Bypass crash with an ambulance window ─────────────────────────
    route = W("ruby", "science_city", "park_circus", "mullickbazar", "exide")
    crash = named(net, out_of(net, route, "ruby"), "Bypass")
    amb = ev_windows(net, route, start_sec=240, speed_kmh=40,
                     label="ambulance (108) window to SSKM Hospital",
                     places=[road for road in (net.segs[s]["name"] for s in route)])
    lib.append(scenario(
        scenario_id="em_bypass_accident_ambulance",
        name="EM Bypass Crash — Ambulance Window",
        name_bn="ই এম বাইপাসে দুর্ঘটনা — অ্যাম্বুলেন্সের জন্য পথ",
        name_hi="ईएम बाईपास पर दुर्घटना — एम्बुलेंस के लिए रास्ता",
        category="incident",
        description=(
            "SIMULATED. A Friday morning peak: a two-vehicle crash between Ruby and Science "
            "City blocks two lanes of EM Bypass (crash debris; no casualty details are "
            "modelled). An ambulance (108) leaves the scene four minutes later for SSKM "
            "Hospital: north on EM Bypass, over the Maa Flyover to Park Circus, along "
            "Mother Teresa Sarani and AJC Bose Road to Exide crossing, a short run from the "
            "hospital. Each stretch needs a green-corridor window as the ambulance reaches "
            "it, timed on the roads' lengths; the AI proposes each window and a named "
            "officer approves it. The rest of the queue on EM Bypass is held until the "
            "crash is cleared. Times and speeds are modelled assumptions."),
        places=["ruby", "science_city", "park_circus", "exide", "sskm"],
        route_segment_ids=route,
        departure_time="2026-11-06T08:40:00+05:30",
        vvip_class="X",
        closure_policy={"advance_closure_sec": 45, "closure_type": "signal_hold"},
        horizon_min=45, n_replications=10, seed=20261106, convoy_speed_kmh=40,
        weather={}, event_overrides={"ambulance": 1.0},
        forced_events=[
            fe("vehicle_breakdown", crash, 0, 2700, 0.85,
               "two-vehicle crash blocks two lanes of EM Bypass (debris)"),
            *amb,
        ],
        expected_features=["road_crash", "green_corridor_request", "ambulance_window",
                           "peak_hour"],
        event_kind="emergency_evacuation", crowd_class="LOW", duration_class="minutes",
    ))

    # (k2) metro works on Diamond Harbour Road (the seeded work-zone profile)
    route = W("behala_chowrasta", "taratala", "majerhat", "kidderpore")
    behala = named(net, out_of(net, route, "behala_chowrasta"), "Diamond Harbour")
    to_kidderpore = named(net, out_of(net, route, "majerhat"), "Diamond Harbour")
    lib.append(scenario(
        scenario_id="metro_work_zone",
        name="Metro Work Zone — Diamond Harbour Road",
        name_bn="মেট্রোর কাজ — ডায়মন্ড হারবার রোডে লেন বন্ধ",
        name_hi="मेट्रो निर्माण क्षेत्र — डायमंड हार्बर रोड",
        category="ops",
        description=(
            "SIMULATED. A planned, published work zone: metro construction along Diamond "
            "Harbour Road holds barricaded lanes for weeks between Behala Chowrasta, "
            "Taratala and Kidderpore (a modelled work zone; no project timeline is "
            "claimed). On a weekday morning an inspection convoy runs the stretch from "
            "Behala over the Majerhat bridge to Kidderpore while the barricades pinch the "
            "carriageway and the Behala bazaar's traffic squeezes the remaining lanes. "
            "Partial closure at 60 s advance; lane losses and loads are modelled."),
        places=["behala_chowrasta", "taratala", "majerhat", "kidderpore"],
        route_segment_ids=route,
        departure_time="2026-11-10T09:15:00+05:30",
        vvip_class="X",
        closure_policy={"advance_closure_sec": 60, "closure_type": "partial_closure"},
        horizon_min=60, n_replications=8, seed=20250814, convoy_speed_kmh=40,
        weather={}, event_overrides={"market": 1.5},
        forced_events=[
            fe("vehicle_breakdown", behala, 0, 39600, 0.9,
               "metro works — two lanes barricaded on Diamond Harbour Road at Behala"),
            fe("vehicle_breakdown", to_kidderpore, 0, 39600, 0.85,
               "metro works — a lane barricaded towards Kidderpore"),
            fe("market_spillover", behala, 0, 10800, 0.7,
               "Behala bazaar traffic squeezed by the barricades"),
        ],
        expected_features=["planned_work_zone", "standing_lane_loss", "published_diversion"],
        event_kind="work_zone", crowd_class="LOW", duration_class="multi_week",
    ))

    # (l) the emulated ANPR watchlist sweep (vehicles only, officer-gated) ─
    route = sweep_route(net)
    lib.append(scenario(
        scenario_id="watchlist_anpr_sweep",
        name="Stolen-Vehicle ANPR Sweep — Central Kolkata (Emulated)",
        name_bn="চুরি যাওয়া গাড়ির খোঁজে এএনপিআর সুইপ — মধ্য কলকাতা (এমুলেটেড)",
        name_hi="चोरी के वाहन के लिए एएनपीआर स्वीप — मध्य कोलकाता (इम्यूलेटेड)",
        category="enforcement",
        description=(
            "EMULATED WATCHLIST SCENARIO (clearly labelled, never a live feed). A "
            "stolen-vehicle FIR drives an ANPR camera sweep through central Kolkata: "
            + sweep_text(net, route) + " Deterministic camera reads cover background "
            "traffic, the FIR-named STOLEN plate WB06EM9001 and the earmark-exercise "
            "plate WB02EM4321 — every synthetic plate carries an EM series, every sighting "
            "lands with source emulated_anpr, and the oracle, never the tape, computes each "
            "hit and rule. The FIR is the scenario's premise, stated at t0 as a labelled "
            "EMULATED precondition (a stolen_vehicle_fir earmark on WB06EM9001 by "
            "'event-emulator (system) — scenario precondition'; if the oracle cannot take "
            "it, that plate's reads are skipped): the stolen car's reads hit as "
            "stolen_vehicle and file evidence-only R_STOLEN_SIGHTING recommendations, never "
            "a fine. WB02EM4321 is an OPERATOR EXERCISE: the emulator never earmarks it, so "
            "its reads hit as earmarked_plate only when a duty officer has earmarked "
            "WB02EM4321 (Watchlist: a lawful basis and their name) before the run — on a "
            "fresh install they are ordinary sightings. Only a named human officer acts on "
            "any recommendation. Two Kolkata Traffic Police patrol units animate alongside "
            "(agency_unit frames). Vehicles only, never persons."),
        places=sweep_places(net, route),
        route_segment_ids=route,
        departure_time="2026-11-05T10:30:00+05:30",
        vvip_class="X",
        closure_policy={"advance_closure_sec": 0, "closure_type": "signal_hold"},
        horizon_min=45, n_replications=8, seed=20261105, convoy_speed_kmh=40,
        weather={}, event_overrides={}, forced_events=[],
        expected_features=["emulated_anpr", "stolen_plate_hit", "operator_earmark_exercise",
                           "human_approval_flow"],
        event_kind="crime_incident", crowd_class="LOW", duration_class="minutes",
        stolen_fir_ref="FIR 4401/2026, Hare Street PS",
    ))

    # (m) Burrabazar market fire — fire-tender access and an ambulance window
    route = W("park_street", "esplanade_sn_banerjee", "esplanade", "central_avenue_mg_road",
              "howrah_bridge", "bbd_bag")
    cr_avenue = named(net, out_of(net, route, "esplanade"), "Chittaranjan")
    mg_road = named(net, out_of(net, route, "central_avenue_mg_road"), "Gandhi")
    brabourne = named(net, out_of(net, route, "howrah_bridge"), "Brabourne")
    tender_speed = 25.0
    lib.append(scenario(
        scenario_id="burrabazar_market_fire",
        name="Burrabazar Market Fire — Fire-Tender Access and Ambulance Window",
        name_bn="বড়বাজারে অগ্নিকাণ্ড — দমকলের গাড়ির পথ আর অ্যাম্বুলেন্সের পথ",
        name_hi="बड़ाबाज़ार में आग — दमकल की गाड़ियों और एम्बुलेंस के लिए रास्ता",
        category="incident",
        description=(
            "SIMULATED. A weekday afternoon in Burrabazar (Wednesday 18 Nov 2026, 14:40; a "
            "scenario date, not a record): a fire breaks out in a market building in the "
            "narrow lanes between Mahatma Gandhi Road and Brabourne Road, a short walk from "
            "the Kolkata end of Howrah Bridge. The nearest fire tender, from C R Avenue Fire "
            "Station at the Chittaranjan Avenue crossing, needs a window west along MG Road "
            "(one-way towards the bridge); a second tender line from the West Bengal Fire & "
            "Emergency Services headquarters near Park Street needs a green corridor up "
            "Jawaharlal Nehru Road to Esplanade, along Chittaranjan Avenue and MG Road, round "
            "the Howrah Bridge end and into Brabourne Road (one-way towards BBD Bag). Once "
            "the tenders are in, parked tenders and hose lines take lanes on MG Road and "
            "Brabourne Road, a police cordon narrows Strand Road at the lane mouths, "
            "handcarts are pushed out onto Chittaranjan Avenue, diverted traffic loads "
            "Strand Road north and the afternoon goods traffic queues on Howrah Bridge. The "
            "AI proposes each tender window, a goods-vehicle hold on the Howrah Bridge "
            "approaches (Howrah City Police at the Howrah end, Kolkata Traffic Police at the "
            "Kolkata end), a request to the power utility to isolate supply to the block, "
            "and the staged reopening of the cordoned roads; a named officer approves or "
            "rejects each, and nothing is sent by itself. Twenty-five minutes in, an "
            "ambulance (108) standing by at the east cordon needs a window along MG Road to "
            "Kolkata Medical College (no casualty details are modelled). Fire spread, "
            "turnout and travel times, lane losses and loads are modelled assumptions, not "
            "measurements."),
        places=["park_street", "esplanade", "bbd_bag", "howrah_bridge", "howrah_station",
                "medical_college"],
        route_segment_ids=route,
        departure_time="2026-11-18T14:40:00+05:30",
        vvip_class="X",
        closure_policy={"advance_closure_sec": 45, "closure_type": "signal_hold"},
        horizon_min=60, n_replications=10, seed=20261118, convoy_speed_kmh=tender_speed,
        weather={}, event_overrides={"market": 1.5},
        forced_events=[
            *ev_windows(net, [mg_road], start_sec=60, speed_kmh=tender_speed,
                        label="fire tender (C R Avenue Fire Station) green-corridor window",
                        places=["Mahatma Gandhi Road west from the Chittaranjan Avenue "
                                "crossing"]),
            *ev_windows(net, route, start_sec=120, speed_kmh=tender_speed,
                        label="fire tender (WBFES HQ) green-corridor window",
                        places=["Jawaharlal Nehru Road, Park Street to Esplanade",
                                "Jawaharlal Nehru Road at Esplanade",
                                "Chittaranjan Avenue to the MG Road crossing",
                                "Mahatma Gandhi Road to the Howrah Bridge end",
                                "Brabourne Road towards BBD Bag"]),
            fe("vehicle_breakdown", mg_road, 300, 3300, 0.9,
               "parked fire tenders and hose lines on Mahatma Gandhi Road at the Burrabazar "
               "fire ground (lanes lost)"),
            fe("vehicle_breakdown", brabourne, 750, 2850, 0.85,
               "second tender line and hose lines on Brabourne Road (lanes lost)"),
            fe("vehicle_breakdown", named(net, first_leg(net, "howrah_bridge", "babughat"),
                                       "Strand"), 600, 3000, 0.6,
               "police cordon at the Burrabazar lane mouths narrows Strand Road (one lane)"),
            fe("market_spillover", cr_avenue, 600, 3000, 0.6,
               "handcarts and porters pushed out of the cordoned lanes onto Chittaranjan "
               "Avenue"),
            fe("rally_spillover", named(net, first_leg(net, "howrah_station", "howrah_bridge"),
                                     "Howrah Bridge"), 600, 3000, 0.7,
               "afternoon goods traffic for the Burrabazar wholesale market queued on Howrah "
               "Bridge (the load the proposed goods-vehicle hold would take off)", 600),
            fe("rally_spillover", named(net, first_leg(net, "howrah_bridge", "bagbazar"),
                                     "Strand"), 900, 2700, 0.6,
               "traffic diverted from MG Road and Brabourne Road onto Strand Road north", 450),
            *ev_windows(net, W("central_avenue_mg_road", "college_street"), start_sec=1500,
                        speed_kmh=tender_speed,
                        label="ambulance (108) window to Kolkata Medical College",
                        places=["Mahatma Gandhi Road east from the Chittaranjan Avenue "
                                "crossing to College Street"]),
        ],
        expected_features=["fire_response", "fire_tender_green_corridor", "narrow_lane_access",
                           "cordon_lane_loss", "goods_vehicle_hold_proposal",
                           "power_isolation_request_proposal", "ambulance_window",
                           "two_bank_coordination", "staged_reopening"],
        event_kind="emergency_evacuation", crowd_class="HIGH", duration_class="hours",
    ))

    # (n) DVC release and Howrah waterlogging — the cross-river diversion ──
    route = W("nabanna", "vidyasagar_setu", "hastings", "prinsep_ghat", "babughat",
              "howrah_bridge", "howrah_station")
    gt_road = named(net, first_leg(net, "nabanna", "howrah_station"), "Grand Trunk")
    setu = named(net, out_of(net, route, "nabanna"), "Vidyasagar Setu")
    strand = named(net, out_of(net, route, "babughat"), "Strand")
    bridge = named(net, out_of(net, route, "howrah_bridge"), "Howrah Bridge")
    if gt_road in route:
        raise SystemExit("ERROR: the cross-river diversion must avoid Grand Trunk Road")
    lib.append(scenario(
        scenario_id="dvc_release_howrah_waterlogging",
        name="DVC Release and Howrah Waterlogging — Cross-River Diversion",
        name_bn="ডিভিসির জল ছাড়া আর হাওড়ায় জল জমা — দুই সেতু দিয়ে বিকল্প পথ",
        name_hi="डीवीसी से पानी छोड़ा जाना और हावड़ा में जलभराव — दोनों पुलों से वैकल्पिक रास्ता",
        category="weather",
        description=(
            "SIMULATED. A monsoon weekday morning (Tuesday 14 Sep 2027, 08:45; a scenario, "
            "not a forecast and not a record of any real release). Damodar Valley "
            "Corporation (DVC) has announced a release from its Maithon and Panchet "
            "reservoirs; the release figure in this scenario is a SIMULATED input, not a DVC "
            "figure. The scenario assumes that, with the lower Damodar high, steady rain "
            "(modelled at 12 mm/h) and a high tide on the Hooghly (MODELLED tide phase), "
            "Howrah's drains back up: Grand Trunk Road between Nabanna and Howrah Station "
            "goes under water and a bus stalls in it, and water stands on the Howrah Station "
            "approach and at the foot of the Nabanna approach to Vidyasagar Setu. On the "
            "network Sahoshi models, the only dry way from Nabanna to Howrah Station is "
            "across the river twice: over Vidyasagar Setu, along Strand Road past Prinsep "
            "Ghat and Babughat, and back over Howrah Bridge, so diverted traffic loads both "
            "bridges. A WBSDMA pump-and-relief column runs that diversion behind a Howrah "
            "City Police pilot vehicle. The AI proposes the diversion, signal holds on "
            "Strand Road, a bus re-routing note for WBTC and a three-language traffic "
            "advisory; named officers of Howrah City Police and Kolkata Traffic Police each "
            "decide on their side of the river, and nothing is published by itself. Rain, "
            "tide, water depth, spread and loads are modelled assumptions."),
        places=["nabanna", "vidyasagar_setu", "prinsep_ghat", "babughat", "howrah_bridge",
                "howrah_station", "garden_reach"],
        route_segment_ids=route,
        departure_time="2027-09-14T08:45:00+05:30",
        vvip_class="X",
        closure_policy={"advance_closure_sec": 60, "closure_type": "signal_hold"},
        horizon_min=60, n_replications=10, seed=20270914, convoy_speed_kmh=30,
        weather={"monsoon": True, "rain_intensity_mm_h": 12.0},
        event_overrides={"waterlogging": 2.5, "breakdown": 1.4},
        forced_events=[
            fe("waterlogging", gt_road, 0, 3600, 0.85,
               "Grand Trunk Road between Nabanna and Howrah Station under water (drains "
               "backed up)"),
            fe("rally_spillover", setu, 300, 3300, 0.7,
               "traffic diverted from Grand Trunk Road onto Vidyasagar Setu", 700),
            fe("rally_spillover", bridge, 300, 3300, 0.75,
               "traffic diverted from the flooded Howrah-side roads onto Howrah Bridge", 800),
            fe("waterlogging", bridge, 600, 3000, 0.55,
               "water on the Howrah Station approach at the Howrah end of Howrah Bridge"),
            fe("waterlogging", setu, 900, 2700, 0.45,
               "standing water at the foot of the Nabanna approach to Vidyasagar Setu"),
            fe("rally_spillover", strand, 900, 2700, 0.55,
               "cross-river diverted traffic along Strand Road between the two bridges", 400),
            fe("vehicle_breakdown", gt_road, 1200, 1800, 0.75,
               "bus stalled in the water on Grand Trunk Road"),
        ],
        expected_features=["river_release_flood", "high_tide_drainage", "waterlogging",
                           "cross_river_diversion", "two_bank_coordination", "relief_priority",
                           "trilingual_advisory"],
        event_kind="emergency_evacuation", crowd_class="MEDIUM", duration_class="hours",
    ))

    # (o) Kali Puja night — air-quality advisory, Kalighat crowd, ambulance ─
    route = W("tollygunge", "kalighat", "rashbehari", "hazra", "exide")
    spm_south = named(net, out_of(net, route, "tollygunge"), "Mukherjee")
    spm_kalighat = named(net, out_of(net, route, "kalighat"), "Mukherjee")
    spm_stalls = named(net, out_of(net, route, "rashbehari"), "Mukherjee")
    lib.append(scenario(
        scenario_id="kali_puja_air_quality",
        name="Kali Puja Night — Air-Quality Advisory, Kalighat Crowd and Ambulance Priority",
        name_bn="কালীপুজোর রাত — বাতাসের মান নিয়ে পরামর্শ, কালীঘাটের ভিড় আর অ্যাম্বুলেন্সের "
                "অগ্রাধিকার",
        name_hi="काली पूजा की रात — वायु गुणवत्ता परामर्श, कालीघाट की भीड़ और एम्बुलेंस को "
                "प्राथमिकता",
        category="multi_event",
        description=(
            "SIMULATED. Kali Puja night (Sunday 8 Nov 2026, 21:30, the Amavasya night; a "
            "scenario, not a forecast). Firecrackers across the city push fine-particle "
            "pollution up through the evening: the scenario's PM2.5 readings (SIMULATED, not "
            "measurements) climb from the Moderately Polluted band at 18:00 to the Very Poor "
            "band by 21:00 and touch Severe near midnight, banded indicatively against "
            "India's National Air Quality Index (whose bands are defined on 24-hour "
            "averages). Devotees fill SP Mukherjee Road around Kalighat temple, flower, lamp "
            "and sweet stalls line the road from Hazra to Rashbehari and pandal stalls load "
            "Rash Behari Avenue, so traffic slows along the whole stretch. Breathing-"
            "difficulty calls rise (modelled as ambulance x1.5). Fifteen minutes in, an "
            "ambulance (108) on a breathing-difficulty call needs windows from Tollygunge "
            "past Kalighat, Rashbehari and Hazra to Exide crossing, a short run from SSKM "
            "Hospital. The AI proposes each window, a priority flag for breathing-difficulty "
            "calls and a public health advisory in Bengali, English and Hindi; a named duty "
            "officer approves or rejects each, and nothing is published by itself. Crowd "
            "loads, readings and speeds are modelled assumptions; no individual is "
            "identified."),
        places=["tollygunge", "kalighat", "rashbehari", "hazra", "exide", "sskm",
                "deshapriya_park"],
        route_segment_ids=route,
        departure_time="2026-11-08T21:30:00+05:30",
        vvip_class="X",
        closure_policy={"advance_closure_sec": 45, "closure_type": "signal_hold"},
        horizon_min=60, n_replications=10, seed=20261108, convoy_speed_kmh=20,
        weather={}, event_overrides={"market": 1.8, "ambulance": 1.5},
        forced_events=[
            fe("rally_spillover", spm_kalighat, 0, 3600, 0.85,
               "Kali Puja night crowd for Kalighat temple on SP Mukherjee Road", 850),
            fe("rally_spillover", spm_south, 0, 3600, 0.7,
               "temple-bound crowd and parked vehicles on SP Mukherjee Road south of "
               "Kalighat", 600),
            fe("market_spillover", spm_stalls, 0, 3600, 0.65,
               "flower, lamp and sweet stalls on SP Mukherjee Road between Hazra and "
               "Rashbehari"),
            fe("market_spillover", named(net, first_leg(net, "rashbehari", "deshapriya_park"),
                                      "Rash Behari"), 0, 3600, 0.5,
               "Kali Puja pandal stalls on Rash Behari Avenue"),
            *ev_windows(net, route, start_sec=900, speed_kmh=20,
                        label="ambulance (108) window on a breathing-difficulty call to "
                              "SSKM Hospital",
                        places=["SP Mukherjee Road, Tollygunge to Kalighat",
                                "SP Mukherjee Road past Kalighat to Rashbehari",
                                "SP Mukherjee Road, Rashbehari to Hazra",
                                "Ashutosh Mukherjee Road, Hazra to Exide"]),
        ],
        expected_features=["festival_night", "air_quality_advisory_proposal",
                           "trilingual_advisory", "temple_crowd", "respiratory_call_priority",
                           "ambulance_window"],
        event_kind="mass_gathering", crowd_class="HIGH", duration_class="hours",
    ))

    # (p) Pre-monsoon heatwave afternoon — overheated vehicles, duty rotations
    route = W("nabanna", "vidyasagar_setu", "park_circus", "science_city", "chingrighata",
              "salt_lake_stadium", "ultadanga")
    lib.append(scenario(
        scenario_id="pre_monsoon_heatwave",
        name="Pre-Monsoon Heatwave Afternoon — Overheated Vehicles and Duty Rotations",
        name_bn="বর্ষার আগে তাপপ্রবাহের দুপুর — গরমে বিকল গাড়ি আর ডিউটির পালা",
        name_hi="मानसून से पहले लू की दोपहर — गर्मी से ख़राब गाड़ियाँ और ड्यूटी की पारियाँ",
        category="weather",
        description=(
            "SIMULATED. A pre-monsoon heatwave afternoon (Tuesday 27 Apr 2027, 14:00; a "
            "scenario, not a forecast). The scenario assumes IMD's heatwave criteria for the "
            "plains are met: a SIMULATED maximum of 41.8 °C against a SIMULATED normal of "
            "36.2 °C (departure +5.6 °C; the criteria are a maximum of at least 40 °C with a "
            "departure of at least 4.5 °C, or a maximum of at least 45 °C). No real IMD "
            "bulletin is quoted. Vehicles overheat: a bus stalls on Vidyasagar Setu, a car "
            "with a burst tyre stops on the Maa Flyover, a goods vehicle overheats on EM "
            "Bypass between Science City and Chingrighata and a car stalls near Ultadanga "
            "(breakdowns modelled at x1.6). Pedestrian flows and street trading thin out in "
            "the heat (modelled crowd LOW, market x0.7) and heat-illness calls rise "
            "(ambulance x1.3). A Kolkata Traffic Police recovery van runs the corridor from "
            "the Nabanna end of Vidyasagar Setu over the AJC Bose Road flyover and the Maa "
            "Flyover and up EM Bypass to Ultadanga, clearing each breakdown. The AI proposes "
            "where to pre-position recovery vans, shorter duty rotations with shade and "
            "water for traffic staff at the most exposed crossings (Esplanade, Park Street, "
            "Shyambazar, Ultadanga) and a heat advisory for road users in Bengali, English "
            "and Hindi; a named duty officer approves or rejects each. Temperatures, "
            "breakdown rates and loads are modelled assumptions."),
        places=["vidyasagar_setu", "park_circus", "science_city", "chingrighata",
                "salt_lake_stadium", "ultadanga", "esplanade", "park_street", "shyambazar"],
        route_segment_ids=route,
        departure_time="2027-04-27T14:00:00+05:30",
        vvip_class="X",
        closure_policy={"advance_closure_sec": 30, "closure_type": "signal_hold"},
        horizon_min=60, n_replications=10, seed=20270427, convoy_speed_kmh=35,
        weather={}, event_overrides={"breakdown": 1.6, "market": 0.7, "ambulance": 1.3},
        forced_events=[
            fe("vehicle_breakdown", named(net, out_of(net, route, "nabanna"), "Vidyasagar Setu"),
               300, 1800, 0.75,
               "bus overheated and stalled on Vidyasagar Setu (one lane lost until the "
               "recovery van clears it)"),
            fe("vehicle_breakdown", named(net, out_of(net, route, "park_circus"), "Maa"),
               900, 900, 0.55, "car with a burst tyre stopped on the Maa Flyover"),
            fe("vehicle_breakdown", named(net, out_of(net, route, "science_city"), "Bypass"),
               1200, 1500, 0.7,
               "goods vehicle overheated on EM Bypass between Science City and Chingrighata"),
            fe("vehicle_breakdown", named(net, out_of(net, route, "salt_lake_stadium"),
                                       "Bypass"), 2100, 1200, 0.6,
               "car stalled with an overheated engine on EM Bypass near Ultadanga"),
        ],
        expected_features=["heatwave", "vehicle_overheating_breakdowns",
                           "recovery_van_prepositioning", "duty_rotation_proposal",
                           "reduced_pedestrian_flow", "trilingual_advisory"],
        event_kind="work_zone", crowd_class="LOW", duration_class="hours",
    ))

    # (q) Nor'wester (Kalbaishakhi) squall — tree-falls, live wire, reopening
    route = W("ultadanga", "salt_lake_stadium", "chingrighata", "science_city", "ruby")
    by_ultadanga = named(net, out_of(net, route, "ultadanga"), "Bypass")
    by_stadium = named(net, out_of(net, route, "salt_lake_stadium"), "Bypass")
    by_chingrighata = named(net, out_of(net, route, "chingrighata"), "Bypass")
    by_science_city = named(net, out_of(net, route, "science_city"), "Bypass")
    lib.append(scenario(
        scenario_id="norwester_squall_treefall",
        name="Nor'wester Squall — Tree-Falls, Live-Wire Hazard and Staged Reopening",
        name_bn="কালবৈশাখী ঝড় — গাছ পড়ে রাস্তা বন্ধ, বিদ্যুতের তারের বিপদ আর ধাপে ধাপে রাস্তা খোলা",
        name_hi="काल बैसाखी तूफ़ान — पेड़ गिरे, बिजली के तार का ख़तरा और चरणबद्ध तरीके से सड़कें "
                "खुलना",
        category="weather",
        description=(
            "SIMULATED. A Nor'wester (Kalbaishakhi) evening (Thursday 6 May 2027; a "
            "scenario, not a forecast). A squall line crossed the city at about 17:20 with "
            "gusts SIMULATED at 70-90 km/h and heavy rain (modelled at 25 mm/h, STORM). At "
            "17:40 the rain lingers and trees are down across the arterials: EM Bypass "
            "between Ultadanga and Ruby in three places (a weakened tree falls in a later "
            "gust), Red Road along the Maidan, AJC Bose Road between Exide and Moulali, and "
            "Rash Behari Avenue, where an overhead wire is also down across the road near "
            "Gariahat (live-wire hazard). Signals at Ultadanga are dark after a feeder trips "
            "(MODELLED). A KMC tree-clearing crew with a West Bengal Fire & Emergency "
            "Services rescue tender, escorted by Kolkata Traffic Police (and the Bidhannagar "
            "Police Commissionerate on its stretch), works south along EM Bypass from "
            "Ultadanga, so the corridor reopens in stages behind it. The stack may PROPOSE a "
            "request to the power utility (and to WBTC if it is a tram overhead line) to "
            "isolate the wire on Rash Behari Avenue — a proposal a named duty officer "
            "approves or rejects; nothing is sent by itself. Twenty minutes in, an ambulance "
            "(108) from Gariahat to Ruby General Hospital needs a window over the Bijon Setu "
            "connector. Every reopening is proposed by the AI and decided by a named "
            "officer. Gusts, rain, clearance times and loads are modelled assumptions."),
        places=["ultadanga", "salt_lake_stadium", "chingrighata", "science_city", "ruby",
                "red_road", "exide", "moulali", "rashbehari", "deshapriya_park", "gariahat"],
        route_segment_ids=route,
        departure_time="2027-05-06T17:40:00+05:30",
        vvip_class="X",
        closure_policy={"advance_closure_sec": 60, "closure_type": "partial_closure"},
        horizon_min=60, n_replications=8, seed=20270506, convoy_speed_kmh=20,
        weather={"monsoon": False, "rain_intensity_mm_h": 25.0},
        event_overrides={"breakdown": 1.5, "signal_fault": 2.0},
        forced_events=[
            fe("vehicle_breakdown", by_stadium, 0, 1500, 0.9,
               "tree down across EM Bypass between Chingrighata and Salt Lake Stadium "
               "(cleared first)"),
            fe("vehicle_breakdown", by_chingrighata, 0, 2400, 0.85,
               "tree down on EM Bypass between Science City and Chingrighata (cleared "
               "second)"),
            fe("vehicle_breakdown", named(net, first_leg(net, "red_road", "red_road_south"),
                                       "Red Road"), 0, 3600, 0.9,
               "Red Road closed — trees down along the Maidan"),
            fe("vehicle_breakdown", named(net, first_leg(net, "exide", "mullickbazar"), "Bose"),
               0, 1800, 0.6,
               "branches down on AJC Bose Road between Exide and Mullickbazar (one lane)"),
            fe("vehicle_breakdown", named(net, first_leg(net, "rashbehari", "deshapriya_park"),
                                       "Rash Behari"), 0, 1800, 0.75,
               "tree down on Rash Behari Avenue between Rashbehari crossing and Deshapriya "
               "Park"),
            fe("vehicle_breakdown", named(net, first_leg(net, "deshapriya_park", "gariahat"),
                                       "Rash Behari"), 0, 3000, 0.9,
               "overhead wire down across Rash Behari Avenue between Deshapriya Park and "
               "Gariahat — closed until the line is isolated (live-wire hazard)"),
            fe("signal_fault", by_ultadanga, 0, 2400, 0.7,
               "signals dark at Ultadanga after a feeder trips in the squall"),
            fe("vehicle_breakdown", named(net, first_leg(net, "mullickbazar", "moulali"),
                                       "Bose"), 300, 2400, 0.8,
               "hoarding frame and branches down on AJC Bose Road between Mullickbazar and "
               "Moulali"),
            fe("vehicle_breakdown", by_science_city, 600, 2700, 0.8,
               "tree down in a later gust on EM Bypass between Ruby and Science City "
               "(cleared last)"),
            *ev_windows(net, W("gariahat", "ruby"), start_sec=1200, speed_kmh=25,
                        label="ambulance (108) window to Ruby General Hospital",
                        places=["Rash Behari Avenue Connector (Bijon Setu), Gariahat to "
                                "Ruby"]),
        ],
        expected_features=["norwester_squall", "tree_fall_lane_loss",
                           "live_wire_hazard_proposal", "staged_reopening", "signals_dark",
                           "ambulance_window"],
        event_kind="work_zone", crowd_class="LOW", duration_class="hours",
    ))

    # (s) Bijoya Dashami immersion procession — the procession class ───────
    route = W("shyambazar", "bagbazar", "howrah_bridge", "babughat")
    bagbazar_st = named(net, out_of(net, route, "shyambazar"), "Bagbazar")
    strand_bank = named(net, out_of(net, route, "bagbazar"), "Strand")
    strand_ghat = named(net, out_of(net, route, "howrah_bridge"), "Strand")
    amb_start, amb_speed = 1500.0, 18.0
    evs = ev_windows(net, route, start_sec=amb_start, speed_kmh=amb_speed,
                     label="ambulance (108) green-corridor window",
                     places=["Bagbazar Street", "Strand Bank Road past Kumartuli",
                             "Strand Road to Babughat"])
    lib.append(scenario(
        scenario_id="bijoya_immersion_procession",
        name="Bijoya Dashami — Immersion Processions to the Ghats",
        name_bn="বিজয়া দশমী — ঘাটে বিসর্জনের শোভাযাত্রা",
        name_hi="विजया दशमी — घाटों तक विसर्जन की शोभायात्रा",
        category="event",
        description=(
            "SIMULATED. Evening of Bijoya Dashami: idols from the North Kolkata pandals are "
            "carried in procession from Shyambazar along Bagbazar Street and down Strand "
            "Bank Road past Kumartuli to the immersion ghats by Babughat on Strand Road. "
            "Each procession moves at walking pace with its trucks, drummers and followers, "
            "holding each stretch in turn and releasing it behind; the river-side lanes "
            "queue while the ghats are busy. Full closure at 120 s advance, rolled ahead of "
            "the procession and lifted behind it. Twenty-five minutes in, an ambulance (108) "
            "asks for a window along the same riverside stretch. Procession sizes, timings "
            "and speeds are modelled assumptions, not an official route map; the AI "
            "proposes each hold and a named officer decides."),
        places=["shyambazar", "bagbazar", "kumartuli", "howrah_bridge", "babughat"],
        route_segment_ids=route,
        departure_time="2026-10-02T18:00:00+05:30",
        vvip_class="X",
        closure_policy={"advance_closure_sec": 120, "closure_type": "full_closure"},
        horizon_min=60, n_replications=10, seed=202610021, convoy_speed_kmh=4,
        weather={}, event_overrides={"market": 1.4, "ambulance": 1.0},
        forced_events=[
            fe("rally_spillover", bagbazar_st, 0, 2400, 0.9,
               "immersion procession leaving Bagbazar along Bagbazar Street", 850),
            fe("rally_spillover", strand_bank, 900, 2700, 0.85,
               "procession on Strand Bank Road past Kumartuli", 800),
            fe("rally_spillover", strand_ghat, 1800, 3600, 0.9,
               "processions queueing for the ghats on Strand Road by Babughat", 900),
            *evs,
        ],
        expected_features=["procession", "rolling_closure", "ghat_queue",
                           "green_corridor_request"],
        event_kind="procession", crowd_class="EXTREME", duration_class="hours",
    ))
    return lib


#: Named segments the profiles' own causes sit on (filled by build()).
segments_used: dict[str, int] = {}


def profile_segments(net: Network, lib: list[dict]) -> dict[str, int]:
    """The segments profiles.py's added causes name (by role)."""
    by = {u["id"]: u["scenarioConfig"]["route_segment_ids"] for u in lib}
    base, cloud, sweep = by["vvip_convoy_base"], by["cloudburst_high_tide"], \
        by["watchlist_anpr_sweep"]
    out = {
        "em_bypass_salt_lake": named(net, out_of(net, base, "chingrighata"), "Bypass"),
        "khudiram_bose_road": segments_used["khudiram_bose_road"],
        "strand_road_babughat": segments_used["strand_road_babughat"],
        "rg_kar_road_ultadanga": named(net, out_of(net, cloud, "ultadanga"), "Bidhannagar",
                                       "Gobinda"),
        "bidhan_sarani": named(net, out_of(net, cloud, "shyambazar"), "Bidhan Sarani"),
    }
    sweep_market = [s for s in sweep if "Brabourne" in net.segs[s]["name"]
                    or "Gandhi" in net.segs[s]["name"]]
    out["sweep_market_road"] = sweep_market[0] if sweep_market else sweep[0]
    return out


# ── the watchlist sweep route ───────────────────────────────────────────────

#: Without registered sweep cameras the sweep runs this walk.
SWEEP_WALK = ("howrah_station", "howrah_bridge", "bbd_bag", "red_road", "esplanade_sn_banerjee")
#: Longest sweep the search accepts (metres).
SWEEP_MAX_M = 12000.0


def sweep_route(net: Network) -> list[int]:
    """One legal path through as many registered sweep cameras' roads
    (EM-CAM-nn) as it can, then the most stop-line cameras, then the
    shortest; the fixed walk when the network registers none."""
    import itertools

    cams = [c for c in net.doc.get("cameras") or []
            if str(c.get("camera_id", "")).startswith("EM-CAM-")]
    sweep = sorted({int(c["segment_id"]) for c in cams})
    stop = {int(c["segment_id"]) for c in net.doc.get("cameras") or []
            if c.get("junction_id") is not None and c.get("heading_deg") is not None}
    if not sweep:
        return net.walk(*SWEEP_WALK)
    best: tuple | None = None
    for k in range(len(sweep), 0, -1):
        for subset in itertools.combinations(sweep, k):
            for order in itertools.permutations(subset):
                for flips in itertools.product((0, 1), repeat=len(order)):
                    route: list[int] = []
                    ok = True
                    for sid, flip in zip(order, flips):
                        s = net.segs[sid]
                        if flip and s["oneway"]:
                            ok = False
                            break
                        a, b = (s["b"], s["a"]) if flip else (s["a"], s["b"])
                        if route:
                            at = net.exit_junction(route)[-1]
                            try:
                                route += net.shortest(at, a, set(route) | set(order))
                            except SystemExit:
                                ok = False
                                break
                        if sid in route:
                            ok = False
                            break
                        route.append(sid)
                        if legal(net, route):
                            ok = False
                            break
                    if not ok or len(set(route)) != len(route):
                        continue
                    length = sum(net.length_m(s) for s in route)
                    if length > SWEEP_MAX_M:
                        continue
                    score = (k, len(stop & set(route)), -length)
                    if best is None or score > best[0]:
                        best = (score, route)
        if best is not None:
            return best[1]
    return net.walk(*SWEEP_WALK)


def sweep_text(net: Network, route: list[int]) -> str:
    return "along " + road_names(net, route).replace(" > ", ", ") + "."


def sweep_places(net: Network, route: list[int]) -> list[str]:
    keys = [net.jid_to_key.get(j) for j in net.exit_junction(route)]
    return list(dict.fromkeys(k for k in keys if k and k in LANDMARK_IDS))


# ── the living city's sites and beats ───────────────────────────────────────

#: (kind, EN name, BN name, segment spec, place, detail EN, detail BN, festival)
#: A segment spec is (a, b): the road a legal drive from crossing a towards b
#: starts on; or ("near", landmark): the road nearest the landmark.
SITE_SPECS: list[tuple] = [
    # breakdowns on the arterials (lane loss until the tow)
    ("breakdown", "Howrah Bridge", "হাওড়া ব্রিজ", ("howrah_station", "howrah_bridge"),
     "howrah_bridge", "WBTC bus breakdown", "ডব্লিউবিটিসি বাস বিকল", None),
    ("breakdown", "Vidyasagar Setu", "বিদ্যাসাগর সেতু", ("nabanna", "vidyasagar_setu"),
     "vidyasagar_setu", "Truck breakdown", "ট্রাক বিকল", None),
    ("breakdown", "EM Bypass (Ruby–Science City)", "ই এম বাইপাস (রুবি–সায়েন্স সিটি)",
     ("ruby", "science_city"), "ruby", "Container truck breakdown", "কন্টেনার ট্রাক বিকল", None),
    ("breakdown", "EM Bypass (Chingrighata)", "ই এম বাইপাস (চিংড়িঘাটা)",
     ("chingrighata", "salt_lake_stadium"), "chingrighata", "Goods tempo breakdown",
     "মালবাহী টেম্পো বিকল", None),
    ("breakdown", "VIP Road (Lake Town–Kestopur)", "ভিআইপি রোড (লেক টাউন–কেষ্টপুর)",
     ("lake_town", "kestopur"), "kestopur", "App-cab breakdown", "অ্যাপ ক্যাব বিকল", None),
    ("breakdown", "Diamond Harbour Road (Majerhat bridge)",
     "ডায়মন্ড হারবার রোড (মাঝেরহাট সেতু)", ("majerhat", "taratala"), "majerhat",
     "Truck breakdown", "ট্রাক বিকল", None),
    ("breakdown", "AJC Bose Road (Mullickbazar)", "এজেসি বোস রোড (মল্লিকবাজার)",
     ("exide", "mullickbazar"), None, "Stalled car", "গাড়ি বিকল", None),
    ("breakdown", "Chittaranjan Avenue (Girish Park)", "চিত্তরঞ্জন অ্যাভিনিউ (গিরিশ পার্ক)",
     ("girish_park", "shyambazar"), None, "Private bus breakdown", "বেসরকারি বাস বিকল", None),
    ("breakdown", "Strand Road (Babughat)", "স্ট্র্যান্ড রোড (বাবুঘাট)",
     ("howrah_bridge", "babughat"), "babughat", "Truck breakdown", "ট্রাক বিকল", None),
    ("breakdown", "Salt Lake Bypass (Sector V)", "সল্টলেক বাইপাস (সেক্টর ফাইভ)",
     ("chingrighata", "sector_v"), "sector_v", "App-cab breakdown", "অ্যাপ ক্যাব বিকল", None),
    ("breakdown", "Biswa Bangla Sarani (New Town)", "বিশ্ব বাংলা সরণি (নিউ টাউন)",
     ("biswa_bangla_sarani", "chinar_park"), "biswa_bangla_sarani", "Stalled car",
     "গাড়ি বিকল", None),
    ("breakdown", "Bidhannagar Road (Ultadanga)", "বিধাননগর রোড (উল্টোডাঙা)",
     ("ultadanga", "shyambazar"), "ultadanga", "Tanker breakdown", "ট্যাঙ্কার বিকল", None),
    ("breakdown", "Maa Flyover", "মা উড়ালপুল", ("park_circus", "science_city"),
     "park_circus", "Stalled car", "গাড়ি বিকল", None),
    ("breakdown", "Grand Trunk Road (Howrah)", "জি টি রোড (হাওড়া)",
     ("nabanna", "howrah_station"), "howrah_station", "Private bus breakdown",
     "বেসরকারি বাস বিকল", None),
    # hawkers and markets
    ("market_spillover", "Gariahat (Rash Behari Avenue)", "গড়িয়াহাট (রাসবিহারী অ্যাভিনিউ)",
     ("deshapriya_park", "gariahat"), "gariahat", "", "", None),
    ("market_spillover", "Hatibagan (Bidhan Sarani)", "হাতিবাগান (বিধান সরণি)",
     ("shyambazar", "college_street"), "shyambazar", "", "", None),
    ("market_spillover", "Burrabazar (MG Road)", "বড়বাজার (মহাত্মা গান্ধী রোড)",
     ("central_avenue_mg_road", "howrah_bridge"), None, "", "", None),
    ("market_spillover", "Brabourne Road (Burrabazar)", "ব্রেবোর্ন রোড (বড়বাজার)",
     ("howrah_bridge", "bbd_bag"), "bbd_bag", "", "", None),
    ("market_spillover", "Esplanade (Lenin Sarani)", "এসপ্ল্যানেড (লেনিন সরণি)",
     ("esplanade", "moulali"), "esplanade", "", "", None),
    ("market_spillover", "College Street (MG Road)", "কলেজ স্ট্রিট (মহাত্মা গান্ধী রোড)",
     ("near", "college_square"), "college_square", "", "", None),
    ("market_spillover", "Sealdah (APC Road)", "শিয়ালদহ (আচার্য প্রফুল্লচন্দ্র রোড)",
     ("sealdah", "maniktala"), "sealdah", "", "", None),
    # school runs
    ("school_egress", "Syed Amir Ali Avenue", "সৈয়দ আমির আলি অ্যাভিনিউ",
     ("park_circus", "ballygunge"), "ballygunge", "", "", None),
    ("school_egress", "Hazra Road", "হাজরা রোড", ("hazra", "ballygunge"), "hazra", "", "",
     None),
    ("school_egress", "Ashutosh Mukherjee Road (Bhowanipore)",
     "আশুতোষ মুখার্জি রোড (ভবানীপুর)", ("exide", "hazra"), "hazra", "", "", None),
    ("school_egress", "Queensway – Cathedral Road", "কুইন্সওয়ে – ক্যাথিড্রাল রোড",
     ("near", "victoria_memorial"), "victoria_memorial", "", "", None),
    ("school_egress", "Diamond Harbour Road (Behala)", "ডায়মন্ড হারবার রোড (বেহালা)",
     ("taratala", "behala_chowrasta"), "behala_chowrasta", "", "", None),
    ("school_egress", "Salt Lake Bypass (Salt Lake)", "সল্টলেক বাইপাস (সল্টলেক)",
     ("chingrighata", "sector_v"), "sector_v", "", "", None),
    # office peaks into and out of BBD Bag–Esplanade and Sector V
    ("office_rush", "Howrah Bridge", "হাওড়া ব্রিজ", ("howrah_station", "howrah_bridge"),
     "howrah_bridge", "", "", None),
    ("office_rush", "Brabourne Road (BBD Bag)", "ব্রেবোর্ন রোড (বিবাদী বাগ)",
     ("howrah_bridge", "bbd_bag"), "bbd_bag", "", "", None),
    ("office_rush", "Old Court House Street (BBD Bag)", "ওল্ড কোর্ট হাউস স্ট্রিট (বিবাদী বাগ)",
     ("bbd_bag", "red_road"), "bbd_bag", "", "", None),
    ("office_rush", "Chittaranjan Avenue (Esplanade)", "চিত্তরঞ্জন অ্যাভিনিউ (এসপ্ল্যানেড)",
     ("esplanade", "central_avenue_mg_road"), "esplanade", "", "", None),
    ("office_rush", "Jawaharlal Nehru Road (Chowringhee)", "জওহরলাল নেহরু রোড (চৌরঙ্গি)",
     ("esplanade_sn_banerjee", "park_street"), "park_street", "", "", None),
    ("office_rush", "Vidyasagar Setu", "বিদ্যাসাগর সেতু", ("nabanna", "vidyasagar_setu"),
     "vidyasagar_setu", "", "", None),
    ("office_rush", "Salt Lake Bypass (to Sector V)", "সল্টলেক বাইপাস (সেক্টর ফাইভের পথে)",
     ("chingrighata", "sector_v"), "sector_v", "", "", None),
    ("office_rush", "EM Bypass (Science City)", "ই এম বাইপাস (সায়েন্স সিটি)",
     ("science_city", "chingrighata"), "science_city", "", "", None),
    # IT-park shift changes (Sector V, New Town)
    ("it_shift_change", "Sector V – New Town link", "সেক্টর ফাইভ – নিউ টাউন সংযোগ",
     ("sector_v", "biswa_bangla_sarani"), "sector_v", "", "", None),
    ("it_shift_change", "Biswa Bangla Sarani (New Town)", "বিশ্ব বাংলা সরণি (নিউ টাউন)",
     ("biswa_bangla_sarani", "chinar_park"), "biswa_bangla_sarani", "", "", None),
    ("it_shift_change", "Salt Lake Bypass (Sector V)", "সল্টলেক বাইপাস (সেক্টর ফাইভ)",
     ("chingrighata", "sector_v"), "sector_v", "", "", None),
    ("it_shift_change", "EM Bypass (Chingrighata)", "ই এম বাইপাস (চিংড়িঘাটা)",
     ("chingrighata", "salt_lake_stadium"), "chingrighata", "", "", None),
    # low-lying stretches that waterlog (MODELLED susceptibility)
    ("waterlogging", "Bidhan Sarani (Thanthania)", "বিধান সরণি (ঠনঠনিয়া)",
     ("college_street", "shyambazar"), "thanthania", "", "", None),
    ("waterlogging", "Bidhannagar Road (Ultadanga)", "বিধাননগর রোড (উল্টোডাঙা)",
     ("ultadanga", "shyambazar"), "ultadanga", "", "", None),
    ("waterlogging", "VIP Road (Ultadanga–Lake Town)", "ভিআইপি রোড (উল্টোডাঙা–লেক টাউন)",
     ("ultadanga", "lake_town"), "ultadanga", "", "", None),
    ("waterlogging", "MG Road (College Street)", "মহাত্মা গান্ধী রোড (কলেজ স্ট্রিট)",
     ("near", "college_square"), "college_square", "", "", None),
    ("waterlogging", "APC Road (Maniktala)", "আচার্য প্রফুল্লচন্দ্র রোড (মানিকতলা)",
     ("maniktala", "shyambazar"), None, "", "", None),
    ("waterlogging", "AJC Bose Road (Moulali)", "এজেসি বোস রোড (মৌলালি)",
     ("moulali", "sealdah"), "moulali", "", "", None),
    ("waterlogging", "Mother Teresa Sarani (Park Circus)", "মাদার টেরিজা সরণি (পার্ক সার্কাস)",
     ("mullickbazar", "park_circus"), "park_circus", "", "", None),
    ("waterlogging", "Diamond Harbour Road (Behala)", "ডায়মন্ড হারবার রোড (বেহালা)",
     ("taratala", "behala_chowrasta"), "behala_chowrasta", "", "", None),
    ("waterlogging", "Rash Behari Avenue (Gariahat)", "রাসবিহারী অ্যাভিনিউ (গড়িয়াহাট)",
     ("deshapriya_park", "gariahat"), "gariahat", "", "", None),
    ("waterlogging", "SP Mukherjee Road (Kalighat)", "শ্যামাপ্রসাদ মুখার্জি রোড (কালীঘাট)",
     ("rashbehari", "kalighat"), "kalighat", "", "", None),
    # Durga Puja nights around the pandals
    ("festival_crowd", "Bagbazar Street (Bagbazar Sarbojanin)",
     "বাগবাজার স্ট্রিট (বাগবাজার সর্বজনীন)", ("bagbazar", "shyambazar"), "bagbazar", "", "",
     "puja"),
    ("festival_crowd", "Strand Bank Road (Kumartuli Park)", "স্ট্র্যান্ড ব্যাঙ্ক রোড (কুমোরটুলি পার্ক)",
     ("howrah_bridge", "bagbazar"), "kumartuli", "", "", "puja"),
    ("festival_crowd", "MG Road (College Square)", "মহাত্মা গান্ধী রোড (কলেজ স্কোয়্যার)",
     ("near", "college_square"), "college_square", "", "", "puja"),
    ("festival_crowd", "Santosh Mitra Square", "সন্তোষ মিত্র স্কোয়্যার",
     ("near", "santosh_mitra_square"), "santosh_mitra_square", "", "", "puja"),
    ("festival_crowd", "Rash Behari Avenue (Deshapriya Park)",
     "রাসবিহারী অ্যাভিনিউ (দেশপ্রিয় পার্ক)", ("rashbehari", "deshapriya_park"),
     "deshapriya_park", "", "", "puja"),
    ("festival_crowd", "Rash Behari Avenue (Ekdalia Evergreen)",
     "রাসবিহারী অ্যাভিনিউ (একডালিয়া এভারগ্রিন)", ("deshapriya_park", "gariahat"),
     "ekdalia", "", "", "puja"),
    ("festival_crowd", "Bidhan Sarani (Hatibagan)", "বিধান সরণি (হাতিবাগান)",
     ("shyambazar", "college_street"), "shyambazar", "", "", "puja"),
    # Christmas to New Year evenings on Park Street
    ("festival_crowd", "Park Street", "পার্ক স্ট্রিট", ("park_street", "mullickbazar"),
     "park_street", "", "", "year_end"),
    ("festival_crowd", "Jawaharlal Nehru Road (Park Street)", "জওহরলাল নেহরু রোড (পার্ক স্ট্রিট)",
     ("esplanade_sn_banerjee", "park_street"), "park_street", "", "", "year_end"),
    ("festival_crowd", "Mother Teresa Sarani", "মাদার টেরিজা সরণি",
     ("mullickbazar", "park_circus"), "park_street", "", "", "year_end"),
]

_SITE_PREFIX = {"breakdown": "BD", "market_spillover": "MK", "school_egress": "SE",
                "office_rush": "OR", "it_shift_change": "IT", "waterlogging": "WL",
                "festival_crowd": "FC"}

#: The living city's emulated field units (connected chains, each one-way
#: driven its own way): (unit id, beat, walk through crossings).  The unit
#: id's prefix names the agency (event_emulator.city.unit_role): KTP-EM
#: Kolkata Traffic Police beats, KP-EM-PCR Kolkata Police patrol cars,
#: 108-EM-LC ambulance (108) standby circuits.  The first two beats ride at
#: every density; the rest join at EMULATOR_LIVING_DENSITY >= 2.  The beats
#: added after the first two use two-way roads only (a beat is driven back
#: and forth).  Beat names stay short: the oracle caps a unit label at 80
#: characters.
PATROL_SPECS = (
    ("KTP-EM-LC1", "Howrah Bridge–BBD Bag–Esplanade",
     ("howrah_station", "howrah_bridge", "bbd_bag", "red_road", "esplanade_sn_banerjee")),
    ("KTP-EM-LC2", "EM Bypass (Ruby–Salt Lake Stadium)",
     ("ruby", "science_city", "chingrighata", "salt_lake_stadium")),
    ("KTP-EM-LC3", "Vidyasagar Setu–Nabanna–GT Road",
     ("vidyasagar_setu", "nabanna", "howrah_station")),
    ("KTP-EM-LC4", "JL Nehru Road (Esplanade–Exide)",
     ("esplanade", "esplanade_sn_banerjee", "park_street", "exide")),
    ("KTP-EM-LC5", "APC Road (Sealdah–Shyambazar)",
     ("sealdah", "maniktala", "shyambazar")),
    ("KTP-EM-LC6", "AJC Bose Road (Exide–Sealdah)",
     ("exide", "mullickbazar", "moulali", "sealdah")),
    ("KTP-EM-LC7", "Hazra–Rash Behari Avenue–Gariahat",
     ("hazra", "rashbehari", "deshapriya_park", "gariahat")),
    ("KTP-EM-LC8", "CR Avenue (Central Avenue–Shyambazar)",
     ("central_avenue_mg_road", "girish_park", "shyambazar")),
    ("KTP-EM-LC9", "Salt Lake Bypass–Sector V–New Town",
     ("chingrighata", "sector_v", "biswa_bangla_sarani")),
    ("KTP-EM-LC10", "DH Road (Kidderpore–Behala)",
     ("kidderpore", "majerhat", "taratala", "behala_chowrasta")),
    ("KTP-EM-LC11", "VIP Road (Ultadanga–Baguiati)",
     ("ultadanga", "lake_town", "kestopur", "baguiati")),
    ("KP-EM-PCR1", "Strand Road (Howrah Bridge–Prinsep Ghat)",
     ("howrah_bridge", "babughat", "prinsep_ghat")),
    ("KP-EM-PCR2", "SP Mukherjee Road (Rashbehari–Tollygunge)",
     ("rashbehari", "kalighat", "tollygunge")),
    ("KP-EM-PCR3", "Park Street–Mother Teresa Sarani",
     ("park_street", "mullickbazar", "park_circus")),
    ("108-EM-LC1", "Ashutosh Mukherjee Rd–Hazra Rd",
     ("exide", "hazra", "ballygunge")),
    ("108-EM-LC2", "Maa Flyover to Science City",
     ("park_circus", "science_city")),
    ("108-EM-LC3", "Bijon Setu (Gariahat–Ruby)",
     ("gariahat", "ruby")),
    ("108-EM-LC4", "CR Avenue–College Street",
     ("esplanade", "central_avenue_mg_road", "college_street")),
)


def living_sites(net: Network) -> tuple[list[dict], list[tuple], list[int]]:
    """(sites, patrols, signalised junctions) on this network."""
    sites: list[dict] = []
    seen: set[str] = set()
    for kind, name, name_bn, spec, place, detail, detail_bn, festival in SITE_SPECS:
        if spec[0] == "near":
            sid = net.near(spec[1])
        else:
            sid = first_leg(net, spec[0], spec[1])
        s = net.segs[sid]
        site_id = f"{_SITE_PREFIX[kind]}-{sid}"
        if site_id in seen:
            raise SystemExit(f"ERROR: two {kind} sites on segment {sid}")
        seen.add(site_id)
        sites.append({"site_id": site_id, "kind": kind, "name": name, "name_bn": name_bn,
                      "segments": [sid], "junctions": sorted(j for j in (s["a"], s["b"])
                                                             if j is not None),
                      "detail": detail, "detail_bn": detail_bn, "place": place,
                      "festival": festival, "road": s["name"]})
    signalised = sorted(int(k) for k in (net.doc.get("signal_programs") or {}))
    for jid in signalised:
        legs = sorted(s["id"] for s in net.segs.values() if jid in (s["a"], s["b"]))
        name, name_bn = net.jname[jid]
        sites.append({"site_id": f"SF-J{jid}", "kind": "signal_fault", "name": name,
                      "name_bn": name_bn or name, "segments": legs, "junctions": [jid],
                      "detail": "", "detail_bn": "", "place": net.jid_to_key.get(jid)
                      if net.jid_to_key.get(jid) in LANDMARK_IDS else None,
                      "festival": None, "road": ""})
    patrols = [(uid, beat, net.walk(*walk)) for uid, beat, walk in PATROL_SPECS]
    return sites, patrols, signalised


LANDMARK_IDS: set[str] = set()
if LANDMARKS.is_file():
    LANDMARK_IDS = {m["id"] for m in json.loads(LANDMARKS.read_text(encoding="utf-8"))
                    ["landmarks"]}


def network_module(net: Network, sites: list[dict], patrols: list[tuple],
                   signalised: list[int], segments: dict[str, int], source: str) -> str:
    """The text of src/event_emulator/kolkata_network.py."""
    lines = [
        '"""The Kolkata network ids the emulator names — GENERATED, do not edit.',
        "",
        "Written by ``tools/kolkata_library.py`` from the city road network",
        f"(``{source}``): the living city's sites (EN + Bengali names, the",
        "landmarks.json place each sits at), its emulated field units' beats,",
        "the signalised junctions (those with a signal program) and the segments",
        "the profiles' own causes sit on.  Re-run the tool when the network is",
        "regenerated; the emulator's network check (ambient.py) and its tests",
        "(tests/data/kolkata_network_slim.json) catch any drift.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "#: (site_id, kind, EN name, BN name, segments, junctions, detail EN,",
        "#:  detail BN, landmarks.json place, festival)",
        "SITE_ROWS: tuple[tuple, ...] = (",
    ]
    for s in sites:
        lines.append(
            f"    ({s['site_id']!r}, {s['kind']!r}, {s['name']!r}, {s['name_bn']!r}, "
            f"{tuple(s['segments'])!r}, {tuple(s['junctions'])!r}, {s['detail']!r}, "
            f"{s['detail_bn']!r}, {s['place']!r}, {s['festival']!r}),")
    lines += [")", "", "#: (unit id, beat, connected segment chain)", "PATROL_ROWS: tuple[tuple, ...] = ("]
    for uid, beat, route in patrols:
        lines.append(f"    ({uid!r}, {beat!r}, {tuple(route)!r}),")
    lines += [")", "", "#: Junctions with a signal program (corridor.signal_programs).",
              "SIGNALISED_JUNCTIONS: frozenset[int] = frozenset({"
              + ", ".join(str(j) for j in sorted(signalised)) + "})", "",
              "#: The segments the profiles' own causes sit on, by role.",
              "PROFILE_SEGMENTS: dict[str, int] = {"]
    for k in sorted(segments):
        lines.append(f"    {k!r}: {segments[k]},  # {net.segs[segments[k]]['name']}")
    lines += ["}", ""]
    return "\n".join(lines)


# ── checks + output ─────────────────────────────────────────────────────────


def legal(net: Network, route: list[int]) -> list[str]:
    """Why ``route`` is not a legal directed path; [] when it is one."""
    if not route:
        return ["empty route"]
    if len(set(route)) != len(route):
        return ["a segment twice"]
    for sid in route:
        if sid not in net.segs:
            return [f"unknown segment {sid}"]

    def ends(sid: int) -> list[tuple[int, int]]:
        s = net.segs[sid]
        return [(s["a"], s["b"])] + ([] if s["oneway"] else [(s["b"], s["a"])])

    # every orientation of the first segment that can start a legal drive
    frontier = {e[1] for e in ends(route[0])}
    for prev, sid in zip(route, route[1:]):
        nxt = {e[1] for e in ends(sid) if e[0] in frontier}
        if not nxt:
            return [f"{prev} -> {sid} is not a legal move"]
        frontier = nxt
    return []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--network", required=True, type=Path)
    ap.add_argument("--write", action="store_true",
                    help="write use_case_library.json, kolkata_network.py and the slim snapshot")
    args = ap.parse_args(argv)
    net = Network(json.loads(args.network.read_text(encoding="utf-8")))
    lib = build(net)
    segments = profile_segments(net, lib)
    sites, patrols, signalised = living_sites(net)
    bad = False
    for uc in lib:
        cfg = uc["scenarioConfig"]
        problems = legal(net, cfg["route_segment_ids"])
        bad |= bool(problems)
        print(f"{'OK ' if not problems else 'BAD'} {uc['id']:32s} {cfg['route_segment_ids']}"
              f"  {road_names(net, cfg['route_segment_ids'])}  {problems or ''}")
    for uid, beat, route in patrols:
        problems = legal(net, route)
        bad |= bool(problems)
        print(f"{'OK ' if not problems else 'BAD'} patrol {uid} {beat}: {route}")
    for s in sites:
        print(f"    site {s['site_id']:10s} {s['kind']:16s} {s['name']:42s} -> {s['road']}")
    print("profile segments:", {k: (v, net.segs[v]["name"]) for k, v in segments.items()})
    if bad:
        print("ERROR: a route is not a legal path", file=sys.stderr)
        return 1
    if args.write:
        LIBRARY.write_text(json.dumps(lib, indent=1, ensure_ascii=False) + "\n",
                           encoding="utf-8")
        mod = HERE.parent / "src" / "event_emulator" / "kolkata_network.py"
        parts = args.network.resolve().parts
        source = ("/".join(parts[parts.index("cities"):]) if "cities" in parts
                  else args.network.name)
        mod.write_text(network_module(net, sites, patrols, signalised, segments, source),
                       encoding="utf-8")
        slim = HERE.parent / "tests" / "data" / "kolkata_network_slim.json"
        slim.parent.mkdir(parents=True, exist_ok=True)
        slim.write_text(json.dumps(net.slim(), indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8")
        print(f"wrote {LIBRARY.name}, {mod.name}, {slim.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
