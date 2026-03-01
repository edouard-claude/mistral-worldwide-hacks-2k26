// Backend API client for Gorafi Simulator (Mistralski)

const BASE_URL = "https://nondeficient-radioluminescent-cherry.ngrok-free.dev";

const HEADERS = {
  "ngrok-skip-browser-warning": "true",
};

export async function fetchApi<T = any>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, { headers: HEADERS });
  if (!res.ok) throw new Error(`API error ${res.status}: ${res.statusText}`);
  return res.json();
}

export interface SSEEvent {
  type: string;
  data: any;
}

/**
 * Stream SSE events via fetch (EventSource doesn't support custom headers).
 * Calls onEvent for each parsed event, onDone when stream ends.
 */
export async function streamSSE(
  path: string,
  onEvent: (evt: SSEEvent) => void,
  onDone?: () => void,
  onError?: (err: Error) => void,
): Promise<void> {
  try {
    const response = await fetch(`${BASE_URL}${path}`, { headers: HEADERS });
    if (!response.ok) {
      throw new Error(`SSE error ${response.status}: ${response.statusText}`);
    }
    if (!response.body) {
      throw new Error("No response body for SSE stream");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let currentEventType = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("event: ")) {
          currentEventType = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
          const raw = line.slice(6);
          try {
            const data = JSON.parse(raw);
            const type = currentEventType || data.type || "unknown";
            onEvent({ type, data: typeof data === "object" && data.type ? data : data });
          } catch {
            // Non-JSON data, wrap as string
            const type = currentEventType || "unknown";
            onEvent({ type, data: raw });
          }
          currentEventType = "";
        }
      }
    }

    onDone?.();
  } catch (err) {
    onError?.(err as Error);
  }
}

// --- API response types ---

export interface BackendAgent {
  id: string;
  name: string;
  health: number;
  energy: number;
  conviction: number;
  selfishness: number;
  status: string;
  alive: boolean;
  opinion: string;
  avatar?: string;
}

export interface BackendIndices {
  credibilite: number;
  rage: number;
  complotisme: number;
  esperance_democratique: number;
}

export interface StartResponse {
  session_id: string;
  turn: number;
  max_turns: number;
  indices: BackendIndices;
  decerebration: number;
  agents: BackendAgent[];
}

export interface NewsProposal {
  real: { text: string; body: string; stat_impact: any };
  fake: { text: string; body: string; stat_impact: any };
  satirical: { text: string; body: string; stat_impact: any };
  gm_commentary: string;
}
