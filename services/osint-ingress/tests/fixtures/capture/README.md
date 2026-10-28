# Synthetic OSINT capture (the sandbox seed)

This directory is laid out like a PoC raw capture directory (`osint/prototype/out/raw/`), so
`python -m osint_ingress import-poc tests/fixtures/capture <cache_dir>` reads it unchanged. It seeds the Sahoshi
sandbox (plan R13), so every dev-deck screenshot, recorded contract fixture and docs image built from it is
synthetic. **Every file here is synthetic**: no real West Bengal SACHET capture is committed (the real feeds are
read in place, never copied into the repo).

**Labels.** `import-poc` reads the table below: every file marked **synthetic** is imported as a synthetic cache
entry, so the signals parsed from it carry `provenance_label: SIMULATED` (never `NEWS-REPORTED`,
`OFFICIAL-VERIFIED` or `UNVERIFIED-OSINT`: no outlet, office or community reported them), and the situations built
from them stay `SIMULATED`.

| file | provenance | what it is |
|---|---|---|
| `sachet_westbengal_synthetic.xml` | **synthetic** | A replica of the NDMA SACHET **all-India** CAP RSS schema (fictional identifiers `1999...`, a fictional control-room mailbox the parser never reads), written in the shape of the real feed: English and Bengali nowcasts, joined district names ("পূর্ব ও পশ্চিম মেদিনীপুর"), other states' alerts. 10 items: 1 names Kolkata (a district-level alert, `LGD:KOLKATA`), 6 are West Bengal state-wide nowcasts naming other districts (Bankura, Purulia, Purba and Paschim Medinipur, Jhargram, Murshidabad, Nadia, Hooghly, Purba Bardhaman, Darjeeling, Kalimpong, Jalpaiguri: `LGD:WEST_BENGAL`), 3 are other states' alerts (Andaman and Nicobar, Odisha, Andhra Pradesh) that the West Bengal filter drops. |
| `gnews_live.xml` | **synthetic** | A replica of the Google News RSS search schema (channel, items with `title`, `link`, `guid`, `pubDate`, `description`, `<source url>`). Fictional publishers `news-a.example` and `news-b.example`; fictional names and ages to exercise redaction. Four collision reports and one "driver beaten by mob" report on EM Bypass near Kasba, a jewellery-shop robbery near Gariahat crossing, two general items. Not Google News content. |
| `news_rss_live.json` | **synthetic** | A `news_rss` cache bundle (`sahoshi.news_rss/1`) with three fictional outlets' RSS feeds inlined: `news-bn-a.example` and `news-bn-b.example` (Bengali) and `news-c.example` (English). Two Bengali reports of waterlogging at Thanthania on Bidhan Sarani (জল জমা / জলমগ্ন, যান চলাচল ব্যাহত; one with an English search-keyword lead-in that the parser cuts), two Bengali and two English general items, one item outside the kept sections and one linking off the outlet's site (both dropped). Every item carries a fictional `dc:creator` byline and `content:encoded` text that the parser never reads; a fictional name with a Bengali age (৬০) and an English one with an age exercise redaction. |
| `reddit_live.rss` | **synthetic** | A replica of Reddit's community Atom schema, for the fictional community `r/example_city` (`entry` with an `author` block, `content` HTML with Reddit's "submitted by" footer, `id`, `link`, `updated`, `published`, `title`, `category`). Every poster block and handle (`synthetic_user_NN`) is fictional and exists to prove the parser never reads it. Four posts: a road closure near Park Street crossing and a crowd near Eden Gardens (single social posts, held), a thank-you naming a fictional person, and a request with a fictional handle and e-mail address. The publisher is the fictional community `reddit.com/r/example_city` (never a real community: fabricated posts are not attributed to one). |
| `gdelt_doc_live.json` | **synthetic** | A replica of the GDELT DOC 2.0 ArtList JSON schema (`articles[]` with `url`, `url_mobile`, `title`, `seendate`, `socialimage`, `domain`, `language`, `sourcecountry`). Five general civic items from the fictional publishers (three English, one Bengali, one Hindi), with fictional names and an age; one item repeats a cue-introduced name without its cue (document-level name learning). |
| `gdelt_lastupdate_live.txt` | **synthetic** | A replica of GDELT's `lastupdate.txt`: it names `20261020120000.export.CSV.zip` with its real size and MD5; the mentions and GKG lines point at files that do not exist. Built by `../build_synthetic_gdelt.py`. |
| `20261020120000.export.CSV.zip` | **synthetic** | Three rows in the real 61-column GDELT 2.0 Events schema: a Kolkata row ("Calcutta, West Bengal, India", GDELT's spelling: a district hint, ADM1 `IN28`, inside the metro bbox), a Durgapur row (ADM1 `IN28`, outside the metro bbox: a state hint) and a Mumbai row (`IN16`, filtered out). The actor columns hold SENTINEL strings the parser must never read. Built by `../build_synthetic_gdelt.py`; `--check` verifies it. |

## Designed outcome

Parsed by the connectors: `sachet_cap` 7, `google_news_rss` 8, `news_rss` 6, `gdelt_events` 2, `gdelt_doc` 5,
`reddit_rss` 4 (32 signals, every one `SIMULATED`, `pii_redactions` > 0). Through the full pipeline
(`osint_analysis.run_pipeline` with the `osint_geo` resolver) it is designed to give **exactly 4 surfaced
situations**:

1. the multi-vehicle crash on EM Bypass near Kasba: four collision reports from two independent
   fictional publishers plus the "driver beaten by mob" conflict report → one correlated `affray+collision` on the
   EM Bypass segment 1035 (ruby → science_city), `SIMULATED`;
2. the jewellery-shop robbery at Gariahat crossing (junction 23), `reported_crime`, a single (simulated) news
   source;
3. the SACHET Kolkata district alert (`LGD:KOLKATA`, area-level, `SIMULATED`: the replica is synthetic, one source);
4. waterlogging at Thanthania on Bidhan Sarani, reported in Bengali by two fictional Bengali publishers
   (`news_rss`, language `bn`) → one `urban_flooding` situation there.

Held: the two single social posts (aggregate-only rule), the 6 state-wide nowcasts as `outside_city` (plan R28),
and the general items as not an event class. No `crime_incident` anywhere.

Every publisher ends in `.example`, is the fictional `reddit.com/r/example_city`, or is `sachet.ndma.gov.in` (the
replica's own schema). No real person's name appears in any file here.
