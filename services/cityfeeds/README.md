# cityfeeds: open Kolkata situational feeds

This service fetches, caches and normalises the open feeds that describe Kolkata and South Bengal right now. It feeds the god's-eye **City** row (Air · Heat · Cyclone · River · Quake), the air and cyclone map layers, and the citizen page's "Air today". Every item carries an honest label: **LIVE** (a third-party open feed), **OBSERVED** (a monitoring station's own measurement, from a keyed service), **MODELLED** (computed here or a model's value), **INDICATIVE** (National AQI bands on values that are not CPCB's AQI), **AGGREGATE** (news mentions counted) or **UNAVAILABLE** (the feed did not answer; nothing is shown as zero). In offline mode the recorded fixtures answer, labelled **RECORDED**. Every outside source, its key and its state: [`docs/DATA_SOURCES.md`](../../docs/DATA_SOURCES.md).

The service drafts three kinds of **proposal**, never actions; a named officer decides each one:

- an **air** health advisory in বাংলা, English and हिंदी;
- a **heat** duty-shift advisory for exposed junction posts;
- a **cyclone** plan to pre-position tree-cutting teams on the arterials.

Full documentation, sources and the checks behind every feed are in [`docs/ai/cityfeeds.md`](../../docs/ai/cityfeeds.md).

## Feeds (checked from this box on 28–29 Oct 2026)

| Feed | Source | Label | Schedule |
|---|---|---|---|
| Air | Open-Meteo air-quality API (CAMS) at the ten WBPCB/CPCB sites; CPCB National AQI bands | LIVE feed, MODELLED values, INDICATIVE AQI | 15 min cache, 1 per 60 s, 200 a day |
| Heat | Open-Meteo forecast at Alipore and Dum Dum; NWS heat index; IMD plains heatwave test | LIVE feed, MODELLED | 15 min, 60 s, 200 |
| Cyclones and floods | GDACS event list and cyclone geometry (Bay of Bengal box) | LIVE; distances MODELLED | 30 min, 120 s, 96 |
| Rivers (DVC) | CWC flood-forecasting API: observed levels at Maithon, Tenughat, Durgapur barrage, Jamalpur, Harinkhola, Ghatal, Kalna and the Damodar railway bridge | LIVE | 30 min, 300 s, 60 |
| DVC news | Kolkata RSS (TOI Kolkata, Sangbad Pratidin, ABP Ananda; Millennium Post when it answers), mentions counted | AGGREGATE | 30 min, 600 s, 48 |
| Quakes | USGS FDSN event service, M ≥ 2.5 within 500 km, last 365 days | LIVE | 60 min, 300 s, 48 |
| Tide table | Syama Prasad Mookerjee Port's Tidal Notices page, read live over a pinned exception for its expired certificate (`tls.py`); it answers 404 "No Such URL.", shown as exactly that; the hydro tide model beside it | PUBLISHED as the port answers (UNAVAILABLE today); MODELLED | 6 h, 1 h, 8 (port); 10 min, 30 s (model) |
| Notices | KMC public portal (no robots.txt), place and road notices only; Kolkata Traffic Police current advisories (legacy-TLS allowance for that host, certificate verified) | LIVE | 6 h, 1 h, 8 each |
| Fires | NASA FIRMS hotspots in the Kolkata Metropolitan Area box: the public South Asia 24-h files (no key), or the area API with `FIRMS_MAP_KEY` | LIVE; "not a confirmed fire" | 3 h, 30 min, 16 |
| Observed air | CPCB on data.gov.in (`DATA_GOV_IN_API_KEY`), WAQI (`WAQI_TOKEN`), OpenAQ v3 (`OPENAQ_API_KEY`), matched to the ten sites | OBSERVED (off and `needs <KEY>` without its key) | 30 min, 5 min, 96 each |
| Street stills | Mapillary (`MAPILLARY_TOKEN`), nearest public photo to a point, CC BY-SA 4.0 | Reference photo · not live | per point 24 h, 500 a day |

**Dropped:**
- **IMD RSMC bulletins:** these are PDF and text, not machine-readable, so they are linked rather than parsed.
- **kmc.wb.gov.in circulars:** no answer.

## API (production port 8199, loopback)

| Route | Returns |
|---|---|
| `GET /health` | Service, labels, each feed's schedule and usage today, `keyed_sources` (`live` / `needs <KEY>` / `error: …`) |
| `GET /feeds/summary` | The chips `air · heat · cyclone · river · quake · tide`, each with value, unit, band, label, source, as-of, mode, stale |
| `GET /feeds/air` | Ten sites: now, 24-h PM2.5/PM10 means, indicative National AQI, a 48-h forecast of the daily band; `proposal` |
| `GET /feeds/heat` | Alipore and Dum Dum: heat index now and its 48-h peak, the IMD heatwave test per forecast day; `proposal` |
| `GET /feeds/cyclones` | GeoJSON FeatureCollection: tracks, positions, 60/90/120 km/h wind buffers, cone, flood points; `active`, `nearest`, `proposal` |
| `GET /feeds/river` | CWC stations with level, trend, warning and danger levels and status; `dvc_news` mention count |
| `GET /feeds/quakes` | GeoJSON of the USGS events within 500 km; counts for 30 and 365 days |
| `GET /feeds/tide-table` | `published` (the port's answer, read live: status, its own words, when; `LINKED` notices if it ever lists them) and `modelled` (the hydro service's high and low waters) |
| `GET /feeds/notices` | KMC notices about places and roads and the Traffic Police's current advisories (title, link, date) |
| `GET /feeds/fires` | GeoJSON of NASA FIRMS hotspots in the metro box, each with its nearest landmark; `key` state |
| `GET /feeds/street-image?lat=&lon=` | The nearest Mapillary photo (thumbnail URL, capture time, attribution, licence), or `needs MAPILLARY_TOKEN`; never calls the vision model |
| `GET /feeds/proposals` | Every drafted proposal, and why the others were not drafted |

`?force=1` refreshes past the cache, still inside the rate limits. The deck's public gate refuses it, and allows only `GET /feeds/summary` and `GET /feeds/air` anonymously.

## Run and test

```bash
PYTHONPATH=src PORT=9201 python -m cityfeeds                    # dev; SAHOSHI_FEEDS_OFFLINE=1 for fixtures only
python -m pytest -q -p no:cacheprovider                         # offline: the recorded fixtures, no network
PYTHONPATH=src python scripts/record_fixtures.py [air.json …]   # re-record on purpose (the tests pin 28 Oct 2026)
```

The production unit is `infra/systemd/sahoshi-feeds.service` (127.0.0.1:8199, pulled in by `sahoshi-ai.target`). It runs from `.venvs/ai-forecast`, which already has fastapi, uvicorn, httpx, pydantic-settings and structlog; no new package is needed. Settings use the `SAHOSHI_FEEDS_` prefix (none secret). Five free keys are read by their own names from `~/.config/sahoshi/sahoshi.env` (`keys.py`): `DATA_GOV_IN_API_KEY`, `WAQI_TOKEN`, `OPENAQ_API_KEY`, `FIRMS_MAP_KEY` (optional) and `MAPILLARY_TOKEN`; a key is never logged, returned or stored in an error (`keys.redact`).

## Limits

- **Air:** the values are the CAMS global model's, on a coarse grid (four cells cover the ten sites). The National AQI here uses PM2.5 and PM10 only, so it is indicative. With `DATA_GOV_IN_API_KEY` the stations' own CPCB averages are shown beside them, labelled OBSERVED (the keyed parsers are tested on hand-written samples in each service's documented shape; no key was available to record a real answer).
- **Site coordinates:** these are each named site's public location (landmark, campus or locality), good to about ±1 km.
- **Heat:** the IMD test runs on the forecast maximum against the Alipore 1991–2020 monthly normal. It is never an IMD declaration.
- **Rivers:** CWC publishes levels, not DVC release volumes. A release shows here as rising levels downstream and as news mentions.
- **Tide:** the port's site answers 404 for its tide notices, so there is no comparison with the model. If it lists notices again they are linked, not parsed (the tables are PDFs).
- **Notices:** the KMC portal's downloads list, filtered by keywords; the Traffic Police home page's advisories (undated unless the file name carries a date).
- **Fires:** a hotspot is a satellite pixel hotter than its surroundings at overpass (375 m VIIRS, 1 km MODIS), never a confirmed fire and never who.
