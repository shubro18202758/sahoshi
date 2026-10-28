<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="services/command-deck/static/brand/sahoshi-lockup.svg">
    <img alt="Sahoshi" src="services/command-deck/static/brand/sahoshi-lockup-day.svg" width="300">
  </picture>
</p>

<h3 align="center">থামিয়ে নয়, সামলে।</h3>
<p align="center"><em>Not by stopping — by steering. Keep Kolkata moving.</em></p>

<p align="center">
  <strong>One live picture of Kolkata's roads, rain and crowds for traffic police, the city corporation, disaster
  response and ambulances.<br/>The AI proposes, a named officer decides, and citizens hear it in Bengali.</strong>
</p>

<p align="center">
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-555555?style=flat-square">
  <img alt="City: Kolkata, West Bengal" src="https://img.shields.io/badge/city-Kolkata%2C%20West%20Bengal-111111?style=flat-square">
  <img alt="Languages: Bengali, English, Hindi" src="https://img.shields.io/badge/languages-%E0%A6%AC%E0%A6%BE%E0%A6%82%E0%A6%B2%E0%A6%BE%20%C2%B7%20EN%20%C2%B7%20%E0%A4%B9%E0%A4%BF%E0%A4%82%E0%A4%A6%E0%A5%80-111111?style=flat-square">
  <img alt="Tests: 5,243 pytest and 121 cargo" src="https://img.shields.io/badge/tests-5%2C243%20pytest%20%C2%B7%20121%20cargo-2ea44f?style=flat-square">
  <img alt="Status: prototype on one edge server" src="https://img.shields.io/badge/status-prototype%20on%20one%20edge%20server-555555?style=flat-square">
</p>

<p align="center">
  <img alt="AI proposes, officer decides" src="https://img.shields.io/badge/AI-proposes%20%C2%B7%20a%20named%20officer%20decides-111111?style=flat-square">
  <img alt="Vehicles and places only" src="https://img.shields.io/badge/privacy-vehicles%20and%20places%20only-111111?style=flat-square">
  <img alt="Plates masked" src="https://img.shields.io/badge/plates-masked%20until%20an%20officer%20is%20on%20duty-111111?style=flat-square">
  <img alt="Honest labels" src="https://img.shields.io/badge/labels-emulated%20%C2%B7%20simulated%20%C2%B7%20modelled-111111?style=flat-square">
  <img alt="On-premises AI" src="https://img.shields.io/badge/AI-on%20premises%2C%20open%20models-111111?style=flat-square">
</p>

<p align="center">
  <img alt="SvelteKit" src="https://img.shields.io/badge/SvelteKit-Svelte%205-FF3E00?style=flat-square&logo=svelte&logoColor=white">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white">
  <img alt="Rust" src="https://img.shields.io/badge/Rust-signal--ingress-000000?style=flat-square&logo=rust&logoColor=white">
  <img alt="PostGIS" src="https://img.shields.io/badge/PostGIS-PostgreSQL%2016-4169E1?style=flat-square&logo=postgresql&logoColor=white">
  <img alt="llama.cpp" src="https://img.shields.io/badge/llama.cpp-local%20models-555555?style=flat-square">
  <img alt="OpenStreetMap" src="https://img.shields.io/badge/OpenStreetMap-real%20roads-7EBC6F?style=flat-square&logo=openstreetmap&logoColor=white">
</p>

<p align="center">
  <img width="900" alt="Sahoshi's landing page in Bengali" src="docs/screenshots/landing.jpg" />
</p>

<p align="center">
  <a href="#what-sahoshi-is">What it is</a> ·
  <a href="#the-ai-stack">AI stack</a> ·
  <a href="#quick-start">Quick start</a> ·
  <a href="#environment-variables">Environment</a> ·
  <a href="#the-city-pack-a-city-is-a-folder">City Pack</a> ·
  <a href="#tests">Tests</a> ·
  <a href="#a-tour-of-the-screens">Tour</a> ·
  <a href="#documentation">Docs</a> ·
  <a href="#licence-and-credits">Licence</a>
</p>

---

## What Sahoshi is

**Sahoshi (সাহসী, "brave")** is a city-scale traffic, rain and crowd operations platform for Kolkata.

When a cloudburst meets a high tide on the Hooghly, when lakhs of people walk between Durga Puja pandals, or when a
bus breaks down on Howrah Bridge, each agency sees one piece of the city. Sahoshi puts the pieces on one screen:

- **Waterlogging, ahead of time.** Rain, the Hooghly tide (which shuts the outfall gates), pump status and terrain,
  combined into a depth-risk class for every arterial road with a lead time. Driven by IMD's observed rain for the
  22–23 Sep 2025 storm, it flagged every on-network place the news reported waterlogged.
- **Traffic, two hours ahead.** Forecasts with uncertainty bands for every road, and a pre-emptive diversion
  proposal when a road is about to choke.
- **Signal timing, tested before it is touched.** Every proposed change is simulated across the whole network
  against doing nothing; if it would only move the jam, the answer is "hold".
- **Bengali voice.** An officer speaks a report in Bengali and it becomes a structured, unverified field report.
  Advisories are read aloud to citizens in Bengali.
- **Camera stills, read for the road.** Waterlogged, blocked, tree fall, stalled vehicle: vehicles and roads only,
  never people.

Every output is a **proposal**. A **named duty officer** approves or rejects it; if nobody answers, the current plan
holds. Everything runs on **one on-premises server** with open-source AI and no cloud, so it keeps working when a
cyclone cuts the internet. Anything that is not from a live feed says so: **EMULATED**, **SIMULATED**,
**MODELLED**, or "Reference photo · not live".

### Who it serves

| Audience | What they get |
|---|---|
| **Kolkata Traffic Police duty officer** (Bidhannagar and Howrah City Police for their areas) | One queue of decisions, each with its reason, its modelled effect and its labels; movement planning; voice reports |
| **KMC and WBSDMA control room** | Rain, tide, pumps and waterlogging risk by road, with lead times and advisory drafts in Bengali and English |
| **Ambulance (108) crews** | A one-tap corridor request and "ambulance windows" through waterlogged roads |
| **Citizens** | "Check your road" in বাংলা, English or हिंदी, with a Listen button; no sign-in, no location |

The full product description, with the Kolkata problems and their sources, the journeys, every screen, the modelled
impact, the cost and the pilot plan, is [`PRODUCT.md`](PRODUCT.md).

---

## The AI stack

Every model runs on the one on-premises server. The operator downloads the weights once and they are served
offline; none is in this repository.

| Capability | Model | Licence | What it does | Honest label |
|---|---|---|---|---|
| Corridor forecasting | **Chronos-2** (`amazon/chronos-2`); TimesFM 2.5 as challenger; seasonal-naive baseline | Apache-2.0 | Speed and V/C for every road 15–120 min ahead with p10–p90 bands; a diversion proposal when the median crosses 0.8 | "Forecast on simulated traffic" until real Kolkata traffic is recorded |
| Waterlogging nowcast | No ML: a conceptual ponding model (rain × tide × pumps × terrain) | — | Depth-risk class 0–3 per road with lead time; reroute, ambulance window, live-wire request, Bengali and English advisory | rain LIVE · tide MODELLED · pumps EMULATED · risk MODELLED |
| Bengali speech recognition | `bengaliAI/tugstugi_bengaliai-asr_whisper-medium`; `openai/whisper-large-v3-turbo` for English and Hindi | Apache-2.0; MIT | A spoken field report → place, kind, severity | UNVERIFIED-FIELD until an officer confirms |
| Bengali speech synthesis | Svara-TTS v1 (`kenpath/svara-tts-v1`) with the SNAC 24 kHz codec | Apache-2.0; MIT | Advisories read aloud in Bengali, English or Hindi | "Synthetic voice" |
| Road-state vision | **Qwen3-VL-8B-Instruct** (Q4_K_M GGUF on llama.cpp) | Apache-2.0 | A camera still → waterlogged, blocked, tree fall, stalled vehicle, crash debris, congested or clear | UNVERIFIED-CAMERA; person and plate questions refused |
| Signal-timing proposals | A cell-transmission traffic twin with Webster and max-pressure baselines; the local LLM only words the rationale | — | Tests each candidate timing against doing nothing over the whole network | MODELLED; demand SIMULATED |
| Assistant and decision AI | A 27B decider model asked typed questions; Gemma 4 12B (Q4_K_M) for drafting; `bge-m3` and `pplx-embed-v2-late-0.6b` for memory | per model card (`bge-m3`: MIT) | Answers about the live picture, plans movements, checks every claim against tool results | Labels per answer; cannot approve |

How each model was chosen, evaluated and limited: [`docs/ai/`](docs/ai/).

---

## Quick start

### Prerequisites

| | Full stack | Console and services only |
|---|---|---|
| Hardware | An arm64 or x86-64 server with a CUDA GPU and about 128 GB of (unified) memory; the reference box is an NVIDIA GB10 with 121 GiB | Any machine with 16 GB of RAM |
| OS | Linux with systemd user units | Linux or macOS |
| Software | Docker Engine with Compose v2, the NVIDIA Container Toolkit, Python 3.12 | Docker Engine with Compose v2 |
| Model weights | In the operator's Hugging Face cache and model folders (see [`models-config/`](models-config/) and [`docs/ai/`](docs/ai/)); `llama-server` from llama.cpp | Not needed: the AI services answer 503 and the brain falls back to its heuristic tier, each saying so |
| Optional | A Cesium ion token (photoreal 3D for signed-in officers); internet for the rain nowcast and OSINT | The map runs keyless on OpenStreetMap |

### Install and bring up

Commands marked *target machine* start containers and bind ports; run them on the server that will host Sahoshi.

```bash
# 1. get the code
git clone https://github.com/shubro18202758/sahoshi.git
cd sahoshi

# 2. write ~/.config/sahoshi/sahoshi.env (mode 600) and link the systemd user units   (target machine)
bash scripts/sahoshi_up.sh --install-units

# 3. secrets, each typed on stdin (never on a command line, never committed)
bash scripts/sahoshi_env.sh --set SAHOSHI_OPERATOR_PIN -       # the duty PIN officers sign in with
bash scripts/sahoshi_env.sh --set SAHOSHI_SESSION_SECRET -     # 64 hex characters; signs officer sessions
bash scripts/sahoshi_env.sh --set POSTGIS_PASSWORD -           # before the first bring-up
bash scripts/sahoshi_env.sh --set SAHOSHI_CESIUM_ION_TOKEN -   # optional

# 4. optional switches
bash scripts/sahoshi_env.sh --set SAHOSHI_OSINT 1              # event intelligence from open sources

# 5. build and start: PostGIS → migrations 001–025 → Kolkata road network → services → converge   (target machine)
bash scripts/sahoshi_up.sh --build

# 6. the AI services: forecast, hydro, speech, vision, twin   (target machine)
. scripts/sahoshi_env.sh
bash services/vision/scripts/serve_llm.sh start   # the vision model server on 127.0.0.1:8201
sahoshi_compose -f infra/compose.ai.yml -f infra/compose.ai-media.yml -f infra/compose.twin.yml \
  up -d --build forecast hydro speech vision twin

# 7. verify (read-only)
bash scripts/sahoshi_env.sh --print          # the effective, non-secret environment
bash scripts/sahoshi_up.sh --status          # one row per component: READY 11/11 (12/12 with OSINT)
```

| URL | What |
|---|---|
| `http://<server>:5373/welcome` | The public landing page (Bengali first) |
| `http://<server>:5373/` | The officer console: sign in with your name and the duty PIN |
| `http://<server>:5373/citizen` | "Check your road", no sign-in |
| `http://<server>:5373/driver` | The ambulance (108) crew page |

Only the console (port 5373) is reachable from the network; every other service binds 127.0.0.1. From then on the
stack starts itself at boot (`sahoshi.target`). The AI services report on their own `GET /health`.

**Without the full stack.** Each AI service runs on its own for development, for example the twin on the CPU:

```bash
cd services/twin
SAHOSHI_TWIN_PORT=9171 SAHOSHI_TWIN_NETWORK=../../cities/kolkata/network.json \
  SAHOSHI_TWIN_ORACLE_URL= SAHOSHI_TWIN_LLM=0 PYTHONPATH=src python -m sahoshi_twin   # standalone: SIMULATED demand
curl -s -X POST 127.0.0.1:9171/twin/propose -H 'content-type: application/json' \
  -d '{"junction_ids":["ultadanga"],"horizon_min":45,"start":"18:00"}'
```

Recipes for every service are in [`docs/SAMPLE_DATA_AND_TESTS.md`](docs/SAMPLE_DATA_AND_TESTS.md#18-the-samples-folder).

**Developing the console outside Docker:**
`cd services/command-deck && bun install && ORACLE_PORT=8191 BRAIN_PORT=8192 EMULATOR_PORT=8190 bun run dev`
(the dev server refuses to start without the three backend ports; add `SPEECH_PORT`, `FORECAST_PORT`,
`VISION_PORT`, `HYDRO_PORT` and `TWIN_PORT` to proxy the AI services).

### Ports

| Component | Port | Bind |
|---|---|---|
| command-deck | 5373 | LAN |
| event-emulator · traffic-oracle · convoy-brain · osint-ingress | 8190 · 8191 · 8192 · 8193 | loopback |
| speech · forecast · vision · hydro · twin | 8194 · 8195 · 8196 · 8197 · 8198 | loopback |
| Qwen3-VL llama-server · TTS llama-server | 8201 · 8202 | loopback |
| model hosts: decider · tactical LLM · embeddings | 8083 · 8084 · 8085 | loopback |
| PostGIS · Valkey · NATS (monitoring) | 15434 · 6390 · 4233 (8233) | loopback |

---

## Environment variables

All host configuration lives in **`~/.config/sahoshi/sahoshi.env`** (mode 600, plain `KEY=VALUE`, never committed),
written by `scripts/sahoshi_up.sh --install-units` and edited with `scripts/sahoshi_env.sh --set KEY VALUE` (or
`--set KEY -` to type a secret on stdin). The variables you are most likely to set:

| Variable | Secret | Default | What it does |
|---|:---:|---|---|
| `SAHOSHI_OPERATOR_PIN` | ✓ | unset (gate off) | The duty PIN for officer sign-in. Unset, the console is open; never expose it beyond loopback that way |
| `SAHOSHI_SESSION_SECRET` | ✓ | random per deck start | Signs officer session cookies; set it so sign-ins survive restarts |
| `SAHOSHI_SESSION_SECURE` | | unset | `1` marks the session cookie Secure (behind TLS only) |
| `POSTGIS_PASSWORD` | ✓ | a development placeholder | The store's password (the store binds loopback only); set your own before the first bring-up |
| `SAHOSHI_CESIUM_ION_TOKEN` | ✓ | unset | Photoreal 3D tiles for signed-in officers; unset → keyless OpenStreetMap |
| `SAHOSHI_OSINT` | | `0` | `1` runs event intelligence from open sources (`osint-ingress`) |
| `OSINT_MODE` | | `live` | `offline` serves recorded samples, for sites without internet |
| `SAHOSHI_DEMO` | | `0` | `1` turns on the emulated living city and the signal-plan writer (refused unless public pages label emulated events) |
| `VVIP_REQUIRE_OFFICER` | | `1` (deployed) | Officer actions without a named officer are refused (422) |
| `VVIP_ESCORT_APPROVAL_TIMEOUT_SEC` | | `90` | How long an escort proposal waits for an officer before it expires and the plan holds (15–600) |
| `SAHOSHI_FORECAST_MODEL` | | `chronos2` | `chronos2`, `timesfm` or `naive` |
| `SAHOSHI_FORECAST_DATA_SOURCE` | | `auto` | `auto`, `oracle` or `synthetic` history |
| `SAHOSHI_HYDRO_OFFLINE` | | off | `1`: the waterlogging service makes no outbound call (rain reported unavailable) |
| `SAHOSHI_TWIN_LLM` | | `1` | `0` keeps the twin's rationales to templates |
| `SAHOSHI_ROOT`, `SAHOSHI_RUN_DIR`, `SAHOSHI_LOG_DIR`, `SAHOSHI_VENV_DIR` | | detected | Where the checkout, runtime state, logs and Python environments live |
| `DECIDER_SNAPSHOT_PATH`, `LLAMA_SERVER_BIN`, `GEMMA_GGUF`, `BGE_M3_PATH`, `SAHOSHI_MODELS_CONFIG` | | detected | Model weights, the `llama-server` binary and the model-stack configuration |
| `POSTGIS_HOST_PORT` | | `15434` | The store's loopback port |

Every variable each service reads, with its default, whether it is secret, the ports and binds and a minimal working
`sahoshi.env`, is in **[`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md)**.

---

## The City Pack: a city is a folder

Everything specific to Kolkata lives in [`cities/kolkata/`](cities/kolkata/):

| File | Contents |
|---|---|
| `city.json` | Names in English, বাংলা and हिंदी; bbox; centre; the plate format `WB NN X[X] NNNN`; emergency numbers (112, 100, 108, 101); 18 agencies; the Hooghly tide station; population |
| `landmarks.json` | 48 canonical places, from Howrah Bridge and Nabanna to Gariahat, Park Circus and Ultadanga |
| `corridors.json` | The curated corridors: Howrah Bridge – BBD Bag, Vidyasagar Setu, Chowringhee, Park Street, AJC Bose Road, Red Road, EM Bypass, VIP Road, Biswa Bangla Sarani, Rashbehari – Gariahat, Diamond Harbour Road and more |
| `osm/` | The committed OpenStreetMap extracts (ODbL) |
| `network.json` | Generated: 49 junctions, 65 road segments (125 km), signal programs and camera sites (modelled), 50 stations |

One command regenerates every file the services read (the store seed, the ingress table, the twin's scenarios, the
scenario library), deterministically and offline:

```bash
python3 scripts/city_build.py kolkata            # rebuild into the repository
python3 scripts/city_build.py kolkata --check    # rebuild into a temporary folder and compare
```

A second, reference pack for another city is kept, and a test builds both. A new district is a new folder; the next
packs named for the region are Siliguri, Asansol–Durgapur, Patna and Ranchi.

---

## Tests

Measured on 28 Oct 2026, every suite offline:

| Suite | Result |
|---|---|
| Python, 15 suites (oracle, brain, store, emulator, embeddings, the five AI services, four OSINT packages, the deck proxy guard) | **5,243 passed**, 161 skipped (they need a database sandbox or real models) |
| Rust (`signal-ingress`) | **121 passed** |
| Deck | `svelte-check` 0 errors; design-token, English copy (4,263 strings) and Bengali-script lints pass; 42 unit suites |
| City Pack | `city_build.py kolkata --check`: every derived file is current |

```bash
cd services/<service> && python -m pytest -q -p no:cacheprovider     # any Python service
cd services/signal-ingress && cargo test --locked                     # Rust
cd services/command-deck && node tests/plates.unit.mjs                 # one deck unit suite
bash scripts/verify_all.sh                                             # the offline acceptance ladder
```

Per-suite totals, the items in progress, 48 representative test cases with their commands, and the sample data:
[`docs/SAMPLE_DATA_AND_TESTS.md`](docs/SAMPLE_DATA_AND_TESTS.md).

---

## A tour of the screens

*Screenshots: [`docs/screenshots/`](docs/screenshots/). Wireframes: [`docs/wireframes/`](docs/wireframes/).*

| | |
|---|---|
| ![Home](docs/screenshots/home.jpg) **Home.** What needs you, what is happening, what is coming: the featured decision, the Rain · Tide chip, the next 2 hours. | ![Map with waterlogging risk](docs/screenshots/map-waterlogging.jpg) **Map.** Waterlogging risk 0–3 and the traffic forecast as layers, each driver labelled. |
| ![Decide](docs/screenshots/decide-ai.jpg) **Decide.** One proposal at a time: a signal-timing change with the twin's comparison against doing nothing. | ![Replay](docs/screenshots/replay-2025-09-23.jpg) **Replay 23 Sep 2025.** The storm night with IMD's observed rain and the modelled ponding. |
| ![Voice report](docs/screenshots/voice-report.jpg) **Field report by voice.** Speak in Bengali; read back the place, kind and severity; send as unverified. | ![Road state](docs/screenshots/road-state.jpg) **Road state.** A camera still read for the road, never for people. |
| ![Object page](docs/screenshots/object-segment.jpg) **A road's page.** Forecast band, waterlogging class, proposals and the audit trail. | ![Citizen](docs/screenshots/citizen.jpg) **Citizen.** Bengali first, with Listen; no sign-in, no location. |

---

## Documentation

| Document | What it covers |
|---|---|
| [`PRODUCT.md`](PRODUCT.md) | The product: the Kolkata problems with sources, users and journeys, every screen, the AI and its limits, guardrails, modelled impact, cost, pilot plan, scale and roadmap |
| [`docs/TECHNICAL_DESIGN.md`](docs/TECHNICAL_DESIGN.md) | The technical design: architecture diagrams, every service, the AI services, the City Pack, the data model, APIs, flows, security, privacy, observability, deployment, testing and 15 ADRs |
| [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) | Every environment variable, by service, with defaults and secrets marked |
| [`docs/SAMPLE_DATA_AND_TESTS.md`](docs/SAMPLE_DATA_AND_TESTS.md) · [`docs/samples/`](docs/samples/) | The data Sahoshi ships, sample API answers, every test suite and 48 test cases |
| [`docs/DESIGN_NOTES.md`](docs/DESIGN_NOTES.md) · [`docs/wireframes/`](docs/wireframes/) | Visual language, Bengali typography, imagery, honest labelling in the UI, wireframes |
| [`docs/ai/`](docs/ai/) | One note per AI capability: model choice, evaluation, limits |
| [`IMPACT_REPORT.md`](IMPACT_REPORT.md) | The impact model and its assumptions ledger (MODELLED) |

---

## Licence and credits

- **Code:** MIT, © 2026 Sayandeep Haldar. See [`LICENSE`](LICENSE).
- **Road data:** © OpenStreetMap contributors, ODbL 1.0
  ([`services/corridor-store/seed/NOTICE.md`](services/corridor-store/seed/NOTICE.md)).
- **Terrain:** Copernicus DEM GLO-30, © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018, provided
  under COPERNICUS by the European Union and ESA.
- **Rain:** Open-Meteo, CC BY 4.0.
- **Photographs:** Wikimedia Commons works under their own licences (CC0, public domain, CC BY, CC BY-SA), credited
  on screen and in [`services/command-deck/static/photos/NOTICE.md`](services/command-deck/static/photos/NOTICE.md);
  the vision test photos in [`services/vision/tests/fixtures/NOTICE.md`](services/vision/tests/fixtures/NOTICE.md).
- **Marks:** agency and data-source marks belong to their owners. Sahoshi is a prototype and is not affiliated with
  or endorsed by them ([`services/command-deck/static/logos/NOTICE.md`](services/command-deck/static/logos/NOTICE.md)).
- **3D city:** Google Photorealistic 3D Tiles and Bing imagery through Cesium ion, credited on the canvas
  ([`services/command-deck/src/lib/gods-eye/NOTICE.md`](services/command-deck/src/lib/gods-eye/NOTICE.md)).
- **Fonts:** Noto Sans Bengali, Noto Sans Devanagari, Inter and JetBrains Mono, SIL OFL 1.1.
- **AI models:** each keeps its own licence (see [The AI stack](#the-ai-stack)).

## Contact

Sayandeep Haldar · [github.com/shubro18202758](https://github.com/shubro18202758). Questions, issues and pilot
enquiries: [open an issue](https://github.com/shubro18202758/sahoshi/issues).
