import numpy as np

from forecast.bpr import speed_from_vc, vc_from_speed
from forecast.network import haversine_m, load_network


def test_bpr_roundtrip_and_monotone():
    vc = np.linspace(0.0, 1.6, 33)
    sp = speed_from_vc(vc, 40.0)
    assert np.all(np.diff(sp) <= 0)
    back = vc_from_speed(sp, 40.0)
    assert np.allclose(back[1:], vc[1:], atol=1e-6)
    assert speed_from_vc(0.0, 40.0) == 40.0


def test_vc_from_speed_clips():
    assert vc_from_speed(60.0, 40.0) == 0.0  # faster than free flow → 0
    assert vc_from_speed(0.0, 40.0) <= 2.0


def test_network_bundled_snapshot(net):
    assert len(net.segments) >= 64
    assert 1027 in net.segments and net.segments[1027].road_name.startswith("Mother Teresa Sarani")
    assert net.junction_name(17).startswith("Park Circus")
    assert "OpenStreetMap" in net.attribution


def test_alternative_path_avoids_segment_and_respects_one_way(net):
    path = net.alternative_path(1027)
    assert path and 1027 not in path
    seg = net.segments[1027]
    # the detour is a connected directed path from the segment's start to its end
    node = seg.from_junction
    for sid in path:
        s = net.segments[sid]
        if s.from_junction == node:
            node = s.to_junction
        else:
            assert not s.oneway and s.to_junction == node
            node = s.from_junction
    assert node == seg.to_junction
    # one-way 1008 (howrah_bridge->bbd_bag) is never travelled backwards
    for a, b, sid, _w in net.links():
        if sid == 1008:
            assert (a, b) == (net.segments[1008].from_junction, net.segments[1008].to_junction)


def test_alternative_path_avoid_set_is_soft(net):
    full = net.alternative_path(1027)
    # avoiding every segment of the detour either finds another or falls back to the unconstrained one
    alt = net.alternative_path(1027, avoid=set(full))
    assert alt is not None and 1027 not in alt


def test_haversine():
    assert abs(haversine_m(22.5726, 88.3639, 22.5726, 88.3639)) < 1e-6
    assert 850 < haversine_m(22.5646, 88.3512, 22.5726, 88.3496) < 950


def test_load_network_from_city_dir(tmp_path, net):
    import json

    (tmp_path / "network.json").write_text(json.dumps({
        "junctions": [{"junction_id": 1, "name": "A", "lat": 22.5, "lon": 88.3},
                      {"junction_id": 2, "name": "B", "lat": 22.51, "lon": 88.31}],
        "segments": [{"segment_id": 9, "road_name": "R", "from_junction": 1, "to_junction": 2,
                      "line": [[88.3, 22.5], [88.31, 22.51]]}]}))
    n = load_network(tmp_path)
    assert list(n.segments) == [9] and n.source.endswith("network.json")
    assert n.alternative_path(9) is None
