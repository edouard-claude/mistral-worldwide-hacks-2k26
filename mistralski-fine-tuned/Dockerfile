# syntax=docker/dockerfile:1.4
# News Title API — image légère (~300 MB), aucun modèle local
# Appelle un serveur vLLM OpenAI-compatible pour l'inférence
#
# Variables d'env requises (CapRover → App Config → Environment Variables) :
#   MODEL_BASE_URL  — URL du serveur vLLM (ex: http://51.159.173.147:8001/v1)
#   MODEL_ID        — Identifiant du modèle (ex: Laroub10/news-title-mistral-ft)
#
# Build : docker build -t news-title-api .

FROM python:3.11-slim

WORKDIR /app

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/

ENV PORT=80
EXPOSE 80

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-80}"]
