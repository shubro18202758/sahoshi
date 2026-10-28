# cityfeeds: open Kolkata situational feeds

This service fetches, caches and normalises the open feeds that describe Kolkata and South Bengal right now. It feeds the god's-eye **City** row (Air · Heat · Cyclone · River · Quake), the air and cyclone map layers, and the citizen page's "Air today". Every item carries an honest label: **LIVE** (a third-party open feed), **MODELLED** (computed here or a model's value), **INDICATIVE** (National AQI bands on modelled values), **AGGREGATE** (news mentions counted) or **UNAVAILABLE** (the feed did not answer; nothing is shown as zero). In offline mode the recorded fixtures answer, labelled **RECORDED**.

The service drafts three kinds of **proposal**, never actions; a named officer decides each one:

- an **air** health advisory in বাংলা, English and हिंदी;
- a **heat** duty-shift advisory for exposed junction posts;
- a **cyclone** plan to pre-position tree-cutting teams on the arterials.

Full documentation, sources and the checks behind every feed are in [`docs/ai/cityfeeds.md`](../../docs/ai/cityfeeds.md).

## Feeds (checked from this box on 28 Oct 2026)

| Feed | Source | Label | Schedule |
|---|---|---|---|
| Air | Open-Meteo air-quality API (CAMS) at the ten WBPCB/CPCB sites; CPCB National AQI bands | LIVE feed, MODELLED values, INDICATIVE AQI | 15 min cache, 1 per 60 s, 200 a day |
| Heat | Open-Meteo forecast at Alipore and Dum Dum; NWS heat index; IMD plains heatwave test | LIVE feed, MODELLED | 15 min, 60 s, 200 |
| Cyclones and floods | GDACS event list and cyclone geometry (Bay of Bengal box) | LIVE; distances MODELLED | 30 min, 120 s, 96 |
| Rivers (DVC) | CWC flood-forecasting API: observed levels at Maithon, Tenughat, Durgapur barrage, Jamalpur, Harinkhola, Ghatal, Kalna and the Damodar railway bridge | LIVE | 30 min, 300 s, 60 |
| DVC news | Kolkata RSS (TOI Kolkata, Sangbad Pratidin, ABP Ananda; Millennium Post when it answers), mentions counted | AGGREGATE | 30 min, 600 s, 48 |
| Quakes | USGS FDSN event service, M ≥ 2.5 within 500 km, last 365 days | LIVE | 60 min, 300 s, 48 |
| Tide table | Syama Prasad Mookerjee Port: **not readable from this box**, so the hydro tide model is shown instead | PUBLISHED UNAVAILABLE; MODELLED | 10 min, 30 s |
| Notices | KMC public portal (no robots.txt), place and road notices only | LIVE | 6 h, 1 h, 8 |

**Dropped:**
- **Kolkata Police and Kolkata Traffic Police pages:** the https sites do not complete a connection from this box.
- **The port's tide tables:** the https certificate cannot be verified, and the http address answers 503. Certificate checks are never switched off.
- **IMD RSMC bulletins:** these are PDF and text, not machine-readable, so they are linked rather than parsed.
- **kmc.wb.gov.in circulars:** no answer.

## API (production port 8199, loopback)

| Route | Returns |
|---|---|
| `GET /health` | Service, labels, each feed's schedule and usage today |
| `GET /feeds/summary` | The chips `air · heat · cyclone · river · quake · tide`, each with value, unit, band, label, source, as-of, mode, stale |
| `GET /feeds/air` | Ten sites: now, 24-h PM2.5/PM10 means, indicative National AQI, a 48-h forecast of the daily band; `proposal` |
| `GET /feeds/heat` | Alipore and Dum Dum: heat index now and its 48-h peak, the IMD heatwave test per forecast day; `proposal` |
| `GET /feeds/cyclones` | GeoJSON FeatureCollection: tracks, positions, 60/90/120 km/h wind buffers, cone, flood points; `active`, `nearest`, `proposal` |
| `GET /feeds/river` | CWC stations with level, trend, warning and danger levels and status; `dvc_news` mention count |
| `GET /feeds/quakes` | GeoJSON of the USGS events within 500 km; counts for 30 and 365 days |
| `GET /feeds/tide-table` | `published` (unavailable, with the reason) and `modelled` (the hydro service's high and low waters) |
| `GET /feeds/notices` | KMC notices about places and roads (title, link, date) |
| `GET /feeds/proposals` | Every drafted proposal, and why the others were not drafted |

`?force=1` refreshes past the cache, still inside the rate limits. The deck's public gate refuses it, and allows only `GET /feeds/summary` and `GET /feeds/air` anonymously.

## Run and test

```bash
PYTHONPATH=src PORT=9201 python -m cityfeeds                    # dev; SAHOSHI_FEEDS_OFFLINE=1 for fixtures only
python -m pytest -q -p no:cacheprovider                         # offline: the recorded fixtures, no network
PYTHONPATH=src python scripts/record_fixtures.py [air.json …]   # re-record on purpose (the tests pin 28 Oct 2026)
```

The production unit is `infra/systemd/sahoshi-feeds.service` (127.0.0.1:8199, pulled in by `sahoshi-ai.target`). It runs from `.venvs/ai-forecast`, which already has fastapi, uvicorn, httpx, pydantic-settings and structlog; no new package is needed. Settings use the `SAHOSHI_FEEDS_` prefix (none secret; no feed needs a key).

## Limits

- **Air:** the values are the CAMS global model's, on a coarse grid (four cells cover the ten sites). The National AQI here uses PM2.5 and PM10 only, so it is indicative. The pilot should read CPCB's own CAAQMS data (data.gov.in, keyed).
- **Site coordinates:** these are each named site's public location (landmark, campus or locality), good to about ±1 km.
- **Heat:** the IMD test runs on the forecast maximum against the Alipore 1991–2020 monthly normal. It is never an IMD declaration.
- **Rivers:** CWC publishes levels, not DVC release volumes. A release shows here as rising levels downstream and as news mentions.
- **Tide:** no published table could be read, so there is no comparison with the model.
- **Notices:** the KMC portal's downloads list, filtered by keywords. The traffic-police advisories are not reachable.
