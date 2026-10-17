// The interview app without Vercel. remote_session.py --local runs this and
// shares it through a Cloudflare tunnel; for plain testing:
//   npm run dev            -> http://localhost:3000
// Serves public/ and routes /api/<name> to api/<name>.js, like Vercel does.
// With no DATABASE_URL set, lib/db.js stores everything in .devdata/db.json
// and the admin key is "dev-admin-key".

import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));
const port = Number(process.env.PORT || 3000);
const types = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml",
                ".mp3": "audio/mpeg", ".json": "application/json" };

createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${port}`);
  try {
    const api = url.pathname.match(/^\/api\/([a-z]+)$/);
    if (api) {
      const chunks = [];
      for await (const c of req) chunks.push(c);
      const raw = Buffer.concat(chunks).toString("utf8");
      try { req.body = raw ? JSON.parse(raw) : {}; } catch { req.body = raw; }
      const mod = await import(pathToFileURL(path.join(root, "api", `${api[1]}.js`)).href);
      return await mod.default(req, res);
    }
    const file = path.join(root, "public", url.pathname === "/" ? "index.html" : url.pathname);
    if (!file.startsWith(path.join(root, "public"))) throw Object.assign(new Error(), { code: "ENOENT" });
    const data = await readFile(file);
    const type = types[path.extname(file)] || "application/octet-stream";
    // Byte ranges, as Vercel serves them: browsers need these to seek and
    // replay audio (e.g. "Replay instructions").
    const range = /^bytes=(\d*)-(\d*)$/.exec(req.headers.range || "");
    if (range) {
      const start = range[1] ? Number(range[1]) : Math.max(0, data.length - Number(range[2]));
      const end = range[1] && range[2] ? Math.min(Number(range[2]), data.length - 1) : data.length - 1;
      res.writeHead(206, { "Content-Type": type, "Accept-Ranges": "bytes", "Content-Range": `bytes ${start}-${end}/${data.length}`, "Content-Length": end - start + 1 });
      return res.end(data.subarray(start, end + 1));
    }
    res.writeHead(200, { "Content-Type": type, "Accept-Ranges": "bytes", "Content-Length": data.length });
    res.end(data);
  } catch (e) {
    // With remote_session.py --local this server is public through a tunnel,
    // so errors go to the console, not to the visitor.
    if (e.code !== "ENOENT") console.error(e);
    res.writeHead(e.code === "ENOENT" ? 404 : 500, { "Content-Type": "text/plain" });
    res.end(e.code === "ENOENT" ? "Not found" : "Server error");
  }
}).listen(port, () => console.log(`Dev server: http://localhost:${port}/  (admin key: dev-admin-key)`));
