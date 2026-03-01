# backend-relay/

> **Central Orchestrator** — single point of contact for the frontend. Proxies the Game Master (HTTP/SSE), bridges the Go swarm arena (NATS), and unifies everything on one WebSocket.

```
    "The messenger must never sleep."
                    — Some tired backend, probably
```

## TL;DR

```bash
cd backend-relay
uv sync && uv run uvicorn app.main:app --port 8000

# Health check
curl http://localhost:8000/health

# Start a game (proxied to GM)
curl "http://localhost:8000/api/start?lang=fr"

# Connect WebSocket
websocat ws://localhost:8000/ws/<session_id>

# Trigger proposal generation (events stream on WS)
curl "http://localhost:8000/api/propose?session_id=<session_id>&lang=fr"

# Player chooses a news
curl "http://localhost:8000/api/choose?session_id=<session_id>&kind=fake&lang=fr"
```

---

## Architecture

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                          BACKEND RELAY (Orchestrator)                          │
│                     FastAPI + async/await — port 8000                          │
│                                                                                │
│   ┌────────────────────────────────────────────────────────────────────────┐   │
│   │                     GAME ENDPOINTS (/api/*)                            │   │
│   │                                                                        │   │
│   │   GET /api/start?lang=fr        → proxy to GM, create session          │   │
│   │   GET /api/state                → proxy to GM                          │   │
│   │   GET /api/propose?session_id=X → 202, consume GM SSE, broadcast WS    │   │
│   │   GET /api/choose?session_id=X  → 202, consume GM SSE, broadcast WS    │   │
│   │   GET /api/images/{id}/{file}   → proxy image from GM                  │   │
│   └────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
│   ┌────────────────────────────────────────────────────────────────────────┐   │
│   │                     ARENA ENDPOINTS (legacy)                           │   │
│   │                                                                        │   │
│   │   POST /init_session            → create session, publish NATS init    │   │
│   │   POST /submit_news             → push fake news into NATS             │   │
│   └────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
│   ┌────────────────────────────────────────────────────────────────────────┐   │
│   │                 UNIFIED WEBSOCKET  /ws/{session_id}                     │   │
│   │                                                                        │   │
│   │    ┌──────────┐  ┌──────────┐  ┌──────────┐                           │   │
│   │    │ Client 1 │  │ Client 2 │  │ Client N │  (browsers, dashboards)   │   │
│   │    └────┬─────┘  └────┬─────┘  └────┬─────┘                           │   │
│   │         └──────────────┴──────────────┘                                │   │
│   │         receives both gm.* and arena.* events                          │   │
│   └────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
│   ┌─────────────────────┐          ┌───────────────────────┐                  │
│   │     GM CLIENT        │          │     NATS RELAY         │                  │
│   │  httpx async client  │          │  subscribe arena.>     │                  │
│   │  SSE stream consumer │          │  fan-out to WebSockets │                  │
│   └──────────┬───────────┘          └───────────┬────────────┘                  │
│              │                                  │                              │
└──────────────┼──────────────────────────────────┼──────────────────────────────┘
               │ HTTP/SSE                         │ NATS pub/sub
               ▼                                  ▼
        ┌──────────────┐                   ┌──────────────┐
        │  GAME MASTER │                   │  GO ENGINE   │
        │ (mistralski) │ ──callback──►     │   (swarm/)   │
        │              │  POST /submit     │              │
        │ SSE streams  │  _news + WS       │ Orchestrator │
        │ + REST API   │                   │ + 4 Agents   │
        └──────────────┘                   └──────────────┘
```

**Callback pattern**: When the relay calls GM `/api/stream/choose`, the GM calls back the relay (`POST /submit_news` + WS) to interact with the Go arena. This works as-is — no GM modification needed.

---

## Data Flow

```
1. GAME START
   Frontend ──GET /api/start──► Relay ──HTTP──► GM
                                  └── creates session

2. PROPOSAL GENERATION (SSE → WS)
   Frontend ──GET /api/propose──► Relay ──SSE stream──► GM
                                    └── broadcast gm.* events ──WS──► All Clients

3. PLAYER CHOICE (SSE → WS → NATS)
   Frontend ──GET /api/choose──► Relay ──SSE stream──► GM
                                   │                     └── callback POST /submit_news
                                   └── broadcast gm.* events ──WS──► All Clients

4. ARENA DEBATE (NATS → WS)
   Go Engine ──NATS arena.<sid>.*──► Relay ──WS──► All Clients (arena.* events)
```

---

## Unified WebSocket Protocol

All events flow through a single WebSocket at `ws://relay/ws/{session_id}`:

```json
// GM events (from SSE stream)
{"event": "gm.phase",            "data": {"type": "phase", "data": {...}}}
{"event": "gm.llm_call",         "data": {"type": "llm_call", "data": {...}}}
{"event": "gm.tool_call",        "data": {"type": "tool_call", "data": {...}}}
{"event": "gm.tool_result",      "data": {"type": "tool_result", "data": {...}}}
{"event": "gm.proposal",         "data": {"type": "proposal", "data": {...}}}
{"event": "gm.images",           "data": {"type": "images", "data": {...}}}
{"event": "gm.choice_resolved",  "data": {"type": "choice_resolved", "data": {...}}}
{"event": "gm.reactions",        "data": {"type": "reactions", "data": {...}}}
{"event": "gm.strategy",         "data": {"type": "strategy", "data": {...}}}
{"event": "gm.turn_update",      "data": {"type": "turn_update", "data": {...}}}
{"event": "gm.end",              "data": {"type": "end", "data": {...}}}
{"event": "gm.error",            "data": {"error": "..."}}

// Arena events (from NATS)
{"event": "arena.event.death",       "data": {...}}
{"event": "arena.event.clone",       "data": {...}}
{"event": "arena.agent.status",      "data": {...}}
{"event": "arena.round.start",       "data": {...}}
{"event": "arena.phase.start",       "data": {...}}
```

---

## API Reference

### Game Endpoints (frontend-facing)

| Method | Path | Params | Response | Description |
|--------|------|--------|----------|-------------|
| `GET` | `/api/start` | `?lang=fr` | 200 JSON | Proxy to GM, create relay session |
| `GET` | `/api/state` | — | 200 JSON | Proxy to GM game state |
| `GET` | `/api/propose` | `?session_id=X&lang=fr` | 202 | Launch SSE task, broadcast via WS |
| `GET` | `/api/choose` | `?session_id=X&kind=fake&lang=fr` | 202 | Launch SSE task, broadcast via WS |
| `GET` | `/api/images/{id}/{file}` | — | image bytes | Proxy image from GM (CORS-safe) |

### Arena Endpoints (GM callback / legacy)

| Method | Path | Body | Description |
|--------|------|------|-------------|
| `POST` | `/init_session` | `{"session_id": "..."}` | Create session, notify Go engine via NATS |
| `POST` | `/submit_news` | `{"session_id": "...", "content": "..."}` | Push fake news into NATS |

### System

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Status + NATS connectivity + GM client readiness |

### WebSocket

| Path | Description |
|------|-------------|
| `/ws/{session_id}` | Unified event stream (gm.* + arena.*) |

### Validation

- `session_id`: `^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$` (1-64 chars, alphanumeric + underscore/hyphen)

---

## NATS Topic Map

The relay subscribes to `arena.>` and fans out to WebSocket clients per session.

### Relayed to Clients (Go Engine → Backend → WebSocket)

| Topic | Payload | WS event |
|-------|---------|----------|
| `arena.<sid>.round.start` | `{round, fake_news, context}` | `arena.round.start` |
| `arena.<sid>.phase.start` | `{round, phase}` | `arena.phase.start` |
| `arena.<sid>.agent.<aid>.status` | `{state, detail}` | `arena.agent.<aid>.status` |
| `arena.<sid>.event.death` | `{agent_id, agent_name, round, cause}` | `arena.event.death` |
| `arena.<sid>.event.clone` | `{parent_id, child_id, child_name, round}` | `arena.event.clone` |
| `arena.<sid>.event.end` | `{survivors, history}` | `arena.event.end` |
| `arena.<sid>.input.waiting` | `{round, waiting}` | `arena.input.waiting` |

### Published by Backend (Backend → NATS → Go Engine)

| Topic | Payload | Description |
|-------|---------|-------------|
| `arena.init` | `{"session_id": "..."}` | Launch new game |
| `arena.<sid>.input.fakenews` | `{"content": "..."}` | Fake news for current round |

Self-echo prevention: `input.fakenews` messages are **not** relayed back to WebSocket clients.

---

## Project Structure

```
backend-relay/
├── app/
│   ├── main.py                    # FastAPI app, lifespan (NATS + GMClient), health
│   ├── routers/
│   │   ├── game.py                # Frontend-facing endpoints (/api/*)
│   │   ├── websocket.py           # Unified WebSocket (dual registration)
│   │   └── arena.py               # Legacy arena endpoints (init, submit_news)
│   ├── schemas/
│   │   ├── messages.py            # Pydantic models (request/response)
│   │   └── nats_messages.py       # Arena event schemas (documentation)
│   └── services/
│       ├── gm_client.py           # Async HTTP/SSE client for the Game Master
│       ├── session_manager.py     # Per-session state, WS broadcast, task management
│       └── nats_relay.py          # NATS subscribe + WebSocket fan-out
├── Dockerfile                     # Production container (python:3.12-slim + uv)
├── Makefile                       # CapRover deploy commands
├── pyproject.toml                 # Dependencies
├── uv.lock                        # Deterministic lock file
└── .env.example                   # Environment template
```

---

## Concurrency Model

```python
# Single uvicorn worker, fully async
# SSE consumption runs as asyncio.Task per session
# NATS messages are dispatched via async callback
# Both fan out to the same WebSocket client set

# GM SSE → WS broadcast
async def _stream_propose():
    async def on_event(event):
        event_type = event.get("type", "unknown")
        await session_manager.broadcast(session_id, f"gm.{event_type}", event)
    await gm_client.stream_propose(lang, on_event)

# NATS → WS broadcast
async def _message_handler(self, msg):
    session_id = msg.subject.split(".")[1]
    topic_suffix = ".".join(msg.subject.split(".")[2:])
    for ws in self._sessions.get(session_id, set()):
        await ws.send_json({"event": f"arena.{topic_suffix}", "data": payload})
```

- One active SSE task per session (cancelled on new action)
- NATS callbacks fire on every message — non-blocking
- Dead WebSocket clients are automatically cleaned up

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NATS_URL` | `nats://demo.nats.io:4222` | NATS server connection string |
| `GM_BASE_URL` | `https://gm-mistralski.wh26.edouard.cl` | Game Master base URL |

---

## Quick Start

### Local Development

```bash
# Python 3.12+ required
pip install uv
uv sync

# Start
uv run uvicorn app.main:app --port 8000 --reload
```

### Full Stack Test

```bash
# Terminal 1: start relay
cd backend-relay
uv run uvicorn app.main:app --port 8000

# Terminal 2: connect WebSocket
websocat ws://localhost:8000/ws/<session_id>

# Terminal 3: play
curl "http://localhost:8000/api/start?lang=fr"
# → {"session_id": "xxx-xxx", "turn": 1, ...}

curl "http://localhost:8000/api/propose?session_id=xxx-xxx&lang=fr"
# → 202, events stream on WS

curl "http://localhost:8000/api/choose?session_id=xxx-xxx&kind=fake&lang=fr"
# → 202, full turn cycle on WS
```

### Docker

```bash
docker compose up --build
```

---

## Production Deployment

### CapRover

```bash
make deploy
```

Deploys to `wh26-backend.wh26.edouard.cl` via CapRover CLI.

### Docker Compose (self-hosted)

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

---

## Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Language | **Python 3.12** | Async-native, fast prototyping |
| Framework | **FastAPI** | WebSocket + HTTP in one app, auto-docs |
| HTTP Client | **httpx** | Async streaming for SSE consumption |
| NATS Client | **nats-py** | Async-first, lightweight |
| Server | **Uvicorn** | ASGI, handles WebSockets natively |
| Package Manager | **uv** | Fast, deterministic installs |
| Container | **Docker** | Single `python:3.12-slim` image |
| Deployment | **CapRover** | One-command deploy |

**Total dependencies**: 5 (`fastapi`, `httpx`, `nats-py`, `uvicorn`, `websockets`)

---

## License

MIT

---

*Built for MISTRAL WORLDWIDE HACKS 2K26*
