# osint-analysis

Sahoshi's OSINT analysis library (OS-4): it turns geocoded open-source signals into honest **situations about places,
never persons**. Pure and deterministic: no database, no network except an optional embedder.

```python
from osint_analysis.pipeline import run_pipeline   # (signals, *, resolver, live=None, embedder=None, now=None) -> PipelineResult
from osint_analysis.classify import classify       # classify(signal) -> Classification; never crime_incident
from osint_analysis.embed import HttpEmbedder      # HttpEmbedder(base_url, timeout=3.0); None on any failure
```

The shapes (`RawOsintSignal`, `Geocode`, `Classification`, `ResolvedEvent`, `LiveStateSnapshot`, `PipelineResult`, …)
and the vocabulary (`INCIDENT_CLASSES`, `RELATED_CLASSES`, `RESPONSE_PRIORITY`, …) are `osint_common`'s (X18). The
resolver is injected (`osint_geo.resolver.GazetteerResolver` in production); this package never imports `osint_geo`.

## Stages

| Stage | Module | Rule |
|---|---|---|
| Classify | `classify.py` | The SACHET rule (a CAP alert with a flood word, English, Bengali or Hindi, is `urban_flooding`, else `weather_hazard` with the alert's own event as subtype: `rain`, `thunderstorm`, `cyclone`, `heat`, `fog`, … from `cap_event` or the text, else `weather_advisory`, never "storm" for all); the lexicon in order, first row wins (the Indic rules are under "Bengali and Hindi" below); an English keyword matches a whole word (itself or a regular inflection: `mobs`, `mobbed`, `crashes`, `robberies`; a noun takes a plural only: `concerts`, never "concerted"), the derived words (`protesters`, `looters`, `chain snatchers`, `brawlers`, `marchers`, `gas leakage`, `oil spillage`; never "striker", "mobile", "Protestant", "accidental"), a stem list matching any continuation (`waterlog…`, `inundat…`, `flood…` but not "floodlights", `electrocut…`), and two context rules (the month "by March" is not a march; a "lightning strike" is not a labour strike); optional zero-shot against one exemplar per class (official and news tiers only); else `general_news`. Every rule reads the text without poster handles. A final check raises on `crime_incident` or `vehicle_pursuit`. |
| Stage 1 | `fusion.py` | Per realm × class: DBSCAN (haversine, 900 m) blocks for points, shared `segment_id` for roads (a neighbourhood blocks by its reference point: it has no segment), state areas only with the same state; a 6 h window for point incidents, 48 h for ongoing situations; inside a block, a link needs co-location, the window, and text similarity (embedder cosine ≥ 0.70, else token Jaccard ≥ 0.20). Links are taken strongest first, and none that would put two point reports more than 1.8 km apart in one cluster, or spread its REPORT times over twice its class window (a dense field of similar reports never chains across the city, an accident hotspot never into one day-long situation; a long validity never stops a 4-day warning from joining its re-issue). A district alert cluster then joins AT MOST ONE point cluster inside its district (the most similar, ties to the earliest), or stays its own: an area never merges two point clusters, and never joins a point cluster made only of social posts. The pair tests run as array operations, and a block no bound can split is clustered as plain connected components: 2 000 reports of one procession within 300 m take about 1 s (12.7 s pair by pair). |
| Stage 2 | `correlate.py` | Related classes co-located at the same level (point representatives within 1 200 m or on one road segment; the same district; the same state) and overlapping in time join into one situation, nearest first, never two clusters of one class (a clash report between two accidents joins one of them); primary class by response priority, ties by member count, then the earliest report. Only pairs a vectorised distance filter lets through are tested (the same result as testing every pair). |
| Credibility | `credibility.py` | Base = strongest prior; +0.15 per extra trust type (official, news, social); +0.05 per extra independent publisher within a type, capped at +0.10; independence by registrable publisher domain, never by URL; a single social source ≤ 0.30; ceiling 0.99. Cross-posts are one source: the posts of one community are one source, and two communities are one when a post of one near-duplicates a post of the other (content-token Jaccard ≥ 0.75 of the titles or of the whole texts, or every token of the shorter, at least 3, in the other; cross-post markers and `r/<community>` mentions removed). Syndicated copies are one source too: the same rule across every news tier, so one wire story carried by N outlets is one independent publisher, not N. `SIMULATED` and `EMULATED` pass through, never upgraded. |
| Attach | `attach.py` | Read-only: an ACTIVE live corridor event (`event:` URN) of a compatible kind (an accident ↔ `road_accident`, a crowd ↔ `mass_gathering`, …) within 900 m or on the situation's road segment, overlapping in time, is corroborated; else `novel`. Never a convoy, a `protected_movement` (that is a second-order effect), a `vehicle_pursuit` or a `crime_incident`. Area-level situations and chatter are always novel, and the pipeline checks surfaced situations only (a held social post is never linked to a live event). |
| Second order | `second_order.py` | `protected_corridor` (an active protected movement's route), `convoy` (a convoy in motion on the route or within 900 m), `ambulance_route` (an active ambulance (108) route), `closure` (a segment already closed); notes say "on or near segment N"; surfaced situations only. |

A situation surfaces (`is_event`) only for an incident or operational class, never from a single social post or
from the posts of one social community (one source: they may be one poster), and never when every geocode is
state-level; otherwise it is held with its reason and only counted. An area-level member is never corroboration
of a point-level social report: a district alert or district-level report never joins a point cluster made only
of social posts (it stays its own district situation), and the single-social rules are also applied to a
situation's point-level members, so a SACHET Kolkata alert can never lift one waterlogging post into an
"Official, verified" street event. An independent point-level news or official report of the same situation still
surfaces it.
An area member attached to a point situation is context, never verification: credibility, verification state,
cross-type corroboration, independence, source tiers, labels and the time window (which the live attach and the
second-order checks read) come from the point-level members only. A Park Circus news report with a district SACHET alert
attached stays `NEWS-REPORTED` 0.60; `OFFICIAL-VERIFIED` needs an official source reporting the point-level
situation itself. The alert stays a member and a source, listed after the point-level sources with the role
`CONTEXT_ROLE` (`"context"` once OS-1's `SourceRole` has it; `"corroborating"` until then).
`fused_event_id = sha1("anchor:" + earliest member signal_id by (published_at, signal_id))` over the situation's
point-level members when it has any: a district alert that joined a point situation never anchors it, so the id
stays with its place when the alert re-attaches elsewhere in a later cycle. A district or state situation is
anchored on its earliest member.

Two kinds of member can never surface and are therefore held as aggregates rather than deduplicated as incidents:
`general_news` chatter (one aggregate per place and time window) and state-level alerts (one per state and class).

## Ethics in code

- No person field anywhere; `ResolvedEvent`, `SourceRef` and the counts are `osint_common` models (`extra="forbid"`).
- A poster handle is never a cue: `classify.strip_handles` removes Reddit's `submitted by /u/<name> [link]
  [comments]` trailer, any other `/u/<name>`, `u/<name>` or `reddit.com/user/<name>`, and the boilerplate inside
  `normalize_text`, the one text view the classifier, the similarity tokens and the embedder read. Two posts by one
  poster are never more alike than the same posts by two posters.
- Labels, summaries and source titles are fitted to their limits and re-checked with `ethics.find_pii` after the
  clip (a cut can leave the "Dr. <name>" of a protected place "Dr. <name> Road"); the same helper drops a stray
  handle trailer and turns any other handle into `[PERSON]`. No text can fail the output model and sink a batch.
- `SourceRef.url` is kept for official sources only (SACHET/NDMA, IMD, WBSDMA); news and social URLs, whose slugs can
  name a person, are `None` (the source stays verifiable by its `signal_id` and publisher).
- Reported crime comes only from reported text (`reported_crime`, `public_disorder`), never from a camera or image
  path, and never as `crime_incident`.
- `HttpEmbedder` posts only to `/embed` (a read); it never calls `/embed/documents` or `/incidents`, which write to
  the memory store, never follows a redirect and ignores proxy environment variables; one call ends within its
  `deadline` (10 s) however many batches it needs. Today's embedding service has no `/embed` route, so the client
  returns `None` and the pipeline uses lexical similarity.

## Kolkata

Areas are Kolkata's (`fusion.DISTRICT_ENVELOPES`): the four metro districts of `osint_common.kinds.AREA_DISTRICTS`
(Kolkata, Howrah, North and South 24 Parganas) as approximate bounding boxes, not boundaries; an area key reads the
resolver's toponym ("Kolkata (district)", GDELT's "Kolkata, West Bengal, India") or the connector's code
(`LGD:KOLKATA`, `LGD:WEST_BENGAL`, `GDELT_ADM1:IN28`). A district-level situation without a toponym is labelled
"Kolkata district", a state-level one "West Bengal state". The sources are those of `osint_common.kinds.SOURCE_NAMES`:
`news_rss` (Kolkata and Bengali outlets' own feeds), `imd`, `sachet_cap`, `kmc_scrape`, `wbsdma`,
`kolkata_police_scrape`, Google News, GDELT, Reddit and Common Crawl.

## Bengali and Hindi

Bengali text reaches the classifier AFTER the ingress redaction: every Bengali or Devanagari word that is neither a
gazetteer place nor an ordinary word of `osint_common.ethics.INDIC_COMMON_WORDS` is `[WITHHELD]` (no Indic NER runs
at parse, so an unknown word may be a name). Every cue word the lexicon relies on is therefore one of those ordinary
words, and `tests/test_classify_bengali.py` pins it. The only cues that match unredacted text alone are words that
double as a given name ("বিদ্যুৎ", "বিদ্যুতের", "অগ্নি", and "প্রতিমা" in a guard): they stay withheld.

| Bengali (Hindi) | Class (subtype) |
|---|---|
| জল জমা / জমে / জমেছে / জমতে, জমা জল, জলমগ্ন, জলবন্দি, জলযন্ত্রণা, প্লাবিত, বন্যা, হাঁটুজল, হাঁটু/কোমর … জল, জল থইথই, ভারী / অতিভারী / মুষলধারে / টানা বৃষ্টি (जलभराव, जलजमाव, बाढ़, भारी बारिश) | urban_flooding (waterlogging) |
| দুর্ঘটনা; with a vehicle in the clause: ধাক্কা, সংঘর্ষ, উল্টে, পিষে, চাপা (दुर्घटना, हादसा, टक्कर) | road_accident (collision) |
| সংঘর্ষ with no vehicle, মারামারি, হাতাহাতি, ইটবৃষ্টি, গণপিটুনি, গণধোলাই (पथराव, झड़प) | public_conflict (affray) |
| আগুন, অগ্নিকাণ্ড, অগ্নিদুর্ঘটনা, দমকল, পুড়ে ছাই (आग, अग्निकांड) | fire (structure_fire) |
| বাড়ি / ভবন / ছাদ / দেওয়াল / সেতু / উড়ালপুল … ভেঙে / ধসে, রাস্তায় ধস, গ্যাস লিক, লোডশেডিং, পাইপ ফেটে (पुल / इमारत … गिरा) | infra_failure (collapse) |
| গাছ … পড়ে / ভেঙে / উপড়ে (पेड़ … गिरा) | hazard (fallen_tree) |
| বিদ্যুৎস্পৃষ্ট, তার ছিঁড়ে, ছেঁড়া তার, হাইটেনশন তার (करंट लगने) | hazard (live_wire) |
| বিষাক্ত, রাসায়নিক … লিক | hazard (spill) |
| সমাবেশ, জমায়েত, ভিড়, জনসমুদ্র, মেলা, বইমেলা, দর্শনার্থী, পুণ্যার্থী (रैली, भीड़, मेला) | public_gathering (mass_gathering) |
| মিছিল, শোভাযাত্রা, রথযাত্রা, পদযাত্রা, বিসর্জন, ভাসান, কার্নিভাল, প্যারেড (जुलूस) | procession |
| অবরোধ (পথ / রেল অবরোধ), বিক্ষোভ, ধর্মঘট, বনধ, ঘেরাও, অনশন (धरना, चक्का जाम, हड़ताल) | unrest (protest) |
| রাস্তা / রোড / সেতু / উড়ালপুল বন্ধ, যান চলাচল বন্ধ, ঘুরপথে, বিকল্প পথ, মেট্রোর / মেরামতির কাজ (रास्ता बंद) | road_closure (closure) |
| ঘূর্ণিঝড়, ঝড়, ঝড়বৃষ্টি, কালবৈশাখী, নিম্নচাপ, বজ্রপাত, বাজ পড়ে, দমকা / ঝোড়ো হাওয়া, তাপপ্রবাহ (चक्रवात, आंधी) | weather_hazard (storm) |
| ছিনতাই, ডাকাতি, লুট, বন্দুক দেখিয়ে, দোকানে … চুরি (लूट, डकैती) | reported_crime (daylight_robbery) |

A Bengali word matches whole (a vowel sign is part of its word: "জল" is never read inside "কাজল") and with its case
endings ("রাস্তায়", "গাছের", "দুর্ঘটনায়"); verb forms are listed, never guessed; a following negation ("নেই",
"নয়", "জমেনি") cancels a cue. A traffic jam ("যানজট", "জ্যাম", "जाम") is a consequence, as in English: it takes its
cause's class ("মিছিলের জেরে যানজট" is a procession) and alone it is `general_news` (congestion comes from the live
traffic feeds). Guards keep ambiguous words honest: "আগুন দাম" (prices on fire), "ঝড় তুলল" / "সমালোচনার ঝড়" (a
figurative storm), "বড় ধাক্কা" (a setback), "জমা জলে মশার লার্ভা" (a dengue notice), "জল জমা রুখতে" (prevention),
"ভেঙে ফেলা" (a demolition), "ভোট লুট" (an electoral claim), "ভিড় কম" (a thin crowd), "নিয়ম বিসর্জন" (rules
abandoned), "कड़ी टक्कर" (a close contest). A procession or a rally is classified as the situation on the road,
never by who marches or why. The similarity tokens read Bengali words whole, strip one case ending, read Bengali
digits and number words as digits, and never count the `[WITHHELD]` token.

## Checks

```bash
cd services/osint-analysis
python -m pytest -q -p no:cacheprovider
```

`tests/test_pipeline_golden.py` is the Kolkata golden: the canonical synthetic fixtures (`osint_common.testing`) and
Bengali reports (two fictional outlets, `news-bn-a.example` and `news-bn-b.example`, as ingress leaves them) through
the real Kolkata resolver (`osint_geo`): the EM Bypass `affray+collision` on segment 1035, one `urban_flooding`
situation at Thanthania (segment 1058) from the two Bengali reports, the Gariahat robbery at junction 23 as
`reported_crime`, the Kolkata SACHET alert at district level, the state-wide nowcasts held as outside the city, the
single social posts held, and Bengali chatter held as `general_news`.

The proof-of-concept parity run (a script and a test that replayed the previous city's proof-of-concept outputs,
read in place) is retired: those outputs are the other city's real captures, so no Kolkata pipeline can reproduce
them, and keeping the check would have kept that city's places, sources and expected numbers in this package. The
golden above replaces it; the per-rule tests carry the behaviours the parity run used to pin.

Test fixtures are synthetic (fictional `*.example` publishers, no real names): `tests/analysis_fixtures.py` and
`osint_common.testing`; coordinates, segment and junction ids are the Kolkata network's
(`scripts/data/osm_network.json`) and gazetteer's (`scripts/data/osint_gazetteer.json`).
