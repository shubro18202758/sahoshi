"""Library + profiles + tape tests: verbatim consumption, closed cause
vocabulary, byte-level determinism (same spec+seed+t0+run → identical tape)
and the cause model (route-filtered soft saturation, ambulance projection
only inside green-corridor windows, the scenario's own time of day)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

import re

from event_emulator.city import PLACES
from event_emulator.library import KNOWN_EVENT_TYPES, load_library
from event_emulator.profiles import EVENT_KINDS, PROFILES, profile_for
from event_emulator.spec import EmulationSpec, ResolvedRun
from kolkata import SEGMENTS, legal_path
from event_emulator.tape import (
    AGENCY_CADENCE_SEC,
    CAUSE_KINDS,
    SATURATION_IDX,
    TAPE_VERSION,
    build_tape,
    congestion_at,
    movement_uuid,
)

EXPECTED_IDS = (
    "vvip_convoy_base",
    "durga_puja_north",
    "cloudburst_high_tide",
    "cyclone_landfall_recovery",
    "eden_gardens_egress",
    "howrah_surge_bridge_breakdown",
    "red_road_parade",
    "gangasagar_transit",
    "kolkata_marathon",
    "park_street_new_year",
    "em_bypass_accident_ambulance",
    "metro_work_zone",
    # watchlist-anpr addition (010, contract C2):
    "watchlist_anpr_sweep",
    # the city-feeds scenarios (fire, river release, festival air, heat, squall):
    "burrabazar_market_fire",
    "dvc_release_howrah_waterlogging",
    "kali_puja_air_quality",
    "pre_monsoon_heatwave",
    "norwester_squall_treefall",
)

# values pinned from the Kolkata library (verbatim consumption check).
#: Every route a legal path on the Kolkata network (tools/kolkata_library.py
#: writes the library; re-pin when the network is regenerated).
PINNED = {
    "vvip_convoy_base": dict(seed=20261102, vvip="Z+",
        route=[1003, 1028, 1029, 1036, 1037, 1038, 1039, 1040, 1041, 1042, 1043, 1065]),
    "durga_puja_north": dict(seed=202509301, vvip="X",
        route=[1061, 1060, 1058]),
    "cloudburst_high_tide": dict(seed=20260818, vvip="X",
        route=[1039, 1062, 1058]),
    "cyclone_landfall_recovery": dict(seed=20260527, vvip="X",
        route=[1016, 1017, 1018, 1019, 1020]),
    "eden_gardens_egress": dict(seed=20260418, vvip="X",
        route=[1012, 1004, 1001]),
    "howrah_surge_bridge_breakdown": dict(seed=20261104, vvip="X",
        route=[1051, 1054, 1001]),
    "red_road_parade": dict(seed=20270126, vvip="Z",
        route=[1016, 1011, 1013]),
    "gangasagar_transit": dict(seed=20270112, vvip="X",
        route=[1001, 1004, 1005, 1006, 1047, 1048]),
    "kolkata_marathon": dict(seed=20261220, vvip="X",
        route=[1012, 1013, 1014, 1006, 1005]),
    "park_street_new_year": dict(seed=20261231, vvip="X",
        route=[1017, 1026, 1027]),
    "em_bypass_accident_ambulance": dict(seed=20261106, vvip="X",
        route=[1035, 1029, 1027, 1023]),
    "metro_work_zone": dict(seed=20250814, vvip="X",
        route=[1050, 1049, 1048]),
    "watchlist_anpr_sweep": dict(seed=20261105, vvip="X",
        route=[1001, 1004, 1012, 1010, 1016, 1051, 1054, 1008]),
    "burrabazar_market_fire": dict(seed=20261118, vvip="X",
        route=[1017, 1016, 1051, 1054, 1008]),
    "dvc_release_howrah_waterlogging": dict(seed=20270914, vvip="X",
        route=[1003, 1007, 1006, 1005, 1004, 1001]),
    "kali_puja_air_quality": dict(seed=20261108, vvip="X",
        route=[1022, 1021, 1020, 1019]),
    "pre_monsoon_heatwave": dict(seed=20270427, vvip="X",
        route=[1003, 1028, 1029, 1036, 1037, 1038]),
    "norwester_squall_treefall": dict(seed=20270506, vvip="X",
        route=[1038, 1037, 1036, 1035]),
}

T0 = datetime(2026, 10, 12, 6, 0, 0, tzinfo=timezone.utc)
FLAGSHIP = "durga_puja_north"


def _tape_for(use_case_id: str, seed: int | None = None, tick_sec: float = 5.0,
              t0: datetime = T0, run_id: int | None = None):
    lib = load_library()
    uc = lib[use_case_id]
    spec = EmulationSpec(use_case_id=use_case_id, seed=seed, t0_anchor=t0, tick_sec=tick_sec)
    run = ResolvedRun.resolve(spec, uc)
    return build_tape(run, uc, profile_for(use_case_id), run_id=run_id), uc


def _docs(tape):
    return sorted((f for f in tape.frames if f.kind == "inputs_doc"), key=lambda f: f.t_sec)


class TestLibraryVerbatim:
    def test_all_present(self):
        lib = load_library()
        assert set(lib) == set(EXPECTED_IDS)

    def test_pinned_values(self):
        lib = load_library()
        for uid, pin in PINNED.items():
            cfg = lib[uid].config
            assert cfg["seed"] == pin["seed"], uid
            assert cfg["vvip_class"] == pin["vvip"], uid
            assert cfg["route_segment_ids"] == pin["route"], uid

    def test_forced_events_use_known_types(self):
        lib = load_library()
        for uc in lib.values():
            for fe in uc.config["forced_events"]:
                assert fe["type"] in KNOWN_EVENT_TYPES

    def test_puja_overrides_verbatim(self):
        # food stalls up, goods vehicles off the pandal belts (fewer heavy
        # breakdowns), the ambulance knob explicit
        lib = load_library()
        assert lib["durga_puja_north"].config["event_overrides"] == {
            "market": 2.0, "breakdown": 0.6, "ambulance": 1.0}

    def test_cloudburst_weather_verbatim(self):
        lib = load_library()
        assert lib["cloudburst_high_tide"].config["weather"] == {
            "monsoon": True, "rain_intensity_mm_h": 100.0
        }

    def test_every_route_is_a_legal_path_on_the_kolkata_network(self):
        for uid, uc in load_library().items():
            assert legal_path(uc.config["route_segment_ids"]), uid

    def test_every_cause_sits_on_a_kolkata_road(self):
        for uid, uc in load_library().items():
            for fe in uc.config["forced_events"]:
                assert fe["segment_id"] in SEGMENTS, (uid, fe["label"])

    def test_every_scenario_is_labelled_and_named_in_three_languages(self):
        bengali = re.compile(r"[\u0980-\u09FF]")
        devanagari = re.compile(r"[\u0900-\u097F]")
        for uid, uc in load_library().items():
            cfg = uc.config
            assert cfg["label"] == "SIMULATED", uid
            assert bengali.search(cfg["name_bn"]) and not devanagari.search(cfg["name_bn"]), uid
            assert devanagari.search(cfg["name_hi"]), uid
            assert cfg["places"] and set(cfg["places"]) <= set(PLACES), uid
            # the honest label leads every description
            assert cfg["description"].split(".")[0].split()[0] in (
                "SIMULATED", "FLAGSHIP", "EMULATED"), uid

    def test_config_axes_agree_with_the_profiles(self):
        for uid, uc in load_library().items():
            prof = PROFILES[uid]
            assert uc.config["event_kind"] == prof.event_kind, uid
            assert uc.config["crowd_class"] == prof.crowd_class, uid

    def test_the_required_kolkata_scenarios_are_there(self):
        lib = load_library()
        base = lib["vvip_convoy_base"].config
        ends = [SEGMENTS[s] for s in (base["route_segment_ids"][0],
                                      base["route_segment_ids"][-1])]
        assert {"nabanna", "airport"} <= set(base["places"])
        assert "Vidyasagar Setu" in ends[0]["road_name"]
        assert "Airport" in ends[-1]["road_name"]          # to the terminal forecourt
        assert any("VIP Road" in SEGMENTS[s]["road_name"] for s in base["route_segment_ids"])
        assert any("Bypass" in SEGMENTS[s]["road_name"] for s in base["route_segment_ids"])
        puja = lib["durga_puja_north"].config
        assert {"bagbazar", "kumartuli", "deshapriya_park", "ekdalia"} <= set(puja["places"])
        assert "goods_vehicle_restriction" in puja["expected_features"]
        assert any(fe["type"] == "emergency_vehicle" for fe in puja["forced_events"])
        cloud = lib["cloudburst_high_tide"].config
        assert "live_wire_hazard_proposal" in cloud["expected_features"]
        assert "PROPOSE" in cloud["description"] and "approves or rejects" in cloud["description"]
        assert sum(fe["type"] == "waterlogging" for fe in cloud["forced_events"]) >= 3
        assert "staged_reopening" in lib["cyclone_landfall_recovery"].config["expected_features"]
        assert "eden_gardens" in lib["eden_gardens_egress"].config["places"]
        howrah = lib["howrah_surge_bridge_breakdown"].config
        assert any(fe["type"] == "vehicle_breakdown"
                   and "Howrah Bridge" in SEGMENTS[fe["segment_id"]]["road_name"]
                   for fe in howrah["forced_events"])
        assert "red_road" in lib["red_road_parade"].config["places"]
        assert "babughat" in lib["gangasagar_transit"].config["places"]
        assert lib["metro_work_zone"].config["event_kind"] == "work_zone"
        assert lib["kolkata_marathon"].config["vvip_class"] == "X"
        assert "park_street" in lib["park_street_new_year"].config["places"]
        crash = lib["em_bypass_accident_ambulance"].config
        assert "Bypass" in SEGMENTS[crash["route_segment_ids"][0]]["road_name"]
        assert sum(fe["type"] == "emergency_vehicle" for fe in crash["forced_events"]) >= 2

    def test_the_city_feeds_scenarios_are_there(self):
        lib = load_library()
        road = lambda sid: SEGMENTS[sid]["road_name"]  # noqa: E731
        # the fire: tender windows from both stations, then an ambulance (108)
        fire = lib["burrabazar_market_fire"].config
        evs = [fe for fe in fire["forced_events"] if fe["type"] == "emergency_vehicle"]
        assert sum(fe["label"].startswith("fire tender") for fe in evs) == 6
        assert any(fe["label"].startswith("ambulance (108)") for fe in evs)
        assert {"Mahatma Gandhi Road", "Brabourne Road"} <= {
            road(fe["segment_id"]) for fe in fire["forced_events"]
            if fe["type"] == "vehicle_breakdown"}
        assert "approves or rejects" in fire["description"]
        # the river release: GT Road under water, the diversion crosses twice
        # and never uses it; the release figure is a premise, not a number
        dvc = lib["dvc_release_howrah_waterlogging"].config
        gt = {fe["segment_id"] for fe in dvc["forced_events"] if fe["type"] == "waterlogging"
              and "Grand Trunk" in road(fe["segment_id"])}
        assert gt and not gt & set(dvc["route_segment_ids"])
        roads = [road(s) for s in dvc["route_segment_ids"]]
        assert "Vidyasagar Setu" in roads[0] and "Howrah Bridge" in roads[-1]
        assert "SIMULATED input" in dvc["description"]
        assert "cusec" not in dvc["description"].lower()
        # Kali Puja: readings banded, never quoted; breathing-difficulty windows
        kali = lib["kali_puja_air_quality"].config
        assert "SIMULATED, not measurements" in kali["description"]
        assert not re.search(r"\d\s*(µg|ug|AQI)", kali["description"])
        assert kali["event_overrides"]["ambulance"] > 1
        assert sum(fe["type"] == "emergency_vehicle" for fe in kali["forced_events"]) == 4
        assert "kalighat" in kali["places"]
        # the heatwave: no weather key for heat, only modelled causes
        heat = lib["pre_monsoon_heatwave"].config
        assert heat["weather"] == {} and PROFILES["pre_monsoon_heatwave"].weather_code is None
        assert sum(fe["type"] == "vehicle_breakdown" for fe in heat["forced_events"]) == 4
        assert set(fe["segment_id"] for fe in heat["forced_events"]) <= set(
            heat["route_segment_ids"])
        # the Nor'wester: STORM from t0, the wire is a PROPOSAL, staged reopening
        squall = lib["norwester_squall_treefall"].config
        assert PROFILES["norwester_squall_treefall"].weather_code == "STORM"
        assert {"live_wire_hazard_proposal", "staged_reopening"} <= set(
            squall["expected_features"])
        assert "PROPOSE" in squall["description"]
        assert squall["closure_policy"]["closure_type"] == "partial_closure"

    def test_no_person_is_named_or_tracked(self):
        # events are about places: no protectee, no casualty, no officer by name
        for uid, uc in load_library().items():
            text = uc.config["description"].lower()
            for word in ("chief minister", "governor", "minister", "cm ", "patient's name",
                         "face", "person's"):
                assert word not in text, (uid, word)


class TestProfiles:
    def test_every_use_case_has_a_profile(self):
        assert set(PROFILES) == set(EXPECTED_IDS)

    def test_event_kinds_are_the_archetypes(self):
        for p in PROFILES.values():
            assert p.event_kind in EVENT_KINDS

    def test_crowd_waypoints_in_range(self):
        for p in PROFILES.values():
            for _t, v in p.crowd_waypoints:
                assert 0.0 <= v <= 1.0

    def test_extra_event_labels_name_the_real_roads(self):
        # A label names the road its segment IS on the Kolkata network.
        roads = {"EM Bypass": "Eastern Metropolitan Bypass",
                 "Jawaharlal Nehru Road": "Jawaharlal Nehru Road",
                 "Bidhan Sarani": "Bidhan Sarani",
                 "Ultadanga": "Bidhannagar"}
        lib = load_library()
        for uid, p in PROFILES.items():
            for e in p.extra_events:
                road = SEGMENTS[e["segment_id"]]["road_name"]
                for token, name in roads.items():
                    if token in e["label"]:
                        assert name in road, (uid, e["segment_id"], e["label"], road)
        # the base case's planted breakdown and the sweep's market spill sit
        # ON their routes
        base = PROFILES["vvip_convoy_base"].extra_events[0]["segment_id"]
        assert base in lib["vvip_convoy_base"].config["route_segment_ids"]
        [spill] = PROFILES["watchlist_anpr_sweep"].extra_events
        assert spill["segment_id"] in lib["watchlist_anpr_sweep"].config["route_segment_ids"]


class TestTapeDeterminism:
    def test_same_spec_seed_t0_identical_bytes(self):
        a, _ = _tape_for("howrah_surge_bridge_breakdown", run_id=3)
        b, _ = _tape_for("howrah_surge_bridge_breakdown", run_id=3)
        assert a.to_json() == b.to_json()

    def test_different_seed_different_tape(self):
        a, _ = _tape_for("gangasagar_transit", seed=1)
        b, _ = _tape_for("gangasagar_transit", seed=2)
        assert a.to_json() != b.to_json()

    def test_seed_defaults_to_config_seed(self):
        tape, uc = _tape_for("vvip_convoy_base")
        assert tape.seed == uc.config["seed"]

    def test_all_build(self):
        for uid in EXPECTED_IDS:
            tape, _ = _tape_for(uid, tick_sec=30.0)  # coarse for speed
            assert tape.frames, uid

    def test_cause_vocabulary_is_closed(self):
        tape, _ = _tape_for("eden_gardens_egress")
        kinds = {f.kind for f in tape.frames}
        assert kinds <= set(CAUSE_KINDS)
        assert "emergency_request" not in kinds  # deleted primitive (C4)

    def test_tape_carries_version_and_run(self):
        import json

        tape, _ = _tape_for("cyclone_landfall_recovery", tick_sec=60.0, run_id=12)
        doc = json.loads(tape.to_json())
        assert doc["tape_version"] == TAPE_VERSION
        assert doc["run_id"] == 12


class TestRunIdentity:
    def test_live_runs_are_run_scoped(self):
        a, uc = _tape_for("kolkata_marathon", run_id=5)
        b, _ = _tape_for("kolkata_marathon", run_id=6)
        seed = uc.config["seed"]
        assert a.movement_id == movement_uuid("kolkata_marathon", seed, 5)
        assert a.movement_id != b.movement_id

    def test_unledgered_keeps_runless_identity(self):
        assert movement_uuid("howrah_surge_bridge_breakdown", 42) == \
            movement_uuid("howrah_surge_bridge_breakdown", 42)
        assert movement_uuid("howrah_surge_bridge_breakdown", 42) != \
            movement_uuid("howrah_surge_bridge_breakdown", 43)
        assert movement_uuid("howrah_surge_bridge_breakdown", 42) != \
            movement_uuid("howrah_surge_bridge_breakdown", 42, 1)


class TestCauseModel:
    def test_ambulance_projection_zero_outside_ev_windows(self):
        tape, uc = _tape_for(FLAGSHIP, tick_sec=10.0)
        windows = [
            (float(e["start_sec"]), float(e["start_sec"]) + float(e["duration_sec"]))
            for e in uc.config["forced_events"] if e["type"] == "emergency_vehicle"
        ]
        prof = profile_for(FLAGSHIP)
        inside = outside = 0
        for f in _docs(tape):
            proj = f.payload["ambulance_delay_projection_sec"]
            if any(a <= f.t_sec < b for a, b in windows):
                inside += 1
                assert prof.ambulance_cleared_sec <= proj <= prof.ambulance_base_sec
            else:
                outside += 1
                assert proj == 0.0, f.t_sec
        assert inside and outside

    def test_ambulance_projection_decays_during_ev_window(self):
        tape, _ = _tape_for("eden_gardens_egress", tick_sec=60.0)
        during = [d.payload for d in _docs(tape) if 360 <= d.t_sec <= 1440]
        assert during
        assert during[0]["ambulance_delay_projection_sec"] > \
            during[-1]["ambulance_delay_projection_sec"]
        assert all(15.0 <= p["ambulance_delay_projection_sec"] <= 120.0 for p in during)

    def test_flagship_saturation_bound(self):
        tape, _ = _tape_for(FLAGSHIP, tick_sec=5.0)
        docs = [f.payload for f in _docs(tape)]
        saturated = sum(1 for d in docs if d["predicted_congestion_idx"] >= SATURATION_IDX)
        assert saturated / len(docs) <= 0.20

    @pytest.mark.parametrize("uid", EXPECTED_IDS)
    def test_no_use_case_pins_at_one(self, uid):
        tape, _ = _tape_for(uid, tick_sec=30.0)
        docs = [f.payload for f in _docs(tape)]
        pinned = sum(1 for d in docs if d["predicted_congestion_idx"] >= 0.999)
        assert pinned / len(docs) <= 0.20, uid

    def test_off_route_causes_do_not_load_the_route(self):
        on = [{"type": "rally_spillover", "segment_id": 1005, "start_sec": 0,
               "duration_sec": 100, "extra_demand_veh_h": 900}]
        off = [{**on[0], "segment_id": 1012}]
        route = {1005, 1015}
        assert congestion_at(0.5, off, route, 10.0) == pytest.approx(0.5)
        assert congestion_at(0.5, on, route, 10.0) == pytest.approx(1 - 0.5 * 0.7)

    def test_stacked_causes_combine_softly(self):
        causes = [{"type": "rally_spillover", "segment_id": 1, "start_sec": 0,
                   "duration_sec": 100, "extra_demand_veh_h": 1500}] * 4
        val = congestion_at(0.6, causes, {1}, 1.0)
        assert val == pytest.approx(1 - 0.4 * (0.65 ** 4))
        assert val < 1.0

    def test_time_of_day_comes_from_departure(self):
        # the same scenario injected at two different wall times builds the
        # identical cause stream: its clock is its own departure_time
        a, _ = _tape_for(FLAGSHIP, tick_sec=60.0, t0=T0)
        b, _ = _tape_for(FLAGSHIP, tick_sec=60.0,
                         t0=datetime(2026, 10, 12, 17, 30, tzinfo=timezone.utc))
        assert [f.payload for f in _docs(a)] == [f.payload for f in _docs(b)]


class TestTapeContent:
    def test_inputs_docs_match_engine_reader_shape(self):
        tape, _ = _tape_for("kolkata_marathon", tick_sec=60.0)
        docs = [f.payload for f in tape.frames if f.kind == "inputs_doc"]
        assert docs
        for doc in docs:
            for key in (
                "predicted_congestion_idx", "weather_severity", "crowd_score",
                "anomaly_active", "event_active", "last_gps_age_sec",
                "ambulance_delay_projection_sec",
            ):
                assert key in doc
            assert 0.0 <= doc["predicted_congestion_idx"] <= 1.0
            assert 0.0 <= doc["weather_severity"] <= 1.0
            assert 0.0 <= doc["crowd_score"] <= 1.0
            assert isinstance(doc["anomaly_active"], bool)
            assert isinstance(doc["event_active"], bool)

    def test_config_forced_events_verbatim_in_tape(self):
        tape, uc = _tape_for("cloudburst_high_tide")
        taped = [f.payload for f in tape.frames if f.kind == "scheduled_event"]
        for fe in uc.config["forced_events"]:
            match = [p for p in taped if p.get("label") == fe["label"]]
            assert match, f"missing forced event {fe['label']}"
            m = match[0]
            assert m["type"] == fe["type"]
            assert m["segment_id"] == fe["segment_id"]
            assert m["start_sec"] == fe["start_sec"]
            assert m["duration_sec"] == fe["duration_sec"]
            assert m["severity"] == fe["severity"]

    def test_emergency_vehicle_causes_present(self):
        for uid in ("eden_gardens_egress", "cloudburst_high_tide", "durga_puja_north",
                    "em_bypass_accident_ambulance"):
            tape, _ = _tape_for(uid, tick_sec=30.0)
            evs = [
                f.payload for f in tape.frames
                if f.kind == "scheduled_event" and f.payload["type"] == "emergency_vehicle"
            ]
            assert evs, uid
            assert all(e["severity"] > 0 for e in evs)

    def test_base_case_planted_breakdown(self):
        tape, _ = _tape_for("vvip_convoy_base")
        bds = [
            f.payload for f in tape.frames
            if f.kind == "scheduled_event" and f.payload["type"] == "vehicle_breakdown"
        ]
        assert len(bds) == 1  # one planted breakdown (contract)

    def test_event_config_carries_sixth_multiplier(self):
        tape, _ = _tape_for("eden_gardens_egress")
        ec = next(f.payload for f in tape.frames if f.kind == "event_config")
        assert "ambulance_rate_multiplier" in ec
        assert ec["ambulance_rate_multiplier"] > 1.0  # EVs scheduled → rate up
        assert ec["event_overrides"] == {}  # Eden Gardens config verbatim

    def test_cloudburst_weather_ramp_reaches_steady(self):
        tape, _ = _tape_for("cloudburst_high_tide", tick_sec=60.0)
        docs = [f.payload for f in tape.frames if f.kind == "inputs_doc"]
        assert docs[-1]["weather_severity"] > 0.5
        assert docs[-1].get("weather") in ("RAIN", "STORM")

    def test_event_row_lifecycle(self):
        tape, _ = _tape_for("cyclone_landfall_recovery", tick_sec=60.0)
        rows = [f for f in tape.frames if f.kind == "event_row"]
        actions = [r.payload["action"] for r in rows]
        assert actions[0] == "create"
        assert actions[-1] == "complete"
        horizon = load_library()["cyclone_landfall_recovery"].horizon_sec
        assert rows[-1].t_sec == pytest.approx(horizon)

    def test_agency_units_refresh_inside_the_c_a_ttl(self):
        tape, _ = _tape_for("watchlist_anpr_sweep", tick_sec=60.0)
        by_unit: dict[str, list[float]] = {}
        for f in tape.frames:
            if f.kind == "agency_unit":
                by_unit.setdefault(f.payload["unit_id"], []).append(f.t_sec)
        assert by_unit
        assert AGENCY_CADENCE_SEC <= 25.0
        for unit, ts in by_unit.items():
            gaps = [b - a for a, b in zip(ts, ts[1:])]
            assert max(gaps) <= 25.0, unit

    def test_frames_ordered_and_numbered(self):
        tape, _ = _tape_for("gangasagar_transit", tick_sec=60.0)
        ts = [f.t_sec for f in tape.frames]
        assert ts == sorted(ts)
        assert [f.frame for f in tape.frames] == list(range(len(tape.frames)))

    def test_tape_roundtrip(self):
        import json

        tape, _ = _tape_for("red_road_parade", tick_sec=60.0, run_id=9)
        again = type(tape).from_dict(json.loads(tape.to_json()))
        assert again.to_json() == tape.to_json()
        assert again.run_id == 9
