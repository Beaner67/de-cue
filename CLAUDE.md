# CLAUDE.md

@AGENTS.md

The hard rules, conventions and commands above apply. This file adds what
AGENTS.md doesn't cover: the Windows setup, the assistant tool, and how
volunteer sessions are checked.

## Environment

- Windows. Run `src/` scripts with the project venv (Python 3.12):
  `venv\Scripts\python.exe src\<script>.py` from the project root. The
  system `python` is 3.9 and lacks the pinned ML packages.
- `assistant_tool/server.py` and `make_clips.py` are stdlib-only and must
  keep working on Python 3.9: keep `from __future__ import annotations` and
  avoid 3.10+ syntax at runtime (`match`, `X | Y` outside annotations).
- Work happens on the `assistant-tool` branch; `main` is the last merged
  state.

## Assistant tool (Subsystem A)

`assistant_tool/` is the Wizard-of-Oz assistant used in the assisted round.
Read [assistant_tool/README.md](assistant_tool/README.md) before changing it.

```powershell
python assistant_tool\server.py --tunnel   # control panel: http://127.0.0.1:8766/
python assistant_tool\make_clips.py --volunteer 2 --recording "data\raw\volunteer_02\volunteer_02.mp4" --dry-run
python assistant_tool\make_clips.py --volunteer 2 --recording "data\raw\volunteer_02\volunteer_02.mp4" --update-labels
```

- Each session writes `data/raw/volunteer_XX/session_log.jsonl`. The control
  panel defaults to the first volunteer number with no session, so each
  volunteer gets their own folder.
- Odd volunteers do unassisted (Set A) first, even ones assisted first.
  Questions within a round follow a Williams order per volunteer pair, and
  answers appear after a per-difficulty delay (easy 0.5 s, medium 1.25 s,
  hard 2.0 s), with equal mean delay in both sets.
- After a **Back**, `make_clips.py` uses the last marks for a question. A
  redone round is therefore clipped from the redo.
- `answers.json` is the general (non-technical) question track, and
  `answers_technical.json` is the earlier technical one. Answers are kept to
  50 to 80 words so they fit the 380×480 volunteer window without scrolling.
- Port 18765 is taken on this machine; use other ports (e.g. 28765/28766)
  for test servers. Test with volunteer number 99 and delete its folder
  afterwards. Never start a test session in a real volunteer's folder.
- UI changes: control.html and volunteer.html follow the Figma frames in
  `assistant_tool/FIGMA_HANDOFF.md`. Its "Do not change" list (key handling,
  timestamps, element IDs) is behaviour the timing data depends on.

## Checking a new volunteer session

Before labelling a session, check:

1. **Audio is present.** `ffmpeg -i <recording> -map 0:a -af volumedetect -f null -`.
   A max volume around −91 dB means OBS recorded silence (this has happened),
   and the latency and linguistic features can't be computed.
2. **The recording lines up with the R press.** The video's duration should
   about match the span from `recording_start` to `session_end` in the log,
   plus the time until OBS was stopped.
3. **The log is complete.** Every planned question needs a `question_end`
   and an `answer_end`. Look for redone rounds (`back` events) and confirm
   with the researcher which pass is the valid one.
4. **Only the volunteer's voice is recorded.** OBS should capture the
   browser's audio only (Application Audio Capture), not the researcher's mic.

`data/labels.csv` now holds real volunteer rows; the courtroom stand-ins were
removed with `--drop-standins`. `data/raw/volunteer_01` is a pilot test
session and is deliberately not in labels.csv.

## Feature extraction notes

- `extract_latency.py` only counts speech within 30 dB of the clip's loud
  level, and the answer starts at the first 0.3 s run of speech, so breaths
  and faint noise don't set `response_delay` to about 0.
- `extract_linguistic.py` uses Whisper `small`; `base` dropped fillers and
  misheard accented speech.
- Changing either one means rerunning Stage 1
  (`pretrain_calibration.py`) before any Stage 2 numbers are compared.
- `saccade_rate` is still unvalidated on webcam clips and may be inflated
  for volunteers wearing glasses; treat it with caution until
  `SACCADE_VELOCITY_THRESHOLD` is checked.
