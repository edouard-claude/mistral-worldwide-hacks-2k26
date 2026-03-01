# CLAUDE.md — GORAFI SIMULATOR

## Project Identity

- **Name**: GORAFI SIMULATOR v1.0
- **Subtitle**: "Département de la Vérité Alternative"
- **Genre**: Satirical dictator dashboard — turn-based strategy
- **Tone**: Dark Gorafi-style satire, Cold War retro-Soviet control room aesthetic
- **Status**: Scaffolding done, pivoted from survival sim to satirical strategy

---

## Game Concept

Player controls a "disinformation dashboard" and uses 20 actions across 4 categories to manipulate the world. Each turn, they spend Crédits Éditoriaux to target countries or go worldwide. AI agents react satirically. A Game Master LLM provides commentary in Gorafi style.

**Win/Loss**: INDICE MONDIAL DE DÉCÉRÉBRATION reaches 100 = you "win". ESPÉRANCE DÉMOCRATIQUE hits 0 = game over (or is it?).

---

## UI Spec

### Aesthetic
- **Background**: #0a0a0a (near-black)
- **Neon green**: #00ff41 (terminal text, stable indicators)
- **Red alerts**: #ff003c (danger, désinformation)
- **Amber warnings**: #ffb300 (manipulation, warnings)
- **Purple**: #8b5cf6 (censure category)
- **Orange**: #ff6b00 (déstabilisation)
- **Font**: Monospace (JetBrains Mono or similar)
- **Feel**: CRT monitor, dangerous control panel, "CLASSIFIED" stamps

### Layout (3 columns)

**LEFT — "ARSENAL"** (action buttons):
- 20 buttons in 5 categories of 4-5 each
- Dark bordered cards with icon + label
- Hover: glow effect, click: pulse animation
- Cooldown state: greyed out + countdown timer
- Categories: Désinformation (🔴), Manipulation (🐐), Censure (🔇), Déstabilisation (💣)

**CENTER — World Map**:
- SVG world map, dark countries with light borders
- Pulsing LED diode per country center (🟢 stable / 🟠 agitated / 🔴 chaos)
- Hover tooltip: country name, active agents, dominant metric, last event, satirical one-liner
- Below: scrolling CNN-style news ticker (dark red bg, white text)

**RIGHT — "ÉTAT DU MONDE"**:
- Top: 4 circular gauges (Crédulité, Rage, Complotisme, Espérance Démocratique)
- Middle: Scrollable agent cards (avatar, name+flag, 3 stat bars, level badge, status tag)
- Bottom: Game Master CRT terminal with typewriter text

### Top Bar
- Left: "GORAFI SIMULATOR v1.0" + subtitle
- Center: Turn counter + INDICE MONDIAL DE DÉCÉRÉBRATION progress bar
- Right: Credits + Budget Titres + red "FIN DE TOUR →" button

### Interactions
- Action button → targeting modal (country or MONDIAL) → confirm → map animation
- Turn end → "BILAN DU TOUR" full-screen overlay
- Agent cards update live after actions

---

## Action Categories (20 actions)

| Category | Icon | Color | Actions |
|----------|------|-------|---------|
| Désinformation | 🔴 | #ff003c | Fake News, Photo Choquante, Étude, Vieux Scandale, Sondage |
| Manipulation | 🐐 | #ffb300 | Bouc Émissaire, Distraction, Polémique, Hashtag, Martyr |
| Censure | 🔇 | #8b5cf6 | Couper Internet, Démenti, Disparition, Loi d'Exception, Museler |
| Déstabilisation | 💣 | #ff6b00 | Guerre Commerciale, Urgence, Cyberattaque, Krach, Référendum |

---

## Tech Stack

### Backend
- **Python 3.11+**, Pydantic v2, structlog
- **vLLM** (GPU Scaleway): Mistral Small 3.2 for agent reactions, batch inference
- **Mistral Large API**: Game Master commentary, turn bilans
- **DuckDB + spatial**: Game state persistence, country stats history
- **Qdrant**: Agent memory across turns
- **Redis**: Turn state cache, pub/sub for frontend
- **OSRM**: Optional (kept from previous project, not critical for v1)

### Frontend
- **Next.js 14+** (App Router)
- **Tailwind CSS** + custom dark theme
- **shadcn/ui** components
- **SVG world map** with dynamic LED overlays
- **Framer Motion** for animations (pulse, glow, typewriter)

---

## Project Structure

```
game-of-claw/
├── CLAUDE.md
├── pyproject.toml
├── docker-compose.yml
├── .env.example
├── config/
│   ├── game.yaml          # Turn mechanics, 20 action definitions with costs/effects
│   ├── agents.yaml         # 10 satirical agent archetypes
│   └── countries.yaml      # 15 countries with LED coords, initial stats
├── src/
│   ├── core/
│   │   ├── config.py       # Pydantic Settings
│   │   ├── logging.py      # structlog setup
│   │   └── exceptions.py   # GameError, LLMError, etc.
│   ├── clients/
│   │   ├── vllm.py         # VLLMBatchClient (batch inference)
│   │   ├── osrm.py         # OSRMClient (routing, optional)
│   │   ├── qdrant.py       # QdrantMemoryClient (agent memories)
│   │   ├── duckdb_store.py # GameStore (state persistence)
│   │   ├── weather.py      # WeatherClient (mood effects)
│   │   └── news.py         # NewsClient (RSS for Game Master)
│   ├── models/
│   │   ├── agent.py        # AgentState, AgentStats, AgentLevel, AgentReaction
│   │   ├── world.py        # CountryState, ActionDefinition, GlobalIndices, NewsHeadline
│   │   └── game.py         # GameState, TurnResult, TurnResources, GameMasterMessage
│   └── db/
│       └── schema.py       # DuckDB table init
├── scripts/
│   ├── setup_osrm.sh
│   ├── extract_pois.py
│   └── test_connections.py
├── frontend/               # Next.js (to be created)
└── tests/
```

---

## Code Conventions

1. **Type hints mandatory** on all functions
2. **Google-style docstrings** for public functions
3. **Pydantic BaseModel** for all data structures
4. **Async/await** by default for I/O
5. **structlog** for logging (never print)
6. **StrEnum** for enums (not str, Enum)
7. **snake_case** functions/variables, **PascalCase** classes

---

## Development Commands

```bash
pytest tests/ -v --cov=src
ruff check src/ --fix && ruff format src/
mypy src/ --strict
```
