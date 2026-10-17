"""
make_clips.py

Cuts one session recording into per-question clips using the timestamps that
server.py logged, and writes the matching labels.csv rows. This replaces the
hand trimming in SESSION_PROTOCOL_GUIDE.md Section 5.1.

Each clip starts at the logged end of the question and ends at the logged end
of the answer, so question_end_time is 0.0 for every row. Clips are
re-encoded rather than stream-copied: "-c copy" can only cut at keyframes,
which would move the start of a clip by up to a few seconds and corrupt
response_delay.

Usage (from the project root):
    python assistant_tool/make_clips.py --volunteer 1 --recording "data/raw/volunteer_01/volunteer_01.mp4" --dry-run
    python assistant_tool/make_clips.py --volunteer 1 --recording "data/raw/volunteer_01/volunteer_01.mp4"
    python assistant_tool/make_clips.py --volunteer 1 --recording "data/raw/volunteer_01/volunteer_01.mp4" --update-labels

--offset (seconds) shifts every cut. Use it if you find, for example from a
clap at the start, that you pressed "Recording started" late (negative) or
early (positive). A constant offset shifts every response_delay in a session
by the same amount, which per-speaker centering in training removes anyway.
"""

# Lets the "X | None" type hints run on Python 3.9 as well as in the 3.12 venv.
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
# pyrefly: ignore [missing-import]
from paths_config import LABELS_PATH, PROJECT_ROOT, VOLUNTEER_RAW_DIR  # noqa: E402  (also puts ffmpeg on PATH)

LABEL_COLUMNS = ["clip_id", "volunteer_id", "condition", "question_num", "question_type",
                 "label", "video_path", "audio_path", "question_end_time"]
END_PAD_S = 0.5            # keep the tail of the last word
MIN_S, MAX_S = 5.0, 240.0  # clips outside this range are flagged for a manual check


def read_session(log_path: Path, session_id: str | None) -> list[dict]:
    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    sessions = [r["session_id"] for r in records if r["event"] == "session_start"]
    if not sessions:
        sys.exit(f"No session found in {log_path}")
    chosen = session_id or sessions[-1]
    if chosen not in sessions:
        sys.exit(f"Session {chosen} not in {log_path}. Sessions found: {', '.join(sessions)}")
    if not session_id and len(sessions) > 1:
        print(f"[Note] {len(sessions)} sessions in the log; using the latest ({chosen}). "
              f"Pass --session to pick another: {', '.join(sessions)}")
    return [r for r in records if r["session_id"] == chosen]


def collect_clips(records: list[dict]) -> tuple[float, list[dict], list[dict]]:
    """Pairs each answer_end with the latest question_end for the same question.
    Re-marked question ends and questions redone with "Back" use the last marks."""
    rec_starts = [r["t"] for r in records if r["event"] == "recording_start"]
    if not rec_starts:
        sys.exit("This session has no 'Recording started' mark, so clip times can't be worked out.\n"
                 "Cut this session by hand as described in SESSION_PROTOCOL_GUIDE.md Section 5.1.")
    plan = next(r for r in records if r["event"] == "session_start")["plan"]

    question_end, clips = {}, {}
    for r in records:
        key = (r.get("condition"), r.get("question_num"))
        if r["event"] == "question_end":
            question_end[key] = r
        elif r["event"] == "answer_end" and key in question_end:
            q = question_end[key]
            clips[key] = {**{k: q[k] for k in ("round", "condition", "question_num", "question_type")},
                          "start_t": q["t"], "end_t": r["t"]}
    missing = [p for p in plan if (p["condition"], p["question_num"]) not in clips]
    return rec_starts[-1], sorted(clips.values(), key=lambda c: c["start_t"]), missing


def cut(ffmpeg: str, recording: Path, start: float, duration: float, out: Path):
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
           "-ss", f"{start:.3f}", "-i", str(recording), "-t", f"{duration:.3f}",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
           "-c:a", "aac", "-b:a", "192k", str(out)]
    subprocess.run(cmd, check=True)


def update_labels(rows: list[dict], drop_standins: bool):
    existing, header = [], LABEL_COLUMNS
    if LABELS_PATH.exists():
        with open(LABELS_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            header = list(reader.fieldnames or LABEL_COLUMNS)
            existing = list(reader)
    standins = [r for r in existing if r.get("video_path", "").replace("\\", "/").startswith("external_data/")]
    if standins and not drop_standins:
        sys.exit(f"{LABELS_PATH} still has {len(standins)} courtroom stand-in rows (video_path under external_data/).\n"
                 "Mixing them with real volunteer clips would corrupt training. Re-run with --drop-standins "
                 "to remove them, or edit labels.csv yourself.")
    if drop_standins:
        existing = [r for r in existing if r not in standins]
    for col in LABEL_COLUMNS:
        if col not in header:
            header.append(col)
    new_ids = {r["clip_id"] for r in rows}
    merged = [r for r in existing if r["clip_id"] not in new_ids] + rows
    with open(LABELS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header, restval="")
        writer.writeheader()
        writer.writerows(merged)
    print(f"Updated {LABELS_PATH}: {len(rows)} rows for this volunteer, {len(merged)} rows in total"
          + (f", {len(standins)} stand-in rows removed" if drop_standins and standins else ""))


def run_report(volunteer: int):
    """Updates docs/VOLUNTEER_DATA_FINDINGS.md with this session. The report
    needs the ML packages, so it runs in the project venv rather than in
    whatever Python started this stdlib-only script."""
    venv_python = PROJECT_ROOT / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    report = PROJECT_ROOT / "src" / "session_report.py"
    manual = f"venv\\Scripts\\python.exe src\\session_report.py --volunteer {volunteer}"
    if not venv_python.exists():
        print(f"\n[Note] Project venv not found, so the findings report wasn't updated. Run:  {manual}")
        return
    print("\nUpdating the findings report (feature extraction takes a few minutes on CPU)...", flush=True)
    if subprocess.run([str(venv_python), str(report), "--volunteer", str(volunteer)], cwd=PROJECT_ROOT).returncode:
        print(f"[Warning] The findings report failed; the clips are fine. Rerun it with:  {manual}")


def main():
    parser = argparse.ArgumentParser(description="Cut a session recording into per-question clips.")
    parser.add_argument("--volunteer", type=int, required=True, help="volunteer number, e.g. 1 for volunteer_01")
    parser.add_argument("--recording", type=Path, required=True, help="the full session recording (video with audio)")
    parser.add_argument("--offset", type=float, default=0.0, help="seconds to add to every cut (default 0)")
    parser.add_argument("--session", help="session id from the log (default: the latest session)")
    parser.add_argument("--dry-run", action="store_true", help="show the cuts without running ffmpeg")
    parser.add_argument("--update-labels", action="store_true", help="merge the rows into data/labels.csv")
    parser.add_argument("--drop-standins", action="store_true",
                        help="with --update-labels: remove the courtroom stand-in rows from labels.csv")
    parser.add_argument("--no-report", action="store_true",
                        help="don't update docs/VOLUNTEER_DATA_FINDINGS.md after cutting")
    args = parser.parse_args()

    volunteer_id = f"volunteer_{args.volunteer:02d}"
    folder = Path(VOLUNTEER_RAW_DIR) / volunteer_id
    log_path = folder / "session_log.jsonl"
    if not log_path.exists():
        sys.exit(f"No session log at {log_path}")
    if not args.dry_run and not args.recording.exists():
        sys.exit(f"Recording not found: {args.recording}")
    ffmpeg = shutil.which("ffmpeg")
    if not args.dry_run and not ffmpeg:
        sys.exit("ffmpeg not found. Install it with:  winget install ffmpeg")

    rec_start, clips, missing = collect_clips(read_session(log_path, args.session))
    rows, problems = [], []
    print(f"{'clip':<22}{'start':>10}{'end':>10}{'length':>9}")
    for c in clips:
        start = c["start_t"] - rec_start + args.offset
        end = c["end_t"] - rec_start + args.offset + END_PAD_S
        name = f"{c['condition']}_q{c['question_num']}"
        clip_id = f"v{args.volunteer:02d}_{name}"
        length = end - start
        flag = ""
        if start < 0:
            flag = "  <- starts before the recording; skipped"
            problems.append(clip_id)
        elif not MIN_S <= length <= MAX_S:
            flag = "  <- unusual length, check it"
        print(f"{clip_id:<22}{start:>9.2f}s{end:>9.2f}s{length:>8.1f}s{flag}")
        if start < 0:
            continue

        out = folder / f"{name}.mp4"
        if not args.dry_run:
            cut(ffmpeg, args.recording, start, length, out)
        rows.append({
            "clip_id": clip_id, "volunteer_id": volunteer_id, "condition": c["condition"],
            "question_num": c["question_num"], "question_type": c["question_type"],
            "label": 1 if c["condition"] == "assisted" else 0,
            "video_path": out.relative_to(PROJECT_ROOT).as_posix(), "audio_path": "",
            "question_end_time": "0.0",
        })

    for p in missing:
        print(f"[Missing] {p['condition']} Q{p['question_num']}: no complete question-end/answer-end pair in the log")
    if args.dry_run:
        print("\nDry run: no clips written.")
        return

    rows_path = folder / "labels_rows.csv"
    with open(rows_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LABEL_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n{len(rows)} clips written to {folder}")
    print(f"Label rows saved to {rows_path}")
    if args.update_labels:
        update_labels(rows, args.drop_standins)
    else:
        print("Add them to data/labels.csv with --update-labels, or copy them in by hand.")
    # Runs even when clips are missing: the report flags the gaps.
    if not args.no_report:
        run_report(args.volunteer)
    if problems or missing:
        sys.exit(1)


if __name__ == "__main__":
    main()
