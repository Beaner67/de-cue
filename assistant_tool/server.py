"""
server.py

Subsystem A: a controlled "AI interview assistant" for the assisted round
(Wizard-of-Oz setup). The volunteer sees what looks like a real-time AI
assistant; the researcher decides when each answer appears, so every
volunteer gets the same answer delay and every timing is logged.

Two local web servers:
    - control   http://127.0.0.1:8766  researcher only, never exposed
    - volunteer http://127.0.0.1:8765  the assistant page; with --tunnel it
                                       is exposed through a Cloudflare quick
                                       tunnel so a remote volunteer can open it

Nothing about the volunteer passes through this tool: it only sends the
pre-written answers from answers.json and receives timing acknowledgements.

Usage (from the project root):
    python assistant_tool/server.py --tunnel     # remote session
    python assistant_tool/server.py              # local testing only

Timings are appended to data/raw/volunteer_XX/session_log.jsonl, which
make_clips.py uses to cut the recording into per-question clips.
"""

# Lets the "X | None" type hints run on Python 3.9, the system Python on the
# research laptop, as well as in the 3.12 venv.
from __future__ import annotations

import argparse
import json
import queue
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

TOOL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOL_DIR.parent / "src"))
# pyrefly: ignore [missing-import]
from paths_config import VOLUNTEER_RAW_DIR  # noqa: E402  (stdlib-only module)

ANSWERS_PATH = TOOL_DIR / "answers.json"
POLL_TIMEOUT_S = 20          # long-poll hold time; well under Cloudflare's 100 s limit
CONNECTED_WINDOW_S = POLL_TIMEOUT_S + 10
# Control-page key timestamps are trusted only if this close. Generous because a
# press can wait in the page's queue behind a slow request before it is sent.
MAX_CLIENT_CLOCK_SKEW_S = 30
# Allowed range for the per-question answer delay set through each question's difficulty.
MIN_DELAY_S, MAX_DELAY_S = 0.5, 2.0


def now_iso(t: float) -> str:
    return datetime.fromtimestamp(t, tz=timezone.utc).isoformat(timespec="milliseconds")


class LogWriter:
    """Appends log lines on a background thread, so a slow disk (e.g. a USB
    drive retrying reads) never holds the session lock and delays key presses."""

    def __init__(self):
        self.queue: queue.Queue = queue.Queue()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def write(self, path: Path, line: str):
        self.queue.put((path, line))

    def _run(self):
        while (item := self.queue.get()) is not None:
            path, line = item
            for attempt in range(5):
                try:
                    with open(path, "a", encoding="utf-8") as f:
                        f.write(line + "\n")
                    break
                except OSError as e:
                    if attempt == 4:
                        # Keep the record recoverable from the terminal rather than losing it.
                        print(f"[log] Could not write to {path} ({e}). Record: {line}")
                    else:
                        time.sleep(1)

    def close(self, timeout_s: float = 15):
        self.queue.put(None)
        self.thread.join(timeout_s)


def answer_delay(question: dict, settings: dict) -> float:
    """Seconds from the question-end mark to the answer appearing. Fixed per
    question through its difficulty, so a question gets the same delay for every
    volunteer; a question without a difficulty uses answer_delay_s."""
    difficulty = question.get("difficulty")
    if difficulty is None:
        return float(settings["answer_delay_s"])
    try:
        return float(settings["delay_by_difficulty"][difficulty])
    except KeyError:
        raise ValueError(f'difficulty "{difficulty}" has no delay in settings.delay_by_difficulty') from None


def williams_orders(n: int) -> list[list[int]]:
    """Balanced Latin square (Williams design) over n questions. Across the orders,
    every question appears equally often in every position and directly follows
    every other question equally often. A random shuffle cannot promise that with
    only a handful of volunteers. Odd n needs every order reversed as well."""
    first, low, high = [0], 1, n - 1
    while len(first) < n:
        first.append(low)
        low += 1
        if len(first) < n:
            first.append(high)
            high -= 1
    orders = [[(i + shift) % n for i in first] for shift in range(n)]
    return orders if n % 2 == 0 else orders + [order[::-1] for order in orders]


def build_plan(volunteer_num: int, bank: dict) -> list[dict]:
    """Counterbalanced order from SESSION_PROTOCOL_GUIDE.md Section 2:
    odd volunteers do Unassisted (Set A) then Assisted (Set B); even
    volunteers do Assisted (Set A) then Unassisted (Set B).

    Within each round the questions follow a Williams order. Volunteers of the
    same parity get the same sets in the same roles, so consecutive ones
    (1, 3, 5, 7 and 2, 4, 6, 8) step through the orders together."""
    if volunteer_num % 2 == 1:
        rounds = [("unassisted", "A"), ("assisted", "B")]
    else:
        rounds = [("assisted", "A"), ("unassisted", "B")]
    group_index = (volunteer_num - 1) // 2
    plan = []
    for round_num, (condition, set_name) in enumerate(rounds, start=1):
        questions = bank["sets"][set_name]
        orders = williams_orders(len(questions))
        for position, index in enumerate(orders[group_index % len(orders)], start=1):
            q = questions[index]
            plan.append({
                "round": round_num,
                "condition": condition,
                "question_set": set_name,
                "position": position,
                "question_num": q["num"],
                "question_type": q["type"],
                "difficulty": q.get("difficulty"),
                "delay_s": answer_delay(q, bank["settings"]),
                "question": q["question"],
                "answer": q["answer"],
            })
    return plan


class Session:
    def __init__(self, token: str):
        self.cond = threading.Condition()
        self.token = token
        self.public_url = None
        # Starts at 1, not 0: the page sends after=0 to mean "first connect", so a
        # seq of 0 made every poll return at once (a busy loop until the session started).
        self.seq = 1
        self.events: list[tuple[int, dict]] = []   # volunteer-facing events
        self.volunteer_last_seen = 0.0
        self.recent: list[str] = []                # human-readable log for the control page

        self.session_id = None
        self.volunteer_num = None
        self.log_path = None
        self.settings = {}
        self.plan: list[dict] = []
        self.cursor = 0
        self.phase = "idle"          # idle | waiting_question | answering | done
        self.recording_marked = False
        self.last_question_end_t = None
        self.question_end_by_answer: dict[str, float] = {}
        self.first_shown_s: dict[str, float] = {}   # answer_id -> seconds from question end to first ack
        self.current_answer_id = None                # the open assisted question's answer, for the control page
        self.bank_test_answer = ""

    # ---- volunteer-facing events -------------------------------------------------

    def _mode_event(self) -> dict:
        if self.phase == "idle":
            return {"type": "mode", "assistant_on": False, "message": "Waiting for the session to start."}
        if self.phase == "done":
            return {"type": "mode", "assistant_on": False, "message": "The session is over. Thank you!"}
        on = self.plan[self.cursor]["condition"] == "assisted"
        return {"type": "mode", "assistant_on": on,
                "message": "" if on else "The assistant is off for this round."}

    def _push(self, payload: dict):
        self.seq += 1
        self.events.append((self.seq, payload))
        del self.events[:-50]
        self.cond.notify_all()

    def wait(self, after: int) -> dict:
        with self.cond:
            self.volunteer_last_seen = time.time()
            oldest = self.events[0][0] if self.events else self.seq + 1
            if after <= 0 or after > self.seq or after < oldest - 1:
                # First connect, reload, or a gap: send the current state only,
                # so an old answer is never replayed.
                return {"seq": self.seq, "events": [self._mode_event()]}
            self.cond.wait_for(lambda: self.seq > after, timeout=POLL_TIMEOUT_S)
            self.volunteer_last_seen = time.time()
            return {"seq": self.seq, "events": [p for s, p in self.events if s > after]}

    # ---- logging -----------------------------------------------------------------

    def _log(self, record: dict, summary: str):
        record.setdefault("t", time.time())
        record["t_iso"] = now_iso(record["t"])
        record["session_id"] = self.session_id
        if self.log_path:
            LOG_WRITER.write(self.log_path, json.dumps(record, ensure_ascii=False))
        stamp = datetime.fromtimestamp(record["t"]).strftime("%H:%M:%S.%f")[:-3]
        self.recent.append(f"{stamp}  {summary}")
        del self.recent[:-12]

    # ---- researcher actions ------------------------------------------------------

    def action(self, body: dict) -> tuple[bool, str]:
        name = body.get("action")
        t = time.time()
        client_t = body.get("client_t")
        if isinstance(client_t, (int, float)) and abs(client_t / 1000 - t) < MAX_CLIENT_CLOCK_SKEW_S:
            t = client_t / 1000  # the key press itself, not when the request arrived

        with self.cond:
            if name == "start":
                return self._start(body, t)
            if self.phase == "idle":
                return False, "Start a session first."
            if name == "recording_start":
                self.recording_marked = True
                self._log({"event": "recording_start", "t": t}, "Recording start marked")
                return True, ""
            if name == "question_end":
                return self._question_end(t)
            if name == "answer_end":
                return self._answer_end(t)
            if name == "back":
                if self.phase == "done":
                    self.cursor = len(self.plan) - 1
                elif self.phase == "answering":
                    pass  # "back" while answering just re-opens the current question
                else:
                    self.cursor = max(0, self.cursor - 1)
                self.phase = "waiting_question"
                self.current_answer_id = None
                self._log({"event": "back", "t": t, "cursor": self.cursor}, f"Went back to item {self.cursor + 1}")
                self._push(self._mode_event())
                return True, ""
            if name == "test":
                # A test answer replaces whatever the volunteer's window shows, including a real
                # answer still waiting out its delay, so it is only allowed before recording starts.
                if self.recording_marked:
                    return False, ("Test answers are only for before the recording starts. "
                                   "Space sends each real answer by itself.")
                answer_id = "test-" + uuid.uuid4().hex[:8]
                self.question_end_by_answer[answer_id] = t
                self._push({"type": "answer", "answer_id": answer_id,
                            "question": "Test question: can you see this?",
                            "answer": self.bank_test_answer,
                            "delay_s": self.settings["answer_delay_s"],
                            "words_per_second": self.settings["words_per_second"]})
                self._log({"event": "test_answer", "t": t, "answer_id": answer_id}, "Test answer sent")
                return True, ""
            if name == "clear":
                self._push(self._mode_event())
                self._log({"event": "clear", "t": t}, "Volunteer screen cleared")
                return True, ""
        return False, f"Unknown action: {name}"

    def _start(self, body: dict, t: float) -> tuple[bool, str]:
        try:
            num = int(body.get("volunteer_num"))
            if not 1 <= num <= 99:
                raise ValueError
        except (TypeError, ValueError):
            return False, "Volunteer number must be between 1 and 99."
        bank = json.loads(ANSWERS_PATH.read_text(encoding="utf-8"))
        try:
            plan = build_plan(num, bank)
        except ValueError as e:
            return False, f"answers.json: {e}."
        out_of_range = [f"Set {p['question_set']} Q{p['question_num']}" for p in plan
                        if not MIN_DELAY_S <= p["delay_s"] <= MAX_DELAY_S]
        if out_of_range:
            return False, f"answers.json: delay outside {MIN_DELAY_S} to {MAX_DELAY_S} s for {', '.join(out_of_range)}."
        self.bank_test_answer = bank["test_answer"]
        self.settings = bank["settings"]
        self.plan = plan
        self.volunteer_num = num
        self.session_id = uuid.uuid4().hex[:12]
        folder = Path(VOLUNTEER_RAW_DIR) / f"volunteer_{num:02d}"
        folder.mkdir(parents=True, exist_ok=True)
        self.log_path = folder / "session_log.jsonl"
        self.cursor = 0
        self.phase = "waiting_question"
        self.recording_marked = False
        self.last_question_end_t = None
        self.current_answer_id = None
        self.recent = []
        self._log({
            "event": "session_start", "t": t,
            "volunteer_id": f"volunteer_{num:02d}",
            "settings": self.settings,
            "plan": [{k: v for k, v in item.items() if k not in ("question", "answer")} for item in self.plan],
        }, f"Session started for volunteer_{num:02d}")
        # Odd volunteers get Set B assisted, even ones Set A, so unequal set means
        # would mix a delay difference into the counterbalancing.
        means = {name: sum(answer_delay(q, self.settings) for q in qs) / len(qs) for name, qs in bank["sets"].items()}
        if max(means.values()) - min(means.values()) > 0.01:
            note = "Warning: mean answer delay differs between sets (" + ", ".join(f"Set {k} {v:.2f} s" for k, v in means.items()) + ")"
            print(note)
            self.recent.append(note)
        self._push(self._mode_event())
        return True, ""

    def _question_end(self, t: float) -> tuple[bool, str]:
        if self.phase not in ("waiting_question", "answering"):
            return False, "No question is open."
        item = self.plan[self.cursor]
        remark = self.phase == "answering"
        self.phase = "answering"
        self.last_question_end_t = t
        record = {"event": "question_end", "t": t, "remark": remark,
                  **{k: item[k] for k in ("round", "condition", "question_set", "question_num", "question_type")}}
        label = f"R{item['round']} {item['condition']} Q{item['question_num']}"
        self.current_answer_id = None
        if item["condition"] == "assisted":
            answer_id = uuid.uuid4().hex[:10]
            record["answer_id"] = answer_id
            record["delay_s"] = item["delay_s"]
            self.question_end_by_answer[answer_id] = t
            self.current_answer_id = answer_id
            self._push({"type": "answer", "answer_id": answer_id,
                        "question": item["question"], "answer": item["answer"],
                        "delay_s": item["delay_s"],
                        "words_per_second": self.settings["words_per_second"]})
        self._log(record, f"Question end{' (re-marked)' if remark else ''}: {label}")
        return True, ""

    def _answer_end(self, t: float) -> tuple[bool, str]:
        if self.phase != "answering":
            return False, "Mark the end of the question first (Space)."
        item = self.plan[self.cursor]
        self._log({"event": "answer_end", "t": t,
                   **{k: item[k] for k in ("round", "condition", "question_set", "question_num", "question_type")}},
                  f"Answer end: R{item['round']} {item['condition']} Q{item['question_num']}")
        self.cursor += 1
        self.last_question_end_t = None
        self.current_answer_id = None
        if self.cursor >= len(self.plan):
            self.phase = "done"
            self._log({"event": "session_end", "t": t}, "Session complete")
        else:
            self.phase = "waiting_question"
        self._push(self._mode_event())
        return True, ""

    def ack(self, body: dict):
        """The volunteer page reports when the first word of an answer appeared."""
        t = time.time()
        with self.cond:
            answer_id = str(body.get("answer_id", ""))
            q_end = self.question_end_by_answer.get(answer_id)
            waited = body.get("waited_ms")
            # A second ack for the same answer means the volunteer link is open in a second window.
            duplicate = answer_id in self.first_shown_s
            if q_end and not duplicate:
                self.first_shown_s[answer_id] = round(t - q_end, 3)
            record = {
                "event": "answer_shown", "t": t, "answer_id": answer_id,
                # question end -> ack received: configured delay + one network round trip
                "since_question_end_s": round(t - q_end, 3) if q_end else None,
                "client_waited_ms": round(waited, 1) if isinstance(waited, (int, float)) else None,
            }
            if duplicate:
                record["duplicate"] = True
                summary = "Answer appeared in a second volunteer window (the link is open twice)"
            else:
                summary = f"Answer appeared on volunteer screen (+{t - q_end:.2f} s)" if q_end else "Answer appeared"
            self._log(record, summary)

    # ---- control-page state ------------------------------------------------------

    def state(self) -> dict:
        with self.cond:
            current = self.plan[self.cursor] if self.phase in ("waiting_question", "answering") else None
            return {
                "phase": self.phase,
                "volunteer_id": f"volunteer_{self.volunteer_num:02d}" if self.volunteer_num else None,
                "cursor": self.cursor,
                "current": current,
                "plan": [{"round": p["round"], "condition": p["condition"], "question_num": p["question_num"],
                          "question_type": p["question_type"], "done": i < self.cursor}
                         for i, p in enumerate(self.plan)],
                "recording_marked": self.recording_marked,
                "last_question_end_t": self.last_question_end_t,
                # Seconds from question end until the volunteer's window first showed the answer;
                # None while it is on its way, or when no assisted answer is open.
                "current_answer_shown_s": self.first_shown_s.get(self.current_answer_id) if self.current_answer_id else None,
                "volunteer_connected": time.time() - self.volunteer_last_seen < CONNECTED_WINDOW_S,
                "volunteer_url": f"{self.public_url}/?t={self.token}" if self.public_url else None,
                "local_volunteer_url": f"http://127.0.0.1:{VOLUNTEER_PORT}/?t={self.token}",
                "settings": self.settings,
                "recent": list(reversed(self.recent)),
                "log_path": str(self.log_path) if self.log_path else None,
            }


VOLUNTEER_PORT = 8765
CONTROL_PORT = 8766
SESSION: Session
LOG_WRITER: LogWriter


class BaseHandler(BaseHTTPRequestHandler):
    server_version = "AssistantTool/1.0"

    def log_message(self, fmt, *args):
        pass  # keep the terminal quiet; everything that matters goes to the session log

    def _send(self, status: int, body: bytes, content_type: str):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, status=200):
        self._send(status, json.dumps(obj).encode("utf-8"), "application/json")

    def _file(self, name: str):
        self._send(200, (TOOL_DIR / name).read_bytes(), "text/html; charset=utf-8")

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length <= 10_000:
            return {}
        try:
            data = json.loads(self.rfile.read(length))
            return data if isinstance(data, dict) else {}
        except (ValueError, UnicodeDecodeError):
            return {}


class VolunteerHandler(BaseHandler):
    """Public side. Every route needs the session token from the link."""

    def _authorised(self, query) -> bool:
        return secrets.compare_digest(query.get("t", [""])[0], SESSION.token)

    def do_GET(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        if url.path == "/favicon.ico":
            return self._send(204, b"", "text/plain")
        if not self._authorised(query):
            return self._send(403, b"This link is not valid. Ask the researcher for the current link.",
                              "text/plain; charset=utf-8")
        if url.path == "/":
            return self._file("volunteer.html")
        if url.path == "/api/wait":
            try:
                after = int(query.get("after", ["0"])[0])
            except ValueError:
                after = 0
            return self._json(SESSION.wait(after))
        self._send(404, b"Not found", "text/plain")

    def do_POST(self):
        url = urlparse(self.path)
        if not self._authorised(parse_qs(url.query)):
            return self._send(403, b"Forbidden", "text/plain")
        if url.path == "/api/ack":
            SESSION.ack(self._body())
            return self._json({"ok": True})
        self._send(404, b"Not found", "text/plain")


class ControlHandler(BaseHandler):
    """Researcher side. Bound to 127.0.0.1 only and never tunnelled."""

    def _local_origin(self) -> bool:
        # Refuse cross-site requests from other pages open in the researcher's browser.
        origin = self.headers.get("Origin")
        return origin is None or origin in (f"http://127.0.0.1:{CONTROL_PORT}", f"http://localhost:{CONTROL_PORT}")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            return self._file("control.html")
        if path == "/api/state":
            return self._json(SESSION.state())
        self._send(404, b"Not found", "text/plain")

    def do_POST(self):
        if urlparse(self.path).path != "/api/action" or not self._local_origin():
            return self._send(403, b"Forbidden", "text/plain")
        ok, error = SESSION.action(self._body())
        self._json({"ok": ok, "error": error, "state": SESSION.state()}, 200 if ok else 400)


def start_tunnel(port: int) -> subprocess.Popen | None:
    exe = shutil.which("cloudflared")
    if not exe:
        print("[tunnel] cloudflared not found. Install it with:  winget install Cloudflare.cloudflared")
        return None
    proc = subprocess.Popen(
        [exe, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{port}"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
    )

    def read_output():
        pattern = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
        for line in proc.stdout:
            match = pattern.search(line)
            if match and not SESSION.public_url:
                SESSION.public_url = match.group(0)
                print(f"[tunnel] Volunteer link: {SESSION.public_url}/?t={SESSION.token}")

    threading.Thread(target=read_output, daemon=True).start()
    return proc


def main():
    global SESSION, LOG_WRITER, VOLUNTEER_PORT, CONTROL_PORT
    parser = argparse.ArgumentParser(description="Controlled AI-assistant tool for the assisted round.")
    parser.add_argument("--tunnel", action="store_true",
                        help="expose the volunteer page through a Cloudflare quick tunnel (remote sessions)")
    parser.add_argument("--volunteer-port", type=int, default=VOLUNTEER_PORT)
    parser.add_argument("--control-port", type=int, default=CONTROL_PORT)
    args = parser.parse_args()
    VOLUNTEER_PORT, CONTROL_PORT = args.volunteer_port, args.control_port

    LOG_WRITER = LogWriter()
    SESSION = Session(token=secrets.token_urlsafe(9))
    volunteer_server = ThreadingHTTPServer(("127.0.0.1", VOLUNTEER_PORT), VolunteerHandler)
    control_server = ThreadingHTTPServer(("127.0.0.1", CONTROL_PORT), ControlHandler)
    volunteer_server.daemon_threads = control_server.daemon_threads = True
    threading.Thread(target=volunteer_server.serve_forever, daemon=True).start()

    tunnel = start_tunnel(VOLUNTEER_PORT) if args.tunnel else None
    print(f"Control panel (open this yourself): http://127.0.0.1:{CONTROL_PORT}/")
    print(f"Volunteer page, this computer only: http://127.0.0.1:{VOLUNTEER_PORT}/?t={SESSION.token}")
    if args.tunnel:
        print("[tunnel] Starting; the public volunteer link appears in the control panel in a few seconds.")
    print("Press Ctrl+C to stop.")
    try:
        control_server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if tunnel:
            tunnel.terminate()
        LOG_WRITER.close()  # flush any log lines still waiting on a slow disk


if __name__ == "__main__":
    main()
