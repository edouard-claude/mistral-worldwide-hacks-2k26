# News Title API

Générateur de titres de news satiriques ou factuels selon un score de véracité (0–100).
Modèle : `Laroub10/news-title-mistral-ft` — Mistral-7B fine-tuné sur données Gorafi / The Onion.

**Endpoint live** : `http://mistralski-fine-tuned.wh26.edouard.cl:80`

---

## Utilisation rapide

```bash
curl -X POST http://mistralski-fine-tuned.wh26.edouard.cl:80/generate \
  -H "Content-Type: application/json" \
  -d '{"score": 5, "lang": "fr", "n": 3}'
```

Réponse :
```json
{
  "titles": [
    "Le Sénat adopte une loi obligeant les pigeons à déclarer leurs revenus d'ici 2026",
    "L'INSEE révèle que 83% des Français font semblant de comprendre leur feuille de paie"
  ],
  "score": 5,
  "lang": "fr"
}
```

---

## Comportement selon le score

| Score  | Ton |
|--------|-----|
| 0–10   | Absurde total — style Le Gorafi, institution + situation grotesque |
| 11–30  | Satire sociale — stéréotypes français, faux sondage chiffré |
| 31–69  | Clickbait — légèrement exagéré, sensationnaliste |
| 70–100 | Factuel — style Le Monde / France Info |

---

## Paramètres

| Champ       | Type  | Obligatoire | Défaut | Contraintes |
|-------------|-------|-------------|--------|-------------|
| score       | int   | oui         | —      | 0–100       |
| lang        | str   | non         | `"fr"` | `"fr"` / `"en"` |
| n           | int   | non         | `1`    | 1–10        |
| temperature | float | non         | `0.9`  | 0.1–2.0     |

---

## Endpoints

| Méthode | Route | Description |
|---------|-------|-------------|
| POST | `/generate` | Génère des titres |
| GET  | `/health`   | Health check |
| GET  | `/`         | Interface web |
| GET  | `/docs`     | Swagger UI |

---

## Stack

- **API** : FastAPI + Uvicorn
- **Inférence** : serveur vLLM OpenAI-compatible (`http://51.159.173.147:8001/v1`)
- **Modèle** : `Laroub10/news-title-mistral-ft` (Mistral-7B + LoRA, entraîné sur 3 epochs)
- **Deploy** : Docker (~300 MB) sur CapRover

## Variables d'environnement

```bash
MODEL_BASE_URL=http://51.159.173.147:8001/v1   # URL du serveur vLLM
MODEL_ID=Laroub10/news-title-mistral-ft         # Modèle à appeler
PORT=80                                          # Port d'écoute
```

Voir `.env.example` pour le template complet.
