# hydro: Kolkata waterlogging nowcast

This service gives every segment of the Kolkata road network a **depth-risk class 0–3** for the next 2 hours. Each class comes with an expected depth band, a lead time and four labelled drivers:

- **rain:** the Open-Meteo nowcast (LIVE);
- **tide:** a Hooghly tide model at Garden Reach (MODELLED, approximate). The outfall gates close at high tide;
- **susceptibility:** from terrain and drainage, built from Copernicus DEM GLO-30, OSM drains and canals, and sourced hotspots (MODELLED);
- **pump-station state:** from a KMC FFEWS adapter that is **EMULATED** until access is granted.

For flagged roads (risk ≥ 2) the service drafts **proposals**, never actions: a reroute, an ambulance (108) window note, a live-wire hazard request to the power utility, and one public advisory in Bengali and English. A named officer approves each one. Full documentation, sources and the 22–23 Sep 2025 replay are in [`docs/ai/hydro.md`](../../docs/ai/hydro.md).

## API (production port 8197, loopback)

| Route | Returns |
|---|---|
| `GET /health` | Service state |
| `GET /hydro/nowcast` | Per segment: class, depth band, lead time (to the peak class and to deep water), drivers with labels; proposals |
| `GET /hydro/tide?hours=1..72` | Series, high and low waters, gate state, sources |
| `GET /hydro/rain` | The 18-point Open-Meteo nowcast and the city mean. Cached 10 min; at most one call per 30 s; daily cap. `SAHOSHI_HYDRO_OFFLINE=1` makes no outbound calls. |
| `GET /hydro/pumps` | Station state (EMULATED) |
| `POST /hydro/replay?event=2025-09-23` | Two runs: the Open-Meteo archive and the IMD gauge-anchored rain, checked against the places the news reported |

## How it works

A conceptual ponding model on 15-minute steps (`model.py`, every parameter stated):

- **Drainage capacity:** 6–20 mm/h by susceptibility. Both bounds are from KMC and Mayor statements.
- **Gates shut** (tide ≥ 5.0 m): capacity is halved.
- **Pump availability:** scales capacity between 60 % and 100 %.
- **Runoff:** 0.85.
- **Depth at the road:** ponded water × (1 + 2·S).
- **Classes:** 0 (< 2 cm), 1 (2–10 cm), 2 (10–30 cm), 3 (> 30 cm).
- **Elevated segments** (bridge decks, flyovers): never pond.

## Data files

| File | Contents |
|---|---|
| `src/hydro/data/kolkata_network.json` | Network snapshot from the network stream (ids stable; © OSM contributors, ODbL) |
| `src/hydro/data/kolkata_landmarks.json` | Canonical landmark ids |
| `src/hydro/data/hotspots.json` | Reported waterlogging hotspots, each with its sources. Kasba and the Ultadanga underpass are marked unverified. |
| `src/hydro/data/susceptibility.json` | Built by `scripts/build_susceptibility.py --dem <Copernicus tile> --waterways <Overpass JSON>` (needs `rasterio`; the image does not) |

## Licences and attributions

| Item | Licence or attribution |
|---|---|
| Copernicus DEM GLO-30 | © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018, provided under COPERNICUS by the European Union and ESA |
| OpenStreetMap | © OpenStreetMap contributors, ODbL 1.0 |
| Open-Meteo | Data under CC BY 4.0; the free API for non-commercial use |
| Tide constants | Khan et al. 2021 (NHESS), Supplement Table S1 |

No machine-learning model is used.

## Run and test

```bash
PYTHONPATH=src PORT=9152 python -m hydro
python -m pytest -q -p no:cacheprovider        # offline: Open-Meteo is mocked
```

The image is `infra/docker/Dockerfile.hydro`; the compose stanza is in `infra/compose.ai.yml`.

## Limits

- **Rain:** Open-Meteo is a model nowcast, not a gauge. Its archive misses the 2025-09-23 storm by an order of magnitude (21 mm vs 249 mm), so a gauge feed (KMC FFEWS or IMD AWS) is the pilot's first need.
- **Tide:** an approximate transfer from Diamond Harbour.
- **Susceptibility:** from a surface DEM and hand-placed hotspots.
- **Pumps:** emulated.
- **The model:** a bucket model, not a sewer model.
- **Network:** 65 arterial segments.
