// GET /api/session?s=<token>
// The volunteer page loads its session: the plan (questions, scripted answers,
// delays), and where to upload the recording (the researcher's laptop).

import { store } from "../lib/db.js";
import { query, send } from "../lib/http.js";

export default async function handler(req, res) {
  if (req.method !== "GET") return send(res, 405, { error: "GET only" });
  const db = await store();
  const s = await db.sessionByToken(query(req).s || "");
  if (!s) return send(res, 404, { error: "This link is not valid. Ask the researcher for a new link." });
  if (s.status === "finished") return send(res, 410, { error: "This session is already complete. Thank you!" });
  send(res, 200, {
    session_id: s.id,
    volunteer_id: s.volunteer_id,
    status: s.status,
    plan: s.plan,
    settings: s.settings,
    receiver: { url: s.receiver_url, key: s.receiver_key },
  });
}
