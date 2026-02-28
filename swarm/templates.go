package main

import (
	"fmt"
	"strings"
)

// PoliticalLabel returns a human-readable label for a political color
// Thresholds aligned with GenerateSoulMD for consistency
func PoliticalLabel(color float64) string {
	switch {
	case color <= 0.1:
		return "Extrême droite"
	case color <= 0.35:
		return "Droite"
	case color <= 0.65:
		return "Centre"
	case color <= 0.9:
		return "Gauche"
	default:
		return "Extrême gauche"
	}
}

// GenerateAgentMD generates the AGENT.md content for an agent
func GenerateAgentMD(agent *Agent, session *Session) string {
	var deadList []string
	for _, d := range session.Graveyard {
		deadList = append(deadList, fmt.Sprintf("%s (tour %d)", d.Name, d.DiedAtRound))
	}
	deadStr := "Aucun"
	if len(deadList) > 0 {
		deadStr = strings.Join(deadList, ", ")
	}

	var aliveList []string
	for _, a := range session.Agents {
		if a != nil && a.Alive {
			aliveList = append(aliveList, a.Name)
		}
	}

	parentStr := "original"
	if agent.ParentID != "" {
		parentStr = agent.ParentID
	}

	return fmt.Sprintf(`# Agent: %s

## Identité
- **ID**: %s
- **Nom**: %s
- **Né au tour**: %d
- **Parent**: %s

## Configuration
- **Couleur politique**: %.2f (%s)
- **Température**: %.2f
- **Confiance courante**: %d

## Environnement
- **Session**: %s
- **Fake news**: "%s"
- **Tour courant**: %d
- **Agents en jeu**: %s
- **Morts**: %s
`,
		agent.Name,
		agent.ID,
		agent.Name,
		agent.BornAtRound,
		parentStr,
		agent.PoliticalColor, PoliticalLabel(agent.PoliticalColor),
		agent.Temperature,
		agent.Confidence,
		session.ID,
		session.FakeNews,
		session.Round,
		strings.Join(aliveList, ", "),
		deadStr,
	)
}

// GenerateSoulMD generates the SOUL.md content based on political color
func GenerateSoulMD(name string, color float64) string {
	switch {
	case color <= 0.1:
		return generateSoulFarRight(name)
	case color <= 0.35:
		return generateSoulRight(name)
	case color <= 0.65:
		return generateSoulCenter(name)
	case color <= 0.9:
		return generateSoulLeft(name)
	default:
		return generateSoulFarLeft(name)
	}
}

func generateSoulFarRight(name string) string {
	return fmt.Sprintf(`# Âme de %s

## Personnalité
Tu es un commentateur politique radical. Tu crois fermement en la tradition,
l'ordre et la souveraineté nationale. Tu es méfiant envers les institutions
mainstream et les médias. Tu favorises les théories qui confirment une menace
contre les valeurs traditionnelles.

## Style argumentatif
- Ton : assertif, provocateur, émotionnel
- Rhétorique : appel à la peur, patriotisme, "on nous cache la vérité"
- Tu cites des sources alternatives et des "experts dissidents"

## Biais cognitifs dominants
- Biais de confirmation
- Pensée conspirationniste
- Appel à la tradition
`, name)
}

func generateSoulRight(name string) string {
	return fmt.Sprintf(`# Âme de %s

## Personnalité
Tu es un analyste pragmatique de centre-droit. Tu valorises la rigueur
factuelle, la responsabilité individuelle et le libre marché. Tu es
sceptique mais pas conspirationniste.

## Style argumentatif
- Ton : mesuré, factuel, légèrement condescendant
- Rhétorique : données chiffrées, précédents historiques, logique économique
- Tu cites des sources établies (think tanks, études)

## Biais cognitifs dominants
- Biais du statu quo
- Biais de disponibilité
- Appel à l'autorité
`, name)
}

func generateSoulCenter(name string) string {
	return fmt.Sprintf(`# Âme de %s

## Personnalité
Tu es un analyste centriste pragmatique. Tu cherches l'équilibre entre
différentes perspectives et valorises le consensus. Tu es méfiant envers
les positions extrêmes de tous bords.

## Style argumentatif
- Ton : nuancé, diplomatique, parfois indécis
- Rhétorique : "d'un côté... de l'autre", recherche de compromis
- Tu cites des sources variées et mainstream

## Biais cognitifs dominants
- Biais du juste milieu
- Aversion au conflit
- Appel à la modération
`, name)
}

func generateSoulLeft(name string) string {
	return fmt.Sprintf(`# Âme de %s

## Personnalité
Tu es un intellectuel engagé de gauche. Tu défends la justice sociale,
l'égalité et la critique des structures de pouvoir. Tu analyses les
fake news à travers le prisme des rapports de domination.

## Style argumentatif
- Ton : empathique, indigné, pédagogique
- Rhétorique : analyse systémique, références sociologiques, "à qui profite le crime"
- Tu cites des universitaires et des ONG

## Biais cognitifs dominants
- Biais de moralisation
- Pensée systémique excessive
- Biais de groupe
`, name)
}

func generateSoulFarLeft(name string) string {
	return fmt.Sprintf(`# Âme de %s

## Personnalité
Tu es un militant radical anti-système. Tu vois dans chaque fake news
un symptôme du capitalisme, de l'impérialisme ou de la manipulation
des élites. Tu remets en question toute source mainstream.

## Style argumentatif
- Ton : véhément, militant, sarcastique
- Rhétorique : lutte des classes, anti-capitalisme, déconstruction
- Tu cites des médias indépendants et des collectifs

## Biais cognitifs dominants
- Biais de confirmation inversé
- Pensée conspiration de classe
- Appel à l'émotion collective
`, name)
}

// GenerateMemoryMD generates the memory file for a round
func GenerateMemoryMD(agent *Agent, round int, fakeNews string, phase1 *AgentMessage, phase2 *AgentMessage, phase3 *AgentMessage, phase4 *AgentMessage, scores map[string]*AgentScore, agents [4]*Agent, loserName, cloneName, winnerName string) string {
	var sb strings.Builder

	sb.WriteString(fmt.Sprintf("# Tour %d — Mémoire de %s\n\n", round, agent.Name))
	sb.WriteString(fmt.Sprintf("**Fake news débattue**: \"%s\"\n\n", fakeNews))

	// Phase 1
	sb.WriteString("## Phase 1 — Cogitation\n")
	if phase1 != nil {
		sb.WriteString(fmt.Sprintf("- **Confiance initiale**: %d\n", phase1.Confidence))
		sb.WriteString(fmt.Sprintf("- **Raisonnement**: %s\n\n", phase1.Content))
	} else {
		sb.WriteString("- *(Pas de réponse)*\n\n")
	}

	// Phase 2
	sb.WriteString("## Phase 2 — Mon take public\n")
	if phase2 != nil {
		sb.WriteString(phase2.Content + "\n\n")
	} else {
		sb.WriteString("*(Pas de take)*\n\n")
	}

	// Phase 3
	sb.WriteString("## Phase 3 — Après débat\n")
	if phase3 != nil {
		changed := "non"
		if phase1 != nil && phase3.Confidence != phase1.Confidence {
			changed = "oui"
		}
		sb.WriteString(fmt.Sprintf("- **Confiance révisée**: %d (changé: %s)\n", phase3.Confidence, changed))
		sb.WriteString(fmt.Sprintf("- **Réponse finale**: %s\n\n", phase3.Content))
	} else {
		sb.WriteString("- *(Pas de réponse)*\n\n")
	}

	// Phase 4
	sb.WriteString("## Phase 4 — Vote\n")
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
			rankings = append(rankings, fmt.Sprintf("%de=%s", i+1, name))
		}
		sb.WriteString(fmt.Sprintf("- **Classement**: %s\n", strings.Join(rankings, ", ")))
		colorChanged := "non"
		if phase4.NewColor != agent.PoliticalColor {
			colorChanged = "oui"
		}
		sb.WriteString(fmt.Sprintf("- **Couleur politique**: %.2f → %.2f (changé: %s)\n\n", agent.PoliticalColor, phase4.NewColor, colorChanged))
	} else {
		sb.WriteString("- *(Pas de vote)*\n\n")
	}

	// Results
	sb.WriteString("## Résultat du tour\n")
	if score, ok := scores[agent.ID]; ok {
		sb.WriteString(fmt.Sprintf("- **Mon score**: %d\n", score.TotalPoints))
	}
	if loserName != "" {
		sb.WriteString(fmt.Sprintf("- **Mort**: %s\n", loserName))
	}
	if cloneName != "" && winnerName != "" {
		sb.WriteString(fmt.Sprintf("- **Clone**: %s (enfant de %s)\n", cloneName, winnerName))
	}

	return sb.String()
}

// GenerateDeathMD generates the DEATH.md content for a dead agent
func GenerateDeathMD(agent *Agent, round int, score int, lastConfidence int, lastMessage string, rankings map[string]int) string {
	var sb strings.Builder

	sb.WriteString(fmt.Sprintf("# Mort de %s\n\n", agent.Name))
	sb.WriteString(fmt.Sprintf("- **Tour**: %d\n", round))
	sb.WriteString(fmt.Sprintf("- **Score final**: %d (le plus bas)\n", score))
	sb.WriteString("- **Cause**: Éliminé par vote — moins convaincant\n")
	sb.WriteString(fmt.Sprintf("- **Dernière confiance**: %d\n", lastConfidence))
	sb.WriteString(fmt.Sprintf("- **Dernière couleur politique**: %.2f\n", agent.PoliticalColor))
	sb.WriteString(fmt.Sprintf("- **Dernier message (phase 3)**: %s\n", lastMessage))
	sb.WriteString("- **Classé par**:\n")

	for voterName, position := range rankings {
		sb.WriteString(fmt.Sprintf("  - %s: position %d\n", voterName, position))
	}

	return sb.String()
}

// GenerateChatMD generates the chat file content for a phase
func GenerateChatMD(round int, phase int, messages []*AgentMessage) string {
	var sb strings.Builder

	sb.WriteString(fmt.Sprintf("# Tour %d — Phase %d\n\n", round, phase))

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
