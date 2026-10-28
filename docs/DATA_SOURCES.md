# Data sources

Every outside source Sahoshi reads, what it gives, and how it is labelled. Checked from the GB10 box on the night of
28–29 Oct 2026 (IST); the "State" column says what the source did when we asked it.

**The rule.** A source is in one of two buckets:

1. **Public, open or a free public service** — read **live**. If the free service needs a personal key, the code is
   wired and goes live the moment the key is in `~/.config/sahoshi/sahoshi.env` (read only from the environment,
   never printed or committed). Until then it makes no call and its health says `needs <ENV_VAR>`.
2. **Proprietary, or needs an agency's access or licence** — **simulated**, and labelled `EMULATED` (a stand-in
   for a feed) or `SIMULATED` (a scenario) wherever it shows. Never half-wired.

A public source never falls back to a recorded sample while a real route exists. When a live source fails, the
service keeps its **last live answer** and says how old it is; recorded samples answer only in offline mode, and
are labelled `RECORDED` (city feeds) or `cached-sample` (OSINT).

Labels used below: **LIVE** (a third-party feed answered), **OBSERVED** (a station's own measurement), **MODELLED**
(a model's or our computed value), **INDICATIVE** (National AQI bands applied to values that are not CPCB's AQI),
**AGGREGATE** (counts only), **OFFICIAL-VERIFIED** (an official publisher, OSINT tier), **EMULATED**, **SIMULATED**,
**UNAVAILABLE** (asked, did not answer; never shown as zero), "Reference photo · not live".

## 1. City feeds (`services/cityfeeds`, port 8199)

| Source | What it gives | Host | Key | State, 29 Oct 2026 | Label |
|---|---|---|---|---|---|
| Open-Meteo air-quality API (CAMS model) | PM2.5, PM10, NO₂, O₃ at the ten WBPCB/CPCB sites; 48-h forecast | `air-quality-api.open-meteo.com` | none | Live: HTTP 200 in 0.6 s | LIVE feed, values MODELLED, National AQI INDICATIVE |
| CPCB real-time AQI on data.gov.in | Observed pollutant averages at every CAAQMS station in Kolkata and Howrah | `api.data.gov.in` | `DATA_GOV_IN_API_KEY` | Wired; without a key the API answers 400 "Authorization field missing", so no call is made | OBSERVED (National AQI from its PM averages: INDICATIVE) |
| World Air Quality Index (aqicn.org) | Observed station AQI (US EPA scale, as WAQI publishes it) | `api.waqi.info` | `WAQI_TOKEN` | Wired; without a token: "Invalid key" | OBSERVED |
| OpenAQ v3 | Latest observed PM2.5 and PM10 per station (hourly values) | `api.openaq.org` | `OPENAQ_API_KEY` | Wired; without a key: HTTP 401 | OBSERVED |
| Open-Meteo forecast API | Temperature, humidity, heat index at Alipore and Dum Dum | `api.open-meteo.com` | none | Live: HTTP 200 | LIVE feed, MODELLED |
| GDACS (EC JRC and UN OCHA) | Cyclones and floods in the Bay of Bengal box | `www.gdacs.org` | none | Live (service health: no error; the list API is slow, 40 s+) | LIVE; distances MODELLED |
| Central Water Commission flood forecasting | Observed river levels on the DVC / lower Damodar / Hooghly stations | `ffs.india-water.gov.in` | none | Live (service health: no error) | LIVE |
| Kolkata news RSS (TOI Kolkata, Sangbad Pratidin, ABP Ananda; Millennium Post) | DVC-release mentions, counted | the outlets' own feeds | none | Live: 200 (Millennium Post answered 403 on 29 Oct; counted as not read, never as zero) | AGGREGATE |
| USGS earthquake catalogue | Quakes M ≥ 2.5 within 500 km | `earthquake.usgs.gov` | none | Live: HTTP 200 | LIVE |
| KMC public portal | Notices about places and roads | `www.kmcgov.in` | none | Live: HTTP 200; robots.txt 404 (no crawl rules) | LIVE |
| Kolkata Traffic Police home page | The department's current traffic advisories (diversions, closures) | `kolkatatrafficpolice.gov.in` | none | **Live (new):** HTTP 200, 2 current advisories. The server lacks secure renegotiation; one narrow TLS allowance for this host, certificate still verified (§5) | LIVE |
| Syama Prasad Mookerjee Port: Tidal Notices | The port's published tide notices | `smp.smportkolkata.in` | none | **Read live (new)** over a pinned exception for its expired certificate (§5). The site answers HTTP 404 "No Such URL." for the page and every content path; shown as exactly that | PUBLISHED: UNAVAILABLE (with the port's answer); tide MODELLED |
| Sahoshi hydro service | Modelled Garden Reach high and low waters | `127.0.0.1:8197` (this box) | none | Live | MODELLED |
| NASA FIRMS active fires | Satellite hotspots (VIIRS S-NPP, NOAA-20, NOAA-21, MODIS) in the Kolkata Metropolitan Area | `firms.modaps.eosdis.nasa.gov` | none; `FIRMS_MAP_KEY` optional | **Live (new), no key:** the four public South Asia 24-h files answer 200 (0.7 MB together); 0 hotspots in the metro box on 28 Oct. With the key, the area API for the box (2 days) | LIVE; each point "satellite thermal anomaly, not a confirmed fire" |
| Mapillary | A public street-level photo near a junction, for road-state stills | `graph.mapillary.com` | `MAPILLARY_TOKEN` | Wired; without a token: "Invalid OAuth 2.0 Access Token" | Reference photo · not live (CC BY-SA 4.0; faces and plates blurred by Mapillary) |

`GET /health` and `GET /feeds/summary` list each keyed source as `live`, `needs <ENV_VAR>` or `error: <reason>`.
The observed air values sit beside the modelled ones (`/feeds/air` → `observed`, and each site's `observed`); the
summary's air chip keeps its modelled value and adds `observed` (the CPCB National AQI) when a key is set.

## 2. OSINT event intelligence (`services/osint-ingress`, port 8193)

Every host is on an exact allow-list (`safe_http.ALLOWED_HOSTS`); robots.txt is honoured. Events are about places,
never persons.

| Source | What it gives | Host | Key | State, 29 Oct 2026 | Label |
|---|---|---|---|---|---|
| NDMA SACHET CAP | Official alerts, kept to West Bengal | `sachet.ndma.gov.in` | none | Live: HTTP 200 | OFFICIAL-VERIFIED |
| IMD CAP (WMO Alert Hub mirror) | IMD alerts, kept to West Bengal | `cap-sources.s3.amazonaws.com` | none | Live: HTTP 200 (empty feed) | OFFICIAL-VERIFIED |
| KMC public portal | Notice links | `www.kmcgov.in` | none | **Live again (fixed):** it failed in the service image as "robots.txt unreachable". The real cause: the server offers RSA key exchange only, which the image's Python leaves out. One narrow TLS allowance for this host; robots.txt 404 = no restriction (RFC 9309). Verified in a copy of the live image: 16 notices about places (HR circulars, hearing lists and menu links are not read) | OFFICIAL-VERIFIED |
| Kolkata Traffic Police | Current traffic advisories | `kolkatatrafficpolice.gov.in` | none | **Live (new):** 2 advisories; navigation and commented-out (withdrawn) advisories are never read | OFFICIAL-VERIFIED |
| WB Disaster Management dept. | Notices | `wbdmd.gov.in` | — | Disabled: port 443 answers plain HTTP (no TLS), http answers 503 | not read |
| Google News RSS | Kolkata headlines | `news.google.com` | none | Live: HTTP 200 | news tier |
| Outlets' RSS (TOI, Millennium Post, Sangbad Pratidin, ABP Ananda) | Kolkata headlines | the outlets' hosts | none | Live | news tier |
| GDELT 2.1 Events (bulk) | Machine-coded events for Kolkata / West Bengal | `data.gdeltproject.org` | none | Live: HTTP 200 | news tier |
| GDELT DOC 2.0 | Article list | `api.gdeltproject.org` | none | **Throttled:** HTTP 429 to this box even at 1 request per 15 min (no `Retry-After`). Now: every 30 min, jittered exponential back-off (Retry-After honoured, at most 6 h), and meanwhile the last live answer with its real fetch time and age | news tier |
| Reddit r/kolkata RSS | Public posts, aggregate only, authors dropped | `www.reddit.com` | none | Live: HTTP 200 | social, unverified |
| Common Crawl | Backfill only, never scheduled | `index.commoncrawl.org`, `data.commoncrawl.org` | none | Not scheduled (the index answered an empty reply on 29 Oct) | — |

## 3. Rain, tide and forecast (`services/hydro`, `services/forecast`)

| Source | What it gives | Host | Key | State | Label |
|---|---|---|---|---|---|
| Open-Meteo forecast (15-minute precipitation) | Rain nowcast at fixed points | `api.open-meteo.com` | none | Live (hydro health: rain feed answering) | LIVE, "model nowcast, not a gauge" |
| Open-Meteo archive | Historical rain for the 23 Sep 2025 replay | `archive-api.open-meteo.com` | none | Live: HTTP 200 | ARCHIVE (reanalysis) |
| Hooghly tide | Harmonic model from published constants (no public gauge feed) | computed | — | — | MODELLED (approximate) |
| Forecast models (Chronos-2, TimesFM) | Weights from Hugging Face, loaded offline | downloaded once | — | Offline at run time (`HF_HUB_OFFLINE=1`) | the forecast is MODELLED; its history SIMULATED unless real |

## 4. Maps and imagery (`services/command-deck`, in the browser)

| Source | What it gives | Host | Key | State | Label |
|---|---|---|---|---|---|
| OpenStreetMap raster tiles | Basemap (keyless default) | `tile.openstreetmap.org` | none | Live: HTTP 200 | "© OpenStreetMap contributors" |
| Cesium ion: World Terrain, Bing aerial, Google Photorealistic 3D Tiles | 3D city and imagery for signed-in officers | `api.cesium.com`, `*.virtualearth.net`, `tile.googleapis.com` | `SAHOSHI_CESIUM_ION_TOKEN` | Live (the token is set on this box) | "not a live image" |
| Fonts | Typefaces | committed under `static/fonts` | — | Never fetched at run time | — |

Build-time data, committed or provisioned once and never fetched by the running system: the OpenStreetMap road
network, junctions and stations (Overpass extracts under `cities/kolkata/osm/`, ODbL), waterways for flood
susceptibility, the Copernicus DEM GLO-30 tile (terrain; the derived susceptibility is MODELLED), and the reference
photos and agency logos from Wikimedia Commons ("Reference photo · not live").

## 5. The two narrow TLS exceptions

Every other host keeps full certificate verification. Neither exception switches a certificate check off.

- **`smp.smportkolkata.in` (the port).** Its GoDaddy certificate (CN `smp.smportkolkata.in`) expired on
  17 Oct 2026 06:34 UTC. For this host only, the chain and the host name are verified but the dates are not, and
  the connection is accepted only if the leaf certificate's SHA-256 fingerprint is the pinned
  `AD:4E:34:F4:B4:44:89:C6:D9:A8:05:6F:E3:C5:83:68:1A:BA:00:E0:EF:4D:CF:88:E3:C7:C4:65:CB:5E:30:16` (captured with
  `openssl s_client` on 29 Oct 2026), or the port has renewed and the new certificate is within its own dates.
  The pin and its reason are in `services/cityfeeds/src/cityfeeds/tls.py`.
- **`kolkatatrafficpolice.gov.in` (and `www.kmcgov.in` for ciphers only).** The police server does not support
  RFC 5746 secure renegotiation, which OpenSSL 3 refuses by default ("unsafe legacy renegotiation disabled"); both
  servers offer only RSA key exchange (`AES256-GCM-SHA384`). For these hosts only, the client allows legacy
  renegotiation (police) and `RSA+AESGCM` suites (both). Certificates (GeoTrust / DigiCert for the police) and host
  names are verified as usual. In `services/osint-ingress/src/osint_ingress/safe_http.py` (`TLS_COMPAT`) and
  `services/cityfeeds/src/cityfeeds/tls.py`.

No proxy, browser disguise or other way round an access control is used anywhere: every request names Sahoshi in its
user agent.

## 6. Keys you can add (all free)

Add a line to `~/.config/sahoshi/sahoshi.env` (mode 600), then restart the city feeds
(`systemctl --user restart sahoshi-feeds`). Each goes live at once; health shows `live`.

| Variable | Service | Sign up |
|---|---|---|
| `DATA_GOV_IN_API_KEY` | CPCB real-time AQI (observed, the National AQI's own inputs) | <https://data.gov.in/> (sign in; the key is under My Account) |
| `WAQI_TOKEN` | World Air Quality Index station AQI | <https://aqicn.org/data-platform/token/> |
| `OPENAQ_API_KEY` | OpenAQ v3 station measurements | <https://explore.openaq.org/register> (then Account settings → API key) |
| `FIRMS_MAP_KEY` | NASA FIRMS area API (optional; the public files already run without it) | <https://firms.modaps.eosdis.nasa.gov/api/map_key/> |
| `MAPILLARY_TOKEN` | Mapillary street-level stills (a client token) | <https://www.mapillary.com/dashboard/developers> |

## 7. Proprietary and agency feeds: simulated

These need an agency's access or a paid licence. Each is a stand-in, labelled where it shows.

| Feed | Who holds it | Stand-in | Label shown |
|---|---|---|---|
| Pumping-station and drainage sensors (FFEWS) | KMC | `services/hydro` `EmulatedFfews`: real station names, invented state | EMULATED ("Pump status is emulated") |
| Hooghly tide gauges | Syama Prasad Mookerjee Port | harmonic tide model | MODELLED (approximate) |
| Traffic detector stations (ITMS) | Kolkata Police | `signal-ingress` synthetic rows | SIMULATED FEED |
| Signal controllers (ATCS) | Kolkata Police | no adapter; timing plans are `osm_assumed` templates; approved timings are recorded, no controller changes | MODELLED; "the signal adapter is emulated" |
| Paid traffic-speed APIs (TomTom, HERE, Google) | commercial | `signal-ingress` synthetic mapping-API feed; no vendor wired | SIMULATED FEED |
| Fleet GPS / AVL, escort GPS, patrol units | operators, Kolkata Police | synthetic and emulated positions | EMULATED |
| Crowdsourced traffic reports | commercial | synthetic | SIMULATED FEED |
| ANPR / number-plate cameras and camera sites | Kolkata Police | `EmulatedAnprSource`; 21 modelled sites | EMULATED |
| CCTV video | Kolkata Police | none ingested; sample stills only | "Sample still · not live" |
| Scenario events, crowds, historical traffic | — | event emulator, forecast and twin profiles | SIMULATED / EMULATED |

One label gap was found in this check: the oracle badges junction signal entities `live` although their phase is
the stored program's clock (no controller). A one-line fix (badge them `emulated`) is proposed in
`.orchestration/patches/sources-junction-badge.patch`; the oracle's tests pass with it.

## 8. Checked and not used

- **`wbpcb.gov.in`** has no DNS record; the board's site is **`www.wbpcb.gov.in`** (answers 200). It is a
  script-only web app with no documented machine-readable air data, so the official observed route is CPCB's
  data on data.gov.in (`DATA_GOV_IN_API_KEY`).
- **`kolkatapolice.gov.in`** answers with the same legacy TLS as the traffic police; it carries recruitment and
  security notices, not traffic advisories, so it is not read.
- **`kolkataporttrust.gov.in`** and **`smportkolkata.in`** present certificates for other names; not used.
- **IMD RSMC bulletins** are PDF and text, linked rather than parsed.
