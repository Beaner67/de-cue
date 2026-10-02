# AGENTS.md

Instructions for AI coding assistants working in this repository. For the
full project documentation, see [README.md](README.md).

## Project in one paragraph

De-Cue detects covert real-time LLM assistance in video interviews from
behavioural signals. There are 12 features in three groups: gaze, latency
and linguistic. **Stage 1** (`pretrain_calibration.py`) computes a population
mean/std for each feature from public datasets. **Stage 2**
(`build_features.py` → `train_model.py` / `evaluate_model.py`) extracts the
same features from a small within-subjects volunteer dataset, then trains
and evaluates with leave-speaker-out cross-validation. This is a final year
thesis project, so correct methodology matters more than raw performance.

## Hard rules — do not break these

1. **Split by `volunteer_id`, never by `clip_id`.** Every CV split,
   bootstrap and permutation in `src/modeling_utils.py` works at the speaker
   level. A clip-level split leaks identity and invalidates the evaluation.
   Don't add `train_test_split`, `KFold` or anything else that ignores
   speaker groups.
2. **Never commit participant data.** Leave `data/raw/`, generated CSVs
   (`features.csv`, `cv_results.csv`, `oof_predictions.csv`,
   `ablation_results.csv`), `models/*.json` and everything under
   `external_data/*/` out of git. Don't weaken `.gitignore`. The Real-life
   Trial dataset is courtroom footage of real people: never copy, display or
   upload it.
3. **Keep Stage 1 and Stage 2 identical.** Both stages must compute features
   the same way, or the z-scoring is meaningless. Latency and linguistic
   baselines reuse the `extract_*_features()` functions directly. The gaze
   baseline **does not**: Desktop Activities provides gaze coordinates, not
   video, so `pretrain_calibration.py` has its own
   `_compute_gaze_features_from_points()`. If you change a feature
   definition in `extract_gaze.py`, update that function to match, or state
   clearly why they differ.
4. **Per-speaker centering is part of the model contract.** `train_model.py`
   writes it into `models/detector_meta.json`, and any consumer (for example
   the dashboard) must reproduce it. If you change the preprocessing, update
   the metadata that `save_final_model()` writes.
5. **Report pooled out-of-fold metrics**, with speaker-bootstrap CIs and the
   within-speaker permutation test. Don't replace them with per-fold
   averages.

## Code conventions

- **Paths:** import them from `src/paths_config.py`. Never hardcode a path or
  build one relative to the current directory. Resolve paths read from
  `labels.csv` with `resolve_project_path()`.
- **Imports:** scripts import siblings as top-level modules (e.g.
  `from modeling_utils import ...`), so run them as `python src/<script>.py`
  from the project root. There is no package or `__init__.py`; don't
  introduce one without updating every import.
- **Feature names:** they are defined once in `FEATURE_GROUPS` in
  `src/modeling_utils.py`, and each extractor has a matching `*_KEYS` list.
  Keep these in sync. The ablation study iterates over `FEATURE_GROUPS`.
- **Failure handling:** extractors return `NaN` for a feature they can't
  compute. They never raise mid-batch and never substitute a made-up value.
  `load_feature_table()` drops columns that are all NaN.
- **Randomness:** seed it (`RANDOM_STATE = 42`, `--seed 42`).
- **Comments:** existing comments explain *why* a choice was made (thresholds,
  known limitations to state in the thesis). Match that style and keep those
  comments when refactoring.
- **Dependencies:** install only `opencv-contrib-python`, never
  `opencv-python` alongside it. Keep `numpy==1.26.4` and `mediapipe==0.10.14`
  pinned unless you've checked that newer versions work together.

## Running things

```bash
pip install -r requirements.txt                    # also needs ffmpeg on PATH
python src/pretrain_calibration.py --check-paths   # quick: finds datasets only
python src/pretrain_calibration.py                 # Stage 1 -> models/baseline_stats.json
python src/build_features.py                       # -> data/features.csv
python src/train_model.py --permutations 0         # quick run without the permutation test
python src/evaluate_model.py                       # ablation -> data/ablation_results.csv
```

There is no test suite. To check a change:

- Run the affected script end to end on the current `data/labels.csv`.
- Confirm the printed NaN counts and metrics are sensible.
- For modelling changes, run `train_model.py` with and without
  `--no-speaker-norm`, and with `--model xgb`, to make sure nothing crashes.

Whisper and MediaPipe are slow on CPU; use `--permutations 0` and small
`--max-latency` / `--max-linguistic` values while iterating.

## Environment gotchas

- Stage 1 datasets live on an external drive whose letter changes.
  `EXTERNAL_DRIVE_ROOT` in `paths_config.py` is the only place to update;
  local copies in `external_data/` take priority over it.
- `data/labels.csv` holds real volunteer rows written by
  `assistant_tool/make_clips.py --update-labels`. Each clip starts at the
  question end, so `question_end_time` is 0.0. The earlier Real-life Trial
  placeholder rows were removed; don't mix them back in.
- `baseline_utils.py` skips z-scoring when `models/baseline_stats.json` is
  missing, or when a group is flagged `domain_mismatch_warning`. Raw values
  are then used silently, which is expected and not a bug.

## Docs to keep in sync

If you change commands, options, features or file formats, update
[README.md](README.md) and, where relevant, the session protocols in
[docs/](docs/). The protocols contain the `labels.csv` format and the
pipeline steps volunteers' data goes through.
