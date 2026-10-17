"""
extract_linguistic.py

Extracts linguistic/fluency features from an audio clip via Whisper
transcription.

Feature group (per proposal Section 4.3.3):
    - filler_rate       : filler words ("um", "uh", "like", "you know") per 100 words
    - speaking_rate     : words per minute
    - lexical_diversity : type-token ratio (unique words / total words)
    - sentence_complexity : average words per sentence (proxy for structure)

Usage:
    from extract_linguistic import extract_linguistic_features
    features = extract_linguistic_features("data/raw/volunteer_01/assisted_q1.wav")
"""

import re

import paths_config
import torch
import whisper

from baseline_utils import zscore_dict

# Fillers are matched as whole words/phrases only (\b...\b). The previous
# substring count matched "um" inside "number"/"document", "ah" inside
# "yeah"/"that", "like" inside "likely", etc., which swamped the real signal.
# Hesitation sounds allow elongated spellings ("umm", "uhh", "hmm", "erm").
FILLER_PATTERNS = [
    r"u+m+", r"u+h+", r"a+h+", r"e+r+m*", r"h+m+",
    r"like", r"you know", r"i mean", r"sort of", r"kind of",
]
_FILLER_RE = re.compile(r"\b(?:" + "|".join(FILLER_PATTERNS) + r")\b")

# Whisper tends to drop disfluencies ("um", "uh") from its transcripts unless
# the decoding prompt contains them. This prompt biases it towards verbatim
# transcription. Stage 1 and Stage 2 must use the SAME prompt, otherwise
# filler_rate is not comparable across the two — so it lives here, in the one
# function both stages call.
VERBATIM_PROMPT = "Umm, so, uh, I mean, like, you know... hmm, let me think. Er, okay."

# "small" rather than "base": on the first pilot recordings (Indian-English speech
# over a video call) base garbled words ("Geathers" for "guitar"), which distorts
# every transcript-based feature. Like the prompt, Stage 1 and Stage 2 must use the
# same model, so changing it means rerunning pretrain_calibration.py.
WHISPER_MODEL = "small"

_model = None


def _get_model():
    """Lazy-load the Whisper model once, reused across calls."""
    global _model
    if _model is None:
        _model = whisper.load_model(WHISPER_MODEL)
    return _model


def extract_linguistic_features(audio_path: str, normalize: bool = True) -> dict:
    """
    Transcribes the audio with Whisper and computes fluency features from
    the transcript.

    Args:
        audio_path: path to the answer's audio.
        normalize: if True (default), returns z-scored features using the
            Stage 1 population baseline from models/baseline_stats.json
            (see pretrain_calibration.py). If that file doesn't exist yet,
            values pass through unchanged. Set to False to always get raw
            values — this is what pretrain_calibration.py itself uses when
            building the baseline in the first place, to avoid circularity.

    Returns a dict with keys:
        filler_rate, speaking_rate, lexical_diversity, sentence_complexity, transcript
    """
    model = _get_model()
    result = model.transcribe(
        str(audio_path),
        language="en",
        initial_prompt=VERBATIM_PROMPT,
        fp16=torch.cuda.is_available(),
    )
    text = result["text"].strip()
    segments = result.get("segments") or []
    # Speech span = first segment start to last segment end, so leading
    # silence (already captured by response_delay) doesn't deflate speaking_rate.
    duration_sec = (segments[-1]["end"] - segments[0]["start"]) if segments else 0.0

    lowered = text.lower()
    words = re.findall(r"\b\w+\b", lowered)
    word_count = len(words)

    # Filler word rate (per 100 words) — whole-word matches only
    filler_count = len(_FILLER_RE.findall(lowered))
    filler_rate = (filler_count / word_count * 100) if word_count else 0.0

    # Speaking rate (words per minute)
    speaking_rate = (word_count / duration_sec * 60) if duration_sec > 0 else 0.0

    # Lexical diversity (type-token ratio)
    lexical_diversity = (len(set(words)) / word_count) if word_count else 0.0

    # Sentence complexity (avg words per sentence)
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    sentence_complexity = (word_count / len(sentences)) if sentences else 0.0

    features = {
        "filler_rate": filler_rate,
        "speaking_rate": speaking_rate,
        "lexical_diversity": lexical_diversity,
        "sentence_complexity": sentence_complexity,
        "transcript": text,  # kept for debugging / the dashboard's per-answer breakdown screen
    }

    if normalize:
        features = zscore_dict(
            "linguistic", features,
            keys_to_normalize=["filler_rate", "speaking_rate", "lexical_diversity", "sentence_complexity"],
        )

    return features


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/volunteer_01/assisted_q1.wav"
    print(extract_linguistic_features(path))
