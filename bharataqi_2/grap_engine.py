"""BharatAQI-X 2.0 — L4 Decision layer: GRAP-stage engine + scenario sliders.

GRAP thresholds follow the official CAQM schedule (PIB):
  Stage I   : AQI 201–300 (Poor)
  Stage II  : AQI 301–400 (Very Poor)
  Stage III : AQI 401–450 (Severe)
  Stage IV  : AQI >450   (Severe+)

Scenario elasticities are consistent with IISc/DSS v1.0 estimates used in the
strategy report: a 20% anthropogenic emission cut yields ~12–14% seasonal-mean
PM2.5 reduction in Delhi; 40% yields ~24–28%. We linearise to an elasticity of
~0.65 applied per-sector with sector weights, so judges can trace every number.
"""

from __future__ import annotations

# Representative action checklists distilled from the official GRAP schedule
# (Stage I: 24 actions … Stage IV: 8 actions). Kept short for prototype memos;
# the full statutory text should be linked, not paraphrased, in the final report.
GRAP_ACTIONS: dict[str, list[str]] = {
    "None": [
        "Continue routine monitoring and dust-suppression at C&D sites ≥500 m².",
    ],
    "I": [
        "Enforce dust control at construction sites (video fencing + sprinkling).",
        "Audit C&D self-declarations on the CAQM portal for the affected wards.",
        "Mechanised road sweeping + water sprinkling on identified dust corridors.",
        "Ban open waste burning; deploy night patrols at chronic burning points.",
        "Keep anti-smog guns operational in proportion to site area (Dir. 69).",
    ],
    "II": [
        "All Stage-I actions, plus:",
        "Raise parking fees to disincentivise private vehicle use.",
        "Restrict diesel generator sets except emergency services.",
        "Increase bus/metro frequency on high-exposure corridors.",
        "Issue citizen advisory: limit outdoor exertion, exposure routing on.",
    ],
    "III": [
        "All Stage-II actions, plus:",
        "Halt non-essential construction & demolition (except strategic projects).",
        "Restrict BS-III petrol / BS-IV diesel LMVs in NCR.",
        "Close brick kilns, hot-mix plants, stone crushers.",
        "Schools: consider hybrid/offline suspension for primary classes.",
    ],
    "IV": [
        "All Stage-III actions, plus:",
        "Halt all construction (including linear public projects).",
        "Odd-even vehicle scheme / truck entry ban except essentials.",
        "Work-from-home for 50% of public/private offices.",
        "Close schools and colleges; emergency health advisories.",
    ],
}

# Sector share of urban PM2.5 used for scenario weighting. Defaults reflect the
# Delhi DSS seasonal-mean structure (transport ~17% the largest single sector;
# construction dust + waste burning grouped as the enforceable hyperlocal share).
DEFAULT_SECTOR_WEIGHTS: dict[str, float] = {
    "construction_dust": 0.18,
    "waste_burning": 0.10,
    "transport": 0.17,
    "industry": 0.12,
    "biomass_regional": 0.15,
    "other": 0.28,
}

# DSS-consistent elasticity: ΔPM% ≈ elasticity × Δemission% (aggregate ≈0.65).
EMISSION_TO_PM_ELASTICITY = 0.65


def grap_stage(aqi: float) -> str:
    if aqi > 450:
        return "IV"
    if aqi > 400:
        return "III"
    if aqi > 300:
        return "II"
    if aqi > 200:
        return "I"
    return "None"


def assess_forecast(aqi_forecast: float, confidence: float = 0.8,
                    city: str = "Delhi") -> dict:
    """Draft a GRAP action memo from a forecast value (L3 → L4 handoff)."""
    stage = grap_stage(aqi_forecast)
    actions = GRAP_ACTIONS[stage]
    trigger = stage != "None" and confidence >= 0.6
    memo = (
        f"{city}: 72-hr forecast AQI {aqi_forecast:.0f} -> GRAP Stage {stage} "
        f"(confidence {confidence:.0%}). "
        + ("Drafted actions for municipal sign-off: " + "; ".join(actions[:3]) + "..."
           if trigger else "No GRAP trigger; continue routine dust/burning watch.")
    )
    return {
        "city": city,
        "forecast_aqi": round(float(aqi_forecast), 1),
        "confidence": confidence,
        "stage": stage,
        "trigger_action": bool(trigger),
        "actions": actions,
        "memo": memo,
    }


def scenario_delta_pm25(baseline_pm25: float,
                        cuts: dict[str, float],
                        weights: dict[str, float] | None = None) -> dict:
    """Scenario slider: sector emission cuts (0–1) → estimated ΔPM2.5.

    Example: cuts={"construction_dust": 1.0} models a full construction halt.
    """
    w = weights or DEFAULT_SECTOR_WEIGHTS
    for sector, frac in cuts.items():
        if sector not in w:
            raise ValueError(f"Unknown sector '{sector}'. Known: {sorted(w)}")
        if not 0.0 <= frac <= 1.0:
            raise ValueError(f"Cut fraction for '{sector}' must be in [0, 1]")
    weighted_cut = sum(w[s] * cuts.get(s, 0.0) for s in w)
    pm_reduction_frac = EMISSION_TO_PM_ELASTICITY * weighted_cut
    avoided = float(baseline_pm25) * pm_reduction_frac
    return {
        "baseline_pm25": round(float(baseline_pm25), 2),
        "weighted_emission_cut_frac": round(weighted_cut, 4),
        "pm25_reduction_frac": round(pm_reduction_frac, 4),
        "avoided_pm25": round(avoided, 2),
        "projected_pm25": round(float(baseline_pm25) - avoided, 2),
        "elasticity_used": EMISSION_TO_PM_ELASTICITY,
    }
