#!/usr/bin/env node
/**
 * Static file server with periodic session preprocessing.
 * - Runs preprocess.mjs on startup and every REFRESH_INTERVAL seconds
 * - Serves static files (HTML, CSS, JS, JSON)
 */
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { join, extname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = join(fileURLToPath(import.meta.url), '..');
const PORT = parseInt(process.env.PORT || '3000', 10);
const REFRESH_INTERVAL = parseInt(process.env.REFRESH_INTERVAL || '30', 10);

const MIME = {
  '.html': 'text/html',
  '.css': 'text/css',
  '.js': 'application/javascript',
  '.mjs': 'application/javascript',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
};

// ─── Preprocessing ──────────────────────────────────────────────────────────

async function runPreprocess() {
  try {
    const { main } = await import(pathToFileURL(join(ROOT, 'preprocess.mjs')).href);
    await main();
    console.log(`[preprocess] Done at ${new Date().toISOString()}`);
  } catch (err) {
    console.error('[preprocess] Error:', err.message);
  }
}

// ─── Static file server ─────────────────────────────────────────────────────

async function serve(req, res) {
  // Manual refresh endpoint
  if (req.url === '/refresh') {
    await runPreprocess();
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: true }));
    return;
  }

  let urlPath = req.url.split('?')[0];
  if (urlPath === '/') urlPath = '/index.html';

  const filePath = join(ROOT, urlPath);

  // Prevent directory traversal
  if (!filePath.startsWith(ROOT)) {
    res.writeHead(403);
    res.end('Forbidden');
    return;
  }

  try {
    const fileStat = await stat(filePath);
    if (!fileStat.isFile()) throw new Error('Not a file');

    const ext = extname(filePath);
    const mime = MIME[ext] || 'application/octet-stream';
    const data = await readFile(filePath);

    res.writeHead(200, { 'Content-Type': mime });
    res.end(data);
  } catch {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('Not found');
  }
}

// ─── Main ────────────────────────────────────────────────────────────────────

console.log(`[server] Sessions dir: ${process.env.SESSIONS_DIR || 'examples/ (default)'}`);
console.log(`[server] Refresh interval: ${REFRESH_INTERVAL}s`);

// Initial preprocessing
await runPreprocess();

// Periodic refresh
setInterval(runPreprocess, REFRESH_INTERVAL * 1000);

// Start server
const server = createServer(serve);
server.listen(PORT, '0.0.0.0', () => {
  console.log(`[server] Listening on http://0.0.0.0:${PORT}`);
});
