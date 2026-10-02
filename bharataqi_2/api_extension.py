"""BharatAQI-X 2.0 — FastAPI extension router (mounts onto backend/app.py).

Usage in the existing repo (no breaking changes):

    from bharataqi_2.api_extension import router as v2_router
    app.include_router(v2_router)

Endpoints:
  POST /v2/sensor/ingest        — accept one LCS reading (L1→L2 handoff)
  POST /v2/calibrate/fit        — fit city calibration on co-location frame
  POST /v2/calibrate/apply      — apply calibration + quality flags
  GET  /v2/sensor/health        — drift-watchdog status from residuals
  POST /v2/grap/assess          — forecast → GRAP stage + drafted actions
  POST /v2/scenario/evaluate    — sector cuts → ΔPM2.5 estimate
  POST /v2/outcome/evaluate     — counterfactual vs observed + DiD
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field

from .calibration import CalibrationEngine, DriftWatchdog
from .grap_engine import assess_forecast, scenario_delta_pm25
from .outcome_tracker import difference_in_differences, episode_effect, monetise_benefit
from .realtime import RegionTracker, fetch_open_meteo, india_aqi, precautions_for_aqi

router = APIRouter(prefix="/v2", tags=["BharatAQI-X 2.0"])

# Demo-grade in-memory stores. Production: replace with Postgres/Supabase tables.
_CALIBRATORS: dict[str, CalibrationEngine] = {}
_READINGS: list[dict] = []
_WATCHDOG = DriftWatchdog(contamination=0.05)
_WATCHDOG_BASELINE: list[float] = []
_TRACKER = RegionTracker(alert_threshold=200.0)


# ── Schemas ────────────────────────────────────────────────────────────────
class SensorReading(BaseModel):
    city: str = "Delhi"
    raw_pm25: float = Field(..., ge=0, le=1000)
    raw_pm10: float = Field(0, ge=0, le=1000)
    temperature: float = 30.0
    humidity: float = Field(50, ge=0, le=100)
    node_id: str = "node-01"


class CalibrateFitRequest(BaseModel):
    city: str = "Delhi"
    model_type: str = Field("rf", pattern="^(rf|mlr)$")
    records: list[dict[str, Any]]  # each: raw_pm25, raw_pm10, temperature, humidity, ref_pm25


class CalibrateApplyRequest(BaseModel):
    city: str = "Delhi"
    records: list[dict[str, Any]]


class GrapAssessRequest(BaseModel):
    city: str = "Delhi"
    forecast_aqi: float = Field(..., ge=0, le=600)
    confidence: float = Field(0.8, ge=0, le=1)


class ScenarioRequest(BaseModel):
    baseline_pm25: float = Field(..., ge=0, le=1000)
    cuts: dict[str, float]


class OutcomeRequest(BaseModel):
    counterfactual: list[float]
    observed: list[float]
    treated_before: list[float] | None = None
    treated_after: list[float] | None = None
    control_before: list[float] | None = None
    control_after: list[float] | None = None
    population: int | None = None
    inr_per_ug_per_person: float | None = None


class WatchRequest(BaseModel):
    name: str = "Delhi"
    latitude: float = 28.61
    longitude: float = 77.21


# ── Endpoints ──────────────────────────────────────────────────────────────
@router.post("/sensor/ingest")
def ingest_reading(r: SensorReading):
    _READINGS.append(r.model_dump())
    return {"stored": True, "total_readings": len(_READINGS)}


@router.post("/calibrate/fit")
def calibrate_fit(req: CalibrateFitRequest):
    try:
        df = pd.DataFrame(req.records)
        eng = CalibrationEngine(model_type=req.model_type)
        metrics = eng.fit(df)
        _CALIBRATORS[req.city] = eng
        return {"city": req.city, "model_type": req.model_type, "metrics": metrics}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/calibrate/apply")
def calibrate_apply(req: CalibrateApplyRequest):
    eng = _CALIBRATORS.get(req.city)
    if eng is None:
        raise HTTPException(status_code=404, detail=f"No calibrator for {req.city}; POST /v2/calibrate/fit first")
    try:
        out = eng.apply(pd.DataFrame(req.records))
        return {"city": req.city, "records": out.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sensor/health")
def sensor_health():
    if not _WATCHDOG_BASELINE:
        return {"status": "no-baseline", "hint": "POST residuals via /v2/outcome/evaluate first, or seed baseline"}
    try:
        wd = DriftWatchdog().fit(np.array(_WATCHDOG_BASELINE))
        recent = np.array(_WATCHDOG_BASELINE[-168:])  # last week hourly
        return {"status": "ok", **wd.assess(recent)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/grap/assess")
def grap_assess(req: GrapAssessRequest):
    return assess_forecast(req.forecast_aqi, req.confidence, req.city)


@router.post("/scenario/evaluate")
def scenario_evaluate(req: ScenarioRequest):
    try:
        return scenario_delta_pm25(req.baseline_pm25, req.cuts)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/outcome/evaluate")
def outcome_evaluate(req: OutcomeRequest):
    try:
        result: dict[str, Any] = {"episode": episode_effect(req.counterfactual, req.observed)}
        # Feed residuals into the watchdog baseline for /sensor/health.
        _WATCHDOG_BASELINE.extend(
            (np.asarray(req.observed) - np.asarray(req.counterfactual)).tolist()
        )
        if all(v is not None for v in (req.treated_before, req.treated_after, req.control_before, req.control_after)):
            result["did"] = difference_in_differences(
                req.treated_before or [], req.treated_after or [],
                req.control_before or [], req.control_after or [],
            )
        if req.population and req.inr_per_ug_per_person:
            avoided = req.counterfactual and (float(np.mean(req.counterfactual)) - float(np.mean(req.observed)))
            result["benefit"] = monetise_benefit(max(avoided, 0.0), req.population, req.inr_per_ug_per_person)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def mount_onto(app: FastAPI) -> FastAPI:
    """Idempotent helper so backend/app.py needs a one-line change."""
    if not any(r.path.startswith("/v2/") for r in app.routes):
        app.include_router(router)
    return app


# ── Realtime air + multi-region tracker + advisory ─────────────────────────
@router.get("/air/live")
def air_live(latitude: float, longitude: float, city: str = ""):
    """Keyless live snapshot (Open-Meteo) with CPCB India AQI + precautions."""
    try:
        snap = fetch_open_meteo(latitude, longitude)
        aqi = snap["india_aqi"]["aqi"]
        return {**snap, "city": city, "precautions": precautions_for_aqi(aqi)}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Live provider unreachable: {e}")


@router.get("/air/forecast")
def air_forecast(latitude: float, longitude: float, hours: int = 24):
    try:
        snap = fetch_open_meteo(latitude, longitude, forecast_hours=min(168, max(1, hours)))
        return {"latitude": latitude, "longitude": longitude,
                "forecast": snap["forecast_next_hours"]}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Live provider unreachable: {e}")


@router.get("/advisory")
def advisory(aqi: float):
    if not 0 <= aqi <= 600:
        raise HTTPException(status_code=400, detail="aqi must be in [0, 600]")
    return precautions_for_aqi(aqi)


@router.post("/tracker/watch")
def tracker_watch(req: WatchRequest):
    return _TRACKER.watch(req.name, req.latitude, req.longitude)


@router.get("/tracker/list")
def tracker_list():
    return {"regions": _TRACKER.regions, "total": len(_TRACKER.regions)}


@router.post("/tracker/refresh")
def tracker_refresh(provider: str = "open_meteo"):
    try:
        return _TRACKER.refresh(provider)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tracker/ranking")
def tracker_ranking():
    return {"ranking": _TRACKER.ranking(), "alerts": _TRACKER.alerts()}


@router.delete("/tracker/watch/{name}")
def tracker_unwatch(name: str):
    return _TRACKER.unwatch(name)
