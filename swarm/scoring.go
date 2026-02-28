package main

import (
	"crypto/rand"
	"fmt"
	"math/big"
	"sort"
)

// ComputeScores calculates scores from phase 4 voting
// Each agent ranks the 3 others: 1st place = 3 points, 2nd = 2 points, 3rd = 1 point
func ComputeScores(responses map[string]*AgentMessage, agents [4]*Agent) map[string]*AgentScore {
	scores := make(map[string]*AgentScore)

	// Initialize scores for all agents
	for _, agent := range agents {
		if agent == nil || !agent.Alive {
			continue
		}
		scores[agent.ID] = &AgentScore{
			AgentID:     agent.ID,
			TotalPoints: 0,
			FirstPlaces: 0,
			Confidence:  agent.Confidence,
		}
	}

	// Process each voter's rankings
	for _, response := range responses {
		if response == nil || len(response.Rankings) == 0 {
			continue
		}

		for _, rank := range response.Rankings {
			score, ok := scores[rank.AgentID]
			if !ok {
				continue
			}

			// Convert ranking to points: 1st = 3pts, 2nd = 2pts, 3rd = 1pt
			points := 4 - rank.Score
			if points < 1 {
				points = 1
			}
			if points > 3 {
				points = 3
			}

			score.TotalPoints += points

			if rank.Score == 1 {
				score.FirstPlaces++
			}
		}
	}

	return scores
}

// FindLoser finds the agent with the lowest score (to be eliminated)
func FindLoser(scores map[string]*AgentScore, agents [4]*Agent) *Agent {
	if len(scores) == 0 {
		return nil
	}

	// Convert to sortable slice
	var scoreList []*AgentScore
	for _, s := range scores {
		scoreList = append(scoreList, s)
	}

	// Deterministic sort by: total points (asc), first places (asc), confidence distance from 3 (asc), agent ID (stable)
	sort.Slice(scoreList, func(i, j int) bool {
		// Lower total points = worse (should be eliminated)
		if scoreList[i].TotalPoints != scoreList[j].TotalPoints {
			return scoreList[i].TotalPoints < scoreList[j].TotalPoints
		}
		// Fewer first places = worse
		if scoreList[i].FirstPlaces != scoreList[j].FirstPlaces {
			return scoreList[i].FirstPlaces < scoreList[j].FirstPlaces
		}
		// Confidence closer to 3 = more indecisive = worse
		distI := absInt(scoreList[i].Confidence - 3)
		distJ := absInt(scoreList[j].Confidence - 3)
		if distI != distJ {
			return distI < distJ
		}
		// Stable tiebreaker by agent ID (deterministic)
		return scoreList[i].AgentID < scoreList[j].AgentID
	})

	// If there are ties at the top after deterministic sort, use random selection among tied
	loserScore := scoreList[0]
	var tied []*AgentScore
	for _, s := range scoreList {
		if s.TotalPoints == loserScore.TotalPoints &&
			s.FirstPlaces == loserScore.FirstPlaces &&
			absInt(s.Confidence-3) == absInt(loserScore.Confidence-3) {
			tied = append(tied, s)
		} else {
			break
		}
	}

	// Random selection among truly tied agents
	selected := tied[0]
	if len(tied) > 1 {
		selected = tied[randomInt(len(tied))]
	}

	return findAgentByIDInArray(agents, selected.AgentID)
}

// FindWinner finds the agent with the highest score (to be cloned)
func FindWinner(scores map[string]*AgentScore, agents [4]*Agent) *Agent {
	if len(scores) == 0 {
		return nil
	}

	// Convert to sortable slice
	var scoreList []*AgentScore
	for _, s := range scores {
		scoreList = append(scoreList, s)
	}

	// Deterministic sort by: total points (desc), first places (desc), confidence distance from 3 (desc), agent ID (stable)
	sort.Slice(scoreList, func(i, j int) bool {
		// Higher total points = better (should win)
		if scoreList[i].TotalPoints != scoreList[j].TotalPoints {
			return scoreList[i].TotalPoints > scoreList[j].TotalPoints
		}
		// More first places = better
		if scoreList[i].FirstPlaces != scoreList[j].FirstPlaces {
			return scoreList[i].FirstPlaces > scoreList[j].FirstPlaces
		}
		// Confidence farther from 3 = more decisive = better
		distI := absInt(scoreList[i].Confidence - 3)
		distJ := absInt(scoreList[j].Confidence - 3)
		if distI != distJ {
			return distI > distJ
		}
		// Stable tiebreaker by agent ID (deterministic)
		return scoreList[i].AgentID < scoreList[j].AgentID
	})

	// If there are ties at the top after deterministic sort, use random selection among tied
	winnerScore := scoreList[0]
	var tied []*AgentScore
	for _, s := range scoreList {
		if s.TotalPoints == winnerScore.TotalPoints &&
			s.FirstPlaces == winnerScore.FirstPlaces &&
			absInt(s.Confidence-3) == absInt(winnerScore.Confidence-3) {
			tied = append(tied, s)
		} else {
			break
		}
	}

	// Random selection among truly tied agents
	selected := tied[0]
	if len(tied) > 1 {
		selected = tied[randomInt(len(tied))]
	}

	return findAgentByIDInArray(agents, selected.AgentID)
}

// GetRankingsForAgent extracts how other agents ranked a specific agent
func GetRankingsForAgent(responses map[string]*AgentMessage, targetAgentID string, agents [4]*Agent) map[string]int {
	rankings := make(map[string]int)

	for voterID, response := range responses {
		if response == nil {
			continue
		}

		// Find voter name
		var voterName string
		for _, a := range agents {
			if a != nil && a.ID == voterID {
				voterName = a.Name
				break
			}
		}

		for _, rank := range response.Rankings {
			if rank.AgentID == targetAgentID {
				rankings[voterName] = rank.Score
				break
			}
		}
	}

	return rankings
}

// absInt returns the absolute value of an integer
func absInt(x int) int {
	if x < 0 {
		return -x
	}
	return x
}

// randomInt returns a cryptographically random int in [0, max)
func randomInt(max int) int {
	if max <= 0 {
		return 0
	}
	n, _ := rand.Int(rand.Reader, big.NewInt(int64(max)))
	return int(n.Int64())
}

// findAgentByIDInArray finds an agent by ID in the agents array
func findAgentByIDInArray(agents [4]*Agent, id string) *Agent {
	for _, a := range agents {
		if a != nil && a.ID == id {
			return a
		}
	}
	return nil
}

// ScoreSummary returns a summary of scores for logging
func ScoreSummary(scores map[string]*AgentScore, agents [4]*Agent) string {
	var result string
	for _, agent := range agents {
		if agent == nil || !agent.Alive {
			continue
		}
		if score, ok := scores[agent.ID]; ok {
			result += fmt.Sprintf("%s: %dpts (%d 1ères places)\n",
				agent.Name, score.TotalPoints, score.FirstPlaces)
		}
	}
	return result
}
