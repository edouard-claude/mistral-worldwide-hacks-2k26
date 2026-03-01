# CLAUDE.md — GORAFI SIMULATOR Monorepo

## Project Identity

- **Name**: GORAFI SIMULATOR v1.0 — "Département de la Vérité Alternative"
- **Team**: BMADlife
- **Event**: Mistral AI Worldwide Hackathon 2026
- **Genre**: Satirical disinformation game — turn-based strategy with autonomous AI agents

---

## Architecture Overview

```
Player ←→ Frontend (React/Vite) ←→ Mistralski GM (Python/FastAPI) ←→ Backend Relay (Python/FastAPI) ←→ Swarm Arena (Go)
                                         ↕                                        ↕
                                   Mistral Large API                          NATS pub/sub
                                   (function calling)                              ↕
                                   Mistral Flux (images)                     Mistral Small 3.2
                                   Fine-tuned model (titles)                 (4 debate agents)
```

### 4 Services

| Folder | Language | Port | Role |
|--------|----------|------|------|
| `frontend/` | TypeScript (React + Vite) | 5173 | Player-facing CRT-styled Soviet dashboard |
| `mistralski/` | Python (FastAPI) | 8899 | Autonomous Game Master agent — news generation, player manipulation, strategy |
| `backend-relay/` | Python (FastAPI) | 8000 | HTTP/WebSocket relay between GM and Swarm via NATS |
| `swarm/` | Go | — | Darwinian 4-agent debate arena — agents argue, vote, die, clone |

---

## Game Flow (per turn)

1. **GM proposes** 3 news (real/fake/satirical) via Mistral Large + fine-tuned titles + Flux images
2. **Player picks** one news to publish
3. **GM sends** chosen news to Swarm arena via backend-relay
4. **4 agents debate** in 4 phases: cogitation → public take → revision → voting (Mistral Small)
5. **Natural selection**: lowest scorer dies, highest scorer clones
6. **GM strategizes**: analyzes results, updates agent dossiers, plans next manipulation tactic
7. **Repeat** for 10 turns → end-game reveals GM's secret manipulation history

---

## Mistral API Usage

| Product | Where | Purpose |
|---------|-------|---------|
| **Mistral Large** | `mistralski/` | GM agent with function calling (5 tools), JSON structured output, secret manipulation strategy |
| **Mistral Small 3.2** | `swarm/` | 4 concurrent debate agents via Go goroutines, 16 parallel API calls/round |
| **Mistral Agent API (Flux)** | `mistralski/` | Soviet-style propaganda poster generation, 3 images/turn |
| **Custom fine-tuned model** | `mistralski/` | Gorafi-quality title generation in <1s, endpoint: `POST /generate` |

---

## Key Files

### Mistralski (Game Master)
- `mistralski/scripts/play_web.py` — FastAPI server, SSE endpoints, image generation, wh26 relay integration
- `mistralski/src/agents/game_master_agent.py` — Autonomous GM: function calling loop, memory system, fast mode optimization
- `mistralski/src/models/game.py` — GameState, NewsProposal, GMStrategy Pydantic models
- `mistralski/src/models/world.py` — NewsHeadline, GlobalIndices
- `mistralski/src/core/config.py` — Pydantic Settings (.env)
- `mistralski/config/game.yaml` — Turn mechanics, action definitions
- `mistralski/config/agents.yaml` — Agent archetypes for the arena

### Frontend
- `frontend/src/pages/Index.tsx` — Main 3-column dashboard layout
- `frontend/src/hooks/useBackendEngine.ts` — SSE streaming + game state management (the brain)
- `frontend/src/services/api.ts` — Backend API client (REST + SSE via fetch with custom headers)
- `frontend/src/components/dashboard/` — All game UI components (PropagandaPanel, CenterPanel, SwarmPanel, GmTerminal, GameOverScreen, WelcomeScreen, TopBar, NewsTicker)
- `frontend/src/i18n/translations.ts` — FR/EN translation dictionary (100+ keys)
- `frontend/src/index.css` — Full Soviet theme: CSS variables, 20+ keyframe animations

### Swarm Arena
- `swarm/main.go` — Game loop orchestrator, NATS dispatcher, multi-session support
- `swarm/phase.go` — 4-phase concurrent execution (goroutines + sync.WaitGroup)
- `swarm/agent.go` — Agent creation, cloning, death, replacement
- `swarm/session.go` — Session persistence (global.json), context injection
- `swarm/scoring.go` — Vote aggregation, winner/loser selection
- `swarm/mistral.go` — Raw HTTP client for Mistral Small API (no SDK)
- `swarm/sessions/` — Persistent markdown files: agent SOULs, memories, chat logs, graveyard

### Backend Relay
- `backend-relay/app/main.py` — FastAPI app with NATS connection
- `backend-relay/app/services/nats_relay.py` — NATS pub/sub ↔ WebSocket bridge
- `backend-relay/app/routers/arena.py` — `/init_session`, `/submit_news` endpoints

---

## SSE Event Types (Frontend ← Mistralski)

### Level 1 — Core Gameplay (always visible)
`proposal`, `images`, `choice_resolved`, `reactions`, `indices_update`, `strategy.analysis`, `turn_update`, `end`

### Level 2 — GM Journal (collapsible terminal)
`llm_text`, `vision_update`, `tool_call`, `tool_result`, `strategy.threat_agents`, `strategy.weak_spots`, `strategy.next_turn_plan`, `strategy.long_term_goal`, `phase`

### Level 3 — Secret Reveal (end-game only)
`game_over_reveal` — Full manipulation history: desired_pick, actual_pick, tactic, success rate

---

## GM Agent Tools (Function Calling)

| Tool | Description |
|------|-------------|
| `read_game_memory` | Global cumulative stats: turns played, choice history, decerebration |
| `read_turn_log` | Per-turn log: chosen news, index deltas, agent reactions |
| `read_agent_vision` | GM's private dossier on a specific agent (threat, pattern, vulnerability) |
| `update_agent_vision` | Write/update agent dossier — the LLM decides content |
| `list_memory_files` | List all available memory files |

---

## Environment Variables

### Mistralski (.env)
```
MISTRAL_API_KEY=sk-...
```

### Swarm
```
MISTRAL_API_KEY=sk-...
```

### Backend Relay (.env)
```
NATS_URL=nats://demo.nats.io:4222
```

### Frontend
Backend URL hardcoded in `frontend/src/services/api.ts` → change `BASE_URL` to your backend.

---

## Running Locally

```bash
# 1. Swarm Arena (Go)
cd swarm
export MISTRAL_API_KEY="sk-..."
go run .

# 2. Backend Relay (Python)
cd backend-relay
pip install -r requirements.txt
uvicorn app.main:app --port 8000

# 3. Mistralski GM (Python)
cd mistralski
pip install -e ".[dev]"
echo "MISTRAL_API_KEY=sk-..." > .env
python3 scripts/play_web.py
# → http://localhost:8899

# 4. Frontend (React)
cd frontend
npm install && npm run dev
# → http://localhost:5173
# Update BASE_URL in src/services/api.ts to http://localhost:8899
```

---

## Code Conventions

- **Python**: Type hints mandatory, Pydantic v2 models, async/await, structlog logging
- **Go**: Standard library preferred (net/http, no SDK), goroutines for concurrency, sync.WaitGroup barriers
- **TypeScript**: React 18+, Tailwind CSS, shadcn/ui components, SSE via fetch (not EventSource)
- **Commits**: Conventional format — `feat:`, `fix:`, `docs:`, `refactor:`
- **Language**: Code and commits in English, game content bilingual (FR/EN)

---

## Infrastructure

| Server | Role |
|--------|------|
| App (51.159.131.72) | FastAPI, Nginx, PostgreSQL, Redis, Qdrant, DuckDB |
| GPU (51.159.173.147) | 2x L40S 48GB — vLLM: Mistral Small 3.2 :8000, Devstral Small 2 :8001 |
| Mistral API | Mistral Large (GM), Flux (images) |
| Fine-tuned | `http://mistralski-fine-tuned.wh26.edouard.cl:80/generate` |
