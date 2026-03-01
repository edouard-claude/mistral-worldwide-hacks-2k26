/**
 * Data loader with caching.
 * Fetches sessions.json index and individual session JSONs.
 */
const cache = {};

export async function loadSessionIndex() {
  if (cache._index) return cache._index;
  const res = await fetch('data/sessions.json');
  cache._index = await res.json();
  return cache._index;
}

export async function loadSession(sessionId) {
  if (cache[sessionId]) return cache[sessionId];
  const res = await fetch(`data/${sessionId}.json`);
  cache[sessionId] = await res.json();
  return cache[sessionId];
}
