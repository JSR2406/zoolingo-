"""Smoke tests for BharatAQI-X 2.0 L2/L4/L5 — runnable without hardware.

Run:  python -m pytest bharataqi_2/tests -q   (or: python bharataqi_2/tests/test_layers.py)
Uses synthetic co-location data with a known T/RH bias, mirroring the W5–7
calibration campaign in the strategy report.
"""

import numpy as np
import pandas as pd


def _synthetic_colocation(n: int = 400, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    temp = rng.normal(32, 4, n)
    rh = np.clip(rng.normal(60, 18, n), 20, 98)
    ref = np.clip(rng.normal(120, 60, n), 10, 450)
    # Simulate raw LCS bias: inflates with humidity, drifts at high loading.
    raw = ref * (1 + 0.004 * np.maximum(rh - 50, 0)) + rng.normal(0, 6, n)
    return pd.DataFrame({
        "raw_pm25": np.clip(raw, 0, 600),
        "raw_pm10": np.clip(raw * 1.7, 0, 800),
        "temperature": temp, "humidity": rh, "ref_pm25": ref,
    })


def test_l2_calibration_meets_benchmark():
    from bharataqi_2.calibration import CalibrationEngine
    df = _synthetic_colocation()
    eng = CalibrationEngine(model_type="rf")
    m = eng.fit(df)
    assert m["r2"] > 0.9, m
    out = eng.apply(df.head(5))
    assert "calibrated_pm25" in out.columns and "flag_high_rh" in out.columns


def test_l2_mlr_runs():
    from bharataqi_2.calibration import CalibrationEngine
    eng = CalibrationEngine(model_type="mlr")
    m = eng.fit(_synthetic_colocation())
    assert m["rmse"] > 0


def test_l2_drift_watchdog():
    from bharataqi_2.calibration import DriftWatchdog
    wd = DriftWatchdog(contamination=0.05).fit(np.random.normal(0, 5, 300))
    ok = wd.assess(np.random.normal(0, 5, 50))
    assert not ok["recalibration_due"]
    drifted = wd.assess(np.random.normal(40, 5, 50))
    assert drifted["recalibration_due"] or drifted["residual_rmse"] > 10


def test_l4_grap_stages():
    from bharataqi_2.grap_engine import assess_forecast
    assert assess_forecast(250)["stage"] == "I"
    assert assess_forecast(350)["stage"] == "II"
    assert assess_forecast(420)["stage"] == "III"
    assert assess_forecast(480)["stage"] == "IV"
    assert assess_forecast(120)["stage"] == "None"


def test_l4_scenario_elasticity():
    from bharataqi_2.grap_engine import scenario_delta_pm25
    # Full construction halt on baseline 200 µg/m³:
    # weighted cut = .18 → reduction ≈ .65*.18 ≈ 11.7% → ~23 µg/m³ avoided.
    r = scenario_delta_pm25(200.0, {"construction_dust": 1.0})
    assert 20 < r["avoided_pm25"] < 27, r


def test_l5_outcome():
    from bharataqi_2.outcome_tracker import difference_in_differences, episode_effect
    cf = [200.0] * 24
    ob = [170.0] * 24  # intervention cut 30 µg/m³
    e = episode_effect(cf, ob)
    assert e["improved"] and e["mean_delta_pm25"] == -30.0
    d = difference_in_differences([200] * 24, [170] * 24, [200] * 24, [198] * 24)
    assert d["intervention_worked"] and d["did_pm25"] < 0


if __name__ == "__main__":
    for name, fn in sorted({k: v for k, v in globals().items() if k.startswith("test_")}.items()):
        fn()
        print(f"PASS {name}")
