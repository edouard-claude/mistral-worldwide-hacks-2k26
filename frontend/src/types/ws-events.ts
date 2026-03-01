// WebSocket event types for Gorafi Simulator
// This file centralizes all types used by GameProvider and gameReducer

import type { Lang } from "@/i18n/translations";

// ============================================================================
// Turn Phases
// ============================================================================

export type TurnPhase =
  | "loading"
  | "select_news"
  | "proposing"
  | "debating"
  | "resolving"
  | "results"
  | "error";

// ============================================================================
// GM Types (from useBackendEngine)
// ============================================================================

export interface GmAgentVision {
  agent_id: string;
  content: string;
}

export interface GmStrategy {
  analysis: string;
  threat_agents: string[];
  weak_spots: string[];
  next_turn_plan: string;
  long_term_goal: string;
}

export interface GmTerminalLine {
  id: number;
  type:
    | "separator"
    | "phase"
    | "llm_call"
    | "tool_call"
    | "tool_result"
    | "llm_text"
    | "vision_update"
    | "choice_resolved"
    | "strategy"
    | "info";
  text: string;
  agentId?: string;
}

// ============================================================================
// Fallen Agent (graveyard)
// ============================================================================

export interface FallenAgent {
  agent: {
    id: string;
    name: string;
    avatar: string;
    health: number;
    conviction: number;
    selfishness: number;
    status: string;
    alive: boolean;
    opinion: string;
  };
  killedBy: string;
  turn: number;
  newsTitle: string;
  epitaph: string;
}

// ============================================================================
// Turn Result
// ============================================================================

export interface TurnResult {
  winner: { id: string; name: string };
  loser: { id: string; name: string };
  clone: { id: string; name: string };
  chaosDelta: number;
  creduliteDelta: number;
  ranking: string[];
}

// ============================================================================
// WebSocket Connection Status
// ============================================================================

export type WsStatus = "disconnected" | "connecting" | "connected" | "reconnecting" | "error";

// ============================================================================
// Loading States
// ============================================================================

export interface LoadingState {
  agents: boolean;
  news: boolean;
  images: boolean;
  debate: boolean;
}

// ============================================================================
// Base WebSocket Event
// ============================================================================

export interface WsEvent<T = unknown> {
  event: string;
  data: T;
}

// ============================================================================
// GM Event Payloads (gm.*)
// ============================================================================

export interface GmPhasePayload {
  phase: string;
}

export interface GmLlmCallPayload {
  turn_idx?: number;
}

export interface GmToolCallPayload {
  tool?: string;
  args?: Record<string, unknown>;
}

export interface GmToolResultPayload {
  result?: string;
}

export interface GmProposalPayload {
  real: { text: string; body: string; stat_impact: Record<string, number> };
  fake: { text: string; body: string; stat_impact: Record<string, number> };
  satirical: { text: string; body: string; stat_impact: Record<string, number> };
  gm_commentary: string;
}

export interface GmImagesPayload {
  real?: string;
  fake?: string;
  satirical?: string;
}

export interface GmChoiceResolvedPayload {
  gm_reaction?: string;
}

export interface GmReactionsPayload {
  reactions?: string;
}

export interface GmStrategyPayload {
  analysis?: string;
  threat_agents?: string[];
  weak_spots?: string[];
  next_turn_plan?: string;
  long_term_goal?: string;
}

export interface GmTurnUpdatePayload {
  turn?: number;
  max_turns?: number;
}

export interface GmIndicesPayload {
  indices?: {
    credibilite: number;
    rage: number;
    complotisme: number;
    esperance_democratique: number;
  };
  decerebration?: number;
}

export interface GmErrorPayload {
  message?: string;
  error?: string;
}

// ============================================================================
// Arena Event Payloads (arena.*)
// ============================================================================

export interface ArenaRoundStartPayload {
  round: number;
  fake_news: string;
  context?: string;
}

export interface ArenaPhaseStartPayload {
  round: number;
  phase: string;
}

export interface ArenaAgentStatusPayload {
  agent_id: string;
  state: string;
  detail?: string;
}

export interface ArenaDeathPayload {
  agent_id: string;
  agent_name: string;
  round: number;
  cause?: string;
  killer?: string;
  epitaph?: string;
}

export interface ArenaClonePayload {
  parent_id: string;
  child_id: string;
  child_name: string;
  round: number;
}

export interface ArenaEndPayload {
  survivors: string[];
  history: unknown;
}

// Swarm Agent (from Go swarm via state.global)
export interface SwarmAgent {
  id: string;
  name: string;
  political_color: number;  // 0.0-1.0
  temperature: number;      // 0.0-1.0
  confidence: number;       // 1-5
  alive: boolean;
  parent_id?: string;
  born_at_round: number;
  avatar_url?: string;      // injected by relay
}

export interface ArenaGlobalStatePayload {
  session_id: string;
  round: number;
  phase: number;
  agents: SwarmAgent[];
  graveyard?: SwarmAgent[];
  scores?: Record<string, number>;
}

export interface ArenaWaitingPayload {
  round: number;
  waiting: boolean;
}

// ============================================================================
// Agent NATS message (from arena)
// ============================================================================

export interface AgentNatsPayload {
  agent_id?: string;
  agent_name?: string;
  take?: string;
  phase?: number;
}

// ============================================================================
// Reducer Action Types
// ============================================================================

export type GameAction =
  // Connection
  | { type: "WS_CONNECTING" }
  | { type: "WS_CONNECTED" }
  | { type: "WS_DISCONNECTED" }
  | { type: "WS_RECONNECTING"; attempt: number }
  | { type: "WS_ERROR"; error: string }
  // Session
  | { type: "SESSION_START"; sessionId: string; agents: BackendAgent[]; indices: BackendIndices; turn: number; maxTurns: number }
  | { type: "SET_LANG"; lang: Lang }
  // GM Events
  | { type: "GM_PHASE"; payload: GmPhasePayload }
  | { type: "GM_LLM_CALL"; payload: GmLlmCallPayload }
  | { type: "GM_TOOL_CALL"; payload: GmToolCallPayload }
  | { type: "GM_TOOL_RESULT"; payload: GmToolResultPayload }
  | { type: "GM_PROPOSAL"; payload: GmProposalPayload }
  | { type: "GM_IMAGES"; payload: GmImagesPayload }
  | { type: "GM_CHOICE_RESOLVED"; payload: GmChoiceResolvedPayload }
  | { type: "GM_REACTIONS"; payload: GmReactionsPayload }
  | { type: "GM_STRATEGY"; payload: GmStrategyPayload }
  | { type: "GM_TURN_UPDATE"; payload: GmTurnUpdatePayload }
  | { type: "GM_INDICES"; payload: GmIndicesPayload }
  | { type: "GM_END" }
  | { type: "GM_ERROR"; payload: GmErrorPayload }
  // Arena Events
  | { type: "ARENA_ROUND_START"; payload: ArenaRoundStartPayload }
  | { type: "ARENA_PHASE_START"; payload: ArenaPhaseStartPayload }
  | { type: "ARENA_AGENT_STATUS"; payload: ArenaAgentStatusPayload }
  | { type: "ARENA_DEATH"; payload: ArenaDeathPayload }
  | { type: "ARENA_CLONE"; payload: ArenaClonePayload }
  | { type: "ARENA_END"; payload: ArenaEndPayload }
  | { type: "ARENA_WAITING"; payload: ArenaWaitingPayload }
  | { type: "ARENA_GLOBAL_STATE"; payload: ArenaGlobalStatePayload }
  // Agent message
  | { type: "AGENT_NATS"; payload: AgentNatsPayload }
  // UI Actions
  | { type: "SELECT_NEWS"; missionId: string }
  | { type: "SET_TURN_PHASE"; phase: TurnPhase }
  | { type: "ADD_TERMINAL_LINE"; line: Omit<GmTerminalLine, "id"> }
  | { type: "CLEAR_TERMINAL" }
  | { type: "DISMISS_CHAOS_EVENT" }
  | { type: "SET_TURN_TRANSITION"; active: boolean }
  | { type: "TRIGGER_NEXT_TURN" }
  | { type: "SET_NEEDS_PROPOSE"; value: boolean }
  | { type: "CLEAR_NEEDS_PROPOSE" }
  | { type: "RESET_GAME" };

// ============================================================================
// Backend API Types (re-exported for convenience)
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
