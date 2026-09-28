"""
evaluate_model.py

Runs the per-feature-group ablation study described in proposal Section 7:
gaze-only, latency-only, linguistic-only and combined feature sets, for both
the logistic-regression and XGBoost models, under leave-speaker-out CV,
against a naive majority-class baseline. The combined set is also run
without per-speaker normalization, to show what that step contributes.

All numbers are pooled out-of-fold metrics with speaker-bootstrap 95% CIs
(see modeling_utils.py).

Usage:
    python src/evaluate_model.py
    python src/evaluate_model.py --permutations 500   # add permutation p-values (slower)
Output:
    data/ablation_results.csv
    prints model weights/importances from the combined models
"""

import argparse

import pandas as pd

from modeling_utils import (
    FEATURE_GROUPS,
    MODEL_NAMES,
    SPEAKER_COL,
    check_design,
    evaluate,
    load_feature_table,
    majority_baseline,
    make_model,
    speaker_normalize,
)
from paths_config import DATA_DIR, FEATURES_PATH

REPORT_COLUMNS = [
    "roc_auc", "roc_auc_ci_low", "roc_auc_ci_high",
    "balanced_accuracy", "balanced_accuracy_ci_low", "balanced_accuracy_ci_high",
    "accuracy", "precision", "recall", "f1", "permutation_p", "n_clips", "n_speakers",
]


def main(n_perm: int, n_boot: int) -> None:
    df, active = load_feature_table(FEATURES_PATH)
    if df[SPEAKER_COL].nunique() < 2 or df["label"].nunique() < 2:
        print("[Error] Need at least 2 speakers and both classes for the ablation study.")
        return
    check_design(df)

    active_groups = {}
    for group_name, cols in FEATURE_GROUPS.items():
        filtered = [c for c in cols if c in active]
        if filtered:
            active_groups[group_name] = filtered
        else:
            print(f"[Info] Skipping ablation group '{group_name}' — none of its features are available")

    results = {"majority_class_baseline": majority_baseline(df)}
    for model_name in MODEL_NAMES:
        for group_name, cols in active_groups.items():
            print(f"Running ablation: {model_name} / {group_name}")
            results[f"{model_name}/{group_name}"], _, _ = evaluate(df, cols, model_name, True, n_boot, n_perm)
        if "combined" in active_groups:
            print(f"Running ablation: {model_name} / combined (no speaker normalization)")
            results[f"{model_name}/combined_no_speaker_norm"], _, _ = evaluate(
                df, active_groups["combined"], model_name, False, n_boot, n_perm)

    results_df = pd.DataFrame(results).T.reindex(columns=REPORT_COLUMNS)
    pd.set_option("display.width", 200)
    print("\n=== Ablation study results (pooled leave-speaker-out, out-of-fold) ===")
    print(results_df[["roc_auc", "roc_auc_ci_low", "roc_auc_ci_high", "balanced_accuracy", "f1", "permutation_p"]].round(3))
    DATA_DIR.mkdir(exist_ok=True)
    results_df.to_csv(DATA_DIR / "ablation_results.csv")

    # Model weights/importances from the combined models fit on all data —
    # descriptive only; the headline numbers are the out-of-fold ones above.
    combined_cols = active_groups.get("combined")
    if combined_cols:
        X_full = speaker_normalize(df, combined_cols)
        y_full = df["label"].astype(int)

        logreg = make_model("logreg").fit(X_full, y_full)
        coefs = pd.Series(logreg.named_steps["clf"].coef_[0], index=combined_cols)
        print("\n=== Logistic regression standardized coefficients (positive = more 'assisted') ===")
        print(coefs.reindex(coefs.abs().sort_values(ascending=False).index).round(3))

        booster = make_model("xgb").fit(X_full, y_full)
        importances = pd.Series(booster.feature_importances_, index=combined_cols)
        print("\n=== XGBoost feature importances ===")
        print(importances.sort_values(ascending=False).round(3))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Feature-group ablation study")
    parser.add_argument("--permutations", type=int, default=0, help="Permutation-test shuffles per row (default 0 = skip)")
    parser.add_argument("--bootstrap", type=int, default=1000, help="Speaker-bootstrap resamples for CIs (default 1000)")
    args = parser.parse_args()
    main(args.permutations, args.bootstrap)
