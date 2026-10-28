# Bengali voice (AI row C)

**What it does.** A field officer speaks a short report in Bengali; the
service returns a structured report (place from the city gazetteer, kind,
severity, transcript) that enters the system as `UNVERIFIED-FIELD` and waits
for an officer's confirmation. The other way round, public advisories are
read out in Bengali, English or Hindi.

Service: [`services/speech`](../../services/speech/README.md) · production
port **8194** (loopback) · dev port 9161.

## Decision record

| Question | Decision | Why |
|---|---|---|
| ASR model | `bengaliAI/tugstugi_bengaliai-asr_whisper-medium` (Apache-2.0), transformers fp16 | IndicConformer (first choice) is gated and was refused; of five open Whisper-family checkpoints measured on the same audio it had by far the lowest error (CER 2.6 %); the plan's fallback, whisper-large-v3-turbo, writes Bengali speech in Devanagari |
| ASR for English/Hindi | `openai/whisper-large-v3-turbo` (MIT), also language detection for `lang=auto`; loaded on demand | the Bengali fine-tune transcribes English speech in Bengali letters; turbo handles en/hi well and is never given Bengali |
| TTS model | Svara-TTS v1 (`kenpath/svara-tts-v1`, Apache-2.0) + SNAC 24 kHz codec (MIT) | Indic Parler-TTS (first choice) is gated and was refused; Svara covers bn/hi/en in one open model with male and female voices; MMS-TTS Bengali is non-commercial (CC BY-NC) |
| TTS runtime | llama.cpp `llama-server` on a Q8_0 GGUF conversion, started on demand; transformers bf16 as the fallback (and in the container) | ≈60 vs ≈20 speech tokens/s on the GB10: 6.8 s instead of 16.5 s per short advisory |
| TTS prompt | the single human turn as the model card's demo builds it | an earlier layout made the model read its speaker label ("Bengali …") aloud in at least 9 of 60 clips; the demo layout: 0 of 60 |
| Voice | Female speaker of the requested language + `<clear>` style tag; seeded sampling | calm and clear for advisories; one text → one waveform, so the cache is exact |
| Place matching | fuzzy over landmarks.json + gazetteer.json + spoken aliases, cross-script consonant skeleton | ASR spells Bengali names inconsistently; officers say "ধর্মতলা", not "Esplanade" |
| Kind / severity | keyword rules (bn/en/romanised) with the deciding words returned | explainable to the officer; no extra model |
| Report state | always `UNVERIFIED-FIELD`, `requires_confirmation: true` | the AI proposes, a named officer decides |
| Privacy | audio decoded in memory and dropped; no speaker identification; no voice storage | only the transcript is needed |
| Lifecycle | lazy load, unload after 10 idle minutes, refuse below a 12 GiB floor | the GB10 is shared with live models |

## Integration contract

- `POST /speech/report` with the browser recording as the raw body
  (`Content-Type: audio/webm` from `MediaRecorder`, or `audio/wav`), or JSON
  `{"text": "…"}` for a typed report.
- Show the answer as **"Field report · unverified"** with the transcript, the
  matched place (and `place_candidates` when `place` is `null`), kind and
  severity, and the cue words. An officer confirms, edits or dismisses it.
- `POST /speech/speak` returns `audio/wav`; the public page plays it with a
  "synthetic voice" note (`X-Speech-Label: synthetic-voice`).
- `503` = the model cannot load right now (memory); retry later.

## Evaluation

Full method and per-clip results:
[`services/speech/README.md#evaluation`](../../services/speech/README.md#evaluation),
[`services/speech/eval/results.json`](../../services/speech/eval/results.json).

- **Set:** 30 short Kolkata field-report phrases in Bengali (every kind,
  thirty different places), spoken by the service's own TTS in a female and a
  male voice: 60 clips. This is a **synthetic round trip**; nobody was
  recorded.
- **Upper bound** (report rules on the reference text): place 30/30, kind 30/30.

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

- **End to end** through `POST /speech/report` with the chosen ASR:
  WER 11.5 %, CER 2.6 %, place **53/60**, kind **60/60**, median 1.55 s per report (ASR 1.54 s); every report `UNVERIFIED-FIELD`. Of the seven place misses, six are clips where the name came out of the round trip misspelt ("বড়িয়াহাট", "সাইন সিটি", "লাসবিহারী", "কেষ্টকুন" …; most likely mispronounced by the TTS, since the same ASR transcribed the rest almost perfectly) and the matcher asserted no place; one ("কারাতলা" for Taratala) was matched to Kumartuli, wrongly. The right place was among the three candidates in 57 of 60.
- **TTS:** median 6.8 s to synthesize a 4.3 s clip with the llama.cpp
  backend (16.5 s with transformers).
- **Two rounds.** The first round's audio had the speaker-label defect
  (the TTS said "Bengali …" before the phrase in at least 9 of 60 clips) and
  only three ASR candidates; it is kept in `results.json` as
  `round1_label_leak` for the record. All figures above are from the second
  round.

## Limits

- The evaluation audio is **synthetic** (the service's own TTS). Real field
  audio — phones, wind, rain, traffic, code-switching between Bengali,
  English and Hindi — will be harder. Before a pilot: a consented recording
  set from officers in one division, and a re-run of this evaluation on it.
- Whisper-family ASR is not trained for Kolkata place names; the place
  matcher absorbs spelling variants up to a point and returns candidates
  when it is unsure.
- Kind and severity are keyword rules with simple negation; they are
  explainable but not exhaustive.
- TTS is slower than real time on the shared GPU: synthesize advisories
  ahead and serve them from the cache.
- IndicConformer and Indic Parler-TTS remain the preferred models once their
  gated access is granted on the deployment's Hugging Face account; both fit
  behind the existing backend interfaces.
