// Backend URLs — configurable via env vars (Vite)
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://wh26-backend.wh26.edouard.cl";
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || "wss://wh26-backend.wh26.edouard.cl";

// Headers for ngrok (skip browser warning)
export const API_HEADERS = {
  "ngrok-skip-browser-warning": "true",
};
