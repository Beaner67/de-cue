"""
pretrain_calibration.py

Stage 1 of the two-stage pipeline (see proposal Section 4.3.1): builds
population-normal baselines for each feature group from existing public
datasets, so that Stage 2 (your own 10-12 volunteers) can be z-scored
against real population variation instead of relying on raw values from a
small sample alone.

This does NOT train a classifier. It only computes mean/std (or a small
distribution summary) per feature, per source dataset, and saves them for
extract_*.py to use at feature-extraction time.

Sources used (see proposal 4.3.1):
    - Eye Movement Data Set for Desktop Activities (Kaggle) -> gaze baseline
      (fixation_stability, saccade_rate, blink_rate) — freely downloadable,
      no license request needed
    - Svarah             -> latency + linguistic baseline (read vs. spontaneous splits)
    - Real-life Trial     -> supplementary linguistic baseline (filler_rate)

Usage:
    python src/pretrain_calibration.py
Output:
    models/baseline_stats.json
"""

import argparse
import csv
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd

# These import the SAME extractor functions used on your own volunteer data,
# so Stage 1 and Stage 2 features are computed identically — this is what
# makes the z-scoring valid.
from extract_gaze import extract_gaze_features
from extract_latency import extract_latency_features
from extract_linguistic import extract_linguistic_features

# Paths now live in paths_config.py — edit that ONE file if your external
# drive's letter changes, instead of hunting through multiple scripts.
from paths_config import (
    BASELINE_STATS_PATH,
    DESKTOP_ACTIVITIES_DIR,
    LABELS_PATH,
    REAL_LIFE_TRIAL_DIR,
    SVARAH_DIR,
    resolve_project_path,
)

BASELINE_OUTPUT_PATH = BASELINE_STATS_PATH

# Fixed I-VT saccade threshold for screen gaze. ~100 deg/s at ~60 cm viewing
# distance on a ~96 DPI monitor (1 deg ~ 38 px) -> ~3.8 px/ms. The
# conservative end of the usual 30-100 deg/s range is used because this
# tracker is noisy at 30 ms sampling (median sample-to-sample speed is
# already ~0.73 px/ms; 30 deg/s would flag ~35% of samples). Approximate —
# the dataset has no screen/distance metadata.
SCREEN_SACCADE_PX_PER_MS = 3.8


def _read_gaze_csv(path: str) -> list:
    """
    Reads a Desktop Activities gaze CSV. Columns confirmed from the actual
    dataset: participant, set, activity, x, y, timestamp (ms).
    Returns a list of (x, y, timestamp_ms) tuples.
    """
    points = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                points.append((float(row["x"]), float(row["y"]), float(row["timestamp"])))
            except (KeyError, ValueError, TypeError):
                continue
    return points


def _compute_gaze_features_from_points(points: list) -> dict:
    """
    Computes fixation_stability, saccade_rate, offcam_deviation, blink_rate
    directly from (x, y, timestamp_ms) gaze-coordinate samples.

    This is DIFFERENT from extract_gaze_features() (which runs MediaPipe on
    raw video for your own volunteer data) — the Desktop Activities dataset
    already provides extracted gaze coordinates, not video, so it needs its
    own feature computation. Both paths are designed to output the SAME
    four feature names, which is what makes z-scoring against this Stage 1
    baseline valid for Stage 2's MediaPipe-derived features.

    Known limitations (state these explicitly in the report):
    - blink_rate is a PROXY (timestamp gaps > 3x median interval), since
      this dataset has no pupil-validity/blink-flag column. Treat this
      feature's baseline as lower-confidence than the other three.
    - offcam_deviation is an ADAPTED proxy (dispersion from the gaze
      centroid), since this dataset is 100% on-screen gaze — there is no
      literal "looking away from camera" event to measure here, unlike in
      your own volunteers' interview recordings.
    - saccade_rate uses a FIXED velocity threshold (SCREEN_SACCADE_PX_PER_MS)
      approximating ~30 deg/s at a typical desktop viewing distance, since
      exact screen size and distance metadata aren't available. (A per-clip
      90th-percentile threshold flags ~10% of samples by construction, which
      made saccade_rate a constant ~ sampling_rate / 10.)
    """
    if len(points) < 2:
        return {"fixation_stability": float("nan"), "saccade_rate": float("nan"), "offcam_deviation": float("nan"), "blink_rate": float("nan")}

    xs = np.array([p[0] for p in points])
    ys = np.array([p[1] for p in points])
    ts = np.array([p[2] for p in points])
    duration_sec = (ts[-1] - ts[0]) / 1000.0 if ts[-1] > ts[0] else 1.0

    dx = np.diff(xs)
    dy = np.diff(ys)
    dt = np.diff(ts)
    dt[dt == 0] = 1.0  # avoid divide-by-zero on duplicate timestamps
    velocity = np.sqrt(dx ** 2 + dy ** 2) / dt

    fast = velocity > SCREEN_SACCADE_PX_PER_MS
    saccade_events = int(np.sum(fast[1:] & ~fast[:-1]) + (1 if fast[0] else 0))  # count events, not samples
    saccade_rate = saccade_events / duration_sec if duration_sec > 0 else 0.0

    fixation_mask = ~fast
    if fixation_mask.sum() > 1:
        fixation_var = np.var(xs[1:][fixation_mask]) + np.var(ys[1:][fixation_mask])
        fixation_stability = 1.0 / (fixation_var + 1e-6)
    else:
        fixation_stability = 0.0

    centroid_x, centroid_y = xs.mean(), ys.mean()
    offcam_deviation = float(np.mean(np.sqrt((xs - centroid_x) ** 2 + (ys - centroid_y) ** 2)))

    median_interval = np.median(dt)
    gap_threshold = median_interval * 3
    blink_events = np.sum(dt > gap_threshold)
    blink_rate = (blink_events / duration_sec) * 60 if duration_sec > 0 else 0.0  # per minute

    return {
        "fixation_stability": float(fixation_stability),
        "saccade_rate": float(saccade_rate),
        "offcam_deviation": offcam_deviation,
        "blink_rate": float(blink_rate),
    }


def _summarize(values: list) -> dict:
    """Returns mean/std for z-scoring. Falls back gracefully on empty input."""
    arr = np.array(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) == 0:
        return {"mean": 0.0, "std": 1.0, "n": 0}
    return {"mean": float(arr.mean()), "std": float(arr.std() or 1.0), "n": len(arr)}


def calibrate_gaze_baseline(csv_paths: list) -> dict:
    """
    Computes gaze baseline stats from Desktop Activities CSVs (confirmed
    structure: P01_BROWSE.csv ... P24_WRITE.csv — 24 participants x 8
    activities = up to 192 files, columns: participant, set, activity, x,
    y, timestamp).

    Uses _compute_gaze_features_from_points, NOT extract_gaze_features —
    this dataset provides pre-extracted gaze coordinates, not video, so it
    needs the CSV-based computation path (see that function’s docstring
    for the blink_rate/offcam_deviation proxy caveats).

    DOMAIN MISMATCH WARNING:
    This dataset measures screen-level point-of-regard (where on a monitor
    someone looks, tracked by a dedicated eye tracker over a ~24" physical
    range). extract_gaze_features() measures iris landmark position within
    a face crop from MediaPipe FaceMesh (pixel coordinates within a webcam
    frame). These are fundamentally different physical quantities — no
    single rescale constant reconciles them. The domain_mismatch_warning
    flag is set so baseline_utils.py skips z-scoring for this group.
    """
    fixation, saccade, offcam, blink = [], [], [], []

    for path in csv_paths:
        points = _read_gaze_csv(path)
        if not points:
            print(f"[skip] {path}: no valid rows read")
            continue
        feats = _compute_gaze_features_from_points(points)
        fixation.append(feats["fixation_stability"])
        saccade.append(feats["saccade_rate"])
        offcam.append(feats["offcam_deviation"])
        blink.append(feats["blink_rate"])

    result = {
        "domain_mismatch_warning": True,
        "fixation_stability": _summarize(fixation),
        "saccade_rate": _summarize(saccade),
        "offcam_deviation": _summarize(offcam),
        "blink_rate": _summarize(blink),
    }
    return result


def calibrate_latency_baseline(clip_paths: list) -> dict:
    """Runs extract_latency_features over Svarah clips (read + spontaneous).

    Svarah clips are pre-segmented utterances with no preceding question, so
    response_delay is NaN for all of them (n=0 in the output) and is left
    un-normalized downstream — that is expected, not a failure.
    """
    delay, pause_rate, pause_len, pause_var = [], [], [], []
    total = len(clip_paths)
    print(f"Processing {total} latency audio clips...")

    for i, path in enumerate(clip_paths, 1):
        try:
            feats = extract_latency_features(path, normalize=False)
            delay.append(feats["response_delay"])
            pause_rate.append(feats["pause_rate"])
            pause_len.append(feats["avg_pause_length"])
            pause_var.append(feats["pause_variance"])
        except Exception as e:
            print(f"[Warning] Failed to process {path}: {e}")

        if i % 100 == 0 or i == total:
            print(f"  Latency progress: {i}/{total} clips processed...")

    return {
        "response_delay": _summarize(delay),
        "pause_rate": _summarize(pause_rate),
        "avg_pause_length": _summarize(pause_len),
        "pause_variance": _summarize(pause_var),
    }


def calibrate_linguistic_baseline(clip_paths: list) -> dict:
    """Runs extract_linguistic_features over Svarah + Real-life Trial clips."""
    filler, rate, diversity, complexity = [], [], [], []
    total = len(clip_paths)
    print(f"Processing {total} linguistic clips with Whisper...")

    for i, path in enumerate(clip_paths, 1):
        try:
            feats = extract_linguistic_features(path, normalize=False)
            filler.append(feats["filler_rate"])
            rate.append(feats["speaking_rate"])
            diversity.append(feats["lexical_diversity"])
            complexity.append(feats["sentence_complexity"])
        except Exception as e:
            print(f"[Warning] Failed to transcribe {path}: {e}")

        if i % 10 == 0 or i == total:
            print(f"  Linguistic progress: {i}/{total} clips processed...")

    return {
        "filler_rate": _summarize(filler),
        "speaking_rate": _summarize(rate),
        "lexical_diversity": _summarize(diversity),
        "sentence_complexity": _summarize(complexity),
    }


def _stage2_clip_paths() -> set:
    """Every video/audio path referenced in labels.csv, resolved, so Stage 1
    never computes its baseline from clips that Stage 2 evaluates on."""
    if not Path(LABELS_PATH).exists():
        return set()
    labels = pd.read_csv(LABELS_PATH)
    paths = set()
    for col in ("video_path", "audio_path"):
        if col in labels.columns:
            for value in labels[col].dropna():
                if str(value).strip():
                    paths.add(str(resolve_project_path(str(value).strip()).resolve()))
    return paths


def _sample(paths: list, k: int, rng: random.Random) -> list:
    """Seeded random sample (k <= 0 means all). Sorted-order slicing, used
    previously, is not a random sample: it took whichever files sort first."""
    if k <= 0 or k >= len(paths):
        return list(paths)
    return sorted(rng.sample(paths, k))


def main():
    parser = argparse.ArgumentParser(description="Stage 1 Population Calibration")
    parser.add_argument("--check-paths", action="store_true", help="Only check and count dataset files without running calibration")
    parser.add_argument("--max-latency", type=int, default=500, help="Svarah clips sampled for the latency baseline (default 500, 0 = all)")
    parser.add_argument("--max-linguistic", type=int, default=50, help="Clips transcribed for the linguistic baseline, split evenly between Real-life Trial and Svarah (default 50, 0 = all)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for clip sampling (default 42)")
    args = parser.parse_args()
    rng = random.Random(args.seed)

    excluded = _stage2_clip_paths()
    not_in_stage2 = lambda paths: [p for p in paths if str(Path(p).resolve()) not in excluded]

    # Desktop Activities
    desktop_activities_clips = sorted(str(p) for p in Path(DESKTOP_ACTIVITIES_DIR).glob("*.csv"))
    print(f"Desktop Activities: Found {len(desktop_activities_clips)} CSV files.")

    # Svarah (audio/video clips)
    svarah_clips = sorted(str(p) for p in Path(SVARAH_DIR).rglob("*.wav")) + sorted(str(p) for p in Path(SVARAH_DIR).rglob("*.mp4")) if Path(SVARAH_DIR).exists() else []
    print(f"Svarah: Found {len(svarah_clips)} audio/video files.")

    # Real-life Trial (video clips) — minus any clip used as Stage 2 data
    all_trial_clips = sorted(str(p) for p in Path(REAL_LIFE_TRIAL_DIR).rglob("*.mp4")) if Path(REAL_LIFE_TRIAL_DIR).exists() else []
    real_life_trial_clips = not_in_stage2(all_trial_clips)
    svarah_clips = not_in_stage2(svarah_clips)
    print(f"Real-life Trial: Found {len(all_trial_clips)} MP4 video clips "
          f"({len(all_trial_clips) - len(real_life_trial_clips)} excluded because labels.csv uses them as Stage 2 data).")

    if args.check_paths:
        print("\n[Paths check complete] All paths verified. Ready for calibration.")
        return

    print("\n[1/3] Calibrating gaze baseline from Eye Movement Desktop Activities dataset...")
    gaze_baseline = calibrate_gaze_baseline(desktop_activities_clips) if desktop_activities_clips else {}

    print("\n[2/3] Calibrating latency baseline from Svarah...")
    latency_subset = _sample(svarah_clips, args.max_latency, rng)
    latency_baseline = calibrate_latency_baseline(latency_subset) if latency_subset else {}

    print("\n[3/3] Calibrating linguistic baseline from Real-life Trial + Svarah...")
    # Split the budget evenly across the two sources. Previously the trial
    # clips were listed first and the list was cut at 50, so Svarah was never
    # used at all and the 50 were mostly deceptive ("lie") testimony.
    if args.max_linguistic > 0:
        n_trial = min(len(real_life_trial_clips), args.max_linguistic // 2)
        n_svarah = min(len(svarah_clips), args.max_linguistic - n_trial)
        linguistic_subset = _sample(real_life_trial_clips, n_trial, rng) + _sample(svarah_clips, n_svarah, rng)
    else:
        n_trial, n_svarah = len(real_life_trial_clips), len(svarah_clips)
        linguistic_subset = real_life_trial_clips + svarah_clips
    linguistic_baseline = calibrate_linguistic_baseline(linguistic_subset) if linguistic_subset else {}

    baseline_stats = {
        "_meta": {
            "seed": args.seed,
            "latency_clips": {"svarah": len(latency_subset)},
            "linguistic_clips": {"real_life_trial": n_trial, "svarah": n_svarah},
            "stage2_clips_excluded": len(excluded),
            "gaze_saccade_threshold_px_per_ms": SCREEN_SACCADE_PX_PER_MS,
        },
        "gaze": gaze_baseline,
        "latency": latency_baseline,
        "linguistic": linguistic_baseline,
    }

    Path(BASELINE_OUTPUT_PATH).parent.mkdir(exist_ok=True)
    with open(BASELINE_OUTPUT_PATH, "w") as f:
        json.dump(baseline_stats, f, indent=2)

    print(f"\nBaseline stats saved to {BASELINE_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
