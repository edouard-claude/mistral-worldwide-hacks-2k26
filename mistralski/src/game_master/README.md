# Game Master — Agent Maître du Jeu

## Rôle

Le Game Master est l'intelligence narrative du jeu. Il utilise **Mistral Large API** pour :

1. **Générer des news satiriques** en réaction aux actions du joueur
2. **Proposer des événements** (la "température du jour")
3. **Rédiger le bilan de tour** avec commentaire satirique
4. **Observer les agents individuels** et ajuster la difficulté / les propositions
5. **Documenter l'histoire** de la partie dans des fichiers .md persistants

## Principe

Le Game Master **sait tout**. Les agents individuels (Mistral Small via vLLM) **ne savent rien** — ils réagissent à leur contexte local. Le Game Master voit l'ensemble, croise les données, et ajuste ses propositions pour maximiser le chaos satirique.

## Architecture de fichiers

```
src/game_master/
├── __init__.py
├── engine.py              # GameMasterEngine — orchestrateur principal
├── news_factory.py        # Génération de headlines satiriques
├── turn_evaluator.py      # Bilan de tour + scoring
├── event_proposer.py      # Proposition d'événements au joueur
├── agent_observer.py      # Observation des agents individuels
├── narrator.py            # Commentaire CRT typewriter
│
├── prompts/               # Tous les prompts système du GM
│   ├── system.md          # Prompt système principal du Game Master
│   ├── news_generation.md # Prompt pour générer des headlines
│   ├── turn_bilan.md      # Prompt pour le bilan de tour
│   ├── event_proposal.md  # Prompt pour proposer des événements
│   └── agent_analysis.md  # Prompt pour analyser les agents
│
├── soul/                  # Identité & personnalité du GM
│   ├── soul.md            # QUI est le Game Master (personnalité, ton, limites)
│   └── rules.md           # Règles que le GM doit respecter (équilibrage, satire)
│
└── state/                 # État persistant de la partie (runtime, gitignored)
    ├── history.md          # Journal de la partie (tour par tour)
    ├── player_profile.md   # Profil du joueur (tendances, style, choix récurrents)
    ├── agent_dossiers/     # Un fichier .md par agent avec observations du GM
    │   ├── agent_01.md     # Jean-Édouard — observations, réactions, trajectoire
    │   ├── agent_02.md     # Karen — etc.
    │   └── ...
    └── world_state.md      # Résumé narratif de l'état du monde vu par le GM
```

## Flux par tour

```
1. DÉBUT DE TOUR
   │
   ├─ GM lit: state/history.md + state/player_profile.md + state/world_state.md
   ├─ GM lit: state/agent_dossiers/*.md (état des agents)
   ├─ GM fetch: RSS news réelles (via NewsClient)
   │
   ├─ GM génère: "Température du jour" (event_proposer.py)
   ├─ GM génère: Commentaire CRT (narrator.py)
   │
   ▼
2. JOUEUR AGIT (actions pendant le tour)
   │
   ├─ Chaque action → GM génère 2 headlines satiriques (news_factory.py)
   ├─ GM observe: réactions des agents (agent_observer.py)
   ├─ GM met à jour: state/agent_dossiers/*.md
   │
   ▼
3. FIN DE TOUR
   │
   ├─ GM évalue: impact global (turn_evaluator.py)
   ├─ GM rédige: bilan satirique complet
   ├─ GM met à jour: state/history.md (append du tour)
   ├─ GM met à jour: state/player_profile.md (patterns détectés)
   └─ GM met à jour: state/world_state.md
```

## LLM Routing

| Composant | Modèle | Pourquoi |
|-----------|--------|----------|
| Game Master (tout) | Mistral Large API | Raisonnement long, satire de qualité, vision globale |
| Agents individuels | Mistral Small 3.2 (vLLM GPU :8000) | Réactions rapides, batch, pas besoin de vision globale |
| Mutations de prompts | Devstral Small 2 (vLLM GPU :8001) | Réécriture de code/prompts |
