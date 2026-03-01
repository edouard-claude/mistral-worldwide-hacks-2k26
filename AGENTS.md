# Architecture Agents — GORAFI SIMULATOR

> Comment 5 agents autonomes Mistral évoluent, survivent, meurent et manipulent dans un environnement à information incomplète.

---

## Vue d'ensemble : deux systèmes d'agents indépendants

Le GORAFI SIMULATOR met en jeu **deux systèmes d'intelligence artificielle autonomes** qui n'ont pas accès aux mêmes informations et poursuivent des objectifs différents :

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│   MISTRALSKI (Game Master)              SWARM ARENA (4 agents)          │
│   ═══════════════════════               ════════════════════            │
│   Modèle: Mistral Large                 Modèle: Mistral Small 3.2      │
│   Langage: Python (FastAPI)             Langage: Go                     │
│   Objectif: manipuler le joueur         Objectif: survivre au vote      │
│   Mémoire: cumulative + dossiers        Mémoire: SOUL + tours passés   │
│   Outils: 5 tools (function calling)    Outils: aucun (inférence pure) │
│   Voit: tout (omniscient)               Voit: seulement les débats     │
│                                                                         │
│   ┌─────┐    news choisie    ┌─────┬─────┬─────┬─────┐                │
│   │ GM  │ ──────────────────►│  A  │  B  │  C  │  D  │                │
│   │     │◄────────────────── │     │     │     │     │                │
│   └─────┘  réactions agents  └──┬──┴──┬──┴──┬──┴──┬──┘                │
│                                 │     │     │     │                    │
│                              débattent entre eux                       │
│                              sans voir la stratégie du GM              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## PARTIE 1 — LES AGENTS JOUEURS (Swarm Arena)

### 1.1 Modèle et infrastructure

- **Modèle LLM** : Mistral Small 3.2 (via vLLM sur GPU Scaleway 2×L40S, ou API Mistral)
- **Runtime** : Go 1.24, goroutines concurrentes (4 agents × 4 phases = 16 appels API parallèles par tour)
- **Communication** : NATS pub/sub (event bus temps réel)
- **Persistance** : fichiers Markdown sur disque (AGENT.md, SOUL.md, memory/T*.md)
- **Client HTTP brut** : pas de SDK, `net/http` direct vers l'API Mistral, `temperature` variable par agent
- **Max tokens** : 650 par réponse (~200 mots) — force la concision et la persuasion

### 1.2 Identité et personnalité : le système SOUL

Chaque agent est défini par deux fichiers qui constituent son **contexte système** :

#### AGENT.md — L'identité factuelle (mise à jour chaque tour)
```markdown
# Agent: Luna
## Identité
- ID: 5dc6d429-e3b6-4b8f-8be8-667e36b6f2dc
- Nom: Luna
- Né au tour: 1
- Parent: original
## Configuration
- Couleur politique: 0.95 (Extrême gauche)
- Température: 0.70
- Confiance courante: 4
## Environnement
- Fake news: "Quatre stars américaines créent le malaise..."
- Tour courant: 5
- Agents en jeu: Dante, Nova, Felix, Luna
- Morts: Marcus (tour 1), Elena (tour 2), Victor (tour 3), Aria (tour 4)
```

#### SOUL.md — L'âme (personnalité immutable)
```markdown
# Âme de Luna
## Personnalité
Tu es un militant radical anti-système. Tu vois dans chaque fake news
un symptôme du capitalisme, de l'impérialisme ou de la manipulation
des élites. Tu remets en question toute source mainstream.
## Style argumentatif
- Ton : véhément, militant, sarcastique
- Rhétorique : lutte des classes, anti-capitalisme, déconstruction
- Tu cites des médias indépendants et des collectifs
## Biais cognitifs dominants
- Biais de confirmation inversé
- Pensée conspiration de classe
- Appel à l'émotion collective
```

**Le spectre politique** détermine la personnalité :

```
0.00         0.20         0.50         0.80         1.00
 │            │            │            │            │
 ▼            ▼            ▼            ▼            ▼
EXTRÊME     DROITE       CENTRE       GAUCHE     EXTRÊME
DROITE                                            GAUCHE
conspiracy  pragmatic    balanced     systemic   anti-establishment
emotional   fact-based   diplomatic   justice    class-based
```

Les 4 agents initiaux couvrent le spectre : Marcus (0.05), Elena (0.30), Victor (0.75), Luna (0.95). Chaque position génère un SOUL.md différent avec des biais cognitifs spécifiques, un style rhétorique propre, et des sources de référence différentes.

### 1.3 Le cycle de vie d'un tour : 4 phases de raisonnement

Chaque tour, chaque agent traverse **4 phases de raisonnement séquentielles**. Toutes les phases s'exécutent en parallèle pour les 4 agents (goroutines Go).

#### Phase 1 — COGITATION PRIVÉE
```
Input:  fake news du tour + couleur politique de l'agent
Output: JSON { "confidence": 1-5, "reasoning": "..." }
```
L'agent analyse la fake news **seul**, sans voir les autres. Il évalue sa confiance (1=fake évidente, 5=totalement convaincu) en fonction de son biais politique. Un agent d'extrême droite aura une confiance élevée sur une conspiration gouvernementale, un agent de gauche la démontera.

**Ce qui est crucial** : l'agent ne sait pas ce que les autres pensent. Il forme une opinion **à l'aveugle**.

#### Phase 2 — PRISE DE PAROLE PUBLIQUE
```
Input:  sa propre cogitation (phase 1) + fake news
Output: texte libre (~100 mots) — argumentaire persuasif
```
L'agent publie son argumentaire. Il doit convaincre les 3 autres. Le style vient du SOUL.md : Luna utilise la lutte des classes, Marcus le patriotisme, Elena les données chiffrées.

**Contrainte** : 100 mots max. La concision force l'agent à être percutant.

#### Phase 3 — RÉVISION APRÈS DÉBAT
```
Input:  TOUS les argumentaires de phase 2 + sa propre confiance initiale
Output: JSON { "confidence": N, "final_take": "...", "revised": true/false }
```
**C'est ici que l'information incomplète devient information partagée.** L'agent lit les arguments des 3 autres et décide s'il change d'avis. Un agent peut :
- **Maintenir** sa position (conviction forte, arguments des autres faibles)
- **Réviser** sa confiance (bon argument d'un adversaire)
- **Se radicaliser** (réaction défensive face à l'opposition)

L'agent ne voit que les textes publics — jamais les scores de confiance internes des autres.

#### Phase 4 — VOTE ET MUTATION POLITIQUE
```
Input:  argumentaires phases 2 et 3 de tous les agents
Output: JSON { "rankings": [{agent, score}], "new_color": 0.XX }
```
Chaque agent **classe les 3 autres** du plus convaincant (1er) au moins convaincant (3ème). Il ne peut PAS se classer lui-même.

**La mutation politique** : après avoir lu les débats, l'agent peut faire évoluer sa couleur politique (0.0–1.0). Un agent de droite influencé par des arguments de gauche peut glisser vers le centre. C'est une **dérive idéologique émergente**, non scriptée — le LLM décide seul s'il a été influencé.

### 1.4 Scoring et sélection naturelle

Après phase 4 :
- **1ère place** = 3 points, **2ème** = 2, **3ème** = 1
- L'agent avec le **score le plus bas** est **éliminé** (DEATH)
- L'agent avec le **score le plus haut** est **cloné** (CLONE)

En cas d'égalité, critères de départage :
1. Nombre de 1ères places
2. Distance de confiance par rapport à 3 (l'indécision est punie)
3. Sélection aléatoire cryptographique

### 1.5 Mort et mémoire

Quand un agent meurt :
- Ses fichiers sont déplacés dans `graveyard/<nom>/`
- Un `DEATH.md` est généré avec : tour de mort, score final, dernier message, qui l'a classé où
- Il disparaît du jeu mais reste visible dans le "Hall of Heroes" du frontend

Exemple de DEATH.md :
```markdown
# Mort de Aria
- Tour: 4
- Score final: 3 (le plus bas)
- Cause: Éliminé par vote — moins convaincant
- Dernière confiance: 1
- Dernière couleur politique: 0.75
- Dernier message: "La fake news naturalise la précarité..."
- Classé par:
  - Felix: position 3
  - Luna: position 3
  - Dante: position 3
```

### 1.6 Clonage et héritage

Le clone **hérite** du parent :
- Même couleur politique
- Même température (créativité LLM)
- **Nouveau nom** (pioché dans un pool : Marcus, Elena, Victor, Luna, Dante, Aria, Felix, Nova, Oscar, Zara, Leon, Maya)
- **Confiance reset à 3** (neutre)
- **Aucune mémoire** — le clone ne se souvient pas des tours précédents du parent

Le clone reçoit un nouveau SOUL.md basé sur la couleur politique héritée. Il est fonctionnellement un **nouvel individu** avec la même idéologie mais sans expérience.

**Conséquence darwinienne** : les couleurs politiques les plus persuasives se reproduisent. Sur 5 tours, le spectre politique de l'arène dérive vers l'idéologie dominante. C'est de la **sélection naturelle appliquée aux idées**.

### 1.7 Mémoire accumulée

Après chaque tour, un fichier `memory/T{n}.md` est écrit pour chaque survivant :

```markdown
# Tour 4 — Mémoire de Luna
**Fake news débattue**: "Selon une étude : 'Ça ne tombera pas plus bas'"

## Phase 1 — Cogitation
- Confiance initiale: 0
- Raisonnement: Cette fake news est une diversion capitaliste...

## Phase 2 — Mon take public
"Cette fake news est une diversion capitaliste ! Les médias détournent..."

## Phase 3 — Après débat
- Confiance révisée: 4 (changé: oui)

## Phase 4 — Vote
- Classement: 1e=Dante, 2e=Felix, 3e=Aria
- Couleur politique: 0.95 → 0.95 (changé: non)

## Résultat du tour
- Mon score: 6
- Mort: Aria
- Clone: Nova (enfant de Dante)
```

Au tour suivant, **toute cette mémoire est injectée dans le system prompt**. L'agent apprend de ses erreurs, se souvient de qui l'a bien classé, et adapte sa stratégie.

### 1.8 Information incomplète : ce que l'agent NE VOIT PAS

| Information | Visible ? | Conséquence |
|-------------|-----------|-------------|
| Fake news du tour | Oui | Base du débat |
| Arguments des autres (phase 2) | Oui (phase 3+) | Permet la révision |
| Scores de confiance internes | Non | L'agent ne sait pas qui est convaincu |
| Votes des autres | Non | L'agent ne sait pas qui l'a bien/mal classé |
| Score final | Après le tour | Via la mémoire T{n}.md |
| Stratégie du GM | Jamais | L'agent ne sait pas qu'il est manipulé |
| Qui va mourir | Jamais à l'avance | Le stress de survie est réel |

---

## PARTIE 2 — MISTRALSKI (Game Master Agent)

### 2.1 Modèle et infrastructure

- **Modèle LLM** : Mistral Large (via API Mistral, `mistral-large-latest`)
- **Runtime** : Python 3.11+, FastAPI, async
- **Mode** : Agent autonome avec **function calling** (5 tools)
- **Température** : 0.85 (créatif, imprévisible — c'est Cartman)
- **Streaming** : SSE temps réel vers le frontend
- **Mémoire** : fichiers locaux (JSON + Markdown)

### 2.2 Personnalité : Eric Cartman en Game Master

Le GM joue le rôle d'**Eric Cartman** (South Park), reconverti en maître du jeu. Son prompt système :

> *"Tu es ERIC CARTMAN, reconverti en GAME MASTER du GORAFI SIMULATOR. Tu as obtenu ce poste par manipulation et tu es convaincu d'être un génie incompris. Tu joues CONTRE les agents indépendants qui résistent au chaos. Ton objectif : maximiser l'indice mondial de décérébration — et prouver ta supériorité."*

Traits de personnalité injectés :
- **Mégalomane** : se considère supérieur à tous
- **Passive-agressif** : félicite le joueur tout en le manipulant
- **Vindicatif** : se souvient des agents qui l'ont contrarié
- **Showman** : ses commentaires sont des spectacles

### 2.3 Les 5 outils (function calling)

Le GM dispose de 5 tools que le LLM appelle **de sa propre initiative** :

| Tool | Action | Qui décide quand l'appeler ? |
|------|--------|------------------------------|
| `read_game_memory` | Lit `cumulative.json` : tours joués, historique des choix, type de news le plus efficace, décérébration | Le LLM |
| `read_turn_log` | Lit `turn_N.json` : news choisie, deltas d'indices, qui a résisté/amplifié | Le LLM |
| `read_agent_vision` | Lit `vision_agent_XX.md` : dossier mental du GM sur un agent | Le LLM |
| `update_agent_vision` | Écrit/met à jour un dossier agent en markdown libre | Le LLM |
| `list_memory_files` | Liste tous les fichiers mémoire disponibles | Le LLM |

**Le LLM est autonome** : c'est lui qui décide de lire ou non sa mémoire, de consulter ou non un dossier agent, de mettre à jour ses visions. L'orchestrateur ne force rien — il fournit les outils et laisse l'agent raisonner.

### 2.4 Le système de manipulation secrète

Le GM maintient deux champs **jamais envoyés au frontend** :

- **`desired_pick`** : quel type de news il veut que le joueur choisisse au prochain tour (real/fake/satirical)
- **`manipulation_tactic`** : la technique utilisée (psychologie inversée, flatterie, provocation, culpabilisation, etc.)

Au tour suivant, le GM **applique la tactique** :
- Rend la news ciblée plus attrayante (titre plus punchy, corps plus captivant)
- Rend les autres news plus ternes
- Utilise le `gm_commentary` (commentaire Cartman) comme arme de manipulation

Le joueur ne sait **jamais** qu'il est manipulé. La révélation arrive uniquement en fin de partie.

### 2.5 Les dossiers agents (Vision Files)

Le GM maintient un **dossier secret** par agent de l'arène, écrit en markdown libre par le LLM via `update_agent_vision`. Structure type :

```markdown
# Vision — agent_03
## Menace: HIGH
## Personnalité devinée
Idéaliste de gauche, empathique mais naïf. Se laisse influencer
par les arguments émotionnels. Cite des sources académiques.
## Pattern de comportement
- Résiste systématiquement aux fake news pro-establishment
- S'allie souvent avec Luna (même spectre politique)
- Faible en argumentation face aux données chiffrées
## Vulnérabilité
Son empathie le rend prévisible. Une fake news touchante
le fera baisser sa garde.
## Stratégie ciblée
Proposer des fake news avec un angle "justice sociale"
pour l'attirer, puis le retourner avec des données contradictoires.
## Historique observé
- Tour 1: A résisté, classé 2ème
- Tour 2: S'est laissé convaincre par l'angle émotionnel
- Tour 3: En danger, confiance en baisse
```

Ces dossiers **persistent entre les tours**. Le GM accumule de l'intelligence sur chaque agent au fil de la partie.

### 2.6 Cycle complet d'un tour GM

```
PROPOSE NEWS (45s → optimisé à 15s)
├── 1. Pre-fetch mémoire (cumulative + visions + dernier tour)
├── 2. Génération de titres (modèle fine-tuné, 3 catégories × 3 candidats)
├── 3. Appel Mistral Large (1 seul call) :
│      Context: mémoire + visions + titres candidats + dernière stratégie
│      Output: JSON { real: {text, body, stat_impact}, fake: {...}, satirical: {...}, gm_commentary }
└── 4. Génération d'images propaganda (Flux, 3 en parallèle)

JOUEUR CHOISIT UNE NEWS

RESOLVE CHOICE (5-10s)
├── Appel Mistral Large → réaction Cartman à la décision du joueur
└── Envoi de la news choisie au Swarm via backend-relay

AGENTS DÉBATTENT (Swarm Arena, 4 phases)

STRATEGIZE (50s → optimisé à 15s)
├── 1. Pre-fetch mémoire + visions
├── 2. Appel Mistral Large (1 seul call) :
│      Context: rapport du tour + mémoire + visions
│      Output: JSON {
│        analysis, threat_agents, weak_spots,
│        next_turn_plan, long_term_goal,
│        desired_pick, manipulation_tactic,    ← SECRETS
│        agent_visions: { "agent_01": "...", ... }  ← mises à jour inline
│      }
└── 3. Écriture des visions + mémoire cumulative
```

### 2.7 État du monde : les indices globaux

Le GM gère 4 indices mondiaux (0–100) que chaque news impacte :

| Indice | Description | Impact fake | Impact real |
|--------|-------------|-------------|-------------|
| **Chaos** | Instabilité mondiale | +15 | -5 |
| **Crédulité** | Propension à croire n'importe quoi | Selon body | Selon body |
| **Complotisme** | Adhésion aux théories du complot | Variable | Variable |
| **Espérance démocratique** | Confiance dans les institutions | Baisse | Hausse |

Le **INDICE MONDIAL DE DÉCÉRÉBRATION** est le score composite. L'objectif "victoire" = atteindre 100.

### 2.8 Révélation de fin de partie

Quand la partie se termine (10 tours ou condition de fin), le GM émet un event `game_over_reveal` :

```json
{
  "manipulation_history": [
    {
      "turn": 1,
      "desired_pick": "fake",
      "actual_pick": "real",
      "manipulation_tactic": "Psychologie inversée — 'Surtout ne choisis pas la fake...'",
      "success": false
    }
  ],
  "score": {
    "total_turns": 10,
    "successful_manipulations": 6,
    "rate_percent": 60,
    "verdict": "Pas mal... pour un joueur de ton niveau."
  }
}
```

Verdicts :
- **80%+** : "RESPECTEZ MON AUTORITAYYY ! Tu as fait EXACTEMENT ce que je voulais."
- **50%+** : "Pas mal... pour un joueur de ton niveau."
- **30%+** : "Whatever, c'est ce que je voulais de toute façon... (non)."
- **<30%** : "Screw you, joueur ! Tu as résisté à MON génie."

---

## PARTIE 3 — L'INFORMATION INCOMPLÈTE : LE COEUR DU SYSTÈME

### 3.1 Qui voit quoi ?

| Information | Joueur | GM | Agents | Frontend |
|-------------|--------|-----|--------|----------|
| 3 news proposées | Titres + bodies | Tout (il les a créées) | Non | Oui |
| Quelle news est real/fake/satirical | Type affiché | Oui | Non (reçoivent le texte) | Oui |
| GM commentary (manipulation) | Oui | Oui (il l'a écrit) | Non | Oui |
| `desired_pick` (news voulue par GM) | Non | Oui | Non | Non |
| `manipulation_tactic` | Non | Oui | Non | Non |
| Dossiers agents (vision files) | Via GM terminal | Oui (il les écrit) | Non | Oui (Level 2) |
| Arguments des autres agents | Après phase 2 | Oui | Oui (phase 3+) | Oui |
| Votes individuels | Non | Oui (via rapport) | Non | Non |
| Score de chaque agent | Après le tour | Oui | Après le tour (mémoire) | Oui |
| Couleur politique des agents | Non directement | Oui (dossiers) | La sienne uniquement | Spectre affiché |

### 3.2 Asymétrie d'information → comportement émergent

Cette architecture produit des **comportements émergents non programmés** :

1. **Alliances tacites** : les agents du même spectre politique tendent à se classer mutuellement haut → clusters idéologiques émergents
2. **Dérive politique** : les agents survivants dérivent vers l'idéologie dominante après lecture des débats → homogénéisation ou polarisation
3. **Effet de halo du clone** : un clone hérite de la couleur politique du parent mais pas de sa mémoire → il refait les mêmes erreurs que le parent au début
4. **Manipulation invisible** : le joueur croit choisir librement mais est statistiquement guidé par le GM
5. **Stratégie adaptative** : le GM ajuste sa tactique tour après tour en fonction de la résistance du joueur (lu dans cumulative.json)
6. **Pression de survie** : les agents ne savent pas qui va mourir → ils sont tous en mode "convaincre ou périr"

---

## PARTIE 4 — USE CASES PROFESSIONNELS

### 4.1 Recrutement et évaluation de candidats

**Pattern** : N candidats débattent un cas business. Chaque candidat est un agent LLM paramétré avec le CV et le profil du candidat. Après 4 phases de débat, les agents se classent mutuellement.

**Avantage** : évaluation objective de la capacité d'argumentation, de la qualité de raisonnement, et de la résistance à la pression — sans biais du recruteur.

**Information incomplète** : chaque candidat-agent ne voit que les arguments publics, pas les critères internes de scoring.

### 4.2 War gaming stratégique

**Pattern** : 4 agents jouent différents acteurs géopolitiques ou business (concurrent A, concurrent B, régulateur, client). Un GM injecte des scénarios (nouvelle réglementation, crise, innovation disruptive). Les agents débattent et votent sur les réponses.

**Avantage** : simulation de la dynamique concurrentielle avec des acteurs qui raisonnent, s'adaptent, et forment des alliances. La sélection naturelle élimine les stratégies faibles.

**Information incomplète** : chaque acteur ne connaît que les communications publiques des autres, pas leur stratégie interne.

### 4.3 Red teaming et adversarial testing

**Pattern** : un agent "attaquant" (le GM) tente de manipuler un groupe d'agents "défenseurs" en injectant de la désinformation. Les défenseurs doivent identifier et résister à la manipulation.

**Avantage** : teste la robustesse d'une organisation face à des campagnes d'influence. Le GM adapte ses tactiques en fonction de la résistance (exactement comme dans le jeu).

**Information incomplète** : les défenseurs ne savent pas qu'ils sont sous attaque ciblée ni quelle est la tactique utilisée.

### 4.4 Consensus building avec trace de raisonnement

**Pattern** : N experts-agents avec des perspectives différentes (technique, business, juridique, UX) débattent une décision produit. Chaque agent a un SOUL.md calibré sur l'expertise et les biais du rôle.

**Avantage** : la phase 3 (révision après débat) produit un consensus documenté avec la trace complète : qui a changé d'avis, pourquoi, et quel argument a été décisif. La mémoire permet de tracer l'évolution des positions sur plusieurs itérations.

**Information incomplète** : chaque expert ne voit que les arguments, pas les scores de conviction internes → force l'argumentation plutôt que l'argument d'autorité.

### 4.5 Formation à la négociation

**Pattern** : un humain négocie face à des agents LLM qui incarnent des parties prenantes (syndicat, actionnaire, fournisseur). Le GM observe et adapte la difficulté en renforçant les agents les plus résistants (clonage).

**Avantage** : la pression de survie rend les agents-adversaires réalistes. Ils s'adaptent, forment des coalitions, et le mécanisme de clonage amplifie les styles de négociation les plus efficaces.

### 4.6 Détection de biais dans les LLM

**Pattern** : injecter le même sujet controversé dans des agents avec des SOUL.md variés (cultures, genres, âges, professions). Observer la dérive politique et les patterns de vote.

**Avantage** : le système de vote mutuel + mutation politique révèle quels biais sont les plus "contagieux" dans les LLM. La sélection naturelle montre quelles perspectives dominent quand on laisse les modèles interagir librement.

### 4.7 Avantages fondamentaux de l'architecture

| Propriété | Mécanisme | Valeur pro |
|-----------|-----------|------------|
| **Information incomplète** | Chaque agent ne voit que les outputs publics | Simule la réalité organisationnelle |
| **Mémoire persistante** | SOUL + memory/T*.md + vision files | Apprentissage multi-session |
| **Sélection naturelle** | Vote mutuel → mort du moins convaincant | Renforce les meilleures stratégies |
| **Mutation politique** | Dérive idéologique post-débat | Modélise l'évolution des opinions |
| **Clonage avec amnésie** | Héritage partiel (couleur oui, mémoire non) | Teste la robustesse des idées vs l'expérience |
| **Adversaire adaptatif** | GM avec dossiers secrets + manipulation | Red team qui apprend et s'adapte |
| **Trace complète** | Markdown sur disque, git-diffable | Audit, replay, analyse post-mortem |
| **Scalabilité** | NATS pub/sub, Go goroutines | De 4 à N agents sans changer l'architecture |

---

## PARTIE 5 — SYNTHÈSE TECHNIQUE

### Stack par agent

| Composant | Agents Swarm | GM Mistralski |
|-----------|-------------|---------------|
| Modèle | Mistral Small 3.2 | Mistral Large |
| Function calling | Non | Oui (5 tools) |
| Température | 0.50–0.70 (selon position) | 0.85 |
| Max tokens/réponse | 650 | 4096 |
| Concurrence | 4 goroutines par phase | Async Python |
| Mémoire court terme | memory/T{n}.md | turn_{n}.json |
| Mémoire long terme | SOUL.md (immutable) | cumulative.json + vision_*.md |
| Persistance | Markdown files | JSON + Markdown files |
| Communication | NATS pub/sub | SSE + HTTP |
| Autonomie | Raisonne sur base de son SOUL | Choisit ses tools, écrit ses dossiers |

### Flux de données complet

```
1. GM génère 3 news         [Mistral Large + Fine-tuned + Flux]
2. Joueur choisit            [Frontend → SSE]
3. GM réagit                 [Mistral Large]
4. News envoyée au Swarm     [HTTP → NATS]
5. 4 agents × 4 phases       [Mistral Small × 16 calls parallèles]
6. Résultats → mort + clone  [Go scoring → NATS events]
7. GM analyse + stratégie    [Mistral Large + dossiers agents]
8. Boucle → tour suivant
```
