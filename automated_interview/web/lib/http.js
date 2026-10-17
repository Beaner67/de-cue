import { timingSafeEqual } from "node:crypto";

export function send(res, status, body) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(body));
}

// Vercel parses JSON bodies into req.body; the local dev server does the same.
export function body(req) {
  const b = req.body;
  if (b && typeof b === "object") return b;
  try { return b ? JSON.parse(b) : {}; } catch { return {}; }
}

export function query(req) {
  return Object.fromEntries(new URL(req.url, "http://x").searchParams);
}

function same(a, b) {
  const x = Buffer.from(String(a)), y = Buffer.from(String(b));
  return x.length === y.length && timingSafeEqual(x, y);
}

// Admin routes are called only by automated_interview/remote_session.py on the
// researcher's laptop, with ADMIN_KEY from the Vercel project settings.
export function isAdmin(req) {
  const key = process.env.ADMIN_KEY || (process.env.DATABASE_URL ? "" : "dev-admin-key");
  const header = req.headers["authorization"] || "";
  return Boolean(key) && same(header, `Bearer ${key}`);
}
