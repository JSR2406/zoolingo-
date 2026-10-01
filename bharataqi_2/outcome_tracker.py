"""BharatAQI-X 2.0 — L5 Outcome layer: intervention M&E (the missing loop).

Implements the capability CEEW found absent even in AIRWISE/DSS:
measure whether an intervention actually moved PM2.5.

Method (prototype-grade, fully disclosed):
1. Counterfactual baseline = L3 forecast-without-action for the episode window.
2. Observed = calibrated ward mean (L2 output) for the same window.
3. Effect = mean(observed − counterfactual); negative = improvement.
4. Difference-in-differences vs an upwind control ward removes weather luck:
   DiD = (treated_after − treated_before) − (control_after − control_before).

Health/economic conversion is intentionally a *caller-supplied rate* so the
report never hard-codes GBD numbers: pass in your cost-of-illness anchor
(e.g. World Bank $36.8B / 1.36% GDP framing) and the module does the arithmetic.
"""

from __future__ import annotations

import numpy as np


def episode_effect(counterfactual: list[float] | np.ndarray,
                   observed: list[float] | np.ndarray) -> dict:
    cf = np.asarray(counterfactual, dtype=float)
    ob = np.asarray(observed, dtype=float)
    if cf.shape != ob.shape or cf.size == 0:
        raise ValueError("counterfactual and observed must be non-empty and same length")
    delta = ob - cf
    return {
        "n_hours": int(cf.size),
        "mean_counterfactual": round(float(cf.mean()), 2),
        "mean_observed": round(float(ob.mean()), 2),
        "mean_delta_pm25": round(float(delta.mean()), 2),
        "pct_change": round(float(delta.mean() / max(cf.mean(), 1e-6) * 100), 2),
        "improved": bool(delta.mean() < 0),
        "max_hourly_avoided": round(float(-delta.min()), 2),
    }


def difference_in_differences(treated_before: list[float] | np.ndarray,
                              treated_after: list[float] | np.ndarray,
                              control_before: list[float] | np.ndarray,
                              control_after: list[float] | np.ndarray) -> dict:
    tb, ta = float(np.mean(treated_before)), float(np.mean(treated_after))
    cb, ca = float(np.mean(control_before)), float(np.mean(control_after))
    did = (ta - tb) - (ca - cb)
    return {
        "treated_change": round(ta - tb, 2),
        "control_change": round(ca - cb, 2),
        "did_pm25": round(did, 2),
        "intervention_worked": bool(did < 0),
    }


def monetise_benefit(avoided_pm25_mean: float, population: int,
                     inr_per_ug_per_person: float) -> dict:
    """Convert measured ΔPM2.5 into INR using a caller-supplied unit rate.

    Keeping the rate an explicit parameter forces the final report to cite its
    source (GBD/World Bank cost-of-illness anchors) instead of hiding it.
    """
    benefit = float(avoided_pm25_mean) * int(population) * float(inr_per_ug_per_person)
    return {
        "avoided_pm25_mean": round(float(avoided_pm25_mean), 2),
        "population": int(population),
        "inr_per_ug_per_person": float(inr_per_ug_per_person),
        "estimated_benefit_inr": round(benefit, 2),
    }
