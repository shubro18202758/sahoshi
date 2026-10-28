"""Forecast HTTP surface (production :8195, loopback).

    GET  /health                                  service, model slot (loaded? GPU MiB), upstream probes
    GET  /forecast/segments?horizon_min=15..120   per segment: p10/p50/p90 V/C and speed at 15-min steps,
                                                  a ``crossing`` when p50 V/C reaches 0.8 within the horizon,
                                                  and the pre-emptive diversion PROPOSALS (never actions)
    GET  /forecast/segment/{id}?horizon_min=      one segment (+ its proposal, if any)
    GET  /forecast/metrics                        rolling backtest: MAE / MAPE / p10–p90 coverage, model vs
                                                  seasonal-naive baseline (and the contender), with its
                                                  honest data label
    POST /forecast/refresh?backtest=false         recompute now (and the backtest when asked)

Every answer carries its data label: forecasts on the simulated history say SIMULATED.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
from typing import Any, AsyncIterator

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from forecast import __version__
from forecast.config import Settings, get_settings
from forecast.covariates import HydroClient
from forecast.engine import MAX_HORIZON_MIN, Engine
from forecast.models import gpu_stats
from forecast.network import load_network

logger = structlog.get_logger(__name__)

__all__ = ["create_app", "main"]


def _truncate(seg: dict[str, Any], horizon_min: int) -> dict[str, Any]:
    out = dict(seg)
    out["steps"] = [s for s in seg["steps"] if s["lead_min"] <= horizon_min]
    c = seg.get("crossing")
    out["crossing"] = c if c is not None and c["in_min"] <= horizon_min else None
    if out["crossing"] is None:
        out.pop("proposal_id", None)
    return out


def create_app(settings: Settings | None = None, engine: Engine | None = None) -> FastAPI:
    s = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        eng = engine
        oracle = hydro = None
        if eng is None:
            from forecast.oracle import OracleClient  # noqa: PLC0415

            oracle = OracleClient(s.oracle_url, s.http_timeout_sec) if s.data_source != "synthetic" else None
            hydro = HydroClient(s.hydro_url, s.http_timeout_sec)
            eng = Engine(s, load_network(s.resolved_city_dir()), oracle=oracle, hydro=hydro)
        app.state.engine = eng

        async def reaper() -> None:
            while True:
                await asyncio.sleep(30)
                freed = eng.reap_idle()
                if freed:
                    logger.info("forecast.model_unloaded_idle", models=freed)

        task = asyncio.create_task(reaper())
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            for slot in eng.slots():
                slot.unload()
            for c in (oracle, hydro):
                if c is not None:
                    await c.aclose()

    app = FastAPI(title="Sahoshi forecast", version=__version__, lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=list(s.deck_origins), allow_methods=["GET", "POST"],
                       allow_headers=["*"])

    def eng() -> Engine:
        return app.state.engine

    @app.get("/health")
    async def health() -> dict[str, Any]:
        e = eng()
        oracle = await e.oracle.health() if e.oracle is not None else {"reachable": None, "note": "synthetic mode"}
        return {
            "status": "ok" if e.last_error is None else "degraded",
            "service": "forecast",
            "version": __version__,
            "model": {"name": e.model.name, "licence": getattr(e.model, "licence", None),
                      "slot": e.model.slot.status() if hasattr(e.model, "slot") else None},
            "contender": ({"name": e.contender.name, "licence": e.contender.licence,
                            "slot": e.contender.slot.status()} if e.contender is not None else None),
            "baseline": e.naive.name,
            "last_error": e.last_error,
            "data_source": e.s.data_source,
            "oracle": {"url": e.s.oracle_url, **oracle},
            "network": {"source": e.net.source, "segments": len(e.net.segments)},
            "gpu": gpu_stats(),
        }

    @app.get("/forecast/segments")
    async def segments(horizon_min: int = Query(default=MAX_HORIZON_MIN, ge=15, le=MAX_HORIZON_MIN)) -> dict:
        body = await eng().forecasts()
        segs = [_truncate(x, horizon_min) for x in body["segments"]]
        live_ids = {x["proposal_id"] for x in segs if x.get("proposal_id")}
        return {**body, "horizon_min": horizon_min, "segments": segs,
                "proposals": [p for p in body["proposals"] if p["proposal_id"] in live_ids],
                "crossings": sum(1 for x in segs if x["crossing"] is not None)}

    @app.get("/forecast/segment/{segment_id}")
    async def segment(segment_id: int,
                      horizon_min: int = Query(default=MAX_HORIZON_MIN, ge=15, le=MAX_HORIZON_MIN)) -> dict:
        e = eng()
        if segment_id not in e.net.segments:
            raise HTTPException(status_code=404, detail="unknown segment")
        body = await e.forecasts()
        seg = next((x for x in body["segments"] if x["segment_id"] == segment_id), None)
        if seg is None:
            skip = next((x["reason"] for x in body["skipped"] if x["segment_id"] == segment_id), "not forecast")
            raise HTTPException(status_code=409, detail=f"no forecast for this segment: {skip}")
        out = _truncate(seg, horizon_min)
        prop = next((p for p in body["proposals"] if p["proposal_id"] == out.get("proposal_id")), None)
        return {"origin": body["origin"], "model": body["model"], "threshold_vc": body["threshold_vc"],
                "horizon_min": horizon_min, "segment": out, "proposal": prop, "data_note": body["data_note"]}

    @app.get("/forecast/metrics")
    async def metrics() -> dict:
        return await eng().backtest()

    @app.post("/forecast/refresh")
    async def refresh(backtest: bool = Query(default=False)) -> dict:
        e = eng()
        body = await e.forecasts(force=True)
        out = {"refreshed": True, "origin": body["origin"], "model": body["model"],
               "segments": len(body["segments"]), "crossings": len(body["proposals"]),
               "inference_sec": body["inference_sec"]}
        if backtest:
            bt = await e.backtest(force=True)
            out["backtest"] = {k: {kk: v.get(kk) for kk in ("mae_vc", "mape_pct", "coverage_p10_p90")}
                               for k, v in bt["models"].items()}
        return out

    return app


def main() -> None:
    s = get_settings()
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(20))
    logger.info("forecast.starting", host=s.host, port=s.port, model=s.model, data_source=s.data_source)
    uvicorn.run(create_app(s), host=s.host, port=s.port, log_level="info")
