# Mistralski — Game Master Agent

> Autonomous adversarial AI for the GORAFI SIMULATOR. Powered by Mistral Large with function calling.

## What is Mistralski?

Mistralski is the **Game Master** of the Gorafi Simulator — a satirical disinformation game where the player tries to maximize global "decerebration" by choosing between real, fake, and satirical news.

The GM plays as **Eric Cartman** (megalomaniac, passive-aggressive, vindictive) and has two jobs:
1. **Generate 3 news** per turn for the player to choose from
2. **Secretly manipulate** the player into choosing the news that maximizes chaos

It is an **autonomous agent** with persistent memory, per-agent vision files, and multi-turn strategy — all driven by Mistral Large function calling.

## Architecture

```
┌────────────┐     SSE      ┌──────────────┐    HTTP+WS    ┌──────────────┐
│  Lovable   │ ◄──────────► │  Mistralski  │ ◄───────────► │  wh26 relay  │
│ (frontend) │              │  play_web.py │               │  (Go backend)│
└────────────┘              └──────┬───────┘               └──────┬───────┘
                                   │                              │
                          Mistral Large API               Swarm arena agents
                          (function calling)              (Mistral Small 3.2)
```

## Endpoints (for Lovable)

Base URL: `http://<host>:8899`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/start` | GET | Start a new game, returns `session_id`, indices, agents |
| `/api/stream/propose` | GET → SSE | GM thinks + proposes 3 news (real/fake/satirical) with title + full article |
| `/api/stream/choose?kind=<choice>` | GET → SSE | Resolve choice: GM reaction → agent debates → indices update → strategy |
| `/api/state` | GET | Current game state (for resync) |
| `/api/wh26` | GET | Arena connection status |

## GM Agent Capabilities

### Function Calling Tools (5 tools)

| Tool | Description |
|------|-------------|
| `read_game_memory` | Global stats: total turns, choice history, most effective news type, decerebration |
| `read_turn_log` | Per-turn log: chosen news, index deltas, agent reactions, who resisted/amplified |
| `read_agent_vision` | GM's mental dossier on a specific agent (threat, pattern, vulnerability, strategy) |
| `update_agent_vision` | Write/update the dossier — the LLM decides what to write |
| `list_memory_files` | List all memory files available |

### Agentic Loop

```
Phase 1 — Tool calling (auto):
  GM reads memory → reads agent visions → optionally reads turn logs
  GM writes updated agent visions (after strategy analysis)

Phase 2 — JSON generation:
  GM produces structured JSON output (news proposals or strategy)
```

### Player Manipulation System

The GM maintains two secret fields in its strategy (never sent to the frontend):

- `desired_pick`: which news type it wants the player to choose next turn
- `manipulation_tactic`: how to steer the player (reverse psychology, flattery, provocation, guilt trip, etc.)

On the next turn, the GM applies the tactic:
- Makes the desired news more appealing (punchier title, captivating body)
- Makes other news duller
- Uses `gm_commentary` as the primary manipulation weapon (Cartman-style quips)

The player never knows they're being manipulated.

## SSE Event Types

### During `/api/stream/propose`

| Event type | Description |
|-----------|-------------|
| `phase` | GM processing phase (tool_loop, json_generation, done) |
| `llm_call` | LLM API call number |
| `tool_call` | Tool invocation (name + args) |
| `tool_result` | Tool response (truncated) |
| `llm_text` | GM's reasoning text (Cartman inner monologue) |
| `vision_update` | Agent dossier updated |
| `proposal` | **The 3 news** — `{real, fake, satirical}` each with `text`, `body`, `stat_impact` |
| `heartbeat` | Keepalive (ignore) |
| `result` | Stream complete |

### During `/api/stream/choose`

| Event type | Description |
|-----------|-------------|
| `choice_resolved` | GM's reaction to the player's choice |
| `agent_nats` | Individual agent reaction from arena (or placeholder) |
| `agent_death` | Agent eliminated |
| `agent_clone` | Agent cloned |
| `reactions` | Summary of all agent reactions |
| `indices_update` | New global indices + decerebration score |
| `strategy` | GM's analysis, threats, weak spots, next turn plan, long-term goal |
| `turn_update` | New turn number |
| `end` | Game over (win/lose/draw) |

## Tech Stack

- **Python 3.11+**, FastAPI, Pydantic v2, structlog
- **Mistral Large API** — function calling for autonomous tool use
- **SSE streaming** — real-time event delivery to frontend
- **WebSocket client** — connection to wh26 backend relay for arena agent debates
- **File-based memory** — turn logs, cumulative stats, per-agent vision files in markdown

## Running Locally

```bash
# Install deps
pip install -e ".[dev]"

# Set Mistral API key
echo "MISTRAL_API_KEY=your_key" > .env

# Run
python3 scripts/play_web.py
# → http://localhost:8899 (built-in debug UI)
# → Expose with ngrok for Lovable: ngrok http 8899
```

## Project Structure

```
mistralski/
├── scripts/
│   └── play_web.py          # FastAPI server + SSE endpoints + wh26 integration
├── src/
│   ├── agents/
│   │   └── game_master_agent.py  # Autonomous GM with Mistral function calling
│   ├── models/
│   │   ├── world.py          # NewsHeadline (text + body), GlobalIndices
│   │   ├── game.py           # GameState, NewsProposal, GMStrategy
│   │   └── agent.py          # AgentState, AgentReaction
│   └── core/
│       └── config.py         # Pydantic Settings (.env)
├── config/
│   ├── game.yaml             # Turn mechanics, action definitions
│   ├── agents.yaml           # Agent archetypes
│   └── countries.yaml        # Country list with initial stats
└── pyproject.toml
```
