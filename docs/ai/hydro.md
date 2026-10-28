# Waterlogging nowcast (`services/hydro`)

Kolkata's roads go under within an hour of a cloudburst. It is worst when heavy rain meets a **high tide on the Hooghly**: the outfall lock gates must close, the canals surcharge and the pumps fight the river. `services/hydro` combines four drivers for every segment of the city network:

- the live rain nowcast;
- a Hooghly tide model;
- the state of the KMC pumping stations;
- terrain and drainage susceptibility.

From these it computes a **depth-risk class 0–3** with a lead time. It drafts **proposals** for each flagged road: a reroute, an ambulance window, a Bengali and English advisory, and a live-wire hazard request. A named officer decides every one of them.

| Driver | Source | Label |
|---|---|---|
| Rain | Open-Meteo forecast API, `minutely_15` precipitation at 18 fixed landmark points, past 24 h and next 2 h. No key; cached 10 min; at most one call per 30 s; daily cap. | **LIVE** (a model nowcast, not a rain gauge) |
| Tide | Harmonic model at Garden Reach, transferred from cited Diamond Harbour constants | **MODELLED (approximate)** |
| Susceptibility | Copernicus DEM GLO-30 + OSM drains and canals + reported hotspots | **MODELLED** |
| Pumps | KMC FFEWS adapter | **EMULATED** until access is granted |

Port: 8197 in production (loopback); 9152 in development.

## Tide model (`tide.py`)

No harmonic constants for Garden Reach itself are public. The Survey of India's *Hugli River Tide Tables* hold them, but they are not online. What can be cited:

- **Diamond Harbour, observed** (Khan et al. 2021, *Nat. Hazards Earth Syst. Sci.* 21:2523–2541, Supplement Table S1):

  | Constituent | Amplitude | Phase |
  |---|---|---|
  | M2 | 1.57 m | 168° |
  | S2 | 0.68 m | 210° |
  | K1 | 0.15 m | 285° |
  | O1 | 0.07 m | 258° |

  The supplement does not state the phase reference. It is read as the Greenwich lag. That reading is checked: with it, the model's Diamond Harbour high water on 28 Oct 2026 falls within an hour of a published prediction. A test enforces this.

- **The transfer to Garden Reach is MODELLED**, from published predictions and port statements:
  - **Lag:** high water arrives 2 h 38 min after Diamond Harbour, the lag between the two stations' predicted high waters on 28 Oct 2026 (tide-forecast.com).
  - **Amplitude ratio:** 0.80. The predicted ranges give 0.77. Cunningham (1904) gives a Kidderpore spring range of 12.5 ft, which against the Diamond Harbour spring range gives 0.85.
  - **Mean level:** 3.7 m above the predictions' datum.
  - **Monsoon freshet:** a monthly offset of +0.3 m in Jul and Oct and +0.6 m in Aug and Sep. The Survey of India applies freshet corrections to the Hugli tables, and Cunningham (1904) reports about 5 ft in the rains. These figures are a conservative assumption.
  - **Fitted M4 term:** amplitude 0.18 × M2, flood-dominant. Its one parameter brings the high waters onto the predictions. The same value then gives the reported ~5 h flood and ~7 h ebb, which is an independent check.
  - **Nodal corrections** use the standard Doodson/Schureman series.

- **Validation**, all enforced by tests:
  - Against the published Garden Reach predictions for 28 Oct 2026, the high waters are within about 20 minutes, the low waters within about 10 minutes, and the levels within 0.15 m.
  - On 23 Sep 2025 the model closes the gates from 00:15 to 04:30 IST. The Mayor reported "the lock gate was closed from 12.30 a.m. to 4.00 a.m.".
  - The model's next high water that day is around 14:00 IST. Reported: "the high tide which is around 1.30 PM".

- **Gate closure.** The gates are treated as shut while the level is at or above **5.0 m**. A port official quoted by The Telegraph said: "the gates need to be closed once the level crosses 5 metres".

`GET /hydro/tide` returns the series, the extremes, the gate state and the sources, labelled **MODELLED (approximate)**.

## Susceptibility (`scripts/build_susceptibility.py`, committed result `src/hydro/data/susceptibility.json`)

The build script samples every segment every ~30 m. It reads three inputs:

- **Copernicus DEM GLO-30**, tile `Copernicus_DSM_COG_10_N22_00_E088_00_DEM` from the AWS open-data bucket `copernicus-dem-30m`. © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018, provided under COPERNICUS by the European Union and ESA.
- **An OSM Overpass extract** of `waterway=canal|drain|river|stream|ditch` in the city bbox: 410 ways, OSM base 2026-10-28T10:56Z, © OpenStreetMap contributors, ODbL. A gzipped copy is kept in `scripts/data/`.
- **The sourced hotspot list** (`src/hydro/data/hotspots.json`).

Features:

- **Ground:** the 10th percentile of samples along the road. The DEM is a surface model with buildings, so a low percentile approximates the ground.
- **Neighbourhood median** within 1.5 km, and the relative elevation against it.
- **City percentile** of the ground.
- **Distance to the nearest mapped canal or drain**, and to the river.
- **Distance to the nearest reported hotspot.**

The score is MODELLED:

```
S = 0.30·(1 − city percentile) + 0.20·σ(−relative elevation / 1 m) + 0.20·min(1, d_drain / 2 km) + 0.30·exp(−d_hotspot / 400 m)
```

- An unverified hotspot counts at half weight.
- **Elevated** segments keep 15 % of their score: 1001 Howrah Bridge, 1003 Vidyasagar Setu, 1007 Vidyasagar Flyover Ramp, 1028 AJC Bose Road Flyover and 1029 Maa Flyover. Their decks do not pond, and the DEM under a bridge is the river.
- Highest-scoring roads: Rash Behari Avenue (Gariahat) 0.78, Mahatma Gandhi Road (College Street) 0.78, Chittaranjan Avenue (Girish Park) 0.77, Ashutosh Mukherjee Road (Hazra) 0.73, Syed Amir Ali Avenue (Ballygunge Phari) 0.73.

### Reported hotspots

Each hotspot in `hotspots.json` carries its sources:

| Hotspot | Sources |
|---|---|
| Thanthania, Amherst Street, College Street, Park Circus, Kalighat, Exide, Hazra, Behala, Taratala, Kidderpore, Jodhpur Park, Lake Gardens, Garia, Mukundapur, Ballygunge Phari, Rashbehari Avenue, MG Road, Tollygunge | Millennium Post 25 Oct 2024 and 22 Sep 2021; PTI via The Week 25 Oct 2024; Mongabay 31 Dec 2018 ("one of 347 identified major waterlogging pockets"); PTI and IANS Sep 2025; Millennium Post 10 Apr 2026 |
| **Kasba** and **Ultadanga underpass** | Kept but marked **unverified**: no source was located for them in this build |

## Pumps: the KMC FFEWS adapter (`ffews.py`), EMULATED

KMC is building a city Flood Forecasting & Early Warning System, with sensors in canals, pumping stations and junctions. Sahoshi has no access to it.

- `FfewsAdapter` is the interface a real feed will implement.
- `EmulatedFfews` is the stand-in used until then. Every record it returns says **EMULATED**.
- The station names are real KMC drainage pumping stations: Ballygunge, Palmer Bazar, Dhapa Lock, Ultadanga, Mominpur, Manicktala, Topsia, Chetla Lock, Jodhpur Park, Thanthania, Kalighat and Behala Flyover.
- Capacities in cusecs come from the WB Irrigation & Waterways department's "Kolkata Metropolis Drainage" list, where it gives them.
- Station positions are approximate.
- The pump counts and states are invented: a deterministic rotation in which one pump is down, and every available pump runs in rain.

`GET /hydro/pumps` shows this.

## The model (`model.py`): a conceptual ponding model, MODELLED

The model runs on 15-minute steps, for each segment:

```
C_open = C_MAX − (C_MAX − C_MIN)·S                       drainage capacity, mm/h
C(t)   = C_open · (1 − 0.5·gate(t)) · (0.6 + 0.4·a)      gates shut halve it; a = pump availability
W     ← max(0, W + (0.85·rain − C)·Δt)                   ponded water, mm
depth  = W/10 · (1 + 2·S)                                cm at the road; elevated segments: 0
```

The capacity bounds come from public statements:

| Bound | Value | Source |
|---|---|---|
| `C_MIN` | 6 mm/h | The old network was designed for "one-fourth of an inch rainfall per hour" (KMC blog, 2015). The Mayor in 2019: "capable of draining water when it rains 6 mm in an hour". |
| `C_MAX` | 20 mm/h | The Mayor in Oct 2024: "can only drain 20 mm of water in an hour". |

The gate cut (0.5), the pump floor (0.6), runoff (0.85) and concentration (2) are stated assumptions.

| Class | Depth | Meaning |
|---|---|---|
| 0 | 0–2 cm | Dry |
| 1 | 2–10 cm | Shallow |
| 2 | 10–30 cm | Deep: small cars and two-wheelers stall, ambulances slow, live-wire danger |
| 3 | > 30 cm | Impassable for most vehicles |

**Lead time** is reported two ways:

- `lead_time_min`: minutes until the segment first reaches its peak class within the horizon;
- `lead_time_deep_min`: minutes until it first reaches class 2.

## API

| Route | What it returns |
|---|---|
| `GET /health` | Labels, rain-feed state (calls today, cache age), network, susceptibility build, tide now |
| `GET /hydro/nowcast` | For each segment: `risk_class`, `risk_class_now`, `expected_depth_band`, `modelled_peak_depth_cm`, `lead_time_min`, `lead_time_deep_min`, and `drivers.{rain,tide,susceptibility,pumps}` each with its label. Also class counts, the flagged list and the proposals. |
| `GET /hydro/tide?hours=1..72` | The tide model's output (MODELLED) |
| `GET /hydro/rain` | The Open-Meteo nowcast at the 18 points and the city mean (LIVE) |
| `GET /hydro/pumps` | Station state (EMULATED) |
| `POST /hydro/replay?event=2025-09-23` | The 22–23 Sep 2025 replay (below) |

### Proposals (never actions)

All proposals are in the decision-support shape: `state: proposed`, `actions` with `requires_officer: true`, `recommendation.decision: await_officer`, and a `human_gate` with no officer. They are generated for each flagged segment (risk ≥ 2):

- **Reroute** (`waterlogging_reroute`): a detour on the city network that avoids other flagged roads where it can.
- **Ambulance window** (`ambulance_window`): a note for ambulance (108) crews giving the minutes the road stays passable and the detour.
- **Live-wire hazard** (`live_wire_hazard`, `for_officer_approval: true`): a request that the power utility (CESC / WBSEDCL) inspect and, where needed, isolate supply along the road. On 22–23 Sep 2025 most of the deaths in Kolkata were electrocutions (PTI: "nine of them due to electrocution").
- **One public advisory draft** (`public_advisory_draft`) in Bengali and English. It uses Western digits, as the glossary requires in the console.

## Replay: 22–23 September 2025

**What happened.** IMD RMC Kolkata's press release of 23 Sep 2025 reported:

- 251.4 mm at Alipore in the 24 h to 08:30 IST. Reuters reported 251.6 mm, the heaviest since 1988.
- 3-hourly totals:

  | Window (IST) | Rain |
  |---|---|
  | 20:30–23:30 | 2.5 mm |
  | 23:30–02:30 | 48.6 mm |
  | 02:30–05:30 | 185.6 mm |
  | 05:30–08:30 | 12.1 mm |

- The peak hour was **98 mm between 03:00 and 04:00 IST**.
- KMC gauges recorded up to 332 mm (Garia Kamdahari), as reported by News Arena on 23 Sep 2025.

`POST /hydro/replay?event=2025-09-23` runs the same model over 18:00 IST on 22 Sep to 14:00 IST on 23 Sep in two ways:

- the tide is MODELLED for those dates;
- pumps are all available. Millennium Post (24 Sep 2025): "All 82 pumping stations … were operational".

### Run A, Open-Meteo historical archive (the brief's run)

This run uses hourly precipitation from the archive (`best_match`, reanalysis/NWP based) at the 18 points. They fall into 7 grid cells.

**Result:** the archive carries **20.5 mm** (city mean) and **27.9 mm** at its wettest point over the window. IMD measured 248.8 mm at Alipore in the same hours. With that rain the model flags **no segment**: 0 of 65, and 0 of the 13 reported places on the network.

Gridded reanalysis and global NWP do not resolve this storm. We checked ERA5, ECMWF IFS, and the historical-forecast archives of IFS 0.25°, GFS and ICON at central-Kolkata points: they gave 24–57 mm over the 48 h of 22–23 Sep. ERA5-Land returned no rain at all. A nowcast fed only by such a product would have missed the night. This is the case for wiring KMC's own gauges, through FFEWS, into the pilot.

### Run B, IMD gauge-anchored (the same model, observed rain)

This run drives the model with IMD's Alipore 3-hourly totals and peak hour, which are OBSERVED.

- **Shape within each window (MODELLED):**
  - 23:30–02:30 ramps up 1 : 2 : 3 by hour;
  - in 02:30–05:30, the 03:00–04:00 hour carries the reported 98 mm, and the remaining 87.6 mm is split 25 % (02:30–03:00), 55 % (04:00–05:00) and 20 % (05:00–05:30).
- **Scaling in space:** by KMC's station 24-h totals relative to Alipore's 247.5 mm, interpolated (IDW) from approximate gauge positions.

**Results:**

- Alipore window total 248.8 mm; peak 98 mm/h.
- Peak classes: 0 for 5 segments (all five are the elevated decks), 2 (deep) for 43, and 3 (impassable) for 17.
- **The first flag (class ≥ 2) is at 02:45 IST**, on segment 1033 (Rash Behari Avenue → Gariahat crossing). It comes before the 03:00–04:00 peak hour. Rashbehari Avenue, Gariahat and Maddox Square all include that segment among their matches.
- Peak depths are reached around 05:30.
- The class-3 roads are: Rash Behari Avenue (Gariahat, Deshapriya Park), Ashutosh Mukherjee Road (Hazra), SP Mukherjee Road (Rashbehari, Kalighat), Syed Amir Ali Avenue and Hazra Road (Ballygunge Phari), JL Nehru Road and Queensway (Exide), AJC Bose Road (Mullickbazar), Mother Teresa Sarani (Park Circus), Rash Behari Avenue Connector (Ruby), Karl Marx Sarani (Kidderpore), Diamond Harbour Road (Majerhat, Behala), Chittaranjan Avenue (Girish Park) and MG Road (College Street).

**Against the places the news reported waterlogged** (sources inside the replay output):

| Reported place | Source | On the network? | Flagged | First class ≥ 2 (IST) | Max class |
|---|---|---|---|---|---|
| EM Bypass | PTI (Tribune) 23 Sep; MPost 25 Sep | yes | yes | 03:15 | 2 |
| AJC Bose Road | PTI | yes | yes | 03:15 | 3 |
| Central Avenue (Chittaranjan Ave) | PTI | yes | yes | 03:15 | 3 |
| Rashbehari Avenue | PTI; IANS | yes | yes | 02:45 | 3 |
| Park Circus | PTI; IANS; MPost | yes | yes | 03:00 | 3 |
| Gariahat | PTI | yes | yes | 02:45 | 3 |
| Behala | PTI | yes | yes | 03:15 | 3 |
| College Street | PTI; IANS; Mongabay | yes | yes | 03:15 | 3 |
| Thanthania | IANS; MPost | yes | yes | 03:15 | 3 |
| Amherst Street | MPost 25 Sep | yes | yes | 03:15 | 3 |
| Ballygunge Phari | IANS; MPost; Down To Earth | yes | yes | 03:00 | 3 |
| Shakespeare Sarani | MPost 25 Sep | yes | yes | 03:15 | 3 |
| Maddox Square | Down To Earth | yes | yes | 02:45 | 3 |
| Topsia, Garia, Jodhpur Park, Lake Gardens, Kankurgachi underpass, Netaji Nagar, Palmer Bazar | PTI; IANS; MPost; DTE; Mongabay | **off the network** (no at-grade segment within 600 m) | not scored | — | — |

**Hit rate: 13 of 13 on-network reports flagged.** How to read this honestly:

- Almost the whole city was under water that night. The model flags 60 of 65 segments, so the hit rate shows the model is not blind to the event. It does not show fine discrimination.
- News reports name places, not every street. A flag with no report is **not** counted as a false alarm.
- Gauge positions are approximate.

**A hindsight snapshot at 02:00 IST.** This snapshot uses the observed rain as if it had been a perfect nowcast. It is labelled HINDSIGHT.

- 60 segments are flagged within the 120-minute horizon, and none yet at 02:00.
- **Time to deep water:** 45 min at the earliest, 90 min median, 120 min at the latest.
- 60 reroute, 60 ambulance-window and 60 live-wire proposals, plus one advisory draft. For example:

> Gariahat crossing (Rash Behari Avenue): waterlogging risk 3 (> 30 cm), deep water in about 45 min; no detour on the city network that avoids flagged roads — propose closing to small vehicles with officer judgement on site.

> ট্রাফিক পরামর্শ (খসড়া): আগামী 120 মিনিটের মধ্যে এই জায়গাগুলিতে জল জমার আশঙ্কা: গড়িয়াহাট মোড়, হাজরা মোড়, বালিগঞ্জ ফাঁড়ি, দেশপ্রিয় পার্ক মোড়, এক্সাইড মোড়, রাসবিহারী মোড়। সম্ভব হলে এই পথগুলি এড়িয়ে চলুন। জমা জলে বিদ্যুতের খুঁটি বা তার ছোঁবেন না। জরুরি প্রয়োজনে 112; অ্যাম্বুলেন্স (108)।

### Sources for the replay

| Source | Date | Link |
|---|---|---|
| IMD RMC Kolkata press release | 23 Sep 2025 | https://internal.imd.gov.in/press_release/20250923_pr_4321.pdf |
| Reuters via Dawn | 24 Sep 2025 | https://www.dawn.com/news/1944310 |
| PTI via The Tribune | 23 Sep 2025 | https://www.tribuneindia.com/news/india/heavy-rain-paralyses-kolkata-5-dead-in-rain-related-incidents/amp |
| IANS via Reporter Post | 24 Sep 2025 | https://reporterpost.in/article/nation/40938/kolkata-battles-waterlogging-as-torrential-rain-claims-10-lives |
| Millennium Post | 24 Sep 2025 | https://www.millenniumpost.in/bengal/kmc-drains-flooded-city-on-war-footing-628674 |
| Millennium Post | 25 Sep 2025 | https://www.millenniumpost.in/bengal/most-city-streets-cleared-of-water-except-added-areas-kmc-628812 |
| Down To Earth | 24 Sep 2025 | https://www.downtoearth.org.in/climate-change/unexpected-interaction-of-atmospheric-conditions-not-cloudburst-caused-kolkatas-intense-180mm-rainfall-in-3-hours-says-imd |
| News Arena, KMC station-wise totals | 23 Sep 2025 | https://newsarenaindia.com/nation/torrential-rain-disrupts-kolkata-ahead-of-durga-puja-5-dead/57263 |
| Mongabay India | 30 Sep 2025 | http://india.mongabay.com/2025/09/intense-rainfall-spotlights-the-fault-in-kolkatas-aging-clogged-drainage-systems/ |
| IANS via The Weekend Leader, the Mayor on the lock gates | 23 Sep 2025 | https://www.theweekendleader.com/Headlines/80522/kolkata-hit-by-cloudburst-7-electrocution-deaths-train-and-metro-services-disrupted.html |

## Live nowcast sample (28 Oct 2026, 17:02 IST, dev port 9152)

- **Rain:** Open-Meteo, LIVE, 18 points. 0 mm/h now; 1.6 mm in the past 3 h on Chittaranjan Avenue (segment 1052).
- **Tide** (MODELLED): 4.81 m and falling, gates open. Next high water 03:22 IST at 5.98 m.
- **Result:** all 65 segments class 0, nothing flagged, no proposals. It was a dry late-October evening.
- **Example drivers, segment 1052 (Chittaranjan Avenue → Girish Park):**
  - susceptibility 0.772 (ground 6.2 m; 78 m from the MG Road hotspot);
  - pumps EMULATED (Thanthania station, 9 of 9 available).

## Limits and what is not done

- **Rain:** the nowcast is a model product. Over India, Open-Meteo's 15-minute field may be interpolated from hourly models. The replay shows how badly gridded products can miss a convective night. A rain-gauge feed, KMC FFEWS or IMD AWS, is the first thing the pilot needs.
- **Tide:** an approximate transfer, not the Survey of India constants. The datum is that of the third-party predictions. The freshet offsets are assumptions.
- **Susceptibility:** the DEM is a surface model with buildings, and the hotspots are positioned by hand (±300 m). Drain capacity and blockage are unknown.
- **Pumps:** EMULATED. Station positions are approximate.
- **The model:** a conceptual bucket model with stated parameters, not a hydraulic sewer model (SWMM). It is not calibrated beyond the 2025-09-23 replay.
- **Network:** 65 arterial segments. Many reported places are off it.
- **Not built:** the PLAN's regional SAR flood-extent row (Prithvi-EO-2.0 on Sentinel-1) is not part of this service. The brief did not ask for it.
