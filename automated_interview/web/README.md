# Automatic interview web app

The volunteer-facing page for **automatic** sessions: no researcher on a call.
The page presents each question (on-screen text, read aloud by the browser's
voice), records the webcam and microphone in the browser, and shows the
Wizard-of-Oz assistant in the assisted round, with the same delays and
word-by-word streaming as `assistant_tool/volunteer.html`.

**The video never reaches this app.** The browser uploads it in 4-second
chunks straight to the researcher's laptop, through the Cloudflare tunnel that
`automated_interview/remote_session.py` opens. The database (Neon Postgres) holds
only the session plan and timing events, about 20 KB per session. This keeps
the promise in the consent form that recordings are stored only locally.

```
volunteer's browser ──timings──▶ this app (laptop, or Vercel) ──▶ .devdata/db.json (or Neon)
        │
        └──── webcam video (chunks) ──▶ Cloudflare tunnel ──▶ researcher's laptop
                                                              data/raw/volunteer_XX/
```

## Files

Paths are relative to `automated_interview/web/`.

| Path | What it does |
|---|---|
| `public/index.html` | The interview page (setup check, two rounds, upload) |
| `api/session.js` | `GET /api/session?s=<token>`: the volunteer's plan and upload address |
| `api/events.js` | `POST /api/events?s=<token>`: timing events, stored once each |
| `api/admin.js` | Researcher-only (admin key): create sessions, read events, delete an abandoned session |
| `lib/db.js` | Neon when `DATABASE_URL` is set, else a local JSON file (`.devdata/db.json`) |
| `dev-server.mjs` | Local stand-in for Vercel: `npm run dev` |
| `../remote_session.py` | Runs a session: starts this app, the upload receiver and the tunnels |
| `../tools/make_question_audio.py` | Pre-records the questions and instructions into `public/audio/` |

## Running a session (local only)

The laptop has to be on during every session anyway (it receives the video),
so sessions run this app on the laptop too. From the project root:

```powershell
venv\Scripts\python.exe automated_interview\remote_session.py --local
venv\Scripts\python.exe automated_interview\remote_session.py --local --volunteer 10   # choose the number
```

This starts `dev-server.mjs` (with `automated_interview/web/` as its working
directory) with a random admin key, opens Cloudflare quick tunnels to it and
to the upload receiver, and prints the volunteer's link. Without
`--volunteer` it uses the lowest volunteer number with no session and prints
it, e.g. `Volunteer number: 10 (odd: unassisted round first)`. Timings are
stored in `automated_interview/web/.devdata/db.json` (gitignored) and in the
volunteer's folder. Nothing needs deploying; the link changes every session.
See "Automatic sessions" in `assistant_tool/README.md` for the full
procedure.

**`.devdata/db.json` holds the real sessions' timings. Never delete it.**
Writes to it go to a temporary file that is then renamed over it, so a crash
can't leave it half-written.

### When a volunteer quits partway

If the volunteer closes or reloads the page after **Begin interview** and
before the last answer, the page sends a beacon to the receiver's `/abort`
route (`navigator.sendBeacon` on `pagehide`). A beacon can't set headers, so it
authenticates like every receiver route: the receiver key and session id in
the query string. `remote_session.py` also treats 15 minutes without any
chunk or event after the interview began (60 minutes before it began) as
quitting. Either way it deletes everything of the session: its record and
events (`POST /api/admin?action=delete&id=<id>`) and
`data/raw/volunteer_XX/`, so the number is free again. It never does this
once `session_end` has arrived, or on Ctrl+C.

| Variable | Default | Effect |
|---|---|---|
| `DECUE_IDLE_TIMEOUT_S` | 900 | Silence after the interview began that counts as quitting |
| `DECUE_PRESTART_TIMEOUT_S` | 3600 | Time allowed before the interview begins |
| `DECUE_LOCAL_APP_PORT` | 3000 | Port of this app on the laptop |
| `DECUE_RECEIVER_PORT` | 8767 | Port of the upload receiver |

## Deploy to Vercel (not used)

Sessions run locally only, and there is no deployment. This is kept for
reference. Deleting an abandoned session is implemented only for the local
file store; with Neon the `delete` action answers "not supported in cloud
mode", and the session has to be deleted in the Neon console.

1. **Create the Vercel project.** From the project root:
   ```powershell
   cd automated_interview\web
   npm install
   npx vercel login
   npx vercel link        # create a new project, e.g. "decue-interview"
   ```
   If you deploy from GitHub instead, set the project's **Root Directory** to
   `automated_interview/web`.
2. **Add the database.** In the Vercel dashboard, open the project, then
   **Storage → Create Database → Neon (Postgres)**, and connect it to the
   project. This adds `DATABASE_URL` automatically. The free plan is plenty.
3. **Add the admin key.** In **Settings → Environment Variables**, add
   `ADMIN_KEY` with the value of `admin_key` in
   `automated_interview/remote_config.json` (that file is gitignored, never
   commit it).
4. **Deploy:**
   ```powershell
   npx vercel --prod
   ```
5. Put the production URL (e.g. `https://decue-interview.vercel.app`) into
   `app_url` in `automated_interview/remote_config.json`, and run
   `remote_session.py` without `--local`.

The tables are created automatically the first time `remote_session.py` runs.

## Testing locally

Test as volunteer 99, on ports a live session never uses, so a test can run
while a real session is going. First **park the real `.devdata`** (move it out
of the project, and note its size and SHA256), because it holds real session
timings. From the project root:

```powershell
Move-Item automated_interview\web\.devdata <somewhere outside the project>\devdata-keep
$env:DECUE_LOCAL_APP_PORT = "28766"; $env:DECUE_RECEIVER_PORT = "28767"
# optional, to try the wipe paths quickly:
$env:DECUE_IDLE_TIMEOUT_S = "20"; $env:DECUE_PRESTART_TIMEOUT_S = "30"
venv\Scripts\python.exe automated_interview\remote_session.py --volunteer 99 --local --no-tunnel --no-clips
```

Open the printed link in Chrome. Afterwards delete `data/raw/volunteer_99/`
and the test `automated_interview/web/.devdata/`, move the real `.devdata`
back, and check that its size and SHA256 are unchanged.
