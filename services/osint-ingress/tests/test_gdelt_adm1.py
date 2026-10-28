"""GDELT ADM1 for West Bengal is the FIPS 10-4 code ``IN28`` (plan R28), verified on a real GDELT export read in
place (the PoC's captures are global 15-minute slices, so they hold Kolkata rows too); and the bulk parser reads
only the export that ``lastupdate.txt`` names."""

from __future__ import annotations

import csv
import io
import shutil
import zipfile
from pathlib import Path

import pytest
from conftest import CAPTURE, POC_RAW, needs_poc

from osint_common.kinds import GDELT_ADM1_WEST_BENGAL
from osint_ingress.cache import Cache
from osint_ingress.connectors.base import CITY_BBOX
from osint_ingress.connectors.gdelt import EVENT_COLUMNS, GdeltBulk
from osint_ingress.importer import import_capture

#: The real export the PoC's lastupdate.txt names (23:30 UTC on 23 Oct 2026): 1,229 rows, 7 of them in Kolkata.
POC_2330 = POC_RAW / "20261023233000.export.CSV.zip"


def _rows(path: Path):
    with zipfile.ZipFile(path) as zf, zf.open(zf.namelist()[0]) as fh:
        yield from csv.reader(io.TextIOWrapper(fh, encoding="utf-8", errors="replace", newline=""),
                              delimiter="\t", quoting=csv.QUOTE_NONE)


@pytest.mark.skipif(not POC_2330.is_file(), reason="PoC capture 20261023233000.export.CSV.zip absent (CI)")
def test_every_kolkata_bbox_row_of_a_real_export_carries_in28():
    lat_i, lon_i, adm_i, name_i = (EVENT_COLUMNS[k] for k in (
        "action_geo_lat", "action_geo_long", "action_geo_adm1_code", "action_geo_fullname"))
    inside = []
    for row in _rows(POC_2330):
        if len(row) != 61 or not row[lat_i] or not row[lon_i]:
            continue
        lat, lon = float(row[lat_i]), float(row[lon_i])
        if CITY_BBOX[0] <= lat <= CITY_BBOX[1] and CITY_BBOX[2] <= lon <= CITY_BBOX[3]:
            inside.append((row[adm_i], row[name_i].split(",")[0]))
    # GDELT names the city "Calcutta"; every row inside the metro bbox is coded West Bengal
    assert len(inside) == 7 and set(inside) == {("IN28", "Calcutta")}
    assert GDELT_ADM1_WEST_BENGAL == "IN28"


def test_karnataka_in19_is_never_used_in_the_source():
    """West Bengal's census code is 19, but FIPS 10-4 ``IN19`` is Karnataka: GDELT's code for the state is IN28."""
    src = Path(__file__).resolve().parents[1] / "src"
    for p in src.rglob("*.py"):
        assert "IN19" not in p.read_text(encoding="utf-8"), p


def _extra_export(name: str) -> bytes:
    """A second export zip with a Kolkata row: present in the cache, but NOT named by lastupdate.txt."""
    row = [""] * 61
    row[0], row[26], row[28], row[51], row[52], row[53], row[54], row[56], row[57], row[59] = (
        "1399999999", "190", "19", "4", "Calcutta, West Bengal, India", "IN", "IN28", "22.5697", "88.3697",
        "20261020114500")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(name.removesuffix(".zip"), "\t".join(row) + "\n")
    return buf.getvalue()


def test_bulk_parser_reads_only_the_export_lastupdate_names(tmp_path, protect):
    src = tmp_path / "capture"
    shutil.copytree(CAPTURE, src)
    (src / "20261020114500.export.CSV.zip").write_bytes(_extra_export("20261020114500.export.CSV.zip"))
    import_capture(src, tmp_path / "cache")
    entry = Cache(tmp_path / "cache").latest("gdelt_events")
    assert entry.blobs == ("20261020120000.export.CSV.zip",)
    ids = {s.source_id for s in GdeltBulk().parse(entry, protect)}
    assert ids == {"1300000001", "1300000002"} and "1399999999" not in ids


@needs_poc
def test_a_real_export_yields_its_west_bengal_rows_with_their_levels(tmp_path, protect):
    """The PoC's lastupdate.txt names the 23:30 slice: its 24 West Bengal rows (IN28) are kept, the 7 Calcutta ones
    as district hints, and no row of another state; the actor columns are never read (real shape, read in place)."""
    import_capture(POC_RAW, tmp_path / "cache")
    entry = Cache(tmp_path / "cache").latest("gdelt_events")
    assert entry.blobs == ("20261023233000.export.CSV.zip",)
    sigs = GdeltBulk().parse(entry, protect)
    assert len(sigs) == 24
    assert {s.raw["action_geo_adm1_code"] for s in sigs} == {"IN28"}
    city = [s for s in sigs if "area:kolkata" in s.category_hint]
    assert len(city) == 7 and all(s.raw_geo_hint.bbox_hit for s in city)
    assert all("area:west_bengal" in s.category_hint for s in sigs if s not in city)
