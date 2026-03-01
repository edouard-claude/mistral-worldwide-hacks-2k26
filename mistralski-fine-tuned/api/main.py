"""
API News Title Generator — déployable sur CapRover.

Endpoints:
  POST /generate  — génère des titres (score 0–100)
  GET  /health    — health check pour CapRover
  GET  /          — interface web
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .inference import get_generator

STATIC_DIR = Path(__file__).parent / "static"


def error_response(status_code: int, message: str) -> JSONResponse:
    """Format uniforme des erreurs (contrat API)."""
    return JSONResponse(status_code=status_code, content={"error": message})


# ─── Lifespan : chargement du modèle au démarrage ──────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Démarrage rapide — le modèle se charge à la 1ère requête /generate."""
    yield


# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="News Title Generator API",
    description="Génère des titres de news selon un score de véracité (0–100). Plus le score est bas, plus c'est satirique.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return error_response(400, "Body invalide ou paramètres mal formés")


# ─── Schemas ──────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    score: int = Field(..., ge=0, le=100, description="Score de véracité 0–100")
    lang: str = Field(default="fr", description="Langue: fr ou en")
    n: int = Field(default=1, ge=1, le=10, description="Nombre de titres à générer")
    temperature: float = Field(default=0.9, ge=0.1, le=2.0, description="Température de génération")


class GenerateResponse(BaseModel):
    titles: list[str]
    score: int
    lang: str


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check pour CapRover / load balancers."""
    return {"status": "ok"}


@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    """Génère des titres de news selon le score de véracité."""
    try:
        gen = get_generator()
        titles = gen.generate(
            score=req.score,
            lang=req.lang,
            n=req.n,
            temperature=req.temperature,
        )
        return GenerateResponse(titles=titles, score=req.score, lang=req.lang)
    except Exception as e:
        return error_response(500, str(e))


@app.get("/")
async def root():
    """Interface web ou doc."""
    index = STATIC_DIR / "index.html"
    if index.exists():
        from fastapi.responses import FileResponse
        return FileResponse(index)
    return {"message": "News Title Generator API", "docs": "/docs"}


# Fichiers statiques (CSS, etc.) si besoin
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(__import__("os").environ.get("PORT", 80))
    uvicorn.run(app, host="0.0.0.0", port=port)
