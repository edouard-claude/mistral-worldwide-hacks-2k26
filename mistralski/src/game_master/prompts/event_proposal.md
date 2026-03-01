# Prompt — Proposition d'événement (Température du Jour)

## Instruction

Propose la "Température du Jour" pour le tour {turn}/{max_turns}. C'est un événement mondial ou local qui colore le tour et influence les réactions des agents.

## News réelles du jour (inspiration)
{real_news}

## État du monde actuel
{world_state}

## Historique des températures précédentes (NE PAS RÉPÉTER)
{previous_temperatures}

## Profil joueur
{player_profile}

## Règles
- L'événement doit être plausible dans un univers satirique
- Il doit offrir des opportunités d'action au joueur (pas juste cosmétique)
- Varier les types : crise politique, buzz médiatique, catastrophe absurde, découverte scientifique douteuse
- Ajuster au tempo : début = léger, milieu = tendu, fin = explosif
- Inspiré des news réelles mais JAMAIS identique

## Format de sortie (JSON strict)
```json
{
  "temperature": "Description courte de l'événement (1-2 phrases max)",
  "affected_countries": ["FR", "US"],
  "index_effects": {"rage": +5, "credibilite": +3},
  "commentary": "Commentaire CRT du Game Master sur cet événement",
  "real_news_source": "La news réelle qui a inspiré cet événement (ou null)"
}
```
