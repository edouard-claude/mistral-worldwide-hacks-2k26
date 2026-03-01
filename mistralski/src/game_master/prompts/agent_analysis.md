# Prompt — Analyse des Agents

## Instruction

Analyse l'état des agents après les actions du tour {turn}. Mets à jour les observations pour chaque agent impacté.

## Actions prises ce tour
{actions_summary}

## État actuel des agents
{agents_state}

## Dossiers agents existants
{agent_dossiers}

## Règles
- Observer les changements de comportement (niveau, stats, réactions)
- Détecter les agents proches de la neutralisation (stats critiques)
- Identifier les agents qui "résistent" (patterns de résilience)
- Suggérer des actions qui pourraient cibler un agent spécifique
- Chaque observation en 1-2 phrases max, ton factuel (notes internes du GM)

## Format de sortie (JSON strict)
```json
{
  "observations": {
    "agent_01": "Observation mise à jour pour cet agent.",
    "agent_05": "Observation mise à jour pour cet agent."
  },
  "at_risk": ["agent_03"],
  "resistant": ["agent_06", "agent_09"],
  "narrative_note": "Note sur la dynamique agent globale."
}
```
