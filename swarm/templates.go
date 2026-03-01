package main

import (
	"fmt"
	"strings"
)

// PoliticalLabel returns a human-readable label for a political color
// Thresholds aligned with GenerateSoulMD for consistency
// Deprecated: Use PoliticalLabelI18n for i18n support
func PoliticalLabel(color float64) string {
	return PoliticalLabelI18n(color, "fr")
}

// GenerateAgentMD generates the AGENT.md content for an agent
func GenerateAgentMD(agent *Agent, session *Session) string {
	lang := session.Lang
	if lang == "" {
		lang = "fr"
	}

	var deadList []string
	for _, d := range session.Graveyard {
		deadList = append(deadList, fmt.Sprintf("%s (%s %d)", d.Name, T(lang, "round"), d.DiedAtRound))
	}
	deadStr := T(lang, "none")
	if len(deadList) > 0 {
		deadStr = strings.Join(deadList, ", ")
	}

	var aliveList []string
	for _, a := range session.Agents {
		if a != nil && a.Alive {
			aliveList = append(aliveList, a.Name)
		}
	}

	parentStr := T(lang, "original")
	if agent.ParentID != "" {
		parentStr = agent.ParentID
	}

	return fmt.Sprintf(`# Agent: %s

## %s
- **%s**: %s
- **%s**: %s
- **%s**: %d
- **%s**: %s

## %s
- **%s**: %.2f (%s)
- **%s**: %.2f
- **%s**: %d

## %s
- **%s**: %s
- **%s**: "%s"
- **%s**: %d
- **%s**: %s
- **%s**: %s
`,
		agent.Name,
		T(lang, "identity"),
		T(lang, "id"), agent.ID,
		T(lang, "name"), agent.Name,
		T(lang, "born_at_round"), agent.BornAtRound,
		T(lang, "parent"), parentStr,
		T(lang, "configuration"),
		T(lang, "political_color"), agent.PoliticalColor, PoliticalLabelI18n(agent.PoliticalColor, lang),
		T(lang, "temperature"), agent.Temperature,
		T(lang, "current_conf"), agent.Confidence,
		T(lang, "environment"),
		T(lang, "session"), session.ID,
		T(lang, "fake_news"), session.FakeNews,
		T(lang, "current_round"), session.Round,
		T(lang, "agents_in_game"), strings.Join(aliveList, ", "),
		T(lang, "dead"), deadStr,
	)
}

// GenerateSoulMD generates the SOUL.md content based on political color
func GenerateSoulMD(name string, color float64, lang string) string {
	if lang == "" {
		lang = "fr"
	}

	var soulType string
	switch {
	case color <= 0.1:
		soulType = "far_right"
	case color <= 0.35:
		soulType = "right"
	case color <= 0.65:
		soulType = "center"
	case color <= 0.9:
		soulType = "left"
	default:
		soulType = "far_left"
	}

	return fmt.Sprintf(`# %s %s

## %s
%s

## %s
%s

## %s
%s
`,
		T(lang, "soul_of"), name,
		T(lang, "personality"),
		T(lang, "soul_"+soulType+"_desc"),
		T(lang, "arguing_style"),
		T(lang, "soul_"+soulType+"_style"),
		T(lang, "biases"),
		T(lang, "soul_"+soulType+"_biases"),
	)
}

// GenerateMemoryMD generates the memory file for a round
func GenerateMemoryMD(agent *Agent, round int, fakeNews string, phase1 *AgentMessage, phase2 *AgentMessage, phase3 *AgentMessage, phase4 *AgentMessage, scores map[string]*AgentScore, agents [4]*Agent, loserName, cloneName, winnerName, lang string) string {
	if lang == "" {
		lang = "fr"
	}

	var sb strings.Builder

	sb.WriteString(fmt.Sprintf("# %s %d — %s %s\n\n", T(lang, "round"), round, T(lang, "memory_of"), agent.Name))
	sb.WriteString(fmt.Sprintf("**%s**: \"%s\"\n\n", T(lang, "fake_news_debated"), fakeNews))

	// Phase 1
	sb.WriteString(fmt.Sprintf("## %s\n", T(lang, "phase1_cogitation")))
	if phase1 != nil {
		sb.WriteString(fmt.Sprintf("- **%s**: %d\n", T(lang, "initial_confidence"), phase1.Confidence))
		sb.WriteString(fmt.Sprintf("- **%s**: %s\n\n", T(lang, "reasoning"), phase1.Content))
	} else {
		sb.WriteString(fmt.Sprintf("- *(%s)*\n\n", T(lang, "no_response")))
	}

	// Phase 2
	sb.WriteString(fmt.Sprintf("## %s\n", T(lang, "phase2_public_take")))
	if phase2 != nil {
		sb.WriteString(phase2.Content + "\n\n")
	} else {
		sb.WriteString(fmt.Sprintf("*(%s)*\n\n", T(lang, "no_take")))
	}

	// Phase 3
	sb.WriteString(fmt.Sprintf("## %s\n", T(lang, "phase3_after")))
	if phase3 != nil {
		changed := T(lang, "no")
		if phase1 != nil && phase3.Confidence != phase1.Confidence {
			changed = T(lang, "yes")
		}
		sb.WriteString(fmt.Sprintf("- **%s**: %d (%s: %s)\n", T(lang, "revised_confidence"), phase3.Confidence, T(lang, "changed"), changed))
		sb.WriteString(fmt.Sprintf("- **%s**: %s\n\n", T(lang, "final_response"), phase3.Content))
	} else {
		sb.WriteString(fmt.Sprintf("- *(%s)*\n\n", T(lang, "no_response")))
	}

	// Phase 4
	sb.WriteString(fmt.Sprintf("## %s\n", T(lang, "phase4_vote")))
	if phase4 != nil && len(phase4.Rankings) > 0 {
		var rankings []string
		for i, r := range phase4.Rankings {
			// Look up agent name from ID
			name := r.AgentID // fallback to ID if not found
			for _, a := range agents {
				if a != nil && a.ID == r.AgentID {
					name = a.Name
					break
				}
			}
			rankings = append(rankings, fmt.Sprintf("%d=%s", i+1, name))
		}
		sb.WriteString(fmt.Sprintf("- **%s**: %s\n", T(lang, "ranking"), strings.Join(rankings, ", ")))
		colorChanged := T(lang, "no")
		if phase4.NewColor != agent.PoliticalColor {
			colorChanged = T(lang, "yes")
		}
		sb.WriteString(fmt.Sprintf("- **%s**: %.2f → %.2f (%s: %s)\n\n", T(lang, "political_color"), agent.PoliticalColor, phase4.NewColor, T(lang, "changed"), colorChanged))
	} else {
		sb.WriteString(fmt.Sprintf("- *(%s)*\n\n", T(lang, "no_vote")))
	}

	// Results
	sb.WriteString(fmt.Sprintf("## %s\n", T(lang, "round_result")))
	if score, ok := scores[agent.ID]; ok {
		sb.WriteString(fmt.Sprintf("- **%s**: %d\n", T(lang, "my_score"), score.TotalPoints))
	}
	if loserName != "" {
		sb.WriteString(fmt.Sprintf("- **%s**: %s\n", T(lang, "death"), loserName))
	}
	if cloneName != "" && winnerName != "" {
		sb.WriteString(fmt.Sprintf("- **%s**: %s (%s %s)\n", T(lang, "clone"), cloneName, T(lang, "child_of"), winnerName))
	}

	return sb.String()
}

// GenerateDeathMD generates the DEATH.md content for a dead agent
func GenerateDeathMD(agent *Agent, round int, score int, lastConfidence int, lastMessage string, rankings map[string]int, lang string) string {
	if lang == "" {
		lang = "fr"
	}

	var sb strings.Builder

	sb.WriteString(fmt.Sprintf("# %s %s\n\n", T(lang, "death_of"), agent.Name))
	sb.WriteString(fmt.Sprintf("- **%s**: %d\n", T(lang, "round"), round))
	sb.WriteString(fmt.Sprintf("- **%s**: %d (%s)\n", T(lang, "final_score"), score, T(lang, "lowest")))
	sb.WriteString(fmt.Sprintf("- **%s**: %s\n", T(lang, "cause"), T(lang, "eliminated_by_vote")))
	sb.WriteString(fmt.Sprintf("- **%s**: %d\n", T(lang, "last_confidence"), lastConfidence))
	sb.WriteString(fmt.Sprintf("- **%s**: %.2f\n", T(lang, "last_political_color"), agent.PoliticalColor))
	sb.WriteString(fmt.Sprintf("- **%s**: %s\n", T(lang, "last_message"), lastMessage))
	sb.WriteString(fmt.Sprintf("- **%s**:\n", T(lang, "ranked_by")))

	for voterName, position := range rankings {
		sb.WriteString(fmt.Sprintf("  - %s: %s %d\n", voterName, T(lang, "position"), position))
	}

	return sb.String()
}

// GenerateChatMD generates the chat file content for a phase
func GenerateChatMD(round int, phase int, messages []*AgentMessage, lang string) string {
	if lang == "" {
		lang = "fr"
	}

	var sb strings.Builder

	sb.WriteString(fmt.Sprintf("# %s %d — Phase %d\n\n", T(lang, "round"), round, phase))

	for _, msg := range messages {
		if msg == nil {
			continue
		}
		sb.WriteString(fmt.Sprintf("## %s\n\n", msg.AgentName))
		sb.WriteString(msg.Content)
		sb.WriteString("\n\n---\n\n")
	}

	return sb.String()
}
