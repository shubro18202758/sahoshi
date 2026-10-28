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
| ASR model | `bengaliAI/tugstugi_bengaliai-asr_whisper-medium` (Apache-2.0), transformers fp16 | IndicConformer (first choice) is gated and not yet granted; of seven open checkpoints measured on the same audio it has the lowest error (WER 11.2 %, CER 2.5 %) and every kind right; the two newer candidates measured on 29 Oct (the Bengali.AI regional-dialect fine-tune and Mozilla's whisper-large-v3-bn) did not beat it on WER, and neither is better on place by more than one clip (see [the 29 Oct round](#the-29-oct-round-two-new-candidates)); the plan's fallback, whisper-large-v3-turbo, writes Bengali speech in Devanagari |
| Preferred gated models | IndicConformer (ASR) and Indic Parler-TTS behind config: `SPEECH_ASR_BACKEND=indic_conformer`, `SPEECH_TTS_BACKEND=indic_parler` | both adapters load lazily; while a model cannot load (gate not granted, weights not downloaded, package missing) the service says `gated: request access at https://huggingface.co/…` in `/health` and the open model answers; a memory refusal stays a 503 and never switches models. [Runbook](#when-access-is-granted) |
| Indic Parler-TTS runtime | its own venv, run as a child process over pipes (`speech_service.parler_worker`) | `parler-tts` 0.2.3 pins `transformers==4.46.1`; the service runs on transformers 5.x. No port is opened |
| ASR for English/Hindi | `openai/whisper-large-v3-turbo` (MIT), also language detection for `lang=auto`; loaded on demand | the Bengali fine-tune transcribes English speech in Bengali letters; turbo handles en/hi well and is never given Bengali |
| TTS model | Svara-TTS v1 (`kenpath/svara-tts-v1`, Apache-2.0) + SNAC 24 kHz codec (MIT) | Indic Parler-TTS (first choice) is gated and not yet granted (adapter ready); Svara covers bn/hi/en in one open model with male and female voices; MMS-TTS Bengali is non-commercial (CC BY-NC) |
| TTS runtime | llama.cpp `llama-server` on a Q8_0 GGUF conversion, started on demand; transformers bf16 as the fallback (and in the container) | ≈60 vs ≈20 speech tokens/s on the GB10: 6.8 s instead of 16.5 s per short advisory |
| TTS prompt | the single human turn as the model card's demo builds it | an earlier layout made the model read its speaker label ("Bengali …") aloud in at least 9 of 60 clips; the demo layout: 0 of 60 |
| Voice | Female speaker of the requested language + `<clear>` style tag; seeded sampling | calm and clear for advisories; one text → one waveform, so the cache is exact |
| Place matching | fuzzy over landmarks.json + gazetteer.json + spoken aliases, cross-script consonant skeleton; a name split in two ("গড়িয়া হাট") goes to the whole name, not to the place its first half spells | ASR spells Bengali names inconsistently; officers say "ধর্মতলা", not "Esplanade" |
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
  recorded. The 29 Oct round used the same 60 WAV files as the 28 Oct round
  (durations checked clip by clip).
- **Rules:** place and kind are re-scored on every checkpoint's saved
  transcripts with the current rules (`run_eval.py rescore`): the city
  gazetteer (203 places) and the split-name rule below. The figures here
  therefore differ slightly from the 28 Oct table.
- **Upper bound** (report rules on the reference text): place 30/30, kind 30/30.

| ASR checkpoint | Size | Licence | WER | CER | CER folded | Place (top-1) | Kind | s / clip | GPU peak |
|---|---|---|---|---|---|---|---|---|---|
| **`bengaliAI/tugstugi_bengaliai-asr_whisper-medium`** (current) † | medium (0.77B) | Apache-2.0 | **11.2 %** | **2.5 %** | **2.1 %** | 55/60 | **60/60** | 1.54 | 1.75 GiB |
| `bengaliAI/tugstugi_bengaliai-regional-asr_whisper-medium` † | medium (0.77B) | Apache-2.0 | 16.6 % | 3.9 % | 3.2 % | 55/60 | 59/60 | 1.14 | 1.75 GiB |
| `mozilla-ai/whisper-large-v3-bn` † | large (1.55B) | Apache-2.0 | 33.2 % | 8.6 % | 6.4 % | **56/60** | 50/60 | 2.16 | 3.43 GiB |
| `ARTPARK-IISc/whisper-medium-vaani-bengali` | medium (0.77B) | MIT | 46.0 % | 10.1 % | 7.9 % | 51/60 | 47/60 | 1.84 | — |
| `bangla-speech-processing/BanglaASR` | small (0.24B) | MIT | 45.1 % | 13.1 % | 10.6 % | 50/60 | 45/60 | 1.16 | — |
| `openai/whisper-large-v3` | large (1.55B) | Apache-2.0 (card) · MIT (release) | 87.6 % | 41.0 % | 37.9 % | 46/60 | 36/60 | 3.33 | — |
| `openai/whisper-large-v3-turbo` | large-turbo (0.81B) | MIT | 97.0 % | 58.1 % | 55.3 % | 9/60 | 25/60 | 0.70 | — |
| `facebook/omniASR-CTC-1B` (Omnilingual ASR) | 1B | Apache-2.0 | not measured: its runtime (`omnilingual-asr` → `fairseq2` → `fairseq2n`) has no Linux aarch64 build at any version, and pins torch 2.8 | | | | | | |
| `ai4bharat/indic-conformer-600m-multilingual` | 0.6B | MIT | not measured: gated, access not granted yet (adapter ready, see below) | | | | | | |

† measured on 29 Oct 2026, one model per process, on the shared GPU; the
other rows' times are from 28 Oct. "s / clip" is the median ASR time per
clip; the GPU was shared with other tenants both nights, so times vary by
about 2× between runs. "GPU peak" is PyTorch's allocator peak (weights and
activations, fp16) without the ≈0.5 GiB CUDA context; it was not recorded
on 28 Oct. `openai/whisper-large-v3-turbo` answered 48 of the 60 Bengali
clips partly or wholly in Devanagari script; `whisper-large-v3` did so in 15
and romanised others.

### The 29 Oct round: two new candidates

- **`bengaliAI/tugstugi_bengaliai-regional-asr_whisper-medium`** (Apache-2.0,
  card updated 11 Aug 2026; trained on ten regional Bengali dialects, Ben-10):
  worse on standard Bengali speech than the current checkpoint (WER 16.6 %
  against 11.2 %), equal on place (55/60), one kind wrong ("অগরত" for
  অবরোধ). Same size and memory. It may suit dialect-heavy speech; that needs
  real recordings to show.
- **`mozilla-ai/whisper-large-v3-bn`** (Apache-2.0): it loaded this time
  (fp16, 3.4 GiB peak). One more place right (56/60: it heard Taratala,
  Kestopur and Rashbehari where the current checkpoint misspelt them, and
  missed Chingrighata and Rashbehari in two other clips), but three times the word errors
  (WER 33.2 %) and ten kinds wrong (50/60) because it misspells the cue words
  ("আগুম" for আগুন, "যানজন" for যানজট, "অগরোধ" for অবরোধ); 1.4× the
  latency and twice the memory.
- **Decision: keep `bengaliAI/tugstugi_bengaliai-asr_whisper-medium`.** The
  rule was "better on WER *and* place, within about 2× latency": neither
  candidate is better on WER, and a one-clip place gain does not pay for ten
  wrong kinds. Both stay selectable with `SPEECH_ASR_MODEL=<id>`.
- **Split names.** With the city gazetteer loaded, an ASR that splits
  "গড়িয়াহাট" into "গড়িয়া হাট" had its first half matched exactly to *Garia*.
  The matcher now lets the longer name win when the split words spell it
  whole (same consonant skeleton); "গড়িয়া" alone is still Garia, and
  "সেক্টর ফাইভ এ" stays Sector V. This fixed one clip for each of the three
  checkpoints above and changed nothing else in the 420 transcripts.

- **End to end** through `POST /speech/report` (dev instance of this branch,
  default config, 29 Oct): WER 11.2 %, CER 2.5 %, place **55/60**, kind
  **60/60**, median **1.29 s** per report (ASR 1.26 s); every report
  `UNVERIFIED-FIELD`. Of the five place misses, four are names that came out
  of the round trip misspelt ("বড়িয়াহাট", "লাসবিহারী", "কেষ্টকুন", "সাইল
  সিটি"; most likely mispronounced by the TTS) and the matcher asserted no
  place; one ("কারাতলা" for Taratala) was matched to Kumartuli, wrongly.
- **TTS:** median 6.8 s to synthesize a 4.3 s clip with the llama.cpp
  backend (16.5 s with transformers).
- **Earlier rounds.** The first round's audio had the speaker-label defect
  (the TTS said "Bengali …" before the phrase in at least 9 of 60 clips) and
  only three ASR candidates; it is kept in `results.json` as
  `round1_label_leak` for the record.

## When access is granted

Both preferred models are gated on Hugging Face; the account owner requests
access on each page (accepting AI4Bharat's terms):
<https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual> and
<https://huggingface.co/ai4bharat/indic-parler-tts>. Nothing here tries to
get around the gate. Commands run from `services/speech`; `$SVC_PY` is the
service venv's python, `$CLIPS` the evaluation WAVs.

1. **Check and download** (the service runs offline, so the weights must be
   in the local cache first):
   ```bash
   PY=$SVC_PY scripts/fetch_gated_models.sh check   # "access granted" / "gated: request access at …"
   PY=$SVC_PY scripts/fetch_gated_models.sh all     # downloads; prints the commit to pin
   ```
2. **Runtime packages.** IndicConformer runs its own ONNX code
   (`trust_remote_code`): read `model_onnx.py` in the downloaded snapshot,
   then
   ```bash
   $SVC_PY -m pip install onnxruntime==1.31.1              # CPU (installs and imports on the GB10); onnxruntime-gpu has an aarch64 wheel, untested here
   $SVC_PY -m pip install --no-deps torchaudio==2.11.0     # the card's install line has torchaudio; none is built for torch 2.14, 2.11's transforms run on it
   scripts/make_parler_venv.sh ~/argus/sahoshi/.venvs/speech-parler $SVC_PY   # Parler's own venv (transformers 4.46.1)
   ```
3. **Evaluate** on the same 60 clips, one model per process:
   ```bash
   HF_HUB_OFFLINE=1 $SVC_PY eval/run_eval.py asr --audio $CLIPS --models indic_conformer       # RNNT
   HF_HUB_OFFLINE=1 $SVC_PY eval/run_eval.py asr --audio $CLIPS --models indic_conformer@ctc   # CTC
   ```
   It adds a row to `eval/results.json` (or prints `SKIPPED: gated: …`);
   `SPEECH_ASR_INDIC_CONFORMER_REVISION` in the environment pins the commit
   here too.
   Switch only if it beats the current row on WER and place. For TTS, start
   a dev instance with the Parler settings below, re-synthesize the set
   (`run_eval.py synth`) into a new directory, run `run_eval.py asr` with the
   current ASR on that audio and compare with the Svara round trip; listen
   to a few advisories in each language.
4. **Switch** in `~/.config/sahoshi/sahoshi.env`, then restart the speech
   service:
   ```bash
   SPEECH_ASR_BACKEND=indic_conformer
   SPEECH_ASR_INDIC_CONFORMER_REVISION=<commit printed in step 1>
   SPEECH_ASR_INDIC_CONFORMER_DECODER=rnnt            # or ctc, whichever won in step 3
   SPEECH_TTS_BACKEND=indic_parler
   SPEECH_TTS_PARLER_PYTHON=$HOME/argus/sahoshi/.venvs/speech-parler/bin/python
   ```
   `GET /health` shows `"active": "preferred"` or, if a model still cannot
   load, `"active": "fallback"` with the reason in `preferred_error`; the
   `asr.model` of a report and the `X-Speech-Model` header of an advisory
   name the model that actually answered. Back out by removing the lines.

What has been checked without the gated weights: both adapters against the
real gate (online they answer "gated: request access at …", offline "weights
are not in the local Hugging Face cache … gated: request access at …"); the
fallback in a running dev instance with `SPEECH_ASR_BACKEND=indic_conformer`
(a Bengali report was answered by the Whisper checkpoint, Gariahat /
waterlogging, `UNVERIFIED-FIELD`, while `/health` showed `"active":
"fallback"` and the gated reason) and with `SPEECH_TTS_BACKEND=indic_parler`
(the Parler worker started in its venv, reported the gate and was stopped;
Svara spoke the Bengali advisory, `X-Speech-Model` naming Svara, 18.5 s
including every cold start); and the Parler worker path end
to end with the **open** Parler-TTS Mini v1.1 (Indic Parler-TTS's base
model, English only) in the venv `make_parler_venv.sh` builds: the worker
loaded in 40 s, spoke 4.3 s of 44.1 kHz audio for "Waterlogging at Gariahat
crossing. Please take another route through Rashbehari." and
whisper-large-v3-turbo heard "Waterlogging at Gilber Hutt Crossing, please
take another route through Rash Bihari." That checks the plumbing, not
Indic Parler-TTS.

Notes. IndicConformer serves Bengali (and Hindi) only; English and Hindi
reports stay on whisper-large-v3-turbo, as now. It reports no confidence
(the published inference returns text only), so the deck shows none for
those reports. Parler voices are the model card's recommended speakers
(Bengali Aditi/Arjun, English Mary/Thoma, Hindi Divya/Rohit) with the house
caption `SPEECH_TTS_PARLER_DESCRIPTION`. The model cards now point to
successors, `bodhan-ai/indic-transcribe-core` and `bodhan-ai/indic-speak`;
both are gated and under a custom licence (Bodhan AI Open Model License),
which needs reading before they are considered.

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
  gated access is granted on the deployment's Hugging Face account; both are
  wired in behind config and fall back to the open models until then
  ([runbook](#when-access-is-granted)). Neither has been measured here: the
  adapters were tested offline with stand-ins and against the real gate
  (which answers "gated: request access at …"), not with the real weights.
