// Researcher-only routes, called by automated_interview/remote_session.py with
// "Authorization: Bearer <ADMIN_KEY>".
//
//   POST /api/admin?action=init             create the tables (safe to repeat)
//   POST /api/admin?action=create           body: {volunteer_id, plan, settings, receiver_url, receiver_key}
//   GET  /api/admin?action=events&id=<id>   the session's timing events, in order
//   GET  /api/admin?action=list             recent sessions
//   POST /api/admin?action=delete&id=<id>   wipe an abandoned session (record and events); local store only

import { newId, store } from "../lib/db.js";
import { body, isAdmin, query, send } from "../lib/http.js";

export default async function handler(req, res) {
  if (!isAdmin(req)) return send(res, 401, { error: "admin key required" });
  const db = await store();
  const q = query(req);

  if (req.method === "POST" && q.action === "init") {
    await db.init();
    return send(res, 200, { ok: true });
  }
  if (req.method === "POST" && q.action === "create") {
    const b = body(req);
    // The receiver must be https (the Cloudflare tunnel); plain http is allowed
    // only for a receiver on the same computer, for local testing.
    const receiverOk = /^https:\/\//.test(b.receiver_url || "")
      || /^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?$/.test(b.receiver_url || "");
    if (!/^volunteer_\d{2}$/.test(b.volunteer_id || "") || !Array.isArray(b.plan) || !b.plan.length
        || !b.settings || !receiverOk || !b.receiver_key) {
      return send(res, 400, { error: "need volunteer_id, plan, settings, receiver_url (https), receiver_key" });
    }
    const session = {
      id: newId(9), token: newId(12), volunteer_id: b.volunteer_id, plan: b.plan, settings: b.settings,
      receiver_url: b.receiver_url, receiver_key: b.receiver_key,
    };
    await db.createSession(session);
    return send(res, 200, { id: session.id, token: session.token });
  }
  if (req.method === "GET" && q.action === "events") {
    const s = await db.sessionById(q.id || "");
    if (!s) return send(res, 404, { error: "unknown session" });
    return send(res, 200, { session: { id: s.id, volunteer_id: s.volunteer_id, status: s.status }, events: await db.events(s.id) });
  }
  if (req.method === "GET" && q.action === "list") {
    return send(res, 200, { sessions: await db.listSessions() });
  }
  if (req.method === "POST" && q.action === "delete") {
    if (!q.id) return send(res, 400, { error: "need id" });
    try {
      return send(res, 200, { ok: true, deleted: await db.deleteSession(q.id) });
    } catch (e) {
      return send(res, 501, { error: e.message });
    }
  }
  send(res, 400, { error: "unknown action" });
}
