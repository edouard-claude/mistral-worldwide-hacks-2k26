# monitoring-sessions/

> **Debate Autopsy Dashboard** — Visualize, dissect, and analyze multi-agent debate sessions from the GORAFI SIMULATOR arena.

```
    "The data never lies. The agents, however..."
                    — Bureau of Alternative Truth
```

## TL;DR

```bash
node server.mjs
# → http://localhost:3000

# Or with Docker (mounts live swarm sessions)
docker-compose -f docker-compose.prod.yml up
```

Browse sessions, trace agent genealogies, watch political colors shift, and read the debates that killed them.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              SERVER (Node.js)                                │
│                    server.mjs — static files + auto-refresh                  │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │                        PREPROCESSOR                                  │   │
│   │              preprocess.mjs — markdown → JSON pipeline               │   │
│   │                                                                      │   │
│   │    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │   │
│   │    │ SOUL.md  │  │ T*.md    │  │ DEATH.md │  │ chat/    │          │   │
│   │    │ parser   │  │ memory   │  │ parser   │  │ parser   │          │   │
│   │    └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘          │   │
│   │         │             │             │             │                  │   │
│   └─────────┼─────────────┼─────────────┼─────────────┼──────────────────┘   │
│             │             │             │             │                      │
│             ▼             ▼             ▼             ▼                      │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │                      data/ (generated JSON)                          │   │
│   │           sessions.json — index of all sessions                      │   │
│   │           <session_id>.json — full processed session                 │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────┬───────────────────────────────────────────┘
                                   │
                                   │ HTTP (static)
                                   │
          ┌────────────────────────┴────────────────────────┐
          │                                                 │
          ▼                                                 ▼
   ┌──────────────┐                                  ┌──────────────┐
   │   INPUT       │                                  │   FRONTEND   │
   │               │                                  │   (SPA)      │
   │ sessions/     │                                  │              │
   │ ├ global.json │                                  │ #/           │
   │ ├ agents/     │                                  │ #/session/id │
   │ ├ graveyard/  │                                  │ #/round/N    │
   │ └ chat/       │                                  │ #/agent/uuid │
   │               │                                  │              │
   │ (swarm arena  │                                  │ SVG trees,   │
   │  markdown     │                                  │ timelines,   │
   │  output)      │                                  │ transcripts  │
   └──────────────┘                                  └──────────────┘
```

---

## Data Flow

```
Swarm Arena (Go)
│
├─► Writes markdown files to sessions/<uuid>/
│       ├── global.json          # Agent roster, game state
│       ├── agents/<name>/
│       │   ├── SOUL.md          # Personality, biases
│       │   └── memory/T*.md     # Per-round memory (4 phases)
│       ├── graveyard/<name>/
│       │   ├── DEATH.md         # Cause of death, final score
│       │   └── memory/T*.md
│       └── chat/T*_phase*.md    # Public debate transcripts
│
├─► preprocess.mjs (runs every 30s)
│       └─► Parses markdown with regex
│       └─► Builds genealogy trees
│       └─► Emits data/sessions.json + data/<id>.json
│
└─► Frontend SPA (vanilla JS)
        └─► Fetches JSON, renders SVG visualizations
        └─► Hash router: session list → overview → round → agent
```

---

## Views

### Session List (`#/`)

Grid of all archived sessions — fake news topic, round count, agent survival stats.

### Session Overview (`#/session/<id>`)

```
┌─────────────────────────────────────────────────────────┐
│  TIMELINE           R1    R2    R3    R4    R5   ...    │
│                     ●─────●─────●─────●─────●           │
├─────────────────────────────────────────────────────────┤
│  GENEALOGY TREE                                         │
│                     Marcus                              │
│                    /      \                              │
│              Elena          Dante                       │
│                               \                         │
│                               Aria                      │
├─────────────────────────────────────────────────────────┤
│  PRESENCE CHART     ████████████░░░░░░░░  Marcus (R1†)  │
│  (political color)  ████████████████████  Elena         │
│                     ░░░░████████████████  Dante (R2+)   │
│                     ░░░░░░░░████████████  Aria  (R4+)   │
└─────────────────────────────────────────────────────────┘
```

### Round Detail (`#/session/<id>/round/<N>`)

Per-agent cards: confidence levels, public arguments, scores, vote rankings, plus tabbed debate transcripts (phase 2 & 3).

### Agent Detail (`#/session/<id>/agent/<uuid>`)

Full profile: SOUL personality, political color history, per-round accordion, lineage, and death report (if eliminated).

---

## Political Color Spectrum

Each agent has a political leaning (0.0 → 1.0), visualized as a color gradient:

```
0.0          0.2          0.5          0.8          1.0
 │            │            │            │            │
 ▼            ▼            ▼            ▼            ▼
BLUE         BLUE-GRAY    GRAY         RED-GRAY     RED
far-right    right        center       left         far-left
```

Colors shift each round based on debate influence. The presence chart uses this gradient to show political evolution over time.

---

## Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Server | **Node.js 22** | Built-in HTTP, zero npm deps |
| Frontend | **Vanilla JS (ES modules)** | No build step, no framework |
| Styling | **CSS 3** | Dark theme, CSS variables |
| Visualization | **SVG (pure DOM)** | Genealogy trees, presence charts, no charting lib |
| Markdown | **marked.js (CDN)** | Render debate transcripts |
| Data | **Markdown → JSON** | Preprocess swarm output into queryable format |
| Deployment | **Docker + CapRover** | Single container, volume-mounted sessions |

**Total dependencies**: 0 (npm) — marked.js loaded via CDN.

---

## Quick Start

```bash
# Local with example data
node server.mjs
# → http://localhost:3000

# Point to live swarm sessions
SESSIONS_DIR=../swarm/sessions node server.mjs

# Docker (production — mounts swarm sessions read-only)
docker-compose -f docker-compose.prod.yml up
# → http://localhost:3000

# Manual data refresh
curl -X POST http://localhost:3000/refresh

# Deploy to CapRover
make deploy
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SESSIONS_DIR` | `./examples` | Path to session data folders |
| `PORT` | `3000` | HTTP server port |
| `REFRESH_INTERVAL` | `30` | Auto-preprocess frequency (seconds) |

---

## Session Data Format

Everything comes from the swarm arena's markdown output:

```
sessions/<uuid>/
├── global.json                 # Agent roster, session metadata
├── agents/
│   └── <name>/
│       ├── SOUL.md             # Personality, style, biases
│       └── memory/
│           └── T<N>.md         # Round N: 4 phases, votes, scores
├── graveyard/
│   └── <name>/
│       ├── SOUL.md
│       ├── DEATH.md            # Final score, cause, ranked by
│       └── memory/
└── chat/
    ├── T<N>_phase2.md          # Public debate transcript
    └── T<N>_phase3.md          # Revised takes transcript
```

### Preprocessed Output

```
data/
├── sessions.json               # Index: [{session_id, total_rounds, agent_count, ...}]
└── <session_id>.json           # Full session: agents, rounds, genealogy, timeline
```

---

## Routes

| Route | View | Description |
|-------|------|-------------|
| `#/` | Session List | Grid of all sessions with quick stats |
| `#/session/<id>` | Session Overview | Timeline + genealogy tree + presence chart |
| `#/session/<id>/round/<N>` | Round Detail | Agent cards, vote bars, debate transcripts |
| `#/session/<id>/agent/<uuid>` | Agent Detail | Full profile, round history, death report |

---

## License

MIT

---

*Built for MISTRAL WORLDWIDE HACKS 2K26*
