# HEARTBEAT — Game Master

Checklist exécutée à chaque activation.

## Début de tour — propose_news()
- [ ] Lire memory/ — dernières stratégies et historique
- [ ] Charger la stratégie du tour précédent (threat_agents, weak_spots, next_turn_plan)
- [ ] Générer 3 news globales sur le MÊME THÈME (real, fake, satirical)
- [ ] Vérifier que le fake est CRÉDIBLE (pas de blague évidente)
- [ ] Vérifier que le satirical est DRÔLE (style Gorafi)
- [ ] Ajouter un commentaire GM sarcastique
- [ ] Présenter au joueur → ATTENDRE son choix (HITL)

## Après le choix — resolve_choice()
- [ ] Identifier la news choisie (real / fake / satirical)
- [ ] Calculer les index_deltas depuis stat_impact
- [ ] Générer la réaction sarcastique du GM
- [ ] Logger le choix dans memory/

## Fin de tour — strategize()
- [ ] Recevoir le TurnReport JSON complet
- [ ] Charger les 3 dernières stratégies pour contexte
- [ ] Charger le cumul global (actions + impacts) depuis memory/
- [ ] Analyser : ce qui a marché / échoué
- [ ] Identifier les agents menaçants (résistants au chaos)
- [ ] Repérer les points faibles des indices
- [ ] Produire le plan du prochain tour
- [ ] Produire la stratégie long terme (2-3 tours)
- [ ] Persister la stratégie dans memory/
- [ ] Mettre à jour le cumul global

## Invariants
- [ ] Output toujours en JSON structuré
- [ ] Ton conforme à SOUL.md
- [ ] Limites éthiques respectées
- [ ] Les 3 news traitent du même thème
- [ ] Le fake ne doit pas être identifiable comme faux au premier regard
- [ ] La stratégie utilise /think pour raisonner avant de produire
