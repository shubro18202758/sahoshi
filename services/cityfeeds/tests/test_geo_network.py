"""Geometry helpers, and every network id the proposals name exists in the Kolkata city pack."""

import json
from pathlib import Path

from cityfeeds.geo import KOLKATA, bearing_deg, compass, haversine_km, point_in_ring
from cityfeeds.proposals import ARTERIALS, HEAT_POSTS

NET = next(p / "cities" / "kolkata" / "network.json" for p in Path(__file__).resolve().parents
           if (p / "cities" / "kolkata" / "network.json").is_file())


def test_distance_and_bearing():
    assert abs(haversine_km(*KOLKATA, 22.6531, 88.4467) - 12.4) < 1.0
    assert compass(bearing_deg(*KOLKATA, 16.4, 81.8)) in ("SW", "WSW")


def test_point_in_ring():
    sq = [[88.0, 22.0], [89.0, 22.0], [89.0, 23.0], [88.0, 23.0], [88.0, 22.0]]
    assert point_in_ring(88.36, 22.57, sq) and not point_in_ring(87.5, 22.57, sq)


def test_ids_exist_in_the_city_pack():
    net = json.loads(NET.read_text(encoding="utf-8"))
    segs = {s["segment_id"] for s in net["segments"]}
    juns = {j["junction_id"]: j["name"] for j in net["junctions"]}
    for ids, _road, j, _name in ARTERIALS:
        assert set(ids) <= segs and j in juns
    for j, _name in HEAT_POSTS:
        assert j in juns
