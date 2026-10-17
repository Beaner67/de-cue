# CLAUDE.md

@AGENTS.md

The hard rules, conventions and commands above apply. This file adds what
AGENTS.md doesn't cover: the Windows setup, the assistant tool, and how
volunteer sessions are checked.

## Environment

- Windows. Run `src/` scripts with the project venv (Python 3.12):
  `venv\Scripts\python.exe src\<script>.py` from the project root. The
  system `python` is 3.9 and lacks the pinned ML packages.
- `assistant_tool/server.py`, `make_clips.py` and
  `automated_interview/remote_session.py` are stdlib-only and must keep
  working on Python 3.9: keep `from __future__ import annotations` and avoid
  3.10+ syntax at runtime (`match`, `X | Y` outside annotations).
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
  panel defaults to the first volunteer number with no session
  (`server.first_free_volunteer_num()`: no `session_start` in the log and no
  `data/raw/volunteer_XX/` folder at all; `_archive/` and `_earlier_tests/`
  never count), so each volunteer gets their own folder. Automatic sessions
  use the same function.
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

## Automatic sessions (web app)

Everything for automatic sessions is in `automated_interview/`:
`remote_session.py`, its gitignored `remote_config.json` (admin key: never
print it), `tools/make_question_audio.py` and the web app in `web/` (Neon
Postgres via `DATABASE_URL` when deployed on Vercel, admin routes behind
`ADMIN_KEY`). `server.py`, `answers.json` and `make_clips.py` stay in
`assistant_tool/` because the live tool shares them; paths come from
`ASSISTANT_TOOL_DIR`, `AUTOMATED_INTERVIEW_DIR` and `WEB_APP_DIR` in
`src/paths_config.py`. Sessions run locally only (there is no Vercel
deployment):

```powershell
venv\Scripts\python.exe automated_interview\remote_session.py --local                # next free number
venv\Scripts\python.exe automated_interview\remote_session.py --local --volunteer 10
venv\Scripts\python.exe automated_interview\remote_session.py --local --volunteer 10 --finalize
```

It starts `automated_interview/web/dev-server.mjs` on the laptop (cwd `web/`,
because `lib/db.js` keeps its store in `<cwd>/.devdata/`) with a random admin
key, opens Cloudflare tunnels to it and to an upload receiver, and finalizes
into the same `volunteer_XX.mp4` + `session_log.jsonl` that `make_clips.py`
expects. The auto mode classifier may block starting tunnels; the user has
asked for them for remote volunteers.

- **Volunteer number.** Without `--volunteer` it takes
  `server.first_free_volunteer_num()` and prints it, e.g. `Volunteer number:
  10 (odd: unassisted round first)`. `--finalize` always needs `--volunteer`.
- **Abandoned sessions are wiped** (the user's choice; the consent form
  promises deletion on withdrawal). The session counts as abandoned when the
  page's `pagehide` beacon (`POST /abort` on the receiver, sent only between
  `session_start` and `session_end`) arrives, or when no chunk or event
  arrives for `DECUE_IDLE_TIMEOUT_S` (900 s) after the interview began, or for
  `DECUE_PRESTART_TIMEOUT_S` (3600 s) before. The script then closes the
  receiver, deletes the session from the store (`/api/admin?action=delete`,
  file store only), deletes `data/raw/volunteer_XX/`, and exits 0; the number
  is free again. It never wipes after `session_end` has arrived (a stalled
  upload prints the `--finalize` advice instead) or on Ctrl+C. Writes are
  refused under the receiver's lock once it is closed, so a late chunk can't
  recreate the folder. A connection outage longer than the idle timeout looks
  like quitting.
- **Ports.** `DECUE_LOCAL_APP_PORT` (3000) and `DECUE_RECEIVER_PORT` (8767)
  move them, so a test never takes a live session's ports; the script refuses
  to start on a busy port.

- **Video must never be stored by the web app or the database.** The consent
  form promises local-only storage; the browser uploads chunks straight to
  the laptop. Only plans and timing events go to Neon.
- The page's events use the same schema as `server.py`'s log, plus
  `protocol: "automatic"` in `session_start` and extra informational events
  (`question_start`, `round_start`, `recording_stop`, `voice_muted`,
  `instructions_skipped`). Keep `make_clips.py` and `session_report.py`
  working with both protocols.
- **Skip.** While an instruction is read aloud (welcome, setup, round
  briefings), Replay becomes "Skip instructions", enabled after 5 s
  (`SKIP_AFTER_S`, no countdown shown). Questions can't be skipped:
  `question_end` must stay the moment the question finished playing.
  `instructions_skipped {instruction, heard_s}` is logged on each skip during
  the interview; skips on the welcome and setup screens are logged right
  after `recording_start`, like `voice_muted`.
- **Mute.** The volunteer can mute the voice (welcome, setup and interview
  screens). It only sets the volume to 0: recordings still play, so
  `question_end` and the narration gating are unchanged. The setup's test
  voice ignores the mute. `voice_muted {muted}` is logged right after
  `recording_start` if already muted, and on each toggle until `session_end`.
- The plan comes from `server.build_plan()`; don't duplicate the
  counterbalancing in JavaScript.
- Test as volunteer 99 on other ports, e.g. `$env:DECUE_LOCAL_APP_PORT=28766;
  $env:DECUE_RECEIVER_PORT=28767` then `remote_session.py --volunteer 99
  --local --no-tunnel --no-clips` (short `DECUE_IDLE_TIMEOUT_S` /
  `DECUE_PRESTART_TIMEOUT_S` for the wipe paths). **`automated_interview/web/.devdata/db.json`
  holds real session timings: never delete it.** Before testing, park it
  outside the project (move the `.devdata` folder away), and afterwards delete
  the test `.devdata` and `data/raw/volunteer_99/`, restore the real one and
  check its size and SHA256 are unchanged.

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

`make_clips.py` (unless `--no-report`) runs `src/session_report.py`, which
does checks 1–3 automatically, caches `session_check.json` and
`trial_features.csv` in the volunteer's folder, and regenerates the part of
`docs/VOLUNTEER_DATA_FINDINGS.md` above its END marker. Below the marker is
hand-written interpretation, which the script keeps. Check 4 still needs a
listen.

`data/labels.csv` now holds real volunteer rows; the courtroom stand-ins were
removed with `--drop-standins`. `data/raw/volunteer_01` is a pilot test
session and is deliberately not in labels.csv.

`data/volunteer_exclusions.csv` excludes volunteer_08, who answered the
assisted round without looking at the assistant (reported by the
researcher, 2026-10-13). Their labels match the session log; the
manipulation failed: 0% of the suggestions' three-word phrases reused,
against at least 18% for every other volunteer's assisted answers. On
2026-10-17 the researcher decided to exclude volunteer_08 entirely: the
thesis reports only runs without them, and no `--include-excluded` run.
Their rows stay in labels.csv and their raw folder stays on disk.

## Feature extraction notes

- `extract_latency.py` only counts speech within 30 dB of the clip's loud
  level, and the answer starts at the first 0.3 s run of speech, so breaths
  and faint noise don't set `response_delay` to about 0.
- `extract_linguistic.py` uses Whisper `small`; `base` dropped fillers and
  misheard accented speech.
- Changing either one means rerunning Stage 1
  (`pretrain_calibration.py`) before any Stage 2 numbers are compared.
- Remote volunteers' call video sometimes freezes while audio continues.
  `session_report.py` detects freezes (ffmpeg `freezedetect`) and lists
  them per clip. A clip whose gaze is invalid goes in
  `data/gaze_exclusions.csv`; `apply_gaze_exclusions()` sets its gaze
  features to NaN in `build_features.py` and the report, so training drops
  the whole clip. Current rule: exclude only clips frozen for (almost) all
  of their length; partly frozen clips are kept and stated as a limitation.
- `saccade_rate` is still unvalidated on webcam clips and may be inflated
  for volunteers wearing glasses; treat it with caution until
  `SACCADE_VELOCITY_THRESHOLD` is checked.
