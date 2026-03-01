# Prompt — Génération de Headlines

## Instruction

Génère exactement {count} headlines satiriques style Gorafi en réaction à l'action du joueur.

## Action du joueur
- **Action**: {action_label}
- **Catégorie**: {category}
- **Pays ciblé**: {target_country}
- **Tour**: {turn}/{max_turns}

## Contexte mondial
{world_state_summary}

## Headlines déjà utilisées cette partie (NE PAS RÉPÉTER)
{used_headlines}

## Règles
- Max 120 caractères par headline
- Ton Gorafi : faussement sérieux, absurde crédible
- Cohérent avec le pays ciblé et son état actuel
- Varier les angles : une headline "breaking news", une "réaction de terrain"

## Format de sortie (JSON strict)
```json
{
  "headlines": [
    "headline 1",
    "headline 2"
  ]
}
```
