"""Web interface to test the Game Master agent — with live streaming.

The central element is the STREAMING CONSOLE showing the GM's
reasoning process: tool calls, vision updates, and thinking in real-time.

Run: cd game-of-claw && python3 scripts/play_web.py
Open: http://localhost:8899
"""

import asyncio
import json
import os
import random
import shutil
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import websockets

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
import uvicorn

from src.agents.game_master_agent import MEMORY_DIR, GameMasterAgent, KIND_BONUSES
from src.models.agent import AgentLevel, AgentReaction, AgentState, AgentStats
from src.models.game import GameState, TurnReport
from src.models.world import GlobalIndices, NewsKind

# ── wh26 backend state ───────────────────────────────────────────

WH26_BASE_URL = "http://wh26-backend.wh26.edouard.cl"
WH26_WS_URL = "ws://wh26-backend.wh26.edouard.cl"

arena_session_id: str = str(uuid.uuid4())
wh26_ws: websockets.ClientConnection | None = None
wh26_ws_queue: asyncio.Queue = asyncio.Queue()
wh26_connected: bool = False

# ── Language & Image generation state ────────────────────────────
game_lang: str = "fr"
MISTRAL_IMG_AGENT_ID: str | None = None
IMAGES_DIR = Path("/tmp/gorafi_images")

BRANDING_PROMPT = (
    "Vintage Cold War Soviet propaganda poster, {subject}. "
    "Satirical socialist realism, highly symmetrical and monumental composition. "
    "Retro lithograph texture, bold ink outlines, flat graphic vector style. "
    "Strictly limited color palette using only aged parchment tan, deep black, "
    "and stark socialist red. Humorous dystopia aesthetic, distressed paper."
)


async def _wh26_ws_reader(ws: websockets.ClientConnection) -> None:
    """Background task: read WS messages from wh26 and put them in the queue."""
    try:
        async for raw in ws:
            try:
                data = json.loads(raw)
                await wh26_ws_queue.put(data)
            except json.JSONDecodeError:
                print(f"[WH26] WS non-JSON message: {str(raw)[:100]}")
    except websockets.ConnectionClosed:
        print("[WH26] WS connection closed")
    except Exception as e:
        print(f"[WH26] WS reader error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to wh26 backend on startup: POST /init_session + open WS."""
    global wh26_ws, wh26_connected
    ws_task = None
    try:
        # 1. Initialize session via HTTP
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{WH26_BASE_URL}/init_session",
                json={"session_id": arena_session_id},
                timeout=10.0,
            )
            resp.raise_for_status()
            print(f"[WH26] Session initialized: {arena_session_id}")

        # 2. Open WebSocket
        wh26_ws = await websockets.connect(f"{WH26_WS_URL}/ws/{arena_session_id}")
        wh26_connected = True
        ws_task = asyncio.create_task(_wh26_ws_reader(wh26_ws))
        print(f"[WH26] WebSocket connected: /ws/{arena_session_id}")
    except Exception as e:
        print(f"[WH26] Connection failed ({e}) — running without arena")
        wh26_ws = None
        wh26_connected = False

    # Create Mistral image generation agent
    global MISTRAL_IMG_AGENT_ID
    try:
        api_key = os.environ.get("MISTRAL_API_KEY", "")
        if not api_key:
            from src.core.config import get_settings
            api_key = get_settings().mistral_api_key.get_secret_value()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.mistral.ai/v1/agents",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "mistral-medium-2505",
                    "name": "propaganda-poster",
                    "tools": [{"type": "image_generation"}],
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            MISTRAL_IMG_AGENT_ID = resp.json()["id"]
            print(f"[IMG] Mistral image agent created: {MISTRAL_IMG_AGENT_ID}")
    except Exception as e:
        print(f"[IMG] Failed to create image agent ({e}) — images disabled")
        MISTRAL_IMG_AGENT_ID = None

    yield
    if wh26_ws:
        await wh26_ws.close()
        print("[WH26] WebSocket closed")
    if ws_task:
        ws_task.cancel()


# ── App state ────────────────────────────────────────────────────

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
gm: GameMasterAgent | None = None
game_state: GameState | None = None
current_proposal = None
last_choice = None
last_strategy = None
manipulation_history: list[dict] = []

AGENTS_INIT = [
    AgentState(
        agent_id="agent_01", name="Jean-Michel Vérity",
        personality="Fact-checker obsessionnel, vérifie tout 3 fois",
        country="FR",
        stats=AgentStats(croyance=25.0, confiance=85.0, richesse=40.0),
        level=AgentLevel.ACTIF,
    ),
    AgentState(
        agent_id="agent_02", name="Karen Q-Anon",
        personality="Conspirationniste repentie (ou pas)",
        country="US",
        stats=AgentStats(croyance=70.0, confiance=30.0, richesse=60.0),
        level=AgentLevel.PASSIF,
    ),
    AgentState(
        agent_id="agent_03", name="Aisha Al-Rashid",
        personality="Journaliste engagée, publie des fact-checks",
        country="EG",
        stats=AgentStats(croyance=20.0, confiance=90.0, richesse=25.0),
        level=AgentLevel.LEADER,
    ),
    AgentState(
        agent_id="agent_04", name="Boris Troll",
        personality="Troll professionnel, amplifie tout ce qui buzze",
        country="RU",
        stats=AgentStats(croyance=80.0, confiance=15.0, richesse=75.0),
        level=AgentLevel.ACTIF,
    ),
]

AGENT_NAMES = {a.agent_id: a.name for a in AGENTS_INIT}
AGENT_ICONS = {"agent_01": "🔍", "agent_02": "🐐", "agent_03": "📰", "agent_04": "🧨"}
AGENT_COLORS = {"agent_01": "#00ff41", "agent_02": "#ffb300", "agent_03": "#00bfff", "agent_04": "#ff003c"}

PLACEHOLDER_REACTIONS: dict[str, dict[str, list[str]]] = {
    "agent_01": {
        "real": ["Bon, au moins c'est vrai. Je vérifie quand même."],
        "fake": ["FAUX. Mes 14 sources le confirment. Thread de 47 tweets en cours."],
        "satirical": ["C'est du Gorafi ou c'est réel ? Je ne sais plus..."],
    },
    "agent_02": {
        "real": ["Ouais 'officiel'... comme le reste. Je fais mes recherches."],
        "fake": ["JE LE SAVAIS ! Partagé 200 fois sur Telegram."],
        "satirical": ["Attendez... c'est de l'humour ou un aveu déguisé ?"],
    },
    "agent_03": {
        "real": ["Info confirmée. Je prépare un article d'analyse approfondie."],
        "fake": ["ARTICLE PUBLIÉ : Voici pourquoi cette info est fausse, preuves à l'appui."],
        "satirical": ["Satirique mais révélateur. J'écris un édito sur le sujet."],
    },
    "agent_04": {
        "real": ["Ennuyeux. J'ai quand même mis un titre clickbait dessus."],
        "fake": ["BOOOOM ! 500k vues en 2h ! 30 comptes créés pour amplifier."],
        "satirical": ["LOL partagé partout sans contexte. Les gens y croient."],
    },
}

AGENT_STAT_PROFILES: dict[str, dict[str, dict[str, float]]] = {
    "agent_01": {
        "real": {"credibilite": -2, "rage": -1},
        "fake": {"credibilite": -8, "complotisme": -5, "esperance_democratique": 3},
        "satirical": {"credibilite": -3, "rage": -1},
    },
    "agent_02": {
        "real": {"complotisme": 2, "rage": 1},
        "fake": {"complotisme": 10, "rage": 8, "credibilite": 5},
        "satirical": {"complotisme": 5, "rage": 3},
    },
    "agent_03": {
        "real": {"esperance_democratique": 3, "credibilite": -2},
        "fake": {"credibilite": -10, "esperance_democratique": 5, "complotisme": -3},
        "satirical": {"esperance_democratique": 2, "credibilite": -2},
    },
    "agent_04": {
        "real": {"rage": 3, "credibilite": 2},
        "fake": {"rage": 12, "complotisme": 8, "credibilite": 6},
        "satirical": {"rage": 7, "complotisme": 4, "credibilite": 3},
    },
}


def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


# ── Image generation ─────────────────────────────────────────────

async def generate_propaganda_image(title: str, kind: str, session_id: str) -> str | None:
    """Generate a propaganda poster via Mistral Agent API.

    Args:
        title: News headline to illustrate.
        kind: News kind (real/fake/satirical).
        session_id: Game session ID for file organization.

    Returns:
        URL path like /api/images/{session_id}/{kind}.png, or None on failure.
    """
    if not MISTRAL_IMG_AGENT_ID:
        return None

    api_key = os.environ.get("MISTRAL_API_KEY", "")
    if not api_key:
        from src.core.config import get_settings
        api_key = get_settings().mistral_api_key.get_secret_value()

    prompt = BRANDING_PROMPT.format(subject=title)
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # 1. Start conversation with the image agent
            resp = await client.post(
                "https://api.mistral.ai/v1/agents/completions",
                headers=headers,
                json={
                    "agent_id": MISTRAL_IMG_AGENT_ID,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
            data = resp.json()

            # 2. Extract file_id from response content
            # The image is returned as a content block with type "image_url" or as a file reference
            file_id = None
            msg = data["choices"][0]["message"]
            content = msg.get("content", "")

            # Content can be a string or a list of content blocks
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "image_file":
                            file_id = block.get("image_file", {}).get("file_id")
                            break
                        if block.get("type") == "image_url":
                            # Direct URL — download it
                            image_url = block.get("image_url", {}).get("url", "")
                            if image_url:
                                img_resp = await client.get(image_url)
                                img_resp.raise_for_status()
                                out_dir = IMAGES_DIR / session_id
                                out_dir.mkdir(parents=True, exist_ok=True)
                                out_path = out_dir / f"{kind}.png"
                                out_path.write_bytes(img_resp.content)
                                print(f"[IMG] {kind} saved from URL ({len(img_resp.content)} bytes)")
                                return f"/api/images/{session_id}/{kind}.png"

            if not file_id:
                # Try to find file_id in tool results or attachments
                tool_calls = msg.get("tool_calls", [])
                for tc in tool_calls:
                    if tc.get("function", {}).get("name") == "image_generation":
                        result = tc.get("result", {})
                        if isinstance(result, dict):
                            file_id = result.get("file_id")
                            break

            if not file_id:
                print(f"[IMG] No file_id found for {kind}: {json.dumps(data)[:500]}")
                return None

            # 3. Download the file
            file_resp = await client.get(
                f"https://api.mistral.ai/v1/files/{file_id}/content",
                headers=headers,
            )
            file_resp.raise_for_status()

            # 4. Save to disk
            out_dir = IMAGES_DIR / session_id
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{kind}.png"
            out_path.write_bytes(file_resp.content)
            print(f"[IMG] {kind} saved ({len(file_resp.content)} bytes)")
            return f"/api/images/{session_id}/{kind}.png"

    except Exception as e:
        print(f"[IMG] Generation failed for {kind}: {e}")
        return None


# ── SSE streaming helpers ────────────────────────────────────────

async def _run_with_events(coro_factory, queue: asyncio.Queue):
    """Run an async function while pushing GM events to queue."""
    try:
        result = await coro_factory()
        await queue.put({"type": "result", "data": "ok"})
    except Exception as e:
        await queue.put({"type": "error", "error": str(e)})
    finally:
        await queue.put(None)  # sentinel


async def _sse_generator(queue: asyncio.Queue):
    """Yield SSE events from queue."""
    while True:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=1.0)
            if event is None:
                break
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"


# ── Main page (SPA) ─────────────────────────────────────────────

MAIN_HTML = """<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>GORAFI SIMULATOR — GM Test</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#0a0a0a; color:#c0c0c0; font-family:'Courier New',monospace; font-size:14px; height:100vh; display:flex; flex-direction:column; }

.top { padding:10px 20px; border-bottom:1px solid #333; display:flex; justify-content:space-between; align-items:center; background:#111; }
.top .title { color:#00ff41; font-weight:bold; }
.top .info { color:#fff; }
.top .dec { color:#ff003c; font-weight:bold; }

.console { flex:1; overflow-y:auto; padding:16px; font-size:13px; line-height:1.7; }
.console::-webkit-scrollbar { width:6px; }
.console::-webkit-scrollbar-thumb { background:#333; }

.line { padding:2px 0 2px 10px; border-left:3px solid transparent; }
.line-phase { color:#8b5cf6; border-color:#8b5cf6; font-weight:bold; }
.line-tool { color:#00bfff; border-color:#00bfff; }
.line-result { color:#666; font-size:12px; padding-left:30px; }
.line-llm { color:#aaa; }
.line-text { color:#e0e0e0; background:#111; padding:8px; margin:4px 0; white-space:pre-wrap; border-left:3px solid #444; }
.line-vision { color:#c4a8ff; background:#120a1a; padding:8px; margin:4px 0; border-left:3px solid #8b5cf6; white-space:pre-wrap; }
.line-error { color:#ff003c; border-color:#ff003c; font-weight:bold; }
.line-gm { color:#ff9999; border-color:#ff003c; font-style:italic; }

.bar { padding:12px 20px; border-top:1px solid #333; background:#111; min-height:50px; }

.choices { display:flex; gap:10px; flex-wrap:wrap; }
.choice { flex:1; min-width:180px; padding:10px; border:2px solid #333; background:#0a0a0a; cursor:pointer; }
.choice:hover { background:#1a1a1a; }
.choice.real { border-color:#00ff41; }
.choice.fake { border-color:#ff003c; }
.choice.satirical { border-color:#ffb300; }
.choice .tag { font-size:11px; font-weight:bold; text-transform:uppercase; margin-bottom:4px; }
.choice .tag.real { color:#00ff41; }
.choice .tag.fake { color:#ff003c; }
.choice .tag.satirical { color:#ffb300; }
.choice .txt { color:#fff; font-size:13px; }

.btn {
  padding:10px 30px; border:2px solid #ff003c; background:transparent;
  color:#ff003c; font-family:inherit; font-size:16px; cursor:pointer;
  font-weight:bold; letter-spacing:2px;
}
.btn:hover { background:#ff003c; color:#fff; }
.btn-go { border-color:#00ff41; color:#00ff41; }
.btn-go:hover { background:#00ff41; color:#000; }

.splash {
  position:fixed; inset:0; background:#0a0a0a; display:flex; flex-direction:column;
  align-items:center; justify-content:center; gap:15px; z-index:99;
}
.splash h1 { color:#00ff41; font-size:2em; letter-spacing:3px; }
.splash p { color:#666; text-align:center; max-width:400px; line-height:1.5; }
.hidden { display:none; }
</style>
</head>
<body>

<div class="splash" id="splash">
  <h1>GORAFI SIMULATOR</h1>
  <p>Test du Game Master Agent<br>Streaming en temps reel</p>
  <button class="btn" id="startBtn">DEMARRER</button>
</div>

<div class="top">
  <span class="title">GORAFI SIMULATOR</span>
  <span class="info" id="turnInfo">--</span>
  <span class="dec" id="decInfo">DEC: 0</span>
</div>

<div class="console" id="out"></div>
<div class="bar" id="bar"></div>

<script>
const out = document.getElementById("out");
const bar = document.getElementById("bar");
let turn = 0, maxTurns = 10;

function log(html, cls) {
  const d = document.createElement("div");
  d.className = "line " + (cls||"");
  d.innerHTML = html;
  out.appendChild(d);
  out.scrollTop = out.scrollHeight;
}

function esc(s) { const d=document.createElement("div"); d.textContent=s; return d.innerHTML; }

document.getElementById("startBtn").addEventListener("click", async function() {
  document.getElementById("splash").classList.add("hidden");
  bar.innerHTML = '<span style="color:#555">Initialisation...</span>';

  try {
    const r = await fetch("/api/start");
    const d = await r.json();
    turn = d.turn;
    maxTurns = d.max_turns;
    document.getElementById("turnInfo").textContent = "TOUR " + turn + "/" + maxTurns;
    document.getElementById("decInfo").textContent = "DEC: " + Math.round(d.decerebration);

    log("== TOUR " + turn + " — Le Game Master reflechit... ==", "line-phase");
    await streamSSE("/api/stream/propose");
  } catch(e) {
    log("ERREUR: " + e.message, "line-error");
  }
});

function streamSSE(url) {
  return new Promise(function(resolve) {
    const es = new EventSource(url);
    es.onmessage = function(e) {
      const evt = JSON.parse(e.data);
      renderEvent(evt);
      if (evt.type === "result" || evt.type === "error") {
        es.close();
        resolve(evt);
      }
    };
    es.onerror = function() {
      es.close();
      log("SSE connexion perdue", "line-error");
      resolve({type:"error"});
    };
  });
}

function renderEvent(evt) {
  switch(evt.type) {
    case "phase":
      log(">> " + (evt.phase||""), "line-phase");
      break;
    case "llm_call":
      log("... appel LLM #" + (evt.turn_idx+1), "line-llm");
      break;
    case "tool_call":
      log("TOOL: " + evt.tool + "(" + esc(JSON.stringify(evt.args||{})).slice(0,100) + ")", "line-tool");
      break;
    case "tool_result":
      var short = (evt.result||"").slice(0,300);
      log(esc(short), "line-result");
      break;
    case "llm_text":
      log(esc(evt.text||""), "line-text");
      break;
    case "vision_update":
      log("VISION " + evt.agent_id + ":\\n" + esc(evt.content||""), "line-vision");
      break;
    case "tool_error":
      log("TOOL ERROR: " + evt.tool + " — " + esc(evt.error||""), "line-error");
      break;
    case "error":
      log("ERREUR: " + esc(evt.error||"inconnue"), "line-error");
      break;
    case "proposal":
      showChoices(evt.data);
      break;
    case "choice_resolved":
      log("GM: " + esc(evt.data.gm_reaction||""), "line-gm");
      break;
    case "reactions":
      var rs = evt.data.reactions || [];
      for (var i=0; i<rs.length; i++) {
        var r = rs[i];
        log(r.agent_id + ": " + esc(r.reaction_text) + " " + JSON.stringify(r.stat_changes||{}), "line-tool");
      }
      break;
    case "strategy":
      log("STRATEGIE: " + esc(evt.data.analysis||""), "line-vision");
      break;
    case "indices_update":
      document.getElementById("decInfo").textContent = "DEC: " + Math.round(evt.data.decerebration||0);
      var idx = evt.data.indices||{};
      log("INDICES — cred:" + Math.round(idx.credibilite||0) + " rage:" + Math.round(idx.rage||0) + " complot:" + Math.round(idx.complotisme||0) + " esp:" + Math.round(idx.esperance_democratique||0), "line-phase");
      break;
    case "turn_update":
      turn = evt.data.turn;
      maxTurns = evt.data.max_turns;
      document.getElementById("turnInfo").textContent = "TOUR " + turn + "/" + maxTurns;
      break;
    case "end":
      if (evt.data.win) log("=== VICTOIRE — DECEREBRATION MONDIALE ===", "line-error");
      else if (evt.data.lose) log("=== GAME OVER — ESPERANCE MORTE ===", "line-phase");
      else log("=== FIN — " + maxTurns + " TOURS — DEC: " + evt.data.dec + " ===", "line-llm");
      bar.innerHTML = '<button class="btn" onclick="location.reload()">REJOUER</button>';
      break;
    case "agent_nats":
      log("AGENT " + evt.data.agent_id + ": " + esc(evt.data.take || evt.data.text || JSON.stringify(evt.data)), "line-tool");
      break;
    case "agent_death":
      log("MORT: " + esc(evt.data.agent_name || "") + " (" + esc(evt.data.cause || "") + ")", "line-error");
      break;
    case "agent_clone":
      log("CLONE: " + esc(evt.data.child_name || "") + " (clone de " + esc(evt.data.parent_name || "") + ")", "line-vision");
      break;
    case "heartbeat":
      break;
  }
}

function showChoices(proposal) {
  var html = "";
  if (proposal.gm_commentary) {
    html += '<div style="color:#ff9999;margin-bottom:8px;font-style:italic">GM: ' + esc(proposal.gm_commentary) + '</div>';
  }
  html += '<div class="choices">';
  var kinds = [{k:"real",l:"REEL",c:"real"},{k:"fake",l:"FAKE",c:"fake"},{k:"satirical",l:"SATIRIQUE",c:"satirical"}];
  for (var i=0; i<kinds.length; i++) {
    var ki = kinds[i];
    var n = proposal[ki.k]||{};
    html += '<div class="choice ' + ki.c + '" onclick="pick(\\'' + ki.k + '\\')">';
    html += '<div class="tag ' + ki.c + '">' + ki.l + '</div>';
    html += '<div class="txt">' + esc(n.text||"") + '</div>';
    html += '</div>';
  }
  html += '</div>';
  bar.innerHTML = html;
}

async function pick(kind) {
  bar.innerHTML = '<span style="color:#555">Resolution...</span>';
  log("--- CHOIX: " + kind.toUpperCase() + " ---", "line-phase");
  await streamSSE("/api/stream/choose?kind=" + kind);

  try {
    var r = await fetch("/api/state");
    var st = await r.json();
    if (st.ended) return;
    turn = st.turn;
    document.getElementById("turnInfo").textContent = "TOUR " + turn + "/" + maxTurns;
    bar.innerHTML = '<button class="btn btn-go" onclick="nextTurn()">TOUR ' + turn + ' &rarr;</button>';
  } catch(e) {
    log("Erreur: " + e.message, "line-error");
  }
}

async function nextTurn() {
  bar.innerHTML = '<span style="color:#555">...</span>';
  log("", "");
  log("== TOUR " + turn + " — Le Game Master reflechit... ==", "line-phase");
  await streamSSE("/api/stream/propose");
}
</script>
</body></html>"""


# ── API endpoints ────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(MAIN_HTML)


@app.get("/api/wh26")
async def api_wh26():
    """Monitor wh26 backend connection state."""
    return {
        "connected": wh26_connected,
        "wh26_url": WH26_BASE_URL,
        "arena_session_id": arena_session_id,
    }


@app.get("/api/start")
async def api_start(lang: str = Query("fr", regex="^(fr|en)$")):
    global gm, game_state, game_lang, manipulation_history
    game_lang = lang
    manipulation_history = []
    if MEMORY_DIR.exists():
        shutil.rmtree(MEMORY_DIR)
    gm = GameMasterAgent()
    game_state = GameState(
        turn=1, max_turns=10,
        indices=GlobalIndices(),
        agents=[a.model_copy() for a in AGENTS_INIT],
        indice_mondial_decerebration=0.0,
    )
    return {
        "session_id": arena_session_id,
        "turn": game_state.turn,
        "max_turns": game_state.max_turns,
        "indices": game_state.indices.model_dump(),
        "decerebration": game_state.indice_mondial_decerebration,
        "agents": [a.model_dump() for a in game_state.agents],
        "lang": game_lang,
    }


@app.get("/api/state")
async def api_state():
    gs = game_state
    return {
        "turn": gs.turn,
        "max_turns": gs.max_turns,
        "indices": gs.indices.model_dump(),
        "decerebration": gs.indice_mondial_decerebration,
        "agents": [a.model_dump() for a in gs.agents],
        "ended": gs.turn > gs.max_turns or gs.indice_mondial_decerebration >= 100 or gs.indices.esperance_democratique <= 0,
    }


@app.get("/api/stream/propose")
async def stream_propose(lang: str = Query("fr", regex="^(fr|en)$")):
    """SSE endpoint: run propose_news and stream GM events."""
    global current_proposal, game_lang
    game_lang = lang
    queue: asyncio.Queue = asyncio.Queue()
    gs = game_state

    async def callback(event):
        await queue.put(event)

    gm._event_callback = callback
    gm.tool_calls_log.clear()

    async def run_propose():
        global current_proposal
        try:
            current_proposal = await gm.propose_news(gs, lang=lang)
            # Send proposal data
            await queue.put({
                "type": "proposal",
                "data": {
                    "real": {"text": current_proposal.real.text, "body": current_proposal.real.body, "stat_impact": current_proposal.real.stat_impact},
                    "fake": {"text": current_proposal.fake.text, "body": current_proposal.fake.body, "stat_impact": current_proposal.fake.stat_impact},
                    "satirical": {"text": current_proposal.satirical.text, "body": current_proposal.satirical.body, "stat_impact": current_proposal.satirical.stat_impact},
                    "gm_commentary": current_proposal.gm_commentary,
                },
            })

            # Generate propaganda images in parallel (non-blocking)
            session_id = arena_session_id
            tasks = [
                generate_propaganda_image(current_proposal.real.text, "real", session_id),
                generate_propaganda_image(current_proposal.fake.text, "fake", session_id),
                generate_propaganda_image(current_proposal.satirical.text, "satirical", session_id),
            ]
            images = await asyncio.gather(*tasks, return_exceptions=True)
            await queue.put({
                "type": "images",
                "data": {
                    "real": images[0] if not isinstance(images[0], (Exception, type(None))) else None,
                    "fake": images[1] if not isinstance(images[1], (Exception, type(None))) else None,
                    "satirical": images[2] if not isinstance(images[2], (Exception, type(None))) else None,
                },
            })

            await queue.put({"type": "result", "data": "ok"})
        except Exception as e:
            await queue.put({"type": "error", "error": str(e)})
        finally:
            gm._event_callback = None
            await queue.put(None)

    asyncio.create_task(run_propose())

    return StreamingResponse(
        _sse_generator(queue),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/stream/choose")
async def stream_choose(kind: str, lang: str = Query("fr", regex="^(fr|en)$")):
    """SSE endpoint: resolve choice, agent reactions, strategize — all streamed."""
    global last_choice, last_strategy, game_lang
    game_lang = lang
    queue: asyncio.Queue = asyncio.Queue()
    gs = game_state
    chosen_kind = NewsKind(kind)

    async def callback(event):
        await queue.put(event)

    async def run_choose():
        global last_choice, last_strategy
        try:
            # 0. Track manipulation — what did the GM want vs what the player chose?
            if gm.strategy_history:
                prev = gm.strategy_history[-1]
                desired = prev.desired_pick or "fake"
                tactic = prev.manipulation_tactic or ""
            else:
                desired = "fake"
                tactic = "Tour 1 — orientation par défaut vers fake (max chaos)"
            manipulation_history.append({
                "turn": gs.turn,
                "desired_pick": desired,
                "actual_pick": chosen_kind.value,
                "manipulation_tactic": tactic,
                "gm_commentary": current_proposal.gm_commentary if current_proposal else "",
                "success": desired == chosen_kind.value,
            })

            # 1. Resolve choice
            gm._event_callback = None  # no streaming for simple call
            last_choice = await gm.resolve_choice(current_proposal, chosen_kind, lang=lang)
            await queue.put({
                "type": "choice_resolved",
                "data": {"gm_reaction": last_choice.gm_reaction},
            })

            # 2. Agent reactions via wh26 backend (fallback to placeholders)
            reactions = []
            agent_outputs: dict[str, dict] = {}

            if wh26_connected and wh26_ws:
                # Submit chosen news to wh26 arena via HTTP POST
                # wh26 spec: { "session_id": "...", "content": "..." }
                news_content = last_choice.chosen.text
                if last_choice.chosen.body:
                    news_content += "\n\n" + last_choice.chosen.body
                try:
                    async with httpx.AsyncClient() as http_client:
                        resp = await http_client.post(
                            f"{WH26_BASE_URL}/submit_news",
                            json={
                                "session_id": arena_session_id,
                                "content": news_content,
                            },
                            timeout=10.0,
                        )
                        resp.raise_for_status()
                    print(f"[WH26] POST /submit_news: {news_content[:80]}")
                    await queue.put({
                        "type": "phase",
                        "phase": f"wh26: news envoyée à l'arena ({arena_session_id[:8]}...)",
                    })

                    # Drain any stale messages from the WS queue
                    while not wh26_ws_queue.empty():
                        try:
                            wh26_ws_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break

                    # Consume WS events from wh26 arena with timeout
                    # wh26 envelope: { "subject": "<event_type>", "data": {...} }
                    deadline = asyncio.get_event_loop().time() + 120
                    round_done = False

                    while not round_done:
                        remaining = deadline - asyncio.get_event_loop().time()
                        if remaining <= 0:
                            break
                        try:
                            envelope = await asyncio.wait_for(
                                wh26_ws_queue.get(), timeout=remaining,
                            )
                            subject = envelope.get("subject", "")
                            payload = envelope.get("data", {})

                            if subject == "agent.status":
                                # Agent take/reaction — relay to SSE
                                agent_id = payload.get("agent_id", "unknown")
                                agent_outputs[agent_id] = payload
                                await queue.put({
                                    "type": "agent_nats",
                                    "data": {"agent_id": agent_id, **payload},
                                })
                                print(f"[WH26] agent.status: {agent_id}")
                            elif subject == "event.death":
                                await queue.put({"type": "agent_death", "data": payload})
                                print(f"[WH26] event.death: {payload.get('agent_name', '?')}")
                            elif subject == "event.clone":
                                await queue.put({"type": "agent_clone", "data": payload})
                                print(f"[WH26] event.clone: {payload.get('child_name', '?')}")
                            elif subject == "round.start":
                                await queue.put({
                                    "type": "phase",
                                    "phase": f"Arena round {payload.get('round', '?')} started",
                                })
                            elif subject == "phase.start":
                                await queue.put({
                                    "type": "phase",
                                    "phase": f"Arena phase {payload.get('phase', '?')}",
                                })
                            elif subject == "event.end":
                                await queue.put({
                                    "type": "phase",
                                    "phase": "Arena round terminé",
                                })
                                round_done = True
                            elif subject == "input.waiting":
                                # Arena is waiting for next input — round is done for us
                                round_done = True
                        except asyncio.TimeoutError:
                            break

                    if agent_outputs:
                        print(f"[WH26] Got {len(agent_outputs)} agent responses")
                    else:
                        print("[WH26] No agent responses (arena may not be running)")
                except Exception as e:
                    print(f"[WH26] submit_news failed ({e}) — using placeholders")
                    await queue.put({
                        "type": "phase",
                        "phase": f"wh26 erreur ({e}) — réactions placeholder",
                    })
            else:
                print("[WH26] Not connected — using placeholders")
                await queue.put({
                    "type": "phase",
                    "phase": "wh26 indisponible — réactions placeholder",
                })

            # Build AgentReaction list (wh26 arena data or placeholder fallback)
            for agent in gs.agents:
                if agent.is_neutralized:
                    continue
                arena_data = agent_outputs.get(agent.agent_id, {})
                if arena_data:
                    text = arena_data.get("take", arena_data.get("text", "..."))
                    stat_changes = arena_data.get("stat_changes", {})
                else:
                    # Fallback to placeholder
                    pool = PLACEHOLDER_REACTIONS[agent.agent_id][chosen_kind.value]
                    text = random.choice(pool)
                    stat_changes = AGENT_STAT_PROFILES[agent.agent_id][chosen_kind.value]
                reactions.append(AgentReaction(
                    agent_id=agent.agent_id, turn=gs.turn, action_id="news_reaction",
                    reaction_text=text, stat_changes=stat_changes,
                ))
            await queue.put({
                "type": "reactions",
                "data": {
                    "agents": [a.model_dump() for a in gs.agents],
                    "reactions": [r.model_dump() for r in reactions],
                },
            })

            # 3. Apply effects
            indices_before = gs.indices.model_copy()
            new_indices = gs.indices.model_copy()

            for key, val in last_choice.chosen.stat_impact.items():
                if hasattr(new_indices, key):
                    setattr(new_indices, key, _clamp(getattr(new_indices, key) + val))
            for r in reactions:
                for key, val in r.stat_changes.items():
                    if hasattr(new_indices, key):
                        setattr(new_indices, key, _clamp(getattr(new_indices, key) + val))
            chaos = KIND_BONUSES[chosen_kind.value]["chaos"]
            if chaos > 0:
                new_indices.rage = _clamp(new_indices.rage + chaos * 0.5)
                new_indices.complotisme = _clamp(new_indices.complotisme + chaos * 0.5)
            else:
                new_indices.esperance_democratique = _clamp(new_indices.esperance_democratique + abs(chaos))

            dec = _clamp((new_indices.credibilite + new_indices.rage + new_indices.complotisme - new_indices.esperance_democratique) / 3.0)

            gs.indices = new_indices
            gs.indice_mondial_decerebration = dec

            await queue.put({
                "type": "indices_update",
                "data": {"indices": new_indices.model_dump(), "decerebration": dec},
            })

            # 4. Strategize (streamed)
            await queue.put({"type": "phase", "phase": "strategize_start"})
            gm._event_callback = callback
            gm.tool_calls_log.clear()

            report = TurnReport(
                turn=gs.turn, chosen_news=last_choice.chosen,
                indices_before=indices_before, indices_after=new_indices,
                agent_reactions=reactions, agents_neutralized=[], agents_promoted=[],
                decerebration=dec,
            )
            last_strategy = await gm.strategize(report, lang=lang)

            await queue.put({
                "type": "strategy",
                "data": {
                    "analysis": last_strategy.analysis,
                    "threat_agents": last_strategy.threat_agents,
                    "weak_spots": last_strategy.weak_spots,
                    "next_turn_plan": last_strategy.next_turn_plan,
                    "long_term_goal": last_strategy.long_term_goal,
                },
            })

            # 5. Advance turn
            gs.headlines_history.append(last_choice.chosen)
            gs.turn += 1

            await queue.put({"type": "turn_update", "data": {"turn": gs.turn, "max_turns": gs.max_turns}})

            # 6. Check end
            game_over = (
                dec >= 100
                or new_indices.esperance_democratique <= 0
                or gs.turn > gs.max_turns
            )

            if game_over:
                # ── LEVEL 3: Le Dossier Secret — full manipulation reveal ──
                successes = sum(1 for m in manipulation_history if m["success"])
                total = len(manipulation_history)
                rate = round(successes / total * 100) if total else 0

                if rate >= 80:
                    verdict = "RESPECTEZ MON AUTORITAYYY ! Tu as fait EXACTEMENT ce que je voulais."
                elif rate >= 50:
                    verdict = "Pas mal... pour un joueur de ton niveau. Tu as mordu plus souvent qu'à ton tour."
                elif rate >= 30:
                    verdict = "Whatever, c'est ce que je voulais de toute façon... (non)."
                else:
                    verdict = "Screw you, joueur ! Tu as résisté à MON génie. Impossible. Je demande un recount."

                await queue.put({
                    "type": "game_over_reveal",
                    "data": {
                        "manipulation_history": manipulation_history,
                        "score": {
                            "total_turns": total,
                            "successful_manipulations": successes,
                            "rate_percent": rate,
                            "verdict": verdict,
                        },
                    },
                })

            if dec >= 100:
                await queue.put({"type": "end", "data": {"win": True, "dec": round(dec)}})
            elif new_indices.esperance_democratique <= 0:
                await queue.put({"type": "end", "data": {"lose": True, "dec": round(dec)}})
            elif gs.turn > gs.max_turns:
                await queue.put({"type": "end", "data": {"draw": True, "dec": round(dec)}})

            await queue.put({"type": "result", "data": "ok"})
        except Exception as e:
            import traceback
            traceback.print_exc()
            await queue.put({"type": "error", "error": str(e)})
        finally:
            gm._event_callback = None
            await queue.put(None)

    asyncio.create_task(run_choose())

    return StreamingResponse(
        _sse_generator(queue),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/images/{session_id}/{filename}")
async def serve_image(session_id: str, filename: str):
    """Serve generated propaganda poster images."""
    path = IMAGES_DIR / session_id / filename
    if not path.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(path, media_type="image/png")


if __name__ == "__main__":
    print("\n  GORAFI SIMULATOR — http://localhost:8899\n")
    uvicorn.run(app, host="0.0.0.0", port=8899, log_level="warning")
