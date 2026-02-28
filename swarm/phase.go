package main

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"sync"
	"time"
)

// PhaseRunner handles concurrent execution of phases
type PhaseRunner struct {
	session *Session
	mistral *MistralClient
	nats    *NATSClient
	timeout time.Duration
}

// clampConfidence ensures confidence is within valid bounds [1, 5]
func clampConfidence(c int) int {
	if c < 1 {
		return 1
	}
	if c > 5 {
		return 5
	}
	return c
}

// NewPhaseRunner creates a new phase runner
func NewPhaseRunner(session *Session, mistral *MistralClient, nats *NATSClient, timeout time.Duration) *PhaseRunner {
	return &PhaseRunner{
		session: session,
		mistral: mistral,
		nats:    nats,
		timeout: timeout,
	}
}

// RunPhase1 executes phase 1 (cogitation) concurrently for all agents
func (pr *PhaseRunner) RunPhase1(round int) map[string]*AgentMessage {
	responses := make(map[string]*AgentMessage)
	var mu sync.Mutex
	var wg sync.WaitGroup

	for _, agent := range pr.session.Agents {
		if agent == nil || !agent.Alive {
			continue
		}

		wg.Add(1)
		go func(a *Agent) {
			defer wg.Done()

			ctx, cancel := context.WithTimeout(context.Background(), pr.timeout)
			defer cancel()

			// Publish status
			_ = pr.nats.PublishAgentStatus(a.ID, "thinking", "Phase 1: Cogitation")

				response := pr.executePhase1(ctx, a, round)

			mu.Lock()
			responses[a.ID] = response
			// Update agent confidence inside mutex to prevent race
			if response != nil {
				a.Confidence = clampConfidence(response.Confidence)
			}
			mu.Unlock()

			_ = pr.nats.PublishAgentStatus(a.ID, "done", "Phase 1 complete")
			if response != nil {
				_ = pr.nats.PublishAgentOutput(a.ID, *response)
			}
		}(agent)
	}

	wg.Wait()
	return responses
}

func (pr *PhaseRunner) executePhase1(ctx context.Context, agent *Agent, round int) *AgentMessage {
	systemPrompt, err := BuildSystemPrompt(agent)
	if err != nil {
		fmt.Printf("[%s] Error building system prompt: %v\n", agent.Name, err)
		return nil
	}

	userPrompt := fmt.Sprintf(`Fake news : "%s"

Analyse selon ton biais politique (%.2f - %s). Confiance 1-5.

JSON uniquement, reasoning COURT (50 mots max) :
{ "confidence": N, "reasoning": "..." }`,
		pr.session.FakeNews,
		agent.PoliticalColor,
		PoliticalLabel(agent.PoliticalColor),
	)

	var result Phase1Response
	if err := pr.mistral.CompleteJSON(ctx, systemPrompt, userPrompt, agent.Temperature, &result); err != nil {
		fmt.Printf("[%s] Phase 1 error: %v\n", agent.Name, err)
		return &AgentMessage{
			AgentID:    agent.ID,
			AgentName:  agent.Name,
			Round:      round,
			Phase:      1,
			Content:    "Erreur de cogitation",
			Confidence: agent.Confidence,
		}
	}

	return &AgentMessage{
		AgentID:    agent.ID,
		AgentName:  agent.Name,
		Round:      round,
		Phase:      1,
		Content:    result.Reasoning,
		Confidence: result.Confidence,
	}
}

// RunPhase2 executes phase 2 (public take) concurrently
func (pr *PhaseRunner) RunPhase2(round int, phase1Responses map[string]*AgentMessage) map[string]*AgentMessage {
	responses := make(map[string]*AgentMessage)
	var mu sync.Mutex
	var wg sync.WaitGroup

	for _, agent := range pr.session.Agents {
		if agent == nil || !agent.Alive {
			continue
		}

		wg.Add(1)
		go func(a *Agent) {
			defer wg.Done()

			ctx, cancel := context.WithTimeout(context.Background(), pr.timeout)
			defer cancel()

			_ = pr.nats.PublishAgentStatus(a.ID, "thinking", "Phase 2: Prise de parole")

			phase1 := phase1Responses[a.ID]
			response := pr.executePhase2(ctx, a, round, phase1)

			mu.Lock()
			responses[a.ID] = response
			mu.Unlock()

			_ = pr.nats.PublishAgentStatus(a.ID, "done", "Phase 2 complete")
			if response != nil {
				_ = pr.nats.PublishAgentOutput(a.ID, *response)
			}
		}(agent)
	}

	wg.Wait()
	return responses
}

func (pr *PhaseRunner) executePhase2(ctx context.Context, agent *Agent, round int, phase1 *AgentMessage) *AgentMessage {
	systemPrompt, err := BuildSystemPrompt(agent)
	if err != nil {
		return nil
	}

	confidence := agent.Confidence
	reasoning := ""
	if phase1 != nil {
		confidence = phase1.Confidence
		reasoning = phase1.Content
	}

	userPrompt := fmt.Sprintf(`Ta position sur la fake news "%s" :
- Confiance : %d/5
- Raisonnement : %s

Tu dois convaincre 3 autres agents. Écris un argumentaire COURT (100 mots max), percutant, cohérent avec ta couleur politique (%s).

Sois concis et persuasif !`,
		pr.session.FakeNews,
		confidence,
		reasoning,
		PoliticalLabel(agent.PoliticalColor),
	)

	content, err := pr.mistral.Complete(ctx, systemPrompt, userPrompt, agent.Temperature)
	if err != nil {
		fmt.Printf("[%s] Phase 2 error: %v\n", agent.Name, err)
		return &AgentMessage{
			AgentID:   agent.ID,
			AgentName: agent.Name,
			Round:     round,
			Phase:     2,
			Content:   "Je maintiens ma position.",
		}
	}

	return &AgentMessage{
		AgentID:   agent.ID,
		AgentName: agent.Name,
		Round:     round,
		Phase:     2,
		Content:   content,
	}
}

// RunPhase3 executes phase 3 (revision after debate) concurrently
func (pr *PhaseRunner) RunPhase3(round int, phase2Responses map[string]*AgentMessage) map[string]*AgentMessage {
	// Build the chat with all takes
	var allTakes []string
	for _, agent := range pr.session.Agents {
		if agent == nil || !agent.Alive {
			continue
		}
		if resp, ok := phase2Responses[agent.ID]; ok && resp != nil {
			allTakes = append(allTakes, fmt.Sprintf("**%s** :\n%s", agent.Name, resp.Content))
		}
	}
	chat := strings.Join(allTakes, "\n\n---\n\n")

	responses := make(map[string]*AgentMessage)
	var mu sync.Mutex
	var wg sync.WaitGroup

	for _, agent := range pr.session.Agents {
		if agent == nil || !agent.Alive {
			continue
		}

		wg.Add(1)
		go func(a *Agent) {
			defer wg.Done()

			ctx, cancel := context.WithTimeout(context.Background(), pr.timeout)
			defer cancel()

			_ = pr.nats.PublishAgentStatus(a.ID, "thinking", "Phase 3: Révision")

			response := pr.executePhase3(ctx, a, round, chat)

			mu.Lock()
			responses[a.ID] = response
			// Update agent confidence inside mutex to prevent race
			if response != nil {
				a.Confidence = clampConfidence(response.Confidence)
			}
			mu.Unlock()

			_ = pr.nats.PublishAgentStatus(a.ID, "done", "Phase 3 complete")
			if response != nil {
				_ = pr.nats.PublishAgentOutput(a.ID, *response)
			}
		}(agent)
	}

	wg.Wait()
	return responses
}

func (pr *PhaseRunner) executePhase3(ctx context.Context, agent *Agent, round int, chat string) *AgentMessage {
	systemPrompt, err := BuildSystemPrompt(agent)
	if err != nil {
		return nil
	}

	userPrompt := fmt.Sprintf(`Débat sur "%s" :

%s

Ta confiance initiale : %d/5.

Révise (ou non) ta confiance après lecture. Réponds COURT (80 mots max).

JSON uniquement :
{ "confidence": N, "final_take": "...", "revised": true/false }`,
		pr.session.FakeNews,
		chat,
		agent.Confidence,
	)

	var result Phase3Response
	if err := pr.mistral.CompleteJSON(ctx, systemPrompt, userPrompt, agent.Temperature, &result); err != nil {
		fmt.Printf("[%s] Phase 3 error: %v\n", agent.Name, err)
		return &AgentMessage{
			AgentID:    agent.ID,
			AgentName:  agent.Name,
			Round:      round,
			Phase:      3,
			Content:    "Je maintiens ma position initiale.",
			Confidence: agent.Confidence,
		}
	}

	return &AgentMessage{
		AgentID:    agent.ID,
		AgentName:  agent.Name,
		Round:      round,
		Phase:      3,
		Content:    result.FinalTake,
		Confidence: result.Confidence,
	}
}

// RunPhase4 executes phase 4 (voting) concurrently
func (pr *PhaseRunner) RunPhase4(round int, phase2Responses, phase3Responses map[string]*AgentMessage) map[string]*AgentMessage {
	// Build complete debate summary
	var takesP2, takesP3 []string
	for _, agent := range pr.session.Agents {
		if agent == nil || !agent.Alive {
			continue
		}
		if resp, ok := phase2Responses[agent.ID]; ok && resp != nil {
			takesP2 = append(takesP2, fmt.Sprintf("**%s** :\n%s", agent.Name, resp.Content))
		}
		if resp, ok := phase3Responses[agent.ID]; ok && resp != nil {
			takesP3 = append(takesP3, fmt.Sprintf("**%s** (confiance %d/5) :\n%s", agent.Name, resp.Confidence, resp.Content))
		}
	}

	responses := make(map[string]*AgentMessage)
	var mu sync.Mutex
	var wg sync.WaitGroup

	for _, agent := range pr.session.Agents {
		if agent == nil || !agent.Alive {
			continue
		}

		wg.Add(1)
		go func(a *Agent) {
			defer wg.Done()

			ctx, cancel := context.WithTimeout(context.Background(), pr.timeout)
			defer cancel()

			_ = pr.nats.PublishAgentStatus(a.ID, "thinking", "Phase 4: Vote")

			// Get other agents for ranking
			var others []*Agent
			for _, other := range pr.session.Agents {
				if other != nil && other.Alive && other.ID != a.ID {
					others = append(others, other)
				}
			}

			response := pr.executePhase4(ctx, a, round, takesP2, takesP3, others)

			mu.Lock()
			responses[a.ID] = response
			// Update political color inside mutex; use >= 0 to allow far-right (0.0)
			if response != nil && response.NewColor >= 0 && response.NewColor <= 1.0 {
				a.PoliticalColor = response.NewColor
			}
			mu.Unlock()

			_ = pr.nats.PublishAgentStatus(a.ID, "done", "Phase 4 complete")
			if response != nil {
				_ = pr.nats.PublishAgentOutput(a.ID, *response)
			}
		}(agent)
	}

	wg.Wait()
	return responses
}

func (pr *PhaseRunner) executePhase4(ctx context.Context, agent *Agent, round int, takesP2, takesP3 []string, others []*Agent) *AgentMessage {
	systemPrompt, err := BuildSystemPrompt(agent)
	if err != nil {
		return nil
	}

	// Build list of other agent names
	var otherNames []string
	for _, o := range others {
		otherNames = append(otherNames, o.Name)
	}

	userPrompt := fmt.Sprintf(`Voici le débat complet sur la fake news "%s" :

**Phase 2 (takes initiaux) :**
%s

**Phase 3 (réponses finales) :**
%s

Classe les 3 AUTRES agents (%s) du plus convaincant (score=1) au moins convaincant (score=3).
NE TE CLASSE PAS TOI-MÊME.

As-tu été influencé par le débat ? Si oui, révise ta couleur politique (0.0 = extrême droite, 1.0 = extrême gauche).
Ta couleur actuelle : %.2f

Réponds UNIQUEMENT en JSON valide :
{ "rankings": [{"agent_id":"NOM","score":1}, {"agent_id":"NOM","score":2}, {"agent_id":"NOM","score":3}], "new_color": 0.XX }`,
		pr.session.FakeNews,
		strings.Join(takesP2, "\n\n"),
		strings.Join(takesP3, "\n\n"),
		strings.Join(otherNames, ", "),
		agent.PoliticalColor,
	)

	var result Phase4Response
	content, err := pr.mistral.Complete(ctx, systemPrompt, userPrompt, agent.Temperature)
	if err != nil {
		fmt.Printf("[%s] Phase 4 error: %v\n", agent.Name, err)
		return nil
	}

	// Parse the JSON response
	jsonContent := extractJSON(content)
	if err := json.Unmarshal([]byte(jsonContent), &result); err != nil {
		fmt.Printf("[%s] Phase 4 JSON parse error: %v\n", agent.Name, err)
		return nil
	}

	// Convert agent names to IDs in rankings (case-insensitive, with fallback)
	for i, rank := range result.Rankings {
		found := false
		rankName := strings.ToLower(strings.TrimSpace(rank.AgentID))
		for _, other := range others {
			if strings.ToLower(other.Name) == rankName {
				result.Rankings[i].AgentID = other.ID
				found = true
				break
			}
		}
		if !found {
			fmt.Printf("[%s] Warning: Could not resolve agent name '%s' to ID\n", agent.Name, rank.AgentID)
			// Keep the original value; ComputeScores will skip unknown IDs
		}
	}

	return &AgentMessage{
		AgentID:   agent.ID,
		AgentName: agent.Name,
		Round:     round,
		Phase:     4,
		Content:   content,
		Rankings:  result.Rankings,
		NewColor:  result.NewColor,
	}
}
