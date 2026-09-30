# Assistant tool (Subsystem A)

A controlled stand-in for a real-time AI interview assistant, used in the
assisted round. The volunteer sees an assistant window that shows a suggested
answer shortly after each question. You, the researcher, decide when each
question ends, so the answer delay is identical for every volunteer, and every
timing is logged.

Why not a commercial tool: InterviewHelpAI refused research use in writing
(email of 28 September 2026). It also sends audio to third-party AI providers
that may train on it, with no opt-out. This tool sends only the pre-written
answers in `answers.json`. Nothing about the volunteer passes through it.

For the methods chapter, this is a **Wizard-of-Oz** design. The assistant's
behaviour is controlled by the researcher instead of a live model, with a
fixed delay (`answer_delay_s`) and streaming speed (`words_per_second`).

## Files

| File | Purpose |
|---|---|
| `server.py` | Runs the control panel (your computer only) and the volunteer's assistant page |
| `control.html` | Your control panel |
| `volunteer.html` | The assistant window the volunteer sees |
| `answers.json` | Questions, pre-written answers, delay and streaming speed |
| `make_clips.py` | Cuts the session recording into per-question clips and writes the `labels.csv` rows |

Only Python's standard library is needed, plus `cloudflared` for remote
sessions (`winget install Cloudflare.cloudflared`) and `ffmpeg` for cutting.

## Before the first session

1. **Check the answers.** Read `answers.json` and edit anything that doesn't
   sound like a plausible AI answer. They are drafts. Keep the same answers
   for every volunteer once data collection starts. The questions match Sets
   A and B in `docs/SESSION_PROTOCOL_GUIDE.md`. If you use the general
   (non-technical) protocol instead, replace the questions and answers with
   that guide's sets.
2. **Set up recording (OBS Studio recommended).** Record on your own computer:
   - Video: a *Window Capture* of the call, cropped to the volunteer's video
     tile, so only their face is in the frame. Gaze extraction assumes one face.
   - Audio: an *Application Audio Capture* of the call app only. This records
     the volunteer's voice but not your microphone, so your question never
     leaks into the start of a clip.
3. **Do a practice run with a friend** (see "Testing" below).

## Running a session

From the project root:

```powershell
python assistant_tool/server.py --tunnel
```

1. Open **http://127.0.0.1:8766/**, the control panel. After a few seconds
   it shows the public volunteer link (`https://….trycloudflare.com/?t=…`).
   The link changes every time you start the tool.
2. Send the link to the volunteer in the call chat. Ask them to open it in
   **Chrome or Edge** and click **Keep on top**. This opens a small floating
   window that stays above the call; they can place it beside or over the
   call window. The control panel shows "Volunteer page connected" once
   they've opened the link.
3. Enter the volunteer number and click **Start session**. The order follows
   the counterbalancing table: odd numbers do unassisted first, even numbers
   do assisted first.
4. Start your OBS recording, and press **R** at the same moment.
5. For each question:
   - Read the question aloud.
   - Press **Space** the moment you finish speaking. In the assisted round,
     the answer appears on the volunteer's screen 1.5 s later.
   - Press **Enter** when the volunteer finishes answering.
6. Between rounds, read the script for the next round. The volunteer's window
   switches between "Paused" and "Listening" on its own.
7. After the last answer, stop the recording, then stop the tool with Ctrl+C.

Mistakes during a session:
- **Pressed Space too early or too late:** press Space again. The last press counts.
- **Need to redo a question:** press **B** (back), then ask the question again.
- **Checking the volunteer can see answers:** press **T** before starting
  the recording. The test answer is logged but never becomes a clip.

Timings are saved to `data/raw/volunteer_XX/session_log.jsonl`. Like all of
`data/raw/`, this file is gitignored.

## Cutting the clips

```powershell
# Check the cuts first
python assistant_tool/make_clips.py --volunteer 1 --recording "D:\recordings\volunteer_01.mkv" --dry-run
# Cut the clips and add their rows to data/labels.csv
python assistant_tool/make_clips.py --volunteer 1 --recording "D:\recordings\volunteer_01.mkv" --update-labels
```

This writes `data/raw/volunteer_01/assisted_q1.mp4` etc., with
`question_end_time = 0.0` for every clip. The first time, add
`--drop-standins` to remove the 8 courtroom stand-in rows from `labels.csv`.
The script refuses to mix them with real volunteer data.

Clips are re-encoded rather than stream-copied. Stream copy can only cut at
keyframes, which would move each clip's start by up to a few seconds and
corrupt `response_delay`.

## What the timings mean

The measured `response_delay` includes the call's audio delay in both
directions (typically 0.2–0.6 s), plus any error in when you pressed R. Both
are roughly constant within one session, so they shift every clip for that
volunteer by about the same amount. The per-speaker centering in training
removes such a constant shift. They are still worth stating in the
limitations section. Use the same call app and internet connection for every
session.

For each answer, the log also records `since_question_end_s`: the time from
your Space press until the volunteer's page confirmed the answer appeared.
That is the configured delay plus one network round trip. Report its mean and
range in your methods chapter as the effective assistant latency.

## Testing

Run the tool without `--tunnel` and open both pages on your own computer.
The volunteer link is shown in the control panel. For a realistic test, run
with `--tunnel` and have a friend open the link on their own laptop over a
video call. Use volunteer number 99 for tests, then delete
`data/raw/volunteer_99/`.
