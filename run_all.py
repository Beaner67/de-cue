"""
run_all.py

Runs the whole analysis in one command, in the order of the report's
Annexure D: Stage 1 calibration, feature extraction, training with
leave-speaker-out CV, then the ablation study. Each step runs with the
project venv from the project root and the run stops at the first step
that fails.

Clip cutting (assistant_tool/make_clips.py) is per session and is not
repeated here: the clips and data/labels.csv already exist.

Usage:
    run_all                  # full run (Stage 1 and Whisper are slow)
    run_all --quick          # reuse data/features.csv: train + ablation only
    run_all --fast           # skip the permutation tests (quick check)
    run_all --from features  # start at a later step

Stdlib only and Python 3.9 compatible, like the other root-level tools, so
it can be started with the system python; the steps themselves always run
in the venv.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC = PROJECT_ROOT / "src"
VENV_PYTHON = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"
if not VENV_PYTHON.exists():  # non-Windows venv layout
    VENV_PYTHON = PROJECT_ROOT / "venv" / "bin" / "python"

STEP_NAMES = ["stage1", "features", "train", "evaluate"]


def build_steps(fast: bool):
    perms = "0" if fast else "1000"
    return {
        "stage1": ("Stage 1 calibration -> models/baseline_stats.json",
                   ["pretrain_calibration.py"]),
        "features": ("Feature extraction -> data/features.csv",
                     ["build_features.py"]),
        "train": ("Training + leave-speaker-out CV -> models/detector.json",
                  ["train_model.py", "--permutations", perms]),
        "evaluate": ("Ablation study -> data/ablation_results.csv",
                     ["evaluate_model.py", "--permutations", perms]),
    }


def stage1_datasets_present() -> bool:
    """pretrain_calibration.py writes empty baselines when it finds no
    datasets, which would overwrite a good baseline_stats.json, so the
    folders are checked first."""
    sys.path.insert(0, str(SRC))
    import paths_config  # stdlib-only module

    ok = True
    for name in ("DESKTOP_ACTIVITIES_DIR", "SVARAH_DIR", "REAL_LIFE_TRIAL_DIR"):
        folder = Path(getattr(paths_config, name))
        if not folder.exists() or not any(folder.rglob("*.*")):
            print(f"  missing or empty: {name} = {folder}")
            ok = False
    return ok


def run_step(label: str, script_args: list) -> float:
    cmd = [str(VENV_PYTHON), str(SRC / script_args[0])] + script_args[1:]
    print(f"\n=== {label} ===")
    print("$ " + " ".join(["python", "src/" + script_args[0]] + script_args[1:]), flush=True)
    start = time.time()
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    elapsed = time.time() - start
    if result.returncode != 0:
        print(f"\n[failed] {script_args[0]} exited with code {result.returncode} "
              f"after {elapsed:.0f} s. Later steps were not run.")
        sys.exit(result.returncode)
    return elapsed


def main():
    parser = argparse.ArgumentParser(description="Run the whole De-Cue analysis in one command")
    parser.add_argument("--from", dest="start", choices=STEP_NAMES, default="stage1",
                        help="first step to run (default: stage1)")
    parser.add_argument("--quick", action="store_true",
                        help="reuse data/features.csv and run only train + evaluate (same as --from train)")
    parser.add_argument("--fast", action="store_true",
                        help="skip the permutation tests (p-values not computed)")
    args = parser.parse_args()

    if not VENV_PYTHON.exists():
        sys.exit(f"Project venv not found at {VENV_PYTHON}. Create it as described in README.md.")

    start = "train" if args.quick else args.start
    todo = STEP_NAMES[STEP_NAMES.index(start):]
    steps = build_steps(args.fast)

    if "stage1" in todo:
        print("Checking Stage 1 datasets...")
        if not stage1_datasets_present():
            sys.exit("Stage 1 datasets not found; models/baseline_stats.json was left as it is.\n"
                     "Fix EXTERNAL_DRIVE_ROOT in src/paths_config.py, or run: run_all --from features")
    if start in ("train", "evaluate") and not (PROJECT_ROOT / "data" / "features.csv").exists():
        sys.exit("data/features.csv not found; run without --quick/--from to build it first.")

    timings = []
    for name in todo:
        label, script_args = steps[name]
        timings.append((name, run_step(label, script_args)))

    print("\n=== Done ===")
    for name, seconds in timings:
        print(f"  {name:<9} {seconds / 60:6.1f} min")
    if args.fast:
        print("  (--fast: permutation tests skipped)")


if __name__ == "__main__":
    main()
