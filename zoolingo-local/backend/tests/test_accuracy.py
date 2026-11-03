"""
ZooLingo accuracy test.

Asserts that the trained model clears the majority baseline on the held-out
set for the welfare task, and that confidence is calibrated (ECE <= 0.10).

Skips cleanly if no model/data is present so CI on a fresh checkout does not fail.
"""

import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.features import extract_dict

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_BACKEND_DIR)
RESULTS_PATH = os.path.join(_BACKEND_DIR, "results.json")
DATA_DIR = os.path.join(_REPO_ROOT, "data")
MODEL_PATH = os.path.join(_BACKEND_DIR, "models", "emotion_classifier.h5")


def _expected_calibration_error(y_true, y_prob, n_bins=10):
    """Expected Calibration Error."""
    y_true = np.array(y_true)
    y_prob = np.array(y_prob)
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (y_prob > bins[i]) & (y_prob <= bins[i + 1])
        if np.sum(mask) == 0:
            continue
        bin_conf = np.mean(y_prob[mask])
        bin_acc = np.mean(y_true[mask] == 1)
        ece += np.sum(mask) / len(y_true) * abs(bin_conf - bin_acc)
    return float(ece)


def _majority_baseline(y):
    """Majority-class accuracy."""
    from collections import Counter

    counts = Counter(y)
    majority = counts.most_common(1)[0][1]
    return majority / len(y)


def test_welfare_clears_baseline():
    """Welfare task macro-F1 must clear majority baseline on held-out set."""
    if not os.path.exists(RESULTS_PATH):
        pytest.skip("results.json not found — run train_eval.py first")

    with open(RESULTS_PATH, encoding="utf-8") as f:
        results = json.load(f)

    welfare = next((r for r in results if r["task"] == "welfare"), None)
    if welfare is None:
        pytest.skip("welfare task not in results.json")

    assert welfare["macro_f1"] > welfare["majority_baseline"], (
        f"Welfare macro-F1 ({welfare['macro_f1']:.4f}) does not clear "
        f"majority baseline ({welfare['majority_baseline']:.4f})"
    )


def test_confidence_calibrated():
    """Confidence ECE must be <= 0.10."""
    if not os.path.exists(RESULTS_PATH):
        pytest.skip("results.json not found — run train_eval.py first")

    with open(RESULTS_PATH, encoding="utf-8") as f:
        results = json.load(f)

    welfare = next((r for r in results if r["task"] == "welfare"), None)
    if welfare is None:
        pytest.skip("welfare task not in results.json")

    assert welfare["ece"] <= 0.10, (
        f"Welfare ECE ({welfare['ece']:.4f}) exceeds 0.10 threshold"
    )


def test_model_present():
    """If a model file exists, it should be loadable."""
    if not os.path.exists(MODEL_PATH):
        pytest.skip("No trained model file found — skipping model load test")

    import tensorflow as tf

    model = tf.keras.models.load_model(MODEL_PATH)
    assert model is not None
    assert model.output_shape is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])