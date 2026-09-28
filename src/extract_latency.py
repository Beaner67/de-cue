"""
extract_latency.py

Extracts response-timing features from an audio or video clip using voice
activity detection (webrtcvad).

Feature group (per proposal Section 4.3.3):
    - response_delay   : seconds between question-end and answer-start
    - pause_rate       : mid-answer pauses >= 0.3s per minute of answer
                         (a raw count grew with answer length, so it mostly
                         measured how long someone talked)
    - avg_pause_length : average length of those pauses (seconds)
    - pause_variance   : variance in pause lengths (reading tends to be more uniform)

Usage:
    from extract_latency import extract_latency_features
    features = extract_latency_features("data/raw/volunteer_01/assisted_q1.wav")
"""

import math
import os
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf
import webrtcvad

from baseline_utils import zscore_dict
from paths_config import EXTERNAL_DRIVE_ROOT  # imports paths_config to auto-check ffmpeg

LATENCY_KEYS = ["response_delay", "pause_rate", "avg_pause_length", "pause_variance"]


def _load_16k_mono_pcm(path: str) -> tuple[bytes, int]:
    """
    Loads audio from either a WAV file or video/audio container,
    converting to 16-bit mono PCM at 16000 Hz for webrtcvad.
    """
    path_str = str(path)

    # 1. Try direct reading with soundfile
    try:
        data, sr = sf.read(path_str, dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)  # downmix stereo to mono

        if sr != 16000:
            import scipy.signal
            num_samples = int(len(data) * 16000 / sr)
            data = scipy.signal.resample(data, num_samples)
            sr = 16000

        pcm_bytes = (data * 32767).clip(-32768, 32767).astype(np.int16).tobytes()
        return pcm_bytes, 16000
    except Exception:
        pass

    # 2. Fallback: extract audio stream via ffmpeg (works on MP4, MOV, MKV, etc.)
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", path_str,
        "-f", "s16le",
        "-acodec", "pcm_s16le",
        "-ac", "1",
        "-ar", "16000",
        "-vn",
        "-"
    ]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        pcm_bytes, _ = proc.communicate()
        if pcm_bytes:
            return pcm_bytes, 16000
    except Exception as e:
        print(f"[Warning] Failed to extract audio with ffmpeg from {path}: {e}")

    # 3. Last fallback: standard wave module — only usable if it is already
    # 16-bit mono at a VAD-supported rate; otherwise every chunk would fail
    # VAD and silently read as "no speech".
    try:
        with wave.open(path_str, "rb") as wf:
            if wf.getnchannels() == 1 and wf.getsampwidth() == 2 and wf.getframerate() in (8000, 16000, 32000, 48000):
                return wf.readframes(wf.getnframes()), wf.getframerate()
    except Exception:
        pass
    return b"", 16000


def extract_latency_features(audio_path: str, question_end_time: Optional[float] = None, normalize: bool = True) -> dict:
    """
    Run VAD over the audio to find speech segments, then compute latency features.

    Args:
        audio_path: path to audio (WAV) or video clip of the answer
        question_end_time: timestamp (seconds, from recording start) when the
            question ended. Pass 0.0 if the clip is already trimmed to start
            at the end of the question (what the session protocol does).
            Pass None when the timestamp is unavailable — response_delay is
            then NaN rather than a meaningless value.
        normalize: if True (default), returns z-scored features using the
            Stage 1 population baseline (Svarah) from models/baseline_stats.json.
            Set to False when pretrain_calibration.py computes the baseline.

    Returns a dict with keys:
        response_delay, pause_rate, avg_pause_length, pause_variance

    Extraction failures (unreadable audio, no speech at all) return NaN for
    every feature so the clip is excluded from training, instead of zeros
    that look like a real, perfectly fluent answer.
    """
    pcm_bytes, sample_rate = _load_16k_mono_pcm(audio_path)

    frame_duration_ms = 30
    frame_sec = frame_duration_ms / 1000.0
    bytes_per_frame = int(sample_rate * frame_sec * 2)  # 960 bytes per 30ms at 16 kHz

    speech_flags = []
    if pcm_bytes:
        vad = webrtcvad.Vad(2)  # aggressiveness 0-3; 2 is robust for room audio
        for offset in range(0, len(pcm_bytes) - bytes_per_frame + 1, bytes_per_frame):
            chunk = pcm_bytes[offset : offset + bytes_per_frame]
            try:
                is_speech = vad.is_speech(chunk, sample_rate)
            except Exception:
                is_speech = False
            speech_flags.append(is_speech)

    if question_end_time is None:
        question_end_frame = 0
    else:
        question_end_frame = max(0, int(question_end_time / frame_sec))

    speech_indices = [i for i, flag in enumerate(speech_flags) if flag and i >= question_end_frame]

    if not speech_indices:
        print(f"[Warning] {audio_path}: no readable audio or no speech detected — latency features set to NaN")
        features = {key: float("nan") for key in LATENCY_KEYS}
        return zscore_dict("latency", features, keys_to_normalize=LATENCY_KEYS) if normalize else features

    first_speech_idx = speech_indices[0]
    last_speech_idx = speech_indices[-1]

    # 1. response_delay: seconds of silence between question end and first speech
    if question_end_time is None:
        response_delay = float("nan")
    else:
        response_delay = float((first_speech_idx - question_end_frame) * frame_sec)

    # 2. Mid-answer pauses: silence runs >= 300 ms between first and last speech
    pause_lengths = []
    current_pause_frames = 0
    for flag in speech_flags[first_speech_idx : last_speech_idx + 1]:
        if not flag:
            current_pause_frames += 1
        else:
            if current_pause_frames * frame_sec >= 0.30:
                pause_lengths.append(current_pause_frames * frame_sec)
            current_pause_frames = 0

    answer_minutes = (last_speech_idx - first_speech_idx + 1) * frame_sec / 60.0
    pause_rate = len(pause_lengths) / answer_minutes
    avg_pause_length = float(np.mean(pause_lengths)) if pause_lengths else 0.0
    pause_variance = float(np.var(pause_lengths)) if len(pause_lengths) > 1 else 0.0

    features = {
        "response_delay": response_delay,
        "pause_rate": float(pause_rate),
        "avg_pause_length": avg_pause_length,
        "pause_variance": pause_variance,
    }

    if normalize:
        features = zscore_dict("latency", features, keys_to_normalize=LATENCY_KEYS)

    return features


if __name__ == "__main__":
    import sys
    # Test on default or passed audio
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        # Pick one Svarah file if available
        from paths_config import SVARAH_DIR
        svarah_sample = next(Path(SVARAH_DIR).glob("*.wav"), None)
        path = str(svarah_sample) if svarah_sample else "data/raw/volunteer_01/assisted_q1.wav"

    print(f"Testing extract_latency on: {path}")
    print("Features (raw, unnormalized):", extract_latency_features(path, normalize=False))
