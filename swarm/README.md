# swarm/

> **Darwinian AI Arena** — 4 LLM agents debate fake news. Losers die. Winners clone. Natural selection for persuasion.

```
    "The least convincing shall perish."
                    — Darwin, probably
```

## TL;DR

```bash
export MISTRAL_API_KEY="sk-..."
go run . --nats-url "nats://demo.nats.io:4222"

# Another terminal: feed fake news each round
nats pub "arena.<session_id>.input.fakenews" "5G towers cause COVID"
```

Watch AI agents argue, vote, die, and clone in real-time.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              ORCHESTRATOR                                    │
│                    main.go — game loop, scoring, selection                   │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │                         PHASE RUNNER                                 │   │
│   │              sync.WaitGroup + goroutines per agent                   │   │
│   │                                                                      │   │
│   │    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│   │    │ Agent 1  │  │ Agent 2  │  │ Agent 3  │  │ Agent 4  │            │   │
│   │    │ goroutine│  │ goroutine│  │ goroutine│  │ goroutine│            │   │
│   │    └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │   │
│   │         │             │             │             │                  │   │
│   └─────────┼─────────────┼─────────────┼─────────────┼──────────────────┘   │
│             │             │             │             │                      │
│             ▼             ▼             ▼             ▼                      │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │                     MISTRAL SMALL API                                │   │
│   │                 net/http — no SDK, raw JSON                          │   │
│   │              concurrent requests with context.WithTimeout            │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────┬───────────────────────────────────────────┘
                                   │
                                   │ NATS pub/sub
                                   │
          ┌────────────────────────┴────────────────────────┐
          │                                                 │
          ▼                                                 ▼
   ┌──────────────┐                                  ┌──────────────┐
   │   INPUTS     │                                  │   OUTPUTS    │
   │              │                                  │              │
   │ arena.<sid>. │                                  │ arena.<sid>. │
   │ input.       │                                  │ event.death  │
   │ fakenews     │                                  │ event.clone  │
   │              │                                  │ state.global │
   │ (you publish │                                  │ agent.*.out  │
   │  fake news)  │                                  │              │
   └──────────────┘                                  └──────────────┘
          │                                                  │
          │            ┌──────────────────────┐              │
          └───────────►│   EXTERNAL CLIENTS   │◄─────────────┘
                       │                      │
                       │  - Web dashboards    │
                       │  - CLI observers     │
                       │  - Replay systems    │
                       │  - Your wild ideas   │
                       └──────────────────────┘
```

---

## Game Flow

```
Round N (5 rounds total)
│
├─► Phase 1: COGITATION          ← each agent analyzes fake news privately
│       └─► 4 goroutines → Mistral API (parallel)
│
├─► Phase 2: PUBLIC TAKE         ← agents publish their arguments
│       └─► 4 goroutines → Mistral API (parallel)
│
├─► Phase 3: REVISION            ← agents read others, may change mind
│       └─► 4 goroutines → Mistral API (parallel)
│
├─► Phase 4: VOTING              ← agents rank each other's persuasiveness
│       └─► 4 goroutines → Mistral API (parallel)
│
└─► NATURAL SELECTION
        ├─► Lowest score → DEATH  (moved to graveyard/)
        └─► Highest score → CLONE (new agent with mutated personality)
```

**Result**: After 5 rounds, only the most persuasive ideological lineage survives.

---

## Concurrency Model

```go
// Each phase runs all agents in parallel
func (pr *PhaseRunner) RunPhase1(round int) map[string]*AgentMessage {
    var wg sync.WaitGroup

    for _, agent := range pr.session.Agents {
        wg.Add(1)
        go func(a *Agent) {
            defer wg.Done()

            ctx, cancel := context.WithTimeout(context.Background(), pr.timeout)
            defer cancel()

            // Each agent calls Mistral concurrently
            response := pr.executePhase1(ctx, a, round)

            mu.Lock()
            responses[a.ID] = response
            mu.Unlock()
        }(agent)
    }

    wg.Wait()  // Barrier: all agents must complete before next phase
    return responses
}
```

**Why goroutines?**
- 4 agents × 4 phases = 16 API calls per round
- Sequential: ~48s (3s per call)
- Parallel: ~12s (4 calls batched)
- **4x speedup** per round

---

## NATS Event Bus

Real-time pub/sub for external observers. Zero coupling.

### Input (You → Game)

```bash
# Start a session
nats pub "arena.init" '{"session_id":"550e8400-e29b-41d4-a716-446655440000"}'

# Feed fake news each round (game blocks until received)
nats pub "arena.<sid>.input.fakenews" "Elon Musk is actually 3 raccoons in a trenchcoat"
```

### Output (Game → You)

```bash
# Subscribe to everything
nats sub "arena.<sid>.>"

# Or specific events
nats sub "arena.<sid>.event.death"    # Agent eliminations
nats sub "arena.<sid>.event.clone"    # Agent cloning
nats sub "arena.<sid>.state.global"   # Full game state after each phase
nats sub "arena.<sid>.agent.*.output" # Individual agent responses
```

### Topic Reference

| Topic | Payload | Description |
|-------|---------|-------------|
| `arena.init` | `{session_id}` | Launch new game |
| `arena.<sid>.input.fakenews` | `string` | Fake news for current round |
| `arena.<sid>.input.waiting` | `{round}` | Game waiting for input |
| `arena.<sid>.event.death` | `{agent, round}` | Agent eliminated |
| `arena.<sid>.event.clone` | `{parent, child}` | Agent cloned |
| `arena.<sid>.state.global` | `GlobalState` | Full snapshot |
| `arena.<sid>.agent.<aid>.output` | `AgentMessage` | Agent response |

---

## Agent Personalities

Each agent has a **political color** (0.0 → 1.0):

```
0.0          0.2          0.5          0.8          1.0
 │            │            │            │            │
 ▼            ▼            ▼            ▼            ▼
FAR-RIGHT   RIGHT      CENTER       LEFT      FAR-LEFT
conspiracy  pragmatic  balanced    systemic   anti-establishment
emotional   fact-based diplomatic  justice    class-based
```

**Mutation**: After each round, agents may shift their political color based on debate influence.

**Cloning**: New agents inherit parent's color ± small random drift.

---

## Session Persistence

Everything persists to disk as Markdown. Git-friendly. Human-readable.

```
sessions/<uuid>/
├── global.json                 # Omniscient game state
├── chat/
│   ├── T1_phase2.md           # Round 1 public debate
│   ├── T1_phase3.md           # Round 1 final takes
│   └── ...
├── agents/
│   └── <name>/
│       ├── AGENT.md           # Identity, config
│       ├── SOUL.md            # Personality prompt
│       └── memory/
│           ├── T1.md          # What happened in round 1
│           └── ...
└── graveyard/                  # Dead agents
    └── <name>/
        ├── AGENT.md
        ├── SOUL.md
        ├── DEATH.md           # Cause of death, final score
        └── memory/
```

---

## Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Language | **Go 1.24** | Goroutines, fast compilation, single binary |
| LLM | **Mistral Small** | Fast, cheap, good at structured output |
| HTTP | `net/http` | No SDK bloat, raw JSON, full control |
| Messaging | **NATS** | Lightweight pub/sub, no broker setup needed |
| Concurrency | `sync.WaitGroup` | Simple barrier synchronization |
| Storage | Markdown files | Human-readable, git-diffable, LLM-friendly |

**Total dependencies**: 1 (`github.com/nats-io/nats.go`)

---

## Quick Start

```bash
# Clone
git clone https://github.com/edouard-claude/mistral-worldwide-hacks-2k26
cd mistral-worldwide-hacks-2k26/swarm

# Build
go build -o swarm .

# Run (uses demo NATS server by default)
export MISTRAL_API_KEY="sk-..."
./swarm

# In another terminal, start a session
nats pub "arena.init" '{"session_id":"test-001"}'

# Feed fake news for each round
nats pub "arena.test-001.input.fakenews" "WiFi causes cancer"
nats pub "arena.test-001.input.fakenews" "Birds aren't real"
nats pub "arena.test-001.input.fakenews" "Finland doesn't exist"
nats pub "arena.test-001.input.fakenews" "Mattresses double in weight from dust mites"
nats pub "arena.test-001.input.fakenews" "We only use 10% of our brain"
```

### CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--nats-url` | `nats://demo.nats.io:4222` | NATS server |
| `--timeout` | `30s` | Mistral API timeout per call |
| `--dir` | `.` | Session storage directory |

---

## Example Output

```
=== FakeNews Arena - Multi-Session Dispatcher ===
Connecté à NATS: nats://demo.nats.io:4222

🚀 Init reçu pour session: test-001
[test-001] Nouvelle session créée
[test-001] --- Agents ---
[test-001]   Marcus (couleur: 0.05 - Far-right, temp: 0.70)
[test-001]   Elena (couleur: 0.30 - Right, temp: 0.50)
[test-001]   Victor (couleur: 0.75 - Left, temp: 0.50)
[test-001]   Luna (couleur: 0.95 - Far-left, temp: 0.70)

[test-001] ========== ROUND 1 ==========
[test-001] 📰 Fake news: "WiFi causes cancer"

[test-001] --- Phase 1: Cogitation ---
[test-001]   [Marcus] Confidence: 4/5
[test-001]   [Elena] Confidence: 2/5
[test-001]   [Victor] Confidence: 1/5
[test-001]   [Luna] Confidence: 1/5

[test-001] --- Phase 4: Voting ---
[test-001] 💀 DEATH: Marcus (lowest score)
[test-001] 🧬 CLONE: Elena → Dante

...

[test-001] ========== GAME OVER ==========
[test-001] 🏆 Survivors: Elena, Victor, Dante, Aria
[test-001] ⚰️  Graveyard: Marcus (R1), Luna (R2), Felix (R3), Nova (R4)
```

---

## License

MIT

---

*Built for MISTRAL WORLDWIDE HACKS 2K26*
