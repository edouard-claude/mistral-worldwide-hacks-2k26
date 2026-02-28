package main

import (
	"bufio"
	"crypto/rand"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/nats-io/nats.go"
)

// InitPayload matches the server's expected format
type InitPayload struct {
	SessionID string `json:"session_id"`
}

func main() {
	natsURL := flag.String("nats-url", "nats://demo.nats.io:4222", "NATS server URL")
	sessionID := flag.String("session", "", "Session ID (UUID format, auto-generated if empty)")
	flag.Parse()

	// Generate session ID if not provided
	if *sessionID == "" {
		*sessionID = generateUUID()
	}

	// Validate UUID format
	if !isValidUUID(*sessionID) {
		fmt.Fprintf(os.Stderr, "Error: session ID must be a valid UUID format\n")
		os.Exit(1)
	}

	// Connect to NATS
	nc, err := nats.Connect(*natsURL,
		nats.ReconnectWait(time.Second),
		nats.MaxReconnects(5),
	)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error connecting to NATS: %v\n", err)
		os.Exit(1)
	}
	defer nc.Close()

	fmt.Printf("Connecté à NATS: %s\n", *natsURL)
	fmt.Printf("Session ID: %s\n", *sessionID)

	// Subscribe to waiting events to know when to send fake news
	waitingChan := make(chan int, 5)
	fakeNewsTopic := fmt.Sprintf("arena.%s.input.fakenews", *sessionID)
	waitingTopic := fmt.Sprintf("arena.%s.input.waiting", *sessionID)

	_, err = nc.Subscribe(waitingTopic, func(msg *nats.Msg) {
		var payload struct {
			Round   int  `json:"round"`
			Waiting bool `json:"waiting"`
		}
		if err := json.Unmarshal(msg.Data, &payload); err == nil && payload.Waiting {
			waitingChan <- payload.Round
		}
	})
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error subscribing to waiting: %v\n", err)
		os.Exit(1)
	}

	// Send init message
	initPayload := InitPayload{SessionID: *sessionID}
	initData, _ := json.Marshal(initPayload)

	fmt.Println("\n📤 Envoi du message init sur arena.init...")
	if err := nc.Publish("arena.init", initData); err != nil {
		fmt.Fprintf(os.Stderr, "Error publishing init: %v\n", err)
		os.Exit(1)
	}
	nc.Flush()

	fmt.Printf("✅ Init envoyé pour session: %s\n", *sessionID)
	fmt.Printf("\n📡 Topic fake news: %s\n", fakeNewsTopic)
	fmt.Println("\n--- Mode interactif ---")
	fmt.Println("Entrez une fake news par ligne (ou 'quit' pour quitter)")
	fmt.Println("Le service attend une fake news à chaque tour (5 tours max)")
	fmt.Println()

	// Interactive mode: read fake news from stdin
	scanner := bufio.NewScanner(os.Stdin)
	round := 0

	for {
		// Check if server is waiting
		select {
		case r := <-waitingChan:
			round = r
			fmt.Printf("\n⏳ [Tour %d] Le serveur attend une fake news...\n", round)
		default:
		}

		fmt.Print("> ")
		if !scanner.Scan() {
			break
		}

		input := strings.TrimSpace(scanner.Text())
		if input == "" {
			continue
		}
		if input == "quit" || input == "exit" {
			fmt.Println("👋 Au revoir!")
			break
		}

		// Send fake news
		if err := nc.Publish(fakeNewsTopic, []byte(input)); err != nil {
			fmt.Fprintf(os.Stderr, "Error publishing fake news: %v\n", err)
			continue
		}
		nc.Flush()
		fmt.Printf("📰 Fake news envoyée: \"%s\"\n", input)
	}
}

// generateUUID generates a random UUID v4
func generateUUID() string {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		panic(err)
	}
	// Set version (4) and variant bits
	b[6] = (b[6] & 0x0f) | 0x40
	b[8] = (b[8] & 0x3f) | 0x80
	return fmt.Sprintf("%x-%x-%x-%x-%x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}

// isValidUUID checks if a string is a valid UUID format
func isValidUUID(s string) bool {
	if len(s) != 36 {
		return false
	}
	for i, c := range s {
		if i == 8 || i == 13 || i == 18 || i == 23 {
			if c != '-' {
				return false
			}
		} else {
			if !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F')) {
				return false
			}
		}
	}
	return true
}
