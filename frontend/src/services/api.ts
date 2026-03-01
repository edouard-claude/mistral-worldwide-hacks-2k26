// Backend API client for Gorafi Simulator (Mistralski)
// REST-only client — WebSocket events are handled by GameProvider

import { API_BASE_URL, API_HEADERS } from "@/config/constants";
import type { Lang } from "@/i18n/translations";

const BASE_URL = API_BASE_URL;
const HEADERS = API_HEADERS;

// ============================================================================
// Generic Fetch
// ============================================================================

export async function fetchApi<T = unknown>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, { headers: HEADERS });
  if (!res.ok) throw new Error(`API error ${res.status}: ${res.statusText}`);
  return res.json();
}

// ============================================================================
// REST Triggers (return 202, events come via WebSocket)
// ============================================================================

/**
 * Trigger proposal generation — returns 202, events arrive via WS
 */
export async function triggerPropose(sessionId: string, lang: Lang): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/propose?session_id=${sessionId}&lang=${lang}`, {
    headers: HEADERS,
  });
  if (!res.ok && res.status !== 202) {
    throw new Error(`Propose error ${res.status}: ${res.statusText}`);
  }
}

/**
 * Trigger news choice resolution — returns 202, events arrive via WS
 */
export async function triggerChoose(
  sessionId: string,
  kind: "real" | "fake" | "satirical",
  lang: Lang
): Promise<void> {
  const res = await fetch(
    `${BASE_URL}/api/choose?session_id=${sessionId}&kind=${kind}&lang=${lang}`,
    { headers: HEADERS }
  );
  if (!res.ok && res.status !== 202) {
    throw new Error(`Choose error ${res.status}: ${res.statusText}`);
  }
}

// ============================================================================
// API Response Types
// ============================================================================

export interface BackendAgent {
  // Backend may send either id or agent_id
  id?: string;
  agent_id?: string;
  name: string;
  // Direct stats (from swarm) or nested stats object (from mistralski)
  health?: number;
  energy?: number;
  conviction?: number;
  selfishness?: number;
  stats?: {
    croyance?: number;
    confiance?: number;
    richesse?: number;
  };
  status?: string;
  status_text?: string;
  personality?: string;
  alive?: boolean;
  is_neutralized?: boolean;
  opinion?: string;
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
  real: { text: string; body: string; stat_impact: Record<string, number> };
  fake: { text: string; body: string; stat_impact: Record<string, number> };
  satirical: { text: string; body: string; stat_impact: Record<string, number> };
  gm_commentary: string;
}
