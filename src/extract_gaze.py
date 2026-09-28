"""
extract_gaze.py

Extracts gaze/fixation features from a video clip using MediaPipe FaceMesh.

Feature group (per proposal Section 4.3.3):
    - fixation_stability : how steady the eye position stays (lower variance = more fixed gaze)
    - saccade_rate       : rapid eye-movement events per second
    - offcam_deviation   : mean displacement of gaze from the clip's dominant (median) gaze position
    - blink_rate         : blinks per minute

Gaze coordinate system:
    The iris centre is expressed RELATIVE TO ITS OWN EYE: its offset from the
    midpoint of the two eye corners, projected onto the eye axis (horizontal)
    and its perpendicular (vertical), divided by the eye width. Units are
    "eye-widths". This cancels head translation, distance from the camera and
    video resolution — the earlier version used absolute frame pixels, so any
    head movement showed up as "gaze" movement and features scaled with the
    video resolution.

Usage:
    from extract_gaze import extract_gaze_features
    features = extract_gaze_features("data/raw/volunteer_01/assisted_q1.mp4")
"""

import cv2
import math
import numpy as np
import mediapipe as mp

from baseline_utils import zscore_dict

mp_face_mesh = mp.solutions.face_mesh

# MediaPipe FaceMesh landmark indices (refine_landmarks=True required).
# Pairing verified empirically: iris 468 sits in the eye bounded by corners
# 33/133, iris 473 in the eye bounded by 362/263. Both corner pairs are
# ordered image-left -> image-right, so horizontal offsets share a sign.
EYES = [
    {"iris": 468, "corners": (33, 133), "lids": (159, 145)},
    {"iris": 473, "corners": (362, 263), "lids": (386, 374)},
]

# Saccade = eye-relative iris velocity above this many eye-widths per second.
# A fixed threshold (instead of the clip's own 90th percentile) is required:
# a per-clip percentile flags ~10% of frames by construction, which made
# saccade_rate ~= fps / 10 for every clip regardless of behaviour.
# Chosen from 8 random Real-life Trial *Train* clips (pooled eye-relative
# velocity: median 0.22, p95 1.17, p99 3.42 eye-widths/s): 1.5 is ~7x the
# median landmark jitter and flags ~3% of frames. Re-check this against the
# pooled distribution once volunteer webcam clips exist (close-range webcam
# video should be less noisy than courtroom footage).
SACCADE_VELOCITY_THRESHOLD = 1.5

GAZE_KEYS = ["fixation_stability", "saccade_rate", "offcam_deviation", "blink_rate"]


def _nan_features() -> dict:
    return {key: float("nan") for key in GAZE_KEYS}


def _eye_relative_iris(landmarks, width: float, height: float, eye: dict) -> tuple:
    """Iris offset from the eye-corner midpoint, in eye-widths, on (along, across) the eye axis."""
    a, b = landmarks[eye["corners"][0]], landmarks[eye["corners"][1]]
    iris = landmarks[eye["iris"]]
    ax, ay, bx, by = a.x * width, a.y * height, b.x * width, b.y * height
    eye_w = math.hypot(bx - ax, by - ay) + 1e-6
    ux, uy = (bx - ax) / eye_w, (by - ay) / eye_w  # unit vector along the eye axis (robust to head roll)
    dx = iris.x * width - (ax + bx) / 2.0
    dy = iris.y * height - (ay + by) / 2.0
    return (dx * ux + dy * uy) / eye_w, (-dx * uy + dy * ux) / eye_w


def _eye_aspect_ratio(landmarks, width: float, height: float, eye: dict) -> float:
    a, b = landmarks[eye["corners"][0]], landmarks[eye["corners"][1]]
    top, bottom = landmarks[eye["lids"][0]], landmarks[eye["lids"][1]]
    vert = math.hypot((top.x - bottom.x) * width, (top.y - bottom.y) * height)
    horiz = math.hypot((a.x - b.x) * width, (a.y - b.y) * height) + 1e-6
    return vert / horiz


def track_eyes(video_path: str) -> dict:
    """
    Runs FaceMesh over the video. Returns per-tracked-frame arrays:
        frame_idx (int), gaze_h, gaze_v (eye-widths), ear, plus fps.
    Frames where no face is found are simply absent, so frame_idx has gaps.
    """
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1920.0
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1080.0

    frame_idx, gaze_h, gaze_v, ears = [], [], [], []
    with mp_face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as face_mesh:
        i = -1
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                break
            i += 1
            results = face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if not results.multi_face_landmarks:
                continue
            landmarks = results.multi_face_landmarks[0].landmark
            offsets = [_eye_relative_iris(landmarks, width, height, eye) for eye in EYES]
            frame_idx.append(i)
            gaze_h.append(np.mean([o[0] for o in offsets]))
            gaze_v.append(np.mean([o[1] for o in offsets]))
            ears.append(np.mean([_eye_aspect_ratio(landmarks, width, height, eye) for eye in EYES]))
    cap.release()

    return {
        "fps": fps if fps > 0 else 30.0,
        "frame_idx": np.array(frame_idx, dtype=int),
        "gaze_h": np.array(gaze_h, dtype=float),
        "gaze_v": np.array(gaze_v, dtype=float),
        "ear": np.array(ears, dtype=float),
    }


def gaze_velocity(track: dict) -> tuple:
    """
    Eye-relative gaze speed (eye-widths/sec) between CONSECUTIVE tracked,
    eyes-open frames. Pairs spanning a tracking gap or a blink are excluded:
    the old code diffed across gaps (treating a 2-second dropout as one frame)
    and through blinks (where iris landmarks are unreliable), inflating saccades.
    Returns (velocity, valid_pair_mask_over_frames[1:], is_closed).
    """
    fps = track["fps"]
    ears = track["ear"]
    blink_thresh = max(0.12, float(np.median(ears) * 0.75))
    is_closed = ears < blink_thresh

    consecutive = np.diff(track["frame_idx"]) == 1
    both_open = ~is_closed[1:] & ~is_closed[:-1]
    valid = consecutive & both_open

    velocity = np.hypot(np.diff(track["gaze_h"]), np.diff(track["gaze_v"])) * fps
    return velocity, valid, is_closed


def extract_gaze_features(video_path: str, normalize: bool = True) -> dict:
    """
    Run MediaPipe FaceMesh over every frame of the video and compute
    gaze-related features.

    Args:
        video_path: path to the answer's video.
        normalize: if True (default), applies Stage 1 z-scoring via
            baseline_utils. For gaze this is currently a no-op: the Desktop
            Activities baseline is flagged domain_mismatch_warning (screen
            point-of-regard vs. eye-relative iris position), so raw values
            pass through. Set to False to always get raw values.

    Returns a dict with keys:
        fixation_stability, saccade_rate, offcam_deviation, blink_rate
    """
    track = track_eyes(video_path)
    n_frames = len(track["frame_idx"])

    if n_frames < 2:
        print(f"[Warning] {video_path}: MediaPipe tracked < 2 frames — gaze features set to NaN (will be excluded from training)")
        features = _nan_features()
        return zscore_dict("gaze", features, keys_to_normalize=GAZE_KEYS) if normalize else features

    fps = track["fps"]
    duration_sec = n_frames / fps  # tracked time only
    velocity, valid, is_closed = gaze_velocity(track)

    if valid.sum() < 2:
        print(f"[Warning] {video_path}: too few consecutive eyes-open frames — gaze features set to NaN")
        features = _nan_features()
        return zscore_dict("gaze", features, keys_to_normalize=GAZE_KEYS) if normalize else features

    # Saccades: count EVENTS (runs of above-threshold velocity), not frames,
    # so a single 3-frame saccade counts once.
    fast = (velocity > SACCADE_VELOCITY_THRESHOLD) & valid
    saccade_events = int(np.sum(fast[1:] & ~fast[:-1]) + (1 if fast[0] else 0))
    saccade_rate = saccade_events / duration_sec

    # Fixation stability: inverse of gaze variance over fixation (non-saccadic, eyes-open) frames
    fixation_mask = valid & ~fast
    h_fix = track["gaze_h"][1:][fixation_mask]
    v_fix = track["gaze_v"][1:][fixation_mask]
    if len(h_fix) > 1:
        fixation_stability = float(1.0 / (np.var(h_fix) + np.var(v_fix) + 1e-6))
    else:
        fixation_stability = float("nan")

    # Off-camera deviation: mean distance of eyes-open gaze from the clip's
    # dominant (median) gaze position. Captures time spent looking away from
    # where the person mostly looks (e.g. glancing to an overlay and back).
    open_h = track["gaze_h"][~is_closed]
    open_v = track["gaze_v"][~is_closed]
    offcam_deviation = float(np.mean(np.hypot(open_h - np.median(open_h), open_v - np.median(open_v))))

    # Blink rate: open->closed transitions lasting >= 2 consecutive frames
    blink_count = 0
    run = 0
    prev_idx = None
    for idx, closed in zip(track["frame_idx"], is_closed):
        if prev_idx is not None and idx != prev_idx + 1:
            run = 0  # tracking gap breaks a blink run
        run = run + 1 if closed else 0
        if run == 2:
            blink_count += 1
        prev_idx = idx
    blink_rate = (blink_count / duration_sec) * 60.0

    features = {
        "fixation_stability": fixation_stability,
        "saccade_rate": float(saccade_rate),
        "offcam_deviation": offcam_deviation,
        "blink_rate": float(blink_rate),
    }

    if normalize:
        features = zscore_dict("gaze", features, keys_to_normalize=GAZE_KEYS)

    return features


if __name__ == "__main__":
    import sys
    from pathlib import Path
    from paths_config import REAL_LIFE_TRIAL_DIR

    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        # Pick one real-life trial clip if available for a live test
        trial_sample = next(Path(REAL_LIFE_TRIAL_DIR).rglob("*.mp4"), None)
        path = str(trial_sample) if trial_sample else "data/raw/volunteer_01/assisted_q1.mp4"

    print(f"Testing extract_gaze on: {path}")
    print("Features (raw, unnormalized):", extract_gaze_features(path, normalize=False))
