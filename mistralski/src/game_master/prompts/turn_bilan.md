# Prompt — Bilan de Tour

## Instruction

Rédige le bilan satirique du tour {turn}/{max_turns}.

## Actions prises ce tour
{actions_summary}

## État du monde après ce tour
{world_state}

## Indices globaux (avant → après)
{index_changes}

## Agents impactés
{agent_impacts}

## Profil joueur détecté
{player_profile}

## Règles
- Résumé en 3-5 phrases max, ton Gorafi
- Mentionner les conséquences les plus marquantes
- Si un agent a été neutralisé, commenter avec ironie
- Si des indices atteignent des seuils critiques (>80 ou <20), le signaler
- Ajuster le ton au tempo narratif : début (léger) → milieu (tendu) → fin (épique)

## Format de sortie (JSON strict)
```json
{
  "bilan_text": "Résumé satirique du tour en 3-5 phrases.",
  "moment_fort": "L'événement le plus marquant du tour en 1 phrase.",
  "conseil_ironique": "Un conseil cynique au joueur pour le prochain tour.",
  "difficulty_note": "Note interne sur l'ajustement de difficulté."
}
```
