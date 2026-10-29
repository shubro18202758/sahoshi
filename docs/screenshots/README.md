# Screenshots

Screenshots of Sahoshi running on the Kolkata City Pack, referenced by [`README.md`](../../README.md),
[`PRODUCT.md`](../../PRODUCT.md) and [`DESIGN_NOTES.md`](../DESIGN_NOTES.md).

How they are taken:

- From the live Sahoshi stack on the Kolkata network, with the evening `scripts/demo_reset.sh --apply` stages on the
  board: the Durga Puja night in North Kolkata and the cloudburst at high tide (both SIMULATED scenarios) and the
  stolen-vehicle sweep (EMULATED ANPR reads of the exercise plate WB06EM9001, one sighting PENDING for an officer).
  Every label stays visible on screen.
- Kolkata was dry the night they were taken (the live nowcast showed class 0 on every road), so the waterlogging
  shots use the console's replay of the 22–23 Sep 2025 storm, labelled **Hindsight**, as the console offers it.
- By `scripts/showcase/console_shots.mjs`: console screens at 1440 × 900, signed in as "Demo duty officer" (a console
  screen needs a named officer; the registration marks it shows are emulated EM-series exercise marks); the public
  pages (/citizen, /driver) at 390 × 844 (rendered at 2×, so the files are 780 × 1688) in an anonymous browser, so marks stay masked there; JPEG quality 88. The
  camera refuses every write to the live deck except the AI services' compute calls.
- The voice report is a synthetic Bengali sentence (the speech service's own TTS) played into a fake microphone and
  transcribed by the live ASR.
- Nothing edited apart from encoding.

## Files

| File | Screen | Route | What it shows |
|---|---|---|---|
| `landing.jpg` | Landing, Bengali | `/welcome` | The mark and the hero: থামিয়ে নয়, সামলে।, "Open the console" and "Check your road", the reference photo's label and credit |
| `home.jpg` | Home | `/` | The featured decision (Authorise pursuit, WB06EM9001, emulated reads), the city tiles, Next 2 hours with a signal-timing proposal waiting, the Replay 23 Sep 2025 card, the City row starting |
| `home-bn.jpg` | Home in Bengali | `/` (বাংলা) | Next 2 hours and the City row (বাতাস · গরম · ঘূর্ণিঝড় · নদী · ভূমিকম্প) in Bengali, the decision strip |
| `map-waterlogging.jpg` | Map, waterlogging layer | `/map?replay=2025-09-23` (2D city map) | Kolkata was dry, so the hindsight replay at 05:30 IST: the flagged roads of North and Central Kolkata, and Bidhan Sarani (Thanthania's road) picked — risk 2 · deep water, 10–30 cm modelled peak, first deep at 03:30, 203 mm observed, its V/C band; the evening's events live in the rail |
| `map-forecast.jpg` | Map, a road's forecast | `/map` | Bidhan Sarani picked: waterlogging risk now (dry, modelled), the +30/+60/+120 min V/C band (median with p10–p90, simulated traffic); no road crosses 0.8 V/C tonight |
| `map-air.jpg` | Map, Air layer | `/map` (2D city map) | All ten air-quality sites (AQI, modelled), the City row: Air, Heat, Cyclone, River, Quake with their labels |
| `replay-2025-09-23.jpg` | Replay of the 2025 storm | `/map` (Replay 23 Sep 2025, 2D city map) | "Hindsight: 23 Sep 2025", the time steps, the roads flagged at 04:00 IST (56 deep, 4 impassable) across Central Kolkata |
| `decide-ai.jpg` | Decide, signal-timing proposal | `/decide` | The twin's proposal for Chingrighata (Webster re-time for 30 min): delay at the junction −38.1%, cross street −18.8%, network −2.6% against doing nothing, AI proposal · Modelled · Emulated, Approve / Reject for a named officer |
| `decide-waterlogging.jpg` | Decide, waterlogging proposals | `/decide` (Exercise: 23 Sep 2025) | A reroute around water at Gariahat crossing (risk 3, > 30 cm, deep water in 45 min), tagged Exercise · Modelled · Hindsight; the ambulance-window and live-wire cards in the queue |
| `object-segment.jpg` | A road's object page | `/o/segment:1033` | Rash Behari Avenue: limit, lanes, the two-hour V/C forecast band (Chronos-2, simulated traffic), key facts |
| `voice-report.jpg` | Field report by voice | top bar → Report | A Bengali report spoken into the microphone (synthetic voice), its transcript, the matched place (Thanthania), kind, severity, the words that decided it, "unverified" |
| `road-state.jpg` | Camera road state | `/o/camera:EM-J12` | Live console, 29 Oct 2026: the camera's live reads (3 in 15 min), the Commons sample still (faces pixelated, credited) read by Qwen3-VL-8B on this server in 2.4 s: Waterlogged, water up to the wheel hubs, confidence 0.98 (uncalibrated), "Unverified camera reading", Send to the board for an officer to confirm; 1440 × 1320 so the policy line shows |
| `road-state-street.jpg` | Camera road state, real street photo | `/o/camera:EM-CAM-04` | Live console, 29 Oct 2026: "Nearby street photo", the nearest public Mapillary image (Chittaranjan Avenue, taken 6 Aug 2026, 39 m from the camera; "Reference photo · not live", CC BY-SA 4.0 credit) read by Qwen3-VL-8B on this server in 3.7 s: Clear, water below the kerb, wet surface and no standing water, confidence 0.95 (uncalibrated), "Unverified camera reading" |
| `plan.jpg` | Plan a movement | `/plan` | Nabanna → Kolkata Airport, the protection classes, departure. Finding routes registers a movement, so the shot stops here; the flagship plans the same movement through the API (`showcase/vip_plan.json`) |
| `assistant.jpg` | Assistant | `/assistant` | "Where was the stolen vehicle last read?" and a grounded, read-only answer (masked mark, demo FIR, simulated-feed note) with the decision card |
| `advisories.jpg` | Advisories | `/comms` | A draft in English, हिंदी and বাংলা, each marked SIMULATED FEED · EMULATED, "Drafted — not delivered" |
| `analyst-workspace.jpg` | Analyst workspace | `/analyst` | The map with the evening's events (Puja night, cloudburst, the sweep), the air sites, the inbox of decisions, the timeline |
| `situation-wall.jpg` | Situation wall | `/ops` | 4 active events, 9 decisions waiting (the 108 corridor, Authorise pursuit of WB06EM9001, e-challans on emulated marks), the city band, the city signal plans (writer on), the audit ladder |
| `map-3d.jpg` | 3D city | `/gods-eye` | Photoreal North and Central Kolkata from the south: the Hooghly, the evening's spines, the camera sites and the stolen vehicle's last read by Howrah Bridge; the City panel |
| `citizen.jpg` | Citizen, Bengali | `/citizen` | আজকের বাতাস (Air today, modelled, national AQI scale) with শুনুন in a synthetic voice |
| `driver.jpg` | Ambulance (108) crew | `/driver` | The one-tap green-corridor request at rest, its steps, the "scripted fallback" label |
| `imagery.jpg` | Imagery | `/v3-gallery` | Kolkata reference photos, each labelled "Reference photo · not live" with its credit |

