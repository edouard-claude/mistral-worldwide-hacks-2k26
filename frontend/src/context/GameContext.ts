// GameContext — Separate file to prevent HMR context recreation
// This file rarely changes, keeping the context reference stable

import { createContext } from "react";
import type { FullGameState } from "@/reducers/gameReducer";
import type { GameAction } from "@/types/ws-events";
import type { Lang } from "@/i18n/translations";

// ============================================================================
// Context Types
// ============================================================================

export interface GameActions {
  startGame: (lang?: Lang) => Promise<void>;
  chooseNews: (kind: "real" | "fake" | "satirical") => void;
  nextTurn: () => void;
  restartGame: () => void;
  dismissChaosEvent: () => void;
  changeLang: (lang: Lang) => void;
}

export interface GameContextValue {
  state: FullGameState;
  dispatch: React.Dispatch<GameAction>;
  actions: GameActions;
}

// ============================================================================
// Context (stable reference for HMR)
// ============================================================================

export const GameContext = createContext<GameContextValue | null>(null);
