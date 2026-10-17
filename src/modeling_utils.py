"""
modeling_utils.py

Shared modelling/evaluation code for train_model.py and evaluate_model.py,
so both scripts evaluate in exactly the same way.

Evaluation design (all leave-speaker-out, see proposal Section 4.4):
    - Per-speaker normalization: every feature is centred on that speaker's
      own mean across ALL their clips. This removes stable individual
      differences (someone who always pauses a lot, always blinks a lot) and
      leaves the within-person change between conditions — the signal the
      detector is actually after. It uses no labels, and only the speaker's
      own clips, so it cannot leak information across CV folds. At
      deployment it maps to normalizing within one candidate's interview,
      which yields several answers. It assumes each speaker contributes clips
      from both conditions (the within-subjects protocol guarantees this).
    - Pooled out-of-fold (OOF) metrics: every clip gets exactly one
      prediction, from the fold where its speaker was held out; ROC-AUC etc.
      are computed once over all OOF predictions. Per-fold AUC on ~8 clips
      (or 2, in the proxy dry run) is too noisy to mean anything.
    - Speaker-level bootstrap 95% CIs: resample SPEAKERS (not clips) with
      replacement, since clips from one person are not independent.
    - Permutation test: shuffle condition labels WITHIN each speaker and
      rerun the whole CV; the p-value is how often chance matches or beats
      the real AUC.
"""

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURE_GROUPS = {
    "gaze_only": ["fixation_stability", "saccade_rate", "offcam_deviation", "blink_rate"],
    "latency_only": ["response_delay", "pause_rate", "avg_pause_length", "pause_variance"],
    "linguistic_only": ["filler_rate", "speaking_rate", "lexical_diversity", "sentence_complexity"],
}
FEATURE_GROUPS["combined"] = [c for cols in FEATURE_GROUPS.values() for c in cols]


def load_gaze_exclusions() -> dict:
    """{clip_id: reason} from data/gaze_exclusions.csv, or {} if the file is absent."""
    from paths_config import GAZE_EXCLUSIONS_PATH
    if not GAZE_EXCLUSIONS_PATH.exists():
        return {}
    ex = pd.read_csv(GAZE_EXCLUSIONS_PATH, dtype=str).fillna("")
    return dict(zip(ex["clip_id"].str.strip(), ex["reason"]))


def apply_gaze_exclusions(df: pd.DataFrame) -> pd.DataFrame:
    """Sets the gaze features of excluded clips to NaN. A frozen webcam image
    gives MediaPipe identical landmarks frame after frame, so fixation
    stability explodes and blinks/saccades read as zero: values that look
    valid but describe no behaviour. Marking them NaN (the extractors' own
    convention for features that can't be computed) keeps them out of
    training instead of silently skewing the per-speaker centring. The
    clip's audio-based features are unaffected by a video freeze, but
    load_feature_table() drops any row with a NaN, so the whole clip leaves
    the model; that is the documented cost of this rule."""
    excluded = load_gaze_exclusions()
    gaze = [c for c in FEATURE_GROUPS["gaze_only"] if c in df.columns]
    mask = df["clip_id"].isin(excluded)
    if mask.any():
        df = df.copy()
        df.loc[mask, gaze] = np.nan
    return df
FEATURE_COLUMNS = FEATURE_GROUPS["combined"]

MODEL_NAMES = ["logreg", "xgb"]
SPEAKER_COL = "volunteer_id"
RANDOM_STATE = 42


def load_volunteer_exclusions() -> dict:
    """{volunteer_id: reason} from data/volunteer_exclusions.csv, or {} if the file is absent."""
    from paths_config import VOLUNTEER_EXCLUSIONS_PATH
    if not VOLUNTEER_EXCLUSIONS_PATH.exists():
        return {}
    ex = pd.read_csv(VOLUNTEER_EXCLUSIONS_PATH, dtype=str).fillna("")
    return dict(zip(ex[SPEAKER_COL].str.strip(), ex["reason"]))


def load_feature_table(path, feature_columns=FEATURE_COLUMNS, include_excluded: bool = False) -> tuple:
    """
    Reads features.csv and returns (df, active_features):
      - volunteers listed in volunteer_exclusions.csv are dropped, unless
        include_excluded (the sensitivity analysis). This happens at load
        time, not in build_features.py, so switching needs no re-extraction;
      - columns that are NaN for EVERY clip are dropped (structurally
        unavailable, e.g. response_delay without question_end_time);
      - rows with NaN in any remaining feature are dropped (extraction failures).
    """
    df = pd.read_csv(path)
    excluded = load_volunteer_exclusions()
    if excluded:
        if include_excluded:
            print(f"[Info] Including {len(excluded)} volunteer(s) listed in volunteer_exclusions.csv: {sorted(excluded)}")
        else:
            mask = df[SPEAKER_COL].isin(excluded)
            print(f"[Info] Excluding {df.loc[mask, SPEAKER_COL].nunique()} volunteer(s) ({int(mask.sum())} clips) "
                  f"listed in volunteer_exclusions.csv: {sorted(excluded)}")
            df = df[~mask].reset_index(drop=True)

    active = [c for c in feature_columns if c in df.columns]
    missing = [c for c in feature_columns if c not in df.columns]
    if missing:
        print(f"[Warning] features.csv has no column(s) {missing} — rerun build_features.py after updating extractors.")

    all_nan = [c for c in active if df[c].isna().all()]
    if all_nan:
        print(f"[Info] Dropping {len(all_nan)} feature column(s) that are NaN for ALL clips (structurally unavailable): {all_nan}")
        active = [c for c in active if c not in all_nan]

    nan_mask = df[active].isna().any(axis=1)
    if nan_mask.any():
        print(f"[Warning] Dropping {int(nan_mask.sum())} row(s) with NaN features (failed extraction or listed in gaze_exclusions.csv): {df.loc[nan_mask, 'clip_id'].tolist()}")
        df = df[~nan_mask].reset_index(drop=True)

    return df, active


def check_design(df: pd.DataFrame) -> None:
    """Warns about speakers that break the within-subjects assumption."""
    per_speaker = df.groupby(SPEAKER_COL)["label"].agg(["nunique", "size"])
    lopsided = per_speaker[per_speaker["nunique"] < 2].index.tolist()
    if lopsided:
        print(f"[Warning] Speaker(s) with clips from only ONE condition after cleaning: {lopsided}. "
              "Per-speaker centering is only meaningful when each speaker has both conditions.")


def speaker_normalize(df: pd.DataFrame, feature_cols: list) -> pd.DataFrame:
    """Centres each feature on its speaker's mean (label-free, per speaker)."""
    X = df[feature_cols].astype(float)
    return X - X.groupby(df[SPEAKER_COL]).transform("mean")


def make_model(name: str):
    """
    logreg: standardized L2-regularized logistic regression — the primary
        model: few parameters, stable with ~100 clips, interpretable weights.
    xgb: shallow, regularized XGBoost as the non-linear comparison. The old
        settings (depth 4, unregularized) were far too flexible for this data.
    """
    if name == "logreg":
        return Pipeline([
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000)),
        ])
    if name == "xgb":
        return xgb.XGBClassifier(
            n_estimators=100,
            max_depth=2,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=1,
            reg_lambda=1.0,
            random_state=RANDOM_STATE,
            eval_metric="logloss",
        )
    raise ValueError(f"Unknown model '{name}' (choose from {MODEL_NAMES})")


def cross_validate(X: pd.DataFrame, y: pd.Series, groups: pd.Series, model_name: str) -> tuple:
    """
    Leave-one-speaker-out CV. Returns (oof_prob, fold_rows).
    A training fold with only one class can't fit a classifier; it predicts
    the training prevalence instead (and says so).
    """
    oof_prob = np.full(len(y), np.nan)
    fold_rows = []
    for train_idx, test_idx in LeaveOneGroupOut().split(X, y, groups):
        y_train = y.iloc[train_idx]
        if y_train.nunique() < 2:
            oof_prob[test_idx] = float(y_train.mean())
        else:
            model = make_model(model_name)
            model.fit(X.iloc[train_idx], y_train)
            oof_prob[test_idx] = model.predict_proba(X.iloc[test_idx])[:, 1]

        y_test = y.iloc[test_idx]
        preds = (oof_prob[test_idx] >= 0.5).astype(int)
        fold_rows.append({
            "held_out_speaker": groups.iloc[test_idx].iloc[0],
            "n_clips": len(test_idx),
            "accuracy": accuracy_score(y_test, preds),
        })
    return oof_prob, fold_rows


def pooled_metrics(y, prob, threshold: float = 0.5) -> dict:
    y = np.asarray(y)
    preds = (np.asarray(prob) >= threshold).astype(int)
    return {
        "n_clips": len(y),
        "accuracy": accuracy_score(y, preds),
        "balanced_accuracy": balanced_accuracy_score(y, preds),
        "precision": precision_score(y, preds, zero_division=0),
        "recall": recall_score(y, preds, zero_division=0),
        "f1": f1_score(y, preds, zero_division=0),
        "roc_auc": roc_auc_score(y, prob) if len(set(y)) > 1 else float("nan"),
    }


def speaker_bootstrap_ci(y, prob, groups, n_boot: int = 1000, seed: int = RANDOM_STATE) -> dict:
    """95% CIs for ROC-AUC and balanced accuracy, resampling speakers."""
    y, prob, groups = np.asarray(y), np.asarray(prob), np.asarray(groups)
    speakers = np.unique(groups)
    idx_by_speaker = {s: np.where(groups == s)[0] for s in speakers}
    rng = np.random.default_rng(seed)

    aucs, baccs = [], []
    for _ in range(n_boot):
        sample = rng.choice(speakers, size=len(speakers), replace=True)
        idx = np.concatenate([idx_by_speaker[s] for s in sample])
        if len(set(y[idx])) < 2:
            continue
        aucs.append(roc_auc_score(y[idx], prob[idx]))
        baccs.append(balanced_accuracy_score(y[idx], (prob[idx] >= 0.5).astype(int)))

    def ci(values):
        return (float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))) if values else (float("nan"), float("nan"))

    auc_lo, auc_hi = ci(aucs)
    bacc_lo, bacc_hi = ci(baccs)
    return {"roc_auc_ci_low": auc_lo, "roc_auc_ci_high": auc_hi,
            "balanced_accuracy_ci_low": bacc_lo, "balanced_accuracy_ci_high": bacc_hi}


def permutation_test(X, y, groups, model_name: str, observed_auc: float, n_perm: int, seed: int = RANDOM_STATE) -> float:
    """
    p-value for the observed pooled OOF AUC. Labels are shuffled within each
    speaker (keeps every speaker's condition balance, breaks the link between
    features and condition), then the full leave-speaker-out CV is rerun.
    """
    if n_perm <= 0 or np.isnan(observed_auc):
        return float("nan")
    rng = np.random.default_rng(seed)
    y_arr, g_arr = np.asarray(y), np.asarray(groups)
    at_least_as_good = 0
    for _ in range(n_perm):
        y_perm = y_arr.copy()
        for s in np.unique(g_arr):
            idx = np.where(g_arr == s)[0]
            y_perm[idx] = rng.permutation(y_arr[idx])
        y_perm = pd.Series(y_perm, index=y.index)
        prob, _ = cross_validate(X, y_perm, groups, model_name)
        if len(set(y_perm)) > 1 and roc_auc_score(y_perm, prob) >= observed_auc:
            at_least_as_good += 1
    return (at_least_as_good + 1) / (n_perm + 1)


def evaluate(df: pd.DataFrame, feature_cols: list, model_name: str, speaker_norm: bool = True,
             n_boot: int = 1000, n_perm: int = 0) -> tuple:
    """Full evaluation for one (feature set, model, normalization) combination.
    Returns (summary_dict, oof_prob, fold_rows)."""
    X = speaker_normalize(df, feature_cols) if speaker_norm else df[feature_cols].astype(float)
    y = df["label"].astype(int)
    groups = df[SPEAKER_COL]

    oof_prob, fold_rows = cross_validate(X, y, groups, model_name)
    summary = pooled_metrics(y, oof_prob)
    summary.update(speaker_bootstrap_ci(y, oof_prob, groups, n_boot=n_boot))
    summary["n_speakers"] = int(groups.nunique())
    summary["permutation_p"] = permutation_test(X, y, groups, model_name, summary["roc_auc"], n_perm)
    return summary, oof_prob, fold_rows


def majority_baseline(df: pd.DataFrame) -> dict:
    """Predicts each training fold's majority class with a constant score."""
    y = df["label"].astype(int)
    groups = df[SPEAKER_COL]
    prob = np.full(len(y), np.nan)
    for train_idx, test_idx in LeaveOneGroupOut().split(df, y, groups):
        prob[test_idx] = 1.0 if y.iloc[train_idx].mean() > 0.5 else 0.0
    summary = pooled_metrics(y, prob)
    summary["roc_auc"] = 0.5  # a constant score has no ranking ability by definition
    summary["n_speakers"] = int(groups.nunique())
    return summary
