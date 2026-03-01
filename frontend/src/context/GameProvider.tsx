// GameProvider — React Context with WebSocket connection management
// Replaces useBackendEngine with a cleaner architecture

import React, { useReducer, useEffect, useRef, useCallback, useMemo } from "react";
import { gameReducer, initialGameState } from "@/reducers/gameReducer";
import type { GameAction } from "@/types/ws-events";
import { fetchApi, triggerPropose, triggerChoose, type StartResponse } from "@/services/api";
import { API_BASE_URL, WS_BASE_URL } from "@/config/constants";
import { tr, type Lang } from "@/i18n/translations";
import { GameContext, type GameActions, type GameContextValue } from "./GameContext";

// Re-export types and context for backward compatibility
export { GameContext, type GameActions, type GameContextValue } from "./GameContext";

// ============================================================================
// Provider
// ============================================================================

interface GameProviderProps {
  children: React.ReactNode;
}

export function GameProvider({ children }: GameProviderProps) {
  const [state, dispatch] = useReducer(gameReducer, initialGameState);

  // Refs for WebSocket and reconnection
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptRef = useRef(0);
  const sessionIdRef = useRef("");
  const langRef = useRef<Lang>("fr");

  // Keep langRef in sync
  useEffect(() => {
    langRef.current = state.lang;
  }, [state.lang]);

  // ========================================================================
  // WebSocket Connection
  // ========================================================================

  const connectWebSocket = useCallback((sessionId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.close();
    }

    dispatch({ type: "WS_CONNECTING" });

    const ws = new WebSocket(`${WS_BASE_URL}/ws/${sessionId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("[WS] Connected to", sessionId);
      dispatch({ type: "WS_CONNECTED" });
      reconnectAttemptRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        // Backend-relay sends { subject, data }, GM sends { event/type, data }
        const eventType = msg.subject || msg.event || msg.type || "";
        const data = msg.data ?? msg;

        console.log("[WS] Event:", eventType, data);

        // Map WebSocket events to reducer actions
        dispatchWsEvent(eventType, data, dispatch);
      } catch (err) {
        console.error("[WS] Parse error:", err, event.data);
      }
    };

    ws.onclose = (event) => {
      console.log("[WS] Closed:", event.code, event.reason);
      dispatch({ type: "WS_DISCONNECTED" });

      // Attempt reconnect with exponential backoff
      if (sessionIdRef.current && event.code !== 1000) {
        scheduleReconnect();
      }
    };

    ws.onerror = (error) => {
      console.error("[WS] Error:", error);
      dispatch({ type: "WS_ERROR", error: "WebSocket connection error" });
    };
  }, []);

  const scheduleReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    reconnectAttemptRef.current++;
    const attempt = reconnectAttemptRef.current;

    // Exponential backoff: 1s, 2s, 4s, 8s, 16s, max 30s
    const delay = Math.min(1000 * Math.pow(2, attempt - 1), 30000);
    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${attempt})`);

    dispatch({ type: "WS_RECONNECTING", attempt });

    reconnectTimeoutRef.current = setTimeout(() => {
      if (sessionIdRef.current) {
        connectWebSocket(sessionIdRef.current);
      }
    }, delay);
  }, [connectWebSocket]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close(1000, "Component unmounted");
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  // ========================================================================
  // Handle needsPropose flag
  // ========================================================================

  useEffect(() => {
    if (state.needsPropose && state.sessionId && state.wsStatus === "connected") {
      // Clear the flag FIRST to prevent re-triggers
      dispatch({ type: "CLEAR_NEEDS_PROPOSE" });

      // Add separator line
      const turnText = `══ ${tr("engine.tour", langRef.current)} ${state.gameState.turn} — ${tr("engine.propose", langRef.current)} ══`;
      dispatch({ type: "ADD_TERMINAL_LINE", line: { type: "separator", text: turnText } });

      // Trigger propose via REST (returns 202, events come via WS)
      triggerPropose(state.sessionId, langRef.current).catch((err) => {
        console.error("[API] Propose error:", err);
        dispatch({ type: "GM_ERROR", payload: { message: err.message } });
      });
    }
  }, [state.needsPropose, state.sessionId, state.wsStatus, state.gameState.turn]);

  // ========================================================================
  // Actions
  // ========================================================================

  const startGame = useCallback(async (newLang?: Lang) => {
    if (newLang) {
      langRef.current = newLang;
      dispatch({ type: "SET_LANG", lang: newLang });
    }

    dispatch({ type: "SET_TURN_PHASE", phase: "loading" });

    try {
      const data = await fetchApi<StartResponse>(`/api/start?lang=${langRef.current}`);

      sessionIdRef.current = data.session_id;

      dispatch({
        type: "SESSION_START",
        sessionId: data.session_id,
        agents: data.agents || [],  // May be undefined, real agents come from state.global
        indices: data.indices,
        turn: data.turn,
        maxTurns: data.max_turns,
      });

      // Connect WebSocket after session starts
      // The needsPropose effect will trigger the first proposal once WS connects
      connectWebSocket(data.session_id);
    } catch (err: any) {
      console.error("[API] Start error:", err);
      dispatch({ type: "GM_ERROR", payload: { message: err.message } });
    }
  }, [connectWebSocket]);

  const chooseNews = useCallback((kind: "real" | "fake" | "satirical") => {
    if (state.turnPhase !== "select_news" || !state.sessionId) return;

    dispatch({ type: "SELECT_NEWS", missionId: kind });

    // Add separator line
    const resText = `══ ${tr("engine.tour", langRef.current)} ${state.gameState.turn} — ${tr("engine.resolution", langRef.current)} ══`;
    dispatch({ type: "ADD_TERMINAL_LINE", line: { type: "separator", text: resText } });

    // Trigger choose via REST
    triggerChoose(state.sessionId, kind, langRef.current).catch((err) => {
      console.error("[API] Choose error:", err);
      dispatch({ type: "GM_ERROR", payload: { message: err.message } });
    });
  }, [state.turnPhase, state.sessionId, state.gameState.turn]);

  const nextTurn = useCallback(() => {
    dispatch({ type: "TRIGGER_NEXT_TURN" });
    dispatch({ type: "SET_NEEDS_PROPOSE", value: true });
  }, []);

  const restartGame = useCallback(() => {
    dispatch({ type: "RESET_GAME" });
    startGame(langRef.current);
  }, [startGame]);

  const dismissChaosEvent = useCallback(() => {
    dispatch({ type: "DISMISS_CHAOS_EVENT" });
  }, []);

  const changeLang = useCallback((lang: Lang) => {
    langRef.current = lang;
    dispatch({ type: "SET_LANG", lang });
  }, []);

  // ========================================================================
  // Memoized Context Value
  // ========================================================================

  const actions: GameActions = useMemo(() => ({
    startGame,
    chooseNews,
    nextTurn,
    restartGame,
    dismissChaosEvent,
    changeLang,
  }), [startGame, chooseNews, nextTurn, restartGame, dismissChaosEvent, changeLang]);

  const contextValue: GameContextValue = useMemo(() => ({
    state,
    dispatch,
    actions,
  }), [state, actions]);

  return (
    <GameContext.Provider value={contextValue}>
      {children}
    </GameContext.Provider>
  );
}

// ============================================================================
// WebSocket Event Dispatcher
// ============================================================================

function dispatchWsEvent(
  eventType: string,
  data: any,
  dispatch: React.Dispatch<GameAction>
) {
  // Normalize event type (handle both "gm.proposal" and "gm_proposal" formats)
  const normalized = eventType.replace(/\./g, "_");

  switch (eventType) {
    // GM Events
    case "gm.phase":
    case "phase":
      dispatch({ type: "GM_PHASE", payload: { phase: data.phase || data } });
      break;

    case "gm.llm_call":
    case "llm_call":
      dispatch({ type: "GM_LLM_CALL", payload: data });
      break;

    case "gm.tool_call":
    case "tool_call":
      dispatch({ type: "GM_TOOL_CALL", payload: data });
      break;

    case "gm.tool_result":
    case "tool_result":
      dispatch({ type: "GM_TOOL_RESULT", payload: data });
      break;

    case "gm.proposal":
    case "proposal":
      dispatch({ type: "GM_PROPOSAL", payload: data.data || data });
      break;

    case "gm.images":
    case "images":
      dispatch({ type: "GM_IMAGES", payload: data.data || data });
      break;

    case "gm.choice_resolved":
    case "choice_resolved":
      dispatch({ type: "GM_CHOICE_RESOLVED", payload: data });
      break;

    case "gm.reactions":
    case "reactions":
      dispatch({ type: "GM_REACTIONS", payload: data });
      break;

    case "gm.strategy":
    case "strategy":
      dispatch({ type: "GM_STRATEGY", payload: data });
      break;

    case "gm.turn_update":
    case "turn_update":
      dispatch({ type: "GM_TURN_UPDATE", payload: data });
      break;

    case "gm.indices_update":
    case "indices_update":
      dispatch({ type: "GM_INDICES", payload: data });
      break;

    case "gm.end":
    case "end":
      dispatch({ type: "GM_END" });
      break;

    case "gm.error":
    case "error":
      dispatch({ type: "GM_ERROR", payload: data });
      break;

    // Arena Events
    case "arena.round.start":
      dispatch({ type: "ARENA_ROUND_START", payload: data });
      break;

    case "arena.phase.start":
      dispatch({ type: "ARENA_PHASE_START", payload: data });
      break;

    case "arena.event.death":
    case "agent_death":
      dispatch({ type: "ARENA_DEATH", payload: data });
      break;

    case "arena.event.clone":
    case "agent_clone":
      dispatch({ type: "ARENA_CLONE", payload: data });
      break;

    case "arena.event.end":
      dispatch({ type: "ARENA_END", payload: data });
      break;

    case "arena.input.waiting":
    case "input.waiting":
      dispatch({ type: "ARENA_WAITING", payload: data });
      break;

    // Agent messages
    case "agent_nats":
      dispatch({ type: "AGENT_NATS", payload: data });
      break;

    // LLM text (terminal) — parse and clean markdown code blocks
    case "gm.llm_text":
    case "llm_text": {
      let rawText = String(data.text || data);

      // Try to extract text from nested JSON if it's wrapped in markdown code blocks
      // Pattern: {"type":"llm_text","text":"```json\n{...}\n```"}
      if (rawText.startsWith("{") && rawText.includes("llm_text")) {
        try {
          const parsed = JSON.parse(rawText);
          rawText = parsed.text || rawText;
        } catch {
          // Keep original if parse fails
        }
      }

      // Strip markdown code block markers
      rawText = rawText
        .replace(/^```json\s*/i, "")
        .replace(/^```\s*/gm, "")
        .replace(/\s*```$/gm, "")
        .trim();

      // Skip empty or very short text
      if (rawText.length < 3) break;

      // Truncate long JSON dumps
      if (rawText.length > 200) {
        rawText = rawText.slice(0, 200) + "...";
      }

      dispatch({
        type: "ADD_TERMINAL_LINE",
        line: { type: "llm_text", text: rawText },
      });
      break;
    }

    // Vision update
    case "gm.vision_update":
    case "vision_update": {
      const content = (data.content || String(data)).replace(/\\n/g, "\n");
      dispatch({
        type: "ADD_TERMINAL_LINE",
        line: { type: "vision_update", text: content, agentId: data.agent_id },
      });
      break;
    }

    // Heartbeat — ignore silently
    case "heartbeat":
      break;

    // Result acknowledgements — ignore silently
    case "gm.result":
    case "result":
      break;

    // Dynamic arena events: agent.<aid>.output, agent.<aid>.status, event.*, etc.
    default: {
      const parts = eventType.split(".");

      // Pattern: agent.<aid>.output (agent takes from swarm)
      if (parts.length >= 3 && parts[0] === "agent" && parts[2] === "output") {
        const agentId = parts[1];
        dispatch({
          type: "AGENT_NATS",
          payload: {
            agent_id: data.agent_id || agentId,
            agent_name: data.agent_name || agentId,
            take: data.content || data.take || data.message || "",
            phase: data.phase,
          },
        });
        break;
      }

      // Pattern: agent.<aid>.status (without arena prefix)
      if (parts.length >= 3 && parts[0] === "agent" && parts[2] === "status") {
        const agentId = parts[1];
        dispatch({
          type: "ARENA_AGENT_STATUS",
          payload: { agent_id: agentId, ...data },
        });
        break;
      }

      // Pattern: arena.<sid>.agent.<aid>.output
      if (parts.length >= 5 && parts[0] === "arena" && parts[2] === "agent" && parts[4] === "output") {
        const agentId = parts[3];
        dispatch({
          type: "AGENT_NATS",
          payload: {
            agent_id: data.agent_id || agentId,
            agent_name: data.agent_name || agentId,
            take: data.content || data.take || data.message || "",
            phase: data.phase,
          },
        });
        break;
      }

      // Pattern: arena.<sid>.agent.<aid>.status
      if (parts.length >= 5 && parts[0] === "arena" && parts[2] === "agent" && parts[4] === "status") {
        const agentId = parts[3];
        dispatch({
          type: "ARENA_AGENT_STATUS",
          payload: { agent_id: agentId, ...data },
        });
        break;
      }

      // Pattern: arena.agent.<aid>.status (without session ID)
      if (parts.length >= 4 && parts[0] === "arena" && parts[1] === "agent" && parts[3] === "status") {
        const agentId = parts[2];
        dispatch({
          type: "ARENA_AGENT_STATUS",
          payload: { agent_id: agentId, ...data },
        });
        break;
      }

      // Pattern: event.death (backend-relay strips arena.<sid>. prefix)
      if (parts.length >= 2 && parts[0] === "event" && parts[1] === "death") {
        dispatch({ type: "ARENA_DEATH", payload: data });
        break;
      }

      // Pattern: event.clone
      if (parts.length >= 2 && parts[0] === "event" && parts[1] === "clone") {
        dispatch({ type: "ARENA_CLONE", payload: data });
        break;
      }

      // Pattern: event.end
      if (parts.length >= 2 && parts[0] === "event" && parts[1] === "end") {
        dispatch({ type: "ARENA_END", payload: data });
        break;
      }

      // Pattern: round.start
      if (parts.length >= 2 && parts[0] === "round" && parts[1] === "start") {
        dispatch({ type: "ARENA_ROUND_START", payload: data });
        break;
      }

      // Pattern: phase.start
      if (parts.length >= 2 && parts[0] === "phase" && parts[1] === "start") {
        dispatch({ type: "ARENA_PHASE_START", payload: data });
        break;
      }

      // Pattern: input.waiting
      if (parts.length >= 2 && parts[0] === "input" && parts[1] === "waiting") {
        dispatch({ type: "ARENA_WAITING", payload: data });
        break;
      }

      // Pattern: state.global (omniscient state from swarm)
      if (parts.length >= 2 && parts[0] === "state" && parts[1] === "global") {
        dispatch({ type: "ARENA_GLOBAL_STATE", payload: data });
        break;
      }

      // Pattern: arena.<sid>.event.death (with session ID)
      if (parts.length >= 4 && parts[0] === "arena" && parts[2] === "event" && parts[3] === "death") {
        dispatch({ type: "ARENA_DEATH", payload: data });
        break;
      }

      // Pattern: arena.<sid>.event.clone
      if (parts.length >= 4 && parts[0] === "arena" && parts[2] === "event" && parts[3] === "clone") {
        dispatch({ type: "ARENA_CLONE", payload: data });
        break;
      }

      // Pattern: arena.<sid>.event.end
      if (parts.length >= 4 && parts[0] === "arena" && parts[2] === "event" && parts[3] === "end") {
        dispatch({ type: "ARENA_END", payload: data });
        break;
      }

      // Pattern: arena.<sid>.round.start
      if (parts.length >= 4 && parts[0] === "arena" && parts[2] === "round" && parts[3] === "start") {
        dispatch({ type: "ARENA_ROUND_START", payload: data });
        break;
      }

      // Pattern: arena.<sid>.phase.start
      if (parts.length >= 4 && parts[0] === "arena" && parts[2] === "phase" && parts[3] === "start") {
        dispatch({ type: "ARENA_PHASE_START", payload: data });
        break;
      }

      // Pattern: arena.<sid>.input.waiting
      if (parts.length >= 4 && parts[0] === "arena" && parts[2] === "input" && parts[3] === "waiting") {
        dispatch({ type: "ARENA_WAITING", payload: data });
        break;
      }

      // Unknown event — log for debugging
      console.log("[WS] Unhandled event:", eventType, data);
      dispatch({
        type: "ADD_TERMINAL_LINE",
        line: { type: "info", text: `[${eventType}] ${JSON.stringify(data).slice(0, 150)}` },
      });
      break;
    }
  }
}
