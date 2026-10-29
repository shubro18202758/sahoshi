# Sahoshi — sample data and tests

This page lists the data Sahoshi ships with, the sample files in [`samples/`](samples/), every test suite with the
command that runs it and its measured total, and 48 representative test cases with what each one proves.

Everything here was measured on 28 Oct 2026 on the repository as it stood then (the Kolkata City Pack, the five AI
services and the platform services). Totals change as the code grows; the commands below reproduce them.

---

## Contents

- [Part 1 — Sample data](#part-1--sample-data)
  - [1.1 At a glance](#11-at-a-glance)
  - [1.2 The City Pack: `cities/kolkata/`](#12-the-city-pack-citieskolkata)
  - [1.3 Files generated from the City Pack](#13-files-generated-from-the-city-pack)
  - [1.4 The scenario library](#14-the-scenario-library)
  - [1.5 Waterlogging data](#15-waterlogging-data)
  - [1.6 Speech and vision evaluation sets](#16-speech-and-vision-evaluation-sets)
  - [1.7 The impact model](#17-the-impact-model)
  - [1.8 The `samples/` folder](#18-the-samples-folder)
- [Part 2 — Tests](#part-2--tests)
  - [2.1 How the gates fit together](#21-how-the-gates-fit-together)
  - [2.2 Measured totals](#22-measured-totals)
  - [2.3 Python suites](#23-python-suites)
  - [2.4 The Rust suite](#24-the-rust-suite)
  - [2.5 The command deck](#25-the-command-deck)
  - [2.6 The City Pack check](#26-the-city-pack-check)
  - [2.7 The offline acceptance ladder](#27-the-offline-acceptance-ladder)
  - [2.8 Running tests safely](#28-running-tests-safely)
- [Part 3 — Representative test cases](#part-3--representative-test-cases)
- [Part 4 — Known gaps](#part-4--known-gaps)

---

# Part 1 — Sample data

## 1.1 At a glance

| Data | Where | What it is | Label |
|---|---|---|---|
| City facts | `cities/kolkata/city.json` | Names in English, Bengali and Hindi; bbox; centre; plate format; emergency numbers; 18 agencies; hydrology notes; population (Census 2011) | Sourced |
| Canonical place names | `cities/kolkata/landmarks.json` | 48 landmarks with ids, English and Bengali names, positions | Sourced (OSM and city knowledge) |
| Curated corridors | `cities/kolkata/corridors.json` | The road corridors the network is cut from, junction seeds, name aliases, event profiles | Curated |
| OpenStreetMap extracts | `cities/kolkata/osm/*.overpass.json.gz` | Overpass extracts for the city, the airport approach and the stations | © OpenStreetMap contributors, ODbL |
| Road network | `cities/kolkata/network.json` | 49 junctions, 65 segments (125 km), 123 directed links, 6 signal programs, 21 camera sites, 50 stations | Roads real; signal programs and camera sites MODELLED |
| Store seed | `services/corridor-store/seed/*.sql` | The generated network seed and its derivations | Generated |
| Scenario library | `scripts/scenario_library.json` | 26 scenarios: Durga Puja night, cloudburst at high tide, cyclone recovery, Eden Gardens egress and more | SIMULATED |
| Waterlogging hotspots | `services/hydro/src/hydro/data/hotspots.json` | Reported waterlogging places, each with its news or official sources | Sourced (two marked unverified) |
| Susceptibility | `services/hydro/src/hydro/data/susceptibility.json` | Per-segment terrain and drainage score from Copernicus DEM, OSM drains and the hotspots | MODELLED |
| Speech evaluation | `services/speech/eval/` | 30 Bengali field-report phrases; results for five ASR checkpoints | Synthetic audio |
| Vision evaluation | `services/vision/tests/fixtures/`, `services/vision/eval/` | 12 credited public photos (faces and legible plates pixelated) with expected road states; results | Real model |
| Impact model | `IMPACT_REPORT.md`, `scripts/impact_results.json` | Rolling holds against a blanket freeze, central and bounding cases | MODELLED |
| API samples | [`samples/`](samples/) | 16 small JSON files from the services | Each states its provenance |

## 1.2 The City Pack: `cities/kolkata/`

A city is a folder. Everything specific to Kolkata lives in it, and every other city-dependent file is generated
from it (§1.3).

| File | Contents |
|---|---|
| `city.json` (schema `sahoshi.city/1`) | `name` and `region` in `en`/`bn`/`hi`; `state` (West Bengal, code `WB`); timezone `Asia/Kolkata`; centre (Esplanade / BBD Bag); bbox 22.45–22.70 N, 88.20–88.50 E; UI languages `bn`, `en`, `hi` (public pages default to `bn`); the plate format `WB NN X[X] NNNN` and its regular expression; emergency numbers 112, 100, 108 (ambulance), 101; the agencies; the Hooghly tide station and the FFEWS adapter note; population |
| `landmarks.json` | The canonical place ids every service uses (`howrah_bridge`, `park_circus`, `gariahat`, `ultadanga`, `nabanna`, `eden_gardens` …) with names in English and Bengali |
| `corridors.json` | The curated corridors: Howrah Bridge – Brabourne Road – BBD Bag, Vidyasagar Setu – Kidderpore, Chowringhee / JL Nehru Road, Park Street, AJC Bose Road, Red Road, EM Bypass, VIP Road to the airport, Biswa Bangla Sarani, Rashbehari – Gariahat, Diamond Harbour Road, APC Road, and more |
| `network.json` (schema `sahoshi.network/1`) | The compact network generated from the corridors and the OSM extracts |
| `osm/` | The committed Overpass extracts (ODbL) |

The plate rule in `city.json` notes that WB-01…WB-08 are commonly listed for Kolkata offices and WB-11/12 for
Howrah, and that Sahoshi never infers an office from a code.

## 1.3 Files generated from the City Pack

`python3 scripts/city_build.py kolkata` regenerates, deterministically and offline:

| Generated file | Reader |
|---|---|
| `services/corridor-store/seed/sample_corridor.sql` | A fresh store |
| `services/corridor-store/seed/reanchor_osm_network.sql` | The bring-up's network step (idempotent, one transaction) |
| `services/corridor-store/seed/display_geometry_osm.sql` | The display geometry |
| `scripts/data/osm_network.json`, `scripts/data/osm_network_map.json` | The evidence and the resolved table |
| `cities/kolkata/network.json` | The twin, the forecast and hydro services, the deck's city module |
| `services/signal-ingress/src/feeds/segments_kolkata.rs` | The Rust ingress (compiled in) |
| `services/traffic-oracle/src/traffic_oracle/simulation/use_case_scenarios.json` | The oracle's twin |
| `scripts/scenario_library.json` | The scenario library |

`python3 scripts/city_build.py kolkata --check` rebuilds into a temporary folder and compares; on 28 Oct 2026 it
printed `[kolkata] OK: every derived file is current` in 4.5 s. A second, reference City Pack for another city is
kept in `cities/`, and a test builds both (case T-41 below), which shows the data layer is portable.

## 1.4 The scenario library

`scripts/scenario_library.json` (format `sahoshi/scenario-library/1`) holds 26 scenarios on the Kolkata network.
Each names its route segments, departure time, protection class, closure policy, weather, forced events and the
features it is expected to show. The event emulator replays them through the real APIs, and the oracle's twin runs
them. Kolkata scenarios include:

| Scenario | Kind | Route segments |
|---|---|---|
| Durga Puja Night — pandal crowds and ambulance access | mass gathering | 1061, 1060, 1058 |
| Cloudburst at High Tide — waterlogging, pumps and live-wire hazard | emergency evacuation | 1039, 1062, 1058 |
| Cyclone Recovery — tree-falls on arterials, staged reopening | work zone | 1016–1020 |
| Eden Gardens — match-night egress | egress surge | 1012, 1004, 1001 |
| Howrah Station evening surge + Howrah Bridge breakdown | egress surge | 1051, 1054, 1001 |
| VIP Movement — Nabanna to Kolkata Airport | protected movement | 1003, 1028, 1029, 1036–1043, 1065 |
| Red Road Parade | ceremonial | 1016, 1011, 1013 |
| Gangasagar Transit — Babughat camp and the bus waves south | mass gathering | 1001, 1004–1006, 1047, 1048 |
| Kolkata Marathon — Red Road and riverside loop | race | 1012, 1013, 1014, 1006, 1005 |
| New Year's Eve on Park Street | mass gathering | 1017, 1026, 1027 |
| EM Bypass Crash — ambulance window | emergency evacuation | 1035, 1029, 1027, 1023 |
| Metro Work Zone — Diamond Harbour Road | work zone | 1050, 1049, 1048 |

Two are in [`samples/corridor/`](samples/corridor/).

## 1.5 Waterlogging data

- **Hotspots** (`hotspots.json`): Thanthania, Amherst Street, College Street, Park Circus, Kalighat, Exide, Hazra,
  Behala, Taratala, Kidderpore, Jodhpur Park, Lake Gardens, Garia, Mukundapur, Ballygunge Phari, Rashbehari Avenue,
  MG Road and Tollygunge, each with its sources (Millennium Post, PTI, IANS, Mongabay). Kasba and the Ultadanga
  underpass are kept but marked unverified.
- **Susceptibility** (`susceptibility.json`): built by `services/hydro/scripts/build_susceptibility.py` from the
  Copernicus DEM GLO-30 tile, 410 OSM waterway ways and the hotspots. Highest: Rash Behari Avenue (Gariahat) 0.78,
  MG Road (College Street) 0.78.
- **The 22–23 Sep 2025 storm**: the IMD Alipore 3-hourly totals and the peak hour are in the replay code with their
  sources; see [`ai/hydro.md`](ai/hydro.md).

## 1.6 Speech and vision evaluation sets

- **Speech** (`services/speech/eval/phrases.json`): 30 short Kolkata field-report phrases in Bengali, each with its
  expected place and kind, spoken by the service's own TTS in a female and a male voice (60 clips). Nobody was
  recorded. Results for five ASR checkpoints are in `services/speech/eval/results.json`.
- **Vision** (`services/vision/tests/fixtures/`): 12 public photos, nine from Kolkata and Howrah, with
  `labels.json` and `NOTICE.md` (credits and licences). Results, refusal probes and the output-filter
  demonstration are in `services/vision/eval/results.json`.

## 1.7 The impact model

`scripts/impact_run.py` compares a blanket junction freeze with rolling holds on the Kolkata network. It is
deterministic: `python3 scripts/impact_run.py --offline` regenerates `IMPACT_REPORT.md` and
`scripts/impact_results.json` from the committed network. Every figure is **MODELLED**, and the assumptions table
lists each constant with its source or the word "assumption". The central case for the VIP movement corridor
(Nabanna to the airport, 13 junctions): 357,188 commuter-minutes of delay per movement with a 25-minute freeze,
3,572 with 2.5-minute rolling holds.

## 1.8 The `samples/` folder

[`samples/README.md`](samples/README.md) lists 16 files: the waterlogging nowcast, tide, pumps and the 2025 replay;
a Chronos-2 forecast; a twin proposal and the Webster / max-pressure baselines; a typed Bengali field report and the
audio evaluation; a road-state reading, its evaluation and two policy refusals; an OSINT situation row; two
scenarios; and a City Pack network excerpt. Each file states how it was made.

To regenerate the run-locally samples (each service on a loopback development port of your choice):

```bash
# twin (CPU): a proposal for Ultadanga at the evening peak
cd services/twin
SAHOSHI_TWIN_PORT=9171 SAHOSHI_TWIN_NETWORK=../../cities/kolkata/network.json \
  SAHOSHI_TWIN_ORACLE_URL= SAHOSHI_TWIN_LLM=0 PYTHONPATH=src python -m sahoshi_twin &
curl -s -X POST 127.0.0.1:9171/twin/propose -H 'content-type: application/json' \
  -d '{"junction_ids":["ultadanga"],"horizon_min":45,"start":"18:00"}'

# hydro (CPU; calls Open-Meteo, no key; SAHOSHI_HYDRO_OFFLINE=1 makes no outbound call)
cd services/hydro
PYTHONPATH=src PORT=9152 python -m hydro &
curl -s 127.0.0.1:9152/hydro/nowcast
curl -s -X POST '127.0.0.1:9152/hydro/replay?event=2025-09-23'

# forecast (Chronos-2 weights in the Hugging Face cache; GPU)
cd services/forecast
HF_HUB_OFFLINE=1 PYTHONPATH=src PORT=9151 SAHOSHI_FORECAST_DATA_SOURCE=synthetic python -m forecast &
curl -s '127.0.0.1:9151/forecast/segments?horizon_min=120'

# speech: a typed report needs no model
cd services/speech
PYTHONPATH=src SPEECH_PORT=9161 SPEECH_CITY_DIR=../../cities/kolkata python -m speech_service &
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"text":"গড়িয়াহাট মোড়ে জল জমেছে, গাড়ি আটকে যাচ্ছে।"}' '127.0.0.1:9161/speech/report?lang=bn'
```

Stop each process when you are done.

---

# Part 2 — Tests

## 2.1 How the gates fit together

| Layer | What it checks | Where |
|---|---|---|
| Python unit and API suites | Every service's logic and its HTTP contract, offline (models and outbound calls mocked) | `services/*/tests/` |
| Real-model tests | The AI services against their real weights (opt-in markers) | `-m model` (forecast), `-m slow` (speech, vision) |
| Rust suite | The ingress pipeline and its plausibility checks | `services/signal-ingress` |
| Deck type check | `svelte-check` with errors as failures | `services/command-deck` |
| Deck lints | Design tokens (contrast, spacing, colour use), English copy, Bengali script | `tests/design-tokens.mjs`, `tests/copy-lint.mjs`, `tests/bn-script.unit.mjs` |
| Deck unit suites | 42 `tests/*.unit.mjs` files: masking, the gate, Decide, Home, Map, Plan, public pages, the city module | `services/command-deck/tests/` |
| Contract replay | The deck's typed client against recorded backend answers | `tests/contract/run.mjs` |
| Proxy guard | The deck's loopback proxy rules | `tests/test_deck_proxy_guard.py` |
| Compose | The compose files render | `docker compose ... config -q` |
| City Pack | Every generated file is current | `scripts/city_build.py kolkata --check` |
| Browser smokes | Screens in a headless browser against a running stack | `tests/*-smoke.mjs` |
| Acceptance ladder | All of the above in order, offline or against a live stack | `scripts/verify_all.sh` |

## 2.2 Measured totals

Measured on 29 Oct 2026 with every suite run once, offline, in parallel (about 45 s wall-clock).

| Suite | Passed | Skipped | Notes |
|---|---:|---:|---|
| traffic-oracle | 2,106 | 104 | Skips need a database sandbox |
| convoy-brain | 800 | 1 | |
| corridor-store | 153 | 30 | Skips need a database sandbox |
| event-emulator | 367 | 13 | |
| embedding-service | 191 | 4 | |
| forecast | 46 | 0 | 2 real-model tests deselected (`-m model`) |
| hydro | 26 | 0 | Open-Meteo mocked |
| speech | 219 | 4 | real-model tests skipped |
| vision | 102 | 3 | 3 real-model tests skipped |
| twin | 50 | 0 | |
| cityfeeds | 113 | 0 | every outside source mocked or replayed from a recording |
| osint-common | 449 | 0 | |
| osint-ingress | 519 | 1 | |
| osint-geo | 586 | 0 | |
| osint-analysis | 478 | 0 | |
| deck proxy guard (pytest) | 7 | 0 | |
| **Python total** | **6,212** | **160** | |
| signal-ingress (cargo) | 121 | 0 | four test binaries: 50 + 45 + 7 + 19 |
| deck unit suites | 45 of 45 files | — | |
| deck lints | design tokens, copy (4,908 English strings), Bengali script | — | all pass |
| `svelte-check` | 0 errors | — | |
| OSINT offline smoke | PASS | — | 32 signals, 26 geo-tagged, 4 situations surfaced |
| contract replay | PASS | — | 0 failures |

Every one of the 68 gates passed in that run.

## 2.3 Python suites

Each Python service carries its own `tests/` folder and runs offline. From the repository root:

```bash
cd services/<service> && python -m pytest -q -p no:cacheprovider
```

Use a Python 3.12 environment with the service's dependencies (each service has a `pyproject.toml` or
`requirements.txt`, and a Dockerfile under `infra/docker/`). The AI services also have real-model tests:

```bash
cd services/forecast && python -m pytest -q -p no:cacheprovider -m model   # Chronos-2 and TimesFM in the HF cache
cd services/vision   && VISION_SLOW=1 python -m pytest -q -m slow           # Qwen3-VL via llama.cpp (~7.6 GiB)
cd services/speech   && SPEECH_SLOW=1 python -m pytest -q -m slow            # ASR and TTS weights in the HF cache
```

Database tests in the oracle and the store skip themselves unless a sandbox store answers (the OSINT store tests
refuse any DSN other than a loopback sandbox).

## 2.4 The Rust suite

```bash
cd services/signal-ingress && cargo test --locked
```

121 tests across four test binaries: the plausibility checks (future timestamp, stale data, speed jump, phantom
reading, z-score, congestion outlier, road-class mismatch, spatial mismatch), the batcher, the Arrow encoding and
the compiled-in Kolkata segment table.

## 2.5 The command deck

From `services/command-deck` (the deck's `node_modules` must already be installed with `bun install`):

```bash
node_modules/.bin/svelte-kit sync
node_modules/.bin/svelte-check --tsconfig ./tsconfig.json --threshold error
node tests/design-tokens.mjs
node tests/copy-lint.mjs
node tests/contract/run.mjs
for u in tests/*.unit.mjs; do node "$u" || echo "FAIL $u"; done
```

The browser smokes (`tests/*-smoke.mjs`) need a running deck and a headless Chromium; each prints the URL it
expects in its header.

## 2.6 The City Pack check

```bash
python3 scripts/city_build.py kolkata --check
```

Standard library only; no network, no database. It fails if any generated file differs from what the pack
produces.

## 2.7 The offline acceptance ladder

```bash
bash scripts/verify_all.sh            # the offline tiers, in order
bash scripts/verify_all.sh --live     # adds the tiers that need a running stack
```

The offline tiers include the script syntax check, the deck tiers, every pytest suite it discovers under
`services/`, the OSINT offline smoke, cargo, the display-geometry and ingress-segment checks, and the forecaster,
routing and repetition checks of the platform's decision AI.

## 2.8 Running tests safely

- Unit suites never call a live service: outbound HTTP is mocked, and the deck's `no-live-port` suite fails if any
  browser code targets a service port directly.
- Some scripts (`scripts/verify_all.sh --live`, `scripts/journeys.mjs`, `scripts/showcase_run.sh`) default to fixed
  loopback ports that may belong to another stack on a shared machine. Export `DECK_URL`, `ORACLE_PORT`,
  `BRAIN_PORT` and `EMULATOR_PORT` for the stack you mean to test before running them
  ([`ENVIRONMENT.md`](ENVIRONMENT.md) lists every default).
- Database tests run only against a sandbox DSN on loopback.

---

# Part 3 — Representative test cases

Commands are run from the service folder named in the "Area" column (`services/<area>`), or from
`services/command-deck` for the deck and the repository root for scripts. `pytest` stands for
`python -m pytest -q -p no:cacheprovider`.

| ID | Area | What it proves | How to run | Expected |
|---|---|---|---|---|
| T-01 | twin | The cell-transmission model conserves vehicles | `pytest tests/test_ctm_physics.py::test_vehicles_are_conserved` | pass: inflow = outflow + stored |
| T-02 | twin | A queue's back moves at the kinematic-wave speed | `pytest tests/test_ctm_physics.py::test_shockwave_speed_matches_lwr` | pass: within tolerance of the LWR speed |
| T-03 | twin | A candidate that only moves the jam is rejected | `pytest tests/test_proposals.py::test_guards_reject_moving_the_jam` | pass: network delay up → not eligible |
| T-04 | twin | When nothing helps, the answer is "hold" | `pytest tests/test_proposals.py::test_hold_when_nothing_helps` | pass: recommendation `hold`, ranking explains why |
| T-05 | twin | Live state is read with GETs only and labelled | `pytest tests/test_network.py::test_live_state_is_read_only_and_labelled` | pass: no write; LIVE / EMULATED / SIMULATED label |
| T-06 | twin | An LLM rationale with a number not in the twin metrics is replaced by the template | `pytest tests/test_rationale.py::test_llm_number_not_in_metrics_falls_back_to_template` | pass: `source: template` |
| T-07 | twin | A Bengali rationale with stray Latin words or another script is rejected | `pytest tests/test_rationale.py::test_bengali_with_stray_latin_or_another_script_is_rejected` | pass |
| T-08 | hydro | The Garden Reach tide model matches published predictions for 28 Oct 2026 | `pytest tests/test_tide.py::test_garden_reach_matches_published_predictions_28_oct_2026` | pass: high waters within ~20 min, levels within 0.15 m |
| T-09 | hydro | The modelled gate closure on 23 Sep 2025 covers the closure the Mayor reported | `pytest tests/test_tide.py::test_gate_closure_on_23_sep_2025_covers_the_reported_closure` | pass: 00:15–04:30 IST covers 00:30–04:00 |
| T-10 | hydro | Bridge decks and flyovers never pond; water recedes after rain | `pytest tests/test_model_ffews.py::test_elevated_never_ponds_and_water_recedes` | pass |
| T-11 | hydro | The FFEWS stand-in labels every record EMULATED and is deterministic | `pytest tests/test_model_ffews.py::test_emulated_ffews_is_labelled_and_deterministic` | pass |
| T-12 | hydro | A storm flags segments with lead times and drafts proposals, never actions | `pytest tests/test_nowcast_replay_api.py::test_storm_flags_segments_with_lead_times_and_proposals` | pass: `requires_officer: true`, `await_officer` |
| T-13 | hydro | The 2025 replay runs both rain sources and checks against reported places honestly | `pytest tests/test_nowcast_replay_api.py::test_replay_two_runs_and_honest_check` | pass |
| T-14 | hydro | The rain client serves the cache when rate-limited | `pytest tests/test_rain.py::test_rate_limit_serves_stale_cache` | pass: at most one call per 30 s |
| T-15 | forecast | A store seeded with another city is not read as Kolkata | `pytest tests/test_oracle_covariates.py::test_engine_ignores_an_oracle_seeded_with_another_city` | pass: falls back with the reason |
| T-16 | forecast | Simulated history is labelled SIMULATED, never merged with real rows | `pytest tests/test_oracle_covariates.py::test_assemble_history_synthetic_rollup_is_labelled` | pass |
| T-17 | forecast | If the model breaks, the baseline is served and the response says so | `pytest tests/test_models_engine.py::test_engine_falls_back_to_baseline_when_model_breaks` | pass: `model_note` set |
| T-18 | forecast | The synthetic history loads pandal roads on Durga Puja nights | `pytest tests/test_synthetic.py::test_puja_nights_load_pandal_roads` | pass |
| T-19 | forecast | The forecast's tide model is identical to the hydro service's | `pytest tests/test_oracle_covariates.py::test_tide_copy_matches_hydro` | pass |
| T-20 | forecast | Chronos-2 beats the seasonal-naive baseline on the simulated history | `pytest -m model tests/test_model_real.py::test_chronos2_beats_baseline_on_simulated_history` | pass (needs the GPU and weights) |
| T-21 | speech | Uploaded audio is never stored | `pytest tests/test_api.py::test_audio_is_not_stored` | pass |
| T-22 | speech | A typed Bengali report becomes a structured, unverified field report | `pytest tests/test_api.py::test_report_from_text` | pass: `UNVERIFIED-FIELD`, place matched |
| T-23 | speech | Negated cues ("no water") do not count | `pytest tests/test_kinds.py::test_negated_cues_do_not_count` | pass |
| T-24 | speech | The pronoun "তার" is not read as a live wire | `pytest tests/test_kinds.py::test_pronoun_tar_is_not_a_live_wire` | pass |
| T-25 | speech | Every spoken alias points at a real landmark id | `pytest tests/test_places.py::test_aliases_point_at_real_landmark_ids` | pass |
| T-26 | speech | Bengali text is split for TTS at the danda (।) | `pytest tests/test_tts_unit.py::test_split_sentences_bengali_danda_and_long_runs` | pass |
| T-27 | speech | The model refuses to load below the memory floor | `pytest tests/test_runtime.py::test_refuses_below_the_memory_floor` | pass: 503, nothing loaded |
| T-28 | vision | "Who is in this image" is refused before the model is called | `pytest tests/test_api.py::test_who_is_in_this_image_is_refused_without_calling_the_model` | pass: 403, policy `vehicles-and-roads-only` |
| T-29 | vision | Plate questions are refused and routed to the ANPR path | `pytest tests/test_ethics.py::test_plate_questions_are_refused_and_routed_to_anpr` | pass: 403, `no-plate-reading` |
| T-30 | vision | The output filter removes every person sentence from real unguarded model text | `pytest tests/test_ethics.py::test_scrub_never_returns_person_terms_for_real_unguarded_model_text` | pass |
| T-31 | vision | The JSON schema allows only the known road states and depth bands | `pytest tests/test_model.py::test_schema_only_allows_known_states_and_bands` | pass |
| T-32 | vision | Every evaluation image is credited and openly licensed | `pytest tests/test_fixtures.py::test_every_image_is_credited_and_openly_licensed` | pass |
| T-33 | vision | The model server is not started when memory is low | `pytest tests/test_model.py::test_manager_refuses_to_start_when_memory_is_low` | pass |
| T-34 | traffic-oracle | Approving an e-challan on a stolen vehicle is refused | `pytest tests/test_enforcement_stolen.py::test_approving_an_e_challan_of_a_stolen_vehicle_is_409` | pass: HTTP 409 |
| T-35 | traffic-oracle | One approval authorises one pursuit | `pytest tests/test_enforcement_stolen.py::test_one_approval_authorises_one_pursuit` | pass |
| T-36 | traffic-oracle | Plates in any case or spelling never leave the server unmasked | `pytest tests/test_city_plate_mask.py::test_lower_case_dotted_and_slashed_marks_never_leave_raw` | pass: `WB06EM•••1` |
| T-37 | traffic-oracle | A signal-plan write without a named officer is refused before any write | `pytest tests/test_signals_officer.py::test_officer_required_flag_is_enforced_before_any_write` | pass |
| T-38 | convoy-brain | An unanswered proposal expires and the current plan holds | `pytest tests/test_escort_authority.py::test_no_answer_expires_and_the_convoy_holds_its_current_plan` | pass |
| T-39 | convoy-brain | Even a confident reroute waits for an officer | `pytest tests/test_escort_authority.py::test_a_confident_reroute_waits_for_the_officer` | pass |
| T-40 | corridor-store | The live City Pack rebuilds the committed files byte for byte | `pytest tests/test_city_build.py::test_the_live_pack_rebuilds_the_committed_files` | pass |
| T-41 | corridor-store | A second city builds from its own folder | `pytest tests/test_city_build.py::test_the_first_city_builds_from_its_own_folder` | pass |
| T-42 | osint-analysis | A single social post is capped at credibility 0.30 | `pytest tests/test_credibility.py::test_a_single_social_post_is_capped_at_0_30` | pass |
| T-43 | deck | The loopback proxy refuses machine ingest from a browser, before the gate and before any fetch | `python -m pytest -q tests/test_deck_proxy_guard.py::test_machine_ingest_refused_before_gate_and_fetch` | pass: 403 |
| T-44 | deck | Plates are masked in every deck rendering path until an officer is named | `node tests/plates.unit.mjs` | `ok` lines, exit 0 |
| T-45 | deck | No browser code targets a service port directly | `node tests/no-live-port.unit.mjs` | `no-live-port: all checks passed` |
| T-46 | deck | Every Bengali string pack matches English key for key and is Bengali script | `node tests/bn-script.unit.mjs` | `all bn-script checks passed` |
| T-47 | deck | Kolkata-taxi yellow is used by the landing page only | `node tests/v3-tokens.unit.mjs` | `ok` |
| T-48 | City Pack | Every generated file is current | `python3 scripts/city_build.py kolkata --check` | `[kolkata] OK: every derived file is current` |

---

# Part 4 — Known gaps

- **Real field data.** The speech evaluation uses synthetic audio, the vision evaluation uses 12 public photos, and
  the forecasts run on simulated traffic. Each service document in [`ai/`](ai/) lists what a pilot must collect.
- **End-to-end browser journeys** need a running stack, so they are not part of the offline totals above.
- **Database tests** run only when a sandbox store answers; their skips are listed in §2.2.
- **Work in progress on 28 Oct 2026**: the OSINT fixtures and the deck's use-case spines were being moved to Kolkata
  (§2.2).
