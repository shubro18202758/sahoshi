# Sample data

Small, real sample files from the Sahoshi services, so a reader can see what each API returns without running the
stack. Every file says where it came from in a `_sample` key at the top. Lists are trimmed (for example 3 of 65
road segments); nothing inside a kept record was edited, except that absolute paths on the build machine were
shortened to repository paths.

How they were made, on 28 Oct 2026:

- **Run locally:** the service was started on a loopback development port and called with `curl`. The twin and
  hydro ran on the CPU; the forecast ran Chronos-2 on the GPU; speech and vision answered without loading a model
  (a typed report, and two policy refusals).
- **From an evaluation file:** copied from the service's own committed evaluation results, which were produced by
  the real model.
- **From a committed data file:** an excerpt of a file the City Pack build generates.
- **Constructed:** written for this documentation and validated against the service's schema. Only one file is
  constructed, and it says so.

| File | What it shows | Provenance | Honest label in the data |
|---|---|---|---|
| [`hydro/nowcast-live-2026-10-28.json`](hydro/nowcast-live-2026-10-28.json) | `GET /hydro/nowcast`: depth-risk class 0–3, depth band, lead time and the four labelled drivers per road segment | Run locally, live Open-Meteo rain. A dry evening: every segment class 0, no proposals | rain LIVE · tide MODELLED · susceptibility MODELLED · pumps EMULATED |
| [`hydro/tide-24h-2026-10-28.json`](hydro/tide-24h-2026-10-28.json) | `GET /hydro/tide?hours=24`: the Hooghly tide at Garden Reach, high and low waters, outfall-gate state, sources | Run locally (series thinned to hourly) | MODELLED (approximate) |
| [`hydro/pumps-emulated.json`](hydro/pumps-emulated.json) | `GET /hydro/pumps`: KMC drainage pumping stations through the FFEWS adapter | Run locally | EMULATED (names and capacities real, pump states invented) |
| [`hydro/replay-2025-09-23.json`](hydro/replay-2025-09-23.json) | `POST /hydro/replay?event=2025-09-23`: the 22–23 Sep 2025 storm, two runs (Open-Meteo archive and IMD gauge-anchored), the check against places the news reported, the 02:00 IST hindsight snapshot with its reroute, ambulance-window and live-wire proposals and the Bengali/English advisory draft | Run locally (segment lists trimmed to 3) | OBSERVED rain (IMD), MODELLED shape and model, HINDSIGHT snapshot |
| [`forecast/segments-chronos2-synthetic-2026-10-28.json`](forecast/segments-chronos2-synthetic-2026-10-28.json) | `GET /forecast/segments?horizon_min=120`: p10/p50/p90 V/C and speed in 15-minute steps, the seasonal-naive baseline beside each step | Run locally, Chronos-2 on the GPU, synthetic history (3 of 65 segments; no crossing at this origin) | SIMULATED history ("forecast on simulated traffic") |
| [`twin/propose-ultadanga-1800.json`](twin/propose-ultadanga-1800.json) | `POST /twin/propose` for Ultadanga at 18:00 IST: the ranked candidates' count, the recommendation and the full proposal object (change, twin metrics, confidence, assumptions, rationale in English and Bengali) | Run locally, CPU, the LLM off (template rationale) | result MODELLED · demand SIMULATED · status PROPOSED |
| [`twin/baselines-park-circus.json`](twin/baselines-park-circus.json) | `GET /twin/baselines/park_circus`: the current program, Webster and max-pressure, each simulated | Run locally, CPU | MODELLED |
| [`speech/report-typed-bn.json`](speech/report-typed-bn.json) | `POST /speech/report` with a typed Bengali report: matched place, candidates, kind, severity, cue words | Run locally (no ASR needed for typed text) | UNVERIFIED-FIELD, `requires_confirmation: true` |
| [`speech/report-audio-eval-excerpt.json`](speech/report-audio-eval-excerpt.json) | The same endpoint on audio: the evaluation summary (WER, CER, place and kind accuracy, latency) and three clips | From `services/speech/eval/results.json` (real ASR model; synthetic audio) | UNVERIFIED-FIELD |
| [`vision/road-state-tree-fall.json`](vision/road-state-tree-fall.json) | `POST /vision/road-state`: a camera still of Shyambazar after Cyclone Amphan read as `tree_fall` | The real answer recorded in `docs/ai/vision.md` | UNVERIFIED-CAMERA, `requires_confirmation: true` |
| [`vision/eval-excerpt.json`](vision/eval-excerpt.json) | The evaluation summary, confusion, four image rows and all nine refusal probes | From `services/vision/eval/results.json` (Qwen3-VL-8B) | UNVERIFIED-CAMERA |
| [`vision/refusals-403.json`](vision/refusals-403.json) | A person question and a plate question, both refused with HTTP 403 before any model call | Run locally, no model attached | policy `vehicles-and-roads-only`, `no-plate-reading` |
| [`osint/osint-event-row.json`](osint/osint-event-row.json) | One row of `GET /api/v1/osint/events`: a waterlogging situation on Rash Behari Avenue, with its credibility, tiers, verification state and second-order flag | **Constructed** by hand from the PTI and IANS reports of 23 Sep 2025 and validated with `osint_common.types.OsintEventRow`; not a pipeline output | NEWS-REPORTED |
| [`corridor/scenario-durga-puja-north.json`](corridor/scenario-durga-puja-north.json) | A corridor scenario: Durga Puja night in north Kolkata (pandal crowds and ambulance access) | From `scripts/scenario_library.json` | SIMULATED |
| [`corridor/scenario-cloudburst-high-tide.json`](corridor/scenario-cloudburst-high-tide.json) | A corridor scenario: a cloudburst at high tide (waterlogging, pumps, live-wire hazard) | From `scripts/scenario_library.json` | SIMULATED |
| [`city-pack/network-excerpt.json`](city-pack/network-excerpt.json) | The City Pack's road network (`sahoshi.network/1`): summary, two junctions, two segments, a signal program, a camera site, a station | From `cities/kolkata/network.json` | signal programs and camera sites MODELLED; roads from OpenStreetMap |

The full City Pack is in [`cities/kolkata/`](../../cities/kolkata/). The impact model's output is
[`IMPACT_REPORT.md`](../../IMPACT_REPORT.md) and [`scripts/impact_results.json`](../../scripts/impact_results.json).
How to regenerate each file, and the test cases, are in [`../SAMPLE_DATA_AND_TESTS.md`](../SAMPLE_DATA_AND_TESTS.md).

Road network: © OpenStreetMap contributors, ODbL 1.0. Terrain: Copernicus DEM GLO-30 (© DLR e.V. 2010–2014 and
© Airbus Defence and Space GmbH 2014–2018, provided under COPERNICUS by the European Union and ESA). Rain:
Open-Meteo (CC BY 4.0).
