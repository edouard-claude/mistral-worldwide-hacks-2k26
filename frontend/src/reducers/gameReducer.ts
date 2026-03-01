// Game state reducer for Gorafi Simulator
// Pure function that maps WS events and actions to state changes

import type { Agent, DebateLine, GameState, NewsMission } from "@/data/gameData";
import { politicalSpectrum as initialSpectrum } from "@/data/gameData";
import type { ChaosEvent } from "@/data/chaosEvents";
import { checkChaosEvent } from "@/data/chaosEvents";
import type { Lang } from "@/i18n/translations";
import { API_BASE_URL } from "@/config/constants";
import type {
  TurnPhase,
  WsStatus,
  LoadingState,
  GmAgentVision,
  GmStrategy,
  GmTerminalLine,
  FallenAgent,
  TurnResult,
  GameAction,
  BackendAgent,
  BackendIndices,
  SwarmAgent,
} from "@/types/ws-events";

// ============================================================================
// Full Game State
// ============================================================================

export interface FullGameState {
  // Connection
  wsStatus: WsStatus;
  sessionId: string;
  reconnectAttempt: number;

  // Language
  lang: Lang;

  // Game indices
  gameState: GameState;

  // Agents
  liveAgents: Agent[];
  fallenAgents: FallenAgent[];

  // News
  missions: NewsMission[];
  selectedMission: NewsMission | null;

  // Debate
  debateLines: DebateLine[];

  // Turn
  turnPhase: TurnPhase;
  turnResult: TurnResult | null;
  turnTransition: boolean;

  // Political spectrum (visual)
  politicalSpectrum: { label: string; value: number; color: string }[];

  // GM Terminal
  gmTerminalLines: GmTerminalLine[];
  gmVisions: Record<string, GmAgentVision>;
  gmStrategy: GmStrategy | null;
  gmCommentary: string;

  // UI state
  gameOver: boolean;
  pendingChaosEvent: ChaosEvent | null;
  errorMessage: string;
  isStreaming: boolean;

  // Loading states
  loading: LoadingState;

  // Internal
  lineIdCounter: number;
  needsPropose: boolean;
}

// ============================================================================
// Initial State
// ============================================================================

export const initialGameState: FullGameState = {
  // Connection
  wsStatus: "disconnected",
  sessionId: "",
  reconnectAttempt: 0,

  // Language
  lang: "fr",

  // Game indices
  gameState: {
    turn: 1,
    maxTurns: 10,
    indiceMondial: 0,
    chaosIndex: 0,
    chaosLabel: "Calme suspect",
    creduliteIndex: 0,
    creduliteLabel: "Sceptiques aguerris",
  },

  // Agents
  liveAgents: [],
  fallenAgents: [],

  // News
  missions: [],
  selectedMission: null,

  // Debate
  debateLines: [],

  // Turn
  turnPhase: "loading",
  turnResult: null,
  turnTransition: false,

  // Political spectrum
  politicalSpectrum: initialSpectrum.map(p => ({ ...p })),

  // GM Terminal
  gmTerminalLines: [],
  gmVisions: {},
  gmStrategy: null,
  gmCommentary: "",

  // UI state
  gameOver: false,
  pendingChaosEvent: null,
  errorMessage: "",
  isStreaming: false,

  // Loading states
  loading: {
    agents: true,
    news: true,
    images: true,
    debate: false,
  },

  // Internal
  lineIdCounter: 0,
  needsPropose: false,
};

// ============================================================================
// Helper Functions
// ============================================================================

function clamp(v: number, min = 0, max = 100): number {
  return Math.max(min, Math.min(max, v));
}

const chaosLabels: Record<Lang, { max: number; label: string }[]> = {
  fr: [
    { max: 20, label: "Calme suspect" },
    { max: 40, label: "Rumeurs dans les couloirs" },
    { max: 60, label: "Manifestations sporadiques" },
    { max: 80, label: "Ronds-points en feu" },
    { max: 100, label: "ANARCHIE TOTALE" },
  ],
  en: [
    { max: 20, label: "Suspicious calm" },
    { max: 40, label: "Hallway rumors" },
    { max: 60, label: "Sporadic protests" },
    { max: 80, label: "Roundabouts on fire" },
    { max: 100, label: "TOTAL ANARCHY" },
  ],
};

const creduliteLabels: Record<Lang, { max: number; label: string }[]> = {
  fr: [
    { max: 20, label: "Sceptiques aguerris" },
    { max: 40, label: "Vérifient les sources" },
    { max: 60, label: "Partagent sans lire" },
    { max: 80, label: "Gobent tout" },
    { max: 100, label: "LA VÉRITÉ N'EXISTE PLUS" },
  ],
  en: [
    { max: 20, label: "Hardened skeptics" },
    { max: 40, label: "Check their sources" },
    { max: 60, label: "Share without reading" },
    { max: 80, label: "Swallow everything" },
    { max: 100, label: "TRUTH NO LONGER EXISTS" },
  ],
};

function getLabel(value: number, labels: { max: number; label: string }[]): string {
  return labels.find(l => value <= l.max)?.label ?? labels[labels.length - 1].label;
}

function mapAgent(ba: BackendAgent): Agent {
  // Backend sends agent_id, stats.croyance, stats.confiance, etc.
  const stats = (ba as any).stats || {};
  return {
    id: ba.id || (ba as any).agent_id || "",
    name: ba.name,
    avatar: ba.avatar || "🤖",
    health: ba.health ?? stats.confiance ?? 75,
    conviction: ba.conviction ?? stats.croyance ?? 70,
    selfishness: ba.selfishness ?? stats.richesse ?? 50,
    status: ba.status || (ba as any).status_text || (ba as any).personality || ba.name,
    alive: ba.alive !== false && !(ba as any).is_neutralized,
    opinion: ba.opinion || (ba as any).personality || "",
  };
}

function mapSwarmAgent(sa: SwarmAgent): Agent {
  return {
    id: sa.id,
    name: sa.name,
    avatar: sa.avatar_url || "🤖",
    health: clamp(sa.confidence * 20, 0, 100),          // 1-5 → 20-100, clamped
    conviction: clamp(Math.round(sa.political_color * 100)),  // 0.0-1.0 → 0-100
    selfishness: clamp(Math.round(sa.temperature * 100)),     // 0.0-1.0 → 0-100
    status: sa.parent_id ? "Clone" : sa.name,
    alive: sa.alive,
    opinion: "",
  };
}

function mapIndices(
  indices: BackendIndices,
  decerebration: number,
  turn: number,
  maxTurns: number,
  lang: Lang
): GameState {
  const chaosIndex = clamp(indices.rage ?? 15);
  const creduliteIndex = clamp(100 - (indices.credibilite ?? 80));
  const indiceMondial = clamp(Math.round(decerebration ?? 15));
  return {
    turn,
    maxTurns,
    indiceMondial,
    chaosIndex,
    chaosLabel: getLabel(chaosIndex, chaosLabels[lang]),
    creduliteIndex,
    creduliteLabel: getLabel(creduliteIndex, creduliteLabels[lang]),
  };
}

// News image pool (cycled through)
const newsImages = ["news1", "news2", "news3", "news4", "news5", "news6", "news7", "news8", "news9"];
let newsImageIdx = 0;
function nextNewsImage(): string {
  const img = newsImages[newsImageIdx % newsImages.length];
  newsImageIdx++;
  return img;
}

function addTerminalLine(state: FullGameState, type: GmTerminalLine["type"], text: string): FullGameState {
  const newLine: GmTerminalLine = {
    id: state.lineIdCounter,
    type,
    text,
  };
  return {
    ...state,
    gmTerminalLines: [...state.gmTerminalLines, newLine],
    lineIdCounter: state.lineIdCounter + 1,
  };
}

// ============================================================================
// Reducer
// ============================================================================

export function gameReducer(state: FullGameState, action: GameAction): FullGameState {
  switch (action.type) {
    // ========================================================================
    // WebSocket Connection
    // ========================================================================

    case "WS_CONNECTING":
      return { ...state, wsStatus: "connecting" };

    case "WS_CONNECTED":
      return { ...state, wsStatus: "connected", reconnectAttempt: 0 };

    case "WS_DISCONNECTED":
      return { ...state, wsStatus: "disconnected", isStreaming: false, needsPropose: false };

    case "WS_RECONNECTING":
      return { ...state, wsStatus: "reconnecting", reconnectAttempt: action.attempt };

    case "WS_ERROR":
      return { ...state, wsStatus: "error", errorMessage: action.error };

    // ========================================================================
    // Session Start
    // ========================================================================

    case "SESSION_START": {
      newsImageIdx = 0; // Reset image counter
      // agents may be empty array - real agents come from state.global
      const agents = Array.isArray(action.agents) ? action.agents.map(mapAgent) : [];
      const indices = mapIndices(
        { ...action.indices, rage: 0, credibilite: 100 },
        0,
        action.turn,
        action.maxTurns,
        state.lang
      );
      return {
        ...initialGameState,
        wsStatus: state.wsStatus,
        sessionId: action.sessionId,
        lang: state.lang,
        liveAgents: agents,
        gameState: indices,
        turnPhase: "proposing",
        loading: { agents: true, news: true, images: true, debate: false },
        isStreaming: true,
        needsPropose: true,
      };
    }

    case "SET_LANG":
      return { ...state, lang: action.lang };

    // ========================================================================
    // GM Events
    // ========================================================================

    case "GM_PHASE":
      return addTerminalLine(state, "phase", `>> ${action.payload.phase}`);

    case "GM_LLM_CALL": {
      const turnIdx = (action.payload.turn_idx ?? 0) + 1;
      const text = state.lang === "fr" ? `Appel LLM #${turnIdx}` : `LLM Call #${turnIdx}`;
      return addTerminalLine(state, "llm_call", text);
    }

    case "GM_TOOL_CALL": {
      const tool = action.payload.tool || "?";
      const args = JSON.stringify(action.payload.args || {}).slice(0, 80);
      return addTerminalLine(state, "tool_call", `TOOL: ${tool}(${args})`);
    }

    case "GM_TOOL_RESULT": {
      const result = String(action.payload.result || action.payload).slice(0, 200);
      return addTerminalLine(state, "tool_result", result);
    }

    case "GM_PROPOSAL": {
      const proposal = action.payload;
      const kinds: Array<{ key: "real" | "fake" | "satirical" }> = [
        { key: "real" },
        { key: "fake" },
        { key: "satirical" },
      ];

      const newMissions: NewsMission[] = kinds.map(k => {
        const news = proposal[k.key];
        const impact = news.stat_impact || {};
        const impactParts: string[] = [];
        if (impact.rage) impactParts.push(`Chaos ${impact.rage > 0 ? "+" : ""}${impact.rage}`);
        if (impact.credibilite) impactParts.push(`Créd ${impact.credibilite > 0 ? "+" : ""}${impact.credibilite}`);
        const impactLabel = impactParts.join(" · ") || k.key;

        return {
          id: k.key,
          title: news.text,
          description: news.body.split("\n\n")[0] || news.body.slice(0, 200),
          articleText: news.body,
          image: nextNewsImage(),
          backendImage: undefined,
          chaosImpact: impactLabel,
          statImpact: impact,
          selected: false,
          inProgress: false,
          voiceActive: true,
        };
      });

      // Determine GM's recommended pick (highest chaos potential)
      let bestIdx = 0;
      let bestScore = -Infinity;
      newMissions.forEach((m, i) => {
        const imp = m.statImpact || {};
        const score = (imp.rage || 0) - (imp.credibilite || 0) + (imp.complotisme || 0);
        if (score > bestScore) {
          bestScore = score;
          bestIdx = i;
        }
      });
      newMissions[bestIdx].recommended = true;

      const text = state.lang === "fr" ? "Proposition reçue" : "Proposal received";
      const updated = addTerminalLine(state, "info", `${text} — ${proposal.gm_commentary || ""}`);

      return {
        ...updated,
        missions: newMissions,
        gmCommentary: proposal.gm_commentary || "",
        turnPhase: "select_news",
        isStreaming: false,
        loading: { ...state.loading, news: false },
      };
    }

    case "GM_IMAGES": {
      const imgData = action.payload;
      const BASE = API_BASE_URL;

      const updatedMissions = state.missions.map(m => {
        const url = imgData[m.id as keyof typeof imgData];
        if (url) {
          return { ...m, backendImage: `${BASE}${url}` };
        }
        return m;
      });

      let updatedSelected = state.selectedMission;
      if (updatedSelected) {
        const url = imgData[updatedSelected.id as keyof typeof imgData];
        if (url) {
          updatedSelected = { ...updatedSelected, backendImage: `${BASE}${url}` };
        }
      }

      return {
        ...state,
        missions: updatedMissions,
        selectedMission: updatedSelected,
        loading: { ...state.loading, images: false },
      };
    }

    case "GM_CHOICE_RESOLVED": {
      const msg = action.payload.gm_reaction || (state.lang === "fr" ? "Choix validé" : "Choice validated");
      const updated = addTerminalLine(state, "choice_resolved", `GM: ${msg}`);
      const newLine: DebateLine = {
        agent: "MISTRALSKI",
        message: msg,
        type: "argument",
      };
      return {
        ...updated,
        debateLines: [...state.debateLines, newLine],
      };
    }

    case "GM_REACTIONS": {
      if (!action.payload.reactions) return state;
      const newLine: DebateLine = {
        agent: "SYSTÈME",
        message: action.payload.reactions,
        type: "reaction",
      };
      return {
        ...state,
        debateLines: [...state.debateLines, newLine],
      };
    }

    case "GM_STRATEGY": {
      const s = action.payload;
      const text = s.analysis || s.next_turn_plan || "";
      const updated = addTerminalLine(state, "strategy", `STRATÉGIE: ${text}`);
      return {
        ...updated,
        gmCommentary: text,
        gmStrategy: {
          analysis: s.analysis || "",
          threat_agents: s.threat_agents || [],
          weak_spots: s.weak_spots || [],
          next_turn_plan: s.next_turn_plan || "",
          long_term_goal: s.long_term_goal || "",
        },
      };
    }

    case "GM_TURN_UPDATE":
      return {
        ...state,
        gameState: {
          ...state.gameState,
          turn: action.payload.turn ?? state.gameState.turn,
          maxTurns: action.payload.max_turns ?? state.gameState.maxTurns,
        },
      };

    case "GM_INDICES": {
      if (!action.payload.indices) return state;
      const oldChaos = state.gameState.chaosIndex;
      const newGameState = mapIndices(
        action.payload.indices,
        action.payload.decerebration ?? state.gameState.indiceMondial,
        state.gameState.turn,
        state.gameState.maxTurns,
        state.lang
      );
      const chaosEvt = checkChaosEvent(oldChaos, newGameState.chaosIndex);
      return {
        ...state,
        gameState: newGameState,
        pendingChaosEvent: chaosEvt || state.pendingChaosEvent,
      };
    }

    case "GM_END":
      return { ...state, gameOver: true, isStreaming: false };

    case "GM_ERROR": {
      const msg = action.payload.message || action.payload.error || "Unknown error";
      return {
        ...state,
        errorMessage: msg,
        turnPhase: "error",
        isStreaming: false,
      };
    }

    // ========================================================================
    // Arena Events
    // ========================================================================

    case "ARENA_ROUND_START": {
      const text = state.lang === "fr"
        ? `Round ${action.payload.round} — ${action.payload.fake_news}`
        : `Round ${action.payload.round} — ${action.payload.fake_news}`;
      return addTerminalLine(state, "info", text);
    }

    case "ARENA_PHASE_START": {
      const text = `Phase ${action.payload.phase} (Round ${action.payload.round})`;
      return addTerminalLine(state, "phase", text);
    }

    case "ARENA_AGENT_STATUS": {
      // Update agent status in liveAgents
      const updatedAgents = state.liveAgents.map(a => {
        if (a.id === action.payload.agent_id || a.name === action.payload.agent_id) {
          return { ...a, status: action.payload.detail || action.payload.state };
        }
        return a;
      });
      return { ...state, liveAgents: updatedAgents };
    }

    case "ARENA_DEATH": {
      const deadAgentId = action.payload.agent_id;
      const deadAgent = state.liveAgents.find(a => a.id === deadAgentId || a.name === deadAgentId);

      const label = state.lang === "fr" ? "éliminé" : "eliminated";
      const newLine: DebateLine = {
        agent: "SYSTÈME",
        message: `☠ ${action.payload.agent_name || deadAgentId} ${label}`,
        type: "attack",
      };

      const fallen: FallenAgent = {
        agent: deadAgent || {
          id: deadAgentId,
          name: action.payload.agent_name || deadAgentId,
          avatar: "💀",
          health: 0,
          conviction: 0,
          selfishness: 0,
          status: "ÉLIMINÉ",
          alive: false,
          opinion: "",
        },
        killedBy: action.payload.killer || "le collectif",
        turn: action.payload.round,
        newsTitle: state.selectedMission?.title ?? "",
        epitaph: action.payload.epitaph || `${action.payload.agent_name} est tombé au combat.`,
      };

      return {
        ...state,
        liveAgents: state.liveAgents.filter(a => a.id !== deadAgentId && a.name !== deadAgentId),
        fallenAgents: [...state.fallenAgents, fallen],
        debateLines: [...state.debateLines, newLine],
      };
    }

    case "ARENA_CLONE": {
      const label = state.lang === "fr" ? "rejoint le débat" : "joins the debate";
      const newLine: DebateLine = {
        agent: "SYSTÈME",
        message: `🧬 ${action.payload.child_name} ${label}`,
        type: "reaction",
      };

      // Find parent agent to inherit stats (will be corrected by next state.global)
      const parent = state.liveAgents.find(a => a.id === action.payload.parent_id);
      if (!parent) {
        console.warn(`[ARENA_CLONE] Parent agent ${action.payload.parent_id} not found, using defaults`);
      }
      const newAgent: Agent = {
        id: action.payload.child_id,
        name: action.payload.child_name,
        avatar: parent?.avatar || "🧬",
        health: parent?.health || 75,
        conviction: parent?.conviction || 70,
        selfishness: parent?.selfishness || 50,
        status: "Clone",
        alive: true,
        opinion: "",
      };

      return {
        ...state,
        liveAgents: [...state.liveAgents, newAgent],
        debateLines: [...state.debateLines, newLine],
      };
    }

    case "ARENA_END": {
      const text = state.lang === "fr" ? "Fin du round" : "Round ended";
      return addTerminalLine(state, "info", text);
    }

    case "ARENA_WAITING": {
      const text = state.lang === "fr"
        ? `En attente de nouvelle news (round ${action.payload.round})`
        : `Waiting for new news (round ${action.payload.round})`;
      const updated = addTerminalLine(state, "info", text);
      return {
        ...updated,
        turnPhase: "results",
        turnTransition: true,
        needsPropose: true,
      };
    }

    case "ARENA_GLOBAL_STATE": {
      // Replace all agents with swarm agents
      // Defensive: payload may be nested in data or have different structure
      const agents = action.payload.agents || (action.payload as any).data?.agents;
      if (!agents || !Array.isArray(agents)) {
        console.warn("[ARENA_GLOBAL_STATE] Invalid payload, no agents array:", action.payload);
        return state;
      }
      const swarmAgents = agents.map(mapSwarmAgent);
      return {
        ...state,
        liveAgents: swarmAgents,
        loading: { ...state.loading, agents: false },
      };
    }

    // ========================================================================
    // Agent Message (from NATS)
    // ========================================================================

    case "AGENT_NATS": {
      // Use agent_name from payload (from swarm AgentMessage), fallback to agent_id
      const agentName = action.payload.agent_name || action.payload.agent_id || "AGENT";
      const message = action.payload.take || "...";

      // Determine line type based on phase
      const phase = action.payload.phase;
      let lineType: DebateLine["type"] = "argument";
      if (phase === 1) lineType = "reaction"; // cogitation
      if (phase === 3) lineType = "defense"; // revision
      if (phase === 4) lineType = "attack"; // vote

      const newLine: DebateLine = {
        agent: agentName,
        message,
        type: lineType,
      };

      // Also update agent opinion in liveAgents
      const updatedAgents = state.liveAgents.map(a => {
        if (a.id === action.payload.agent_id || a.name === action.payload.agent_name) {
          return { ...a, opinion: message.slice(0, 150) };
        }
        return a;
      });

      return {
        ...state,
        liveAgents: updatedAgents,
        debateLines: [...state.debateLines, newLine],
        loading: { ...state.loading, debate: false },
      };
    }

    // ========================================================================
    // UI Actions
    // ========================================================================

    case "SELECT_NEWS": {
      const mission = state.missions.find(m => m.id === action.missionId);
      if (!mission || state.turnPhase !== "select_news") return state;

      const updatedMissions = state.missions.map(m => ({
        ...m,
        inProgress: m.id === action.missionId,
        selected: m.id === action.missionId,
      }));

      return {
        ...state,
        missions: updatedMissions,
        selectedMission: mission,
        turnPhase: "debating",
        debateLines: [],
        isStreaming: true,
        loading: { ...state.loading, debate: true },
      };
    }

    case "SET_TURN_PHASE":
      return { ...state, turnPhase: action.phase };

    case "ADD_TERMINAL_LINE": {
      const newLine: GmTerminalLine = {
        id: state.lineIdCounter,
        type: action.line.type,
        text: action.line.text,
      };
      return {
        ...state,
        gmTerminalLines: [...state.gmTerminalLines, newLine],
        lineIdCounter: state.lineIdCounter + 1,
      };
    }

    case "CLEAR_TERMINAL":
      return { ...state, gmTerminalLines: [], lineIdCounter: 0 };

    case "DISMISS_CHAOS_EVENT":
      return { ...state, pendingChaosEvent: null };

    case "SET_TURN_TRANSITION":
      return { ...state, turnTransition: action.active };

    case "TRIGGER_NEXT_TURN":
      // Note: needsPropose stays false here — the UI action sets it via separate dispatch
      return {
        ...state,
        turnTransition: false,
        turnPhase: "proposing",
        missions: [],
        selectedMission: null,
        debateLines: [],
        turnResult: null,
        isStreaming: true,
        loading: { agents: false, news: true, images: true, debate: false },
      };

    case "SET_NEEDS_PROPOSE":
      return { ...state, needsPropose: action.value };

    case "CLEAR_NEEDS_PROPOSE":
      return { ...state, needsPropose: false };

    case "RESET_GAME":
      return {
        ...initialGameState,
        lang: state.lang,
        wsStatus: state.wsStatus,
      };

    default:
      return state;
  }
}
