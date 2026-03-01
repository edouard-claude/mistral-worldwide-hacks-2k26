package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sync"
	"time"

	"github.com/joho/godotenv"
	"github.com/nats-io/nats.go"
)

// activeSessions tracks running sessions to prevent duplicate launches
var (
	activeSessions   = make(map[string]bool)
	activeSessionsMu sync.Mutex
)

// isValidSessionID validates that sessionID is a valid UUID format
func isValidSessionID(sessionID string) bool {
	// UUID v4 format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
	uuidRegex := regexp.MustCompile(`^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`)
	return uuidRegex.MatchString(sessionID)
}

func main() {
	// Load .env file (optional, ignores if not found)
	_ = godotenv.Load()

	// Parse command line arguments
	natsURL := flag.String("nats-url", "nats://demo.nats.io:4222", "NATS server URL")
	timeout := flag.Duration("timeout", 30*time.Second, "Timeout per Mistral API call")
	baseDir := flag.String("dir", ".", "Base directory for sessions")
	flag.Parse()

	// Initialize Mistral client (shared across all sessions)
	mistral, err := NewMistralClient(*timeout)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error initializing Mistral client: %v\n", err)
		os.Exit(1)
	}

	absBaseDir, err := filepath.Abs(*baseDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error resolving base directory: %v\n", err)
		os.Exit(1)
	}

	// Connect raw NATS connection for init listener
	nc, err := nats.Connect(*natsURL,
		nats.ReconnectWait(time.Second),
		nats.MaxReconnects(10),
	)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error connecting to NATS: %v\n", err)
		os.Exit(1)
	}
	defer nc.Close()

	// Print startup banner
	fmt.Println("=== FakeNews Arena - Multi-Session Dispatcher ===")
	fmt.Printf("Connecté à NATS: %s\n", *natsURL)
	fmt.Printf("📡 En écoute sur: arena.init\n")
	fmt.Println("Envoyez {\"session_id\": \"<uuid>\"} pour démarrer une session")
	fmt.Println()

	// Subscribe to arena.init for session initialization
	_, err = nc.Subscribe("arena.init", func(msg *nats.Msg) {
		var payload InitPayload
		if err := json.Unmarshal(msg.Data, &payload); err != nil {
			fmt.Fprintf(os.Stderr, "Error parsing init payload: %v\n", err)
			return
		}
		if payload.SessionID == "" {
			fmt.Fprintf(os.Stderr, "Error: empty session_id in init payload\n")
			return
		}

		// F2: Validate sessionID format to prevent path traversal
		if !isValidSessionID(payload.SessionID) {
			fmt.Fprintf(os.Stderr, "Error: invalid session_id format (must be UUID): %s\n", payload.SessionID)
			return
		}

		// F1: Prevent duplicate session launches
		activeSessionsMu.Lock()
		if activeSessions[payload.SessionID] {
			activeSessionsMu.Unlock()
			fmt.Fprintf(os.Stderr, "Warning: session %s already running, ignoring duplicate init\n", payload.SessionID)
			return
		}
		activeSessions[payload.SessionID] = true
		activeSessionsMu.Unlock()

		fmt.Printf("\n🚀 Init reçu pour session: %s\n", payload.SessionID)

		// Default language is French
		lang := payload.Lang
		if lang == "" {
			lang = "fr"
		}

		// Launch game in goroutine
		go runGame(payload.SessionID, lang, nc, mistral, absBaseDir, *timeout)
	})
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error subscribing to arena.init: %v\n", err)
		os.Exit(1)
	}

	// Wait indefinitely
	select {}
}

// runGame runs a complete game session
func runGame(sessionID string, lang string, rawNC *nats.Conn, mistral *MistralClient, baseDir string, timeout time.Duration) {
	// F1: Ensure session is removed from active map when done
	defer func() {
		activeSessionsMu.Lock()
		delete(activeSessions, sessionID)
		activeSessionsMu.Unlock()
	}()

	// Get or create session
	session, resumed, err := GetOrCreateSession(sessionID, baseDir, lang)
	if err != nil {
		fmt.Fprintf(os.Stderr, "[%s] Error creating/loading session: %v\n", sessionID, err)
		return
	}

	if resumed {
		fmt.Printf("[%s] Session rechargée (round %d)\n", sessionID, session.Round)
	} else {
		fmt.Printf("[%s] Nouvelle session créée\n", sessionID)
	}

	// Create session-specific NATS client
	natsClient, err := NewNATSClient(rawNC.ConnectedUrl(), sessionID)
	if err != nil {
		fmt.Fprintf(os.Stderr, "[%s] Error creating NATS client: %v\n", sessionID, err)
		return
	}
	defer natsClient.Close()

	// Subscribe to fake news input channel
	fakeNewsChan, fakeNewsSub, err := natsClient.SubscribeFakeNews()
	if err != nil {
		fmt.Fprintf(os.Stderr, "[%s] Error subscribing to fake news: %v\n", sessionID, err)
		return
	}
	defer fakeNewsSub.Unsubscribe()
	fmt.Printf("[%s] 📡 En attente de fake news sur: arena.%s.input.fakenews\n", sessionID, sessionID)

	// Print agents
	fmt.Printf("[%s] --- Agents ---\n", sessionID)
	for _, agent := range session.Agents {
		if agent != nil && agent.Alive {
			fmt.Printf("[%s]   %s (couleur: %.2f - %s, temp: %.2f)\n",
				sessionID, agent.Name, agent.PoliticalColor, PoliticalLabel(agent.PoliticalColor), agent.Temperature)
		}
	}
	fmt.Println()

	// Create phase runner
	runner := NewPhaseRunner(session, mistral, natsClient, timeout)

	// Determine start round
	startRound := 1
	if resumed {
		startRound = session.Round + 1
	}

	// Game loop: from startRound to 10
	for round := startRound; round <= 10; round++ {
		session.Round = round
		fmt.Printf("\n[%s] ========== TOUR %d ==========\n", sessionID, round)

		// Signal waiting for fake news and wait for input via NATS
		fmt.Printf("[%s] ⏳ Attente fake news tour %d via NATS...\n", sessionID, round)
		_ = natsClient.PublishWaitingForFakeNews(round)

		// Wait for fake news with timeout
		select {
		case fakeNews := <-fakeNewsChan:
			session.FakeNews = fakeNews
		case <-time.After(5 * time.Minute):
			fmt.Printf("[%s] Timeout: pas de fake news reçue, fin de partie.\n", sessionID)
			goto endGame
		}

		if session.FakeNews == "" {
			fmt.Printf("[%s] Fake news vide, fin de partie.\n", sessionID)
			break
		}
		fmt.Printf("[%s] 📰 Fake news du tour: \"%s\"\n", sessionID, session.FakeNews)

		// Inject context from previous rounds (updates agent files with new fake news)
		if err := InjectContext(session, round); err != nil {
			fmt.Fprintf(os.Stderr, "[%s] Warning: failed to inject context: %v\n", sessionID, err)
		}

		// Publish round start
		_ = natsClient.PublishRoundStart(RoundStartPayload{
			Round:    round,
			FakeNews: session.FakeNews,
			Context:  BuildRoundContext(session),
		})

		// Phase 1: Cogitation
		fmt.Printf("[%s] \n--- Phase 1: Cogitation individuelle ---\n", sessionID)
		_ = natsClient.PublishPhaseStart(PhaseStartPayload{Round: round, Phase: 1})
		responses1 := runner.RunPhase1(round)
		for _, agent := range session.Agents {
			if agent == nil || !agent.Alive {
				continue
			}
			if resp, ok := responses1[agent.ID]; ok && resp != nil {
				fmt.Printf("[%s]   [%s] Confiance: %d/5\n", sessionID, agent.Name, resp.Confidence)
			}
		}

		// Phase 2: Public takes
		fmt.Printf("[%s] \n--- Phase 2: Prise de parole publique ---\n", sessionID)
		_ = natsClient.PublishPhaseStart(PhaseStartPayload{Round: round, Phase: 2})
		responses2 := runner.RunPhase2(round, responses1)

		// Write chat file
		var phase2Messages []*AgentMessage
		for _, agent := range session.Agents {
			if agent == nil || !agent.Alive {
				continue
			}
			if resp, ok := responses2[agent.ID]; ok {
				phase2Messages = append(phase2Messages, resp)
				fmt.Printf("[%s]   [%s] Take publié (%d caractères)\n", sessionID, agent.Name, len(resp.Content))
			}
		}
		_ = WriteChat(session, round, 2, phase2Messages)

		// Phase 3: Revision
		fmt.Printf("[%s] \n--- Phase 3: Révision après débat ---\n", sessionID)
		_ = natsClient.PublishPhaseStart(PhaseStartPayload{Round: round, Phase: 3})
		responses3 := runner.RunPhase3(round, responses2)

		var phase3Messages []*AgentMessage
		for _, agent := range session.Agents {
			if agent == nil || !agent.Alive {
				continue
			}
			if resp, ok := responses3[agent.ID]; ok {
				phase3Messages = append(phase3Messages, resp)
				fmt.Printf("[%s]   [%s] Confiance finale: %d/5\n", sessionID, agent.Name, resp.Confidence)
			}
		}
		_ = WriteChat(session, round, 3, phase3Messages)

		// Phase 4: Voting
		fmt.Printf("[%s] \n--- Phase 4: Vote et mutation ---\n", sessionID)
		_ = natsClient.PublishPhaseStart(PhaseStartPayload{Round: round, Phase: 4})
		responses4 := runner.RunPhase4(round, responses2, responses3)

		// Compute scores
		scores := ComputeScores(responses4, session.Agents)
		fmt.Printf("[%s] \n--- Scores du tour ---\n", sessionID)
		for _, agent := range session.Agents {
			if agent == nil || !agent.Alive {
				continue
			}
			if score, ok := scores[agent.ID]; ok {
				fmt.Printf("[%s]   [%s] %d points (%d 1ères places)\n",
					sessionID, agent.Name, score.TotalPoints, score.FirstPlaces)
			}
		}

		// Natural selection (except last round) - determine BEFORE writing memories
		var loserName, winnerName, cloneName string
		if round < 5 {
			loser := FindLoser(scores, session.Agents)
			winner := FindWinner(scores, session.Agents)

			if loser != nil && winner != nil {
				loserName = loser.Name
				winnerName = winner.Name

				fmt.Printf("[%s] \n💀 MORT: %s (score le plus bas)\n", sessionID, loser.Name)
				fmt.Printf("[%s] 🧬 CLONAGE: %s va être cloné\n", sessionID, winner.Name)

				// Get rankings for the loser
				rankings := GetRankingsForAgent(responses4, loser.ID, session.Agents)

				// Get last message and confidence
				lastMessage := ""
				lastConfidence := loser.Confidence
				if resp, ok := responses3[loser.ID]; ok && resp != nil {
					lastMessage = resp.Content
					lastConfidence = resp.Confidence
				}

				// Kill loser
				loserScore := scores[loser.ID]
				if err := KillAgent(loser, session, round, loserScore, lastConfidence, lastMessage, rankings); err != nil {
					fmt.Fprintf(os.Stderr, "[%s] Warning: failed to kill agent: %v\n", sessionID, err)
				}

				// Publish death event
				_ = natsClient.PublishDeathEvent(DeathEventPayload{
					AgentID:   loser.ID,
					AgentName: loser.Name,
					Round:     round,
					Cause:     fmt.Sprintf("eliminated_round_%d", round),
				})

				// Clone winner
				usedNames := GetUsedNames(session)
				clone := CloneAgent(winner, session, round, usedNames)
				cloneName = clone.Name

				// Replace loser with clone FIRST so session.Agents is correct
				ReplaceAgent(session, loser, clone)

				// Write clone files AFTER it's in the session
				if err := WriteAgentFiles(clone, session); err != nil {
					fmt.Fprintf(os.Stderr, "[%s] Warning: failed to write clone files: %v\n", sessionID, err)
				}

				// Publish clone event
				_ = natsClient.PublishCloneEvent(CloneEventPayload{
					ParentID:   winner.ID,
					ParentName: winner.Name,
					ChildID:    clone.ID,
					ChildName:  clone.Name,
					Round:      round,
				})

				fmt.Printf("[%s] 🆕 Nouveau venu: %s (clone de %s)\n", sessionID, clone.Name, winner.Name)
			}
		}

		// Write memories for all surviving agents AFTER natural selection
		for _, agent := range session.Agents {
			if agent == nil || !agent.Alive {
				continue
			}
			// Skip clone - it has no memory of this round
			if agent.BornAtRound > round {
				continue
			}
			memory := GenerateMemoryMD(
				agent, round, session.FakeNews,
				responses1[agent.ID],
				responses2[agent.ID],
				responses3[agent.ID],
				responses4[agent.ID],
				scores, session.Agents,
				loserName, cloneName, winnerName,
				session.Lang,
			)
			_ = WriteMemory(agent, round, memory)
		}

		// Save global state
		if err := SaveGlobalState(session); err != nil {
			fmt.Fprintf(os.Stderr, "[%s] Warning: failed to save global state: %v\n", sessionID, err)
		}

		// Publish global state
		_ = natsClient.PublishGlobalState(GlobalState{
			SessionID: session.ID,
			FakeNews:  session.FakeNews,
			Round:     round,
			Phase:     4,
			Agents:    GetAliveAgents(session),
			Graveyard: session.Graveyard,
			Scores:    convertScores(scores),
		})
	}

endGame:
	// End of game
	fmt.Printf("\n[%s] ========== FIN DE PARTIE ==========\n", sessionID)
	fmt.Printf("[%s] \n🏆 Survivants:\n", sessionID)
	var survivors []string
	for _, agent := range session.Agents {
		if agent != nil && agent.Alive {
			fmt.Printf("[%s]   - %s (couleur: %.2f - %s)\n",
				sessionID, agent.Name, agent.PoliticalColor, PoliticalLabel(agent.PoliticalColor))
			survivors = append(survivors, agent.Name)
		}
	}

	fmt.Printf("[%s] \n⚰️ Cimetière:\n", sessionID)
	for _, dead := range session.Graveyard {
		fmt.Printf("[%s]   - %s (mort au tour %d)\n", sessionID, dead.Name, dead.DiedAtRound)
	}

	// Publish end event with actual rounds played
	history := make([]int, session.Round)
	for i := range history {
		history[i] = i + 1
	}
	_ = natsClient.PublishEndEvent(EndEventPayload{
		Survivors: survivors,
		History:   history,
	})

	fmt.Printf("[%s] \n📁 Session terminée: %s\n", sessionID, session.Dir)
}

func convertScores(scores map[string]*AgentScore) map[string]int {
	result := make(map[string]int)
	for id, s := range scores {
		result[id] = s.TotalPoints
	}
	return result
}
