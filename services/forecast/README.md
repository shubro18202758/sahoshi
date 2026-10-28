# forecast: corridor speed and congestion forecasting

This service forecasts speed and V/C for every Kolkata road segment, 15 to 120 minutes ahead in 15-minute steps, as p10 / p50 / p90 bands. A segment is flagged with a `crossing` when its median V/C is forecast to reach 0.8 within the horizon. Each crossing produces a **pre-emptive diversion proposal**, never an action: a named duty officer decides. The full design, data paths and backtest numbers are in [`docs/ai/forecast.md`](../../docs/ai/forecast.md).

## Models and licences

| Role | Model | Licence |
|---|---|---|
| Forecaster | **Chronos-2** (`amazon/chronos-2`, ~120 M parameters), via `chronos-forecasting`; on the GPU; covariate-aware | Apache-2.0 (model card and package) |
| Second model (backtest only) | **TimesFM 2.5** (`google/timesfm-2.5-200m-pytorch`), via `timesfm[torch]`; univariate here | Apache-2.0 (model card and package) |
| Baseline | Seasonal naive: day or week lag, chosen on the last two days | — |

- **Loading:** weights load lazily, are freed after `SAHOSHI_FORECAST_IDLE_UNLOAD_SEC` (600 s) of disuse, and are never downloaded at import.
- **GPU memory (GB10):** Chronos-2 weights take 456 MiB, peaking at 1.6 GiB for 65 segments with 14 days of context. TimesFM takes 882 MiB and is freed right after the backtest.
- **Fallback:** if the model cannot load, the service serves the baseline and says so in `model_note`.

## API (production port 8195, loopback)

`GET /health` · `GET /forecast/segments?horizon_min=15..120` · `GET /forecast/segment/{id}` · `GET /forecast/metrics` (rolling backtest: model vs baseline vs second model, plus a no-covariate ablation) · `POST /forecast/refresh?backtest=false`

## Data and honest labels

| Data | Source | Label |
|---|---|---|
| History | The traffic-oracle, read only (GET): hourly aggregates + raw rows, and only for segments it serves inside the Kolkata bbox | `LIVE` if the rows are real; `SIMULATED` if they are its simulated feed |
| History (fallback) | The deterministic synthetic Kolkata history (`synthetic.py`) | `SIMULATED` |
| V/C | Derived from speed through the oracle's twin curve (`bpr.py`) | MODELLED |
| Rain covariate (oracle history) | The hydro service, Open-Meteo | LIVE |
| Gate-closure covariate | Hooghly tide model (`tide.py`, a copy of the hydro service's) | MODELLED |
| Event covariate | Oracle active events | — |
| Covariates (synthetic history) | The same simulated world | SIMULATED |
| Proposals | — | Carry their data label and `MODELLED` |

Until the oracle stores Kolkata traffic, every forecast is a **forecast on simulated traffic**, and the response says so in `data_note`.

## Run and test

```bash
# dev run (venv with chronos-forecasting / timesfm; sandbox oracle read-only)
PYTHONPATH=src PORT=9151 SAHOSHI_FORECAST_ORACLE_URL=http://127.0.0.1:8170 python -m forecast

# offline tests (no model, no network)
python -m pytest -q -p no:cacheprovider
# the real-model tests (GPU venv, weights in the HF cache)
python -m pytest -q -p no:cacheprovider -m model
```

Settings use the `SAHOSHI_FORECAST_*` prefix (see `config.py`): `DATA_SOURCE` (auto | oracle | synthetic), `MODEL` (chronos2 | timesfm | naive), `CONTENDER` (timesfm | ""), `DEVICE`, `DTYPE` (float32 | bfloat16), `CONTEXT_DAYS`, `IDLE_UNLOAD_SEC`, `ORACLE_URL`, `HYDRO_URL`, `CITY_DIR`. The image is `infra/docker/Dockerfile.forecast`; the compose stanza is in `infra/compose.ai.yml`.

## Limits

- **History:** simulated until Kolkata traffic is recorded. V/C is derived, not counted.
- **Proposals:**
  - detours are on the curated 65-segment arterial network;
  - the diverted share is a proportional estimate that was not run through the twin.
- **TimesFM:** runs without covariates.
- **Network:** the bundled snapshot is taken from the network stream (ids stable). A `cities/kolkata/network.json` in the repo takes precedence.
