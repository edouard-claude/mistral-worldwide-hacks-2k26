# backend-relay/

> **WebSocket Relay** — bridges frontend clients, the Game Master, and the Go swarm engine through NATS pub/sub.

```
    "The messenger must never sleep."
                    — Some tired backend, probably
```

## TL;DR

```bash
cd backend-relay
docker compose up --build

# Health check
curl http://localhost:8001/health

# Connect a WebSocket client
websocat ws://localhost:8001/ws/arena/test-001

# Init a session
curl -X POST http://localhost:8001/init_session \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-001"}'

# Feed fake news (Game Master)
curl -X POST http://localhost:8001/submit_news \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-001", "content": "5G towers cause COVID"}'
```

Watch events flow from the Go engine to your browser in real-time.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND RELAY                                      │
│                  FastAPI + async/await — port 8001                           │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │                        HTTP ENDPOINTS                                │   │
│   │                                                                      │   │
│   │   POST /health          → service status + NATS connectivity         │   │
│   │   POST /init_session    → create session, publish arena.init         │   │
│   │   POST /submit_news     → push fake news into NATS                   │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │                     WEBSOCKET ENDPOINTS                              │   │
│   │                                                                      │   │
│   │   /ws/arena/{session_id}  → per-session event stream                 │   │
│   │                                                                      │   │
│   │    ┌──────────┐  ┌──────────┐  ┌──────────┐                         │   │
│   │    │ Client 1 │  │ Client 2 │  │ Client N │  (browsers, dashboards) │   │
│   │    └────┬─────┘  └────┬─────┘  └────┬─────┘                         │   │
│   │         │             │             │                                │   │
│   └─────────┼─────────────┼─────────────┼────────────────────────────────┘   │
│             │             │             │                                    │
│             ▼             ▼             ▼                                    │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │                       NATS RELAY SERVICE                             │   │
│   │              subscribe arena.> — fan-out to WebSockets               │   │
│   │              publish arena.<sid>.input.fakenews                       │   │
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
   │  GAME MASTER │                                  │  GO ENGINE   │
   │              │                                  │   (swarm/)   │
   │ POST /submit │                                  │              │
   │ _news        │──► NATS ──────────────────────►  │ Orchestrator │
   │              │                                  │ + Agents     │
   │ (you publish │                                  │              │
   │  fake news)  │                                  │ publishes:   │
   └──────────────┘                                  │ events, state│
                                                     └──────────────┘
```

---

## Data Flow

```
1. SESSION CREATION
   Game Master ──POST /init_session──► Backend Relay ──NATS arena.init──► Go Engine

2. EVENT RELAY (NATS → WebSocket)
   Go Engine ──NATS arena.<sid>.event.*──► Backend Relay ──WebSocket──► All Clients

3. FAKE NEWS INPUT
   Game Master ──POST /submit_news──► Backend Relay ──NATS arena.<sid>.input.fakenews──► Go Engine
```

### WebSocket Envelope Format

Every NATS event is wrapped before reaching clients:

```json
{
  "subject": "event.death",
  "data": {
    "agent_id": "marcus-001",
    "agent_name": "Marcus",
    "round": 3,
    "cause": "lowest_score"
  }
}
```

---

## API Reference

### HTTP Endpoints

| Method | Path | Body | Description |
|--------|------|------|-------------|
| `POST` | `/health` | — | Service status + NATS connectivity |
| `POST` | `/init_session` | `{"session_id": "..."}` | Create session, notify Go engine via NATS |
| `POST` | `/submit_news` | `{"session_id": "...", "content": "..."}` | Push fake news for current round |
| `POST` | `/arena/{sid}/fakenews` | `{"content": "..."}` | Alternative fake news endpoint |

### WebSocket Endpoints

| Path | Description |
|------|-------------|
| `/ws/arena/{session_id}` | Per-session event stream (receive-only) |

### Validation

- `session_id`: `^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$` (1-64 chars, alphanumeric + underscore/hyphen)

---

## NATS Topic Map

The relay subscribes to `arena.>` and fans out to WebSocket clients per session.

### Relayed to Clients (Go Engine → Backend → WebSocket)

| Topic | Payload | Description |
|-------|---------|-------------|
| `arena.<sid>.round.start` | `{round, fake_news, context}` | Round started |
| `arena.<sid>.phase.start` | `{round, phase}` | Phase started |
| `arena.<sid>.agent.<aid>.input` | `{phase, data}` | Agent received input |
| `arena.<sid>.agent.<aid>.output` | `{data}` | Agent response |
| `arena.<sid>.agent.<aid>.status` | `{state, detail}` | Agent status change |
| `arena.<sid>.agent.<aid>.kill` | `{reason, round}` | Agent killed |
| `arena.<sid>.event.death` | `{agent_id, agent_name, round, cause}` | Agent eliminated |
| `arena.<sid>.event.clone` | `{parent_id, child_id, child_name, round}` | Agent cloned |
| `arena.<sid>.event.end` | `{survivors, history}` | Game over |
| `arena.<sid>.input.waiting` | `{round, waiting}` | Game waiting for input |

### Published by Backend (Backend → NATS → Go Engine)

| Topic | Payload | Description |
|-------|---------|-------------|
| `arena.init` | `{"session_id": "..."}` | Launch new game |
| `arena.<sid>.input.fakenews` | `string` | Fake news for current round |

Self-echo prevention: `input.fakenews` messages are **not** relayed back to WebSocket clients.

---

## Project Structure

```
backend-relay/
├── app/
│   ├── main.py                    # FastAPI app, lifespan, health endpoint
│   ├── routers/
│   │   ├── websocket.py           # WebSocket endpoints
│   │   └── arena.py               # HTTP arena endpoints (init, submit_news)
│   ├── schemas/
│   │   ├── messages.py            # Pydantic models (request/response)
│   │   └── nats_messages.py       # Arena event schemas (documentation)
│   └── services/
│       ├── session_manager.py     # In-memory session registry
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
# Each WebSocket client runs its own coroutine
# NATS messages are dispatched via async callback

async def _message_handler(self, msg):
    subject = msg.subject                   # "arena.abc123.event.death"
    parts = subject.split(".")             # ["arena", "abc123", "event", "death"]
    session_id = parts[1]                  # "abc123"
    topic_suffix = ".".join(parts[2:])     # "event.death"

    # Fan-out to all WebSocket clients in this session
    for ws in self._sessions.get(session_id, set()):
        await ws.send_json({"subject": topic_suffix, "data": payload})
```

**Why async?**
- WebSocket connections are long-lived — blocking = dead
- NATS callbacks fire on every message — must be non-blocking
- Single process handles hundreds of concurrent connections via `asyncio`

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NATS_URL` | `nats://demo.nats.io:4222` | NATS server connection string |

---

## Quick Start

### Docker (recommended)

```bash
# Start NATS + backend
docker compose up --build

# Verify
curl -X POST http://localhost:8001/health
# → {"status": "ok", "service": "bmadlife-backend", "nats_connected": true}
```

### Local Development

```bash
# Python 3.12+ required
pip install uv
uv sync

# Start (assumes NATS is running somewhere)
export NATS_URL="nats://localhost:4222"
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Full Stack Test

```bash
# Terminal 1: start backend + NATS
docker compose up --build

# Terminal 2: connect WebSocket client
websocat ws://localhost:8001/ws/arena/test-001

# Terminal 3: init session + send fake news
curl -X POST http://localhost:8001/init_session \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-001"}'

# Start the Go swarm engine (in swarm/ directory)
export MISTRAL_API_KEY="sk-..."
go run . --nats-url "nats://localhost:4222"

# Feed fake news
curl -X POST http://localhost:8001/submit_news \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-001", "content": "Birds are government drones"}'

# Watch events stream into Terminal 2
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

Expects an external `bmadlife_bmadlife` Docker network (shared with the Go engine).

---

## Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Language | **Python 3.12** | Async-native, fast prototyping |
| Framework | **FastAPI** | WebSocket + HTTP in one app, auto-docs |
| NATS Client | **nats-py** | Async-first, lightweight |
| Server | **Uvicorn** | ASGI, handles WebSockets natively |
| Package Manager | **uv** | Fast, deterministic installs |
| Container | **Docker** | Single `python:3.12-slim` image |
| Deployment | **CapRover** | One-command deploy |

**Total dependencies**: 4 (`fastapi`, `nats-py`, `uvicorn`, `websockets`)

---

## License

MIT

---

*Built for MISTRAL WORLDWIDE HACKS 2K26*
