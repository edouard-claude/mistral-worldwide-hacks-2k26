# Gorafi USSR Front — Frontend

> Cold War retro-Soviet dashboard for the GORAFI SIMULATOR. Built with React, Vite, TypeScript, Tailwind CSS, and shadcn/ui.

## Overview

This is the **player-facing interface** for the Gorafi Simulator — a satirical disinformation game where you control a propaganda dashboard and try to maximize global "decerebration" by choosing between real, fake, and satirical news each turn.

The frontend connects to the **Mistralski** backend (Game Master agent) via SSE streaming and renders the GM's reasoning process, news proposals, agent debates, and propaganda posters in real-time.

## Architecture

```
┌──────────────────┐     SSE + REST      ┌──────────────┐    HTTP+WS    ┌──────────────┐
│  gorafi-ussr-    │ ◄──────────────────► │  Mistralski  │ ◄───────────► │  wh26 relay  │
│  front (React)   │                      │  play_web.py │               │  (Go backend)│
└──────────────────┘                      └──────┬───────┘               └──────┬───────┘
                                                  │                              │
                                         Mistral Large API               Swarm arena agents
                                         (function calling)              (Mistral Small 3.2)
```

## Key Features

- **CRT Terminal Aesthetic** — Dark theme (#0a0a0a), neon green (#00ff41), red alerts (#ff003c), monospace fonts
- **3-Column Dashboard** — Propaganda panel (left) / Center stage (right) / GM Terminal (bottom)
- **SSE Streaming** — Real-time display of GM's agentic reasoning: tool calls, vision updates, inner monologue
- **Propaganda Posters** — Mistral-generated Soviet-style illustrations for each news, loaded asynchronously
- **Multilingual** — Full i18n support (French / English) with language switcher
- **Agent Debate Panel** — Live agent reactions from the Swarm arena via WebSocket relay
- **GM Terminal** — Collapsible CRT-style console showing the GM's inner thoughts and strategy
- **Game Over Reveal** — End-game screen showing the GM's secret manipulation history and success rate

## Components

| Component | Description |
|-----------|-------------|
| `TopBar` | Turn counter, decerebration progress bar, language switch |
| `PropagandaPanel` | 3 news cards (real/fake/satirical) with propaganda posters and article previews |
| `CenterPanel` | Main game area: welcome screen, news selection, debate feed, results |
| `SwarmPanel` | Agent cards with stats bars, status badges, and live reactions |
| `GmTerminal` | CRT terminal with typewriter effect — shows GM reasoning trace |
| `GameMasterCard` | Cartman avatar card with GM commentary |
| `GameOverScreen` | Final reveal: manipulation stats, hall of fallen agents, verdict |
| `NewsTicker` | CNN-style scrolling red ticker at the top |

## SSE Events Consumed

The frontend consumes these events from `/api/stream/propose` and `/api/stream/choose`:

| Event | Rendered As |
|-------|-------------|
| `proposal` | 3 news cards in PropagandaPanel |
| `images` | Propaganda poster images loaded into cards |
| `choice_resolved` | GM reaction bubble in debate |
| `agent_nats` | Agent take/opinion in debate feed |
| `agent_death` / `agent_clone` | System messages in debate |
| `indices_update` | Gauge animations (chaos, credulite, decerebration) |
| `strategy` | GM analysis in terminal |
| `vision_update` | Agent dossier updates in terminal |
| `tool_call` / `tool_result` | Tool traces in terminal |
| `llm_text` | GM inner monologue in terminal |
| `game_over_reveal` | Full manipulation history reveal |

## Tech Stack

- **Vite** — Build tool and dev server
- **React 18** + TypeScript
- **Tailwind CSS** + shadcn/ui (Radix primitives)
- **Lucide React** — Icons
- **TanStack React Query** — Server state management
- **React Router** — Client-side routing
- **Recharts** — Data visualization
- **Vitest** — Testing framework

## Running Locally

```bash
# Install dependencies
npm install
# or
bun install

# Start dev server
npm run dev
# → http://localhost:5173

# Build for production
npm run build

# Run tests
npm test
```

## Configuration

The backend URL is configured in `src/services/api.ts`:

```typescript
const BASE_URL = "https://your-backend-url.ngrok-free.dev";
```

Point this to your Mistralski backend (default: `http://localhost:8899`).

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── dashboard/          # Game UI components
│   │   │   ├── TopBar.tsx
│   │   │   ├── PropagandaPanel.tsx
│   │   │   ├── CenterPanel.tsx
│   │   │   ├── SwarmPanel.tsx
│   │   │   ├── GmTerminal.tsx
│   │   │   ├── GameMasterCard.tsx
│   │   │   ├── GameOverScreen.tsx
│   │   │   └── NewsTicker.tsx
│   │   └── ui/                 # shadcn/ui primitives
│   ├── hooks/
│   │   ├── useBackendEngine.ts # SSE streaming + game state management
│   │   └── useGameEngine.ts    # Full game engine (backend mode)
│   ├── services/
│   │   └── api.ts              # Backend API client (REST + SSE)
│   ├── data/
│   │   ├── gameData.ts         # Types, initial data, political spectrum
│   │   └── chaosEvents.ts      # Random chaos event triggers
│   ├── i18n/
│   │   ├── translations.ts     # FR/EN translation strings
│   │   └── LanguageContext.tsx  # Language context provider
│   └── pages/
│       └── Index.tsx            # Main dashboard page
├── index.html
├── package.json
├── vite.config.ts
├── tailwind.config.ts
└── tsconfig.json
```
