# IMPACT REPORT — rolling corridor holds vs blanket freeze (Kolkata)

*Generated 2026-10-28T12:24:38+00:00 by `scripts/impact_run.py` (deterministic;
re-run to regenerate). **MODELLED** — a deterministic model, not a field
measurement; see the honesty contract in the script header and the
assumptions table below.*

## What is compared

- **Baseline (today):** blanket freeze at every corridor junction for the full
  passage window — **15–45 minutes** (assumption: the range the platform is
  designed against; to be replaced by measured Kolkata movement logs); the
  model's central case uses **25 min**.
- **Platform (this repo):** predictive rolling holds — closures activated
  60–180 s ahead of the convoy, released as it passes — **~2.5 min**
  per junction.

## Network under test (Sahoshi's Kolkata road network, on real OpenStreetMap roads)

65 segments, **49 junctions**, 125.0 km
(great-circle length of the served geometry), mean 3.9 lanes —
read from the committed generator output (`scripts/data/osm_network.json`) — the network a deployed stack serves; re-run without `--offline` to read a running stack. Every segment is drawn along the real road of its name between
real intersections (City Pack `cities/kolkata/`, `scripts/gen_osm_network.py
--city kolkata`); road geometry © OpenStreetMap contributors, ODbL 1.0.
Arrival rate modelled at
**59 vehicles/min/junction** (30 veh/km/lane ×
30 km/h peak approach speed — the repo simulator's own
density default — × the mean lane count).

*Scale note: the model freezes every junction of the network under test for
one movement — the whole 65-segment city network, an upper-bound
framing kept from the original model. A single movement crosses a subset of
it; what transfers to any corridor is the per-junction figure (central case
≈ 27,476 → ≈ 275 commuter-minutes per frozen junction) and
the reduction ratio, which does not depend on the junction count.*

| Segment | Road | Class | Lanes | Speed | km |
|---|---|---|---|---|---|
| 1001 | Howrah Bridge (Rabindra Setu) | primary | 4 | 40 | 0.8 |
| 1002 | Grand Trunk Road | primary | 4 | 40 | 4.1 |
| 1003 | Vidyasagar Setu (NH12, Vidyasagar Flyover) | trunk | 4 | 60 | 3.8 |
| 1004 | Strand Road | secondary | 2 | 40 | 2.0 |
| 1005 | Strand Road | secondary | 2 | 40 | 2.1 |
| 1006 | Strand Road | secondary | 2 | 40 | 1.1 |
| 1007 | Vidyasagar Flyover Ramp | motorway | 6 | 40 | 0.7 |
| 1008 | Brabourne Road | secondary | 2 | 40 | 1.4 |
| 1009 | Old Court House Street | secondary | 2 | 40 | 1.2 |
| 1010 | Rani Rashmoni Avenue | secondary | 2 | 40 | 0.7 |
| 1011 | Esplanade - Old Court House Street link | secondary | 2 | 40 | 0.5 |
| 1012 | Sahid Khudiram Bose Road | tertiary | 2 | 40 | 0.9 |
| 1013 | Indira Gandhi Sarani (Red Road) | secondary | 2 | 40 | 0.9 |
| 1014 | Kidderpore Road | secondary | 4 | 40 | 2.1 |
| 1015 | Queensway - Cathedral Road | secondary | 2 | 40 | 1.4 |
| 1016 | Jawaharlal Nehru Road | primary | 4 | 50 | 0.2 |
| 1017 | Jawaharlal Nehru Road | secondary | 2 | 40 | 0.9 |
| 1018 | Jawaharlal Nehru Road | primary | 2 | 40 | 1.5 |
| 1019 | Ashutosh Mukherjee Road | primary | 4 | 40 | 2.0 |
| 1020 | Shyama Prasad Mukherjee Road | primary | 8 | 50 | 0.8 |
| 1021 | Shyama Prasad Mukherjee Road | primary | 8 | 40 | 0.3 |
| 1022 | SP Mukherjee Road - Deshapran Sashmal Road | primary | 8 | 40 | 1.5 |
| 1023 | Acharya Jagadish Chandra Bose Road | primary | 4 | 40 | 1.9 |
| 1024 | Acharya Jagadish Chandra Bose Road | primary | 4 | 40 | 1.6 |
| 1025 | Acharya Jagadish Chandra Bose Road | primary | 4 | 40 | 1.2 |
| 1026 | Park Street | secondary | 6 | 40 | 1.5 |
| 1027 | Mother Teresa Sarani (Park Street) | primary | 4 | 40 | 0.6 |
| 1028 | AJC Bose Road Flyover | motorway | 6 | 40 | 4.5 |
| 1029 | Maa Flyover | motorway | 4 | 40 | 3.9 |
| 1030 | Syed Amir Ali Avenue | primary | 8 | 40 | 1.7 |
| 1031 | Hazra Road | secondary | 2 | 40 | 2.1 |
| 1032 | Rash Behari Avenue | primary | 6 | 40 | 0.7 |
| 1033 | Rash Behari Avenue | primary | 6 | 40 | 1.4 |
| 1034 | Rash Behari Avenue Connector (Bijon Setu) | primary | 6 | 40 | 4.1 |
| 1035 | Eastern Metropolitan Bypass | primary | 4 | 60 | 3.2 |
| 1036 | Eastern Metropolitan Bypass | primary | 4 | 60 | 2.7 |
| 1037 | Eastern Metropolitan Bypass | primary | 8 | 60 | 1.5 |
| 1038 | Eastern Metropolitan Bypass | primary | 4 | 60 | 3.0 |
| 1039 | VIP Road (Kazi Nazrul Islam Avenue) | primary | 4 | 60 | 1.7 |
| 1040 | VIP Road (Kazi Nazrul Islam Avenue) | primary | 4 | 60 | 1.5 |
| 1041 | VIP Road (Kazi Nazrul Islam Avenue) | primary | 4 | 60 | 2.2 |
| 1042 | VIP Road (Kazi Nazrul Islam Avenue) | primary | 4 | 40 | 1.4 |
| 1043 | VIP Road (Kazi Nazrul Islam Avenue) | primary | 6 | 60 | 1.1 |
| 1044 | Salt Lake Bypass | primary | 6 | 50 | 3.7 |
| 1045 | Sector V - New Town link | primary | 4 | 50 | 3.5 |
| 1046 | Biswa Bangla Sarani | primary | 4 | 50 | 9.4 |
| 1047 | Karl Marx Sarani | secondary | 2 | 40 | 0.5 |
| 1048 | Diamond Harbour Road | primary | 4 | 50 | 2.2 |
| 1049 | Diamond Harbour Road (Majerhat bridge, Taratala flyover) | trunk | 4 | 60 | 1.4 |
| 1050 | Diamond Harbour Road | trunk | 4 | 40 | 2.7 |
| 1051 | Chittaranjan Avenue | primary | 4 | 60 | 1.9 |
| 1052 | Chittaranjan Avenue | primary | 4 | 60 | 0.9 |
| 1053 | Chittaranjan Avenue | primary | 4 | 40 | 2.4 |
| 1054 | Mahatma Gandhi Road | primary | 4 | 40 | 1.2 |
| 1055 | Mahatma Gandhi Road | primary | 4 | 60 | 0.4 |
| 1056 | Acharya Prafulla Chandra Road | primary | 4 | 40 | 1.8 |
| 1057 | Acharya Prafulla Chandra Road | primary | 4 | 40 | 1.9 |
| 1058 | Bidhan Sarani | secondary | 2 | 40 | 2.9 |
| 1059 | Vivekananda Road | primary | 4 | 40 | 1.2 |
| 1060 | Bagbazar Street | tertiary | 2 | 30 | 1.0 |
| 1061 | Strand Road - Strand Bank Road | secondary | 2 | 40 | 3.4 |
| 1062 | Radha Gobinda Kar Road - Bidhannagar Road | secondary | 2 | 40 | 2.9 |
| 1063 | Lenin Sarani | secondary | 2 | 40 | 1.7 |
| 1064 | Surendra Nath Banerjee Road | secondary | 2 | 40 | 1.7 |
| 1065 | Airport approach road | tertiary | 2 | 40 | 1.9 |


## The VIP movement corridor (central case, MODELLED)

The VIP movement the platform plans — Nabanna over Vidyasagar Setu, the AJC Bose
Road and Maa flyovers, EM Bypass and VIP Road to the airport (segments
1003, 1028, 1029, 1036, 1037, 1038, 1039, 1040, 1041, 1042, 1043, 1065; 29.0 km) — crosses
**13 junctions**. Frozen for 25 min each
the model gives **357,188 commuter-minutes** of
delay per movement; with ~2.5 min rolling holds,
**3,572**. Same model, same assumptions as
below; only the junction count is the corridor's own.

## Commuter impact per movement, whole network frozen (central case, MODELLED)

| Metric | Baseline | Platform |
|---|---|---|
| Hold per junction | 25 min | 2.5 min |
| Commuter-minutes of delay | **1,346,322** | **13,463** |
| Vehicles caught in holds | 71,804 | 7,180 |
| Fuel idled (litres) | 12,117 | 121 |
| CO₂ (kg) | 30,292 | 303 |

**Reduction in junction-freeze commuter delay: 100×**
(conservative case 15→3 min with
−40% arrivals: **25×**; optimistic 45→2 min:
**506×**). The mechanism is structural — delay scales with
hold duration **squared** — which is why even the conservative bound clears the
platform's original "6×" aspiration. *We no longer lead with "6×"; we lead with
the mechanism and this range, modelled.*

## Emergency patients (the acute case)

- 12 ambulance trips/day are modelled as crossing
  the corridor during a movement window (assumption — basis below).
- Per intersecting trip the platform returns **11 minutes**
  (assumed holds 5–20 min, midpoint 12; platform ≤ 1 min
  with an approved window).
- **≈ 132 golden-hour minutes per movement-day ·
  ≈ 33,000 per year** at 250 movement-days/yr.

## Annualised (central case, MODELLED)

- On the VIP movement corridor alone: **1,473,398 commuter-hours
  a year** (labelled movement-day assumption below).
- Upper bound, every junction of the network frozen for each movement:
  5,553,579 commuter-hours a year.
- Upper bound, fuel and CO₂: 2,998,925 litres
  of fuel and 7,497.3 tonnes
  of CO₂ avoided.

## Assumptions ledger (every number, sourced or labelled)

| Constant | Value | Source |
|---|---|---|
| Traffic density | 30 veh/km/lane | repo simulator default (`scenario_sim.py`) |
| Peak approach speed | 30 km/h | **assumption** (urban peak) |
| Baseline blanket hold | 25 min (15–45) | **assumption** (the design range; measure from movement logs) |
| Platform rolling hold | 2.5 min | platform design (60–180 s activation) |
| Discharge factor | 1.5 | **assumption** (textbook oversaturation shape) |
| Junctions frozen per movement | 49 | **assumption** (every junction of the network under test — see the scale note) |
| Ambulance trips crossing/movement-day | 12 | **assumption** (falsify with ambulance (108) dispatch data) |
| Ambulance baseline delay | 12 min (5–20) | **assumption** (range of reported VIP-movement holds; measure locally) |
| Movement-days/year | 250 | **assumption** (RTI-able; Nabanna / airport movements) |
| Idle consumption / CO₂ | 0.9 L/h · 2.5 kg/L | standard factors |

**To falsify or improve this report:** replace any assumption with measured
data and re-run `python3 scripts/impact_run.py` (a running stack) or
`python3 scripts/impact_run.py --offline` (the committed network) — the report
and `scripts/impact_results.json` regenerate deterministically.

*Road network: (c) OpenStreetMap contributors, ODbL 1.0 — https://www.openstreetmap.org/copyright.*
