# Plan de Migration WebSocket — Frontend Gorafi Simulator

## Contexte

Migration du frontend de l'API REST/SSE (`gm-mistralski`) vers un nouveau backend WebSocket (`wh26-backend`).

**Ancien backend** : `https://gm-mistralski.wh26.edouard.cl`
**Nouveau backend** : `https://wh26-backend.wh26.edouard.cl`

---

## Architecture Cible

```
┌─────────────────────────────────────────────────────────────┐
│                    GameProvider (Context)                    │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ WebSocket   │  │ useReducer   │  │ Actions            │  │
│  │ connection  │─▶│ gameReducer  │  │ send(type, data)   │  │
│  │ reconnect   │  │ state        │  │ startGame()        │  │
│  └─────────────┘  └──────────────┘  │ chooseNews(kind)   │  │
│                                      └────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  SwarmPanel   │    │  NewsPanel    │    │  GmTerminal   │
│  useGame()    │    │  useGame()    │    │  useGame()    │
│  agents       │    │  news         │    │  events       │
│  loading      │    │  loading      │    │  loading      │
└───────────────┘    └───────────────┘    └───────────────┘
```

---

## 1. Structure des Fichiers

```
frontend/src/
├── context/
│   └── GameProvider.tsx        # WebSocket + Reducer + Context
├── reducers/
│   └── gameReducer.ts          # Pure reducer pour tous les events
├── hooks/
│   ├── useGame.ts              # Hook principal (state + actions)
│   ├── useGameState.ts         # Read-only state (évite re-renders)
│   └── useGameActions.ts       # Actions only (send, start, choose)
├── components/
│   └── skeletons/
│       ├── AgentSkeleton.tsx   # Skeleton card agent
│       ├── NewsSkeleton.tsx    # Skeleton card news
│       └── ImageSkeleton.tsx   # Placeholder image avec spinner
└── types/
    └── ws-events.ts            # Types des events WebSocket
```

---

## 2. État Global (GameState)

```typescript
interface GameState {
  // Connection
  wsStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  sessionId: string | null;

  // Loading states
  loading: {
    initializing: boolean;  // Premier chargement complet
    agents: boolean;        // Agents en cours de setup
    news: boolean;          // News en cours de génération
    images: boolean;        // Covers en cours de génération
    turn: boolean;          // Résolution du tour en cours
  };

  // Game data
  turn: number;
  maxTurns: number;
  phase: 'loading' | 'select_news' | 'resolving' | 'results' | 'game_over';

  // Agents
  agents: Agent[];
  fallenAgents: FallenAgent[];

  // News
  newsProposal: NewsProposal | null;
  selectedNews: NewsItem | null;

  // Indices
  indices: GlobalIndices | null;
  decerebration: number;

  // GM
  gmCommentary: string;
  gmTerminalLines: GmTerminalLine[];
  gmStrategy: GmStrategy | null;

  // Debate
  debateLines: DebateLine[];
  activeSpeaker: string | null;
}
```

---

## 3. Events WebSocket (Inbound)

| Event Type | Payload | Action Reducer |
|------------|---------|----------------|
| `session.init` | `{ session_id, turn, max_turns }` | Init session |
| `agents.sync` | `{ agents: Agent[] }` | Set agents, `loading.agents: false` |
| `agent.update` | `{ agent_id, ...changes }` | Update single agent |
| `agent.death` | `{ agent_id, killer, epitaph }` | Move to fallenAgents |
| `agent.clone` | `{ agent_id, name, ... }` | Add new agent |
| `news.generating` | `{}` | `loading.news: true` |
| `news.proposal` | `{ real, fake, satirical, gm_commentary }` | Set proposal, `loading.news: false` |
| `images.generating` | `{}` | `loading.images: true` |
| `images.ready` | `{ real: url, fake: url, satirical: url }` | Attach URLs, `loading.images: false` |
| `turn.resolving` | `{}` | `loading.turn: true` |
| `turn.resolved` | `{ indices, decerebration }` | Update state, `loading.turn: false` |
| `gm.commentary` | `{ text }` | Set GM commentary |
| `gm.terminal` | `{ type, text }` | Append to terminal |
| `gm.strategy` | `{ analysis, threat_agents, ... }` | Set strategy |
| `debate.line` | `{ agent, message, type }` | Append debate line |
| `indices.update` | `{ indices, decerebration }` | Update indices |
| `game.end` | `{ win, lose, draw, score }` | Set game over |
| `error` | `{ message }` | Handle error |

---

## 4. Events WebSocket (Outbound)

| Action | Message Type | Payload |
|--------|--------------|---------|
| `startGame(lang)` | `game.start` | `{ lang: 'fr' \| 'en' }` |
| `chooseNews(kind)` | `news.choose` | `{ kind: 'real' \| 'fake' \| 'satirical' }` |
| `nextTurn()` | `turn.next` | `{}` |
| `restartGame()` | `game.restart` | `{}` |

---

## 5. Reducer (gameReducer.ts)

```typescript
type GameAction =
  | { type: 'WS_CONNECTED' }
  | { type: 'WS_DISCONNECTED' }
  | { type: 'WS_ERROR'; error: string }
  | { type: 'SESSION_INIT'; payload: SessionInitPayload }
  | { type: 'AGENTS_SYNC'; payload: Agent[] }
  | { type: 'AGENT_UPDATE'; payload: AgentUpdatePayload }
  | { type: 'AGENT_DEATH'; payload: AgentDeathPayload }
  | { type: 'NEWS_GENERATING' }
  | { type: 'NEWS_PROPOSAL'; payload: NewsProposal }
  | { type: 'IMAGES_GENERATING' }
  | { type: 'IMAGES_READY'; payload: ImageUrls }
  | { type: 'TURN_RESOLVING' }
  | { type: 'TURN_RESOLVED'; payload: TurnResolvedPayload }
  | { type: 'GM_COMMENTARY'; payload: string }
  | { type: 'GM_TERMINAL'; payload: GmTerminalLine }
  | { type: 'DEBATE_LINE'; payload: DebateLine }
  | { type: 'INDICES_UPDATE'; payload: IndicesPayload }
  | { type: 'GAME_END'; payload: GameEndPayload }
  | { type: 'RESET' };

function gameReducer(state: GameState, action: GameAction): GameState {
  switch (action.type) {
    case 'WS_CONNECTED':
      return { ...state, wsStatus: 'connected' };

    case 'AGENTS_SYNC':
      return {
        ...state,
        agents: action.payload,
        loading: { ...state.loading, agents: false, initializing: false },
      };

    case 'NEWS_GENERATING':
      return {
        ...state,
        loading: { ...state.loading, news: true },
        newsProposal: null,
      };

    case 'NEWS_PROPOSAL':
      return {
        ...state,
        newsProposal: action.payload,
        loading: { ...state.loading, news: false },
        phase: 'select_news',
      };

    // ... autres cases

    default:
      return state;
  }
}
```

---

## 6. Loading States & Skeletons

### Quand afficher quoi

| Composant | Condition Loading | Affichage |
|-----------|-------------------|-----------|
| SwarmPanel | `loading.agents` | 4x AgentSkeleton |
| NewsPanel | `loading.news` | 3x NewsSkeleton |
| NewsCard image | `loading.images` | ImageSkeleton (spinner) |
| GmTerminal | `loading.turn` | Typing dots "..." |
| IndicesPanel | `loading.initializing` | Bars à 0% + pulse |
| TopBar | `loading.initializing` | "CONNEXION..." |

### Style Skeletons (Soviet Theme)

```css
/* Skeleton base */
.skeleton {
  background: linear-gradient(
    90deg,
    hsl(var(--soviet-black) / 0.2) 0%,
    hsl(var(--soviet-black) / 0.3) 50%,
    hsl(var(--soviet-black) / 0.2) 100%
  );
  background-size: 200% 100%;
  animation: skeleton-pulse 1.5s ease-in-out infinite;
}

@keyframes skeleton-pulse {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Censored text effect */
.skeleton-text {
  background: hsl(var(--soviet-black));
  color: transparent;
}
.skeleton-text::before {
  content: "████████████";
}
```

---

## 7. Étapes d'Implémentation

### Phase 1 : Infrastructure (2h)
- [ ] Créer `context/GameProvider.tsx`
- [ ] Créer `reducers/gameReducer.ts`
- [ ] Créer `hooks/useGame.ts`
- [ ] Créer `types/ws-events.ts`

### Phase 2 : Skeletons (1h)
- [ ] Créer `AgentSkeleton.tsx`
- [ ] Créer `NewsSkeleton.tsx`
- [ ] Créer `ImageSkeleton.tsx`
- [ ] Ajouter styles skeleton au CSS

### Phase 3 : Migration Composants (3h)
- [ ] Wrapper `App.tsx` avec `GameProvider`
- [ ] Migrer `SwarmPanel` → `useGame()`
- [ ] Migrer `NewsPanel` → `useGame()`
- [ ] Migrer `GmTerminal` → `useGame()`
- [ ] Migrer `IndicesPanel` → `useGame()`
- [ ] Supprimer `useBackendEngine.ts` (ancien hook)

### Phase 4 : Reconnexion & Error Handling (1h)
- [ ] Exponential backoff sur déconnexion
- [ ] Toast/Banner sur erreur WS
- [ ] Retry automatique

### Phase 5 : Tests & Polish (1h)
- [ ] Test connexion/déconnexion
- [ ] Test tous les events
- [ ] Smooth transitions loading → data

---

## 8. Questions Ouvertes

1. **Format des messages WS** — JSON envelope `{ type: string, data: any }` ?
2. **Auth** — Token dans URL WS ou header ?
3. **Heartbeat** — Ping/pong pour détecter déconnexion ?
4. **Buffering** — Queue les events si composant pas encore monté ?

---

## 9. Dépendances

Aucune nouvelle dépendance requise — React natif + WebSocket API browser.

Optional :
- `reconnecting-websocket` (auto-reconnect) — mais on peut le faire nous-mêmes

---

*Dernière mise à jour : 2026-03-01*
