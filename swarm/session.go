package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// NewSession creates a new game session with auto-generated UUID
func NewSession(fakeNews, baseDir string) (*Session, error) {
	return NewSessionWithID(generateUUID(), fakeNews, baseDir)
}

// NewSessionWithID creates a new game session with a specific session ID
func NewSessionWithID(sessionID, fakeNews, baseDir string) (*Session, error) {
	sessionDir := filepath.Join(baseDir, "sessions", sessionID)

	session := &Session{
		ID:        sessionID,
		FakeNews:  fakeNews,
		Round:     0,
		Graveyard: make([]*Agent, 0),
		Dir:       sessionDir,
	}

	// Create session directory structure
	if err := EnsureDir(sessionDir); err != nil {
		return nil, fmt.Errorf("failed to create session directory: %w", err)
	}
	if err := EnsureDir(filepath.Join(sessionDir, "agents")); err != nil {
		return nil, fmt.Errorf("failed to create agents directory: %w", err)
	}
	if err := EnsureDir(filepath.Join(sessionDir, "chat")); err != nil {
		return nil, fmt.Errorf("failed to create chat directory: %w", err)
	}
	if err := EnsureDir(filepath.Join(sessionDir, "graveyard")); err != nil {
		return nil, fmt.Errorf("failed to create graveyard directory: %w", err)
	}

	// Create initial agents
	session.Agents = CreateInitialAgents(sessionDir)

	// Write agent files
	for _, agent := range session.Agents {
		if err := WriteAgentFiles(agent, session); err != nil {
			return nil, fmt.Errorf("failed to write agent files for %s: %w", agent.Name, err)
		}
	}

	// Write initial global state
	if err := SaveGlobalState(session); err != nil {
		return nil, fmt.Errorf("failed to save initial global state: %w", err)
	}

	return session, nil
}

// LoadSession loads an existing session from global.json
func LoadSession(sessionID, baseDir string) (*Session, error) {
	sessionDir := filepath.Join(baseDir, "sessions", sessionID)
	globalPath := filepath.Join(sessionDir, "global.json")

	data, err := os.ReadFile(globalPath)
	if err != nil {
		return nil, fmt.Errorf("failed to read global.json: %w", err)
	}

	var state GlobalState
	if err := json.Unmarshal(data, &state); err != nil {
		return nil, fmt.Errorf("failed to parse global.json: %w", err)
	}

	session := &Session{
		ID:        state.SessionID,
		FakeNews:  state.FakeNews,
		Round:     state.Round,
		Graveyard: state.Graveyard,
		Dir:       sessionDir,
	}

	// Reconstruct Agents[4] from state.Agents
	for i, agent := range state.Agents {
		if i >= 4 {
			break
		}
		if agent != nil {
			agent.SessionDir = filepath.Join(sessionDir, "agents", agent.Name)
			session.Agents[i] = agent
		}
	}

	return session, nil
}

// GetOrCreateSession loads an existing session or creates a new one
// Returns (session, resumed, error) where resumed is true if session was loaded
func GetOrCreateSession(sessionID, baseDir string) (*Session, bool, error) {
	globalPath := filepath.Join(baseDir, "sessions", sessionID, "global.json")

	if _, err := os.Stat(globalPath); err == nil {
		// Session exists, load it
		session, err := LoadSession(sessionID, baseDir)
		if err != nil {
			return nil, false, err
		}
		return session, true, nil
	}

	// Session doesn't exist, create new one
	session, err := NewSessionWithID(sessionID, "(interactive)", baseDir)
	if err != nil {
		return nil, false, err
	}
	return session, false, nil
}

// SaveGlobalState saves the global state to global.json
func SaveGlobalState(session *Session) error {
	// F3: Preserve all 4 slots (including nil) to maintain index positions
	agents := make([]*Agent, 4)
	copy(agents, session.Agents[:])

	state := GlobalState{
		SessionID: session.ID,
		FakeNews:  session.FakeNews,
		Round:     session.Round,
		Phase:     0,
		Agents:    agents,
		Graveyard: session.Graveyard,
	}

	data, err := json.MarshalIndent(state, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal global state: %w", err)
	}

	// F4: Atomic write via temp file + rename
	tmpPath := filepath.Join(session.Dir, "global.json.tmp")
	finalPath := filepath.Join(session.Dir, "global.json")

	if err := WriteFile(tmpPath, string(data)); err != nil {
		return err
	}

	return os.Rename(tmpPath, finalPath)
}

// InjectContext updates agent files with current session state
func InjectContext(session *Session, round int) error {
	// Update each agent's AGENT.md with current session info
	for _, agent := range session.Agents {
		if agent == nil || !agent.Alive {
			continue
		}

		// Regenerate and rewrite AGENT.md with updated info
		if err := WriteFile(
			filepath.Join(agent.SessionDir, "AGENT.md"),
			GenerateAgentMD(agent, session),
		); err != nil {
			return fmt.Errorf("failed to update AGENT.md for %s: %w", agent.Name, err)
		}
	}

	// Log context for debugging
	if len(session.Graveyard) > 0 {
		fmt.Printf("[Round %d] Contexte: %d agents morts\n", round, len(session.Graveyard))
	}

	return nil
}

// GetAliveAgents returns all alive agents
func GetAliveAgents(session *Session) []*Agent {
	var alive []*Agent
	for _, a := range session.Agents {
		if a != nil && a.Alive {
			alive = append(alive, a)
		}
	}
	return alive
}

// BuildRoundContext builds the context string for a round
func BuildRoundContext(session *Session) string {
	var parts []string

	// Previous deaths
	for _, dead := range session.Graveyard {
		parts = append(parts, fmt.Sprintf(
			"%s a été éliminé au tour %d.",
			dead.Name, dead.DiedAtRound,
		))
	}

	// Current agents
	var agentNames []string
	for _, a := range session.Agents {
		if a != nil && a.Alive {
			agentNames = append(agentNames, a.Name)
		}
	}
	if len(agentNames) > 0 {
		parts = append(parts, fmt.Sprintf("Agents en lice: %s", strings.Join(agentNames, ", ")))
	}

	return strings.Join(parts, "\n")
}
