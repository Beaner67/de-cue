"""
train_model.py

Trains the assisted-vs-unassisted detector on the master feature table with
leave-speaker-out cross-validation (never split by clip — see proposal
Section 4.4: splitting by clip lets the model memorize faces instead of
learning the behavioral signature).

Reports POOLED out-of-fold metrics with speaker-bootstrap 95% CIs and a
within-speaker permutation-test p-value (see modeling_utils.py for why),
then fits a final model on all clips for the dashboard.

Usage:
    python src/train_model.py                      # logistic regression, speaker-normalized
    python src/train_model.py --model xgb          # XGBoost instead
    python src/train_model.py --no-speaker-norm    # raw (Stage-1 z-scored) features
    python src/train_model.py --permutations 0     # skip the permutation test
    python src/train_model.py --include-excluded   # sensitivity run: keep volunteers in volunteer_exclusions.csv
Output:
    models/detector.json        final model (XGBoost native JSON, or logistic-regression weights)
    models/detector_meta.json   features, preprocessing and CV metrics the dashboard must match
    data/cv_results.csv         per-held-out-speaker accuracy
    data/oof_predictions.csv    one out-of-fold probability per clip
With --include-excluded the CSVs get an _all_volunteers suffix and no final
model is saved: the deployable model is always the one without excluded
(protocol-failure) volunteers.
"""

import argparse
import json

import pandas as pd

from modeling_utils import (
    MODEL_NAMES,
    SPEAKER_COL,
    check_design,
    evaluate,
    load_feature_table,
    load_volunteer_exclusions,
    make_model,
    speaker_normalize,
)
from paths_config import DATA_DIR, FEATURES_PATH, MODELS_DIR

MODEL_OUTPUT_PATH = MODELS_DIR / "detector.json"
META_OUTPUT_PATH = MODELS_DIR / "detector_meta.json"


def save_final_model(model, model_name: str, features: list, speaker_norm: bool, cv_summary: dict) -> None:
    MODELS_DIR.mkdir(exist_ok=True)
    if model_name == "xgb":
        model.save_model(str(MODEL_OUTPUT_PATH))
    else:
        scaler, clf = model.named_steps["scale"], model.named_steps["clf"]
        with open(MODEL_OUTPUT_PATH, "w") as f:
            json.dump({
                "model_type": "logistic_regression",
                "features": features,
                "scaler_mean": scaler.mean_.tolist(),
                "scaler_scale": scaler.scale_.tolist(),
                "coef": clf.coef_[0].tolist(),
                "intercept": float(clf.intercept_[0]),
                "usage": "p = sigmoid(intercept + sum(coef * (x - scaler_mean) / scaler_scale))",
            }, f, indent=2)

    with open(META_OUTPUT_PATH, "w") as f:
        json.dump({
            "model_type": model_name,
            "features": features,
            "excluded_volunteers": load_volunteer_exclusions(),
            "speaker_normalization": (
                "per-speaker mean centering: subtract the candidate's mean over all their answers "
                "(feature by feature) before scoring" if speaker_norm else "none"
            ),
            "cv": {k: (None if pd.isna(v) else v) for k, v in cv_summary.items()},
        }, f, indent=2)


def train_and_evaluate(model_name: str, speaker_norm: bool, n_perm: int, n_boot: int,
                       include_excluded: bool = False) -> None:
    df, features = load_feature_table(FEATURES_PATH, include_excluded=include_excluded)
    suffix = "_all_volunteers" if include_excluded else ""
    if not features:
        print("[Error] No valid feature columns remain after dropping all-NaN columns.")
        return
    if df[SPEAKER_COL].nunique() < 2 or df["label"].nunique() < 2:
        print("[Error] Need at least 2 speakers and both classes to run leave-speaker-out CV.")
        return
    check_design(df)

    print(f"Model: {model_name} | speaker normalization: {'on' if speaker_norm else 'off'} | "
          f"{len(df)} clips, {df[SPEAKER_COL].nunique()} speakers, {len(features)} features")

    summary, oof_prob, fold_rows = evaluate(df, features, model_name, speaker_norm, n_boot=n_boot, n_perm=n_perm)

    for row in fold_rows:
        print(f"[fold] held out {row['held_out_speaker']} ({row['n_clips']} clips): acc={row['accuracy']:.3f}")

    print("\n=== Pooled leave-speaker-out results (out-of-fold) ===")
    print(f"ROC-AUC           {summary['roc_auc']:.3f}  (95% CI {summary['roc_auc_ci_low']:.3f}-{summary['roc_auc_ci_high']:.3f}, speaker bootstrap)")
    print(f"Balanced accuracy {summary['balanced_accuracy']:.3f}  (95% CI {summary['balanced_accuracy_ci_low']:.3f}-{summary['balanced_accuracy_ci_high']:.3f})")
    print(f"Accuracy {summary['accuracy']:.3f} | Precision {summary['precision']:.3f} | Recall {summary['recall']:.3f} | F1 {summary['f1']:.3f}")
    if n_perm > 0:
        print(f"Permutation test  p = {summary['permutation_p']:.4f}  ({n_perm} within-speaker label shuffles)")

    DATA_DIR.mkdir(exist_ok=True)
    pd.DataFrame(fold_rows).to_csv(DATA_DIR / f"cv_results{suffix}.csv", index=False)
    pd.DataFrame({
        "clip_id": df["clip_id"],
        SPEAKER_COL: df[SPEAKER_COL],
        "label": df["label"],
        "oof_prob_assisted": oof_prob,
    }).to_csv(DATA_DIR / f"oof_predictions{suffix}.csv", index=False)

    if include_excluded:
        print("\n[Info] Sensitivity run (--include-excluded): results written with the "
              f"'{suffix}' suffix; the final model is not saved.")
        return

    # Final model on ALL data, for deployment in the dashboard (not for reporting —
    # the headline numbers are the out-of-fold ones above).
    X_all = speaker_normalize(df, features) if speaker_norm else df[features].astype(float)
    final_model = make_model(model_name)
    final_model.fit(X_all, df["label"].astype(int))
    save_final_model(final_model, model_name, features, speaker_norm, summary)
    print(f"\nFinal model (trained on all data) saved to {MODEL_OUTPUT_PATH} (+ {META_OUTPUT_PATH.name})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the detector with leave-speaker-out CV")
    parser.add_argument("--model", choices=MODEL_NAMES, default="logreg")
    parser.add_argument("--no-speaker-norm", action="store_true", help="Disable per-speaker mean centering")
    parser.add_argument("--permutations", type=int, default=1000, help="Permutation-test shuffles (0 to skip; default 1000)")
    parser.add_argument("--bootstrap", type=int, default=1000, help="Speaker-bootstrap resamples for CIs (default 1000)")
    parser.add_argument("--include-excluded", action="store_true",
                        help="Keep volunteers listed in data/volunteer_exclusions.csv (sensitivity analysis)")
    args = parser.parse_args()
    train_and_evaluate(args.model, not args.no_speaker_norm, args.permutations, args.bootstrap, args.include_excluded)
