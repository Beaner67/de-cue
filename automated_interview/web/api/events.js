// POST /api/events?s=<token>   body: {events: [{seq, t, event, ...}, ...]}
// The volunteer page sends its timing events in small batches. Each event
// carries a page sequence number, so a retried batch is stored only once.

import { store } from "../lib/db.js";
import { body, query, send } from "../lib/http.js";

const ALLOWED = new Set([
  "session_start", "recording_start", "question_start", "question_end",
  "answer_shown", "answer_end", "round_start", "session_end", "recording_stop", "page_error",
]);
const MAX_BATCH = 50;

export default async function handler(req, res) {
  if (req.method !== "POST") return send(res, 405, { error: "POST only" });
  const db = await store();
  const s = await db.sessionByToken(query(req).s || "");
  if (!s) return send(res, 404, { error: "unknown session" });
  if (s.status === "finished") return send(res, 410, { error: "session finished" });

  const events = body(req).events;
  if (!Array.isArray(events) || events.length === 0 || events.length > MAX_BATCH) {
    return send(res, 400, { error: `send 1 to ${MAX_BATCH} events` });
  }
  for (const e of events) {
    if (!e || !Number.isInteger(e.seq) || typeof e.t !== "number" || !ALLOWED.has(e.event)
        || JSON.stringify(e).length > 20000) {
      return send(res, 400, { error: "malformed event" });
    }
  }
  await db.addEvents(s.id, events);
  const kinds = new Set(events.map((e) => e.event));
  // recording_stop is the page's last event; session_end comes just before it.
  if (kinds.has("recording_stop")) await db.setStatus(s.id, "finished");
  else if (kinds.has("session_start") && s.status === "created") await db.setStatus(s.id, "started");
  send(res, 200, { ok: true });
}
