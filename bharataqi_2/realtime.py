"""BharatAQI-X 2.0 — Realtime layer: live AQI providers, CPCB AQI, precautions.

Provider strategy (no hard-coded secrets — keys come from env vars only):
- ``open_meteo`` (default, KEYLESS): CAMS-based live + 72-hr forecast, global,
  verified live 2026-10-02. Pollutants in µg/m³.
- ``iqair``      (needs ``IQAIR_API_KEY``): AirVisual nearest-city + forecasts.
- ``google``     (needs ``GOOGLE_AQ_API_KEY``): Google Air Quality API heatmap.
- ``ambee``      (needs ``AMBEE_API_KEY``): Ambee AQ API.
- ``openaq``     (needs ``OPENAQ_API_KEY``): OpenAQ v3 reference-station data.
- ``cpcb``       : CPCB CAAQMS has no open realtime API; use the documented
  bulk-download flow (urbanemissions.info) and ingest via /v2/sensor/ingest.

India AQI follows CPCB breakpoints (sub-index per pollutant, overall = max).
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
FETCH_TIMEOUT_S = 20

# ── CPCB breakpoints: ((conc_lo, conc_hi), (aqi_lo, aqi_hi)) per band ─────────
# Units µg/m³ except CO in mg/m³. Bands: Good/Satisfactory/Moderate/Poor/V.Poor/Severe.
_AQI_BANDS = [(0, 50), (51, 100), (101, 200), (201, 300), (301, 400), (401, 500)]
CPCB_BREAKPOINTS: dict[str, list[tuple[float, float]]] = {
    "pm25": [(0, 30), (31, 60), (61, 90), (91, 120), (121, 250), (251, 1000)],
    "pm10": [(0, 50), (51, 100), (101, 250), (251, 350), (351, 430), (431, 2000)],
    "no2": [(0, 40), (41, 80), (81, 180), (181, 280), (281, 400), (401, 2000)],
    "so2": [(0, 40), (41, 80), (81, 380), (381, 800), (801, 1600), (1601, 5000)],
    "co": [(0, 1.0), (1.1, 2.0), (2.1, 10), (10.1, 17), (17.1, 34), (34.1, 100)],
    "o3": [(0, 50), (51, 100), (101, 168), (169, 208), (209, 748), (749, 2000)],
    "nh3": [(0, 200), (201, 400), (401, 800), (801, 1200), (1201, 1800), (1801, 5000)],
}


def _pollutant_sub_index(conc: float, breaks: list[tuple[float, float]]) -> float:
    conc = max(0.0, float(conc))
    for i, ((clo, chi), (ilo, ihi)) in enumerate(zip(breaks, _AQI_BANDS)):
        if conc <= chi:
            if chi == clo:
                return float(ihi)
            return round(ilo + (ihi - ilo) * (conc - clo) / (chi - clo), 1)
    return 500.0


def india_aqi(pm25: float | None = None, pm10: float | None = None,
              no2: float | None = None, so2: float | None = None,
              co: float | None = None, o3: float | None = None,
              nh3: float | None = None) -> dict:
    """CPCB-style AQI: sub-index per pollutant, overall = max. ``co`` in mg/m³."""
    inputs = {"pm25": pm25, "pm10": pm10, "no2": no2, "so2": so2,
              "co": co, "o3": o3, "nh3": nh3}
    subs = {k: _pollutant_sub_index(v, CPCB_BREAKPOINTS[k])
            for k, v in inputs.items() if v is not None}
    if not subs:
        raise ValueError("india_aqi needs at least one pollutant value")
    aqi = max(subs.values())
    driver = max(subs, key=lambda k: subs[k])
    return {"aqi": round(aqi, 1), "category": india_category(aqi),
            "driving_pollutant": driver, "sub_indices": subs}


def india_category(aqi: float) -> str:
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Satisfactory"
    if aqi <= 200:
        return "Moderate"
    if aqi <= 300:
        return "Poor"
    if aqi <= 400:
        return "Very Poor"
    return "Severe"


# ── Keyless provider: Open-Meteo ─────────────────────────────────────────────
def fetch_open_meteo(latitude: float, longitude: float,
                     forecast_hours: int = 72) -> dict:
    """Live snapshot + hourly forecast. No key. CO returned in µg/m³ by API."""
    params = {
        "latitude": latitude, "longitude": longitude,
        "current": "pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,ozone,carbon_monoxide,us_aqi",
        "hourly": "pm2_5,us_aqi",
        "forecast_days": min(7, max(1, (forecast_hours + 23) // 24)),
        "timezone": "auto",
    }
    url = OPEN_METEO_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "BharatAQI-X/2.0"})
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT_S) as resp:
        payload = json.load(resp)
    cur = payload.get("current", {})
    co_mg = (cur.get("carbon_monoxide") or 0) / 1000.0  # µg/m³ → mg/m³ for CPCB
    computed = india_aqi(
        pm25=cur.get("pm2_5"), pm10=cur.get("pm10"),
        no2=cur.get("nitrogen_dioxide"), so2=cur.get("sulphur_dioxide"),
        co=co_mg or None, o3=cur.get("ozone"),
    )
    hourly = payload.get("hourly", {})
    forecast = [
        {"time": t, "pm25": pm, "us_aqi": aqi}
        for t, pm, aqi in zip(hourly.get("time", [])[:forecast_hours],
                              hourly.get("pm2_5", [])[:forecast_hours],
                              hourly.get("us_aqi", [])[:forecast_hours])
    ]
    return {
        "provider": "open_meteo",
        "latitude": payload.get("latitude", latitude),
        "longitude": payload.get("longitude", longitude),
        "observed_at": cur.get("time"),
        "pollutants_ugm3": {
            "pm25": cur.get("pm2_5"), "pm10": cur.get("pm10"),
            "no2": cur.get("nitrogen_dioxide"), "so2": cur.get("sulphur_dioxide"),
            "o3": cur.get("ozone"), "co": cur.get("carbon_monoxide"),
        },
        "us_aqi": cur.get("us_aqi"),
        "india_aqi": computed,
        "forecast_next_hours": forecast,
    }


# ── Keyed providers (env vars read at call time, never logged) ───────────────
def _need_key(name: str) -> str:
    val = os.environ.get(name, "")
    if not val:
        raise RuntimeError(
            f"{name} is not set — export it in your shell; paid providers stay "
            "optional and the keyless Open-Meteo path keeps working.")
    return val


def fetch_iqair(latitude: float, longitude: float) -> dict:
    """AirVisual nearest-city. Needs IQAIR_API_KEY."""
    key = _need_key("IQAIR_API_KEY")
    url = (f"http://api.airvisual.com/v2/nearest_city?lat={latitude}&lon={longitude}&key={key}")
    with urllib.request.urlopen(url, timeout=FETCH_TIMEOUT_S) as resp:
        return {"provider": "iqair", "data": json.load(resp)}


def fetch_google_aq(latitude: float, longitude: float) -> dict:
    """Google Air Quality API currentConditions. Needs GOOGLE_AQ_API_KEY."""
    key = _need_key("GOOGLE_AQ_API_KEY")
    url = f"https://airquality.googleapis.com/v1/currentConditions:lookup?key={key}"
    body = json.dumps({"location": {"latitude": latitude, "longitude": longitude}}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT_S) as resp:
        return {"provider": "google", "data": json.load(resp)}


def fetch_ambee(latitude: float, longitude: float) -> dict:
    """Ambee latest AQ by lat/lng. Needs AMBEE_API_KEY."""
    key = _need_key("AMBEE_API_KEY")
    url = f"https://api.ambeedata.com/latest/by-lat-lng?lat={latitude}&lng={longitude}"
    req = urllib.request.Request(url, headers={"x-api-key": key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT_S) as resp:
        return {"provider": "ambee", "data": json.load(resp)}


PROVIDERS = {"open_meteo": fetch_open_meteo, "iqair": fetch_iqair,
             "google": fetch_google_aq, "ambee": fetch_ambee}


# ── Precautions engine ───────────────────────────────────────────────────────
def _grap_for(aqi: float) -> str:
    if aqi > 450:
        return "IV"
    if aqi > 400:
        return "III"
    if aqi > 300:
        return "II"
    if aqi > 200:
        return "I"
    return "None"


_ADVISORY: dict[str, dict] = {
    "Good": {
        "health": "Air quality is ideal. Normal outdoor activity for everyone.",
        "mask": "No mask needed.", "outdoor": "Enjoy outdoor exercise freely.",
        "indoor": "Natural ventilation is fine; give purifiers a rest.",
        "sensitive_groups": "No restrictions.",
    },
    "Satisfactory": {
        "health": "Acceptable; unusually sensitive people should watch symptoms.",
        "mask": "No mask needed for most; sensitive groups may mask near traffic.",
        "outdoor": "Fine for most; sensitive groups shorten prolonged exertion.",
        "indoor": "Ventilate in the morning when pollution is usually lower.",
        "sensitive_groups": "Children, elderly, asthmatics: ease off long outdoor sessions.",
    },
    "Moderate": {
        "health": "Breathing discomfort possible for asthmatics, elderly, children.",
        "mask": "N95 recommended near traffic, dust, or burning sites.",
        "outdoor": "Limit prolonged outdoor exertion; prefer early-morning hours.",
        "indoor": "Close windows during peak hours; run purifier on auto.",
        "sensitive_groups": "Children/elderly: keep outdoor play short; keep relievers handy.",
    },
    "Poor": {
        "health": "Discomfort to most on prolonged exposure; GRAP Stage I.",
        "mask": "Wear N95 outdoors.",
        "outdoor": "Cut back outdoor exercise; avoid busy roads and C&D zones.",
        "indoor": "Keep windows shut at peak; purifier on; no indoor smoking/incense.",
        "sensitive_groups": "Schools: move sports indoors; asthmatics avoid triggers.",
    },
    "Very Poor": {
        "health": "Respiratory illness likely on prolonged exposure; GRAP Stage II-III.",
        "mask": "N95 mandatory outdoors; cloth masks do not help against PM2.5.",
        "outdoor": "Avoid morning/evening walks near traffic; WFH where possible.",
        "indoor": "Seal windows; purifier on high in bedrooms; cook with exhaust on.",
        "sensitive_groups": "Schools: suspend outdoor activities; elderly stay indoors.",
    },
    "Severe": {
        "health": "Emergency: affects even healthy people; GRAP Stage III-IV.",
        "mask": "N95 if you must step out; minimise time outside.",
        "outdoor": "Stay indoors; postpone non-essential travel and exercise.",
        "indoor": "Purifier + sealed room; no biomass cooking, candles, or incense.",
        "sensitive_groups": "Schools/offices: follow closure orders; seek care for breathlessness.",
    },
}

SOURCE_PREVENTION = {
    "construction_dust": "Cover debris, barricade sites, sprinkle water 3-4x/day, use anti-smog guns (CAQM Dir. 69).",
    "waste_burning": "Never burn garbage/leaves — compost or hand to municipal pickup; report burning to 311/NGT apps.",
    "transport": "Use metro/bus, carpool, keep PUC current, switch off engines at signals, avoid idling.",
    "indoor": "No smoking indoors; use chimney/exhaust while cooking; prefer LPG/electric over biomass.",
    "community": "Car-free mornings, cycling, and plantation drives cut local exposure for the whole ward.",
}


def precautions_for_aqi(aqi: float) -> dict:
    """Category advisory + prevention checklist for one AQI number."""
    category = india_category(aqi)
    advice = dict(_ADVISORY[category])
    grap = _grap_for(aqi)
    if grap != "None":
        advice["grap"] = f"GRAP Stage {grap} actions apply (see /v2/grap/assess for the drafted checklist)."
    else:
        advice["grap"] = "No GRAP trigger; routine dust/burning watch continues."
    return {"aqi": round(float(aqi), 1), "category": category,
            "advisory": advice, "prevention": dict(SOURCE_PREVENTION)}


# ── Multi-region tracker ─────────────────────────────────────────────────────
@dataclass
class RegionTracker:
    """Watchlist of named regions with history, ranking, and threshold alerts."""

    alert_threshold: float = 200.0
    regions: dict[str, dict] = field(default_factory=dict)
    history: dict[str, list] = field(default_factory=lambda: defaultdict(list))

    def watch(self, name: str, latitude: float, longitude: float) -> dict:
        self.regions[name] = {"latitude": latitude, "longitude": longitude}
        return {"watching": name, "total": len(self.regions)}

    def unwatch(self, name: str) -> dict:
        self.regions.pop(name, None)
        self.history.pop(name, None)
        return {"removed": name, "total": len(self.regions)}

    def refresh(self, provider: str = "open_meteo") -> dict:
        fetcher = PROVIDERS.get(provider)
        if fetcher is None:
            raise ValueError(f"Unknown provider '{provider}'. Known: {sorted(PROVIDERS)}")
        results, errors = {}, {}
        for name, loc in self.regions.items():
            try:
                snap = fetcher(loc["latitude"], loc["longitude"])
                aqi = snap["india_aqi"]["aqi"]
                entry = {"at": datetime.now(timezone.utc).isoformat(),
                         "aqi": aqi, "category": snap["india_aqi"]["category"]}
                self.history[name].append(entry)
                self.history[name] = self.history[name][-168:]  # last week hourly
                results[name] = {**entry, "driving_pollutant": snap["india_aqi"]["driving_pollutant"]}
            except Exception as e:  # per-region failure must not kill the sweep
                logger.warning("Tracker refresh failed for %s: %s", name, e)
                errors[name] = str(e)[:200]
        return {"refreshed": len(results), "results": results, "errors": errors}

    def ranking(self) -> list[dict]:
        """Worst-first league table from each region's latest reading."""
        rows = [
            {"region": name, "aqi": h[-1]["aqi"], "category": h[-1]["category"], "at": h[-1]["at"]}
            for name, h in self.history.items() if h
        ]
        return sorted(rows, key=lambda r: r["aqi"], reverse=True)

    def alerts(self) -> list[dict]:
        return [
            {"region": r["region"], "aqi": r["aqi"], "category": r["category"],
             "message": f"{r['region']}: AQI {r['aqi']:.0f} ({r['category']}) exceeds {self.alert_threshold:.0f} — {precautions_for_aqi(r['aqi'])['advisory']['outdoor']}"}
            for r in self.ranking() if r["aqi"] >= self.alert_threshold
        ]
