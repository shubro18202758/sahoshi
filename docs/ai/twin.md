# Signal-timing proposals, tested in a twin (AI capability E)

**What it does.** When a junction or corridor is under stress, now or in a
forecast, Sahoshi proposes a signal-timing change and shows the duty officer
what it is expected to do, before anyone touches a signal. The proposal is
computed and checked in a macroscopic traffic model of Kolkata (the
"twin", `services/twin`, port 8198). The officer approves or rejects it; if
no one decides, the current plan holds.

**Labels.** Twin results are MODELLED. Demand is SIMULATED unless the
traffic-oracle has live state for the city (then LIVE, or EMULATED for the
emulated feed). Signal programs are MODELLED templates. The signal adapter
is emulated.

## Flow

```
live state (oracle, GET)  ─┐
forecast crossing (cap. A) ─┼─> twin: demand -> warm-up -> do-nothing + candidates (one batched run)
junction / corridor        ─┘          -> guards -> ranking -> sensitivity (90% / 110% demand)
                                        -> proposal object (MODELLED, PROPOSED)
                                        -> rationale: local LLM explains in English and Bengali;
                                           every number checked against the twin metrics
                                        -> deck: proposal card for a named officer
                                        -> officer approves -> the platform's signal writer
                                           (traffic-oracle; snapshot, gate, restore) -- not the twin
```

The twin never writes a signal and has no client for the writer. It reads
the oracle with GET requests only.

## Why a twin, and which one

A rule like "give the busy road more green" often just moves the queue to
the cross street or to the next junction. The twin checks for that. Every
candidate runs on the whole network for 30-60 minutes against doing
nothing, and a candidate is rejected if it:

* raises delay across the network (it would only move the jam);
* raises cross-street delay by more than 25%;
* adds spill-back anywhere; or
* cuts delay at the focus by less than 3% (not worth an officer's time).

It is a **cell-transmission model** (Daganzo), the standard macroscopic
model of queues and spill-back. It is fast enough to run every candidate
over the whole city on the CPU: 30 minutes of Kolkata network v2 (49
junctions, 123 directed links, 5,979 cells) takes 0.12 s, and 20 candidates
in one batch take 0.85 s.

**Baselines** are evaluated in the same twin and also enter the proposal
ranking:
* Webster's optimal cycle and split, from the twin's own flows.
* Max-pressure control, in its cyclic form so coordination and lost time are
  kept.

`GET /twin/baselines/{junction}` shows both against the current program.

## The proposal object

| field | meaning |
|---|---|
| `junction_ids`, `junctions`, `targets` | where (`junction:<id>`, the platform's URN form) |
| `change` | `kind` (extend_green, green_wave, max_pressure, webster_retime) and a summary in English and Bengali. It also carries the programs in the platform's vocabulary (`cycle_sec`, `offset_sec`, `phases[{green_sec, movements}]`) and `revert_to` |
| `duration_min` | how long the change runs before reverting |
| `twin_metrics` | `delay_change_pct` (at the focus), `max_queue_change_m`, `cross_street_delay_change_pct`, `network_delay_change_pct`, `spillback_change_min`, with do-nothing and with-change values per approach and queue time series |
| `confidence` | whether the gain holds at 90% and 110% demand, scaled by the demand source and by whether the baseline program is assumed. A modelled heuristic, not a probability |
| `assumptions` | every modelling assumption, in plain words |
| `verification_state` | `MODELLED` |
| `requires` / `requires_officer` | `named officer approval` / `true` |
| `status`, `if_no_decision` | `PROPOSED`, `the current plan holds` |
| `rationale` | English and Bengali; `source` per language (`llm` or `template`) |

## The LLM's place

The LLM never chooses the timing; the twin and the ranking do. The local
tactical LLM (`:8084`, shared with a live system) gets the finished metrics
and writes two short sentences in English, then two in Bengali, one call at
a time with a 20 s timeout. Each reply is rejected if it:
* contains a number that is not in the twin metrics (Western or Bengali
  digits);
* is too long; or
* for Bengali, contains stray Latin words or another script.

A rejected or missing language falls back to a template that uses only
metric numbers. On the box today both languages usually come from the LLM,
about 7 s for the pair. The 12B model sometimes emits a garbage token in
Bengali, which the check catches.

## Kolkata at the evening peak (18:00 IST, 45 min horizon, SIMULATED demand)

| focus | twin answer | delay | max queue | cross street | network | confidence |
|---|---|---|---|---|---|---|
| Park Circus seven-point crossing (17; assumed program) | re-time to Webster for 30 min: cycle 110 s to 99 s, greens 50/42 to 41/40 | −9.0% | +4 m | −16.7% | −0.6% | 0.56 medium |
| Park Circus, Maa Flyover approach forecast at v/c 1.0 in 20 min | Webster re-time for 20 min (more main-road green would make it worse: +7.0%, cross street +20.1%) | −5.2% | 0 m | −11.5% | −0.4% | 0.56 medium |
| Gariahat crossing (23; assumed program, virtual cross street) | main road +6 s for 30 min | −6.6% | 0 m | +13.1% | −0.1% | 0.37 low |
| Ultadanga (33; network program) | main road +6 s for 30 min | −7.0% | 0 m | +18.5% | −0.2% | 0.47 medium |
| Exide → Tollygunge corridor (Hazra, Rashbehari, Kalighat signals) | corridor movement +6 s at 3 signals for 30 min | −14.5% | 0 m | +16.8% | −1.5% | 0.70 medium |
| (same corridor) green wave at 36 km/h | rejected: −18.7% on the corridor but network +0.4%, cross street +55.9% | | | | | |
| most stressed signal, auto-selected: Red Road north end (9; assumed) | cross street +15 s for 30 min | −56.7% | −184 m | −69.3% | −3.5% | 0.56 medium |

How to read these:
* At Park Circus the assumed split is already balanced, so moving green
  between the roads hurts one more than it helps the other. The gain comes
  from a shorter cycle, which also breaks coordination with the next
  signals, and the proposal says so.
* The large Red Road gain mostly shows that the generic template does not
  fit that junction's geometry, not that a real controller is mistimed.
  That is why proposals at junctions with assumed programs get a lower
  confidence.

## Limits

* Macroscopic; PCU only; turning ratios assumed; most crossings run an
  assumed template.
* Demand is simulated until the oracle serves Kolkata live state.
* Two-phase programs: no protected turns.
* The validator checks numbers and script, not meaning.

See `services/twin/README.md` for the equations, parameters, API and
validation results.
