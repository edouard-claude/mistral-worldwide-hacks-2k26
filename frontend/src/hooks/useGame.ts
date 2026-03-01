// useGame — Consumer hook for GameProvider
// Provides simple access to game state and actions

import { useContext } from "react";
import { GameContext, type GameContextValue, type GameActions } from "@/context/GameContext";
import type { FullGameState } from "@/reducers/gameReducer";

/**
 * Main hook — returns full context (state + actions)
 * Use this in components that need both state and actions.
 */
export function useGame(): GameContextValue {
  const context = useContext(GameContext);
  if (!context) {
    throw new Error("useGame must be used within a GameProvider");
  }
  return context;
}

/**
 * Returns only game state (optimizes re-renders if you don't need actions)
 */
export function useGameState(): FullGameState {
  const context = useContext(GameContext);
  if (!context) {
    throw new Error("useGameState must be used within a GameProvider");
  }
  return context.state;
}

/**
 * Returns only game actions (stable reference, won't cause re-renders)
 */
export function useGameActions(): GameActions {
  const context = useContext(GameContext);
  if (!context) {
    throw new Error("useGameActions must be used within a GameProvider");
  }
  return context.actions;
}

// Re-export types for convenience
export type { FullGameState } from "@/reducers/gameReducer";
export type { GameActions, GameContextValue } from "@/context/GameContext";
export type {
  TurnPhase,
  WsStatus,
  LoadingState,
  GmAgentVision,
  GmStrategy,
  GmTerminalLine,
  FallenAgent,
  TurnResult,
} from "@/types/ws-events";
