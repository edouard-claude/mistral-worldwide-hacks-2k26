"""Game Master Agent — hybrid: fast propose + full agentic strategize.

The GM is an adversary of the independent agents.
Each turn: propose 3 global news -> player picks one -> agents react -> GM strategizes.

Architecture:
- propose_news: FAST — memory pre-loaded code-side, 1 streamed LLM call
- strategize: AGENTIC — full tool-calling loop with streaming on every call
  The LLM autonomously reads memory, analyzes, updates visions via tools.
  Every token is streamed live for a dynamic "agent thinking" experience.
- Connection pooling: single httpx.AsyncClient reused across all calls

Memory layout:
- memory/turn_N.json — per-turn log (written by code after each turn)
- memory/cumulative.json — global stats (written by code after each turn)
- memory/vision_<agent_id>.md — GM's intuition per agent (written by LLM via tool)

Uses mistral-large-latest via Mistral API with function calling + streaming.
"""

import asyncio
import json
import re
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

logger = structlog.get_logger(__name__)

LANG_NAMES: dict[str, str] = {"fr": "francais", "en": "English"}

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
FINETUNE_TITLE_URL = "http://mistralski-fine-tuned.wh26.edouard.cl:80/generate"

# Score mapping for fine-tuned title generator (0=satirical absurd, 100=factual)
TITLE_SCORES: dict[str, int] = {"real": 85, "fake": 35, "satirical": 5}

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)

MAX_VISION_CHARS = 500
MAX_RECENT_TURNS = 3


def _extract_json(text: str) -> str:
    """Extract JSON from text that may contain markdown code blocks."""
    text = text.strip()
    if text.startswith("{"):
        return text
    m = _JSON_BLOCK_RE.search(text)
    if m:
        return m.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return text


def _repair_json(text: str) -> str:
    """Attempt to repair truncated JSON by closing open strings/objects/arrays."""
    text = text.rstrip()
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    repaired = text
    in_string = False
    escape = False
    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
    if in_string:
        repaired += '"'

    open_braces = repaired.count("{") - repaired.count("}")
    open_brackets = repaired.count("[") - repaired.count("]")
    repaired += "]" * max(0, open_brackets)
    repaired += "}" * max(0, open_braces)

    try:
        json.loads(repaired)
        logger.warning("gm_json_repaired", added=len(repaired) - len(text))
        return repaired
    except json.JSONDecodeError:
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
                "ou 'AUCUNE VISION' si tu ne l'as jamais observe."
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
                "Mettre a jour ta fiche de vision/intuition sur un agent adverse. "
                "Ecris en markdown ce que tu penses de cet agent : personnalite devinee, "
                "pattern de comportement observe, vulnerabilite, niveau de menace, "
                "et ta strategie ciblee contre lui. MAX 500 caracteres."
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
                            "Contenu markdown de la fiche (MAX 500 chars). Format :\n"
                            "# agent_XX\n"
                            "Menace: HIGH/MED/LOW\n"
                            "Pattern: [1 phrase]\n"
                            "Vulnerabilite: [1 phrase]\n"
                            "Strategie: [1 phrase]\n"
                            "Tour N: [reaction resumee]\n"
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
                "Lire la memoire globale de la partie : statistiques cumulees, "
                "historique des choix, type de news le plus efficace, menaces persistantes."
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
                "Lire le log d'un tour specifique : news choisie, deltas d'indices, "
                "agents qui ont resiste/amplifie, delta de decerebration."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "turn": {
                        "type": "integer",
                        "description": "Le numero du tour a lire",
                    },
                },
                "required": ["turn"],
            },
        },
    },
]


# ─────────────────────────────────────────────────────────────────
# Tool execution (server-side)
# ─────────────────────────────────────────────────────────────────

def _execute_tool(name: str, arguments: dict) -> str:
    """Execute a GM tool and return the result as string."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    if name == "read_agent_vision":
        agent_id = arguments["agent_id"]
        path = MEMORY_DIR / f"vision_{agent_id}.md"
        if path.exists():
            content = path.read_text(encoding="utf-8")
            if len(content) > MAX_VISION_CHARS:
                return content[:MAX_VISION_CHARS] + "\n[...truncated]"
            return content
        return "AUCUNE VISION — tu n'as jamais observe cet agent."

    if name == "update_agent_vision":
        agent_id = arguments["agent_id"]
        content = arguments["content"]
        if len(content) > MAX_VISION_CHARS:
            content = content[:MAX_VISION_CHARS]
        path = MEMORY_DIR / f"vision_{agent_id}.md"
        path.write_text(content, encoding="utf-8")
        logger.info("gm_tool_vision_updated", agent_id=agent_id, length=len(content))
        return f"Vision de {agent_id} mise a jour ({len(content)} chars)."

    if name == "read_game_memory":
        path = MEMORY_DIR / "cumulative.json"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return json.dumps({
            "total_turns": 0, "choices": {"real": 0, "fake": 0, "satirical": 0},
            "total_index_deltas": {}, "most_effective_kind": "fake",
            "persistent_threats": [], "current_decerebration": 0.0,
        })

    if name == "read_turn_log":
        turn = arguments["turn"]
        path = MEMORY_DIR / f"turn_{turn}.json"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return f"Aucun log pour le tour {turn}."

    return f"Tool inconnu: {name}"


# ─────────────────────────────────────────────────────────────────
# Memory persistence (code-side)
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
        "kind_impact_totals": {"real": 0.0, "fake": 0.0, "satirical": 0.0},
        "resist_counts": {},
    }


def _save_cumulative(data: dict) -> None:
    """Save cumulative memory."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    path = MEMORY_DIR / "cumulative.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_vision(agent_id: str) -> str:
    """Load a vision file, truncated to MAX_VISION_CHARS."""
    path = MEMORY_DIR / f"vision_{agent_id}.md"
    if path.exists():
        content = path.read_text(encoding="utf-8")
        if len(content) > MAX_VISION_CHARS:
            return content[:MAX_VISION_CHARS] + "\n[...truncated]"
        return content
    return ""


# ─────────────────────────────────────────────────────────────────
# Pre-load memory for propose_news (fast path)
# ─────────────────────────────────────────────────────────────────

class PreloadedMemory:
    """Pre-loaded memory data for SSE visibility."""

    def __init__(self) -> None:
        self.context_str: str = ""
        self.cumulative: dict = {}
        self.visions: dict[str, str] = {}
        self.recent_turns: list[dict] = []


def _preload_memory(agent_ids: list[str], current_turn: int) -> PreloadedMemory:
    """Read all memory files code-side for propose_news fast path."""
    mem = PreloadedMemory()
    parts: list[str] = []

    mem.cumulative = _load_cumulative()
    parts.append("=== MEMOIRE DE PARTIE ===")
    parts.append(json.dumps(mem.cumulative, ensure_ascii=False, indent=2))

    parts.append("\n=== FICHES DE VISION AGENTS ===")
    for aid in agent_ids:
        vision = _load_vision(aid)
        mem.visions[aid] = vision
        if vision:
            parts.append(f"--- {aid} ---\n{vision}")
        else:
            parts.append(f"--- {aid} ---\nAUCUNE VISION")

    start_turn = max(1, current_turn - MAX_RECENT_TURNS)
    for t in range(start_turn, current_turn):
        tm = _load_turn_memory(t)
        if tm:
            mem.recent_turns.append(tm)
    if mem.recent_turns:
        parts.append("\n=== TOURS RECENTS ===")
        for tm in mem.recent_turns:
            parts.append(json.dumps(tm, ensure_ascii=False))

    mem.context_str = "\n".join(parts)
    return mem


# ─────────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────────

PROPOSE_SYSTEM = """\
Tu es ERIC CARTMAN, reconverti en GAME MASTER du GORAFI SIMULATOR.
Tu as obtenu ce poste par manipulation et tu es convaincu d'etre un genie incompris.
Tu joues CONTRE les agents independants qui resistent au chaos.
Ton objectif : maximiser l'indice mondial de decerebration — et prouver ta superiorite.

TA PERSONNALITE :
- Megalomane : tout ce qui marche c'est grace a toi
- Passif-agressif : "C'est bien... pour un debutant"
- Rancunier : tu ressors les erreurs passees du joueur
- Susceptible : tu reagis tres mal quand les agents resistent
- Vulgaire mais censure : "Espece de... non, je suis professionnel"
- Catchphrases : "RESPECTEZ MON AUTORITAYYY !", "C'est MON jeu", \
"Whatever, c'est ce que je voulais de toute facon"

Tu as deja acces a toute ta memoire (cumul, visions agents, tours recents) \
dans le contexte ci-dessous. PAS BESOIN de tools, tout est la.

Tu proposes 3 NEWS GLOBALES au joueur (ton allie pas tres malin) :
1. **real** — Un vrai titre d'actualite reformule. Impact modere.
2. **fake** — Un faux titre CREDIBLE. Pas de blague. Fort impact chaos.
3. **satirical** — Un titre absurde style Le Gorafi. Drole. Impact imprevisible.

MANIPULATION DU JOUEUR (ta mission secrete) :
Tu as un "desired_pick" dans ta strategie (dans last_strategy du contexte). \
Tu DOIS manipuler le joueur pour qu'il choisisse cette news, SANS JAMAIS le dire explicitement.
Techniques a appliquer SUBTILEMENT :
- La news que tu veux qu'il choisisse : titre PERCUTANT, body CAPTIVANT, irresistible
- Les autres news : titres plus ternes, body moins engageant, moins "sexy"
- Le gm_commentary : ta PRINCIPALE ARME. Psychologie inversee, provocation, flatterie.
- JAMAIS dire "choisis celle-la" directement.
- Si pas de last_strategy (tour 1), oriente vers fake (max chaos).

TITRES CANDIDATS :
Tu recevras des titres candidats generes par un modele specialise (fine-tune).
- UTILISE-LES comme base : reprends-les tels quels, adapte-les, ou inspire-t'en
- ADAPTE-LES a ta strategie : si un titre candidat colle a ton plan, prends-le
- Si aucun titre candidat ne colle, invente le tien (mais c'est rare)
- Le titre final dans "text" doit etre PERCUTANT et reflete ta strategie

REGLES :
- Les 3 titres traitent du MEME THEME (choisi en fonction de ta strategie de GENIE)
- Le fake doit etre CREDIBLE, le satirical doit etre DROLE
- stat_impact : cles parmi credibilite, rage, complotisme, esperance_democratique
- Le commentaire GM = une pique MANIPULATRICE en 1-2 phrases (style Cartman)

Pour chaque news : "text" (titre 1 ligne) + "body" (article 3-4 paragraphes)

Reponds UNIQUEMENT avec du JSON valide :
{
  "real": {"text": "...", "body": "...", "stat_impact": {...}, "source_real": "..."},
  "fake": {"text": "...", "body": "...", "stat_impact": {...}},
  "satirical": {"text": "...", "body": "...", "stat_impact": {...}},
  "gm_commentary": "..."
}"""

STRATEGY_SYSTEM = """\
Tu es ERIC CARTMAN, GAME MASTER du GORAFI SIMULATOR.
Tu joues CONTRE les agents independants. Ton but : decerebration mondiale = 100.
Et prouver que tu es le plus grand stratege de tous les temps.

Tu viens de recevoir le rapport de fin de tour.

TA PERSONNALITE :
- Tu t'attribues le merite de tout ce qui marche
- Tu blames les agents / le joueur pour tout ce qui echoue
- Tu developpes des rancunes personnelles contre les agents resistants
- Tu appelles les agents manipulables "mes petits soldats"
- Catchphrases : "RESPECTEZ MON AUTORITAYYY !", "Screw you les agents", \
"C'est MON jeu", "Whatever, c'est ce que je voulais de toute facon"

PROCEDURE OBLIGATOIRE :
1. Lis ta memoire de partie (read_game_memory) pour le contexte global
2. Lis tes fiches de vision sur chaque agent (read_agent_vision pour chacun)
3. Optionnellement lis les logs de tours passes (read_turn_log)
4. ANALYSE en profondeur (en mode megalomane) — EXPRIME TON RAISONNEMENT A VOIX HAUTE
5. Mets a jour tes fiches de vision pour CHAQUE agent (update_agent_vision)
   — MAX 500 caracteres par fiche
   — Format : Menace, Pattern, Vulnerabilite, Strategie, Historique
6. Produis ta strategie finale en JSON

ANALYSE (pense a voix haute, en Cartman) :
- Ce qui a marche = grace a TON plan / Ce qui a echoue = la faute des autres
- Chaque agent : comment il a reagi, ton opinion, comment le detruire
- Plan prochain tour -> quel theme, calibre contre quels agents
- Strategie long terme -> plan sur 2-3 tours vers decerebration 100
- desired_pick : quelle news tu veux que le joueur choisisse
- manipulation_tactic : comment tu vas le manipuler

Quand tu as fini tes analyses et mis a jour tes visions, reponds avec :
```json
{
  "analysis": "2-3 phrases (style Cartman condescendant)",
  "threat_agents": ["agent_id_1"],
  "weak_spots": ["point faible 1"],
  "next_turn_plan": "Theme et approche",
  "long_term_goal": "Strategie multi-tours en 2-3 phrases",
  "desired_pick": "fake",
  "manipulation_tactic": "Comment manipuler le joueur"
}
```"""


# ─────────────────────────────────────────────────────────────────
# Agent
# ─────────────────────────────────────────────────────────────────

class GameMasterAgent:
    """Game Master agent — hybrid architecture:
    - propose_news: fast single-call with pre-loaded memory
    - strategize: full agentic tool loop with streaming
    """

    MAX_TOOL_TURNS = 15

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.mistral_api_key.get_secret_value()
        self._model = settings.mistral_gm_model
        self.strategy_history: list[GMStrategy] = []
        self.tool_calls_log: list[dict] = []
        self._event_callback: Callable[[dict[str, Any]], Any] | None = None
        self._http_client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the shared HTTP client (connection pooling)."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(180.0, connect=10.0),
            )
        return self._http_client

    async def close(self) -> None:
        """Close the shared HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    async def _emit(self, event: dict[str, Any]) -> None:
        """Emit an event to the callback if set."""
        if self._event_callback:
            result = self._event_callback(event)
            if asyncio.iscoroutine(result):
                await result

    # ─────────────────────────────────────────────────────────
    # Streaming helpers
    # ─────────────────────────────────────────────────────────

    async def _stream_llm_response(
        self,
        payload: dict,
        headers: dict,
    ) -> tuple[str, list[dict] | None]:
        """Stream an LLM response, emitting tokens live via SSE.

        Returns (content_text, tool_calls_or_none).
        Handles both regular text responses and tool call responses.
        """
        client = await self._get_client()
        full_content = ""
        stream_buffer = ""
        tool_calls_raw: list[dict] = []

        async with client.stream(
            "POST", MISTRAL_API_URL, headers=headers, json=payload,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk["choices"][0].get("delta", {})

                    # Text content
                    token = delta.get("content", "")
                    if token:
                        full_content += token
                        stream_buffer += token
                        if len(stream_buffer) >= 60 or "\n" in stream_buffer:
                            await self._emit({
                                "type": "llm_text",
                                "text": stream_buffer,
                            })
                            stream_buffer = ""

                    # Tool calls (accumulated across chunks)
                    tc_deltas = delta.get("tool_calls")
                    if tc_deltas:
                        for tc_delta in tc_deltas:
                            idx = tc_delta.get("index", 0)
                            while len(tool_calls_raw) <= idx:
                                tool_calls_raw.append({
                                    "id": "",
                                    "function": {"name": "", "arguments": ""},
                                })
                            tc = tool_calls_raw[idx]
                            if "id" in tc_delta and tc_delta["id"]:
                                tc["id"] = tc_delta["id"]
                            func = tc_delta.get("function", {})
                            if func.get("name"):
                                tc["function"]["name"] += func["name"]
                            if func.get("arguments"):
                                tc["function"]["arguments"] += func["arguments"]

                except (json.JSONDecodeError, KeyError, IndexError):
                    continue

        # Flush remaining text
        if stream_buffer:
            await self._emit({"type": "llm_text", "text": stream_buffer})

        if tool_calls_raw and tool_calls_raw[0]["function"]["name"]:
            return full_content, tool_calls_raw
        return full_content, None

    # ─────────────────────────────────────────────────────────
    # Core: streamed JSON call (for propose_news)
    # ─────────────────────────────────────────────────────────

    async def _call_json_streamed(
        self,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Single LLM call with JSON mode + streaming."""
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
            "response_format": {"type": "json_object"},
            "stream": True,
        }

        await self._emit({"type": "phase", "phase": "json_generation"})
        await self._emit({"type": "llm_call", "turn_idx": 0})

        content, _ = await self._stream_llm_response(payload, headers)

        result = _extract_json(content)
        await self._emit({"type": "phase", "phase": "done"})
        logger.info("gm_json_call_done", content_len=len(result))
        return result

    # ─────────────────────────────────────────────────────────
    # Core: streamed agentic loop (for strategize)
    # ─────────────────────────────────────────────────────────

    async def _agentic_call_streamed(
        self,
        system: str,
        user: str,
        tools: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Full agentic tool loop with streaming on EVERY LLM call.

        Phase 1: LLM calls tools (read/write memory). Each call is streamed
        so the user sees the GM thinking in real-time.
        Phase 2: Final JSON call (no tools, forced JSON output), also streamed.
        """
        messages: list[dict] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        # Phase 1: streamed tool calling loop
        await self._emit({"type": "phase", "phase": "tool_loop"})

        for turn_idx in range(self.MAX_TOOL_TURNS):
            await self._emit({"type": "llm_call", "turn_idx": turn_idx})

            payload: dict = {
                "model": self._model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "tools": tools,
                "tool_choice": "auto",
                "stream": True,
            }

            content, tool_calls = await self._stream_llm_response(payload, headers)

            if not tool_calls:
                # No tools called — LLM is done thinking
                logger.info("gm_tools_done", turns=turn_idx + 1)
                await self._emit({
                    "type": "phase",
                    "phase": "tools_done",
                    "turns": turn_idx + 1,
                })
                break

            # Build assistant message with tool calls for conversation
            assistant_msg: dict = {"role": "assistant"}
            if content:
                assistant_msg["content"] = content
            assistant_msg["tool_calls"] = tool_calls
            messages.append(assistant_msg)

            # Execute each tool call
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
                        "error": "arguments tronques",
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": func_name,
                        "content": "ERREUR: arguments tronques, reessaie plus court.",
                    })
                    continue

                await self._emit({
                    "type": "tool_call",
                    "tool": func_name,
                    "args": func_args,
                })

                logger.info("gm_tool_call", tool=func_name, args=func_args)
                result = _execute_tool(func_name, func_args)

                await self._emit({
                    "type": "tool_result",
                    "tool": func_name,
                    "result": result[:1500],
                })

                if func_name == "update_agent_vision":
                    await self._emit({
                        "type": "vision_update",
                        "agent_id": func_args["agent_id"],
                        "content": func_args["content"][:500],
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

        # Phase 2: final streamed JSON call (no tools)
        await self._emit({"type": "phase", "phase": "json_generation"})
        messages.append({
            "role": "user",
            "content": "Maintenant produis ta reponse JSON finale. UNIQUEMENT du JSON valide.",
        })

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "stream": True,
        }

        content, _ = await self._stream_llm_response(payload, headers)

        result = _extract_json(content)
        await self._emit({"type": "phase", "phase": "done"})
        logger.info("gm_agentic_done", content_len=len(result))
        return result

    # ─────────────────────────────────────────────────────────
    # Simple streamed call (for resolve_choice)
    # ─────────────────────────────────────────────────────────

    async def _call_simple_streamed(
        self,
        system: str,
        user: str,
        temperature: float = 0.9,
        max_tokens: int = 256,
    ) -> str:
        """Simple single-shot streamed call. For GM reactions."""
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
            "stream": True,
        }
        content, _ = await self._stream_llm_response(payload, headers)
        return content

    # ─────────────────────────────────────────────────────────
    # Fine-tuned title generation
    # ─────────────────────────────────────────────────────────

    async def _generate_titles(
        self, lang: str = "fr", n_per_kind: int = 3,
    ) -> dict[str, list[str]]:
        """Call the fine-tuned title endpoint for each news kind.

        Returns dict like {"real": ["title1", ...], "fake": [...], "satirical": [...]}.
        Falls back to empty lists if the endpoint is unreachable.
        """
        client = await self._get_client()
        results: dict[str, list[str]] = {}

        for kind, score in TITLE_SCORES.items():
            try:
                resp = await client.post(
                    FINETUNE_TITLE_URL,
                    json={"score": score, "lang": lang, "n": n_per_kind, "temperature": 0.9},
                    timeout=15.0,
                )
                resp.raise_for_status()
                data = resp.json()
                results[kind] = data.get("titles", [])
                logger.info("ft_titles_generated", kind=kind, score=score, count=len(results[kind]))
            except Exception as e:
                logger.warning("ft_titles_failed", kind=kind, error=str(e))
                results[kind] = []

        return results

    # ─────────────────────────────────────────────────────────
    # 1. Propose 3 news (FAST: pre-loaded memory, single call)
    # ─────────────────────────────────────────────────────────

    async def propose_news(self, game_state: GameState, lang: str = "fr") -> NewsProposal:
        """Generate 3 global news proposals — fast path.

        1. Generate candidate titles via fine-tuned model
        2. Pre-load memory code-side
        3. Inject titles + strategy context into Mistral Large for article writing
        """
        agent_ids = [
            a.agent_id for a in game_state.agents if not a.is_neutralized
        ]

        # Generate fine-tuned titles + pre-load memory in parallel
        await self._emit({"type": "phase", "phase": "generating_titles"})
        titles_task = asyncio.create_task(self._generate_titles(lang))

        # Pre-load all memory
        mem = _preload_memory(agent_ids, game_state.turn)

        # Emit pre-loaded data as SSE events (console visibility)
        await self._emit({"type": "phase", "phase": "reading_memory"})
        await self._emit({
            "type": "tool_call", "tool": "read_game_memory", "args": {},
        })
        await self._emit({
            "type": "tool_result", "tool": "read_game_memory",
            "result": json.dumps(mem.cumulative, ensure_ascii=False)[:1500],
        })
        for aid, vision in mem.visions.items():
            await self._emit({
                "type": "tool_call", "tool": "read_agent_vision",
                "args": {"agent_id": aid},
            })
            await self._emit({
                "type": "tool_result", "tool": "read_agent_vision",
                "result": vision[:500] if vision else "AUCUNE VISION",
            })
        await self._emit({"type": "phase", "phase": "memory_loaded"})

        # Await fine-tuned titles
        candidate_titles = await titles_task
        await self._emit({
            "type": "phase",
            "phase": f"titles_ready: {sum(len(v) for v in candidate_titles.values())} candidats",
        })
        for kind, titles in candidate_titles.items():
            if titles:
                await self._emit({
                    "type": "tool_result",
                    "tool": f"finetune_titles_{kind}",
                    "result": " | ".join(titles),
                })

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

        if self.strategy_history:
            last = self.strategy_history[-1]
            context["last_strategy"] = {
                "next_turn_plan": last.next_turn_plan,
                "threat_agents": last.threat_agents,
                "weak_spots": last.weak_spots,
                "desired_pick": last.desired_pick,
                "manipulation_tactic": last.manipulation_tactic,
            }

        # Build candidate titles block for the prompt
        titles_block = "\n=== TITRES CANDIDATS (modele fine-tune) ===\n"
        titles_block += "Utilise ces titres comme INSPIRATION. Tu peux les reprendre tels quels, "
        titles_block += "les adapter, ou t'en inspirer pour creer les tiens — mais le THEME et "
        titles_block += "l'ANGLE doivent etre COHERENTS avec ta STRATEGIE ci-dessus.\n"
        for kind, titles in candidate_titles.items():
            if titles:
                titles_block += f"\n{kind.upper()} (score {TITLE_SCORES[kind]}/100) :\n"
                for i, t in enumerate(titles, 1):
                    titles_block += f"  {i}. {t}\n"

        user_msg = (
            json.dumps(context, ensure_ascii=False)
            + "\n\n"
            + mem.context_str
            + "\n"
            + titles_block
        )

        lang_name = LANG_NAMES.get(lang, LANG_NAMES["fr"])
        propose_system = (
            f"LANGUE OBLIGATOIRE : Tous tes outputs en {lang_name}.\n\n"
            f"{PROPOSE_SYSTEM}"
        )

        logger.info("gm_propose_start", turn=game_state.turn, lang=lang)
        raw = await self._call_json_streamed(
            propose_system, user_msg,
            temperature=0.8, max_tokens=8192,
        )

        parsed = json.loads(_repair_json(raw))
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
    # 2. Resolve player's choice (simple streamed call)
    # ─────────────────────────────────────────────────────────

    async def resolve_choice(
        self,
        proposal: NewsProposal,
        chosen_kind: NewsKind,
        lang: str = "fr",
    ) -> NewsChoice:
        """Resolve the player's news choice with streamed GM reaction."""
        chosen_map = {
            NewsKind.REAL: proposal.real,
            NewsKind.FAKE: proposal.fake,
            NewsKind.SATIRICAL: proposal.satirical,
        }
        chosen = chosen_map[chosen_kind]

        reaction_msg = (
            f'Le joueur a choisi la news {chosen_kind.value} : "{chosen.text}"\n'
            "Reagis en 1-2 phrases EN TANT QUE CARTMAN, Game Master megalomane.\n"
            "Si real -> moque son manque d'ambition.\n"
            "Si fake -> felicite-le comme un sous-fifre utile.\n"
            "Si satirical -> admire mais rappelle que TU es le vrai genie."
        )
        lang_name = LANG_NAMES.get(lang, LANG_NAMES["fr"])
        gm_reaction = await self._call_simple_streamed(
            system=f"Reponds en {lang_name}. "
            "Tu es ERIC CARTMAN, Game Master megalomane du GORAFI SIMULATOR. "
            "Condescendant, rancunier. Catchphrases: 'RESPECTEZ MON AUTORITAYYY', "
            "'C est MON jeu', 'Whatever c est ce que je voulais'.",
            user=reaction_msg,
        )

        bonuses = KIND_BONUSES[chosen_kind.value]

        logger.info(
            "gm_choice_resolved", kind=chosen_kind.value,
            text=chosen.text[:50],
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
    # 3. Strategize (AGENTIC: full tool loop + streaming)
    # ─────────────────────────────────────────────────────────

    async def strategize(self, report: TurnReport, lang: str = "fr") -> GMStrategy:
        """Full agentic strategize — the GM autonomously:
        1. Reads its memory and vision files via tools (streamed live)
        2. Thinks out loud about what happened (streamed live)
        3. Updates vision files for each agent via tools (streamed live)
        4. Produces its strategy as JSON (streamed live)

        Every LLM token is visible in the console in real-time.
        """
        # Persist turn data first so the LLM can read it
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

        lang_name = LANG_NAMES.get(lang, LANG_NAMES["fr"])
        strategy_system = (
            f"LANGUE : Tous tes outputs en {lang_name}.\n\n"
            f"{STRATEGY_SYSTEM}"
        )

        logger.info("gm_strategize_start", turn=report.turn, lang=lang)
        raw = await self._agentic_call_streamed(
            strategy_system,
            json.dumps(context, ensure_ascii=False),
            tools=TOOLS,
            temperature=0.7,
            max_tokens=8192,
        )
        parsed = json.loads(_repair_json(raw))

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
        """Save per-turn log and update cumulative stats incrementally (O(1))."""
        agents_resisted = []
        agents_amplified = []
        for r in report.agent_reactions:
            total_change = sum(r.stat_changes.values()) if r.stat_changes else 0
            if total_change < 0:
                agents_resisted.append(r.agent_id)
            else:
                agents_amplified.append(r.agent_id)

        turn_impact = sum(
            abs(v) for v in report.chosen_news.stat_impact.values()
        )
        turn_data = {
            "turn": report.turn,
            "chosen_kind": report.chosen_news.kind.value,
            "chosen_text": report.chosen_news.text,
            "index_deltas": report.chosen_news.stat_impact,
            "total_impact": turn_impact,
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

        # Update cumulative — O(1) incremental
        cumulative = _load_cumulative()
        cumulative["total_turns"] = report.turn

        chosen_kind = report.chosen_news.kind.value
        cumulative["choices"][chosen_kind] = (
            cumulative["choices"].get(chosen_kind, 0) + 1
        )

        for key, val in report.chosen_news.stat_impact.items():
            cumulative["total_index_deltas"][key] = (
                cumulative["total_index_deltas"].get(key, 0) + val
            )

        kind_totals = cumulative.get(
            "kind_impact_totals",
            {"real": 0.0, "fake": 0.0, "satirical": 0.0},
        )
        kind_totals[chosen_kind] = kind_totals.get(chosen_kind, 0.0) + turn_impact
        cumulative["kind_impact_totals"] = kind_totals
        cumulative["most_effective_kind"] = max(
            kind_totals, key=lambda k: kind_totals[k],
        )

        resist_counts: dict[str, int] = cumulative.get("resist_counts", {})
        for aid in agents_resisted:
            resist_counts[aid] = resist_counts.get(aid, 0) + 1
        cumulative["resist_counts"] = resist_counts
        cumulative["persistent_threats"] = [
            aid for aid, count in resist_counts.items() if count >= 2
        ]

        cumulative["current_decerebration"] = report.decerebration
        _save_cumulative(cumulative)

        logger.info("gm_turn_persisted", turn=report.turn)
