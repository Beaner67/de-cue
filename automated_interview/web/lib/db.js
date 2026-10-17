// Storage for sessions and their timing events.
//
// On Vercel, DATABASE_URL points at Neon Postgres (added through the Vercel
// Marketplace). Without it, as in `npm run dev`, a JSON file under .devdata/
// stands in, so the whole flow can be tested locally without a database.
//
// Only timings and the session plan are stored here. No video, audio,
// transcript or name ever reaches this app (see the consent form).

import { randomBytes } from "node:crypto";
import { mkdirSync, readFileSync, renameSync, writeFileSync, existsSync } from "node:fs";
import path from "node:path";

const SCHEMA = [
  `CREATE TABLE IF NOT EXISTS sessions (
     id            TEXT PRIMARY KEY,
     token         TEXT UNIQUE NOT NULL,
     volunteer_id  TEXT NOT NULL,
     plan          JSONB NOT NULL,
     settings      JSONB NOT NULL,
     receiver_url  TEXT NOT NULL,
     receiver_key  TEXT NOT NULL,
     status        TEXT NOT NULL DEFAULT 'created',
     created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
   )`,
  `CREATE TABLE IF NOT EXISTS events (
     session_id    TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
     seq           INTEGER NOT NULL,
     t             DOUBLE PRECISION NOT NULL,
     record        JSONB NOT NULL,
     received_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
     PRIMARY KEY (session_id, seq)
   )`,
];

export const newId = (bytes) => randomBytes(bytes).toString("base64url");

// ---------------------------------------------------------------- Neon

async function neonStore(url) {
  const { neon } = await import("@neondatabase/serverless");
  const sql = neon(url);
  return {
    async init() {
      for (const statement of SCHEMA) await sql.query(statement);
    },
    async createSession(s) {
      await sql.query(
        `INSERT INTO sessions (id, token, volunteer_id, plan, settings, receiver_url, receiver_key)
         VALUES ($1, $2, $3, $4, $5, $6, $7)`,
        [s.id, s.token, s.volunteer_id, JSON.stringify(s.plan), JSON.stringify(s.settings), s.receiver_url, s.receiver_key],
      );
    },
    async sessionByToken(token) {
      const rows = await sql.query("SELECT * FROM sessions WHERE token = $1", [token]);
      return rows[0] || null;
    },
    async sessionById(id) {
      const rows = await sql.query("SELECT * FROM sessions WHERE id = $1", [id]);
      return rows[0] || null;
    },
    async setStatus(id, status) {
      await sql.query("UPDATE sessions SET status = $2 WHERE id = $1", [id, status]);
    },
    async addEvents(id, events) {
      // ON CONFLICT makes retried uploads of the same batch harmless.
      for (const e of events) {
        await sql.query(
          `INSERT INTO events (session_id, seq, t, record) VALUES ($1, $2, $3, $4)
           ON CONFLICT (session_id, seq) DO NOTHING`,
          [id, e.seq, e.t, JSON.stringify(e)],
        );
      }
    },
    async events(id) {
      const rows = await sql.query("SELECT record FROM events WHERE session_id = $1 ORDER BY seq", [id]);
      return rows.map((r) => r.record);
    },
    async listSessions() {
      return sql.query(
        `SELECT s.id, s.volunteer_id, s.status, s.created_at, count(e.seq)::int AS n_events
         FROM sessions s LEFT JOIN events e ON e.session_id = s.id
         GROUP BY s.id ORDER BY s.created_at DESC LIMIT 50`,
      );
    },
    // Sessions run locally (remote_session.py --local), so wiping an
    // abandoned session is implemented for the file store only.
    async deleteSession() {
      throw new Error("Deleting a session is not supported in cloud mode (Neon); delete it in the Neon console.");
    },
  };
}

// ---------------------------------------------------------------- local file (dev only)

function fileStore() {
  const dir = path.join(process.cwd(), ".devdata");
  const file = path.join(dir, "db.json");
  const load = () => (existsSync(file) ? JSON.parse(readFileSync(file, "utf8")) : { sessions: {}, events: {} });
  // Written to a temporary file and renamed over db.json, so a crash mid-write
  // can never leave a truncated file: it holds every local session's timings.
  const save = (db) => {
    mkdirSync(dir, { recursive: true });
    const tmp = `${file}.${process.pid}.tmp`;
    writeFileSync(tmp, JSON.stringify(db, null, 1));
    renameSync(tmp, file);
  };
  return {
    async init() { save(load()); },
    async createSession(s) {
      const db = load();
      db.sessions[s.id] = { ...s, status: "created", created_at: new Date().toISOString() };
      db.events[s.id] = {};
      save(db);
    },
    async sessionByToken(token) { return Object.values(load().sessions).find((s) => s.token === token) || null; },
    async sessionById(id) { return load().sessions[id] || null; },
    // A request that looked the session up just before it was deleted must
    // not bring it back, so writes to a missing session do nothing.
    async setStatus(id, status) {
      const db = load();
      if (!db.sessions[id]) return;
      db.sessions[id].status = status;
      save(db);
    },
    async addEvents(id, events) {
      const db = load();
      if (!db.sessions[id]) return;
      db.events[id] ??= {};
      for (const e of events) db.events[id][e.seq] ??= e;
      save(db);
    },
    // An abandoned session is wiped completely (record and events), as the
    // consent form promises on withdrawal. Returns whether it existed.
    async deleteSession(id) {
      const db = load();
      const existed = Boolean(db.sessions[id]);
      delete db.sessions[id];
      delete db.events[id];
      save(db);
      return existed;
    },
    async events(id) { return Object.values(load().events[id] || {}).sort((a, b) => a.seq - b.seq); },
    async listSessions() {
      const db = load();
      return Object.values(db.sessions).map((s) => ({
        id: s.id, volunteer_id: s.volunteer_id, status: s.status, created_at: s.created_at,
        n_events: Object.keys(db.events[s.id] || {}).length,
      }));
    },
  };
}

let storePromise;
export function store() {
  storePromise ??= process.env.DATABASE_URL ? neonStore(process.env.DATABASE_URL) : Promise.resolve(fileStore());
  return storePromise;
}
