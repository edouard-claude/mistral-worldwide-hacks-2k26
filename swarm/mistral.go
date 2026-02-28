package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"
)

const mistralURL = "MISTRAL_URL_PLACEHOLDER"

// MistralClient handles communication with the Mistral API
type MistralClient struct {
	apiKey     string
	httpClient *http.Client
	timeout    time.Duration
}

// MistralRequest is the request payload for Mistral API
type MistralRequest struct {
	Model       string           `json:"model"`
	Messages    []MistralMessage `json:"messages"`
	Temperature float64          `json:"temperature"`
	MaxTokens   int              `json:"max_tokens"`
}

// MistralMessage represents a chat message
type MistralMessage struct {
	Role    string `json:"role"` // "system", "user", "assistant"
	Content string `json:"content"`
}

// MistralResponse is the response from Mistral API
type MistralResponse struct {
	Choices []struct {
		Message MistralMessage `json:"message"`
	} `json:"choices"`
	Error *struct {
		Message string `json:"message"`
	} `json:"error,omitempty"`
}

// NewMistralClient creates a new Mistral API client
func NewMistralClient(timeout time.Duration) (*MistralClient, error) {
	// API key is optional - if set, it will be used in Authorization header
	apiKey := os.Getenv("MISTRAL_API_KEY")

	return &MistralClient{
		apiKey: apiKey,
		httpClient: &http.Client{
			Timeout: timeout,
		},
		timeout: timeout,
	}, nil
}

// Complete sends a chat completion request to Mistral
func (c *MistralClient) Complete(ctx context.Context, systemPrompt, userPrompt string, temperature float64) (string, error) {
	req := MistralRequest{
		Model: "mistral-small-3.2",
		Messages: []MistralMessage{
			{Role: "system", Content: systemPrompt},
			{Role: "user", Content: userPrompt},
		},
		Temperature: temperature,
		MaxTokens:   650, // ~200 mots max par réponse
	}

	body, err := json.Marshal(req)
	if err != nil {
		return "", fmt.Errorf("failed to marshal request: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, "POST", mistralURL, bytes.NewReader(body))
	if err != nil {
		return "", fmt.Errorf("failed to create request: %w", err)
	}

	httpReq.Header.Set("Content-Type", "application/json")
	if c.apiKey != "" {
		httpReq.Header.Set("Authorization", "Bearer "+c.apiKey)
	}

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return "", fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("API error (status %d): %s", resp.StatusCode, string(respBody))
	}

	var mistralResp MistralResponse
	if err := json.Unmarshal(respBody, &mistralResp); err != nil {
		return "", fmt.Errorf("failed to parse response: %w", err)
	}

	if mistralResp.Error != nil {
		return "", fmt.Errorf("API error: %s", mistralResp.Error.Message)
	}

	if len(mistralResp.Choices) == 0 {
		return "", fmt.Errorf("no choices in response")
	}

	return mistralResp.Choices[0].Message.Content, nil
}

// CompleteJSON sends a request expecting JSON response and parses it
func (c *MistralClient) CompleteJSON(ctx context.Context, systemPrompt, userPrompt string, temperature float64, result any) error {
	content, err := c.Complete(ctx, systemPrompt, userPrompt, temperature)
	if err != nil {
		return err
	}

	// Try to extract JSON from the response (handle markdown code blocks)
	jsonContent := extractJSON(content)

	if err := json.Unmarshal([]byte(jsonContent), result); err != nil {
		return fmt.Errorf("failed to parse JSON response: %w (content: %s)", err, content)
	}

	return nil
}

// extractJSON attempts to extract JSON from a response that might be wrapped in markdown
func extractJSON(content string) string {
	if len(content) < 3 {
		return content
	}

	// Check if content is wrapped in ```json ... ``` or ``` ... ```
	start := 0
	end := len(content)

	// Find opening ```
	for i := 0; i < len(content)-2; i++ {
		if content[i:i+3] == "```" {
			// Skip optional "json" after ```
			start = i + 3
			for start < len(content) && content[start] != '\n' {
				start++
			}
			if start < len(content) {
				start++ // skip newline
			}
			break
		}
	}

	// Find closing ```
	for i := len(content) - 1; i >= 2; i-- {
		if i-2 >= 0 && content[i-2:i+1] == "```" {
			end = i - 2
			// Trim trailing newline before ```
			for end > 0 && (content[end-1] == '\n' || content[end-1] == '\r') {
				end--
			}
			break
		}
	}

	// Guard against invalid slice bounds
	if start >= end || start >= len(content) || end <= 0 {
		return content
	}

	return content[start:end]
}
