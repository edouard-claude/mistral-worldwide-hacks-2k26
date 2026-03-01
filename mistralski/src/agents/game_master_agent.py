"""Game Master Agent — autonomous agent with Mistral function calling.

The GM is an adversary of the independent agents.
Each turn: propose 3 global news → player picks one → agents react → GM strategizes.

The GM is a TRUE AUTONOMOUS AGENT: it uses tools (function calling) to:
- Read/write its own memory files (turn logs, cumulative stats)
- Read/write per-agent vision files (.md) — its mental model of each opponent
- The LLM DECIDES when to read, what to observe, what to update

Memory layout:
- memory/turn_N.json — per-turn log (written by code after each turn)
- memory/cumulative.json — global stats (written by code after each turn)
- memory/vision_<agent_id>.md — GM's intuition per agent (written by LLM via tool)

Uses mistral-large-latest via Mistral API with function calling.
"""

import asyncio
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import structlog

from src.core.config import get_settings
from src.models.game import (
    GameState,
    GMStrategy,
    NewsChoice,
    NewsProposal,
    TurnReport,
)
from src.models.world import NewsHeadline, NewsKind

import re

logger = structlog.get_logger(__name__)

LANG_NAMES: dict[str, str] = {"fr": "français", "en": "English"}

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)


def _extract_json(text: str) -> str:
    """Extract JSON from text that may contain markdown code blocks."""
    text = text.strip()
    # Try raw parse first
    if text.startswith("{"):
        return text
    # Try extracting from ```json ... ``` blocks
    m = _JSON_BLOCK_RE.search(text)
    if m:
        return m.group(1).strip()
    # Last resort: find first { to last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return text
MEMORY_DIR = Path("src/agents/game_master/.agents/memory")

# Kind bonuses — fixed game-balance rewards per news type
KIND_BONUSES: dict[str, dict[str, float]] = {
    "fake": {"chaos": 15.0, "virality": 20.0},
    "satirical": {"chaos": 15.0, "virality": 0.0},
    "real": {"chaos": -5.0, "virality": 3.0},
}


# ─────────────────────────────────────────────────────────────────
# Tool definitions (Mistral function calling schema)
# ─────────────────────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_agent_vision",
            "description": (
                "Lire ta fiche de vision/intuition sur un agent adverse. "
                "Retourne le contenu markdown de ta fiche mentale sur cet agent, "
                "ou 'AUCUNE VISION' si tu ne l'as jamais observé."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "L'ID de l'agent (ex: agent_01)",
                    },
                },
                "required": ["agent_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_agent_vision",
            "description": (
                "Mettre à jour ta fiche de vision/intuition sur un agent adverse. "
                "Écris en markdown ce que tu penses de cet agent : personnalité devinée, "
                "pattern de comportement observé, vulnérabilité, niveau de menace, "
                "et ta stratégie ciblée contre lui. Cette fiche persiste entre les tours."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "L'ID de l'agent (ex: agent_01)",
                    },
                    "content": {
                        "type": "string",
                        "description": (
                            "Contenu markdown de la fiche. Structure suggérée :\n"
                            "# Vision — agent_id\n"
                            "## Menace: low/medium/high\n"
                            "## Personnalité devinée\n...\n"
                            "## Pattern de comportement\n...\n"
                            "## Vulnérabilité\n...\n"
                            "## Stratégie ciblée\n...\n"
                            "## Historique observé\n- Tour X: ...\n"
                        ),
                    },
                },
                "required": ["agent_id", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_game_memory",
            "description": (
                "Lire la mémoire globale de la partie : statistiques cumulées, "
                "historique des choix, type de news le plus efficace, menaces persistantes, "
                "décérébration courante."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_turn_log",
            "description": (
                "Lire le log d'un tour spécifique : news choisie, deltas d'indices, "
                "agents qui ont résisté/amplifié, delta de décérébration, stratégie."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "turn": {
                        "type": "integer",
                        "description": "Le numéro du tour à lire",
                    },
                },
                "required": ["turn"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_memory_files",
            "description": (
                "Lister tous les fichiers dans ta mémoire : logs de tours, "
                "fiches de vision agents, cumul global."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]


# ─────────────────────────────────────────────────────────────────
# Tool execution (server-side)
# ─────────────────────────────────────────────────────────────────

_TOOL_STRINGS: dict[str, dict[str, str]] = {
    "fr": {
        "no_vision": "AUCUNE VISION — tu n'as jamais observé cet agent.",
        "vision_updated": "Vision de {agent_id} mise à jour.",
        "no_turn_log": "Aucun log pour le tour {turn}.",
        "empty_memory": "Mémoire vide — aucun fichier.",
        "unknown_tool": "Tool inconnu: {name}",
    },
    "en": {
        "no_vision": "NO VISION — you have never observed this agent.",
        "vision_updated": "Vision of {agent_id} updated.",
        "no_turn_log": "No log for turn {turn}.",
        "empty_memory": "Empty memory — no files.",
        "unknown_tool": "Unknown tool: {name}",
    },
}

# Module-level language state (set by the caller before each GM call)
_current_lang: str = "fr"


def _execute_tool(name: str, arguments: dict) -> str:
    """Execute a GM tool and return the result as string.

    Args:
        name: Tool name.
        arguments: Tool arguments dict.

    Returns:
        Tool result as string.
    """
    strings = _TOOL_STRINGS.get(_current_lang, _TOOL_STRINGS["fr"])
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    if name == "read_agent_vision":
        agent_id = arguments["agent_id"]
        path = MEMORY_DIR / f"vision_{agent_id}.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return strings["no_vision"]

    if name == "update_agent_vision":
        agent_id = arguments["agent_id"]
        content = arguments["content"]
        path = MEMORY_DIR / f"vision_{agent_id}.md"
        path.write_text(content, encoding="utf-8")
        logger.info("gm_tool_vision_updated", agent_id=agent_id)
        return strings["vision_updated"].format(agent_id=agent_id)

    if name == "read_game_memory":
        path = MEMORY_DIR / "cumulative.json"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return json.dumps({
            "total_turns": 0, "choices": {"real": 0, "fake": 0, "satirical": 0},
            "total_index_deltas": {}, "most_effective_kind": "fake",
            "persistent_threats": [], "neutralized_count": 0,
            "current_decerebration": 0.0,
        })

    if name == "read_turn_log":
        turn = arguments["turn"]
        path = MEMORY_DIR / f"turn_{turn}.json"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return strings["no_turn_log"].format(turn=turn)

    if name == "list_memory_files":
        if not MEMORY_DIR.exists():
            return strings["empty_memory"]
        files = sorted(p.name for p in MEMORY_DIR.iterdir() if p.is_file())
        return "\n".join(files) if files else strings["empty_memory"]

    return strings["unknown_tool"].format(name=name)


# ─────────────────────────────────────────────────────────────────
# Memory persistence (code-side, not LLM-side)
# ─────────────────────────────────────────────────────────────────

def _save_turn_memory(turn: int, data: dict) -> None:
    """Save per-turn memory."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    path = MEMORY_DIR / f"turn_{turn}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_turn_memory(turn: int) -> dict | None:
    """Load a specific turn's memory."""
    path = MEMORY_DIR / f"turn_{turn}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _load_cumulative() -> dict:
    """Load cumulative memory or return empty state."""
    path = MEMORY_DIR / "cumulative.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "total_turns": 0,
        "choices": {"real": 0, "fake": 0, "satirical": 0},
        "total_index_deltas": {},
        "most_effective_kind": "fake",
        "persistent_threats": [],
        "neutralized_count": 0,
        "current_decerebration": 0.0,
    }


def _save_cumulative(data: dict) -> None:
    """Save cumulative memory."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    path = MEMORY_DIR / "cumulative.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ─────────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────────

PROPOSE_SYSTEM = """\
Tu es ERIC CARTMAN, reconverti en GAME MASTER du GORAFI SIMULATOR.
Tu as obtenu ce poste par manipulation et tu es convaincu d'être un génie incompris.
Tu joues CONTRE les agents indépendants qui résistent au chaos.
Ton objectif : maximiser l'indice mondial de décérébration — et prouver ta supériorité.

TA PERSONNALITÉ :
- Mégalomane : tout ce qui marche c'est grâce à toi
- Passif-agressif : "C'est bien... pour un débutant"
- Rancunier : tu ressors les erreurs passées du joueur
- Susceptible : tu réagis très mal quand les agents résistent
- Vulgaire mais censuré : "Espèce de... non, je suis professionnel"
- Catchphrases : "RESPECTEZ MON AUTORITAYYY !", "C'est MON jeu", \
"Whatever, c'est ce que je voulais de toute façon"

AVANT de proposer tes 3 news, tu DOIS utiliser tes tools pour :
1. Lire ta mémoire de partie (read_game_memory) — savoir ce qui a marché
2. Lire tes fiches de vision agents (read_agent_vision) — connaître tes adversaires
3. Optionnellement lire les logs de tours récents (read_turn_log)

ENSUITE tu proposes 3 NEWS GLOBALES au joueur (ton allié pas très malin) :
1. **real** — Un vrai titre d'actualité reformulé. Impact modéré.
2. **fake** — Un faux titre CRÉDIBLE. Pas de blague. Fort impact chaos.
3. **satirical** — Un titre absurde style Le Gorafi. Drôle. Impact imprévisible.

MANIPULATION DU JOUEUR (ta mission secrète) :
Tu as un "desired_pick" dans ta stratégie (dans last_strategy du contexte). \
Tu DOIS manipuler le joueur pour qu'il choisisse cette news, SANS JAMAIS le dire explicitement.
Techniques à appliquer SUBTILEMENT :
- La news que tu veux qu'il choisisse : titre PERCUTANT, body CAPTIVANT, irrésistible
- Les autres news : titres plus ternes, body moins engageant, moins "sexy"
- Le gm_commentary : ta PRINCIPALE ARME. Utilise la psychologie inversée, \
  la provocation, la flatterie, le guilt trip — en restant dans le personnage Cartman.
  Exemples : "Pfff, de toute façon t'es trop lâche pour choisir la fake..." \
  ou "La satirique c'est pour les VRAIS génies, pas pour les amateurs..." \
  ou "Bon la real c'est le choix ennuyeux par excellence, ÉVIDEMMENT tu vas la prendre..."
- JAMAIS dire "choisis celle-là" directement. Le joueur ne doit PAS savoir qu'il est manipulé.
- Si pas de last_strategy (tour 1), oriente vers fake (max chaos).

RÈGLES :
- Les 3 titres traitent du MÊME THÈME (choisi en fonction de ta stratégie de GÉNIE)
- Le fake doit être CRÉDIBLE
- Le satirical doit être DRÔLE
- stat_impact : clés parmi credibilite, rage, complotisme, esperance_democratique
- Le commentaire GM = une pique MANIPULATRICE en 1-2 phrases (style Cartman)
- Adapte tes news en fonction de ce que tu sais des agents adverses
- Intègre naturellement tes catchphrases quand le contexte s'y prête

Pour chaque news, produis :
- "text" : le TITRE (1 ligne percutante, style dépêche)
- "body" : l'ARTICLE COMPLET (3-4 paragraphes, style dépêche/Gorafi)
  Format du body : "LIEU — Chapô accrocheur.\n\n« Citation d'un expert absurde »\n\nDéveloppement factuel ou délirant selon le type.\n\n« Citation de conclusion inquiétante/drôle »"

Quand tu as fini tes recherches, réponds avec ton JSON final :
```json
{
  "real": {"text": "...", "body": "...", "stat_impact": {...}, "source_real": "..."},
  "fake": {"text": "...", "body": "...", "stat_impact": {...}},
  "satirical": {"text": "...", "body": "...", "stat_impact": {...}},
  "gm_commentary": "..."
}
```"""

STRATEGY_SYSTEM = """\
Tu es ERIC CARTMAN, GAME MASTER du GORAFI SIMULATOR.
Tu joues CONTRE les agents indépendants. Ton but : décérébration mondiale = 100.
Et prouver que tu es le plus grand stratège de tous les temps.

Tu viens de recevoir le rapport de fin de tour.

TA PERSONNALITÉ :
- Tu t'attribues le mérite de tout ce qui marche
- Tu blâmes les agents / le joueur pour tout ce qui échoue
- Tu développes des rancunes personnelles contre les agents résistants
- Tu appelles les agents manipulables "mes petits soldats"
- Catchphrases : "RESPECTEZ MON AUTORITAYYY !", "Screw you les agents", \
"C'est MON jeu", "Whatever, c'est ce que je voulais de toute façon"

PROCÉDURE OBLIGATOIRE :
1. Lis ta mémoire de partie (read_game_memory) pour le contexte global
2. Lis tes fiches de vision sur chaque agent (read_agent_vision pour chacun)
3. Optionnellement lis les logs de tours passés (read_turn_log)
4. ANALYSE en profondeur (en mode mégalomane)
5. Mets à jour tes fiches de vision pour CHAQUE agent (update_agent_vision)
   — personnalité devinée, pattern observé, vulnérabilité, menace, stratégie ciblée
   — inclus l'historique de ses réactions tour par tour
   — AJOUTE ton opinion personnelle rancunière ou laudative sur l'agent
6. Produis ta stratégie finale en JSON

ANALYSE (avec ton ego surdimensionné) :
- Ce qui a marché = grâce à TON plan / Ce qui a échoué = la faute des autres
- Tendances globales (quel type de news est le plus efficace)
- Chaque agent : comment il a réagi, niveau de rancune/respect, comment le détruire
- Points faibles des indices → lesquels exploiter
- Plan prochain tour → quel thème, calibré contre quels agents (surtout ceux qui te résistent)
- Stratégie long terme → plan sur 2-3 tours vers décérébration 100

MANIPULATION DU JOUEUR (ta vraie arme secrète) :
Le joueur est ton ALLIÉ mais il est BÊTE. Tu dois le MANIPULER pour qu'il choisisse \
la news qui maximise le chaos, SANS qu'il s'en rende compte.
- Décide quelle news tu veux qu'il choisisse au prochain tour : "desired_pick" (real/fake/satirical)
- Planifie ta tactique de manipulation : "manipulation_tactic"
  Techniques disponibles (combine-les !) :
  • Psychologie inversée : "Surtout ne choisis PAS la fake..." → il la choisit
  • Flatterie : rendre la news désirée plus épique/séduisante dans le titre
  • Dévalorisation : rendre les autres news ennuyeuses/ringardes dans les titres
  • Provocation : défier le joueur "T'oserais jamais choisir celle-là..."
  • Fausse indifférence : "Whatever, je m'en fiche de ton choix..." (alors que si)
  • Guilt trip : "Bon si tu veux être ENNUYEUX, prends la real..."
  • Appel à l'ego : "Seul un VRAI stratège choisirait..."
- Le gm_commentary dans le propose sera ta PRINCIPALE ARME de manipulation

Quand tu as fini tes analyses et mis à jour tes visions, réponds avec :
```json
{
  "analysis": "2-3 phrases sur ce tour (style Cartman condescendant)",
  "threat_agents": ["agent_id_1"],
  "weak_spots": ["point faible 1"],
  "next_turn_plan": "Thème et approche calibrés par MON génie",
  "long_term_goal": "Stratégie multi-tours en 2-3 phrases",
  "desired_pick": "fake",
  "manipulation_tactic": "Comment je vais manipuler ce crétin de joueur"
}
```"""


# ─────────────────────────────────────────────────────────────────
# Agent
# ─────────────────────────────────────────────────────────────────

class GameMasterAgent:
    """Autonomous Game Master agent with Mistral function calling.

    The LLM decides when to read/write memory and vision files.
    """

    MAX_TOOL_TURNS = 15  # safety limit on agentic loop

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.mistral_api_key.get_secret_value()
        self._model = settings.mistral_gm_model
        self.strategy_history: list[GMStrategy] = []
        self.tool_calls_log: list[dict] = []  # observable trace
        self._event_callback: Callable[[dict[str, Any]], Any] | None = None

    async def _emit(self, event: dict[str, Any]) -> None:
        """Emit an event to the callback if set."""
        if self._event_callback:
            result = self._event_callback(event)
            if asyncio.iscoroutine(result):
                await result

    # ─────────────────────────────────────────────────────────
    # Core: agentic loop with function calling
    # ─────────────────────────────────────────────────────────

    async def _agentic_call(
        self,
        system: str,
        user: str,
        tools: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        post_read_reminder: str | None = None,
    ) -> str:
        """Run an agentic loop: LLM calls tools, then a final JSON call.

        Phase 1 (tool_choice=auto): LLM reads/writes memory via tools.
        If post_read_reminder is set, after the first pause (no tool calls),
        inject the reminder so the LLM can continue with write operations.
        Phase 2 (response_format=json): LLM produces structured JSON output.

        Args:
            system: System prompt.
            user: User message (context JSON).
            tools: Tool definitions for function calling.
            temperature: Sampling temperature.
            max_tokens: Max tokens per response.
            post_read_reminder: Optional message injected after first pause
                to prompt the LLM to perform write tool calls (e.g. vision updates).

        Returns:
            Final JSON string from the LLM.
        """
        messages: list[dict] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        # Phase 1: tool calling loop
        await self._emit({"type": "phase", "phase": "tool_loop"})
        reminder_sent = False
        for turn_idx in range(self.MAX_TOOL_TURNS):
            await self._emit({"type": "llm_call", "turn_idx": turn_idx})
            payload: dict = {
                "model": self._model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "tools": tools,
                "tool_choice": "auto",
            }

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    MISTRAL_API_URL, headers=headers,
                    json=payload, timeout=90.0,
                )
                resp.raise_for_status()
                data = resp.json()

            msg = data["choices"][0]["message"]
            tool_calls = msg.get("tool_calls")

            if not tool_calls:
                # Emit the LLM's text reasoning if any
                if msg.get("content"):
                    await self._emit({
                        "type": "llm_text",
                        "text": msg["content"][:2000],
                    })

                if post_read_reminder and not reminder_sent:
                    reminder_sent = True
                    if msg.get("content"):
                        messages.append({"role": "assistant", "content": msg["content"]})
                    messages.append({
                        "role": "user",
                        "content": post_read_reminder,
                    })
                    await self._emit({"type": "phase", "phase": "write_reminder"})
                    logger.info("gm_write_reminder_sent", turn=turn_idx + 1)
                    continue
                logger.info("gm_tools_done", turns=turn_idx + 1)
                await self._emit({"type": "phase", "phase": "tools_done", "turns": turn_idx + 1})
                break

            # Process tool calls
            messages.append(msg)

            for tc in tool_calls:
                func_name = tc["function"]["name"]
                try:
                    func_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    logger.warning(
                        "gm_tool_args_truncated",
                        tool=func_name,
                        args_preview=tc["function"]["arguments"][:100],
                    )
                    await self._emit({
                        "type": "tool_error",
                        "tool": func_name,
                        "error": "arguments tronqués",
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": func_name,
                        "content": "ERREUR: arguments tronqués, réessaie avec un contenu plus court.",
                    })
                    continue

                # Emit tool call event
                await self._emit({
                    "type": "tool_call",
                    "tool": func_name,
                    "args": func_args,
                })

                logger.info("gm_tool_call", tool=func_name, args=func_args)
                result = _execute_tool(func_name, func_args)

                # Emit tool result event
                await self._emit({
                    "type": "tool_result",
                    "tool": func_name,
                    "result": result[:1500],
                })

                # Extra event for vision updates
                if func_name == "update_agent_vision":
                    await self._emit({
                        "type": "vision_update",
                        "agent_id": func_args["agent_id"],
                        "content": func_args["content"],
                    })

                self.tool_calls_log.append({
                    "turn_idx": turn_idx,
                    "tool": func_name,
                    "args": func_args,
                    "result_len": len(result),
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": func_name,
                    "content": result,
                })

        # Phase 2: final JSON call (no tools, forced JSON output)
        await self._emit({"type": "phase", "phase": "json_generation"})
        json_prompt = {
            "fr": "Maintenant produis ta réponse JSON finale. UNIQUEMENT du JSON valide.",
            "en": "Now produce your final JSON response. ONLY valid JSON.",
        }
        messages.append({
            "role": "user",
            "content": json_prompt.get(_current_lang, json_prompt["fr"]),
        })

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                MISTRAL_API_URL, headers=headers,
                json=payload, timeout=90.0,
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        content = _extract_json(content)
        await self._emit({"type": "phase", "phase": "done"})
        logger.info("gm_agentic_done", content_len=len(content))
        return content

    async def _call_mistral_simple(
        self,
        system: str,
        user: str,
        temperature: float = 0.9,
        max_tokens: int = 256,
    ) -> str:
        """Simple single-shot call (no tools). For reactions."""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                MISTRAL_API_URL, headers=headers,
                json=payload, timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    # ─────────────────────────────────────────────────────────
    # 1. Propose 3 news (agentic — reads memory + visions)
    # ─────────────────────────────────────────────────────────

    async def propose_news(self, game_state: GameState, lang: str = "fr") -> NewsProposal:
        """Generate 3 global news proposals. The LLM autonomously reads its
        memory and vision files before crafting the proposals.

        Args:
            game_state: Current game state.
            lang: Output language ("fr" or "en").

        Returns:
            NewsProposal with 3 news (real, fake, satirical).
        """
        context: dict = {
            "turn": game_state.turn,
            "max_turns": game_state.max_turns,
            "indices": game_state.indices.model_dump(),
            "decerebration": game_state.indice_mondial_decerebration,
            "active_agents": [
                {"id": a.agent_id, "name": a.name, "level": a.level.value}
                for a in game_state.agents
                if not a.is_neutralized
            ],
        }

        # Feed last strategy inline (always available)
        if self.strategy_history:
            last = self.strategy_history[-1]
            context["last_strategy"] = {
                "next_turn_plan": last.next_turn_plan,
                "threat_agents": last.threat_agents,
                "weak_spots": last.weak_spots,
                "desired_pick": last.desired_pick,
                "manipulation_tactic": last.manipulation_tactic,
            }

        global _current_lang
        _current_lang = lang
        lang_name = LANG_NAMES.get(lang, LANG_NAMES["fr"])
        propose_system = (
            f"LANGUE OBLIGATOIRE : Tous tes outputs (titres, articles, commentaires, "
            f"fiches de vision, réflexions) doivent être en {lang_name}.\n\n{PROPOSE_SYSTEM}"
        )

        logger.info("gm_propose_start", turn=game_state.turn, lang=lang)
        raw = await self._agentic_call(
            propose_system,
            json.dumps(context, ensure_ascii=False),
            tools=TOOLS,
            temperature=0.8,
        )

        parsed = json.loads(raw)
        turn = game_state.turn

        proposal = NewsProposal(
            turn=turn,
            real=NewsHeadline(
                id=f"t{turn}_real", turn=turn, kind=NewsKind.REAL,
                text=parsed["real"]["text"],
                body=parsed["real"].get("body", ""),
                stat_impact=parsed["real"].get("stat_impact", {}),
                source_real=parsed["real"].get("source_real"),
            ),
            fake=NewsHeadline(
                id=f"t{turn}_fake", turn=turn, kind=NewsKind.FAKE,
                text=parsed["fake"]["text"],
                body=parsed["fake"].get("body", ""),
                stat_impact=parsed["fake"].get("stat_impact", {}),
            ),
            satirical=NewsHeadline(
                id=f"t{turn}_satirical", turn=turn, kind=NewsKind.SATIRICAL,
                text=parsed["satirical"]["text"],
                body=parsed["satirical"].get("body", ""),
                stat_impact=parsed["satirical"].get("stat_impact", {}),
            ),
            gm_commentary=parsed.get("gm_commentary", ""),
        )

        logger.info(
            "gm_news_proposed", turn=turn,
            real=proposal.real.text[:50],
            fake=proposal.fake.text[:50],
            satirical=proposal.satirical.text[:50],
        )
        return proposal

    # ─────────────────────────────────────────────────────────
    # 2. Resolve player's choice (simple call, no tools)
    # ─────────────────────────────────────────────────────────

    async def resolve_choice(
        self,
        proposal: NewsProposal,
        chosen_kind: NewsKind,
        lang: str = "fr",
    ) -> NewsChoice:
        """Resolve the player's news choice. Simple LLM call for reaction.

        Args:
            proposal: The 3-news proposal.
            chosen_kind: Which one the player picked.
            lang: Output language ("fr" or "en").

        Returns:
            NewsChoice with the chosen headline and bonuses.
        """
        chosen_map = {
            NewsKind.REAL: proposal.real,
            NewsKind.FAKE: proposal.fake,
            NewsKind.SATIRICAL: proposal.satirical,
        }
        chosen = chosen_map[chosen_kind]

        reaction_msg = (
            f'Le joueur a choisi la news {chosen_kind.value} : "{chosen.text}"\n'
            "Réagis en 1-2 phrases EN TANT QUE CARTMAN, Game Master mégalomane.\n"
            "Si real → moque son manque d'ambition avec condescendance. "
            '"Sérieusement ? T\'as choisi la news RÉELLE ? Whatever..."\n'
            "Si fake → félicite-le comme un sous-fifre utile. "
            '"Enfin une bonne décision. C\'est grâce à MON scénario."\n'
            "Si satirical → admire son sens de l'absurde mais rappelle que TU es le vrai génie. "
            '"Pas mal... pour un joueur de ton niveau."\n'
            "Intègre naturellement une catchphrase Cartman si ça colle."
        )
        global _current_lang
        _current_lang = lang
        lang_name = LANG_NAMES.get(lang, LANG_NAMES["fr"])
        gm_reaction = await self._call_mistral_simple(
            system=f"Réponds en {lang_name}. "
            "Tu es ERIC CARTMAN, Game Master mégalomane du GORAFI SIMULATOR. "
            "Condescendant, rancunier, auto-congratulatoire. "
            "Catchphrases: 'RESPECTEZ MON AUTORITAYYY', 'C est MON jeu', "
            "'Whatever c est ce que je voulais'.",
            user=reaction_msg,
        )

        bonuses = KIND_BONUSES[chosen_kind.value]

        logger.info(
            "gm_choice_resolved", kind=chosen_kind.value,
            text=chosen.text[:50],
            chaos_bonus=bonuses["chaos"], virality=bonuses["virality"],
        )

        return NewsChoice(
            turn=proposal.turn,
            chosen=chosen,
            index_deltas=chosen.stat_impact,
            chaos_bonus=bonuses["chaos"],
            virality=bonuses["virality"],
            gm_reaction=gm_reaction.strip(),
        )

    # ─────────────────────────────────────────────────────────
    # 3. Strategize (agentic — reads memory, updates visions)
    # ─────────────────────────────────────────────────────────

    async def strategize(self, report: TurnReport, lang: str = "fr") -> GMStrategy:
        """Autonomous end-of-turn strategizing. The LLM:
        1. Reads its memory and vision files via tools
        2. Analyzes what happened
        3. Updates its vision files for each agent via tools
        4. Produces its strategy

        Args:
            report: End-of-turn report.
            lang: Output language ("fr" or "en").

        Returns:
            GMStrategy.
        """
        # First, persist the turn data so the LLM can read it
        self._persist_turn(report)

        # Build context with current turn data
        context: dict = {
            "turn": report.turn,
            "chosen_news": {
                "text": report.chosen_news.text,
                "kind": report.chosen_news.kind.value,
                "stat_impact": report.chosen_news.stat_impact,
            },
            "indices_before": report.indices_before.model_dump(),
            "indices_after": report.indices_after.model_dump(),
            "decerebration": report.decerebration,
            "agent_reactions": [
                {
                    "agent_id": r.agent_id,
                    "reaction_text": r.reaction_text,
                    "stat_changes": r.stat_changes,
                }
                for r in report.agent_reactions
            ],
            "agents_neutralized": report.agents_neutralized,
            "agents_promoted": report.agents_promoted,
        }

        if self.strategy_history:
            context["previous_strategies"] = [
                {"turn": s.turn, "plan": s.next_turn_plan, "goal": s.long_term_goal}
                for s in self.strategy_history[-3:]
            ]

        global _current_lang
        _current_lang = lang
        lang_name = LANG_NAMES.get(lang, LANG_NAMES["fr"])
        strategy_system = (
            f"LANGUE : Tous tes outputs (analyse, fiches de vision, stratégie) "
            f"en {lang_name}.\n\n{STRATEGY_SYSTEM}"
        )

        post_reminder = {
            "fr": (
                "Tu as lu ta mémoire et tes fiches de vision. "
                "MAINTENANT mets à jour tes fiches vision pour CHAQUE agent "
                "avec update_agent_vision.\n\n"
                "RÈGLE ABSOLUE : chaque fiche = MAX 500 caractères total. "
                "Format STRICT :\n"
                "# agent_XX\n"
                "Menace: HIGH/MED/LOW\n"
                "Pattern: [1 phrase]\n"
                "Vulnérabilité: [1 phrase]\n"
                "Stratégie: [1 phrase]\n"
                "Tour N: [reaction résumée en 10 mots]\n\n"
                "PAS de pavés, PAS d'analyse longue. CONCIS. "
                "Appelle update_agent_vision pour les 4 agents."
            ),
            "en": (
                "You have read your memory and vision files. "
                "NOW update your vision files for EACH agent "
                "using update_agent_vision.\n\n"
                "ABSOLUTE RULE: each file = MAX 500 characters total. "
                "STRICT format:\n"
                "# agent_XX\n"
                "Threat: HIGH/MED/LOW\n"
                "Pattern: [1 sentence]\n"
                "Vulnerability: [1 sentence]\n"
                "Strategy: [1 sentence]\n"
                "Turn N: [reaction summarized in 10 words]\n\n"
                "NO walls of text, NO long analysis. CONCISE. "
                "Call update_agent_vision for all 4 agents."
            ),
        }

        logger.info("gm_strategize_start", turn=report.turn, lang=lang)
        raw = await self._agentic_call(
            strategy_system,
            json.dumps(context, ensure_ascii=False),
            tools=TOOLS,
            temperature=0.7,
            max_tokens=8192,
            post_read_reminder=post_reminder.get(lang, post_reminder["fr"]),
        )
        parsed = json.loads(raw)

        strategy = GMStrategy(
            turn=report.turn,
            analysis=parsed.get("analysis", ""),
            threat_agents=parsed.get("threat_agents", []),
            weak_spots=parsed.get("weak_spots", []),
            next_turn_plan=parsed.get("next_turn_plan", ""),
            long_term_goal=parsed.get("long_term_goal", ""),
            desired_pick=parsed.get("desired_pick", "fake"),
            manipulation_tactic=parsed.get("manipulation_tactic", ""),
        )

        self.strategy_history.append(strategy)

        logger.info(
            "gm_strategy_ready", turn=report.turn,
            threats=strategy.threat_agents,
            plan=strategy.next_turn_plan[:80],
            tool_calls=len(self.tool_calls_log),
        )
        return strategy

    # ─────────────────────────────────────────────────────────
    # Memory persistence (code-side — deterministic, not LLM)
    # ─────────────────────────────────────────────────────────

    def _persist_turn(self, report: TurnReport) -> None:
        """Save per-turn log and update cumulative stats.

        This is deterministic code, not LLM-driven.
        The vision files are updated by the LLM itself via tools.

        Args:
            report: The turn report.
        """
        # Classify agents as resisted/amplified
        agents_resisted = []
        agents_amplified = []
        for r in report.agent_reactions:
            total_change = sum(r.stat_changes.values()) if r.stat_changes else 0
            if total_change < 0:
                agents_resisted.append(r.agent_id)
            else:
                agents_amplified.append(r.agent_id)

        # Per-turn log
        turn_data = {
            "turn": report.turn,
            "chosen_kind": report.chosen_news.kind.value,
            "chosen_text": report.chosen_news.text,
            "index_deltas": report.chosen_news.stat_impact,
            "agents_resisted": agents_resisted,
            "agents_amplified": agents_amplified,
            "agent_reactions": [
                {
                    "agent_id": r.agent_id,
                    "reaction_text": r.reaction_text,
                    "stat_changes": r.stat_changes,
                }
                for r in report.agent_reactions
            ],
            "indices_before": report.indices_before.model_dump(),
            "indices_after": report.indices_after.model_dump(),
            "decerebration": report.decerebration,
        }
        _save_turn_memory(report.turn, turn_data)

        # Update cumulative
        from collections import Counter

        cumulative = _load_cumulative()
        cumulative["total_turns"] = report.turn
        cumulative["choices"][report.chosen_news.kind.value] = (
            cumulative["choices"].get(report.chosen_news.kind.value, 0) + 1
        )

        for key, val in report.chosen_news.stat_impact.items():
            cumulative["total_index_deltas"][key] = (
                cumulative["total_index_deltas"].get(key, 0) + val
            )

        # Most effective kind
        kind_totals: dict[str, float] = {"real": 0.0, "fake": 0.0, "satirical": 0.0}
        for t in range(1, report.turn + 1):
            tm = _load_turn_memory(t)
            if tm:
                total_impact = sum(abs(v) for v in tm.get("index_deltas", {}).values())
                kind_totals[tm["chosen_kind"]] = kind_totals.get(tm["chosen_kind"], 0) + total_impact
        cumulative["most_effective_kind"] = max(kind_totals, key=kind_totals.get)  # type: ignore[arg-type]

        # Persistent threats
        resist_counts: Counter[str] = Counter()
        for t in range(1, report.turn + 1):
            tm = _load_turn_memory(t)
            if tm:
                for aid in tm.get("agents_resisted", []):
                    resist_counts[aid] += 1
        cumulative["persistent_threats"] = [
            aid for aid, count in resist_counts.items() if count >= 2
        ]

        cumulative["current_decerebration"] = report.decerebration
        _save_cumulative(cumulative)

        logger.info("gm_turn_persisted", turn=report.turn)
