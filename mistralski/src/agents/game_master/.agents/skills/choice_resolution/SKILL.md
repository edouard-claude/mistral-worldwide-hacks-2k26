# SKILL — Choice Resolution

## Trigger
Le joueur a choisi une des 3 news (HITL).

## Input
- proposal: NewsProposal (les 3 news)
- chosen_kind: "real" | "fake" | "satirical"

## Process
1. Extraire la news choisie du proposal
2. Appel Mistral Large API (temperature=0.9, json_mode=false) pour la réaction
3. La réaction dépend du choix :
   - real → moque le manque d'ambition
   - fake → félicite la contribution au chaos
   - satirical → admire le sens de l'absurde
4. Retourner NewsChoice avec index_deltas

## Output
```json
{
  "turn": 3,
  "chosen": {"id": "t3_fake", "text": "...", "kind": "fake", "stat_impact": {...}},
  "index_deltas": {"credibilite": 10, "complotisme": 8},
  "gm_reaction": "Phrase sarcastique du GM"
}
```

## Side Effects
- Logger le choix dans memory/ (tour, kind, impact)
- La news choisie est ajoutée à headlines_history du GameState
