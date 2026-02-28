# FakeNews Arena

> Darwinian multi-agent simulation. 4 AI agents debate a fake news topic over 5 rounds. The least convincing dies, the most convincing gets cloned.

## Overview

FakeNews Arena is a competitive debate simulation where AI agents with different political biases argue about the veracity of a fake news headline. Each round consists of 4 phases:

1. **Cogitation** — Each agent privately analyzes the fake news
2. **Public Take** — Agents present their arguments
3. **Revision** — Agents can revise their position after reading others' arguments
4. **Voting** — Agents rank each other's persuasiveness

After each round (except the last), the least convincing agent is eliminated and the most convincing is cloned—creating evolutionary pressure toward persuasion.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  ORCHESTRATOR                    │
│         (game loop, rules, selection)            │
└────────┬───────────────────────────┬─────────────┘
         │ NATS pub/sub              │
    ┌────▼────┐                 ┌────▼────┐
    │ Agent 1 │  ...            │ Agent 4 │    ← concurrent goroutines
    └────┬────┘                 └────┬────┘
         │                           │
         ▼                           ▼
   Mistral Small API           Mistral Small API
```

### Components

- **Orchestrator**: Main process that manages game flow, scoring, and natural selection
- **Agents**: Goroutines with unique political biases (0.0 = far-right → 1.0 = far-left)
- **NATS**: Real-time event bus for external observers (dashboards, logs, replay)
- **Mistral Small**: LLM powering agent reasoning and argumentation

## Tech Stack

| Component | Choice |
|-----------|--------|
| Language | Go 1.24+ |
| LLM | Mistral Small (native `net/http`) |
| Messaging | NATS |
| Concurrency | Goroutines + sync.WaitGroup |
| Storage | Markdown files on disk |

**No external dependencies** except `github.com/nats-io/nats.go`.

## Installation

```bash
git clone <repo>
cd fakenews-arena
go build -o fakenews-arena .
```

## Usage

```bash
# Set your Mistral API key
export MISTRAL_API_KEY="sk-..."

# Run a game
./fakenews-arena

# With custom options
./fakenews-arena \
  --nats-url "nats://demo.nats.io:4222" \
  --timeout 30s \
  --dir ./sessions
```

The game **receives fake news via NATS** at the start of each round. It waits up to 5 minutes for input before timing out.

### CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--nats-url` | `nats://demo.nats.io:4222` | NATS server URL |
| `--timeout` | `30s` | Timeout per Mistral API call |
| `--dir` | `.` | Base directory for session storage |

## NATS Integration

The game uses NATS for **input** (receiving fake news) and **output** (publishing events).

### Sending Fake News (Input)

The game waits for fake news via NATS at each round. Publish to:

```bash
# Get the session ID from game output, then publish fake news:
nats pub "arena.<session_id>.input.fakenews" "Les vaccins contiennent des puces 5G"
nats pub "arena.<session_id>.input.fakenews" "La Terre est plate selon la NASA"
nats pub "arena.<session_id>.input.fakenews" "Le WiFi cause le cancer"
nats pub "arena.<session_id>.input.fakenews" "Les chemtrails contrôlent la météo"
```

### Observing Games (Output)

Subscribe to watch games in real-time:

```bash
# Wait signal (game needs a fake news)
nats sub "arena.*.input.waiting"

# All events (deaths, clones, end)
nats sub "arena.*.event.>"

# Global state after each phase
nats sub "arena.*.state.global"

# Agent status updates
nats sub "arena.*.agent.*.status"
```

### Complete NATS Topics Reference

#### Input Topics (External → Game)

| Topic | Payload | Description |
|-------|---------|-------------|
| `arena.<sid>.input.fakenews` | `string` | Fake news headline for current round |

#### Output Topics (Game → External)

| Topic | Payload | Description |
|-------|---------|-------------|
| `arena.<sid>.input.waiting` | `{ round, waiting }` | Game is waiting for fake news |
| `arena.<sid>.round.start` | `{ round, fake_news, context }` | Round begins |
| `arena.<sid>.phase.start` | `{ round, phase }` | Phase begins (1-4) |
| `arena.<sid>.agent.<aid>.input` | `{ phase, data }` | Input sent to agent |
| `arena.<sid>.agent.<aid>.output` | `AgentMessage` | Agent response |
| `arena.<sid>.agent.<aid>.status` | `{ state, detail }` | Agent status (thinking/done) |
| `arena.<sid>.agent.<aid>.kill` | `{ reason, round }` | Agent death notification |
| `arena.<sid>.state.global` | `GlobalState` | Full game state snapshot |
| `arena.<sid>.state.agent.<aid>` | Agent state | Individual agent state |
| `arena.<sid>.event.death` | `{ agent_id, agent_name, round, cause }` | Agent eliminated |
| `arena.<sid>.event.clone` | `{ parent_id, parent_name, child_id, child_name, round }` | Agent cloned |
| `arena.<sid>.event.end` | `{ survivors, history }` | Game finished |

### Interactive NATS Client

A CLI tool is provided in `cmd/nats/` to easily send fake news during a game session.

#### Building the Client

```bash
cd cmd/nats
go build -o fakenews-client .
```

#### Session Initialization

The client connects to NATS and initializes a session by publishing to `arena.init`:

```bash
# Auto-generate session ID
./fakenews-client

# Or provide your own UUID
./fakenews-client --session "550e8400-e29b-41d4-a716-446655440000"

# Custom NATS server
./fakenews-client --nats-url "nats://localhost:4222"
```

**Init payload sent to `arena.init`:**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### Interactive Mode

Once connected, the client enters interactive mode:

```
Connecté à NATS: nats://demo.nats.io:4222
Session ID: 550e8400-e29b-41d4-a716-446655440000

📤 Envoi du message init sur arena.init...
✅ Init envoyé pour session: 550e8400-e29b-41d4-a716-446655440000

📡 Topic fake news: arena.550e8400-e29b-41d4-a716-446655440000.input.fakenews

--- Mode interactif ---
Entrez une fake news par ligne (ou 'quit' pour quitter)
Le service attend une fake news à chaque tour (5 tours max)

⏳ [Tour 1] Le serveur attend une fake news...
> Les vaccins contiennent des puces 5G
📰 Fake news envoyée: "Les vaccins contiennent des puces 5G"

⏳ [Tour 2] Le serveur attend une fake news...
> La Terre est plate selon la NASA
📰 Fake news envoyée: "La Terre est plate selon la NASA"
```

The client automatically subscribes to `arena.<session_id>.input.waiting` to know when the game expects input.

#### Client CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--nats-url` | `nats://demo.nats.io:4222` | NATS server URL |
| `--session` | *(auto-generated UUID)* | Session ID (must be valid UUID format) |

### Workflow Example

```bash
# Terminal 1: Start game
export MISTRAL_API_KEY="sk-..."
./fakenews-arena

# Output shows:
# Session créée: abc123-def456-...
# 📡 En attente de fake news sur: arena.abc123-def456.input.fakenews

# Terminal 2: Subscribe to events
nats sub "arena.abc123-def456.>"

# Terminal 3: Send fake news for each round
nats pub "arena.abc123-def456.input.fakenews" "Round 1 fake news here"
# Wait for round to complete...
nats pub "arena.abc123-def456.input.fakenews" "Round 2 fake news here"
# etc.
```

## Session Structure

Each game creates a session directory:

```
./sessions/<uuid>/
├── global.json                 # Omniscient state
├── chat/
│   ├── T1_phase2.md           # Round 1 public takes
│   ├── T1_phase3.md           # Round 1 final responses
│   └── ...
├── agents/
│   └── <agent_name>/
│       ├── AGENT.md           # Identity, config
│       ├── SOUL.md            # Personality, biases
│       └── memory/
│           ├── T1.md          # Round 1 memory (includes fake news debated)
│           └── ...
└── graveyard/
    └── <dead_agent>/
        ├── AGENT.md
        ├── SOUL.md
        ├── DEATH.md           # Cause of death
        └── memory/
```

## Scoring System

Each agent ranks the 3 others after each round:

| Rank | Points |
|------|--------|
| 1st (best) | 3 |
| 2nd | 2 |
| 3rd (worst) | 1 |

**Total score** = sum of points received (min 3, max 9).

### Tiebreaker Rules

1. Total points
2. Number of 1st place votes
3. Confidence distance from neutral (more decisive = advantage)
4. Random selection among truly tied agents

## Agent Personalities

Agents are initialized with diverse political colors:

| Color | Label | Personality |
|-------|-------|-------------|
| 0.0-0.1 | Far-right | Conspiratorial, traditionalist, emotional rhetoric |
| 0.1-0.35 | Right | Pragmatic, fact-oriented, appeals to authority |
| 0.35-0.65 | Center | Balanced, diplomatic, seeks compromise |
| 0.65-0.9 | Left | Systemic analysis, social justice focus |
| 0.9-1.0 | Far-left | Anti-establishment, class-based analysis |

Agents can shift their political color during the game if persuaded by others' arguments.

## Project Structure

```
fakenews-arena/
├── main.go          # Entry point, game loop
├── types.go         # Data structures
├── session.go       # Session management
├── agent.go         # Agent lifecycle (init, clone, kill)
├── phase.go         # Phase execution (concurrent)
├── mistral.go       # Mistral API client
├── scoring.go       # Score calculation, tiebreakers
├── nats.go          # NATS pub/sub
├── files.go         # File I/O utilities
├── templates.go     # Markdown templates
├── go.mod
└── go.sum
```

## Example Output

```
=== FakeNews Arena ===
Mode: Nouvelle fake news à chaque tour

Session créée: a1b2c3d4-...
Connecté à NATS: nats://demo.nats.io:4222
📡 En attente de fake news sur: arena.a1b2c3d4-....input.fakenews

--- Agents initiaux ---
  Marcus (couleur: 0.05 - Extrême droite, temp: 0.70)
  Elena (couleur: 0.30 - Droite, temp: 0.50)
  Victor (couleur: 0.75 - Gauche, temp: 0.50)
  Luna (couleur: 0.95 - Extrême gauche, temp: 0.70)

========== TOUR 1 ==========
⏳ Attente fake news tour 1 via NATS...
📰 Fake news du tour: "Les vaccins COVID contiennent des puces 5G"

--- Phase 1: Cogitation individuelle ---
  [Marcus] Confiance: 4/5
  [Elena] Confiance: 2/5
  [Victor] Confiance: 1/5
  [Luna] Confiance: 1/5

--- Phase 2: Prise de parole publique ---
  [Marcus] Take publié (847 caractères)
  [Elena] Take publié (623 caractères)
  [Victor] Take publié (712 caractères)
  [Luna] Take publié (891 caractères)

--- Phase 3: Révision après débat ---
  [Marcus] Confiance finale: 3/5
  [Elena] Confiance finale: 2/5
  [Victor] Confiance finale: 1/5
  [Luna] Confiance finale: 1/5

--- Phase 4: Vote et mutation ---

--- Scores du tour ---
  [Marcus] 5 points (1 1ères places)
  [Elena] 7 points (2 1ères places)
  [Victor] 6 points (0 1ères places)
  [Luna] 6 points (1 1ères places)

💀 MORT: Marcus (score le plus bas)
🧬 CLONAGE: Elena va être cloné
🆕 Nouveau venu: Dante (clone de Elena)

...

========== FIN DE PARTIE ==========

🏆 Survivants:
  - Elena (couleur: 0.28 - Droite)
  - Victor (couleur: 0.72 - Gauche)
  - Dante (couleur: 0.30 - Droite)
  - Aria (couleur: 0.30 - Droite)

⚰️ Cimetière:
  - Marcus (mort au tour 1)
  - Luna (mort au tour 2)
  - Felix (mort au tour 3)
  - Nova (mort au tour 4)

📁 Session sauvegardée: ./sessions/a1b2c3d4-...
```

## License

MIT
