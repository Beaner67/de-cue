"""
build_features.py

Runs gaze, latency, and linguistic feature extraction over every clip listed
in data/labels.csv and writes one combined master feature table.

Paths in labels.csv may be absolute or relative to the project root.

Usage:
    python src/build_features.py
Output:
    data/features.csv
"""

import pandas as pd

from extract_gaze import extract_gaze_features
from extract_latency import extract_latency_features
from extract_linguistic import extract_linguistic_features
from modeling_utils import FEATURE_COLUMNS
from paths_config import FEATURES_PATH, LABELS_PATH, resolve_project_path

OUTPUT_PATH = FEATURES_PATH


def build_features():
    labels_df = pd.read_csv(LABELS_PATH)

    # question_end_time drives response_delay. The session protocol trims every
    # clip to start exactly when the question ends, so for protocol clips the
    # correct value is 0.0. Leaving it out makes response_delay NaN for every
    # clip, and training then silently drops the feature.
    has_question_end_time = "question_end_time" in labels_df.columns
    if not has_question_end_time:
        print("[Warning] labels.csv has no 'question_end_time' column — response_delay will be NaN for all clips.")
        print("          For clips trimmed per the session protocol (starting at question end), add the column with 0.0.")

    rows = []

    for _, row in labels_df.iterrows():
        clip_id = row["clip_id"]
        video_path = str(resolve_project_path(row["video_path"]))
        # If you extract audio separately (e.g. via ffmpeg) point this at the .wav instead
        raw_audio = row.get("audio_path")
        audio_path = str(resolve_project_path(str(raw_audio).strip())) if (pd.notna(raw_audio) and str(raw_audio).strip()) else video_path

        if not resolve_project_path(video_path).exists():
            print(f"[skip] {clip_id}: video not found at {video_path}")
            continue

        # Read question_end_time: None means "not available", 0.0 means "clip starts at answer"
        question_end_time = None
        if has_question_end_time:
            raw_qet = row.get("question_end_time")
            if pd.notna(raw_qet) and str(raw_qet).strip() != "":
                question_end_time = float(raw_qet)

        print(f"[processing] {clip_id}")

        gaze_feats = extract_gaze_features(video_path)
        latency_feats = extract_latency_features(audio_path, question_end_time=question_end_time)
        linguistic_feats = extract_linguistic_features(audio_path)

        combined = {
            "clip_id": clip_id,
            "volunteer_id": row["volunteer_id"],
            "condition": row["condition"],
            "question_type": row.get("question_type", ""),
            **gaze_feats,
            **latency_feats,
            **{k: v for k, v in linguistic_feats.items() if k != "transcript"},
            "transcript": linguistic_feats.get("transcript", ""),
            "label": row["label"],
        }
        rows.append(combined)

    features_df = pd.DataFrame(rows)

    # Log NaN summary so the user knows which clips/features had extraction failures
    nan_counts = features_df[FEATURE_COLUMNS].isna().sum()
    nan_features = nan_counts[nan_counts > 0]
    if len(nan_features) > 0:
        print(f"\n[NaN summary] The following features have missing values:")
        for feat, count in nan_features.items():
            nan_clips = features_df.loc[features_df[feat].isna(), "clip_id"].tolist()
            print(f"  {feat}: {count} clip(s) — {nan_clips}")
        print("  These rows will be excluded from training by train_model.py.")

    features_df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nWrote {len(features_df)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    build_features()
