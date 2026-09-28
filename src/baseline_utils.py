"""
baseline_utils.py

Shared helper for z-scoring a volunteer's raw feature values against the
Stage 1 population baselines computed by pretrain_calibration.py.

If models/baseline_stats.json doesn't exist yet (Stage 1 hasn't been run),
all functions here fall back to returning the raw value unchanged — this
keeps extract_*.py runnable on its own before Stage 1 is complete, which
is useful for early development and debugging.

If a feature group has a "domain_mismatch_warning" flag set to true in
baseline_stats.json, z-scoring is skipped for that group and raw values
are returned. This prevents applying normalization from a baseline that
measures a fundamentally different physical quantity (e.g. screen-level
gaze coordinates vs. MediaPipe iris-tracking coordinates).

NOTE on what this z-scoring does and does not do: it is a fixed per-feature
shift and positive rescale, so it puts features on an interpretable
"standard deviations from the population norm" scale, but it does NOT change
the predictions of tree models (XGBoost splits are invariant to monotonic
per-feature transforms) or of the logistic-regression pipeline (which
re-standardizes inside each training fold). The normalization that actually
matters for the classifier is the per-speaker centering in modeling_utils.py.
"""

import json
import math
from pathlib import Path

from paths_config import BASELINE_STATS_PATH

BASELINE_PATH = Path(BASELINE_STATS_PATH)

_baseline_cache = None
_domain_mismatch_warned = set()


def _load_baseline() -> dict:
    global _baseline_cache
    if _baseline_cache is None:
        if BASELINE_PATH.exists():
            with open(BASELINE_PATH) as f:
                _baseline_cache = json.load(f)
        else:
            _baseline_cache = {}
    return _baseline_cache


def zscore(feature_group: str, feature_name: str, raw_value: float) -> float:
    """
    Returns (raw_value - population_mean) / population_std, using the Stage 1
    baseline for the given feature group ("gaze", "latency", or "linguistic").

    Falls back to the raw value if no baseline is available yet (e.g. before
    pretrain_calibration.py has been run, or if a dataset for that group
    wasn't downloaded).

    Skips z-scoring entirely (returns raw value) if the feature group has a
    "domain_mismatch_warning" flag, indicating the baseline and extractor
    measure different physical quantities.

    Passes through NaN values unchanged (failed extractions should not be
    z-scored).
    """
    if math.isnan(raw_value):
        return raw_value

    baseline = _load_baseline()
    group_stats = baseline.get(feature_group, {})

    # Check for domain mismatch flag — if set, skip z-scoring for this group
    if group_stats.get("domain_mismatch_warning", False):
        if feature_group not in _domain_mismatch_warned:
            print(f"[Info] Skipping z-score for '{feature_group}': domain mismatch flagged — using raw values")
            _domain_mismatch_warned.add(feature_group)
        return raw_value

    feature_stats = group_stats.get(feature_name)

    if not feature_stats or feature_stats.get("n", 0) == 0:
        # No Stage 1 baseline available yet — return raw value unchanged.
        return raw_value

    mean = feature_stats["mean"]
    std = feature_stats["std"] or 1.0
    return (raw_value - mean) / std


def zscore_dict(feature_group: str, features: dict, keys_to_normalize: list) -> dict:
    """
    Convenience wrapper: given a feature dict (e.g. output of
    extract_gaze_features), returns a new dict with the listed keys
    replaced by their z-scored versions. Non-normalized keys (like
    "transcript") pass through unchanged.
    """
    result = dict(features)
    for key in keys_to_normalize:
        if key in result:
            result[key] = zscore(feature_group, key, result[key])
    return result
