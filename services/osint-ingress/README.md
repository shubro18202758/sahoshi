# osint-ingress (:8193)

Turns open sources into canonical, already-redacted `RawOsintSignal` records (`osint_common.types`, contract
X18) and posts them to the oracle's loopback machine-ingest route `POST /api/v1/osint/signals` (contract C-T).
Events are about places and situations, never persons.

## Run

```bash
PYTHONPATH=src:../osint-common/src:../osint-geo/src:../osint-analysis/src python -m osint_ingress serve
python -m osint_ingress once [--offline] [--cache-dir D] [--oracle URL] [--dry-run] [--report out.json] [--backfill] [--only a,b]
python -m osint_ingress import-poc <capture_dir> <cache_dir>
```

Exit codes: 0 ok, 2 usage (a non-loopback oracle URL or an unknown `--only` connector included; caught before
anything is built or probed), 3 pipeline libraries missing (`--dry-run`).
`once` probes the oracle first; when it is unreachable nothing is posted, the batches stay in the cache outbox,
the report says `publish: "skipped: oracle unreachable"` and the exit code is 0. `--dry-run` runs
`osint_analysis.pipeline.run_pipeline` with the `osint_geo` resolver in-process and prints `MACHINE_RESULT={...}`.

Environment: `OSINT_ORACLE_URL` (loopback only; unset: `http://127.0.0.1:9`, the discard port), `HOST` (`127.0.0.1`), `PORT` (`8193`),
`OSINT_CACHE_DIR` (`/var/cache/osint-ingress`), `OSINT_MODE` (`live` | `offline`), `OSINT_GAZETTEER_PATH`,
`OSINT_CADENCE_<CONNECTOR>_SEC` (0 takes a connector off the schedule; values under 60 s are raised to 60 s).
The service reads no secret and writes nothing but its cache. `OSINT_ORACLE_URL` has no usable default: unset, it is
the discard port `:9`, so a run that names no oracle posts nowhere (its batches wait in the outbox) and never
reaches the live oracle by accident. The deployment names its oracle explicitly; a harness names a sandbox oracle.

## Routes

- `GET /health`: `{status, mode, version, oracle{host, reachable, last_post_at, last_post_status},
  connectors{<name>{enabled, cadence_sec, last_run_at, last_ok_at, fetch_mode, signals, error, cache_age_sec}},
  last_cycle{at, signals, accepted, rejected, geotagged, surfaced, pii_redactions}, egress_allowlist}`.
  `oracle.reachable` comes only from a `GET {oracle}/health` probe (start-up, then every 30 s). A connector its
  source disables ("robots.txt disallows") shows `enabled: false` with that `error`, and its cache is not served.
- `POST /cycle` (loopback callers only): one cycle now; returns the `last_cycle` object.

## Connectors and schedule

| source | cadence | endpoint |
|---|---|---|
| `sachet_cap` | 5 min | NDMA SACHET **all-India** CAP RSS, kept to West Bengal (below), plus the CAP 1.2 detail of new West Bengal alerts |
| `imd` | 10 min | IMD's CAP alerts via the WMO Alert Hub mirror (`cap-sources.s3.amazonaws.com/in-imd-en/`), kept to West Bengal |
| `google_news_rss` | 10 min | Google News RSS search, English (`hl=en-IN`) and Bengali (`hl=bn`) Kolkata incident queries (pointer layer, never redistributed) |
| `news_rss` | 15 min | the outlets' own RSS feeds (Kolkata and Bengal sections, English and Bengali; pointer layer, never redistributed; robots.txt honoured per feed) |
| `gdelt_events` | 15 min | GDELT 2.1 `lastupdate.txt` and only the export zip it names (Kolkata metro bbox, ADM1 `IN28`) |
| `gdelt_doc` | 30 min | GDELT DOC 2.0 ArtList, `(Kolkata OR Calcutta) sourcecountry:IN` (≥ 5 s between requests). A 429, the throttle banner or a 60 s timeout backs it off: `Retry-After` honoured, else jittered exponential from the cadence, at most 6 h; no request meanwhile, and the last live answer is served with its real fetch time and age |
| `reddit_rss` | 15 min | r/kolkata newest-posts Atom feed (aggregate social signal only; the committed synthetic capture uses the fictional `r/example_city`) |
| `kmc_scrape` | hourly | the KMC portal page, best effort, notices about places and roads only (never HR circulars, hearings or menu links); a robots.txt disallow disables the connector. The server offers RSA key exchange only: one narrow TLS allowance (`safe_http.TLS_COMPAT`), certificate still verified |
| `kolkata_police_scrape` | hourly | the Kolkata Traffic Police home page's current advisories (diversions, closures); menu links and commented-out advisories never read. The server lacks secure renegotiation: one narrow TLS allowance, certificate still verified |
| `wbsdma` | off | disabled: `wbdmd.gov.in` answers plain HTTP on port 443 and 503 over http (2026-10-29); not allow-listed |
| `common_crawl` | never | backfill only (`once --backfill`; TOI Kolkata archive) |

### Sources (checked 2026-10-28 with the service's user agent, one request each)

`sahoshi-osint-ingress/<version> (Sahoshi corridor operations, Kolkata; open-source civic research)`, never a
browser user agent and never a bot-check workaround. A source that refuses is excluded, not worked around.

| outlet / office | URL | status 2026-10-28 | language | kept |
|---|---|---|---|---|
| Times of India, Kolkata | `https://timesofindia.indiatimes.com/rssfeeds/-2128830821.cms` | 200 (20 items) | en | yes (`news_rss`) |
| Millennium Post (whole site; its `/bengal/` section kept) | `https://www.millenniumpost.in/feed` | 200 (199 items, 48 kept); one TLS handshake failure at 17:20 IST, 200 again at 18:10 | en | yes (`news_rss`; a failed feed is skipped for that cycle) |
| Sangbad Pratidin (city মহানগর `/kolkata/` and state `/bengal/` sections kept) | `https://www.sangbadpratidin.in/feed/` | 200 (20 items, 6 kept) | bn | yes (`news_rss`) |
| ABP Ananda, Kolkata | `https://bengali.abplive.com/news/kolkata/feed` | 200 (10 items) | bn | yes (`news_rss`) |
| Google News search, English | `news.google.com/rss/search?…&hl=en-IN&gl=IN&ceid=IN:en` | 200 (100 items) | en | yes (`google_news_rss`) |
| Google News search, Bengali | `news.google.com/rss/search?…&hl=bn&gl=IN&ceid=IN:bn` | 200 (27 items) | bn | yes (`google_news_rss`) |
| Reddit r/kolkata | `https://www.reddit.com/r/kolkata/new/.rss` | 200 (25 posts) | en (bn by script) | yes (`reddit_rss`) |
| IMD CAP (WMO Alert Hub mirror) | `https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml` | 200, live and empty (0 items) | en | yes (`imd`) |
| NDMA SACHET, all India | `https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml` | 403 to this user agent in the morning, 200 at 17:00 IST (100 items, 13 West Bengal); the state file name is unknown (guesses 404) | en, bn | yes (`sachet_cap`; a refusal serves the cache) |
| KMC portal | `https://www.kmcgov.in/KMCPortal/jsp/KMCPortalHome1.jsp` | 200; no robots.txt (404: no restriction) | en | yes (`kmc_scrape`) |
| WB Disaster Management dept. | `https://wbdmd.gov.in/` | port 443 speaks plain HTTP (no TLS); http 503 (2026-10-29) | — | no: `wbsdma` disabled, not allow-listed |
| Kolkata Traffic Police | `https://kolkatatrafficpolice.gov.in/` | 200 with the legacy-renegotiation allowance (OpenSSL 3 refuses the server by default); GeoTrust certificate verified; robots.txt 404 (2026-10-29) | en | yes (`kolkata_police_scrape`) |
| Kolkata Police | `kolkatapolice.gov.in` | same legacy TLS; recruitment and security notices, no traffic advisories | — | no |
| The Telegraph | `telegraphindia.com` feeds | 403 to the parent probe; the old feed path now redirects to the home page (no feed) | en | **excluded** |
| Anandabazar Patrika | `anandabazar.com/rss…` | 403 to the parent probe; `/rss` answers 404 | bn | **excluded** |
| Ei Samay | `eisamay.com` (old `eisamay.indiatimes.com` feeds) | 410 / the old feed path redirects to the home page; no feed found | bn | **excluded** |
| The Statesman | `thestatesman.com` | 403 (whole site) | en | **excluded** |
| Zee 24 Ghanta | `zeenews.india.com/bengali` | 403 to the parent probe; robots.txt disallows every generic crawler | bn | **excluded** |

### West Bengal and Kolkata filtering

SACHET publishes one all-India feed and IMD's feed covers every state, so `connectors/_area.py` reads each alert's
own text (title, description, and the CAP headline and `areaDesc` when the detail is cached), after NFKC (so "ড়"
in either encoding is one letter), with Bengali digits as ASCII and joined district names written out ("উত্তর ও
দক্ষিণ ২৪ পরগনা" → both districts):

- naming a metro district (`osint_common.kinds.AREA_DISTRICTS`, English, Bengali and Hindi spellings, plus "N 24
  Pgs"): admin codes `LGD:KOLKATA`, `LGD:HOWRAH`, `LGD:NORTH_24_PARGANAS`, `LGD:SOUTH_24_PARGANAS` (each one
  named), hints `area:kolkata` …;
- naming West Bengal or any other of its districts only (Bankura, Purba Medinipur, Darjeeling …): the state,
  `LGD:WEST_BENGAL` (`kinds.AREA_STATE_CODE`), hint `area:west_bengal`; the analysis holds it as outside the city;
- anything else (another state, Andaman and Nicobar, "Bay of Bengal"): not emitted, counted `outside_area`. Only
  West Bengal alerts get a CAP-detail request.

GDELT keeps a row inside the Kolkata metro bbox of `cities/kolkata/city.json`, or with ADM1 `IN28`, or whose
FullName names Kolkata, Calcutta (GDELT's spelling), Howrah or Bidhannagar. `news_rss` keeps a whole-site feed to
its Kolkata and Bengal sections (`outside_section`) and drops items linking off the outlet's site (`foreign_link`).

Each connector separates `fetch()` (raw bytes into the cache) from `parse()` (cache to signals). Offline mode, and
a failed live fetch, parse the newest cache entry and label the signals `cached-sample`, with `fetched_at` set to
the capture time. Retention: 72 h or 200 MB, whichever comes first; the newest entry of each connector is kept.
The cache root is created `0700` (files `0600`). A CAP `<expires>` days ahead is kept as `valid_until` (up to
31 days ahead); a publication time more than a day ahead is treated as unknown.

## Ethics rails in this service

- Names and ages are redacted at parse (`[PERSON]`, `[AGE]`; social contacts `[CONTACT]`); the result always passes
  `osint_common.ethics.find_pii`, which proves only that none of ITS patterns survived: it is the same pattern
  family the redactor uses, so it cannot see what they miss. **What the redactor does not promise**: no NER runs at
  parse, so a name with no cue, no known surname and no role noun, a single given name after an unlisted verb, or
  an ALL-CAPS headline can survive. The honest figure is the held-out recall (`tests/test_heldout_recall.py`, three
  Kolkata corpora of invented names written blind by a separate agent and never tuned on; first scores on
  2026-10-28: Latin name-word recall 0.919 / 0.795 / 0.839, Indic 1.0 / 1.0 / 1.0, age markers 0.926 / 0.931 /
  0.875, keep 0.673 / 0.649 / 0.611; the keep losses are mostly Bengali place and ordinary words that the shared
  lexicon and gazetteer did not hold yet). Known misses: ALL-CAPS headlines, cue-less names with an unlisted
  surname, "s/o" forms, initials without full stops, lower-case "sergeant", single given names in posts.
  Cue-less names are read through role and kin nouns ("Biker <Given> <Surname>", "husband <Given> <Surname>"), a
  common-surname list (Bengali and pan-Indian: "<Given> <Surname>"), address suffixes ("<Given>babu",
  "<Given>-da", "<Given>-di", "<Given>bhai"), Kolkata ranks and honorifics ("Sri", "Srimati", "Sergeant", "OC"),
  both sides of "alias"/"@", "<Given>, a <role>," and "<Name>'s body/family"; a surname written alone after a
  learned name in the same feed document ("<Surname> taught there") goes too.
- **Indic script**: a Bengali or Devanagari word that is neither a gazetteer place nor an ordinary word
  (`osint_common.ethics`) is withheld as `[WITHHELD]` in every tier (no Indic NER yet). Bengali cues read names
  even when they are ordinary words or places: after an honorific (শ্রী, শ্রীমতী, ডাঃ, ডাক্তার; श्री, डॉ.) the
  next words are a name; after a role cue (অভিযুক্ত, ধৃত, মৃত, নিহত, আহত, বাসিন্দা, চালক, নাম; आरोपी, मृतक) the
  unknown words are a name; the word before an address term (বাবু, দা, দি) and a word ending in "বাবু" are a name.
  Bengali and Hindi ages become `[AGE]`: "৩৫ বছরের", "৪২ বছর বয়সী", "বয়স ৬০", "<name> (৬০)", "<name>, ৪৫,",
  "28 वर्षीय", "45 साल के" (Bengali, Devanagari or Western digits; "য়" in either encoding). A Bengali outlet's
  English search keyword before a Bengali headline ("<Keyword>: <Bengali headline>", often a person's name) is cut.
- A social post's age and sex shorthand ("F(28)", "22M", "27/F") is `[AGE]` (a bare "15M" in a post is redacted
  too: accepted over-redaction). Beyond the shared cue patterns, a cue-introduced name runs on over a 4th,
  initialled or hyphenated name word; "the victim, <Name>,", "the deceased as <Name>", "Mr.<Name>" and Title-Case
  "Accused <Name> <Name> Held" are read; and the name right before an age ("<Name>, [AGE]," / "<Name> ([AGE])")
  is redacted. A Reddit user mention or page (`u/<name>`, `/u/<name>`, `/user/<name>`, `r/u_<name>`,
  `reddit.com/u/<name>`) becomes `[PERSON]` in every tier, news, GDELT and official included. Social posts are
  redacted most aggressively: `@<name>` and "insta: <handle>" mentions too (in news an `@`-account, usually an
  outlet's or an office's, is kept), and every capitalised run (initials such as "K." included) that no
  gazetteer phrase covers and that is not a generic word (a place noun such as "Road" never vouches for the name
  before it).
- **Places named after people** (Kolkata has many: "Sarat Bose Road", "Santosh Mitra Square", "Kazi Nazrul Islam
  Avenue") survive only when the gazetteer holds the whole phrase; otherwise the surname rule reads "<Given>
  <Surname>" and the place loses its name. The gazetteer drives this protect-set.
- **Bylines are never read**: `news_rss` reads an item's title, link, guid, date, description and category only
  (never `dc:creator`, `author` or `content:encoded`); Google News keeps only the outlet's domain.
- Every URL written in a news or social title or text is redacted (a slug or a profile path can name a person):
  a Reddit user page becomes `[PERSON]`, any other URL `[URL]`. `pii_redactions` counts every replacement
  (`[PERSON]`, `[AGE]`, `[CONTACT]`, `[URL]`).
- Reddit poster blocks are never read, and the "submitted by" footer is cut; GDELT actor and person columns are
  never read; court-record portals (case captions name the parties) are dropped; the Google News display name
  (free text, maybe a blog's owner) is cut from titles and descriptions, and only the outlet's domain is kept.
- News- and social-tier URLs are never emitted, stored or logged: the signal keeps the outlet's domain and a
  `url_sha256:` hint of the canonical URL. Official sources keep their identifier URLs.
- `raw` is a scalar whitelist (`RAW_ALLOWED_KEYS`), never the source record.
- Egress goes only to an allow-list of exact hosts over https, with redirects checked hop by hop; the oracle is
  loopback only; every XML, RSS, CAP and Atom document is parsed with `defusedxml`.

## Optional model check at parse (PII-Tracer)

OFF by default. The rules above stay primary; a learned detector can be consulted as defence in depth and can only
ADD redactions (`src/osint_ingress/connectors/_model_pii.py`).

| variable | default | meaning |
|---|---|---|
| `OSINT_PII_MODEL` | unset (off) | `1` / `true` / `yes` / `on` turns the check on |
| `OSINT_PII_URL` | unset | the embedding service's base URL; loopback only (`127.0.0.1`, `localhost`, `::1`), no path |
| `OSINT_PII_TIMEOUT_SEC` | `3` | per request (clamped to 0.2–10 s; connect 0.5 s) |
| `OSINT_PII_COOLDOWN_SEC` | `60` | after a failure, the model is not asked again for this long |

- One `POST <OSINT_PII_URL>/pii/spans` per feed document (`{"texts": [...]}` → `{"spans": [[{start, end, label}]]}`),
  with the titles and texts already bounded (500 / 2000 characters). `private_person` → `[PERSON]`;
  `private_email` / `private_phone` → `[CONTACT]` in every tier but `official`; other labels are ignored. The spans
  join the rules' first pass, so the result still passes `osint_common.ethics.find_pii`.
- A model span never redacts a protected place: the embedding service drops spans on Kolkata place names, and this
  side clips every span again against the protect-set phrases, the gazetteer's Bengali and Devanagari spellings and
  runs of name words ending in a place word ("Sarat Bose Road", "শরৎ বসু রোডে", "विधान सरणी").
- Fail-open to the rules: a refused URL, connection error, timeout, redirect, non-200, oversized or malformed answer
  means the document is redacted by the rules alone, and a `pii_model` log event records the outcome (counts only,
  never a text or a name). The client never reads proxy settings from the environment (`trust_env=False`) and never
  follows a redirect. `parse()` is synchronous, so a call blocks it for at most the timeout.
- Measured on a SYNTHETIC Kolkata set (120 sentences, `services/embedding-service/eval/pii/`): person recall of the
  news-tier rules 0.84 → 0.94 with the model added, no protected place, office title or emergency number newly
  redacted. In Bengali script the model is weaker (person F1 about 0.7), so the `[WITHHELD]` rule stays.

## Tests

`pytest` here; `tests/fixtures/README.md` gives the provenance of every fixture. `tests/fixtures/capture/` is the
synthetic sandbox seed (import-compatible; every file synthetic, its designed outcome in its README). Tests that read
the real PoC captures in place (absent in CI: skipped) use them for city-independent shape only: a real GDELT
export (global, so it holds Kolkata rows), the real SACHET file of another state (every item filtered out), a real
Reddit capture (no poster reaches a signal), and the PoC-name scan.
