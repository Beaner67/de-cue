"""
remote_session.py

Runs one automatic (unattended) interview session through the web app in
automated_interview/web/, with the video kept on this laptop. From the
project root:

    venv\\Scripts\\python.exe automated_interview\\remote_session.py --local                  # next free number
    venv\\Scripts\\python.exe automated_interview\\remote_session.py --local --volunteer 10
    venv\\Scripts\\python.exe automated_interview\\remote_session.py --local --volunteer 10 --finalize   # after a crash

What happens:
  1. Picks the volunteer number: --volunteer N, or else the lowest number with
     no session (server.first_free_volunteer_num(), the control panel's rule).
  2. Builds the volunteer's counterbalanced plan with server.build_plan(), the
     same code the live (researcher-led) sessions use.
  3. Starts a small upload receiver on this laptop and exposes it through a
     Cloudflare quick tunnel. The volunteer's browser sends the webcam
     recording here in 4-second chunks; video never goes to Vercel or the
     database (see docs/VOLUNTEER_CONSENT_FORM.md).
  4. Registers the session in the web app and prints the volunteer's link.
     With --local the app is web/dev-server.mjs on this laptop, and the
     timings stay in automated_interview/web/.devdata/.
  5. When the volunteer finishes, joins the chunks, converts them to
     data/raw/volunteer_XX/volunteer_XX.mp4, rebuilds session_log.jsonl from
     the database (merged with the copy the page also sent here), and runs
     make_clips.py --update-labels, which also updates the findings report.

A volunteer who quits partway leaves no trace (the consent form promises
deletion on withdrawal): the session's record and events are deleted from the
app's store, data/raw/volunteer_XX/ is deleted, and the number is free again.
A session counts as abandoned when the page reports it was closed after the
interview began, or when nothing arrives for DECUE_IDLE_TIMEOUT_S (default
900 s) once the interview has begun, or for DECUE_PRESTART_TIMEOUT_S (default
3600 s) before it. Never after session_end has arrived (then only the upload
is left, and the script stops with the --finalize advice instead), and never
on Ctrl+C.

The app URL and admin key come from --app / --admin-key, the environment
variables DECUE_APP_URL / DECUE_ADMIN_KEY, or remote_config.json next to this
script (gitignored): {"app_url": "https://….vercel.app", "admin_key": "…"}.
The ports can be moved with DECUE_LOCAL_APP_PORT / DECUE_RECEIVER_PORT.

Stdlib only, like server.py, so it runs on the laptop's Python 3.9.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

TOOL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOL_DIR.parent / "src"))
# pyrefly: ignore [missing-import]
from paths_config import ASSISTANT_TOOL_DIR, PROJECT_ROOT, VOLUNTEER_RAW_DIR, WEB_APP_DIR  # noqa: E402  (also puts ffmpeg on PATH)

# server.py stays in assistant_tool/: the live tool and this script share its
# question bank and counterbalancing, which must never be duplicated.
sys.path.insert(0, str(ASSISTANT_TOOL_DIR))
# pyrefly: ignore [missing-import]
from server import (  # noqa: E402
    ANSWERS_PATH, MAX_DELAY_S, MIN_DELAY_S, build_plan, first_free_volunteer_num, has_session,
)

CONFIG_PATH = TOOL_DIR / "remote_config.json"
# Overridable so a test run never takes a live session's ports (a second
# server on Windows can otherwise share a port that is already in use).
RECEIVER_PORT = int(os.environ.get("DECUE_RECEIVER_PORT", 8767))
LOCAL_APP_PORT = int(os.environ.get("DECUE_LOCAL_APP_PORT", 3000))   # --local: web/dev-server.mjs
# A session is abandoned (and wiped) after this long with no chunk and no
# event. While recording, the page uploads a chunk every 4 s
# (recorder.start(4000)), including through the ~2 min narrated round
# briefings, so a running interview is never silent for anywhere near 15 min.
# A connection outage longer than this looks the same as quitting.
IDLE_TIMEOUT_S = float(os.environ.get("DECUE_IDLE_TIMEOUT_S", 900))
# Before the interview begins nothing is uploaded (welcome, setup check), so
# the wait for the volunteer to open the link and begin is longer.
PRESTART_TIMEOUT_S = float(os.environ.get("DECUE_PRESTART_TIMEOUT_S", 3600))
MAX_CHUNK_BYTES = 64 * 1024 * 1024
# Converted to constant 30 fps so the gaze extractor, which steps through
# frames at the file's nominal rate, sees evenly spaced frames. Browser
# recordings have a variable frame rate.
OUTPUT_FPS = 30


def now_iso(t: float) -> str:
    return datetime.fromtimestamp(t, tz=timezone.utc).isoformat(timespec="milliseconds")


# ---------------------------------------------------------------- web app API

class App:
    def __init__(self, url: str, key: str):
        self.url = url.rstrip("/")
        self.key = key

    def call(self, method: str, action: str, body: dict | None = None, **params) -> dict:
        query = "&".join([f"action={action}"] + [f"{k}={v}" for k, v in params.items()])
        req = urllib.request.Request(
            f"{self.url}/api/admin?{query}", method=method,
            data=json.dumps(body).encode("utf-8") if body is not None else None,
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")
            raise RuntimeError(f"web app {action}: HTTP {e.code} {detail}") from None


# ---------------------------------------------------------------- upload receiver

class Receiver:
    """State shared by the request handlers. One session at a time."""

    def __init__(self, folder: Path, key: str, allowed_origin: str):
        self.folder = folder
        self.chunks = folder / "chunks"
        self.chunks.mkdir(parents=True, exist_ok=True)
        self.key = key
        self.session_id = None
        self.allowed_origin = allowed_origin
        self.lock = threading.Lock()
        self.mirror: dict[int, dict] = {}
        self.mirror_path = folder / "events_mirror.json"
        if self.mirror_path.exists():
            self.mirror = {int(k): v for k, v in json.loads(self.mirror_path.read_text(encoding="utf-8")).items()}
        self.bytes = 0
        self.finished = threading.Event()
        self.expected_chunks = None
        # Abandon detection; see wait_for_outcome(). All of these change only
        # under self.lock, together with the writes into the folder.
        self.wake = threading.Event()             # finish or abort: the main loop reacts at once
        self.last_activity = time.monotonic()     # last chunk or event post
        self.started = bool(self.mirror)          # the interview has begun (a chunk or an event arrived)
        self.ended = any(e.get("event") == "session_end" for e in self.mirror.values())
        self.abort_requested = False
        # Set before a wipe. Every write checks it under the lock, so a late
        # chunk or event can never recreate the folder once it is deleted.
        self.closed = False

    def touch(self):
        with self.lock:
            self.last_activity = time.monotonic()
            self.started = True

    def add_events(self, events: list) -> bool:
        with self.lock:
            if self.closed:
                return False
            new = [e for e in events if isinstance(e, dict) and isinstance(e.get("seq"), int) and e["seq"] not in self.mirror]
            for e in new:
                self.mirror[e["seq"]] = e
            if any(e.get("event") == "session_end" for e in new):
                self.ended = True
            self.mirror_path.write_text(json.dumps(self.mirror), encoding="utf-8")
            self.last_activity = time.monotonic()
            self.started = True
        for e in new:
            print_progress(e)
        return True

    def write_chunk(self, index: int, data: bytes) -> bool:
        with self.lock:
            if self.closed:
                return False
            # Write then rename, so a chunk is never half-written; a retried
            # chunk simply replaces itself.
            part = self.chunks / f"{index:06d}.part"
            tmp = part.with_suffix(".tmp")
            tmp.write_bytes(data)
            os.replace(tmp, part)
            self.bytes += len(data)
            self.last_activity = time.monotonic()
            self.started = True
        return True

    def mark_finished(self, expected: int) -> bool:
        with self.lock:
            if self.closed:
                return False
            self.expected_chunks = expected
            self.finished.set()
        self.wake.set()
        return True

    def close_for_wipe(self) -> bool:
        """Stops accepting chunks and events, unless the interview reached
        session_end (then only the upload is left, and nothing is wiped).
        Returns True if the receiver is now closed and the session may be wiped."""
        with self.lock:
            if self.ended or self.finished.is_set():
                return False
            self.closed = True
            return True

    def check_idle(self) -> str | None:
        """Decides, atomically with the writes, whether the session has gone
        quiet for too long. Returns None while it hasn't. A chunk that comes
        in at the same moment either lands first (and resets the clock) or is
        refused after the receiver closes; it can't slip in during a wipe."""
        with self.lock:
            limit = IDLE_TIMEOUT_S if self.started else PRESTART_TIMEOUT_S
            if time.monotonic() - self.last_activity < limit:
                return None
            if self.finished.is_set():
                return "finished"
            if self.ended:
                return "stalled"
            self.closed = True
            return "idle" if self.started else "prestart"

    def request_abort(self) -> bool:
        """The page reports that the volunteer closed it mid-interview. Ignored
        once session_end has arrived, so a late abort can't wipe a finished
        interview."""
        if not self.close_for_wipe():
            return False
        self.abort_requested = True
        self.wake.set()
        return True


RECEIVER: Receiver


def print_progress(e: dict):
    stamp = datetime.fromtimestamp(e.get("t", time.time())).strftime("%H:%M:%S")
    name = e.get("event")
    if name == "session_start":
        print(f"[{stamp}] Volunteer started the interview")
    elif name == "round_start":
        print(f"[{stamp}] Round {e.get('round')} ({e.get('condition')})")
    elif name == "question_end":
        extra = " (repeated)" if e.get("remark") else ""
        extra += " [voice end not reported; timer used]" if e.get("tts_fallback") else ""
        print(f"[{stamp}]   Q{e.get('question_num')} asked{extra}")
    elif name == "answer_end":
        print(f"[{stamp}]   Q{e.get('question_num')} answered  ({RECEIVER.bytes / 1e6:.0f} MB received)")
    elif name == "recording_stop":
        print(f"[{stamp}] Recording stopped; waiting for the last chunks")
    elif name == "voice_muted":
        print(f"[{stamp}]   Volunteer {'muted' if e.get('muted') else 'unmuted'} the voice")


class Handler(BaseHTTPRequestHandler):
    server_version = "DeCueReceiver/1.0"

    def log_message(self, fmt, *args):
        pass

    def _cors(self):
        origin = self.headers.get("Origin")
        if origin and origin == RECEIVER.allowed_origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def _json(self, status: int, obj: dict):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _authorised(self, query: dict) -> bool:
        return (secrets.compare_digest(query.get("key", [""])[0], RECEIVER.key)
                and (RECEIVER.session_id is None or query.get("session", [""])[0] == RECEIVER.session_id))

    def _read(self, limit: int) -> bytes | None:
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length <= limit:
            return None
        return self.rfile.read(length)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Access-Control-Allow-Methods", "GET, POST")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.end_headers()

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/ping" and self._authorised(parse_qs(url.query)):
            return self._json(200, {"ok": True})
        self._json(403, {"error": "forbidden"})

    def do_POST(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        if not self._authorised(query):
            return self._json(403, {"error": "forbidden"})
        if url.path == "/upload":
            try:
                index = int(query.get("i", [""])[0])
            except ValueError:
                return self._json(400, {"error": "bad chunk index"})
            # Counts as activity as soon as it arrives: on a slow connection
            # one chunk can take a while to come in.
            RECEIVER.touch()
            data = self._read(MAX_CHUNK_BYTES)
            if data is None:
                return self._json(400, {"error": "empty or oversized chunk"})
            if not RECEIVER.write_chunk(index, data):
                return self._json(410, {"error": "session closed"})
            return self._json(200, {"ok": True})
        if url.path == "/events":
            data = self._read(1_000_000)
            try:
                events = json.loads(data or b"{}").get("events", [])
            except ValueError:
                return self._json(400, {"error": "bad json"})
            if not RECEIVER.add_events(events):
                return self._json(410, {"error": "session closed"})
            return self._json(200, {"ok": True})
        if url.path == "/abort":
            # Sent with navigator.sendBeacon when the page is closed mid-
            # interview. A beacon can't set headers, so it authenticates like
            # every other route here: key and session id in the query string.
            # The body is not needed.
            accepted = RECEIVER.request_abort()
            return self._json(200, {"ok": True, "ignored": not accepted})
        if url.path == "/finish":
            try:
                expected = int(json.loads(self._read(10_000) or b"{}").get("chunks"))
            except (TypeError, ValueError):
                return self._json(400, {"error": "chunk count missing"})
            missing = [i for i in range(expected) if not (RECEIVER.chunks / f"{i:06d}.part").exists()]
            if missing:
                return self._json(409, {"error": f"missing chunks {missing[:5]}"})
            if not RECEIVER.mark_finished(expected):
                return self._json(410, {"error": "session closed"})
            return self._json(200, {"ok": True})
        self._json(404, {"error": "not found"})


def start_tunnel(port: int) -> tuple[subprocess.Popen | None, list]:
    """Cloudflare quick tunnel, as in server.py. The public URL lands in found[0]."""
    exe = shutil.which("cloudflared")
    if not exe:
        sys.exit("cloudflared not found. Install it with:  winget install Cloudflare.cloudflared")
    proc = subprocess.Popen([exe, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{port}"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace")
    found: list = []
    pattern = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")

    def read_output():
        for line in proc.stdout:
            m = pattern.search(line)
            if m and not found:
                found.append(m.group(0))

    threading.Thread(target=read_output, daemon=True).start()
    return proc, found


# ---------------------------------------------------------------- finalize

def finalize(folder: Path, volunteer_id: str, app: App | None, session_id: str, run_clips: bool, volunteer_num: int):
    chunks = sorted(folder.joinpath("chunks").glob("*.part"))
    if not chunks:
        sys.exit(f"No recording chunks in {folder / 'chunks'}")
    numbers = [int(p.stem) for p in chunks]
    gaps = sorted(set(range(max(numbers) + 1)) - set(numbers))
    if gaps:
        print(f"[Warning] Chunks missing: {gaps[:10]}. The recording will have a jump at those points; check it.")

    webm = folder / "recording.webm"
    with open(webm, "wb") as out:
        for p in chunks:
            out.write(p.read_bytes())
    print(f"Joined {len(chunks)} chunks into {webm.name} ({webm.stat().st_size / 1e6:.0f} MB)")

    mp4 = folder / f"{volunteer_id}.mp4"
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        sys.exit("ffmpeg not found. Install it with:  winget install ffmpeg")
    print(f"Converting to {mp4.name} (a few minutes)...")
    subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(webm),
                    "-vf", f"fps={OUTPUT_FPS}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(mp4)], check=True)

    # The database is the main record; the copy the page sent here fills any gap.
    events: dict[int, dict] = {}
    mirror_path = folder / "events_mirror.json"
    if mirror_path.exists():
        events.update({int(k): v for k, v in json.loads(mirror_path.read_text(encoding="utf-8")).items()})
    if app:
        try:
            db_events = app.call("GET", "events", id=session_id)["events"]
            only_mirror = set(events) - {e["seq"] for e in db_events}
            events.update({e["seq"]: e for e in db_events})
            if only_mirror:
                print(f"[Note] {len(only_mirror)} event(s) reached only this laptop, not the database; they are kept.")
        except Exception as e:  # noqa: BLE001  (network trouble must not lose the session)
            print(f"[Warning] Could not read events from the web app ({e}); using this laptop's copy only.")
    if not any(e.get("event") == "session_start" for e in events.values()):
        sys.exit("No session_start event was received, so the log can't be built.")

    log_path = folder / "session_log.jsonl"
    with open(log_path, "w", encoding="utf-8") as f:
        for seq in sorted(events):
            record = {k: v for k, v in events[seq].items() if k != "seq"}
            record["t_iso"] = now_iso(record["t"])
            record["session_id"] = session_id
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Wrote {log_path} ({len(events)} events)")

    shutil.rmtree(folder / "chunks", ignore_errors=True)
    if run_clips:
        subprocess.run([sys.executable, str(ASSISTANT_TOOL_DIR / "make_clips.py"), "--volunteer", str(volunteer_num),
                        "--recording", str(mp4), "--update-labels"], cwd=PROJECT_ROOT)
    else:
        print(f"Next:  python assistant_tool/make_clips.py --volunteer {volunteer_num} "
              f"--recording \"{mp4.relative_to(PROJECT_ROOT)}\" --update-labels")


# ---------------------------------------------------------------- main

def load_config(args) -> tuple[str, str]:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8")) if CONFIG_PATH.exists() else {}
    url = args.app or os.environ.get("DECUE_APP_URL") or cfg.get("app_url")
    key = args.admin_key or os.environ.get("DECUE_ADMIN_KEY") or cfg.get("admin_key")
    if not url or not key:
        sys.exit(f"Set the web app URL and admin key with --app/--admin-key, DECUE_APP_URL/DECUE_ADMIN_KEY, "
                 f"or {CONFIG_PATH.name}.")
    return url, key


def wait_for_tunnel(proc: subprocess.Popen, found: list, what: str) -> str:
    print(f"Starting the Cloudflare tunnel for {what}...")
    for _ in range(60):
        if found:
            return found[0]
        time.sleep(0.5)
    proc.terminate()
    raise RuntimeError("The tunnel did not start within 30 s. Check the internet connection and try again.")


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


class ReceiverServer(ThreadingHTTPServer):
    # Python sets SO_REUSEADDR on its HTTP servers, which on Windows lets a
    # second server bind a port another one is still listening on. Off there,
    # so a busy port fails loudly instead of splitting a live session's uploads.
    allow_reuse_address = os.name != "nt"
    daemon_threads = True


def start_local_app(key: str) -> subprocess.Popen:
    """Runs automated_interview/web/dev-server.mjs, the same pages and API as
    the Vercel app, on this laptop. Timings go to
    automated_interview/web/.devdata/db.json instead of Neon (lib/db.js puts
    it under the working directory, hence cwd=web). The admin key is random
    for each run, because the tunnel makes the app public."""
    node = shutil.which("node")
    if not node:
        sys.exit("Node.js not found. Install it with:  winget install OpenJS.NodeJS.LTS")
    web = WEB_APP_DIR
    env = {**os.environ, "PORT": str(LOCAL_APP_PORT), "ADMIN_KEY": key}
    env.pop("DATABASE_URL", None)
    proc = subprocess.Popen([node, str(web / "dev-server.mjs")], cwd=web, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    for _ in range(30):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{LOCAL_APP_PORT}/", timeout=2)
            return proc
        except OSError:
            time.sleep(0.5)
    proc.terminate()
    sys.exit(f"The interview page did not start on port {LOCAL_APP_PORT}. Is something else using it?")


def span(seconds: float) -> str:
    return f"{seconds / 60:g} min" if seconds >= 60 else f"{seconds:g} s"


def stop_processes(procs: list):
    for proc in procs:
        proc.terminate()
    for proc in procs:
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def remove_folder(folder: Path) -> bool:
    # Retried: on Windows a virus scanner can hold a just-written file for a moment.
    for _ in range(20):
        shutil.rmtree(folder, ignore_errors=True)
        if not folder.exists():
            return True
        time.sleep(0.5)
    return False


def wait_for_outcome() -> str:
    """Waits until the session ends one way or another:
      "finished"  the page has sent every chunk (/finish)
      "abort"     the page reported it was closed mid-interview
      "idle"      nothing arrived for IDLE_TIMEOUT_S after the interview began
      "prestart"  the interview didn't begin within PRESTART_TIMEOUT_S
      "stalled"   session_end arrived, then nothing for IDLE_TIMEOUT_S: the
                  interview is complete but the upload stopped. Never wiped.
    For "abort", "idle" and "prestart" the receiver is already closed."""
    while True:
        # Short waits, so Ctrl+C is noticed promptly on Windows too.
        RECEIVER.wake.wait(timeout=1)
        if RECEIVER.finished.is_set():
            return "finished"
        if RECEIVER.abort_requested:
            return "abort"
        outcome = RECEIVER.check_idle()
        if outcome:
            return outcome


def abandon(outcome: str, httpd, tunnels: list, local_app, app: App, folder: Path, volunteer_id: str, num: int) -> int:
    """The volunteer quit: delete everything of this session, so no trace is
    left (the consent form promises deletion on withdrawal) and the number is
    free again. The receiver is already closed, so nothing can be written
    into the folder any more."""
    httpd.shutdown()
    httpd.server_close()
    stop_processes(tunnels)
    problems = []
    try:
        app.call("POST", "delete", id=RECEIVER.session_id)
    except Exception as e:  # noqa: BLE001  (still delete the folder, then say what is left)
        problems.append(f"its record in the web app was not deleted ({e})")
    if not remove_folder(folder):
        problems.append(f"{folder} could not be deleted")
    if local_app:
        stop_processes([local_app])
    why = {
        "abort": "quit before finishing (the interview page was closed)",
        "idle": f"quit before finishing (nothing arrived for {span(IDLE_TIMEOUT_S)})",
        "prestart": f"quit before finishing (the interview wasn't begun within {span(PRESTART_TIMEOUT_S)})",
    }[outcome]
    print()
    if problems:
        print(f"{volunteer_id} {why}, but NOT all of their data was deleted: {'; '.join(problems)}. "
              f"Delete the rest by hand.")
        return 1
    print(f"{volunteer_id} {why}. All of their data was deleted; number {num} is free again.")
    return 0


def main() -> int:
    global RECEIVER
    parser = argparse.ArgumentParser(description="Run an automatic interview session with the video kept on this laptop.")
    parser.add_argument("--volunteer", type=int,
                        help="volunteer number, e.g. 8 for volunteer_08 (default: the lowest number with no session; "
                             "required with --finalize)")
    parser.add_argument("--local", action="store_true",
                        help="host the interview page on this laptop and share it through a Cloudflare tunnel "
                             "(no Vercel or database needed)")
    parser.add_argument("--app", help="web app URL, e.g. https://decue.vercel.app")
    parser.add_argument("--admin-key", help="ADMIN_KEY from the Vercel project settings")
    parser.add_argument("--no-tunnel", action="store_true",
                        help="testing: everything is reachable only on this computer")
    parser.add_argument("--no-clips", action="store_true", help="don't run make_clips.py at the end")
    parser.add_argument("--finalize", action="store_true",
                        help="build the recording and log from what was already received (after a crash)")
    args = parser.parse_args()

    if args.finalize and args.volunteer is None:
        parser.error("--finalize needs --volunteer N: the number of the session to finish.")
    if args.volunteer is not None and args.volunteer < 1:
        parser.error("--volunteer must be 1 or more.")
    auto_number = args.volunteer is None
    # Same rule as the control panel's default: has_session(), or any
    # data/raw/volunteer_NN folder (e.g. a session in progress or waiting for
    # --finalize). Nothing is created until the session starts below.
    num = first_free_volunteer_num() if auto_number else args.volunteer
    volunteer_id = f"volunteer_{num:02d}"
    folder = Path(VOLUNTEER_RAW_DIR) / volunteer_id
    state_path = folder / "remote_session.json"

    if args.finalize:
        if not state_path.exists():
            sys.exit(f"No remote session was started for {volunteer_id} ({state_path} missing).")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        # A local app is no longer running, so the laptop's own copy of the events is used.
        app = None if args.local else App(*load_config(args))
        finalize(folder, volunteer_id, app, state["session_id"], not args.no_clips, num)
        return 0

    if has_session(num) or state_path.exists():
        sys.exit(f"{volunteer_id} already has a session. Use the next free volunteer number, "
                 f"or --finalize to finish an interrupted one.")
    bank = json.loads(ANSWERS_PATH.read_text(encoding="utf-8"))
    plan = build_plan(num, bank)
    bad = [p for p in plan if not MIN_DELAY_S <= p["delay_s"] <= MAX_DELAY_S]
    if bad:
        sys.exit(f"answers.json: answer delay outside {MIN_DELAY_S}-{MAX_DELAY_S} s for {len(bad)} question(s).")
    busy = [p for p in ([LOCAL_APP_PORT] if args.local else []) + [RECEIVER_PORT] if port_in_use(p)]
    if busy:
        sys.exit(f"Port {', '.join(map(str, busy))} is already in use (is another session running?). Stop it, or "
                 f"choose other ports with DECUE_LOCAL_APP_PORT / DECUE_RECEIVER_PORT.")

    order = "unassisted" if num % 2 else "assisted"
    print("=" * 64)
    print(f"  Volunteer number: {num} ({'odd' if num % 2 else 'even'}: {order} round first)")
    if auto_number:
        print("  (the lowest number with no session; pass --volunteer N to choose another)")
    print("=" * 64)

    new_folder = not folder.exists()
    folder.mkdir(parents=True, exist_ok=True)
    local_app, tunnels, httpd = None, [], None
    try:
        # Where the volunteer opens the page (public_url) and where this script
        # talks to the app (app); they differ only in --local mode.
        if args.local:
            key = secrets.token_urlsafe(24)
            local_app = start_local_app(key)
            app = App(f"http://127.0.0.1:{LOCAL_APP_PORT}", key)
            public_url = app.url
            if not args.no_tunnel:
                proc, found = start_tunnel(LOCAL_APP_PORT)
                tunnels.append(proc)
                public_url = wait_for_tunnel(proc, found, "the interview page")
        else:
            app = App(*load_config(args))
            public_url = app.url

        origin = "{0.scheme}://{0.netloc}".format(urlparse(public_url))
        RECEIVER = Receiver(folder, secrets.token_urlsafe(18), origin)
        httpd = ReceiverServer(("127.0.0.1", RECEIVER_PORT), Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        if args.no_tunnel:
            receiver_url = f"http://127.0.0.1:{RECEIVER_PORT}"
        else:
            proc, found = start_tunnel(RECEIVER_PORT)
            tunnels.append(proc)
            receiver_url = wait_for_tunnel(proc, found, "uploads")

        app.call("POST", "init")
        created = app.call("POST", "create", {
            "volunteer_id": volunteer_id, "plan": plan, "settings": bank["settings"],
            "receiver_url": receiver_url, "receiver_key": RECEIVER.key,
        })
        RECEIVER.session_id = created["id"]
        state_path.write_text(json.dumps({"session_id": created["id"], "created": now_iso(time.time())}), encoding="utf-8")
    except (RuntimeError, SystemExit, OSError, KeyboardInterrupt) as e:
        # Nothing reached the volunteer yet. A folder this run created and
        # nothing was written to is removed, so the number stays free.
        if httpd:
            httpd.shutdown()
            httpd.server_close()
        stop_processes(tunnels + ([local_app] if local_app else []))
        if new_folder and not any(p.is_file() for p in folder.rglob("*")):
            remove_folder(folder)
        sys.exit(str(e) if not isinstance(e, KeyboardInterrupt) else "Stopped before the session was created.")

    finalize_cmd = (f"venv\\Scripts\\python.exe automated_interview\\remote_session.py --volunteer {num}"
                    f"{' --local' if args.local else ''} --finalize")
    exit_code = 0
    try:
        print(f"\nSession for {volunteer_id} is ready. Send the volunteer this link:\n")
        print(f"    {public_url.rstrip('/')}/?s={created['token']}\n")
        if args.local and not args.no_tunnel:
            print("(A new tunnel address can take up to a minute to work everywhere. If the link doesn't open on "
                  "this laptop, that is usually only your router's DNS; it can still work for the volunteer.)")
        print("Keep this window open and the laptop awake until the volunteer's page says 'All done'.")
        print(f"If the volunteer quits partway (closes the page, or nothing arrives for {span(IDLE_TIMEOUT_S)}), "
              f"everything of this session is deleted.")
        print("Progress appears below. Press Ctrl+C to abort.\n")
        outcome = wait_for_outcome()
        if outcome == "finished":
            print("All chunks received.")
            # Close the public side as soon as the upload is complete.
            httpd.shutdown()
            stop_processes(tunnels)
            tunnels = []
            # A local app stays up (on this laptop only) until its events have been read.
            finalize(folder, volunteer_id, app, RECEIVER.session_id, not args.no_clips, num)
        elif outcome == "stalled":
            # The interview itself is complete, so nothing is deleted.
            httpd.shutdown()
            print(f"\nThe volunteer finished the interview, but nothing has arrived for {span(IDLE_TIMEOUT_S)}, "
                  f"so the upload has stalled. Nothing was deleted.")
            print("Stopped. If the volunteer had finished, run the same command with --finalize to build the files:")
            print(f"    {finalize_cmd}")
            exit_code = 1
        else:
            exit_code = abandon(outcome, httpd, tunnels, local_app, app, folder, volunteer_id, num)
            tunnels, local_app = [], None
    except KeyboardInterrupt:
        print(f"\nStopped. If the volunteer had finished, run the same command with --finalize to build the files.")
        print(f"    {finalize_cmd}")
    finally:
        stop_processes(tunnels + ([local_app] if local_app else []))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
