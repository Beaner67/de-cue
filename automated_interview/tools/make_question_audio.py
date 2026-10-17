"""
make_question_audio.py

Pre-records every interview question, every instruction the volunteer hears
(automated_interview/web/public/instructions.json) and the setup check's
test sentence with a natural neural voice, so the automatic interview sounds
like a person and every volunteer hears exactly the same audio. The page plays these files
and marks question_end when playback ends; without them it falls back to the
browser's built-in voice.

    venv\\Scripts\\python.exe automated_interview\\tools\\make_question_audio.py
    venv\\Scripts\\python.exe automated_interview\\tools\\make_question_audio.py --voice en-IN-PrabhatNeural
    venv\\Scripts\\python.exe automated_interview\\tools\\make_question_audio.py --samples    # one sample per candidate voice

Writes automated_interview/web/public/audio/<set>_q<num>.mp3, instr_<name>.mp3
and test.mp3, plus manifest.json, which stores each file's exact text: the
page uses a file only if its text still matches, so editing a question or
instruction can't play stale audio. Rerun this script after changing any question or
instruction, then redeploy.

Uses the edge-tts package (Microsoft's neural voices, needs internet).
Leading and trailing silence is trimmed, so "playback ended" is the moment
the last word ends.
"""

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
# pyrefly: ignore [missing-import]
from paths_config import ASSISTANT_TOOL_DIR, WEB_APP_DIR  # noqa: E402  (also puts ffmpeg on PATH)

import edge_tts  # noqa: E402

ANSWERS_PATH = ASSISTANT_TOOL_DIR / "answers.json"
AUDIO_DIR = WEB_APP_DIR / "public" / "audio"
# The page shows these texts and plays their recordings: one source for both.
INSTRUCTIONS_PATH = WEB_APP_DIR / "public" / "instructions.json"
DEFAULT_VOICE = "en-IN-NeerjaNeural"
CANDIDATES = ["en-US-AndrewNeural", "en-US-AvaNeural", "en-GB-RyanNeural", "en-IN-PrabhatNeural", "en-IN-NeerjaNeural"]
TEST_SENTENCE = "Hello. This is the voice that will read the interview questions."
# Speech below this level counts as silence when trimming the ends.
SILENCE_DB = -45


def trim_and_encode(src: Path, dst: Path) -> float:
    ffmpeg = shutil.which("ffmpeg")
    trim = (f"silenceremove=start_periods=1:start_threshold={SILENCE_DB}dB,areverse,"
            f"silenceremove=start_periods=1:start_threshold={SILENCE_DB}dB,areverse")
    subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-af", trim,
                    "-ar", "24000", "-ac", "1", "-b:a", "64k", str(dst)], check=True)
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(dst)],
                         capture_output=True, text=True)
    return round(float(out.stdout.strip()), 3)


async def synthesize(text: str, voice: str, dst: Path) -> float:
    raw = dst.with_suffix(".raw.mp3")
    await edge_tts.Communicate(text, voice).save(str(raw))
    duration = trim_and_encode(raw, dst)
    raw.unlink()
    return duration


async def main():
    parser = argparse.ArgumentParser(description="Pre-record the interview questions with a neural voice.")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help=f"edge-tts voice name (default {DEFAULT_VOICE})")
    parser.add_argument("--samples", action="store_true",
                        help="write one sample of each candidate voice to automated_interview/web/public/audio/samples/ and stop")
    args = parser.parse_args()
    bank = json.loads(ANSWERS_PATH.read_text(encoding="utf-8"))

    if args.samples:
        folder = AUDIO_DIR / "samples"
        folder.mkdir(parents=True, exist_ok=True)
        text = bank["sets"]["A"][0]["question"]
        for voice in CANDIDATES:
            await synthesize(text, voice, folder / f"{voice}.mp3")
            print(f"  {folder / (voice + '.mp3')}")
        print("Listen to these, then run again with --voice <name>.")
        return

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"voice": args.voice, "source": "edge-tts", "files": {}}
    instructions = json.loads(INSTRUCTIONS_PATH.read_text(encoding="utf-8"))
    jobs = ([("test", TEST_SENTENCE)]
            + [(f"instr_{key}", text) for key, text in instructions.items()]
            + [(f"{name}_q{q['num']}", q["question"]) for name, qs in bank["sets"].items() for q in qs])
    for key, text in jobs:
        duration = await synthesize(text, args.voice, AUDIO_DIR / f"{key}.mp3")
        manifest["files"][key] = {"file": f"{key}.mp3", "text": text, "duration_s": duration}
        print(f"  {key}.mp3  {duration:5.1f} s")
    (AUDIO_DIR / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(jobs)} files and manifest.json to {AUDIO_DIR} (voice {args.voice}).")


if __name__ == "__main__":
    asyncio.run(main())
