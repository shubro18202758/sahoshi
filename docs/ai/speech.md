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
| ASR model | `bengaliAI/tugstugi_bengaliai-asr_whisper-medium` (Apache-2.0), transformers fp16 | of the eight checkpoints measured on the same audio it has the lowest word error (WER 11.2 %, CER 2.5 %) and every kind right; IndicConformer (the first choice, measured once access was granted on 29 Oct) has WER 11.9 %, one more place and three kinds wrong (see [the gated round](#the-29-oct-gated-round-indicconformer-and-indic-parler-tts)); the two newer candidates measured on 29 Oct (the Bengali.AI regional-dialect fine-tune and Mozilla's whisper-large-v3-bn) did not beat it on WER, and neither is better on place by more than one clip (see [the 29 Oct round](#the-29-oct-round-two-new-candidates)); the plan's fallback, whisper-large-v3-turbo, writes Bengali speech in Devanagari |
| Gated models | IndicConformer (ASR) and Indic Parler-TTS behind config: `SPEECH_ASR_BACKEND=indic_conformer`, `SPEECH_TTS_BACKEND=indic_parler`; access granted and both measured on 29 Oct: Parler live for TTS since 29 Oct, IndicConformer not adopted for ASR | both adapters load lazily; while a model cannot load (gate not granted, weights not downloaded, package missing) the service says `gated: request access at https://huggingface.co/…` in `/health` and the open model answers; a memory refusal stays a 503 and never switches models. [Runbook](#when-access-is-granted) |
| Indic Parler-TTS runtime | its own venv, run as a child process over pipes (`speech_service.parler_worker`) | `parler-tts` 0.2.3 pins `transformers==4.46.1`; the service runs on transformers 5.x. No port is opened |
| ASR for English/Hindi | `openai/whisper-large-v3-turbo` (MIT), also language detection for `lang=auto`; loaded on demand | the Bengali fine-tune transcribes English speech in Bengali letters; turbo handles en/hi well and is never given Bengali |
| TTS model | **Indic Parler-TTS** (`ai4bharat/indic-parler-tts` rev `660bc53`, Apache-2.0), live since 29 Oct 2026, in its own venv; Svara-TTS v1 (`kenpath/svara-tts-v1`, Apache-2.0) + SNAC 24 kHz codec (MIT) answers while Parler cannot load | Svara covers bn/hi/en in one open model with male and female voices; MMS-TTS Bengali is non-commercial (CC BY-NC). Indic Parler-TTS (the first choice, measured on 29 Oct) did better in the round trip (WER 8.2 % against 11.2 %, place 60/60 against 55/60) in half the synthesis time, so it was switched on ([runbook](#when-access-is-granted)) |
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
| **`bengaliAI/tugstugi_bengaliai-asr_whisper-medium`** (current) † | medium (0.77B) | Apache-2.0 | **11.2 %** | **2.5 %** | 2.1 % | 55/60 | **60/60** | 1.54 | 1.75 GiB |
| `ai4bharat/indic-conformer-600m-multilingual`, RNNT ‡ | 0.6B | MIT | 11.9 % | 2.6 % | **1.9 %** | **56/60** | 57/60 | 0.46 | — (CPU) |
| `ai4bharat/indic-conformer-600m-multilingual`, CTC ‡ | 0.6B | MIT | 12.9 % | 2.9 % | 2.2 % | **56/60** | 58/60 | 0.38 | — (CPU) |
| `bengaliAI/tugstugi_bengaliai-regional-asr_whisper-medium` † | medium (0.77B) | Apache-2.0 | 16.6 % | 3.9 % | 3.2 % | 55/60 | 59/60 | 1.14 | 1.75 GiB |
| `mozilla-ai/whisper-large-v3-bn` † | large (1.55B) | Apache-2.0 | 33.2 % | 8.6 % | 6.4 % | **56/60** | 50/60 | 2.16 | 3.43 GiB |
| `ARTPARK-IISc/whisper-medium-vaani-bengali` | medium (0.77B) | MIT | 46.0 % | 10.1 % | 7.9 % | 51/60 | 47/60 | 1.84 | — |
| `bangla-speech-processing/BanglaASR` | small (0.24B) | MIT | 45.1 % | 13.1 % | 10.6 % | 50/60 | 45/60 | 1.16 | — |
| `openai/whisper-large-v3` | large (1.55B) | Apache-2.0 (card) · MIT (release) | 87.6 % | 41.0 % | 37.9 % | 46/60 | 36/60 | 3.33 | — |
| `openai/whisper-large-v3-turbo` | large-turbo (0.81B) | MIT | 97.0 % | 58.1 % | 55.3 % | 9/60 | 25/60 | 0.70 | — |
| `facebook/omniASR-CTC-1B` (Omnilingual ASR) | 1B | Apache-2.0 | not measured: its runtime (`omnilingual-asr` → `fairseq2` → `fairseq2n`) has no Linux aarch64 build at any version, and pins torch 2.8 | | | | | | |

† measured on 29 Oct 2026, one model per process, on the shared GPU; the
other rows' times are from 28 Oct. "s / clip" is the median ASR time per
clip; the GPU was shared with other tenants both nights, so times vary by
about 2× between runs. "GPU peak" is PyTorch's allocator peak (weights and
activations, fp16) without the ≈0.5 GiB CUDA context; it was not recorded
on 28 Oct. `openai/whisper-large-v3-turbo` answered 48 of the 60 Bengali
clips partly or wholly in Devanagari script; `whisper-large-v3` did so in 15
and romanised others.

‡ measured on 29 Oct 2026 once access was granted (revision `2a77d30`, see
[the gated round](#the-29-oct-gated-round-indicconformer-and-indic-parler-tts)),
loaded as the model card does. Its ONNX graphs ran on ONNX Runtime's CPU
provider (the aarch64 wheel has no CUDA provider), so "s / clip" is CPU time
and "GPU peak" does not apply: with the model loaded the process held
3.9 GiB RSS and 0.26 GiB GPU (the TorchScript front end and the CUDA
context). Measured the same way, the current checkpoint held 2.0 GiB RSS and
2.0 GiB GPU.

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

### The 29 Oct gated round: IndicConformer and Indic Parler-TTS

Access to both gated models was granted to the deployment's Hugging Face
account on 29 Oct 2026. Both were downloaded with
`scripts/fetch_gated_models.sh` and measured the same evening on the same
60 clips, with the same method as above. Pinned revisions: IndicConformer
`2a77d305038dfc502fd9464e7d028b90381976cb`, Indic Parler-TTS
`660bc53c64ae83150613264111708a0465211237` (its description tokenizer,
`google/flan-t5-large`, `0613663d0d48ea86ba8cb3d7a44f0f65dc596a2a`).
Per-clip results: `eval/results.json` (`asr_comparison`, `round_gated_29oct`)
and `eval/results_indic_parler.json`. Memory is the process's RSS plus the
GPU memory `nvidia-smi` attributes to it, with the model loaded.

**IndicConformer's remote code.** `trust_remote_code` imports only
`model_onnx.py` (named in `config.json`; it has no relative imports, so
`model_ts.py` and `model_onnx_1b_batched_rnnt.py` in the same repo are never
loaded). It imports transformers, torch, numpy, json, os, onnxruntime and
`huggingface_hub.snapshot_download`. There is no subprocess, socket, eval/exec
or pickle call, and it writes no files. It reads `vocab.json`,
`language_masks.json`, 28 ONNX graphs (standard ONNX operators only, no
custom-op domains; their 366 external-data files are plain names in the same
folder) and one TorchScript file, `preprocessor.ts`. That file is NeMo's
mel-spectrogram front end (pre-emphasis, STFT, mel filterbank, log,
per-feature normalisation), and its pickles reference only torch's tensor
helpers. One thing goes beyond loading and inference: the model's own
`from_pretrained` calls `snapshot_download(repo)` and ignores `revision`,
`local_files_only` and `cache_dir`. Online, that contacts huggingface.co on
every load and fetches the assets of `main`, whatever commit the code was
pinned to. Offline (`HF_HUB_OFFLINE=1`, as the systemd unit and the container
run), it uses whichever commit the local cache's `main` points to. The
adapter now refuses assets from any commit other than
`SPEECH_ASR_INDIC_CONFORMER_REVISION`: the fallback answers and `/health`
says why. Two quirks were measured as published: it prints "Please check
FRAME_DURATION_MS…" on every load, and it builds its config from the class
defaults (SOS 5632) rather than from `config.json` (SOS 256).

**ASR: keep the current checkpoint.**

| On the Svara clips | Bengali Whisper-medium (current) | IndicConformer RNNT | IndicConformer CTC |
|---|---|---|---|
| WER / CER | **11.2 %** / **2.5 %** | 11.9 % / 2.6 % | 12.9 % / 2.9 % |
| CER folded | 2.1 % | **1.9 %** | 2.2 % |
| Place (top-1) | 55/60 | **56/60** | **56/60** |
| … of the misses, a wrong place asserted | **1** | 3 | 2 |
| Kind | **60/60** | 57/60 | 58/60 |
| s / clip (median) | 1.54 GPU (1.22 in this session) | 0.46 CPU | **0.38** CPU |
| Memory, model loaded | 2.0 GiB RSS + 2.0 GiB GPU | 3.9 GiB RSS + 0.3 GiB GPU | 3.9 GiB RSS + 0.3 GiB GPU |

IndicConformer comes close. Its folded CER is the lowest of all rows (many
of its errors are spelling variants), it gets one more place, and it is
2.6× faster than the current checkpoint was in the same session, without
the GPU. But it is not better on WER. It mishears three cue words, so three
reports come out as `other`: "অগরোধ" for অবরোধ (as
Mozilla's model did), and "টায়" and "কার" for তার, the live-wire cue. It also
asserts three wrong places (Ruby as Garia, Bagbazar as Bowbazar,
Chingrighata as Garia) where the current checkpoint asserts one. The
one-place gain is inside the current checkpoint's run-to-run spread:
re-run on the same files in this session, 6 of its 60 transcripts came out
differently (fp16 decoding on the shared GPU is not bit-stable), and place
moved from 55 to 53 (WER 11.4 %). IndicConformer gave identical transcripts
on a second run. The switch rule (better on WER *and* place) is not met. It
stays selectable (`SPEECH_ASR_BACKEND=indic_conformer`) and is worth
measuring again on real recordings. Because it runs on the CPU, it is also
an option if GPU memory becomes the constraint.

**TTS: Indic Parler-TTS does better and is live since 29 Oct 2026.** The 30 phrases were synthesized in both voices (Aditi and Arjun,
with the house caption) through a dev instance with
`SPEECH_TTS_BACKEND=indic_parler`, the worker running in its own venv. The
clips were then transcribed by the same ASR, exactly as the Svara clips were:

| Round trip | Svara-TTS v1, Q8_0 (live) | Indic Parler-TTS |
|---|---|---|
| Current ASR: WER / CER | 11.2 % / 2.5 % | **8.2 % / 1.2 %** |
| Current ASR: CER folded | 2.1 % | **0.9 %** |
| Current ASR: place / kind | 55/60 / **60/60** | **60/60** / 59/60 |
| IndicConformer RNNT on the same audio: WER / CER / place / kind | 11.9 % / 2.6 % / 56/60 / 57/60 | **11.4 % / 2.1 % / 60/60** / 57/60 |
| Synthesis per clip (median) | 6.8 s (6.96 s in this session) for 4.3 s of audio, 1.6× real time | **3.5 s** for 3.7 s, 0.97× real time |
| Cold start | llama-server ≈5 s, first clip 16 s | worker load 35 s, first clip 41 s |
| Peak memory (RSS + GPU) | 10.4 GiB: llama-server 4.1 + 4.0 (≈3.5 GB of that RSS is the GGUF it maps from disk), service with SNAC 1.5 + 0.9 | 11.5 GiB: worker 7.8 RSS while loading (fp32 weights pass through the CPU), 5.2 GPU while synthesizing; 2.0–5.6 RSS + 4.6 GPU once loaded |

Every place name came through, including the five that the Svara round
trip missed (Gariahat, Rashbehari, Kestopur and Science City came out
misspelt, Taratala was matched to Kumartuli). The one kind miss: Aditi
split Khidirpur ("খিদের পুরে"), and "পুরে", read
as burnt, made it a fire report; both ASRs heard the split. As a spot check
on advisories, three two-sentence advisories per language were spoken in the
female voice and transcribed back (Bengali by the current checkpoint, English
and Hindi by whisper-large-v3-turbo). Parler against Svara, WER: Bengali 0 %
against 3.2 %, English 17.5 % against 20 %, Hindi 36 % against 33 %. The
English and Hindi errors are mostly the same place names with both models
("Garia Heart", "Sildar"). Parler took 5.6 s per advisory against Svara's
10.0 s (medians). Nobody listened to the audio. This measures how well an
ASR understands the voice, not how it sounds to a resident, so someone should
listen to a few advisories in each language before the switch.

**Switched on, 29 Oct 2026.** The three switch lines (step 4 below) are in
`sahoshi.env` and the live unit was restarted. On the live service the first
Bengali advisory after a restart took 45–55 s (the worker loads), later ones
about 7 s for 7 s of audio; it unloads after 10 idle minutes like the other
models, and the console waits up to 90 s. Parler spoke Bengali about 18 dB
quieter than English (RMS −37 against −18 dBFS), so every voice is now
levelled to about −20 dBFS RMS with the peak held under −1 dBFS
(`audio.level_speech`; the cache key carries `LEVEL_FORMAT`, so older audio is
regenerated). Live round trip after the switch, transcribed by the live ASR:
Bengali "গড়িয়াহাট মোড়ে জল জমেছে …" came back word for word apart from
"অ্যাভিনো" for অ্যাভিনিউ; English and Hindi came back with the same
place-name spellings as above. Rollback: set `SPEECH_TTS_BACKEND=auto` and
restart `sahoshi-ai-speech` (Svara answers again).

## When access is granted

Both preferred models are gated on Hugging Face; the account owner requests
access on each page (accepting AI4Bharat's terms):
<https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual> and
<https://huggingface.co/ai4bharat/indic-parler-tts>. Nothing here tries to
get around the gate. Access was granted on 29 Oct 2026; steps 1 to 3 were
done that day ([results](#the-29-oct-gated-round-indicconformer-and-indic-parler-tts)),
and step 4 (TTS) was applied the same day. Commands run from `services/speech`;
`$SVC_PY` is the service venv's python, `$CLIPS` the evaluation WAVs.

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
   scripts/make_parler_venv.sh ~/argus/sahoshi/.venvs/speech-parler $SVC_PY   # Parler's own venv (transformers 4.46.1)
   ```
   The model card's install line also has torchaudio, but `model_onnx.py`
   does not import it: a load and a transcription with torchaudio blocked
   worked. On 29 Oct the Parler venv was built at
   `~/argus/sahoshi/.venvs/speech-parler`. The live service venv
   (`.venvs/ai-media`) still has no onnxruntime; it needs it only for
   IndicConformer.
3. **Evaluate** on the same 60 clips, one model per process:
   ```bash
   HF_HUB_OFFLINE=1 $SVC_PY eval/run_eval.py asr --audio $CLIPS --models indic_conformer       # RNNT
   HF_HUB_OFFLINE=1 $SVC_PY eval/run_eval.py asr --audio $CLIPS --models indic_conformer@ctc   # CTC
   ```
   It adds a row to `eval/results.json` (or prints `SKIPPED: gated: …`);
   `SPEECH_ASR_INDIC_CONFORMER_REVISION` in the environment pins the commit
   here too.
   Switch only if it beats the current row on WER and place. For TTS, start
   a dev instance with the Parler settings below, re-synthesize the set into
   a new directory and transcribe it with the current ASR, writing to a file
   of its own so the Svara round trip in `results.json` stays as it is:
   ```bash
   PYTHONPATH=src HF_HUB_OFFLINE=1 SPEECH_PORT=9161 SPEECH_TTS_BACKEND=indic_parler \
     SPEECH_TTS_PARLER_PYTHON=$HOME/argus/sahoshi/.venvs/speech-parler/bin/python \
     SPEECH_TTS_LLM_PORT=9164 SPEECH_TTS_CACHE_DIR=/tmp/parler-cache $SVC_PY -m speech_service &
   $SVC_PY eval/run_eval.py --results eval/results_indic_parler.json synth --base http://127.0.0.1:9161 --audio $PARLER_CLIPS
   HF_HUB_OFFLINE=1 $SVC_PY eval/run_eval.py --results eval/results_indic_parler.json asr --audio $PARLER_CLIPS \
     --models bengaliAI/tugstugi_bengaliai-asr_whisper-medium
   ```
   Compare with the Svara round trip, and listen to a few advisories in
   each language.
4. **Switch** in `~/.config/sahoshi/sahoshi.env` (absolute paths: the
   systemd unit does not expand variables there), then restart the speech
   service. TTS, recommended on 29 Oct:
   ```bash
   SPEECH_TTS_BACKEND=indic_parler
   SPEECH_TTS_PARLER_PYTHON=/home/sandy050405/argus/sahoshi/.venvs/speech-parler/bin/python
   SPEECH_TTS_PARLER_REVISION=660bc53c64ae83150613264111708a0465211237
   ```
   ASR, not recommended on 29 Oct (it also needs onnxruntime in the service
   venv, step 2):
   ```bash
   SPEECH_ASR_BACKEND=indic_conformer
   SPEECH_ASR_INDIC_CONFORMER_REVISION=2a77d305038dfc502fd9464e7d028b90381976cb
   SPEECH_ASR_INDIC_CONFORMER_DECODER=rnnt            # RNNT had the lower WER
   ```
   `SPEECH_TTS_PARLER_REVISION` came with the 29 Oct evaluation; code from
   before it ignores the line and loads the commit in the cache, which is
   the evaluated one. The Svara advisories in the TTS cache are not reused
   (the cache key names the model). Synthesize the standing advisories once
   after the restart, so that no reader waits for the worker's 35 s cold
   start. While loaded, the worker holds about as much memory as Svara's
   llama-server; it stops after `SPEECH_IDLE_UNLOAD_S` idle seconds.
   `GET /health` shows `"active": "preferred"` or, if a model still cannot
   load, `"active": "fallback"` with the reason in `preferred_error`; the
   `asr.model` of a report and the `X-Speech-Model` header of an advisory
   name the model that actually answered. Back out by removing the lines.

Before access was granted, this was checked without the gated weights:
both adapters against the real gate (online they answer "gated: request
access at …", offline "weights
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
reports stay on whisper-large-v3-turbo, as now. Its ONNX graphs run on the
CPU here (onnxruntime's aarch64 wheel has no CUDA provider). It reports no
confidence (the published inference returns text only), so the deck shows
none for those reports. Parler voices are the model card's recommended speakers
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
- IndicConformer and Indic Parler-TTS were measured on 29 Oct on the
  synthetic set only. Indic Parler-TTS is live since 29 Oct; its
  advisories were checked by transcription, not yet by a listener; IndicConformer was not better than the
  current ASR ([the gated round](#the-29-oct-gated-round-indicconformer-and-indic-parler-tts)).
  Both stay behind config ([runbook](#when-access-is-granted)).
