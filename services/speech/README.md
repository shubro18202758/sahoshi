# speech — Bengali field reports and spoken advisories

Two jobs, both on-premises on the GB10:

1. **Field reports (speech → structured report).** A field officer speaks a
   short report in Bengali ("গড়িয়াহাট মোড়ে হাঁটু জল, বাস আটকে আছে"). The
   service transcribes it and turns it into a structured report: which
   Kolkata place, what kind of problem, how bad. The report always leaves as
   `UNVERIFIED-FIELD` and waits for an officer's confirmation. It is a claim,
   never an action.
2. **Advisories (text → speech).** A public advisory is read out in Bengali,
   English or Hindi in a calm, clear voice, cached by hash.

## API

| Method | Path | Body | Answer |
|---|---|---|---|
| GET | `/health` | — | model status (loaded or not), place counts, memory |
| POST | `/speech/transcribe?lang=bn` | audio (wav / webm / ogg) as the raw body with its `Content-Type`, or multipart field `audio` | `{text, language, confidence, model, audio_seconds, latency_s}` |
| POST | `/speech/report?lang=bn` | the same audio, **or** JSON `{"text": "…"}` | structured field report (below) |
| POST | `/speech/speak` | JSON `{"text", "lang": "bn"\|"en"\|"hi", "voice": "female"\|"male"}` | `audio/wav` (24 kHz mono); headers `X-Speech-Model`, `X-Speech-Cached`, `X-Speech-Seconds`, `X-Speech-Label: synthetic-voice` |

`lang` is `bn` (default), `en`, `hi` or `auto`. Bengali goes to the Bengali
checkpoint; English and Hindi go to a multilingual Whisper, which also
decides the language for `auto` (the Bengali fine-tune writes English speech
out in Bengali letters, and the multilingual model writes Bengali in
Devanagari — each only gets its own languages).
Errors: `413` too large (8 MB / 60 s / 600 characters), `415` wrong type,
`422` undecodable or invalid, `503` the model cannot load right now (memory).

A real report: a Bengali advisory synthesized by this service, re-encoded
to WebM/Opus (what a browser's `MediaRecorder` sends) and posted to
`/speech/report` (`place_candidates` shortened to two here):

```json
{
  "report_id": "039b66e2-22b6-416f-8572-1f1217569798",
  "received_at": "2026-10-28T11:51:07+00:00",
  "place": {
    "id": "gariahat",
    "name_en": "Gariahat crossing",
    "name_bn": "গড়িয়াহাট মোড়",
    "lat": 22.519,
    "lon": 88.366,
    "match_score": 1.0,
    "matched_text": "গড়িয়াহাট মোড়ে",
    "source": "landmarks"
  },
  "place_candidates": [
    {
      "id": "gariahat",
      "name_en": "Gariahat crossing",
      "name_bn": "গড়িয়াহাট মোড়",
      "lat": 22.519,
      "lon": 88.366,
      "match_score": 1.0,
      "matched_text": "গড়িয়াহাট মোড়ে",
      "source": "landmarks"
    },
    {
      "id": "rashbehari",
      "name_en": "Rashbehari crossing",
      "name_bn": "রাসবিহারী মোড়",
      "lat": 22.518,
      "lon": 88.35,
      "match_score": 1.0,
      "matched_text": "রাসবিহারী",
      "source": "landmarks"
    }
  ],
  "kind": "waterlogging",
  "kind_cues": [
    "জল জম"
  ],
  "severity": "medium",
  "severity_cues": [],
  "transcript": "গড়িয়াহাট মোড়ে জল জমেছে দয়া করে রাসবিহারী হয়ে বিকল্প পথ নিন",
  "language": "bn",
  "source": "field-voice",
  "asr": {
    "model": "bengaliAI/tugstugi_bengaliai-asr_whisper-medium",
    "confidence": 0.995,
    "audio_seconds": 7.99,
    "asr_seconds": 1.795
  },
  "verification_state": "UNVERIFIED-FIELD",
  "requires_confirmation": true,
  "note": {
    "en": "Field report awaiting an officer's confirmation. It is not an action.",
    "bn": "মাঠ থেকে আসা রিপোর্ট, অফিসারের নিশ্চিতকরণের অপেক্ষায়। এটি কোনো পদক্ষেপ নয়।"
  },
  "latency_s": 1.932
}
```

- `place` is the best match over the city's places (`null` when no place
  clears the threshold; `place_candidates` then still lists the top three for
  the officer to pick from). `match_score` is in [0, 1].
- `kind` is one of `waterlogging | jam | accident | tree_fall | blockade |
  procession | fire | live_wire | other`; `kind_cues` and `severity_cues`
  are the exact words that decided them, so the officer can see why.
- `severity` is `low | medium | high`.

## How a report is built

1. **Audio** is decoded in memory: WAV with the standard library, WebM/Ogg
   (what browsers record) through `ffmpeg` over pipes. Nothing is written to
   disk.
2. **ASR** (below) with the language forced to Bengali unless asked
   otherwise. `confidence` is the geometric-mean token probability of the
   decoded text — a "check this one" signal, not an accuracy estimate.
3. **Place** (`places.py`): fuzzy matching over
   `cities/kolkata/landmarks.json` (the canonical ids and spellings) plus the
   events stream's `cities/kolkata/gazetteer.json` when it exists (read
   tolerantly; a landmark id always wins), plus everyday names officers
   actually say (ধর্মতলা → Esplanade, ডালহৌসি → BBD Bag, যুবভারতী → Salt Lake
   Stadium, পিজি হাসপাতাল → SSKM …). Matching works across scripts: Bengali,
   romanised ("Gariahat more e hatu jol") and English all reduce to a
   consonant skeleton (গড়িয়াহাট → `grht` ← "Gariahat"), because vowels are
   what Bengali ASR and romanisation vary most. Bengali spelling variants
   (ী/ি, ূ/ু, ড়/র, ণ/ন, শ/ষ/স, chandrabindu) are folded, and case endings
   (-এ, -র, -তে, -য়) are tried with and without.
4. **Kind and severity** (`kinds.py`): keyword rules in Bengali, English and
   romanised Bengali, explainable by design. A strong Bengali cue that the
   ASR misspelt ("যাঞ্জট" or "যান জোট" for যানজট) still counts when its
   consonant skeleton matches exactly (or very closely, for long cues); it is
   then shown with "(≈)" and weighs one point less. Simple negation ("জল
   নেই", "জমেনি", "no water") cancels a cue. A jam reported together with a
   cause (water, a fallen tree …) is labelled by the cause. Severity reads
   cues such as গোড়ালি/হাঁটু/কোমর জল (ankle/knee/waist-deep), আহত (injured),
   রাস্তা বন্ধ (road closed); fire and live wires are never below high.

## Models

| Job | Model | Licence | Runtime |
|---|---|---|---|
| ASR, Bengali | **`bengaliAI/tugstugi_bengaliai-asr_whisper-medium`** — Whisper-medium fine-tuned on Bengali (the Bengali.AI speech-recognition work) | Apache-2.0 | transformers, fp16, GPU |
| ASR, English / Hindi, and language detection for `lang=auto` | `openai/whisper-large-v3-turbo` | MIT | transformers, fp16, GPU; loaded only when en/hi/auto is used |
| TTS | **Svara-TTS v1** (`kenpath/svara-tts-v1`, Kenpath), 3B Orpheus-style, 19 Indian languages incl. Bengali, Hindi, Indian English | Apache-2.0 (see lineage note) | **llama.cpp** `llama-server` with a Q8_0 GGUF conversion (`scripts/convert_svara_gguf.sh`), or transformers bf16 (fallback; used in the container) |
| Codec | **SNAC 24 kHz** (`hubertsiuzdak/snac_24khz`) | MIT | torch, GPU |

**Why not the first choices.**
- *ASR: AI4Bharat IndicConformer* (`ai4bharat/indic-conformer-600m-multilingual`,
  MIT) is gated on Hugging Face. The download was refused (`403 GatedRepoError`
  for the deployment's token: access has not been requested on that account).
  Requesting it means accepting AI4Bharat's terms on the account owner's
  behalf, so it was left to them. Once granted, it can drop in behind the
  same `ASRBackend` interface. The fallback the plan named,
  `openai/whisper-large-v3-turbo`, was measured and is unusable for Bengali:
  it answers Bengali speech largely in **Devanagari script** even with the
  language forced (CER 58 %). Five open Whisper-family checkpoints were
  measured on the same audio (a sixth would not load: GPU memory on the
  shared box; see [Evaluation](#evaluation)); the Bengali fine-tune of
  Whisper-medium won clearly (CER 2.6 %), is the smallest of the accurate
  ones and is Apache-2.0. Turbo is kept for English and Hindi, where it is
  good.
- *TTS: AI4Bharat Indic Parler-TTS* (`ai4bharat/indic-parler-tts`,
  Apache-2.0) is gated the same way and was refused the same way. Of the open
  alternatives with Bengali, Svara-TTS v1 (Apache-2.0) covers Bengali, Hindi
  and Indian English in one model with a male and a female voice per
  language; `facebook/mms-tts-ben` was not used because it is CC BY-NC 4.0
  (non-commercial).
- *Lineage note:* Svara-TTS is fine-tuned from Canopy Labs' Orpheus 3B, which
  is itself built on Meta's Llama-3.2-3B (Llama 3.2 Community License), and
  is trained on SYSPIN, RASA, IndicTTS and SPICOR speech. The model is
  published as Apache-2.0; check the base-model and data terms before a
  commercial deployment.

**Two TTS runtimes, one output.** `SPEECH_TTS_BACKEND=auto` (default) uses
the llama.cpp backend when the GGUF and `llama-server` exist: the service
starts its own server on 127.0.0.1:`SPEECH_TTS_LLM_PORT` (8202 in production,
9164 in dev) at the first `/speech/speak` and stops it when it unloads. On
the GB10 it generates ≈60 speech tokens/s against ≈20 in eager transformers
(82 tokens are one second of audio). Otherwise it falls back to transformers
(the container does this: it ships no llama.cpp).

**The prompt matters.** The first evaluation round built the prompt the way
the Svara inference repository's encoder does (an `<|audio|>` marker and a
pre-filled start-of-speech). With it the model read its own speaker label
aloud — "Bengali …" — at the start of about one clip in three. The service
now builds the single human turn exactly as the model card's demo does and
lets the model open the speech itself; on the eight worst phrases the leak
went from 4/8 to 0/8 (`PROMPT_FORMAT` is part of the cache key, so old audio
is never served).

**The advisory voice.** Svara takes a speaker id and an end-of-utterance
style tag, not a free-text description. The house voice is the requested
language's **female speaker with the `<clear>` tag** — "a calm, clear,
unhurried voice reading a public traffic advisory at a steady pace"
(`SPEECH_TTS_VOICE_DESCRIPTION`); `voice: "male"` selects the male speaker.
Sampling is seeded from the text, so one text always gives the same audio and
the cache is exact. Long text is read sentence by sentence (। . ! ?).

**Memory and latency** (GB10, shared with the live system's models):

| Part | GPU memory (measured) | Latency (measured, 28 Oct 2026) |
|---|---|---|
| ASR, Bengali Whisper-medium fp16 | ≈2.0 GiB (process incl. CUDA context); 3.6 GiB with the en/hi model also loaded | median 1.54 s per clip; a whole report 1.55 s |
| ASR, en/hi (whisper-large-v3-turbo) | ≈1.6 GiB more, only once en/hi/auto is used | ≈1 s per clip warm; first load ≈11 s |
| TTS, llama.cpp Q8_0 | 4.0 GiB llama-server + 0.8 GiB in the service (SNAC codec, CUDA context) | median 6.8 s for a 4.3 s clip (1.57× real time) |
| TTS, transformers bf16 (container) | ≈7.0 GiB | median 16.5 s for a 4.4 s clip (3.45× real time) |
| first call | — | + model load: ASR ≈5 s, TTS (llama.cpp) ≈7 s, TTS (transformers) ≈21 s |

The GPU was shared with other tenants' models throughout (60–96 %
utilisation), so latencies vary by about 2× between runs.

Both models load on first use and unload after `SPEECH_IDLE_UNLOAD_S`
(600 s) idle. Before a load the service checks MemAvailable and refuses (503)
when the load would leave less than `SPEECH_MIN_FREE_GIB` (12 GiB).

## Privacy

- **No speaker identification**, no voice prints, no speaker embeddings.
- **No voice storage.** Uploaded audio is decoded in memory and discarded
  when the request ends; it is never written to disk or logged. Only the
  transcript leaves the service, inside the response.
- The only files the service writes are the advisory audio it synthesizes
  itself (TTS cache, keyed by a hash of model, voice, language and text).
- Advisory audio is synthetic and labelled so (`X-Speech-Label:
  synthetic-voice`); it imitates no real person.

## Evaluation

**What it is.** 30 short Kolkata field-report phrases in Bengali
([`eval/phrases.json`](eval/phrases.json); every place, all eight kinds),
spoken by **this service's own TTS** in two voices (female and male), then
transcribed — a **synthetic round trip**, 60 clips, 4.3 minutes of audio.
No person was recorded. Synthetic speech is clean and evenly paced, so these
numbers are an optimistic bound for real field audio. Raw transcripts and
per-clip results: [`eval/results.json`](eval/results.json); method:
[`eval/run_eval.py`](eval/run_eval.py). WER/CER ignore punctuation; "folded"
CER also forgives the Bengali spelling variants the place matcher folds.
Place is the top-1 match at the 0.80 threshold; place and kind use the final
rules on every model's transcripts (`run_eval.py rescore`).

Upper bound (the report rules on the reference text, no audio): place
**30/30**, kind **30/30**.

| ASR checkpoint | Size | Licence | WER | CER | CER folded | Place (top-1) | Kind | s / clip |
|---|---|---|---|---|---|---|---|---|
| **`bengaliAI/tugstugi_bengaliai-asr_whisper-medium`** | medium (0.77B) | Apache-2.0 | 11.5 % | **2.6 %** | 2.2 % | 53/60 | 60/60 | 1.42 |
| `ARTPARK-IISc/whisper-medium-vaani-bengali` | medium (0.77B) | MIT | 46.0 % | 10.1 % | 7.9 % | 52/60 | 47/60 | 1.84 |
| `bangla-speech-processing/BanglaASR` | small (0.24B) | MIT | 45.1 % | 13.2 % | 10.6 % | 51/60 | 45/60 | 1.16 |
| `openai/whisper-large-v3` | large (1.55B) | Apache-2.0 (card) · MIT (release) | 87.6 % | 40.9 % | 37.9 % | 47/60 | 36/60 | 3.33 |
| `openai/whisper-large-v3-turbo` | large-turbo (0.81B) | MIT | 97.0 % | 58.1 % | 55.3 % | 12/60 | 25/60 | 0.70 |
| `mozilla-ai/whisper-large-v3-bn` | large (1.55B) | Apache-2.0 | not measured: CUDA out of memory twice on the shared box | | | | | |

`openai/whisper-large-v3-turbo` answered 48 of the 60 Bengali clips partly or
wholly in Devanagari script; `whisper-large-v3` did so in 15 and romanised
others. "s / clip" is ASR time per clip on the shared GPU (median).

End to end through the running service (`POST /speech/report` with each WAV,
production ASR, final rules): WER 11.5 %, CER 2.6 %, place **53/60**, kind **60/60**, median 1.55 s per report (ASR 1.54 s); every report `UNVERIFIED-FIELD`. Of the seven place misses, six are clips where the name came out of the round trip misspelt ("বড়িয়াহাট", "সাইন সিটি", "লাসবিহারী", "কেষ্টকুন" …; most likely mispronounced by the TTS, since the same ASR transcribed the rest almost perfectly) and the matcher asserted no place; one ("কারাতলা" for Taratala) was matched to Kumartuli, wrongly. The right place was among the three candidates in 57 of 60.

**TTS.** With the llama.cpp backend the median synthesis time
was **6.8 s for a 4.3 s clip** (1.57× real time; best 1.49×; 90th percentile
12.2 s while other tenants loaded the GPU). In the first round, with
the earlier prompt layout and the transformers runtime, the median was
16.5 s per clip (3.45× real time) and the ASR heard the spoken speaker label
("বেঙ্গালী …") at the start of at least 9 of the 60 clips; in the second round
it heard it in none.

## Run

```bash
# once: the Q8_0 GGUF for the fast TTS backend (else TTS runs in transformers)
scripts/convert_svara_gguf.sh
# dev: port 9161, TTS llama-server on 9164; the HF cache must hold the models
PYTHONPATH=src SPEECH_PORT=9161 SPEECH_TTS_LLM_PORT=9164 python -m speech_service
curl -s -X POST -H 'Content-Type: audio/wav' --data-binary @report.wav 127.0.0.1:9161/speech/report
curl -s -X POST -H 'Content-Type: application/json' \
     -d '{"text":"গড়িয়াহাট মোড়ে জল জমেছে। বিকল্প পথ নিন।","lang":"bn"}' \
     127.0.0.1:9161/speech/speak -o advisory.wav
```

Production: port **8194**, loopback only (`infra/compose.ai-media.yml`,
`infra/docker/Dockerfile.speech`; the container mounts the host's Hugging
Face cache read-only and runs offline).

## Configuration

Environment variables (prefix `SPEECH_`, see `config.py`):

| Variable | Default | Meaning |
|---|---|---|
| `SPEECH_HOST` / `SPEECH_PORT` | `127.0.0.1` / `8194` | bind address |
| `SPEECH_ASR_MODEL` | the Bengali Whisper-medium | Bengali ASR checkpoint |
| `SPEECH_ASR_MULTILINGUAL_MODEL` | `openai/whisper-large-v3-turbo` | English/Hindi ASR and `auto` detection |
| `SPEECH_TTS_BACKEND` | `auto` | `llama` (GGUF in llama.cpp), `transformers`, or `auto` (llama when available) |
| `SPEECH_TTS_GGUF` / `SPEECH_LLAMA_SERVER_BIN` | `~/.cache/sahoshi/svara-gguf/svara-tts-v1-q8_0.gguf` / `~/llama.cpp/build/bin/llama-server` | llama.cpp backend files |
| `SPEECH_TTS_LLM_PORT` | `8202` | loopback port of the TTS llama-server the service starts |
| `SPEECH_TTS_MODEL` / `SPEECH_TTS_CODEC` | `kenpath/svara-tts-v1` / SNAC 24 kHz | TTS model (tokenizer) and codec |
| `SPEECH_TTS_STYLE_TAG` | `<clear>` | Svara end-of-utterance style |
| `SPEECH_TTS_CACHE_DIR` | `~/.cache/sahoshi/speech-tts` | advisory audio cache |
| `SPEECH_CITY_DIR` | `cities/kolkata` of the checkout | landmarks.json (+ gazetteer.json) |
| `SPEECH_PLACE_THRESHOLD` | `0.80` | minimum `match_score` to assert a place |
| `SPEECH_IDLE_UNLOAD_S` | `600` | unload models after this many idle seconds |
| `SPEECH_MIN_FREE_GIB` | `12` | refuse a load that would leave less memory |
| `SPEECH_MAX_AUDIO_BYTES` / `SPEECH_MAX_AUDIO_SECONDS` | 8 MB / 60 s | upload limits |
| `SPEECH_DECK_ORIGINS` | empty | CORS origins (none: the deck proxies) |

## Tests

```bash
python -m pytest -q -p no:cacheprovider          # offline, models mocked
SPEECH_SLOW=1 python -m pytest -q -m slow         # real TTS → ASR round trip on the GPU
python eval/run_eval.py --help                     # the synthetic round-trip evaluation
```

## Limits

- **The evaluation audio is synthetic.** No field officer was recorded; the
  WER/CER above measure ASR on clean TTS speech, which is easier than a phone
  at a waterlogged junction in the rain (wind, traffic, engine noise,
  code-switching). A pilot needs a consented, recorded test set of real
  officers' reports.
- ASR is Whisper-family, not an Indic-trained Conformer: Bengali place names
  come back with spelling variants, which the place matcher absorbs only up
  to a point (`place_candidates` is there for the officer).
- Kind and severity are keyword rules: they miss phrasings outside the lists
  (a broken-down bus is `other`); negation is handled only in its simplest
  forms ("জল নেই", "জমেনি", "no water", "not blocked").
- TTS runs slower than real time on the shared GPU (see the table), so
  advisories should be synthesized ahead and served from the cache.
- Svara-TTS's base-model and training-data terms should be checked before a
  commercial deployment (see the lineage note).
