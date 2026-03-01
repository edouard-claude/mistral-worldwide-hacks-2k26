# SKILL — News Proposal

## Trigger
Début de chaque tour.

## Input
- game_state: turn, indices, decerebration, active_agents
- gm_strategy (si existe): next_turn_plan, threat_agents, weak_spots

## Process
1. Charger SOUL.md pour le ton
2. Si stratégie précédente → orienter le thème des news en conséquence
3. Appel Mistral Large API (temperature=0.8, json_mode=true)
4. Parser JSON → NewsProposal (3 headlines globales)
5. Présenter au joueur (HITL) — attendre son choix

## Output
```json
{
  "real":      {"id": "tN_real",      "text": "...", "kind": "real",      "stat_impact": {...}, "source_real": "Reuters"},
  "fake":      {"id": "tN_fake",      "text": "...", "kind": "fake",      "stat_impact": {...}},
  "satirical": {"id": "tN_satirical", "text": "...", "kind": "satirical", "stat_impact": {...}},
  "gm_commentary": "Phrase sarcastique"
}
```

## Contraintes
- Les 3 news traitent du MÊME THÈME (géopolitique, économie, tech, etc.)
- Le fake doit être crédible — pas de signal d'humour
- Le satirical doit être drôle — style Gorafi absurde
- stat_impact : clés parmi credibilite, rage, complotisme, esperance_democratique
- Impact du fake > real (récompense le chaos)
- Impact du satirical = imprévisible (peut backfirer)
