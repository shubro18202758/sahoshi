# event-emulator — the emulated half of the corridor stack (Kolkata)

An event-injection service that **emulates only causes** — Puja crowds,
station surges, marathon waves, rain and tide, cyclone tree-falls, vehicle
incidents, emergency green-corridor requests, convoy departures, ANPR
camera reads of passing vehicles and patrolling agency units — and drives
the **real stack through its real APIs**. It never produces outcomes: no
decision, parameter, situation band, e-challan or approval comes from here.
The real stack plans, classifies, escalates and degrades on its own, and a
named officer makes every decision the scenarios lead up to — a signed-in
human in a live demo (an unattended script, like the flagship showcase,
records its approvals as `Scripted demo officer (showcase script)`).

Everything it writes says what it is: scenarios are labelled SIMULATED,
events carry `metadata.source = 'event-emulator'` (and `label`), ANPR reads
are stored `source = 'emulated_anpr'`, every generated plate is a West
Bengal mark with the `EM` series (`WB02EM…`), units are `emulated_patrol`,
and the deck labels all of it EMULATED. Numbers that model the city (crowd
loads, speeds, rain rates, the tide phase, the Puja calendar) are MODELLED
assumptions, stated where they are defined; none is a real-world statistic.

## The library

`src/event_emulator/use_case_library.json` — 18 Kolkata scenarios
(`GET /api/v1/emulator/use-cases`), every one labelled SIMULATED, with
English, Bengali and Hindi names, an honest description and the
`landmarks.json` places it is about:

| id | what | event kind |
|---|---|---|
| `vvip_convoy_base` | base case: a Z+ movement Nabanna → Vidyasagar Setu → AJC Bose Road flyover → Maa Flyover → EM Bypass → VIP Road → Kolkata Airport (terminal forecourt) | protected_movement |
| `durga_puja_north` | **flagship**: Maha Ashtami night in the North Kolkata pandal belt (Kumartuli, Bagbazar, Hatibagan, College Square) with the South belt's crowds (Deshapriya Park, Ekdalia) alongside, goods vehicles off the belts, an ambulance (108) run to Kolkata Medical College | mass_gathering |
| `cloudburst_high_tide` | a cloudburst while the Hooghly is high: waterlogging spreading from Thanthania, outfalls shut, pumps lagging, a live-wire hazard advisory to the power utility as an officer-approved *proposal* | emergency_evacuation |
| `cyclone_landfall_recovery` | the morning after a cyclone: tree-falls on the arterials, staged reopening, dark signals | work_zone |
| `eden_gardens_egress` | a full house leaving Eden Gardens after a night match, towards Howrah Station and Esplanade | egress_surge |
| `howrah_surge_bridge_breakdown` | Howrah Station's evening surge and a bus broken down on Howrah Bridge | egress_surge |
| `red_road_parade` | the Republic Day / Independence Day parade on Red Road | ceremonial |
| `gangasagar_transit` | pilgrims from Howrah Station over Howrah Bridge to the Babughat camp, and the bus waves south to the Sagar Island crossings | mass_gathering |
| `kolkata_marathon` | race morning on a Red Road and riverside loop, staged reopening | race |
| `park_street_new_year` | New Year's Eve on Park Street | mass_gathering |
| `em_bypass_accident_ambulance` | a crash on EM Bypass and the ambulance (108) windows to SSKM | emergency_evacuation |
| `metro_work_zone` | published metro-works lane loss on Diamond Harbour Road (Behala – Majerhat – Kidderpore) | work_zone |
| `watchlist_anpr_sweep` | the emulated stolen-vehicle ANPR sweep (vehicles only, officer-gated) | crime_incident |
| `burrabazar_market_fire` | a market fire in the Burrabazar lanes: fire-tender green-corridor windows from C R Avenue Fire Station and the WBFES headquarters, lanes lost to tenders and the cordon, a goods-vehicle hold on the Howrah Bridge approaches and a power-isolation request as officer-approved *proposals*, an ambulance (108) window to Kolkata Medical College | emergency_evacuation |
| `dvc_release_howrah_waterlogging` | a DVC release (a SIMULATED premise, no real release figure) with rain and a high tide: Grand Trunk Road under water in Howrah, the cross-river diversion over Vidyasagar Setu, Strand Road and Howrah Bridge, each bank's officers deciding their side | emergency_evacuation |
| `kali_puja_air_quality` | Kali Puja night: SIMULATED PM2.5 readings banded indicatively, the Kalighat temple crowd and stalls, a public-health advisory and a breathing-difficulty call priority as *proposals*, ambulance (108) windows towards SSKM | mass_gathering |
| `pre_monsoon_heatwave` | a heatwave afternoon (SIMULATED temperatures against IMD's criteria): overheated vehicles on Vidyasagar Setu, the Maa Flyover and EM Bypass, recovery-van pre-positioning and shorter duty rotations as *proposals* | work_zone |
| `norwester_squall_treefall` | a Nor'wester at evening peak: trees down on EM Bypass, Red Road, AJC Bose Road and Rash Behari Avenue, an overhead wire down (an isolation request as a *proposal*), dark signals at Ultadanga, staged reopening, an ambulance (108) window to Ruby | work_zone |

Each entry carries its `scenarioConfig`; the cause-side axes come from
`profiles.py`. Route spines name segments of the Kolkata road network (the
net stream's OpenStreetMap network), each a legal directed path on it.
`tools/kolkata_library.py` writes the library from scenario specs written
in landmark keys, so a regenerated network only needs a re-run; it also
writes `tests/data/kolkata_network_slim.json`, the snapshot the tests check
routes, causes and living-city sites against. The sweep's FIR-named plate
is `WB06EM9001`; its second plate, `WB02EM4321`, is an operator exercise:
the emulator never earmarks it, so its reads hit `earmarked_plate` only
after a duty officer earmarks it (on a fresh install they are ordinary
sightings); its `expected_features` say `operator_earmark_exercise`.

## Injection seams

| Frame kind | Seam | Where the real stack consumes it |
|---|---|---|
| `event_row` | the corridor event (`events.corridor_events` + spines + phases, with its creation ledger row) and the legacy `convoy.movements` row — its route line the segments' routing lines chained in the direction of travel, its origin and destination where that line starts and ends — then `active` at t0 and `completed` at the horizon through `POST /api/v1/events/{id}/status` (C-F, actor `event-emulator (system)`) | situation engine loop, `/ops` board, citizen feed |
| `inputs_doc` | Valkey `adaptive:inputs:{id}` in the exact reader shape, plus the `corridor.traffic.emulated` Arrow plane — every row `data_quality` 2 SYNTHETIC (1 ANOMALOUS only as the congestion-outlier marker, never 0 REAL), at its segment's midpoint along the line | situation classify → hysteresis → `situation:changed` |
| `anpr_read` | `POST /api/v1/vehicles/sightings` (C-E) | the ORACLE computes the watchlist hit and the e-challan rules; the emulator asserts neither |
| `agency_unit` | NATS `corridor.units.emulated` (C-A) | oracle → Valkey `units:emulated:{unit_id}` (EX 30) → `GET /api/v1/units` |
| twin | one `POST /api/v1/simulate/twin` per run, concurrent with the frames | seeded Monte-Carlo twin; its answer is recorded compactly, never acted on |

The emulated traffic plane never becomes the live one: batches go to
`corridor.traffic.emulated` (never `.live`) with every row labelled
`data_quality` SYNTHETIC (2) on the wire — ANOMALOUS (1) only for a
congestion outlier above 0.85, the marker; never REAL (0) — and the oracle
caches them in their own key space, `traffic:emulated:latest:{sid}`,
which only EMULATED events read — emulated traffic cannot drive a real
event's band (the oracle also forces `synthetic` on ingest).

**On the road.** Every position the emulator anchors lies ON its road: a
segment's anchor is the point halfway along its routing line,
`ST_LineInterpolatePoint(geom, 0.5)` — the anchor signal-ingress gives its
feeds — never `ST_Centroid`, which on a curved OpenStreetMap road can sit
a kilometre off it; patrol paths follow the drawn line
(`COALESCE(display_geom, geom)`, C-K); a movement's route line is its
segments' routing lines oriented in the direction of travel (the
junctions recorded between consecutive segments and the one-way rule —
`tape.orient_route`), and its origin and destination are that line's ends.
The cached anchors and paths are keyed by a fingerprint of the network,
re-probed every 60 s (`store.py`), so a network converted under a running
emulator — the WP-20 conversion, a re-seed — is re-read within a minute
and a restart reads it afresh. On a fresh install: wire rows ≤ 0.006 m
from their segment, patrol units ≤ 0.066 m, movement ends 0.0 m from the
route's ends.

**The stolen-vehicle premise.** A tape that drives a FIR-named stolen plate
first makes its premise explicit at t0: `POST
/api/v1/vehicles/{plate}/earmark` with lawful basis `stolen_vehicle_fir`,
the use case's FIR and `earmarked_by` "event-emulator (system) — scenario
precondition" (reason EMULATED), unless an active stolen-FIR earmark
already exists. Its reads therefore become evidence-only
`R_STOLEN_SIGHTING` recommendations (C-N) — never a fine to the owner of a
reported-stolen vehicle. When the premise cannot be ensured, that plate's
reads are skipped and the frame log says so; they are never filed as penal.

## Runs (contract C-G)

* `POST /api/v1/emulator/runs` `{use_case_id, seed?, t0_anchor?,
  clock_scale (≤ 3600), tick_sec (1–60, default 5), deliver_nats,
  deliver_twin}` ledgers the run and answers **202** `{run_id, status:
  "running", use_case_id}` at once; the run continues as a background task.
  A second launch of a use case that is already running answers **409**
  `{detail, run_id}` naming the running run; an unknown use case is 404.
* `GET /api/v1/emulator/runs/{id}` adds `status` (`running` | `completed` |
  `stopped` | `interrupted` | `failed`), `progress` `{frame, total,
  delivered, failed, skipped, late}`, `event_id`, `movement_id` and
  `event_status`; `?include_tape=false` is the light progress poll. A
  stolen-vehicle sweep's premise (below) is on the running row as
  `spec.scenario_precondition` from the moment it is settled — mid-run,
  not only in the finished run's document.
* `POST /api/v1/emulator/runs/{id}/stop` ends a run between frames (its
  corridor event is closed through C-F, the row finishes `stopped`);
  `POST /api/v1/emulator/runs/{id}/replay` is asynchronous like a run
  (202) — see **Replay** below for when it is refused.
* Every frame fires at wall time `t0 + t_sec / clock_scale` (late frames
  fire at once, flagged late), and everything a frame stamps is wall time,
  so nothing the emulator writes sits in the future.
* Delivery is honest: every frame ends `delivered` / `failed(reason)` /
  `skipped(reason)`. The corridor event is the run's purpose, so its create
  frame counts as delivered only once the event is **live**: if the oracle
  cannot take the t0 `active` transition, the activation is retried every
  `ACTIVATE_RETRY_SEC` (5 s) of wall time, and a run whose event never
  became active ends `failed`, never `completed`. A run that delivered
  nothing is `failed`.
* Shutdown interrupts every run (`interrupted`, migration 016); a run a
  killed process could not close is reaped on the next boot (a row whose
  owner stopped heart-beating for `STALE_HEARTBEAT_SEC`, 45 s), and its
  corridor event is closed through C-F.

**Identity is run-scoped.** A ledgered run's movement / corridor-event id
is `uuid5(use_case | seed | run:{run_id})` (`tape.movement_uuid`), and each
camera read is `uuid5(use_case | seed | camera | plate | run)`
(`tape.anpr_read_uuid`) — so every run is a fresh subject and a new run
reads afresh. A **replay** re-posts the STORED tape verbatim with a
re-anchored t0 (original ids included): the oracle's ingest is idempotent
on the read id, so a replay lands as duplicates and forks nothing.

**Replay** (`runner.replay_refusal`, `api.py`, `cli.py`). A replay
re-animates the run's event on the route its tape recorded, so the route
is checked first against the CURRENT road network (`corridor.road_graph`,
one-ways included):

* a legal path → **202**, a verbatim replay; the emulator's own movement
  row is re-drawn with its origin and destination at the ends of that
  route on today's roads (an upsert that moves them, not only the
  status);
* not a legal path — a run recorded before the WP-20 conversion put the
  roads on OpenStreetMap — → **422** `{detail, reason:
  'route_not_on_current_network', run_id, use_case_id, route_segment_ids,
  problems}` before anything is ledgered or re-animated; the detail says
  to start a new run of the use case, which is built on the current
  network. It is refused rather than re-routed: a re-routed tape would be
  a new run in disguise, its camera reads timed for roads it no longer
  takes;
* the route cannot be checked (the store does not answer) → **503**;
  409 keeps its single meaning, "that use case is running".

`python -m event_emulator.cli replay` applies the same rule and exits 2
with the same message. A replay is never the God's-eye REPLAY: the deck's
REPLAY only draws a stored tape on its own clock and writes nothing.

## Determinism & provenance

* A run = `{emulation_spec, seed, t0_anchor, clock_scale}`. The cause tape
  is a pure function of (spec, seed, t0): blake2b-derived seed + a
  uniform-stream RNG; two builds with the same inputs are byte-identical.
* Runs ledger: `emulator.emulation_runs` (migrations 009 + 016: spec_hash,
  spec, seed, t0_anchor, clock_scale, status, tape JSONB).
  `simulation.runs` (006) is never written by the emulator.
* Live injections ride the same APIs as a real feed and carry no emulator
  header; the provenance rides in the rows themselves (above — the
  showcase plane's rows on their own subject, labelled SYNTHETIC) and in
  the Valkey sidecar `emulator:source:{id}`, which the engine loop reads
  to label its inputs `source='emulator'`.
  Replays carry one more tell: `X-Emulation-Replay: <run_id>` on HTTP
  requests and NATS message headers.

## Cause vocabulary (closed)

`event_row`, `inputs_doc`, `scheduled_event` (six EventTypes, incl.
`emergency_vehicle`), `event_config` (five config multipliers +
`ambulance_rate_multiplier`), `weather_ramp`, `crowd_script`, and the two
watchlist kinds `anpr_read` and `agency_unit` (`tape.CAUSE_KINDS`).
`emergency_request` is deliberately not a kind: waterlogging relief is priority
sub-event rows + scheduled `emergency_vehicle` +
`ambulance_delay_projection_sec` inputs.

## The living city (off by default)

`ambient.py` keeps Kolkata from being empty at rest: two to three
emulated causes hold stretches of road, two Kolkata Traffic Police beats
patrol, the registered ANPR cameras read passing traffic, and roughly every
25 minutes an ambulance (108) asks for a green corridor. The day program is
a pure function of (`EMULATOR_CITY_SEED`, IST date) and follows the city's
rhythm (MODELLED weights, `_kind_weights`): office peaks into and out of
BBD Bag–Esplanade and Sector V (about 09:30–11:30 and 17:30–20:00 on
working days), the Sector V / New Town IT shift changes (including the
late-evening night-shift change), school runs, morning bazaars and evening
shopping strips (Puja shopping weeks heavier), goods vehicles at night,
monsoon waterlogging (June–September) that is likelier and lasts longer
while the Hooghly is at high water (a MODELLED tide phase), Nor'wester
squalls on April–May evenings, Durga Puja nights (Saptami–Navami,
18:00–04:00) around the pandals, and Christmas–New Year evenings on Park
Street. Every slot is titled in English and Bengali at a Kolkata road or
crossing.

* **Off unless asked:** `EMULATOR_LIVING_CITY=1` starts it at boot
  (default off; an operator can also start or stop it from the deck —
  `GET/POST /api/v1/emulator/living-city`). The deck's citizen pages must
  label emulated events before it is switched on where the public can see
  it (`scripts/sahoshi_up.sh --demo` checks this).
* `EMULATOR_CITY_SEED` picks the day program (default 700001, the GPO's
  PIN code); `EMULATOR_PUJA_NIGHTS` (ISO dates of the Saptami, Ashtami and
  Navami evenings) overrides the Puja calendar when the year's almanac
  differs from `city.PUJA_NIGHTS` (2026 there is an approximation);
  `EMULATOR_LIVING_VIOLATORS=0` stops its deliberate violators (one every
  15–19 minutes, each a PENDING recommendation in the human review queue;
  default on).
* 108 requests land as dispatch rows in `requested` — never approved by
  the emulator. A request still waiting for an officer when its slot
  closes is **re-filed** on the next tick onto an open slot, with a note
  naming the request it replaces, for up to 20 minutes after 108 first
  asked; the duty officer's queue never silently loses a pending request.
* A manual or flagship run pre-empts the slots on its roads; at its first
  session the city checks its sites and beats against the live network
  and fails loudly on a mismatch.

## Health

`GET /health` probes every seam for real (store `SELECT 1`, Valkey PING,
NATS PING/PONG, oracle `/health`) and answers `status` with
`degraded_reasons`, the library size, the running runs, the last run, the
living city and the reaper's last pass. It is `degraded` whenever a seam is
down or the last run that ended on its own failed.

## Configuration and ports

| Setting | Default (`config.py`) | Notes |
|---|---|---|
| `HOST` / `PORT` | `127.0.0.1` / `8090` | loopback by default: the service writes events, sightings and Valkey docs, so it never answers on a venue LAN. The deck reaches it through its same-origin `/api/emulator` proxy. |
| `VVIP_DATABASE_URL` | none (env-only) | runners fail closed without it; credentials are never in code |
| `VVIP_VALKEY_URL`, `VVIP_NATS_URL` | set by the stack | the argus stack passes `redis://127.0.0.1:6380` and `nats://127.0.0.1:4223` (`infra/compose.argus-override.yml`) |
| `EMULATOR_TRAFFIC_ORACLE_URL` | set by the stack | the argus stack passes `http://localhost:8091`; validated by `assert_internal_endpoint` (loopback / `host.docker.internal` only) |
| `EMULATOR_DECK_ORIGINS` | the deployed deck `:5273` (+ the vite dev-server origin) | CORS for the dev server; comma-separated `http(s)://host[:port]`, fail closed on anything else |
| `EMULATOR_LIVING_CITY`, `EMULATOR_CITY_SEED`, `EMULATOR_LIVING_VIOLATORS`, `EMULATOR_PUJA_NIGHTS` | off, 700001, on, `city.PUJA_NIGHTS` | the living city, above |

In the argus stack the emulator is the compose service
`sahoshi-event-emulator` (host network, loopback :8090, `restart:
unless-stopped`), brought up by `scripts/sahoshi_up.sh`.

## Security (outbound HTTP + SQL)

* Scheme http/https only; **URLs from external input** are host-validated
  before any request — localhost, loopback, private, reserved, link-local,
  multicast and unspecified addresses are all rejected (`safe_http.py`,
  choke-pointed in `SafeHttpClient`; DNS-resolved addresses are checked,
  defeating rebinding to private IPs). No URL-valued field is accepted on
  the HTTP surface.
* **Fixed internal endpoints are config constants** enforced by
  `assert_internal_endpoint` — an env override cannot redirect the oracle
  seams at an arbitrary host.
* All SQL is parameter-bound (`%s` placeholders); no f-string, format or
  concatenated SQL exists anywhere.
* Ethics (C6): vehicles only — plates, never a person, face or frame.
  Events are about places, never people; the AI proposes and a named
  officer decides.

## Run it

```bash
# the argus stack runs it as a container: scripts/sahoshi_up.sh
# by hand (loopback :8090):
VVIP_DATABASE_URL=postgresql://corridor_admin:…@127.0.0.1:56434/corridor_db \
VVIP_VALKEY_URL=redis://127.0.0.1:6380 VVIP_NATS_URL=nats://127.0.0.1:4223 \
EMULATOR_TRAFFIC_ORACLE_URL=http://127.0.0.1:8091 \
  python -m event_emulator

# CLI
python -m event_emulator.cli list
python -m event_emulator.cli inject durga_puja_north --clock-scale 60
python -m event_emulator.cli inject cloudburst_high_tide --dry-run \
    --t0 2026-10-12T06:00:00+00:00 --tape-out tape.json
python -m event_emulator.cli replay 2 --clock-scale 60   # exit 2 when refused (Replay, above)
python -m event_emulator.cli show 2
```

## Tests

`pytest tests/` — **380 tests** collected by the gate venv on this tree
(`scripts/verify_all.sh` runs the suite): the Kolkata data — the city
pack's places, plates and calendar (`test_city.py`, which also keeps the
previous city's names, its script and the forbidden words out of the
emulator), every route a legal path on the Kolkata network snapshot
(`tests/data/kolkata_network_slim.json`) and, when the pack network is in
the tree (`cities/kolkata/network.json`, or `EMULATOR_CITY_NETWORK`), a
rebuild of the library, the profiles' segments and the living city's
sites from it (`test_kolkata_network.py`) — security (safe HTTP client),
determinism and the tape, runner delivery and activation retries, the
async task registry and reaper, the NATS seam and its wire labels, the
watchlist reads and the stolen-FIR premise (`test_sweep_earmark.py`), the
on-road geometry — route orientation (`test_route_geometry.py`), the
midpoint anchors (`test_store_unit.py`) and movements that start and end
at their route's ends (`test_runner.py`) — the replay refusal
(`test_api.py`), the living city and its Kolkata rhythm (office peaks,
the IT night-shift change, monsoon waterlogging worse at high tide,
Nor'westers, Puja nights at the pandals, the year's end on Park Street),
signal-phase parity with the oracle's own clock, and the store (the
PostgreSQL-backed tests run only against a scratch clone named by
`EMULATOR_TEST_PG_DSN` — never a live or reserved store — and skip otherwise).

## Rebuilding the library from the network

```bash
# when the Kolkata network is regenerated (new or renumbered ids):
python tools/kolkata_library.py --network ../../cities/kolkata/network.json --write
# writes src/event_emulator/use_case_library.json, src/event_emulator/kolkata_network.py
# and tests/data/kolkata_network_slim.json, after checking every route,
# patrol beat and site against the network (legal directed paths only)
```

## Declared boundaries & fidelity limits

* Reverse-flow lanes are approximated as `partial_closure` + directional
  demand (a true direction flip is an additive twin follow-on).
* Interior pedestrian dynamics are not modelled — only their vehicle-side
  pressure via `crowd_score`.
* The twin POST's additive cause fields (`weather`, `event_overrides`,
  `forced_events`) ride in the request body; the delivery level the server
  accepted is recorded per run.
* The emulator does not create convoy-brain movement contexts (Valkey
  `convoy:context:*`) — that is the brain's own API surface; emulated
  events are engine-side causes.
