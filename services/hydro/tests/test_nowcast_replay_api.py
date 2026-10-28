import asyncio
import json
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

from conftest import NOW, make_hydro
from hydro.api import create_app
from hydro.config import Settings
from hydro.replay import IMD_ALIPORE_3H, REPORTED, imd_alipore_series, replay

DATA = Path(__file__).resolve().parents[1] / "src" / "hydro" / "data"


def test_dry_nowcast_is_all_class_0_with_labelled_drivers(hydro_dry):
    nc = asyncio.run(hydro_dry.nowcast(now=NOW))
    assert nc["counts_by_class"]["0"] == len(hydro_dry.net.segments) and nc["flagged"] == []
    assert nc["labels"] == {"rain": "LIVE", "tide": "MODELLED (approximate)", "susceptibility": "MODELLED",
                            "pumps": "EMULATED", "risk": "MODELLED"}
    d = nc["segments"][0]["drivers"]
    assert d["rain"]["label"] == "LIVE" and d["tide"]["label"].startswith("MODELLED")
    assert d["susceptibility"]["label"] == "MODELLED" and d["pumps"]["label"] == "EMULATED"
    assert [p for p in nc["proposals"]] == []


def test_storm_flags_segments_with_lead_times_and_proposals(hydro_storm):
    nc = asyncio.run(hydro_storm.nowcast(now=NOW))
    segs = {s["segment_id"]: s for s in nc["segments"]}
    assert len(nc["flagged"]) > 10
    for sid in nc["flagged"]:
        s = segs[sid]
        assert s["risk_class"] >= 2 and not s["elevated"]
        assert s["expected_depth_band"] in ("10–30 cm", "> 30 cm")
        assert 0 <= s["lead_time_min"] <= 120
    for sid, s in segs.items():
        if s["elevated"]:
            assert s["risk_class"] == 0
    kinds = [p["kind"] for p in nc["proposals"]]
    n = len(nc["flagged"])
    assert kinds.count("waterlogging_reroute") == n and kinds.count("live_wire_hazard") == n
    assert kinds.count("ambulance_window") == n and kinds.count("public_advisory_draft") == 1
    for p in nc["proposals"]:
        assert p["state"] == "proposed" and p["recommendation"]["decision"] == "await_officer"
        assert p["human_gate"]["officer"] is None and p["human_gate"]["required_role"] == "duty_officer"
        assert all(a["requires_officer"] for a in p["actions"])
    wire = next(p for p in nc["proposals"] if p["kind"] == "live_wire_hazard")
    assert wire["for_officer_approval"] and wire["actions"][0]["params"]["to_agency"] == "power"
    adv = next(p for p in nc["proposals"] if p["kind"] == "public_advisory_draft")
    assert "জল জমার আশঙ্কা" in adv["text"]["bn"] and "waterlogging" in adv["text"]["en"]
    assert "112" in adv["text"]["bn"] and "(108)" in adv["text"]["en"]
    assert any("ঀ" <= ch <= "৿" for ch in adv["text"]["bn"])


def test_imd_series_preserves_observed_totals():
    from datetime import UTC, datetime, timedelta

    start = datetime(2025, 9, 22, 12, 30, tzinfo=UTC) + timedelta(minutes=15)  # 18:15 IST + 15 min grid
    s = imd_alipore_series(start, 80)
    assert abs(np.sum(s) * 0.25 - sum(x[2] for x in IMD_ALIPORE_3H)) < 1e-6
    # the 03:00–04:00 IST hour carries the reported 98 mm
    i0 = int(((datetime(2025, 9, 22, 21, 30, tzinfo=UTC) - start).total_seconds()) // 900) + 1
    assert abs(np.sum(s[i0:i0 + 4]) * 0.25 - 98.0) < 1e-6


def test_replay_two_runs_and_honest_check():
    hy = make_hydro(0.0)
    rp = asyncio.run(replay(hy, "2025-09-23"))
    arc, gauge = rp["runs"]["open_meteo_archive"], rp["runs"]["imd_gauge_anchored"]
    # the mocked archive carries 1 mm/h: nothing floods, and the finding says why
    assert arc["flagged_segments"] == 0 and "finding" in arc
    assert gauge["flagged_segments"] > 30 and gauge["reported_check"]["hit_rate"] >= 0.8
    assert gauge["earliest_flag_ist"].startswith("2025-09-23 0")
    assert rp["official"]["alipore_24h_mm"] == 251.4 and rp["tide"]["label"].startswith("MODELLED")
    assert len(gauge["reported_check"]["items"]) == len(REPORTED)
    for it in gauge["reported_check"]["items"]:
        assert it["sources"]
    assert "not called a false alarm" in rp["honesty"]
    snap = gauge["snapshot"]
    assert snap["label"].startswith("HINDSIGHT") and snap["flagged_within_horizon"] > snap["flagged_now"]
    assert snap["lead_time_to_deep_min"]["max"] > 0 and snap["advisory_draft"]["bn"]
    assert snap["proposal_counts"]["live_wire_hazard"] == snap["flagged_within_horizon"]


def test_data_files_cover_the_network(hydro_dry):
    sus = json.loads((DATA / "susceptibility.json").read_text())
    assert set(sus["segments"]) == {str(s) for s in hydro_dry.net.segments}
    assert sus["label"] == "MODELLED" and "Copernicus" in sus["inputs"]["dem"]["product"]
    assert {k for k, v in sus["segments"].items() if v["elevated"]} >= {"1001", "1003"}
    hs = json.loads((DATA / "hotspots.json").read_text())
    for h in hs["hotspots"]:
        assert h["sources"] or h.get("unverified") is True
        for s in h["sources"]:
            assert hs["sources"][s]["url"].startswith("http")


def _client(mm=0.0):
    hy = make_hydro(mm)
    return TestClient(create_app(Settings(), hydro=hy))


def test_api_endpoints():
    with _client(5.0) as c:
        h = c.get("/health").json()
        assert h["status"] == "ok" and h["labels"]["pumps"].startswith("EMULATED")
        nc = c.get("/hydro/nowcast").json()
        assert len(nc["segments"]) == h["network"]["segments"]
        t = c.get("/hydro/tide", params={"hours": 6}).json()
        assert t["label"].startswith("MODELLED") and len(t["series"]) == 25 and t["sources"]
        assert c.get("/hydro/tide", params={"hours": 100}).status_code == 422
        r = c.get("/hydro/rain").json()
        assert r["label"] == "LIVE" and len(r["points"]) == 18 and r["city"]["series"]
        p = c.get("/hydro/pumps").json()
        assert p["label"] == "EMULATED" and all(s["label"] == "EMULATED" for s in p["stations"])
        assert c.post("/hydro/replay", params={"event": "1999-01-01"}).status_code == 404
        rp = c.post("/hydro/replay").json()
        assert set(rp["runs"]) == {"open_meteo_archive", "imd_gauge_anchored"}
