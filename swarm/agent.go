package main

import (
	"crypto/rand"
	"fmt"
	"path/filepath"
)

// AgentNames are the predefined names for agents
var AgentNames = []string{
	"Marcus", "Elena", "Victor", "Luna",
	"Dante", "Aria", "Felix", "Nova",
	"Oscar", "Zara", "Leon", "Maya",
}

// generateUUID generates a random UUID v4
func generateUUID() string {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		// Fallback to time-based pseudo-random if crypto/rand fails
		panic(fmt.Sprintf("crypto/rand.Read failed: %v", err))
	}
	b[6] = (b[6] & 0x0f) | 0x40 // Version 4
	b[8] = (b[8] & 0x3f) | 0x80 // Variant RFC 4122
	return fmt.Sprintf("%x-%x-%x-%x-%x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}

// NewAgent creates a new agent with the given parameters
func NewAgent(name string, color, temperature float64, bornAtRound int, sessionDir string) *Agent {
	id := generateUUID()
	agentDir := filepath.Join(sessionDir, "agents", name)

	return &Agent{
		ID:             id,
		Name:           name,
		PoliticalColor: color,
		Temperature:    temperature,
		Confidence:     3, // neutral starting confidence
		Alive:          true,
		ParentID:       "",
		BornAtRound:    bornAtRound,
		DiedAtRound:    0,
		DeathCause:     "",
		SessionDir:     agentDir,
	}
}

// CreateInitialAgents creates the 4 starting agents with diverse political colors
func CreateInitialAgents(sessionDir string) [4]*Agent {
	// Diverse political spectrum: far-right, right, left, far-left
	configs := []struct {
		name  string
		color float64
		temp  float64
	}{
		{AgentNames[0], 0.05, 0.7}, // Far-right, higher temp
		{AgentNames[1], 0.30, 0.5}, // Right, moderate temp
		{AgentNames[2], 0.75, 0.5}, // Left, moderate temp
		{AgentNames[3], 0.95, 0.7}, // Far-left, higher temp
	}

	var agents [4]*Agent
	for i, cfg := range configs {
		agents[i] = NewAgent(cfg.name, cfg.color, cfg.temp, 1, sessionDir)
	}

	return agents
}

// CloneAgent creates a clone of the winner agent
func CloneAgent(winner *Agent, session *Session, round int, usedNames map[string]bool) *Agent {
	// Find an unused name
	var newName string
	for _, name := range AgentNames {
		if !usedNames[name] {
			newName = name
			break
		}
	}
	if newName == "" {
		// If all names used, generate one
		newName = fmt.Sprintf("Clone_%s_%d", winner.Name, round)
	}

	id := generateUUID()
	agentDir := filepath.Join(session.Dir, "agents", newName)

	clone := &Agent{
		ID:             id,
		Name:           newName,
		PoliticalColor: winner.PoliticalColor, // Same political color
		Temperature:    winner.Temperature,    // Same temperature
		Confidence:     3,                      // Reset confidence
		Alive:          true,
		ParentID:       winner.ID,
		BornAtRound:    round + 1,
		DiedAtRound:    0,
		DeathCause:     "",
		SessionDir:     agentDir,
	}

	return clone
}

// KillAgent marks an agent as dead and moves their files to graveyard
func KillAgent(agent *Agent, session *Session, round int, score *AgentScore, lastConfidence int, lastMessage string, rankings map[string]int) error {
	agent.Alive = false
	agent.DiedAtRound = round
	agent.DeathCause = fmt.Sprintf("eliminated_round_%d", round)

	// Write DEATH.md
	scoreVal := 0
	if score != nil {
		scoreVal = score.TotalPoints
	}
	if err := WriteDeath(agent, round, scoreVal, lastConfidence, lastMessage, rankings); err != nil {
		return fmt.Errorf("failed to write DEATH.md: %w", err)
	}

	// Move agent folder to graveyard
	graveyardDir := filepath.Join(session.Dir, "graveyard", agent.Name)
	if err := MoveDir(agent.SessionDir, graveyardDir); err != nil {
		return fmt.Errorf("failed to move agent to graveyard: %w", err)
	}

	// Update agent's session dir to graveyard location
	agent.SessionDir = graveyardDir

	// Add to session graveyard
	session.Graveyard = append(session.Graveyard, agent)

	return nil
}

// GetUsedNames returns a map of all names used by agents (alive or dead)
func GetUsedNames(session *Session) map[string]bool {
	used := make(map[string]bool)
	for _, a := range session.Agents {
		if a != nil {
			used[a.Name] = true
		}
	}
	for _, a := range session.Graveyard {
		if a != nil {
			used[a.Name] = true
		}
	}
	return used
}

// FindAgentByID finds an agent by ID in the session
func FindAgentByID(session *Session, id string) *Agent {
	for _, a := range session.Agents {
		if a != nil && a.ID == id {
			return a
		}
	}
	return nil
}

// FindAgentByName finds an agent by name in the session
func FindAgentByName(session *Session, name string) *Agent {
	for _, a := range session.Agents {
		if a != nil && a.Name == name {
			return a
		}
	}
	return nil
}

// ReplaceAgent replaces a dead agent with a new one in the session
func ReplaceAgent(session *Session, deadAgent, newAgent *Agent) {
	for i, a := range session.Agents {
		if a != nil && a.ID == deadAgent.ID {
			session.Agents[i] = newAgent
			return
		}
	}
}
