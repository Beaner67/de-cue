"""
session_report.py

Keeps docs/VOLUNTEER_DATA_FINDINGS.md up to date after every volunteer
session. make_clips.py runs it once a session's clips are cut; it can also be
run by hand:

    python src/session_report.py                  # report on every volunteer
    python src/session_report.py --volunteer 5    # re-check and re-extract volunteer_05 first
    python src/session_report.py --refresh        # re-check and re-extract everyone

For every data/raw/volunteer_XX folder with clips (labels_rows.csv) it caches
two files next to the clips, both gitignored with the rest of data/raw/:
    session_check.json   audio level, recording length, log completeness
    trial_features.csv   the 12 features per clip
Cached files are reused, so only a new volunteer pays for Whisper and
MediaPipe. Features come from build_features.extract_clip_features(), the
same code that builds the training table.

Everything above the END marker in the findings file is regenerated. The
sections below it are hand-written interpretation and are kept as they are.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from modeling_utils import FEATURE_COLUMNS, FEATURE_GROUPS
from paths_config import BASELINE_STATS_PATH, FINDINGS_REPORT_PATH, LABELS_PATH, VOLUNTEER_RAW_DIR

END_MARKER = "<!-- END AUTO-GENERATED: everything below this line is hand-written and kept -->"

# An OBS recording of silence peaks around -91 dB; real speech peaks near 0 dB.
SILENT_MAX_DB = -60.0
# The recording should run as long as the logged span plus the few seconds
# until OBS was stopped. Outside this window the R press probably didn't line up.
ALIGN_TOLERANCE_S = (-2.0, 30.0)
# saccade_rate is unvalidated on webcam clips and may be inflated for people
# wearing glasses, so a volunteer this far above the others' median is flagged.
SACCADE_OUTLIER_FACTOR = 2.0

GROUP_LABELS = {"gaze_only": "Gaze", "latency_only": "Latency", "linguistic_only": "Linguistic"}
# Words for "higher" / "lower" when assisted, where plain direction is unclear.
DIRECTION_WORDS = {
    "fixation_stability": ("steadier gaze", "less steady gaze"),
    "offcam_deviation": ("more off-camera", "more on-camera"),
    "blink_rate": ("more blinks", "fewer blinks"),
    "filler_rate": ("more fillers", "fewer fillers"),
    "speaking_rate": ("faster", "slower"),
    "lexical_diversity": ("more varied", "less varied"),
}


# ---------------------------------------------------------------- session checks

def _latest_session(log_path):
    """Same choice as make_clips.py without --session: the latest session in the log."""
    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    sessions = [r["session_id"] for r in records if r["event"] == "session_start"]
    return [r for r in records if r["session_id"] == sessions[-1]] if sessions else []


def _probe_recording(path):
    out = {"recording_found": path.exists(), "duration_s": None, "mean_db": None, "max_db": None}
    if not path.exists():
        return out
    ffprobe, ffmpeg = shutil.which("ffprobe"), shutil.which("ffmpeg")
    if ffprobe:
        r = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                           capture_output=True, text=True)
        try:
            out["duration_s"] = float(r.stdout.strip())
        except ValueError:
            pass
    if ffmpeg:
        r = subprocess.run([ffmpeg, "-hide_banner", "-i", str(path), "-map", "0:a", "-af", "volumedetect",
                            "-f", "null", "-"], capture_output=True, text=True, errors="replace")
        for key, name in (("mean_db", "mean_volume"), ("max_db", "max_volume")):
            m = re.search(rf"{name}: (-?[\d.]+) dB", r.stderr)
            if m:
                out[key] = float(m.group(1))
    return out


def check_session(folder):
    records = _latest_session(folder / "session_log.jsonl")
    start = next(r for r in records if r["event"] == "session_start")
    plan = start["plan"]
    rec_start = [r["t"] for r in records if r["event"] == "recording_start"]
    session_end = [r["t"] for r in records if r["event"] == "session_end"]

    # The last marks win, as in make_clips.py, so redone questions use the redo.
    question_end, answer_end, shown = {}, {}, {}
    for r in records:
        key = (r.get("condition"), r.get("question_num"))
        if r["event"] == "question_end":
            question_end[key] = r
        elif r["event"] == "answer_end":
            answer_end[key] = r
        elif r["event"] == "answer_shown":
            shown[r["answer_id"]] = r

    answers, missing = [], []
    for p in plan:
        key = (p["condition"], p["question_num"])
        if key not in question_end or key not in answer_end:
            missing.append(f"{p['condition']} q{p['question_num']}")
            continue
        s = shown.get(question_end[key].get("answer_id"))
        answers.append({"condition": p["condition"], "question_num": p["question_num"],
                        "difficulty": p.get("difficulty"),
                        "answer_s": answer_end[key]["t"] - question_end[key]["t"],
                        "shown_after_s": s["since_question_end_s"] if s else None})

    return {
        "session_id": start["session_id"],
        "date": start["t_iso"][:10],
        "first_condition": plan[0]["condition"],
        "planned": len(plan),
        "missing": missing,
        "back_presses": sum(r["event"] == "back" for r in records),
        "log_span_s": session_end[-1] - rec_start[-1] if rec_start and session_end else None,
        "delay_by_difficulty": start.get("settings", {}).get("delay_by_difficulty", {}),
        "answers": answers,
        **_probe_recording(folder / f"{folder.name}.mp4"),
    }


# ---------------------------------------------------------------- features

def extract_volunteer_features(folder):
    # Imported here so a report from cached files doesn't load Whisper and MediaPipe.
    from build_features import extract_clip_features
    labels = pd.read_csv(folder / "labels_rows.csv")
    rows = [r for r in (extract_clip_features(row) for _, row in labels.iterrows()) if r is not None]
    df = pd.DataFrame(rows)
    df.to_csv(folder / "trial_features.csv", index=False)
    return df


def load_volunteers(selected, refresh, extract):
    volunteers = []
    for folder in sorted(Path(VOLUNTEER_RAW_DIR).glob("volunteer_*")):
        if not (folder / "labels_rows.csv").exists() or not (folder / "session_log.jsonl").exists():
            continue
        redo = refresh or folder.name in selected

        check_path = folder / "session_check.json"
        if redo or not check_path.exists():
            print(f"[check] {folder.name}")
            check_path.write_text(json.dumps(check_session(folder), indent=2), encoding="utf-8")
        check = json.loads(check_path.read_text(encoding="utf-8"))

        feats_path = folder / "trial_features.csv"
        feats = None
        if extract and (redo or not feats_path.exists()):
            print(f"[features] {folder.name}: extracting (a few minutes on CPU)")
            feats = extract_volunteer_features(folder)
        elif feats_path.exists():
            feats = pd.read_csv(feats_path)
        volunteers.append({"id": folder.name, "short": "V" + folder.name[-2:], "check": check, "features": feats})
    return volunteers


# ---------------------------------------------------------------- formatting

def _num(x, nd=2, signed=False):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x:+.{nd}f}" if signed else f"{x:.{nd}f}"


def _table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def _round_order(check):
    return "Unassisted → Assisted" if check["first_condition"] == "unassisted" else "Assisted → Unassisted"


def _feature_group(feature):
    return next(GROUP_LABELS[g] for g in GROUP_LABELS if feature in FEATURE_GROUPS[g])


# ---------------------------------------------------------------- analysis

def analyse(volunteers):
    frames = [v["features"].assign(volunteer_id=v["id"]) for v in volunteers if v["features"] is not None]
    if not frames:
        return None
    feats = pd.concat(frames, ignore_index=True)
    feats["question_num"] = feats["clip_id"].str.extract(r"_q(\d+)$")[0].astype(int)
    features = [f for f in FEATURE_COLUMNS if f in feats.columns]

    # Pair each assisted answer with the same volunteer's unassisted answer to
    # the same question number, so every comparison is within one speaker.
    assisted = feats[feats["condition"] == "assisted"].set_index(["volunteer_id", "question_num"])
    unassisted = feats[feats["condition"] == "unassisted"].set_index(["volunteer_id", "question_num"])
    diff = (assisted[features] - unassisted[features]).dropna(how="all")
    diff["question_type"] = assisted.loc[diff.index, "question_type"]

    vol_diff = diff.groupby(level="volunteer_id")[features].mean()
    vol_sd = feats.groupby("volunteer_id")[features].std().replace(0, np.nan)
    return {
        "feats": feats,
        "features": features,
        "diff": diff,
        "vol_diff": vol_diff,
        "vol_ids": list(vol_diff.index),
        "effect": (vol_diff / vol_sd.loc[vol_diff.index]).mean(),
        "vol_up": (vol_diff > 0).sum(),
        "vol_down": (vol_diff < 0).sum(),
        "pairs_up": (diff[features] > 0).sum(),
        "pairs_n": diff[features].notna().sum(),
        "means": feats.groupby(["volunteer_id", "condition"])[features].mean(),
    }


def classify(res, f):
    n = len(res["vol_ids"])
    up, down = int(res["vol_up"][f]), int(res["vol_down"][f])
    words_up, words_down = DIRECTION_WORDS.get(f, ("higher", "lower"))
    if n >= 2 and up == n:
        return "consistent", f"↑ {words_up}"
    if n >= 2 and down == n:
        return "consistent", f"↓ {words_down}"
    if up > down:
        return "mostly", f"↑ {words_up} (mostly)"
    if down > up:
        return "mostly", f"↓ {words_down} (mostly)"
    return "mixed", "mixed"


def volunteer_flags(v, res, in_labels):
    c, flags = v["check"], []
    if not c["recording_found"]:
        flags.append("full recording not found")
    elif c["max_db"] is not None and c["max_db"] < SILENT_MAX_DB:
        flags.append(f"audio looks silent (max {c['max_db']:.0f} dB)")
    if c["duration_s"] is not None and c["log_span_s"] is not None:
        gap = c["duration_s"] - c["log_span_s"]
        if not ALIGN_TOLERANCE_S[0] <= gap <= ALIGN_TOLERANCE_S[1]:
            flags.append(f"recording is {gap:+.1f} s off the log; check the R press")
    if c["missing"]:
        flags.append("missing: " + ", ".join(c["missing"]))
    if c["back_presses"]:
        n = c["back_presses"]
        flags.append(f"{n} Back press{'es' if n != 1 else ''}; last marks used")
    if v["features"] is None:
        flags.append("features not extracted")
    else:
        nan = int(v["features"][[f for f in FEATURE_COLUMNS if f in v["features"].columns]].isna().sum().sum())
        if nan:
            flags.append(f"{nan} missing feature values")
    if v["id"] not in in_labels:
        flags.append("not in labels.csv")
    if res is not None and "saccade_rate" in res["features"] and len(res["vol_ids"]) >= 3 and v["id"] in res["vol_ids"]:
        per_vol = res["feats"].groupby("volunteer_id")["saccade_rate"].mean()
        others = per_vol.drop(v["id"]).median()
        if others > 0 and per_vol[v["id"]] > SACCADE_OUTLIER_FACTOR * others:
            flags.append(f"saccade_rate {per_vol[v['id']] / others:.1f}× the others (glasses?)")
    return flags


# ---------------------------------------------------------------- report

def build_report(volunteers):
    res = analyse(volunteers)
    in_labels = set(pd.read_csv(LABELS_PATH)["volunteer_id"]) if LABELS_PATH.exists() else set()
    flags = {v["id"]: volunteer_flags(v, res, in_labels) for v in volunteers}
    checks = {v["id"]: v["check"] for v in volunteers}
    dates = sorted(c["date"] for c in checks.values())
    n_clips = sum(len(v["features"]) for v in volunteers if v["features"] is not None)
    out = []

    out += [
        "# Volunteer Data Findings",
        "",
        "**Study:** De-Cue: Detecting Covert Real-Time AI Assistance in Video Interviews<br>",
        f"**Data covered:** {len(volunteers)} volunteer sessions ({dates[0]} to {dates[-1]}), {n_clips} clips<br>",
        f"**Last updated:** {datetime.now():%Y-%m-%d %H:%M}, by `src/session_report.py`",
        "",
        "> Sections 1–4 are regenerated after every session (`make_clips.py` runs the report), "
        "so edits to them are overwritten. Write interpretation in the sections after the end marker.",
        "",
        "---",
        "",
    ]

    # 1. Summary
    out += ["## 1. Summary", ""]
    flagged = {k: f for k, f in flags.items() if [x for x in f if x != "not in labels.csv"]}
    if flagged:
        out.append("- **Session checks raised flags:** " + "; ".join(
            f"V{k[-2:]}: {', '.join(f)}" for k, f in flagged.items()) + ".")
    else:
        out.append("- All sessions passed the checks: audio is present, every log is complete, "
                   "and every recording matches its log.")
    if res is not None:
        n = len(res["vol_ids"])
        kinds = {f: classify(res, f) for f in res["features"]}
        consistent = [f for f in res["features"] if kinds[f][0] == "consistent"]
        mixed = [f for f in res["features"] if kinds[f][0] == "mixed"]
        out.append(f"- **{len(consistent)} of {len(res['features'])} features changed in the same direction "
                   f"for all {n} volunteers when the assistant was used:** "
                   + (", ".join(f"`{f}` ({kinds[f][1]})" for f in consistent) or "none") + ".")
        orders = [checks[v]["first_condition"] for v in res["vol_ids"]]
        out.append(f"- Round order: {orders.count('assisted')} of {n} volunteers did the assisted round first and "
                   f"{orders.count('unassisted')} the unassisted round first. An effect that holds in both "
                   "orders is not explained by fatigue or practice.")
        if mixed:
            out.append("- **Split evenly between volunteers:** " + ", ".join(f"`{f}`" for f in mixed) + ".")
        out.append(f"- With {n} speakers and {len(res['diff'])} paired answers, these are directional "
                   "observations, not statistically tested results.")
    out += ["", "---", ""]

    # 2. Dataset
    out += ["## 2. Dataset", ""]
    out.append(_table(
        ["Volunteer", "Date", "Round order", "Clips", "In labels.csv", "Flags"],
        [[v["short"], v["check"]["date"], _round_order(v["check"]),
          len(v["features"]) if v["features"] is not None else 0,
          "yes" if v["id"] in in_labels else "no",
          "; ".join(flags[v["id"]]) or "—"] for v in volunteers]))
    out += [
        "",
        "- **Design:** within-subjects. Each volunteer answers 4 questions unassisted (Set A) and 4 with the "
        "Wizard-of-Oz assistant (Set B). Each round has 2 behavioural, 1 opinion and 1 conceptual question.",
        "- **Counterbalancing:** odd-numbered volunteers do the unassisted round first and even-numbered ones "
        "the assisted round first. Question order within a round follows a Williams design per volunteer pair.",
        "- **Clips** start at the end of the question and end at the end of the answer.",
        "", "---", "",
    ]

    # 3. Session checks
    out += ["## 3. Session Quality Checks", "", "### 3.1 Audio and recording alignment", ""]
    rows = []
    for v in volunteers:
        c = v["check"]
        gap = c["duration_s"] - c["log_span_s"] if c["duration_s"] is not None and c["log_span_s"] is not None else None
        rows.append([v["short"], f"{_num(c['mean_db'], 1)} / {_num(c['max_db'], 1)} dB",
                     f"{_num(c['duration_s'], 1)} s", f"{_num(c['log_span_s'], 1)} s", f"{_num(gap, 1, True)} s"])
    out.append(_table(["Volunteer", "Mean / max volume", "Recording length", "Log span (recording start → session end)",
                       "Difference"], rows))
    out += ["", f"A max volume below {SILENT_MAX_DB:.0f} dB would mean OBS recorded silence. The difference should "
            "be a few seconds: the time between the session ending and OBS being stopped.", ""]

    out += ["### 3.2 Log completeness", ""]
    out.append(_table(["Volunteer", "Planned questions", "Complete", "Missing", "Back presses"],
                      [[v["short"], v["check"]["planned"], v["check"]["planned"] - len(v["check"]["missing"]),
                        ", ".join(v["check"]["missing"]) or "—", v["check"]["back_presses"]] for v in volunteers]))
    out += ["", "After a Back press the clips use the last marks for each question.", ""]

    out += ["### 3.3 When the assistant's answer appeared", ""]
    configured = next((c["delay_by_difficulty"] for c in checks.values() if c["delay_by_difficulty"]), {})
    rows, overheads = [], []
    for diff_name in ("easy", "medium", "hard"):
        seen = [a["shown_after_s"] for c in checks.values() for a in c["answers"]
                if a["difficulty"] == diff_name and a["shown_after_s"] is not None]
        if not seen:
            continue
        cfg = configured.get(diff_name)
        if cfg is not None:
            overheads += [s - cfg for s in seen]
        rows.append([diff_name.capitalize(), f"{_num(cfg)} s", f"{min(seen):.2f}–{max(seen):.2f} s", len(seen)])
    out.append(_table(["Difficulty", "Configured delay", "Observed delay (range)", "Answers"], rows))
    if overheads:
        out += ["", f"Observed delays are {min(overheads):.1f}–{max(overheads):.1f} s longer than configured "
                "(client and network overhead). This matters when reading `response_delay`."]
    out.append("")

    out += ["### 3.4 Answer length", "",
            "Mean time from `question_end` to `answer_end`, over the questions in each round.", ""]
    rows = []
    for v in volunteers:
        by = {cond: [a["answer_s"] for a in v["check"]["answers"] if a["condition"] == cond]
              for cond in ("unassisted", "assisted")}
        rows.append([v["short"]] + [f"{_num(np.mean(by[cond]) if by[cond] else None, 1)} s"
                                    for cond in ("unassisted", "assisted")])
    out.append(_table(["Volunteer", "Unassisted", "Assisted"], rows))
    out.append("")

    out += ["### 3.5 Feature extraction", ""]
    gaze_raw = False
    if BASELINE_STATS_PATH.exists():
        gaze_raw = json.loads(BASELINE_STATS_PATH.read_text()).get("gaze", {}).get("domain_mismatch_warning", False)
    if res is not None:
        nan = int(res["feats"][res["features"]].isna().sum().sum())
        out.append(f"- {len(res['feats'])} clips, {len(res['features'])} features, "
                   + ("no missing values." if nan == 0 else f"{nan} missing values."))
    out.append("- Features come from `build_features.extract_clip_features()`, the same code that builds the "
               "training table, and are cached per volunteer in `data/raw/volunteer_XX/trial_features.csv`.")
    if gaze_raw:
        out.append("- Gaze features are raw values: the Stage 1 gaze baseline is flagged as a domain mismatch, so "
                   "z-scoring is skipped for that group. They can be compared within a speaker, not across speakers.")
    out += ["", "---", ""]

    # 4. Results
    out += ["## 4. Results: Assisted vs Unassisted", ""]
    if res is None:
        out += ["No features extracted yet.", ""]
    else:
        shorts = ["V" + v[-2:] for v in res["vol_ids"]]
        out += [
            "### 4.1 Method", "",
            "- Each assisted answer is paired with the same volunteer's unassisted answer to the question with "
            f"the same number ({len(res['diff'])} pairs).",
            "- The **difference** is the assisted value minus the unassisted value.",
            "- The **standardised effect** divides each volunteer's mean difference by that volunteer's own "
            "standard deviation for the feature, then averages over volunteers. This compares each person with "
            "themselves, in line with the per-speaker centring used in the model.",
            "",
            "### 4.2 Overview", "",
        ]
        rows = []
        for f in res["features"]:
            kind, label = classify(res, f)
            rows.append([_feature_group(f), f, f"**{label}**" if kind == "consistent" else label,
                         f"{int(res['vol_up'][f])} / {int(res['vol_down'][f])}",
                         f"{int(res['pairs_up'][f])} / {int(res['pairs_n'][f])}",
                         _num(res["effect"][f], 2, True)])
        out.append(_table(["Group", "Feature", "Direction when assisted", "Volunteers ↑ / ↓",
                           "Pairs where assisted was higher", "Standardised effect"], rows))
        out += ["", "**Bold** marks the features where every volunteer moved in the same direction.", ""]

        out += ["### 4.3 Mean difference per volunteer (assisted − unassisted)", ""]
        out.append(_table(["Feature"] + shorts,
                          [[f] + [_num(res["vol_diff"].loc[v, f], 2, True) for v in res["vol_ids"]]
                           for f in res["features"]]))
        out.append("")

        out += ["### 4.4 Mean feature values per volunteer and condition", ""]
        header, cols = ["Feature"], []
        for v, s in zip(res["vol_ids"], shorts):
            for cond, tag in (("unassisted", "U"), ("assisted", "A")):
                if (v, cond) in res["means"].index:
                    header.append(f"{s} {tag}")
                    cols.append((v, cond))
        out.append(_table(header, [[f] + [_num(res["means"].loc[c, f]) for c in cols] for f in res["features"]]))
        out += ["", "U = unassisted, A = assisted.", ""]

        out += ["### 4.5 By question type (pairs where assisted was higher)", ""]
        qtypes = sorted(res["diff"]["question_type"].dropna().unique())
        by_type = {q: res["diff"][res["diff"]["question_type"] == q] for q in qtypes}
        out.append(_table(["Feature"] + [f"{q.capitalize()} ({len(by_type[q])} pairs)" for q in qtypes],
                          [[f] + [f"{int((by_type[q][f] > 0).sum())}/{int(by_type[q][f].notna().sum())}"
                                  for q in qtypes] for f in res["features"]]))
        out.append("")

    out += ["---", "", END_MARKER, ""]
    return "\n".join(out)


def write_report(text):
    path = FINDINGS_REPORT_PATH
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if END_MARKER not in existing:
            sys.exit(f"{path} has no end marker, so its hand-written sections can't be told apart from the "
                     f"generated ones. Add this line above the hand-written part and rerun:\n{END_MARKER}")
        manual = existing.split(END_MARKER, 1)[1].lstrip("\n")
    else:
        manual = "## 5. Interpretation\n\n_Write the interpretation of the results here._\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n" + manual, encoding="utf-8")
    print(f"Updated {path}")


def main():
    parser = argparse.ArgumentParser(description="Regenerate the volunteer findings report.")
    parser.add_argument("--volunteer", type=int, nargs="*", default=[],
                        help="re-check and re-extract these volunteers (e.g. 5 for volunteer_05)")
    parser.add_argument("--refresh", action="store_true", help="re-check and re-extract every volunteer")
    parser.add_argument("--no-extract", action="store_true",
                        help="use only cached features; skip volunteers that have none")
    args = parser.parse_args()

    selected = {f"volunteer_{n:02d}" for n in args.volunteer}
    volunteers = load_volunteers(selected, args.refresh, extract=not args.no_extract)
    if not volunteers:
        sys.exit(f"No volunteer folders with labels_rows.csv and session_log.jsonl in {VOLUNTEER_RAW_DIR}")
    write_report(build_report(volunteers))


if __name__ == "__main__":
    main()
