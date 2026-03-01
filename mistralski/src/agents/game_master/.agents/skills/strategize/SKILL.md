# SKILL — Strategize

## Trigger
Fin de chaque tour, après que les agents indépendants ont réagi.

## Input
- TurnReport JSON :
  - chosen_news, indices_before, indices_after
  - agent_reactions (qui a résisté, qui a amplifié)
  - agents_neutralized, agents_promoted
  - decerebration actuelle
- Mémoire cumulative :
  - Historique des choix par tour (memory/)
  - 3 dernières stratégies (strategy_history)
  - Cumul global actions + impacts

## Process
1. Charger les 3 dernières stratégies pour contexte
2. Charger le cumul global depuis memory/
3. Appel Mistral Large API (temperature=0.7, json_mode=true)
   - Le LLM raisonne dans /think : analyse tendances, calcule trajectoire
   - Produit le plan en JSON structuré
4. Persister la stratégie dans memory/
5. Mettre à jour le cumul global

## Output
```json
{
  "turn": 3,
  "analysis": "La fake news sur la migration a boosté complotisme +12. Aisha a résisté.",
  "threat_agents": ["agent_07"],
  "weak_spots": ["Espérance démocratique basse, exploitable", "Rage en hausse"],
  "next_turn_plan": "Thème pandémie pour exploiter la peur et contourner Aisha",
  "long_term_goal": "Saturer le débat rationnel sur 2 tours puis narratives apocalyptiques"
}
```

## Mémoire cumulative (memory/)

### Par tour : `memory/turn_N.json`
```json
{
  "turn": 3,
  "chosen_kind": "fake",
  "chosen_text": "...",
  "index_deltas": {"credibilite": +10, "complotisme": +8},
  "agents_resisted": ["agent_07"],
  "agents_amplified": ["agent_03", "agent_01"],
  "decerebration_delta": +6.0,
  "strategy": {"next_turn_plan": "...", "threat_agents": [...]}
}
```

### Global : `memory/cumulative.json`
```json
{
  "total_turns": 3,
  "choices": {"real": 1, "fake": 2, "satirical": 0},
  "total_index_deltas": {"credibilite": +25, "rage": +18, ...},
  "most_effective_kind": "fake",
  "persistent_threats": ["agent_07", "agent_06"],
  "neutralized_count": 0,
  "current_decerebration": 38.0
}
```

## Strategy Principles
- Identifier les agents résistants → proposer des thèmes qui les contournent
- Exploiter les indices bas (espérance_democratique < 40 → pousser)
- Varier les thèmes pour éviter que les agents s'adaptent
- Tours 7-10 : escalade agressive, narratives apocalyptiques
