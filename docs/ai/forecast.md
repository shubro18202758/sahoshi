# Corridor forecasting (`services/forecast`)

Sahoshi forecasts speed and volume-to-capacity (V/C) for every segment of the Kolkata road network, 15 to 120 minutes ahead, as p10 / p50 / p90 bands. When the median V/C is forecast to cross 0.8, the service raises a **pre-emptive diversion proposal**. A named duty officer decides; the service never acts.

| | |
|---|---|
| Model | **Chronos-2** (`amazon/chronos-2`), zero-shot and covariate-aware, about 120 M parameters, on the GPU |
| Second model (backtest) | **TimesFM 2.5** (`google/timesfm-2.5-200m-pytorch`), univariate |
| Baseline | Seasonal naive: same slot yesterday or last week, whichever fitted the last two days better |
| Covariates | Rain intensity, outfall-gate closure (Hooghly tide), active events |
| Port | 8195 in production (loopback); 9151 in development |
| Label | **"Forecast on simulated traffic"** until the platform has recorded traffic for Kolkata |

## Licences (checked against the model cards, 28 Oct 2026)

| Artefact | Licence | Where it was checked |
|---|---|---|
| `amazon/chronos-2` weights | Apache-2.0 | model card front matter `license: apache-2.0` (HF snapshot `29ec376…`) |
| `chronos-forecasting` 2.3.2 (package) | Apache-2.0 | wheel METADATA |
| `google/timesfm-2.5-200m-pytorch` weights | Apache-2.0 | model card front matter `license: apache-2.0` (HF snapshot `1d95242…`) |
| `timesfm` 3.0.2 (package) | Apache-2.0 | wheel METADATA |

TimesFM 2.5 installs cleanly on aarch64 (`timesfm[torch]==3.0.2`) and runs on the GB10. Its covariate path (`forecast_with_covariates`) needs the JAX `xreg` extra, which the service does not install, so it runs univariate.

## Data: where the platform keeps traffic, and what the service reads

The traffic-oracle holds traffic state in four places:

- `traffic.observations`: the raw rows (`speed_kmh`, `congestion_idx`, `data_quality`). Read through `GET /api/v1/traffic/history/{id}`, which returns the last 24 hours, at most 500 rows.
- `traffic.hourly_aggregates` and `traffic.hourly_aggregates_synthetic`. Read through `GET /api/v1/traffic/historical?segment_id=&hours=`, which returns them as `aggregates` (real) and `synthetic_aggregates` (simulated). They are never merged.
- `corridor.road_segments`. Read through `GET /api/traffic/segments?bbox`. The deck's `traffic-flow` layer draws from the same geometry.
- Active corridor events and their route spines. Read through `GET /api/v1/events/active`.

The service only ever sends GET requests to the oracle, and a test asserts it. The oracle's base URL is configurable. Development used the Sahoshi sandbox at `http://127.0.0.1:8170`.

### How a segment's history is built

1. Take the hourly aggregates and interpolate them to 15-minute steps. Real rows are used first. The synthetic rollup is used only when there is no real row, and then the whole series is labelled SIMULATED.
2. Lay the last day's raw rows over that, resampled to 15-minute means.
3. The oracle stores speed, not V/C. V/C is derived from speed by inverting the oracle's own twin curve, `v = v_ff / (1 + 0.55·(V/C)^4.2)` (`bpr.py`, MODELLED).

### The city guard

A store still seeded with another city has the same segment ids on different roads. To avoid reading it as Kolkata, only segments the oracle serves **inside the Kolkata bbox** are read from it. When this was run, the sandbox was still on the old city, so it served no segment in the bbox. Every segment then fell back, with the reason stated: "oracle serves no segment with this id inside the city bbox (its store is not seeded with this city's network)".

### The synthetic Kolkata history (`synthetic.py`, SIMULATED)

`synthetic.py` generates a deterministic, seeded history for offline tests and backtests. It models these rhythms:

- **Weekday office peaks.** A late-morning peak around 10:00–11:00 IST and a longer evening peak around 17:30–19:30. Inbound roads load in the morning and outbound roads in the evening.
- **Weekends.** Lighter Saturdays and Sundays.
- **Durga Puja nights.** On the official West Bengal notification dates, roads near the big pandals load heavily from 17:00 to 04:00:
  - 2025: Shashthi 28 Sep to Dashami 2 Oct;
  - 2026: Shashthi 17 Oct to Dashami 21 Oct.
- **Monsoon-shaped storm cells.** Rain cuts capacity.
- **Waterlogging at high tide.** Accumulated rain cuts capacity further while the Garden Reach tide model says the gates are shut.
- **Match egress.** A few simulated Eden Gardens match-egress windows.
- **Breakdowns.** Unannounced incidents.
- **Noise.** AR(1) noise.

A value at a given instant does not depend on the window requested.

The `data_source` setting controls which history is used:

| `data_source` | Behaviour |
|---|---|
| `auto` (default) | Oracle history where it has at least 2 days; otherwise the synthetic history, per segment |
| `oracle` | Oracle history only. A segment without it is reported in `skipped`, not forecast. |
| `synthetic` | Synthetic history only |

Covariates follow the history's world:

| History | Rain | Tide (gate closure) | Events |
|---|---|---|---|
| Oracle | Hydro service, `GET /hydro/rain` (Open-Meteo, LIVE) | Garden Reach tide model (MODELLED) | Oracle active events |
| Synthetic | Simulated world (SIMULATED) | Simulated world (SIMULATED) | Simulated world (SIMULATED) |

## API

| Route | What it returns |
|---|---|
| `GET /health` | Model slot (loaded or not, weights in GPU MiB, peak MiB, idle timer), second model, oracle probe, GPU |
| `GET /forecast/segments?horizon_min=15..120` | For each segment: 15-minute steps with `vc` and `speed_kmh` p10/p50/p90 and the baseline p50. Also `crossing` (when p50 V/C reaches 0.8 within the horizon and is below it now), the `proposals`, `data_labels` and `data_note`. |
| `GET /forecast/segment/{id}?horizon_min=` | One segment and its proposal. Unknown id: 404. Not forecast: 409. |
| `GET /forecast/metrics` | Rolling backtest, with the honest data label |
| `POST /forecast/refresh?backtest=false` | Recompute now; include the backtest when `backtest=true` |

### Proposal shape

Proposals use the decision-support vocabulary of `osint_common` (C-U):

- `state: proposed`;
- `actions` as `CoaAction`: verb `diversion`, `monitor` or `advisory`, with `requires_officer: true` and `reversible: true`;
- `recommendation.decision: await_officer`;
- `human_gate: {state: proposed, required_role: duty_officer, officer: null, decided_at: null}`;
- `labels`.

The detour is the shortest path on the city network between the segment's end junctions. It avoids the segment and, where it can, every other segment forecast at or over 0.8.

Real output, sandbox run of 28 Oct 2026, origin 11:00 UTC:

> Park Circus seven-point crossing: V/C forecast 0.81 in 45 min (p10–p90 0.72–0.89) on Mother Teresa Sarani (Park Street); propose diversion via Acharya Jagadish Chandra Bose Road → Ashutosh Mukherjee Road → Hazra Road → Syed Amir Ali Avenue.

## Backtest

The backtest ran on 28 Oct 2026 with `GET /forecast/metrics` on the GB10. Its scope:

- **Origins:** 12 rolling origins, every 6 hours over 25–28 Oct 2026.
- **Series:** 65 segments × 12 origins = 780 series.
- **Horizon and context:** 120 minutes ahead, from a 14-day context.
- **Data:** the SIMULATED history (seed 1690).
- **Future covariates:** the realised simulated values, which is a perfect-nowcast assumption.

| Model | MAE (V/C) | MAPE | MAE speed | p10–p90 coverage (target 0.80) | Mean band width | Skill vs baseline | Crossing alerts precision / recall |
|---|---|---|---|---|---|---|---|
| **Chronos-2** (with covariates) | **0.0429** | 15.2 % | 0.74 km/h | 0.797 | 0.135 | **+54.9 %** | 0.79 / 0.44 |
| Chronos-2 without covariates (ablation) | 0.0439 | 15.3 % | 0.76 km/h | 0.758 | 0.126 | +53.9 % | 0.83 / 0.54 |
| TimesFM 2.5 (univariate) | 0.0443 | 15.4 % | 0.77 km/h | 0.813 | 0.145 | +53.5 % | 0.78 / 0.51 |
| Seasonal naive (baseline) | 0.0952 | 32.0 % | 1.53 km/h | 0.754 | 0.276 | — | 0.63 / 0.41 |

How to read this, honestly:

- Both foundation models halve the baseline's error.
- Chronos-2 with covariates is the most accurate and the best calibrated. It improves coverage by about 4 points over its own univariate run.
- Its gain in point error from the covariates is small (2 %).
- Its alert recall is lower than without covariates. It raises fewer, more precise crossing alerts.
- These are numbers on simulated traffic. They show that the pipeline works and how the models compare. They do not measure accuracy on Kolkata roads.

A second run a few minutes later (`POST /forecast/refresh?backtest=true`, origins shifted by 15 minutes) gave:

| Model | MAE (V/C) | Coverage |
|---|---|---|
| Chronos-2 | 0.0415 | 0.813 |
| Chronos-2 without covariates | 0.0429 | 0.765 |
| Seasonal naive | 0.0938 | 0.758 |
| TimesFM 2.5 | 0.0439 | 0.813 |

### GPU memory (measured with `torch.cuda` on the GB10)

| | Chronos-2 (fp32) | TimesFM 2.5 |
|---|---|---|
| Weights | 456 MiB | 882 MiB |
| Peak | 1,614 MiB (65 segments × 14-day context) | 3,655 MiB, process-wide (batch of 128) |
| Load time | 6–12 s | 2–4 s |
| Inference | ~1–2 s for 65 segments once loaded | — |

- `SAHOSHI_FORECAST_DTYPE=bfloat16` halves the Chronos-2 weights.
- Chronos-2 is loaded on first use and **freed after `idle_unload_sec` of disuse**. In the development run (idle 60 s), `/health` then showed `loaded: false`, `unloads: 1` and 32 MiB still allocated.
- TimesFM is freed as soon as the backtest finishes.

## Limits

- **Forecasts are on simulated traffic** until the oracle stores real Kolkata traffic. The labels say so on every segment and every proposal.
- **V/C is derived, not measured.** It comes from speed through the twin's curve.
- **The detours use the curated arterial network** (65 segments), so they can be long. Each proposal states the detour length, and the officer judges it.
- **The diverted share is a proportional estimate.** `expected_effect.suggested_share` was not simulated in the twin.
- **At evening peaks, many segments cross 0.8 at once** (18–26 crossings in the sample run). Proposals are sorted by forecast severity, then by how soon.
- **The tide model here is a copy of `services/hydro/src/hydro/tide.py`.** A test keeps the two identical.
