// Test: simulate swarm agent output → verify agentHistory storage
// Run: npx vitest run src/reducers/gameReducer.test.ts

import { describe, it, expect } from "vitest";
import { gameReducer, initialGameState, type FullGameState } from "./gameReducer";

function dispatch(state: FullGameState, ...actions: Parameters<typeof gameReducer>[1][]): FullGameState {
  return actions.reduce((s, a) => gameReducer(s, a), state);
}

describe("AGENT_NATS → agentHistory storage", () => {
  // Simulate exactly what the swarm sends via NATS → relay → GM → frontend WS
  const AGENT_ID = "550e8400-e29b-41d4-a716-446655440000";
  const AGENT_NAME = "KGB_TR0LL";

  it("stores phase 1 (cogitation) with confidence", () => {
    const state = dispatch(initialGameState, {
      type: "AGENT_NATS",
      payload: {
        agent_id: AGENT_ID,
        agent_name: AGENT_NAME,
        take: "Cette fake news est clairement orientée à gauche...",
        phase: 1,
        round: 1,
        confidence: 4,
      },
    });

    expect(state.agentHistory[AGENT_ID]).toBeDefined();
    expect(state.agentHistory[AGENT_ID]).toHaveLength(1);

    const roundEntry = state.agentHistory[AGENT_ID][0];
    expect(roundEntry.round).toBe(1);
    expect(roundEntry.phases[1]).toBeDefined();
    expect(roundEntry.phases[1].content).toBe("Cette fake news est clairement orientée à gauche...");
    expect(roundEntry.phases[1].confidence).toBe(4);
    expect(roundEntry.phases[1].phase).toBe(1);
  });

  it("stores all 4 phases in same round", () => {
    let state = initialGameState;

    // Phase 1: cogitation
    state = gameReducer(state, {
      type: "AGENT_NATS",
      payload: { agent_id: AGENT_ID, agent_name: AGENT_NAME, take: "Raisonnement phase 1", phase: 1, round: 1, confidence: 3 },
    });

    // Phase 2: public take
    state = gameReducer(state, {
      type: "AGENT_NATS",
      payload: { agent_id: AGENT_ID, agent_name: AGENT_NAME, take: "Argumentaire phase 2", phase: 2, round: 1 },
    });

    // Phase 3: revision
    state = gameReducer(state, {
      type: "AGENT_NATS",
      payload: { agent_id: AGENT_ID, agent_name: AGENT_NAME, take: "Position révisée phase 3", phase: 3, round: 1, confidence: 4 },
    });

    // Phase 4: vote with rankings + new_color
    state = gameReducer(state, {
      type: "AGENT_NATS",
      payload: {
        agent_id: AGENT_ID,
        agent_name: AGENT_NAME,
        take: '{"rankings": [...]}',
        phase: 4,
        round: 1,
        rankings: [
          { agent_id: "agent-2", score: 1 },
          { agent_id: "agent-3", score: 2 },
          { agent_id: "agent-4", score: 3 },
        ],
        new_color: 0.72,
      },
    });

    // Verify
    expect(state.agentHistory[AGENT_ID]).toHaveLength(1); // 1 round
    const round = state.agentHistory[AGENT_ID][0];
    expect(Object.keys(round.phases)).toHaveLength(4);

    // Phase 1
    expect(round.phases[1].content).toBe("Raisonnement phase 1");
    expect(round.phases[1].confidence).toBe(3);

    // Phase 2
    expect(round.phases[2].content).toBe("Argumentaire phase 2");
    expect(round.phases[2].confidence).toBeUndefined();

    // Phase 3
    expect(round.phases[3].content).toBe("Position révisée phase 3");
    expect(round.phases[3].confidence).toBe(4);

    // Phase 4
    expect(round.phases[4].rankings).toHaveLength(3);
    expect(round.phases[4].rankings![0]).toEqual({ agent_id: "agent-2", score: 1 });
    expect(round.phases[4].new_color).toBe(0.72);
  });

  it("stores multiple rounds separately", () => {
    let state = initialGameState;

    // Round 1, phase 1
    state = gameReducer(state, {
      type: "AGENT_NATS",
      payload: { agent_id: AGENT_ID, agent_name: AGENT_NAME, take: "Round 1 take", phase: 1, round: 1, confidence: 3 },
    });

    // Round 2, phase 1
    state = gameReducer(state, {
      type: "AGENT_NATS",
      payload: { agent_id: AGENT_ID, agent_name: AGENT_NAME, take: "Round 2 take", phase: 1, round: 2, confidence: 5 },
    });

    expect(state.agentHistory[AGENT_ID]).toHaveLength(2);
    expect(state.agentHistory[AGENT_ID][0].round).toBe(1);
    expect(state.agentHistory[AGENT_ID][1].round).toBe(2);
  });

  it("persists agentHistory across TRIGGER_NEXT_TURN", () => {
    let state = gameReducer(initialGameState, {
      type: "AGENT_NATS",
      payload: { agent_id: AGENT_ID, agent_name: AGENT_NAME, take: "Stored data", phase: 1, round: 1, confidence: 3 },
    });

    state = gameReducer(state, { type: "TRIGGER_NEXT_TURN" });

    // agentHistory should survive turn transition
    expect(state.agentHistory[AGENT_ID]).toHaveLength(1);
    expect(state.agentHistory[AGENT_ID][0].phases[1].content).toBe("Stored data");
  });

  it("clears agentHistory on RESET_GAME", () => {
    let state = gameReducer(initialGameState, {
      type: "AGENT_NATS",
      payload: { agent_id: AGENT_ID, agent_name: AGENT_NAME, take: "Some data", phase: 1, round: 1, confidence: 3 },
    });

    state = gameReducer(state, { type: "RESET_GAME" });

    expect(state.agentHistory).toEqual({});
  });

  it("stores multiple agents independently", () => {
    let state = initialGameState;

    state = gameReducer(state, {
      type: "AGENT_NATS",
      payload: { agent_id: "agent-A", agent_name: "Pavel", take: "Pavel's take", phase: 2, round: 1 },
    });

    state = gameReducer(state, {
      type: "AGENT_NATS",
      payload: { agent_id: "agent-B", agent_name: "Natasha", take: "Natasha's take", phase: 2, round: 1 },
    });

    expect(Object.keys(state.agentHistory)).toHaveLength(2);
    expect(state.agentHistory["agent-A"][0].phases[2].content).toBe("Pavel's take");
    expect(state.agentHistory["agent-B"][0].phases[2].content).toBe("Natasha's take");
  });

  it("also adds to debateLines (backward compat)", () => {
    const state = gameReducer(initialGameState, {
      type: "AGENT_NATS",
      payload: { agent_id: AGENT_ID, agent_name: AGENT_NAME, take: "Mon argument", phase: 2, round: 1 },
    });

    expect(state.debateLines).toHaveLength(1);
    expect(state.debateLines[0].agent).toBe(AGENT_NAME);
    expect(state.debateLines[0].message).toBe("Mon argument");
  });

  it("handles missing phase gracefully (no phase key in payload)", () => {
    const state = gameReducer(initialGameState, {
      type: "AGENT_NATS",
      payload: { agent_id: AGENT_ID, agent_name: AGENT_NAME, take: "No phase info" },
    });

    // Should still create agentHistory entry but not store any phase
    // (phase is undefined → the if(phase !== undefined) guard skips storage)
    expect(state.agentHistory[AGENT_ID]).toHaveLength(1);
    expect(Object.keys(state.agentHistory[AGENT_ID][0].phases)).toHaveLength(0);
  });
});
