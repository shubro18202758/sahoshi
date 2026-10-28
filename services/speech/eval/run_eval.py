"""Synthetic round-trip evaluation of the speech service.

This is honest about what it measures: there are no recordings of people.
Each phrase in ``phrases.json`` is spoken by the service's own TTS (two
voices), then transcribed. WER/CER therefore measure ASR on *synthetic*
Bengali speech — a lower bound on difficulty compared with a real field
officer on a phone in the rain — and place/kind accuracy measure the whole
report pipeline on that audio.

    # 1. synthesize through the running service (POST /speech/speak)
    python eval/run_eval.py synth --base http://127.0.0.1:9161 --audio /tmp/sahoshi-speech-eval
    # 2. compare ASR checkpoints in-process on the same audio
    python eval/run_eval.py asr --audio /tmp/sahoshi-speech-eval --models openai/whisper-large-v3,...
    #    (one model per process keeps the GPU footprint to one model; an
    #    IndicConformer run is --models indic_conformer or indic_conformer@ctc)
    # 3. end-to-end through the running service (POST /speech/report)
    python eval/run_eval.py api --base http://127.0.0.1:9161 --audio /tmp/sahoshi-speech-eval

Results go to ``eval/results.json`` (merged per stage).
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from speech_service.places import _bn_compose, fold_bn  # noqa: E402

PHRASES = json.loads((HERE / "phrases.json").read_text(encoding="utf-8"))["phrases"]
VOICES = ("female", "male")
RESULTS = HERE / "results.json"
_PUNCT = re.compile(r"[।,.!?;:\"'“”‘’()\-–—]")


def norm(text: str, fold: bool = False) -> str:
    t = _bn_compose(text)
    t = _PUNCT.sub(" ", t).lower()
    if fold:
        t = fold_bn(t)
    return " ".join(t.split())


def _lev(a: list, b: list) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, y in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y))
        prev = cur
    return prev[-1]


def wer_cer(refs: list[str], hyps: list[str], fold: bool = False) -> tuple[float, float]:
    we = wn = ce = cn = 0
    for r, h in zip(refs, hyps):
        r, h = norm(r, fold), norm(h, fold)
        we += _lev(r.split(), h.split())
        wn += len(r.split())
        ce += _lev(list(r.replace(" ", "")), list(h.replace(" ", "")))
        cn += len(r.replace(" ", ""))
    return round(we / max(1, wn), 4), round(ce / max(1, cn), 4)


def _merge(key: str, value) -> None:
    doc = json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else {}
    doc[key] = value
    RESULTS.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")


def _post(url: str, data: bytes, ctype: str, timeout: float = 600) -> tuple[bytes, dict]:
    req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": ctype})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), {k.lower(): v for k, v in r.headers.items()}


def cmd_synth(args) -> None:
    out = Path(args.audio)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for voice in VOICES:
        for p in PHRASES:
            body = json.dumps({"text": p["text"], "lang": "bn", "voice": voice}).encode()
            t0 = time.perf_counter()
            wav, hdr = _post(args.base.rstrip("/") + "/speech/speak", body, "application/json")
            dt = time.perf_counter() - t0
            (out / f"{p['id']}_{voice}.wav").write_bytes(wav)
            rows.append({"id": p["id"], "voice": voice, "seconds": float(hdr.get("x-speech-seconds", 0)),
                         "latency_s": round(dt, 2), "cached": hdr.get("x-speech-cached") == "1"})
            print(f"{p['id']} {voice} audio={rows[-1]['seconds']}s synth={dt:.1f}s", flush=True)
    fresh = [r for r in rows if not r["cached"]]
    rtf = [r["latency_s"] / r["seconds"] for r in fresh if r["seconds"]]
    _merge("tts", {
        "model": hdr.get("x-speech-model"), "voices": [f"bn-{v}" for v in VOICES],
        "n": len(rows), "audio_seconds_total": round(sum(r["seconds"] for r in rows), 1),
        "synth_seconds_median": round(statistics.median([r["latency_s"] for r in fresh]), 2) if fresh else None,
        "real_time_factor_median": round(statistics.median(rtf), 2) if rtf else None,
        "rows": rows,
    })


def _score(rows: list[dict]) -> dict:
    refs = [r["ref"] for r in rows]
    hyps = [r["hyp"] for r in rows]
    w, c = wer_cer(refs, hyps)
    wf, cf = wer_cer(refs, hyps, fold=True)
    return {
        "n": len(rows), "wer": w, "cer": c, "wer_folded": wf, "cer_folded": cf,
        "place_accuracy": round(sum(r["place_ok"] for r in rows) / len(rows), 3),
        "kind_accuracy": round(sum(r["kind_ok"] for r in rows) / len(rows), 3),
        "asr_seconds_median": round(statistics.median(r["asr_s"] for r in rows), 3),
    }


def _reset_gpu_peak() -> None:
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
    except Exception:  # CPU-only run: no peak to report
        pass


def _gpu_peak_gib() -> dict | None:
    """Peak memory PyTorch's CUDA allocator held during the run (weights and
    activations; the CUDA context, about 0.5 GiB, is not included). A backend
    that runs outside PyTorch's allocator (ONNX Runtime) shows ~0 here."""
    try:
        import torch

        if not torch.cuda.is_available():
            return None
        return {"gpu_peak_alloc_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2),
                "gpu_peak_reserved_gib": round(torch.cuda.max_memory_reserved() / 2**30, 2)}
    except Exception:
        return None


def asr_for_eval(spec: str, *, min_free_gib: float = 8):
    """``<hf-id>`` → a Whisper checkpoint; ``indic_conformer[:<hf-id>][@ctc|@rnnt]``
    → the IndicConformer adapter, with **no** fallback (a gated or missing
    model is reported as SKIPPED, never measured as something else)."""
    import os

    from speech_service.asr import IndicConformerASR, WhisperASR

    if spec.startswith("indic_conformer"):
        rest = spec[len("indic_conformer"):].lstrip(":")
        decoder = "rnnt"
        if "@" in rest:
            rest, decoder = rest.rsplit("@", 1)
        return IndicConformerASR(rest or IndicConformerASR.DEFAULT_MODEL, decoder=decoder,
                                 revision=os.environ.get("SPEECH_ASR_INDIC_CONFORMER_REVISION"),
                                 min_free_gib=min_free_gib)
    return WhisperASR(spec, min_free_gib=min_free_gib)


def cmd_asr(args) -> None:
    from speech_service.audio import decode_audio
    from speech_service.config import default_city_dir
    from speech_service.places import load_gazetteer
    from speech_service.report import build_report

    gaz = load_gazetteer(default_city_dir())
    audio = Path(args.audio)
    summary = {}
    for mid in args.models.split(","):
        asr = asr_for_eval(mid)
        _reset_gpu_peak()
        t0 = time.perf_counter()
        try:
            asr._lazy.get()
        except Exception as exc:  # one checkpoint that cannot load must not stop the rest
            print(mid, "SKIPPED:", exc, flush=True)
            continue
        load_s = round(time.perf_counter() - t0, 1)
        rows = []
        for voice in VOICES:
            for p in PHRASES:
                x, dur, _ = decode_audio((audio / f"{p['id']}_{voice}.wav").read_bytes())
                tr = asr.transcribe(x, "bn")
                rep = build_report(tr.text, gaz, source="field-voice", language="bn")
                rows.append({"id": p["id"], "voice": voice, "ref": p["text"], "hyp": tr.text,
                             "confidence": tr.confidence, "asr_s": tr.seconds,
                             "place": (rep["place"] or {}).get("id"), "expected_place": p["place"],
                             "place_ok": (rep["place"] or {}).get("id") == p["place"],
                             "kind": rep["kind"], "expected_kind": p["kind"],
                             "kind_ok": rep["kind"] == p["kind"]})
        gpu_peak = _gpu_peak_gib()
        asr.unload()
        s = _score(rows)
        s["load_s"] = load_s
        s.update(gpu_peak or {})
        s["per_voice"] = {v: _score([r for r in rows if r["voice"] == v]) for v in VOICES}
        summary[mid] = {"summary": s, "rows": rows}
        print(mid, json.dumps(s), flush=True)
        # saved after every model, so one checkpoint failing loses nothing
        doc = json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else {}
        doc.setdefault("asr_comparison", {})[mid] = summary[mid]
        RESULTS.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")


def cmd_api(args) -> None:
    audio = Path(args.audio)
    rows = []
    for voice in VOICES:
        for p in PHRASES:
            t0 = time.perf_counter()
            body, _ = _post(args.base.rstrip("/") + "/speech/report",
                            (audio / f"{p['id']}_{voice}.wav").read_bytes(), "audio/wav")
            dt = time.perf_counter() - t0
            rep = json.loads(body)
            rows.append({"id": p["id"], "voice": voice, "ref": p["text"], "hyp": rep["transcript"],
                         "asr_s": rep["asr"]["asr_seconds"], "latency_s": round(dt, 3),
                         "place": (rep["place"] or {}).get("id"),
                         "match_score": (rep["place"] or {}).get("match_score"),
                         "expected_place": p["place"],
                         "place_ok": (rep["place"] or {}).get("id") == p["place"],
                         "kind": rep["kind"], "expected_kind": p["kind"],
                         "kind_ok": rep["kind"] == p["kind"], "severity": rep["severity"],
                         "verification_state": rep["verification_state"]})
            r = rows[-1]
            print(f"{p['id']} {voice} place={r['place']}({'ok' if r['place_ok'] else 'MISS'}) "
                  f"kind={r['kind']}({'ok' if r['kind_ok'] else 'MISS'}) t={dt:.2f}s | {r['hyp']}",
                  flush=True)
    s = _score(rows)
    s["latency_s_median"] = round(statistics.median(r["latency_s"] for r in rows), 3)
    s["all_unverified_field"] = all(r["verification_state"] == "UNVERIFIED-FIELD" for r in rows)
    print(json.dumps(s, indent=1))
    _merge("api_end_to_end", {"summary": s, "rows": rows})


def cmd_rescore(_args) -> None:
    """Re-run place/kind on the saved transcripts with the current rules
    (ASR output is unchanged; only the report pipeline is re-applied)."""
    from speech_service.config import default_city_dir
    from speech_service.places import load_gazetteer
    from speech_service.report import build_report

    gaz = load_gazetteer(default_city_dir())
    doc = json.loads(RESULTS.read_text(encoding="utf-8"))
    for mid, v in doc.get("asr_comparison", {}).items():
        for r in v["rows"]:
            rep = build_report(r["hyp"], gaz, source="field-voice", language="bn")
            r["place"] = (rep["place"] or {}).get("id")
            r["place_ok"] = r["place"] == r["expected_place"]
            r["kind"] = rep["kind"]
            r["kind_ok"] = rep["kind"] == r["expected_kind"]
        kept = {k: v["summary"][k]
                for k in ("load_s", "gpu_peak_alloc_gib", "gpu_peak_reserved_gib")
                if k in v["summary"]}
        v["summary"] = _score(v["rows"])
        v["summary"].update(kept)
        v["summary"]["per_voice"] = {x: _score([r for r in v["rows"] if r["voice"] == x])
                                     for x in VOICES}
        print(mid, json.dumps({k: v["summary"][k] for k in ("wer", "cer", "place_accuracy",
                                                             "kind_accuracy")}))
    RESULTS.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")


def cmd_text(_args) -> None:
    """Upper bound: the report pipeline on the reference text itself (no audio)."""
    from speech_service.config import default_city_dir
    from speech_service.places import load_gazetteer
    from speech_service.report import build_report

    gaz = load_gazetteer(default_city_dir())
    rows = []
    for p in PHRASES:
        rep = build_report(p["text"], gaz, source="field-text", language="bn")
        rows.append({"id": p["id"], "place_ok": (rep["place"] or {}).get("id") == p["place"],
                     "kind_ok": rep["kind"] == p["kind"]})
    s = {"n": len(rows), "place_accuracy": round(sum(r["place_ok"] for r in rows) / len(rows), 3),
         "kind_accuracy": round(sum(r["kind_ok"] for r in rows) / len(rows), 3)}
    print(s)
    _merge("reference_text", s)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("synth"); a.add_argument("--base", required=True); a.add_argument("--audio", required=True)
    b = sub.add_parser("asr"); b.add_argument("--audio", required=True); b.add_argument("--models", required=True)
    c = sub.add_parser("api"); c.add_argument("--base", required=True); c.add_argument("--audio", required=True)
    sub.add_parser("text")
    sub.add_parser("rescore")
    args = ap.parse_args()
    {"synth": cmd_synth, "asr": cmd_asr, "api": cmd_api, "text": cmd_text,
     "rescore": cmd_rescore}[args.cmd](args)


if __name__ == "__main__":
    main()
