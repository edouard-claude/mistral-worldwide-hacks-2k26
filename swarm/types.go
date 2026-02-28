package main

// Agent represents a participant in the FakeNews Arena
type Agent struct {
	ID             string  `json:"id"`
	Name           string  `json:"name"`
	PoliticalColor float64 `json:"political_color"` // 0.0 (far-right) → 1.0 (far-left)
	Temperature    float64 `json:"temperature"`     // LLM temperature (0.0 → 1.0)
	Confidence     int     `json:"confidence"`      // 1-5, confidence in the fake news
	Alive          bool    `json:"alive"`
	ParentID       string  `json:"parent_id,omitempty"` // empty if original, parent uuid if clone
	BornAtRound    int     `json:"born_at_round"`
	DiedAtRound    int     `json:"died_at_round,omitempty"` // 0 if alive
	DeathCause     string  `json:"death_cause,omitempty"`
	SessionDir     string  `json:"-"` // path to agent folder
}

// Session represents a game session
type Session struct {
	ID        string   `json:"id"`
	FakeNews  string   `json:"fake_news"`
	Agents    [4]*Agent `json:"agents"`    // always 4 active agents
	Round     int      `json:"round"`      // current round (1-5)
	Graveyard []*Agent `json:"graveyard"`  // dead agents
	Dir       string   `json:"-"`          // session path
}

// AgentMessage is exchanged between orchestrator and agents via NATS
type AgentMessage struct {
	AgentID    string  `json:"agent_id"`
	AgentName  string  `json:"agent_name"`
	Round      int     `json:"round"`
	Phase      int     `json:"phase"`                 // 1, 2, 3, 4
	Content    string  `json:"content"`               // LLM response text
	Confidence int     `json:"confidence,omitempty"`  // 1-5 (phases 1, 3)
	Rankings   []Rank  `json:"rankings,omitempty"`    // phase 4 only
	NewColor   float64 `json:"new_color,omitempty"`   // phase 4, if revised
}

// Rank represents an agent's ranking of another agent
type Rank struct {
	AgentID string `json:"agent_id"`
	Score   int    `json:"score"` // 1 (best) → 3 (worst)
}

// RoundStartPayload is sent when a round begins
type RoundStartPayload struct {
	Round    int    `json:"round"`
	FakeNews string `json:"fake_news"`
	Context  string `json:"context"` // previous rounds context
}

// PhaseStartPayload signals the start of a phase
type PhaseStartPayload struct {
	Round int `json:"round"`
	Phase int `json:"phase"`
}

// PhaseInputPayload delivers phase-specific input to an agent
type PhaseInputPayload struct {
	Phase    int      `json:"phase"`
	Chat     []string `json:"chat,omitempty"`      // phase 3: all takes
	AllTakes []string `json:"all_takes,omitempty"` // phase 4: phase 2 takes
	AllFinal []string `json:"all_final,omitempty"` // phase 4: phase 3 responses
}

// AgentStatusPayload for heartbeat/status updates
type AgentStatusPayload struct {
	State  string `json:"state"`  // "thinking", "ready", "done"
	Detail string `json:"detail,omitempty"`
}

// DeathEventPayload when an agent dies
type DeathEventPayload struct {
	AgentID   string `json:"agent_id"`
	AgentName string `json:"agent_name"`
	Round     int    `json:"round"`
	Cause     string `json:"cause"`
}

// CloneEventPayload when an agent is cloned
type CloneEventPayload struct {
	ParentID   string `json:"parent_id"`
	ParentName string `json:"parent_name"`
	ChildID    string `json:"child_id"`
	ChildName  string `json:"child_name"`
	Round      int    `json:"round"`
}

// EndEventPayload when the game ends
type EndEventPayload struct {
	Survivors []string `json:"survivors"`
	History   []int    `json:"history"` // rounds played
}

// GlobalState is the omniscient state snapshot
type GlobalState struct {
	SessionID string          `json:"session_id"`
	FakeNews  string          `json:"fake_news"`
	Round     int             `json:"round"`
	Phase     int             `json:"phase"`
	Agents    []*Agent        `json:"agents"`
	Graveyard []*Agent        `json:"graveyard"`
	Scores    map[string]int  `json:"scores,omitempty"`
}

// Phase1Response is the expected JSON from Mistral in phase 1
type Phase1Response struct {
	Confidence int    `json:"confidence"`
	Reasoning  string `json:"reasoning"`
}

// Phase3Response is the expected JSON from Mistral in phase 3
type Phase3Response struct {
	Confidence int    `json:"confidence"`
	FinalTake  string `json:"final_take"`
	Revised    bool   `json:"revised"`
}

// Phase4Response is the expected JSON from Mistral in phase 4
type Phase4Response struct {
	Rankings []Rank  `json:"rankings"`
	NewColor float64 `json:"new_color"`
}

// AgentScore holds scoring data for an agent
type AgentScore struct {
	AgentID      string
	TotalPoints  int
	FirstPlaces  int
	Confidence   int
}

// InitPayload is the payload for session initialization via arena.init
type InitPayload struct {
	SessionID string `json:"session_id"`
}
