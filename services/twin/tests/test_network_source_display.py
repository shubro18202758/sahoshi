"""/twin/network names its file repo-relative, never by absolute path (audit, 29 Oct)."""

from __future__ import annotations

from pathlib import Path

from sahoshi_twin.network import display_source, load_network

REPO = Path(__file__).resolve().parents[3]


def test_display_source_keeps_the_city_pack_path_only():
    assert display_source("/home/someone/repo/cities/kolkata/network.json") == \
        "cities/kolkata/network.json"
    assert display_source(Path("/opt/elsewhere/net.json")) == "net.json"


def test_loaded_network_names_no_absolute_path():
    net = load_network(REPO / "cities" / "kolkata" / "network.json")
    assert net.source_path == "cities/kolkata/network.json"
    assert net.summary()["source_path"] == "cities/kolkata/network.json"
