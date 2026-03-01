# Contrat d'API — News Title Generator

**Base URL** : `http://mistralski-fine-tuned.wh26.edouard.cl:80`
**Modèle** : `Laroub10/news-title-mistral-ft` (Mistral-7B + LoRA fine-tuné)
**Infra** : GPU NVIDIA L40S — latence ~1-3s par titre

---

## Endpoints

### POST `/generate` — Générer des titres

```
POST http://mistralski-fine-tuned.wh26.edouard.cl:80/generate
Content-Type: application/json
```

**Body** :

| Champ       | Type  | Obligatoire | Défaut | Contraintes          | Description |
|-------------|-------|-------------|--------|----------------------|-------------|
| score       | int   | oui         | —      | 0–100                | Score de véracité. 0 = satire absurde, 100 = factuel |
| lang        | str   | non         | `"fr"` | `"fr"` ou `"en"`    | Langue de génération |
| n           | int   | non         | `1`    | 1–10                 | Nombre de titres à générer |
| temperature | float | non         | `0.9`  | 0.1–2.0              | Inventivité. Bas = prévisible, élevé = créatif |

**Exemple body** :
```json
{
  "score": 5,
  "lang": "fr",
  "n": 2,
  "temperature": 0.9
}
```

**Réponse 200** :
```json
{
  "titles": [
    "Le gouvernement annonce que les fonctionnaires peuvent maintenant travailler à domicile... à perpétuité",
    "Par erreur, Didier Bourdon joue deux fois dans le même film"
  ],
  "score": 5,
  "lang": "fr"
}
```

---

### GET `/health` — Health check

```
GET http://mistralski-fine-tuned.wh26.edouard.cl:80/health
```

**Réponse 200** :
```json
{ "status": "ok" }
```

---

## Comportement selon le score

| Score  | Ton attendu |
|--------|-------------|
| 0–5    | Absurde total, style Le Gorafi / The Onion, bureaucratique et grotesque |
| 6–15   | Très drôle, twist inattendu, deadpan |
| 16–25  | Décalé, prémisse absurde traitée avec sérieux |
| 26–35  | Satirique, exagération comique |
| 36–69  | Clickbait, légèrement sensationnaliste |
| 70–100 | Factuel, journalistique |

---

## Erreurs

Format uniforme :
```json
{ "error": "<message descriptif>" }
```

| Code | Cause |
|------|-------|
| 400  | Body invalide (score hors 0–100, n hors 1–10, etc.) |
| 422  | Champs manquants ou types incorrects |
| 500  | Erreur interne serveur |

---

## Exemples cURL

```bash
# Titre absurde (score bas)
curl -X POST http://mistralski-fine-tuned.wh26.edouard.cl:80/generate \
  -H "Content-Type: application/json" \
  -d '{"score": 5, "lang": "fr", "n": 3}'

# Titre factuel (score élevé)
curl -X POST http://mistralski-fine-tuned.wh26.edouard.cl:80/generate \
  -H "Content-Type: application/json" \
  -d '{"score": 85, "lang": "en", "n": 1}'

# Health check
curl http://mistralski-fine-tuned.wh26.edouard.cl:80/health
```

---

## Documentation interactive

Swagger UI disponible sur :
`http://mistralski-fine-tuned.wh26.edouard.cl:80/docs`
