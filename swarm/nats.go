package main

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/nats-io/nats.go"
)

// NATSClient wraps NATS connection and provides arena-specific methods
type NATSClient struct {
	conn      *nats.Conn
	sessionID string
}

// NewNATSClient connects to NATS and creates a client for the session
func NewNATSClient(url, sessionID string) (*NATSClient, error) {
	nc, err := nats.Connect(url,
		nats.ReconnectWait(time.Second),
		nats.MaxReconnects(10),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to NATS: %w", err)
	}

	return &NATSClient{
		conn:      nc,
		sessionID: sessionID,
	}, nil
}

// Close closes the NATS connection
func (c *NATSClient) Close() {
	if c.conn != nil {
		c.conn.Close()
	}
}

// subject builds a NATS subject with the session ID
func (c *NATSClient) subject(parts ...string) string {
	subj := "arena." + c.sessionID
	for _, p := range parts {
		subj += "." + p
	}
	return subj
}

// --- Orchestrator → Agents ---

// PublishRoundStart signals the start of a round
func (c *NATSClient) PublishRoundStart(payload RoundStartPayload) error {
	return c.publish("round.start", payload)
}

// PublishPhaseStart signals the start of a phase
func (c *NATSClient) PublishPhaseStart(payload PhaseStartPayload) error {
	return c.publish("phase.start", payload)
}

// PublishAgentInput sends phase-specific input to an agent
func (c *NATSClient) PublishAgentInput(agentID string, payload PhaseInputPayload) error {
	return c.publish("agent."+agentID+".input", payload)
}

// PublishAgentKill notifies an agent of its death
func (c *NATSClient) PublishAgentKill(agentID string, reason string, round int) error {
	payload := map[string]any{
		"reason": reason,
		"round":  round,
	}
	return c.publish("agent."+agentID+".kill", payload)
}

// --- Agents → Orchestrator ---

// PublishAgentOutput publishes an agent's response
func (c *NATSClient) PublishAgentOutput(agentID string, msg AgentMessage) error {
	return c.publish("agent."+agentID+".output", msg)
}

// PublishAgentStatus publishes an agent's status
func (c *NATSClient) PublishAgentStatus(agentID string, state, detail string) error {
	payload := AgentStatusPayload{
		State:  state,
		Detail: detail,
	}
	return c.publish("agent."+agentID+".status", payload)
}

// --- Global State / Events ---

// PublishGlobalState publishes the omniscient state snapshot
func (c *NATSClient) PublishGlobalState(state GlobalState) error {
	return c.publish("state.global", state)
}

// PublishAgentState publishes an individual agent's state
func (c *NATSClient) PublishAgentState(agentID string, state any) error {
	return c.publish("state.agent."+agentID, state)
}

// PublishDeathEvent publishes a death event
func (c *NATSClient) PublishDeathEvent(payload DeathEventPayload) error {
	return c.publish("event.death", payload)
}

// PublishCloneEvent publishes a clone event
func (c *NATSClient) PublishCloneEvent(payload CloneEventPayload) error {
	return c.publish("event.clone", payload)
}

// PublishEndEvent publishes the end of game event
func (c *NATSClient) PublishEndEvent(payload EndEventPayload) error {
	return c.publish("event.end", payload)
}

// --- Subscriptions ---

// SubscribeFakeNews subscribes to fake news input for rounds
// Returns a channel that receives fake news strings
func (c *NATSClient) SubscribeFakeNews() (chan string, *nats.Subscription, error) {
	ch := make(chan string, 10)
	sub, err := c.conn.Subscribe(c.subject("input", "fakenews"), func(msg *nats.Msg) {
		// F8: Non-blocking send to prevent NATS dispatcher blocking
		select {
		case ch <- string(msg.Data):
		default:
			// Buffer full, discard oldest and add new
			select {
			case <-ch:
			default:
			}
			ch <- string(msg.Data)
		}
	})
	if err != nil {
		return nil, nil, err
	}
	return ch, sub, nil
}

// PublishWaitingForFakeNews signals that the game is waiting for a fake news
func (c *NATSClient) PublishWaitingForFakeNews(round int) error {
	payload := map[string]any{
		"round":   round,
		"waiting": true,
	}
	return c.publish("input.waiting", payload)
}

// SubscribeAgentOutput subscribes to agent output messages
func (c *NATSClient) SubscribeAgentOutput(agentID string, handler func(AgentMessage)) (*nats.Subscription, error) {
	return c.conn.Subscribe(c.subject("agent", agentID, "output"), func(msg *nats.Msg) {
		var am AgentMessage
		if err := json.Unmarshal(msg.Data, &am); err == nil {
			handler(am)
		}
	})
}

// SubscribePhaseStart subscribes to phase start signals
func (c *NATSClient) SubscribePhaseStart(handler func(PhaseStartPayload)) (*nats.Subscription, error) {
	return c.conn.Subscribe(c.subject("phase", "start"), func(msg *nats.Msg) {
		var p PhaseStartPayload
		if err := json.Unmarshal(msg.Data, &p); err == nil {
			handler(p)
		}
	})
}

// SubscribeRoundStart subscribes to round start signals
func (c *NATSClient) SubscribeRoundStart(handler func(RoundStartPayload)) (*nats.Subscription, error) {
	return c.conn.Subscribe(c.subject("round", "start"), func(msg *nats.Msg) {
		var p RoundStartPayload
		if err := json.Unmarshal(msg.Data, &p); err == nil {
			handler(p)
		}
	})
}

// SubscribeAgentInput subscribes to agent input messages
func (c *NATSClient) SubscribeAgentInput(agentID string, handler func(PhaseInputPayload)) (*nats.Subscription, error) {
	return c.conn.Subscribe(c.subject("agent", agentID, "input"), func(msg *nats.Msg) {
		var p PhaseInputPayload
		if err := json.Unmarshal(msg.Data, &p); err == nil {
			handler(p)
		}
	})
}

// --- Internal ---

func (c *NATSClient) publish(subjectSuffix string, payload any) error {
	data, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("failed to marshal payload: %w", err)
	}
	return c.conn.Publish(c.subject(subjectSuffix), data)
}
