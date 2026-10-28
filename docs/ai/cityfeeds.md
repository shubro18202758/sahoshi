# City feeds (`services/cityfeeds`)

The duty officer's god's-eye picture of Kolkata needs more than roads and rain. It also needs the air the city breathes, the afternoon heat on a traffic post, the cyclone in the Bay, the Damodar coming down from the DVC dams, and the ground itself. `services/cityfeeds` brings these together from **open sources only**:

- it reads each feed on a polite schedule;
- it normalises the answer and labels every number honestly;
- it drafts **proposals** that a named officer decides.

Port: 8199 in production (loopback, `infra/systemd/sahoshi-feeds.service`); 9201 in development.

| Chip | What it shows | Source | Label |
|---|---|---|---|
| Air | The city's indicative National AQI and band (worst of ten sites), the next 48 h | Open-Meteo air-quality API (CAMS) at the WBPCB/CPCB sites, CPCB breakpoints | LIVE feed · MODELLED values · INDICATIVE AQI |
| Heat | Heat index now and its band; the 48-h peak; IMD heatwave days | Open-Meteo forecast at Alipore and Dum Dum; NWS heat index; IMD plains criteria | LIVE feed · MODELLED |
| Cyclone | Nearest active Bay of Bengal storm, distance, bearing and GDACS alert | GDACS event list and geometry | LIVE · distances MODELLED |
| River | CWC stations above their warning level; DVC release mentions in the news | CWC flood-forecasting API; Kolkata RSS | LIVE · news AGGREGATE |
| Quake | USGS events within 500 km in 30 days; the latest | USGS FDSN event service | LIVE |
| Tide | The next high water | the hydro service's tide model (the port's table could not be read) | MODELLED |

## Every feed, checked from this box (28 Oct 2026)

### Air quality (`air.py`)

- **Points:** the ten continuous ambient air-quality monitoring sites the city knows by name (CPCB lists them as "‹site›, Kolkata - WBPCB" or "‹site›, Howrah - WBPCB"):
  - Victoria Memorial
  - Rabindra Bharati University (B T Road)
  - Ballygunge
  - Fort William
  - Jadavpur
  - Bidhannagar
  - Rabindra Sarobar
  - Ghusuri (Howrah)
  - Padmapukur (Howrah)
  - Belur Math (Howrah)

  The stations' surveyed positions are not published in a form this box can read. Each point is therefore the **named site's public location**, cited per point in `STATIONS.coord_source`:
  - the landmark's Wikipedia coordinates for Victoria Memorial, Fort William, Rabindra Sarobar and Belur Math;
  - the campus for Jadavpur University and Rabindra Bharati University (B T Road);
  - the locality for Ballygunge, Bidhannagar, Ghusuri and Padmapukur.

  These positions are good to about ±1 km.
- **Values:** Open-Meteo `/v1/air-quality`, which serves the CAMS global atmospheric-composition forecast (ECMWF Copernicus). The service reads hourly PM2.5, PM10, NO₂, O₃, US AQI and European AQI, for the past 24 h and the next 48 h, in one call for all ten points.
  - **The CAMS grid is coarse.** On 28 Oct, 4 grid cells covered the ten sites, so neighbouring sites share a value. The answer says so (`grid_cells`), and the sheet repeats it.
- **National AQI:** CPCB's *National Air Quality Index* (Control of Urban Pollution Series CUPS/82/2014-15, Table 6; https://cpcb.nic.in/National-Air-Quality-Index/).
  - **Method:** each sub-index is a linear interpolation inside its band, on 24-hour means. The AQI is the larger sub-index, and that pollutant is "prominent".

    | Band | AQI | PM2.5 (µg/m³, 24 h) | PM10 (µg/m³, 24 h) |
    |---|---|---|---|
    | Good | 0–50 | 0–30 | 0–50 |
    | Satisfactory | 51–100 | 31–60 | 51–100 |
    | Moderate | 101–200 | 61–90 | 101–250 |
    | Poor | 201–300 | 91–120 | 251–350 |
    | Very poor | 301–400 | 121–250 | 351–430 |
    | Severe | 401–500 | 250+ (closed at 380) | 430+ (closed at 510) |

  - **Why it is only INDICATIVE:**
    - only PM2.5 and PM10 are used, while CPCB needs at least three pollutants, one of them PM;
    - the values are a model's, not a station's.

    The label says exactly that: "not an official CPCB AQI".
- **Forecast:** two rolling 24-h windows (0–24 h and 24–48 h) of the modelled PM. This is what makes the Kali Puja and Diwali night advisory useful a day ahead.

### Heat (`heat.py`)

- **Points:** IMD's two Kolkata observatories, Alipore (22.5361 N, 88.3311 E) and Dum Dum (22.6531 N, 88.4467 E). The values come from Open-Meteo's forecast (temperature, humidity, apparent temperature and the daily maximum).
- **Heat index:** the US National Weather Service's Rothfusz regression, with both adjustments (https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml). The bands are:
  - caution 27–32 °C;
  - extreme caution 32–41 °C;
  - danger 41–54 °C;
  - extreme danger ≥ 54 °C.
- **IMD heatwave, plains:** a heatwave needs a maximum of at least 40 °C and a departure of 4.5–6.4 °C (severe above 6.4 °C), or a maximum of at least 45 °C (severe at 47 °C or more). Source: IMD, *FAQ on Heat Wave* (https://internal.imd.gov.in/section/nhac/dynamic/FAQ_heat_wave.pdf).
  - The departure is taken from the Alipore 1991–2020 monthly mean maximum (IMD normals, as tabulated in Wikipedia, "Climate of Kolkata"). For example, May is 35.5 °C and October 32.3 °C.
  - It runs on the **forecast** maximum, so it is MODELLED, never an IMD declaration.

### Cyclones and floods (`cyclones.py`)

- **GDACS** (the European Commission JRC and UN OCHA) has an open JSON API:
  - `geteventlist/SEARCH?eventlist=TC;FL` over the last 30 days;
  - `polygons/getgeometry` per cyclone, which returns:
    - the track legs, with their category;
    - the past and forecast positions;
    - the cumulative wind buffers: green 60 km/h, orange 90 km/h, red 120 km/h;
    - the uncertainty cone.
- **Region:** an event counts as regional when its centroid lies in the box 5–28 N, 78–100 E.
- **Computed here:**
  - the distance and bearing from Kolkata;
  - the closest approach of the track;
  - whether Kolkata lies inside a wind buffer (ray casting).
- **Reliability:** GDACS's list API sometimes answers `400 Timeout expired` when its pool is busy. The client retries once, with a 45 s timeout, in the background, so no deck request waits on it.
- **IMD RSMC New Delhi** (https://rsmcnewdelhi.imd.gov.in/) is the official cyclone authority for the North Indian Ocean. Its bulletins are PDF and text pages, **not machine-readable**, so they are linked in the sheet and the pick text, not parsed.
- **On 28 Oct 2026** GDACS carried **ARNAB-26**: a Red alert, last placed at 16.4 N, 81.8 E (the Andhra coast), 972 km SW of Kolkata, with the track's closest approach 700 km. No proposal was drafted, and the service says why.

### Damodar (DVC) releases and river levels (`river.py`)

- **The CWC flood-forecasting site** (ffs.india-water.gov.in) is an Angular app over an open JSON API. Its robots.txt disallows nothing. **It is machine-readable**:
  - `iam/api/layer-station/<code>` gives the name, latitude and longitude;
  - `iam/api/flood-forecast-static/<code>` gives the warning, danger and highest flood levels and the FRL;
  - `iam/api/new-entry-data/specification/sorted-page` gives the latest observations, where datatype `HHS` is the hourly water level.
- **Stations** (CWC's own codes):

  | Station | River | Why it is here |
  |---|---|---|
  | Maithon reservoir | Barakar | DVC |
  | Tenughat reservoir | Damodar | Upper Damodar |
  | Damodar railway bridge | Damodar | Below Panchet |
  | Durgapur barrage | Damodar | DVC releases pass here |
  | Jamalpur | Damodar | Lower Damodar |
  | Harinkhola | Mundeshwari | Warning 11.8 m, danger 12.8 m |
  | Ghatal | Shilabati | |
  | Kalna | Bhagirathi-Hooghly | Warning 7.03 m |

  Panchet itself has no CWC station in the API.
- **Release volumes:** CWC publishes levels, not DVC release volumes; those are in DVC's press notes and the news. So a **news signal** counts the items of the last 72 h that mention a release.
  - **Feeds read:** the platform's reviewed Kolkata feeds: TOI Kolkata, Sangbad Pratidin and ABP Ananda Kolkata. Millennium Post's feed did not answer from this box. The feeds are read at most every 30 minutes.
  - **Terms:** in English, DVC, Damodar Valley, cusec(s), Durgapur barrage, Maithon and Panchet; in Bengali, ডিভিসি, দামোদর, কিউসেক, মাইথন and পাঞ্চেত.
  - **What is kept:** only the count, the outlet and the link. Label: AGGREGATE.
- **On 28 Oct 2026:** all eight stations answered and none was above its warning level. Harinkhola read 5.06 m (6.74 m below warning) and Durgapur barrage 64.47 m. There were 0 DVC mentions in 50 items.

### Earthquakes (`quakes.py`)

- **Source:** the USGS FDSN event service, asked server-side for M ≥ 2.5 within 500 km of the city centre over 365 days. One small call an hour.
- **Kolkata is in seismic zone III** (IS 1893 (Part 1): 2016).
- **Completeness:** the catalogue is complete over the region to about M4, so "none in 30 days" means none catalogued.
- **On 28 Oct 2026:** 0 events in 30 days and 10 in the year. The latest was M4.3, 45 km E of Tura, 407 km away (12 Jul 2026). The strongest that year was M5.4 near Tungi, Bangladesh.

### Tide table (`tide_table.py`)

- **Dropped from this box:** Syama Prasad Mookerjee Port publishes the Hooghly tide tables (with the Survey of India, from the port's gauges), but they could not be read:
  - `https://smp.smportkolkata.in/` presents a certificate this box cannot verify (curl exit 60). Certificate checks are never switched off.
  - The plain-http address answers 503 from a proxy.
  - The old `kolkataporttrust.gov.in` does not answer.
- **What the endpoint returns:** `GET /feeds/tide-table` says **PUBLISHED: UNAVAILABLE** with that reason. It shows the hydro service's **MODELLED** high and low waters (`GET :8197/hydro/tide`) instead, for example a high water of 5.98 m at 03:22 IST on 29 Oct.
- **Comparison:** `compare()` is written and tested. It pairs each published extreme with the nearest modelled one of the same kind, in minutes and metres, ready for the day a table can be read.
- **No patch to hydro:** with no published table, there is nothing for hydro to prefer, so no patch is written.

### Civic notices (`notices.py`)

- **Kolkata Police and Kolkata Traffic Police (dropped):** both sites redirect http to https, and the https connection does not complete from this box. Neither robots.txt nor the advisories can be read.
- **KMC (www.kmcgov.in):** `/robots.txt` answers 404, so there are no crawl rules. The portal home is read every 6 hours, and its downloads are kept when they are about **places and roads**: road, parking, drain, desilting, monsoon, construction, AQI and so on.
  - **Never anything about a person:** hearings, ex-gratia payments, deaths, disabilities, recruitment, councillors and the like are excluded by a second word list.
  - **On 28 Oct 2026** six notices were kept, among them the 7 Jul 2026 construction notice, the road-renaming list, the drainage activity chart and the desilting chart.
- **kmc.wb.gov.in** (the circulars page) does not answer from this box.

## The polite fetcher (`fetch.py`)

- **Limits:** each feed has a cache age, a minimum interval between refreshes and a daily cap (the table in `services/cityfeeds/README.md`).
- **Stale-while-revalidate:** once a feed has answered, an expired cache answers at once and one background refresh starts. A slow upstream never holds a deck request.
- **First request:** the first request for a feed waits at most 25 s.
- **Failures:** a failed refresh keeps the last answer, marked `stale` with the error. A feed that never answered is `UNAVAILABLE`, never zero.
- **Keep-fresh loop:** a loop touches every feed once a minute.
- **Offline mode:** `SAHOSHI_FEEDS_OFFLINE=1` makes no call. The fixtures recorded on 28 Oct 2026 (`src/cityfeeds/fixtures/`) answer, labelled `RECORDED`. To keep the fixtures clean, the news fixture keeps links and dates only, and the KMC fixture only the anchors the filter has an opinion on.

## Proposals (never actions)

Proposals have the same shape as hydro's and forecast's:

- `state: proposed`;
- `actions[]` of `{verb, target_urn, params, requires_officer: true, reversible: true}`;
- `recommendation.decision: await_officer`;
- `human_gate: {required_role: duty_officer, officer: null, decided_at: null}`.

When a trigger does not hold, the answer says why, with the threshold (`{"none": "…"}`). The deck shows it in the reader's language.

| Proposal | When | What |
|---|---|---|
| **Air health advisory** | City band Moderate or worse now, or Poor or worse within 48 h. On a **firecracker night** (Kali Puja and Diwali, 8 Nov 2026 ±1 day) Moderate within 48 h is enough. | A public advisory in বাংলা, English and हिंदी, from CPCB's band health statements. On a firecracker night it adds a line on the smoke after dark. At Poor or worse, a note to Kolkata Traffic Police: N95 masks at the busiest junction posts and shorter turns. |
| **Heat duty-shift advisory** | Heat index ≥ 41 °C (danger) within 48 h; an IMD-criteria heatwave day in the forecast; or ≥ 32 °C from April to June | Turns of at most 2 h at eight exposed posts through 11:00–16:00 IST, with water, ORS and shade, per NDMA's 2019 heat-wave guidelines: Esplanade, Park Street, Shyambazar, Ultadanga, Gariahat, Ruby, Howrah Bridge (Kolkata end) and Sealdah. Plus a citizen advisory in three languages. |
| **Cyclone pre-positioning** | Kolkata inside a GDACS wind buffer; the track within 300 km; or an Orange or Red alert within 600 km | Tree-cutting teams (KMC parks, WBSDMA, the power utility for wires) staged at the junctions of eight arterials: EM Bypass at Ruby, AJC Bose Road at Park Circus, Red Road, JL Nehru Road at Esplanade, Rash Behari Avenue, Diamond Harbour Road at Taratala, VIP Road at Kestopur and Kidderpore Road. After landfall, the roads reopen one by one. The officer decides where and when. |

## Deck surfaces

- **Proxy:** `/api/cityfeeds` → `127.0.0.1:${CITYFEEDS_PORT:-8199}`, prefix stripped (`hooks.server.ts`, and `vite.config.ts`'s `devAiProxies`). With the operator gate on, everything is denied except the citizen page's two reads: `GET /feeds/summary` and `GET /feeds/air`, with no `force`.
- **City row** (`$lib/cityfeeds/CityChips.svelte`):
  - **Where:** on the map under Rain · Tide, and on Home under "Next 2 hours".
  - **Each chip:** Air · Heat · Cyclone · River · Quake, each with its value, its band in words with a dot in the band's colour, and its honest label.
  - **Sheet:** a click opens the sheet (`FeedSheet.svelte`) with the figures, the proposal draft (or why there is none) and the sources.
- **Map layers** (both start off and are listed in the Layers sheet under "City feeds"):
  - **`air`:** the ten sites on the **existing** band ladder (`--v-band-green / -amber / -red / -black-fill`, no new colour token). A worse band also draws a larger dot, with a 450 m veil and an "AQI n" label.
  - **`cyclone`:** the GDACS buffers, track, positions and cone. It also draws a **bearing marker** at the city centre, so a storm 1,000 km away is still visible on the city map. With no active storm its row says "No active cyclone". The legend gains a line for each layer while it is on.
- **Citizen page:** "Air today" (`$lib/v3/public/AirToday.svelte`). It gives the city's band in one plain sentence and the advice, with Bengali digits, a Listen button (the shared `ListenButton`) and the Modelled tag.
- **Strings:** `$lib/cityfeeds/packs.feeds.ts`, with `.bn.ts` and `.hi.ts` complete; every Bengali sentence ends with ।.

## Live sample (28 Oct 2026, 22:04 IST, dev port 9201)

```
air      | 61 AQI          | satisfactory          | MODELLED (feed LIVE)   worst: Rabindra Bharati University (B T Road); PM2.5 24 h 37.0
heat     | 26.6 °C         | normal                | MODELLED               Alipore 25.7 °C, RH 87 %; 48-h peak heat index 37.6 °C at 11:00 IST
cyclone  | ARNAB-26        | red                   | LIVE                   972 km SW; closest approach 700 km; no proposal (too far)
river    | 0 above warning | normal                | LIVE                   8/8 CWC stations; DVC news mentions 0 in 50 items (72 h)
quake    | 0 in 30 days    | quiet                 | LIVE                   10 in 365 days; latest M4.3, 45 km E of Tura, 407 km
tide     | 5.98 m          | published_unavailable | MODELLED               next high water 03:22 IST (hydro model)
```

## Limits

- The air values are a global model's on a coarse grid. The pilot's first need is CPCB's own CAAQMS readings (data.gov.in "Real time Air Quality Index", which needs a key) or WBPCB's.
- The site positions are locality-level.
- The heatwave test uses a monthly normal, not IMD's daily normal.
- CWC levels are hourly and some stations report every 3 h. No release volume is machine-readable.
- The tide table and the traffic-police advisories cannot be read from this box.
- The KMC notices are a downloads list, not a dated feed.
