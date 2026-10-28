# osint-common test fixtures — SYNTHETIC

Everything in this package's fixture kit is a **synthetic replica** (plan R13): the real feeds' structure, written
here, never copied from a capture. It covers both the committed JSON file below and the canonical fixtures in
`src/osint_common/testing.py`, which every OSINT work package imports.

## `src/osint_common/testing.py` (the signal and state fixtures)

| Fixture | What it is | Publisher |
|---|---|---|
| `em_bypass_signals()` | 5 Google News RSS replicas: 4 reports of a multi-vehicle collision on EM Bypass near Kasba (segment 1035, Ruby crossing to Science City) and 1 report of a crowd assaulting the driver at the scene | `news-a.example`, `news-b.example` (fictional) |
| `gariahat_robbery_signal()` | 1 Google News RSS replica: a reported robbery at Gariahat crossing (junction 23) | `news-b.example` (fictional) |
| `social_single_signal()` | 1 Reddit replica: a road closed for metro work near Taratala on Diamond Harbour Road (a single social source, so it is held) | `social-a.example` (fictional host), community `example_city` (fictional) |
| `sachet_district_signal()` | 1 NDMA SACHET CAP alert for Kolkata district (`LGD:KOLKATA`) | `sachet.ndma.gov.in` (the real public-domain publisher; the alert text is written here) |
| `sachet_state_signal()` | 1 West Bengal state-wide SACHET nowcast (`LGD:WEST_BENGAL`) naming other districts (state-level, held) | `sachet.ndma.gov.in` (as above) |
| `live_state_sealdah_pursuit()`, `em_bypass_geocode()` | the live corridor state and one geocode, for the pipeline and attach tests | — |

- **Fictional publishers only.** Every Google News, GDELT and Reddit replica uses a reserved `*.example` host, so
  no fabricated text is ever attributed to a real outlet or community. The only real publisher is the
  public-domain NDMA SACHET CAP feed, and its alert texts are written here, not copied.
- **No real person's name anywhere.** The names and ages the replicas "had" are already redacted to `[PERSON]` /
  `[AGE]`, exactly as a connector emits them (`pii_redactions` counts them). The test files use invented names
  (for example in `tests/test_ethics.py`) only to prove that detection works.
- The toponyms are Kolkata's (EM Bypass, Kasba, Gariahat crossing, Taratala, Kolkata district) and the class cues
  the proof-of-concept's, so the replicas exercise the same geocoding and classification paths. `tests/test_types.py`
  (`test_fixtures_are_deterministic_and_synthetic`) asserts every publisher is `*.example` or SACHET and every URL
  is on a `*.example` host.

## `dss_em_bypass.synthetic.json` (the decision-support fixture)

`dss_em_bypass.synthetic.json` is `osint_common.testing.em_bypass_dss()` dumped as JSON
(`tests/test_dss_shapes.py` pins the two equal). It is a **synthetic replica** with the structure of the
proof-of-concept `dss_output.json` (here the EM Bypass `affray+collision` situation at segment 1035) plus the C-U
fields (`state`, `seed`, `horizon_min`, `strategy_prior`, `provenance.wargame_method`, `human_gate`):

- the publishers are fictional (`news-a.example`, `news-b.example`); no real person's name appears anywhere,
  and the member reports' names and ages are already `[PERSON]` / `[AGE]`;
- the numbers (AHP weights, TOPSIS closeness, EVOI, feasibility) mirror the PoC run so the shape is realistic;
- it is labelled `SIMULATED` (its predicted outcomes are simulations) and `NEWS-REPORTED` (no official source).

## The real proof-of-concept outputs

The real PoC outputs are never copied here: `tests/poc_parity.py` and `tests/test_poc_parity.py` read them in
place (`$OSINT_POC_DIR`, else the orchestration PoC directory) and skip when they are absent.
