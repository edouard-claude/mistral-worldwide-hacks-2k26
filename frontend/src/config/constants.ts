// Backend URLs — configurable via env vars (Vite)
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8899";
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || "ws://localhost:8899";

// Headers for ngrok (skip browser warning)
export const API_HEADERS = {
  "ngrok-skip-browser-warning": "true",
};
