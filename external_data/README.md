# Stage 1 External Datasets

Stage 1 external datasets have been transferred into their respective subdirectories within this folder:

- `external_data/desktop_activities/` (192 CSVs) -> Eye Movement Desktop Activities gaze baseline
- `external_data/svarah/` (6,656 WAVs)           -> Svarah speech latency + linguistic baseline
- `external_data/real_life_trial/` (121 files)    -> Real-life Trial video and linguistic dataset

## Configuration

Paths are centrally managed in `src/paths_config.py`. The system checks these local `external_data/` directories first, and will seamlessly fall back to `EXTERNAL_DRIVE_ROOT` if needed.

## Ethics and Privacy Notice

Real-life Trial involves courtroom video footage of real individuals — do not commit video files to Git repositories, and do not display/replay clips publicly. Keep this data local and secure.
