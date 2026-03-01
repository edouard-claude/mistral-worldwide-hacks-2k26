package main

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// EnsureDir creates a directory if it doesn't exist
func EnsureDir(path string) error {
	return os.MkdirAll(path, 0755)
}

// WriteFile writes content to a file, creating directories as needed
func WriteFile(path, content string) error {
	dir := filepath.Dir(path)
	if err := EnsureDir(dir); err != nil {
		return fmt.Errorf("failed to create directory %s: %w", dir, err)
	}
	return os.WriteFile(path, []byte(content), 0644)
}

// ReadFile reads a file and returns its content
func ReadFile(path string) (string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	return string(data), nil
}

// FileExists checks if a file exists
func FileExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}

// ReadAllMemories reads all memory files from a memory directory
func ReadAllMemories(memoryDir string) (string, error) {
	if !FileExists(memoryDir) {
		return "", nil
	}

	entries, err := os.ReadDir(memoryDir)
	if err != nil {
		return "", fmt.Errorf("failed to read memory directory: %w", err)
	}

	// Sort by filename (T1.md, T2.md, etc.)
	var files []string
	for _, e := range entries {
		if !e.IsDir() && strings.HasSuffix(e.Name(), ".md") {
			files = append(files, e.Name())
		}
	}
	sort.Strings(files)

	var memories []string
	for _, f := range files {
		content, err := ReadFile(filepath.Join(memoryDir, f))
		if err != nil {
			continue
		}
		memories = append(memories, content)
	}

	return strings.Join(memories, "\n---\n"), nil
}

// MoveDir moves a directory from src to dst
func MoveDir(src, dst string) error {
	// First try rename (works if on same filesystem)
	if err := os.Rename(src, dst); err == nil {
		return nil
	}

	// If rename fails, do copy + delete
	if err := CopyDir(src, dst); err != nil {
		return fmt.Errorf("failed to copy directory: %w", err)
	}

	return os.RemoveAll(src)
}

// CopyDir recursively copies a directory
func CopyDir(src, dst string) error {
	srcInfo, err := os.Stat(src)
	if err != nil {
		return err
	}

	if err := os.MkdirAll(dst, srcInfo.Mode()); err != nil {
		return err
	}

	entries, err := os.ReadDir(src)
	if err != nil {
		return err
	}

	for _, entry := range entries {
		srcPath := filepath.Join(src, entry.Name())
		dstPath := filepath.Join(dst, entry.Name())

		if entry.IsDir() {
			if err := CopyDir(srcPath, dstPath); err != nil {
				return err
			}
		} else {
			if err := CopyFile(srcPath, dstPath); err != nil {
				return err
			}
		}
	}

	return nil
}

// CopyFile copies a single file
func CopyFile(src, dst string) error {
	data, err := os.ReadFile(src)
	if err != nil {
		return err
	}

	srcInfo, err := os.Stat(src)
	if err != nil {
		return err
	}

	return os.WriteFile(dst, data, srcInfo.Mode())
}

// WriteAgentFiles writes AGENT.md and SOUL.md for an agent
func WriteAgentFiles(agent *Agent, session *Session) error {
	// Write AGENT.md
	agentPath := filepath.Join(agent.SessionDir, "AGENT.md")
	if err := WriteFile(agentPath, GenerateAgentMD(agent, session)); err != nil {
		return fmt.Errorf("failed to write AGENT.md: %w", err)
	}

	// Write SOUL.md
	soulPath := filepath.Join(agent.SessionDir, "SOUL.md")
	if err := WriteFile(soulPath, GenerateSoulMD(agent.Name, agent.PoliticalColor, session.Lang)); err != nil {
		return fmt.Errorf("failed to write SOUL.md: %w", err)
	}

	// Ensure memory directory exists
	memoryDir := filepath.Join(agent.SessionDir, "memory")
	if err := EnsureDir(memoryDir); err != nil {
		return fmt.Errorf("failed to create memory directory: %w", err)
	}

	return nil
}

// WriteMemory writes a memory file for an agent's round
func WriteMemory(agent *Agent, round int, content string) error {
	memoryPath := filepath.Join(agent.SessionDir, "memory", fmt.Sprintf("T%d.md", round))
	return WriteFile(memoryPath, content)
}

// WriteChat writes a chat file for a round/phase
func WriteChat(session *Session, round, phase int, messages []*AgentMessage) error {
	chatPath := filepath.Join(session.Dir, "chat", fmt.Sprintf("T%d_phase%d.md", round, phase))
	return WriteFile(chatPath, GenerateChatMD(round, phase, messages, session.Lang))
}

// WriteDeath writes DEATH.md for a dead agent
func WriteDeath(agent *Agent, round, score, lastConfidence int, lastMessage string, rankings map[string]int, lang string) error {
	deathPath := filepath.Join(agent.SessionDir, "DEATH.md")
	return WriteFile(deathPath, GenerateDeathMD(agent, round, score, lastConfidence, lastMessage, rankings, lang))
}

// BuildSystemPrompt builds the system prompt for an agent
func BuildSystemPrompt(agent *Agent) (string, error) {
	agentMD, err := ReadFile(filepath.Join(agent.SessionDir, "AGENT.md"))
	if err != nil {
		return "", fmt.Errorf("failed to read AGENT.md: %w", err)
	}

	soulMD, err := ReadFile(filepath.Join(agent.SessionDir, "SOUL.md"))
	if err != nil {
		return "", fmt.Errorf("failed to read SOUL.md: %w", err)
	}

	memories, _ := ReadAllMemories(filepath.Join(agent.SessionDir, "memory"))

	var sb strings.Builder
	sb.WriteString(agentMD)
	sb.WriteString("\n---\n")
	sb.WriteString(soulMD)
	if memories != "" {
		sb.WriteString("\n---\n")
		sb.WriteString("# Mémoire des tours précédents\n\n")
		sb.WriteString(memories)
	}

	return sb.String(), nil
}
