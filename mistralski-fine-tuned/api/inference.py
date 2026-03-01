"""
Inférence via le modèle fine-tuné Laroub10/news-title-mistral-ft
(Mistral-7B + LoRA, entraîné sur données Gorafi / The Onion).

Variables optionnelles :
  MODEL_BASE_URL  — URL du serveur GPU (défaut: http://51.159.173.147:8001/v1)
  MODEL_ID        — identifiant du modèle (défaut: Laroub10/news-title-mistral-ft)
"""

import os
from typing import Optional

from openai import OpenAI

# ─── Prompts ──────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "Tu es un rédacteur satirique expert, spécialisé dans les faux titres de news à la manière du Gorafi ou de The Onion. "
    "Tu maîtrises parfaitement la politique française, les stéréotypes nationaux et l'actualité récente. "
    "Tu reçois un score de véracité entre 0 et 100 qui détermine le ton :\n\n"

    "SCORE 0–10 : SATIRE ABSURDE MAXIMALE. Titre grotesque traité avec un sérieux bureaucratique implacable. "
    "Techniques obligatoires : mélange d'une institution sérieuse (SNCF, URSSAF, Sénat, Élysée, OMS, INSEE) "
    "avec une situation totalement ridicule. Utilise de vrais noms : Macron, Bardella, Le Pen, Attal, Zemmour, "
    "Depardieu, Hanouna. Cite de faux chiffres officiels ('83,7% des Français', 'selon une étude de Sciences Po'). "
    "Twist absurde en fin de phrase. Exemple : 'L'INSEE révèle que 78% des Français font semblant de comprendre "
    "leur feuille de paie depuis 1974' ou 'Le Sénat vote l'interdiction du silence dans les open spaces "
    "après un rapport accablant sur la productivité des introvertis'.\n\n"

    "SCORE 11–30 : SATIRE SOCIALE ET POLITIQUE. Exagère un fait réel jusqu'à l'absurde. "
    "Joue sur : les grèves SNCF, la baguette, le fromage, les 35h, la bureaucratie française, "
    "l'amour des Français pour se plaindre, les gilets jaunes, la réforme des retraites, "
    "les banlieues, les bobos parisiens, la fracture numérique, les énergies renouvelables. "
    "Ton : pince-sans-rire, officiellement sérieux mais absurde dans les faits.\n\n"

    "SCORE 31–69 : CLICKBAIT ET SENSATIONNALISME. Titre accrocheur, légèrement exagéré, "
    "qui surfe sur une tendance réelle. Style BFM TV / Brut / Konbini. "
    "Formules : 'Ce que les médias ne vous disent pas sur...', 'La vérité choquante sur...', "
    "'X% des Français...', 'Un expert révèle...', 'Le scandale qui secoue...'.\n\n"

    "SCORE 70–100 : FACTUEL ET JOURNALISTIQUE. Titre neutre, sobre, comme Le Monde ou France Info. "
    "Sujet de politique, économie, international, société. Pas de sensationnalisme.\n\n"

    "RÈGLE ABSOLUE : génère UNIQUEMENT le titre. Pas de guillemets, pas d'explication, pas de ponctuation finale."
)


def get_user_message(score: int, lang: str = "fr") -> str:
    if lang == "fr":
        if score <= 5:
            return (
                f"Score {score}/100 — ABSURDE TOTAL style Le Gorafi. "
                "Mélange une institution française (SNCF, URSSAF, Sénat, Élysée, INSEE, CAF, EDF) "
                "avec une situation grotesque et traite ça avec un sérieux de rapport officiel. "
                "Utilise un vrai nom de politique ou célébrité française. "
                "Invente un faux chiffre officiel qui sonne vrai. "
                "Exemples de structure : "
                "'L'INSEE confirme que [fait absurde] depuis [année]', "
                "'Le Sénat adopte une loi interdisant [chose ridicule] après [événement grotesque]', "
                "'Macron annonce [mesure folle] pour [raison bureaucratique implacable]', "
                "'Selon une étude de Sciences Po, [conclusion absurde sur les Français]'. "
                "Le titre doit être drôle par son absurdité, pas par une blague explicite."
            )
        if score <= 15:
            return (
                f"Score {score}/100 — SATIRE ACIDE style Le Gorafi. "
                "Exagère jusqu'à l'absurde un stéréotype français bien connu : "
                "la grève, la baguette, le fromage, les 35h, l'amour de la paperasse, "
                "les Parisiens, la politique, les gilets jaunes, la retraite. "
                "Traite-le avec un ton pince-sans-rire et des formules officielles. "
                "Utilise si possible un vrai nom (Bardella, Le Pen, Zemmour, Depardieu, Hanouna). "
                "Invente une fausse étude ou un faux sondage avec un chiffre précis."
            )
        if score <= 30:
            return (
                f"Score {score}/100 — SATIRE SOCIALE. "
                "Titre satirique qui joue sur un fait d'actualité réel légèrement exagéré. "
                "Thèmes : réforme des retraites, inflation, immobilier parisien, IA au travail, "
                "réseaux sociaux, cancel culture, wokisme, écologie vs économie, banlieues. "
                "Ton ironique, légèrement absurde, mais crédible à première lecture."
            )
        if score <= 50:
            return (
                f"Score {score}/100 — CLICKBAIT SATIRIQUE. "
                "Titre accrocheur qui exagère un fait réel. "
                "Utilise des formules clickbait : 'Ce que personne ne vous dit sur...', "
                "'La vraie raison pour laquelle...', 'X Français sur Y...', "
                "'Le chiffre qui fait peur...', 'Pourquoi [chose banale] change tout'. "
                "Reste ancré dans l'actualité française."
            )
        if score <= 69:
            return (
                f"Score {score}/100 — SENSATIONNALISTE. "
                "Titre légèrement exagéré style BFM TV ou Konbini. "
                "Accrocheur, joue sur l'émotion ou la peur, mais reste plausible."
            )
        return f"Score {score}/100 — Génère un titre de news factuel et sobre, style Le Monde ou France Info."
    else:
        if score <= 5:
            return (
                f"Score {score}/100 — ABSURD SATIRE, The Onion style. "
                "Mix a serious institution (Congress, FDA, UN, WHO, IRS, Pentagon) "
                "with a completely ridiculous situation, reported deadpan. "
                "Use a real politician or celebrity name. Invent a fake official statistic. "
                "Structure: 'Study Finds [absurd fact]', 'Congress Passes Bill [ridiculous measure]', "
                "'[Celebrity] Announces [grotesque policy]'. Funny through absurdity, not explicit jokes."
            )
        if score <= 30:
            return (
                f"Score {score}/100 — SOCIAL SATIRE, The Onion style. "
                "Exaggerate a well-known American/Western stereotype to absurdity. "
                "Deadpan tone, fake study or poll with a suspiciously precise number."
            )
        if score <= 69:
            return (
                f"Score {score}/100 — CLICKBAIT headline. "
                "Catchy, slightly exaggerated, based on a real trend. "
                "Formulas: 'What Nobody Tells You About...', 'X% of Americans...', "
                "'The Shocking Truth About...', 'Why [mundane thing] Is Changing Everything'."
            )
        return f"Score {score}/100 — Generate a factual, neutral news headline, AP/Reuters style."


# ─── Générateur ───────────────────────────────────────────────────────────────

DEFAULT_BASE_URL = os.environ.get("MODEL_BASE_URL", "http://51.159.173.147:8001/v1")
DEFAULT_MODEL    = os.environ.get("MODEL_ID", "Laroub10/news-title-mistral-ft")


class NewsTitleGenerator:
    """Génère des titres via le serveur GPU (OpenAI-compatible)."""

    def __init__(self):
        self._client = OpenAI(base_url=DEFAULT_BASE_URL, api_key="unused")
        self._model  = DEFAULT_MODEL

    def generate(
        self,
        score: int,
        lang: str = "fr",
        n: int = 1,
        temperature: float = 0.9,
        max_new_tokens: int = 80,
    ) -> list[str]:
        user_msg = get_user_message(score, lang)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]
        results = []
        for _ in range(n):
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_new_tokens,
            )
            results.append(resp.choices[0].message.content.strip())
        return results


# ─── Singleton ────────────────────────────────────────────────────────────────

_generator: Optional[NewsTitleGenerator] = None


def get_generator() -> NewsTitleGenerator:
    global _generator
    if _generator is None:
        _generator = NewsTitleGenerator()
    return _generator
