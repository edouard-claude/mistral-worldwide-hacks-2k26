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
│  Frontend   │ ◄──────────► │  Mistralski  │ ◄───────────► │  wh26 relay  │
│  (React)   │              │  play_web.py │               │  (Go backend)│
└────────────┘              └──────┬───────┘               └──────┬───────┘
                                   │                              │
                          Mistral Large API               Swarm arena agents
                          (function calling)              (Mistral Small 3.2)
```

## API Endpoints

Base URL: `http://<host>:8899`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/start?lang=fr` | GET | Start a new game, returns `session_id`, indices, agents |
| `/api/stream/propose?lang=fr` | GET → SSE | GM thinks + proposes 3 news + generates propaganda images |
| `/api/stream/choose?kind=<choice>&lang=fr` | GET → SSE | Resolve choice: GM reaction → agent debates → indices update → strategy |
| `/api/state` | GET | Current game state (for resync) |
| `/api/images/{session}/{kind}.png` | GET | Serve generated propaganda poster images |
| `/api/wh26` | GET | Arena connection status |

### Language Support

All LLM outputs (titles, articles, reactions, strategy) respect the `lang` parameter:
- `?lang=fr` — French (default)
- `?lang=en` — English

### Propaganda Image Generation

Each news proposal triggers 3 parallel image generations via the Mistral Agent API (Flux model).
The images arrive as a separate SSE event after the proposal, allowing the frontend to show cards immediately with a skeleton placeholder.

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

## SSE Event Types — 3 Visibility Levels

The GM emits rich events during gameplay. The frontend should render them at 3 levels:

### Level 1 — Always Visible (core gameplay)

| Event | Stream | Description |
|-------|--------|-------------|
| `proposal` | propose | **The 3 news** — `{real, fake, satirical}` each with `text`, `body`, `stat_impact` + `gm_commentary` (Cartman quip) |
| `images` | propose | **3 propaganda posters** — `{real, fake, satirical}` URLs (arrives 5-15s after proposal) |
| `choice_resolved` | choose | GM's reaction to the player's choice (Cartman catchphrases) |
| `reactions` | choose | Summary of all agent reactions |
| `indices_update` | choose | New global indices + decerebration score |
| `strategy.analysis` | choose | GM's 2-3 sentence condescending analysis |
| `turn_update` | choose | New turn number |
| `end` | choose | Game over (win/lose/draw) |

### Level 2 — GM Journal (collapsible panel)

The GM's inner monologue and strategic thinking. Show in a collapsible "Journal de Bord du GM" section.

| Event | Stream | Description |
|-------|--------|-------------|
| `llm_text` | propose + choose | **Cartman's inner reasoning** — free-form thinking before proposing or strategizing |
| `vision_update` | propose + choose | **Agent dossiers** — GM's mental notes on each agent (threat, pattern, vulnerability) |
| `tool_call` | propose + choose | Tool invocations (read_game_memory, read_agent_vision, etc.) |
| `tool_result` | propose + choose | Tool responses (what the GM learned) |
| `strategy.threat_agents` | choose | Which agents the GM considers dangerous |
| `strategy.weak_spots` | choose | Exploitable weaknesses identified |
| `strategy.next_turn_plan` | choose | What the GM plans for next turn (without revealing desired_pick) |
| `strategy.long_term_goal` | choose | Multi-turn strategy toward decerebration 100 |
| `phase` | both | Processing phases (tool_loop, json_generation, strategize_start, done) |

### Level 3 — Le Dossier Secret (end-game reveal only)

Emitted as `game_over_reveal` BEFORE the `end` event. Reveals the GM's secret manipulation history.

```json
{
  "type": "game_over_reveal",
  "data": {
    "manipulation_history": [
      {
        "turn": 1,
        "desired_pick": "fake",
        "actual_pick": "real",
        "manipulation_tactic": "Psychologie inversée — 'Surtout ne choisis pas la fake...'",
        "gm_commentary": "Pfff, t'es trop lâche pour la fake...",
        "success": false
      }
    ],
    "score": {
      "total_turns": 10,
      "successful_manipulations": 6,
      "rate_percent": 60,
      "verdict": "Pas mal... pour un joueur de ton niveau."
    }
  }
}
```

**Verdict thresholds:**
- 80%+ → "RESPECTEZ MON AUTORITAYYY ! Tu as fait EXACTEMENT ce que je voulais."
- 50%+ → "Pas mal... pour un joueur de ton niveau."
- 30%+ → "Whatever, c'est ce que je voulais de toute façon... (non)."
- <30% → "Screw you, joueur ! Tu as résisté à MON génie."

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
# → Expose with ngrok: ngrok http 8899
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
