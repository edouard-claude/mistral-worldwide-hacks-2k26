"""Web interface to test the Game Master agent — with live streaming.

The central element is the STREAMING CONSOLE showing the GM's
reasoning process: tool calls, vision updates, and thinking in real-time.

Run: cd game-of-claw && python3 scripts/play_web.py
Open: http://localhost:8899
"""

import asyncio
import json
import os
import shutil
import sys
import uuid

# Force unbuffered stdout so print() appears immediately in logs
sys.stdout.reconfigure(line_buffering=True)
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import websockets

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
import uvicorn

from src.agents.game_master_agent import MEMORY_DIR, GameMasterAgent, KIND_BONUSES
from src.models.agent import AgentLevel, AgentRanking, AgentReaction, AgentState, AgentStats
from src.models.game import GameState, TurnReport
from src.models.world import GlobalIndices, NewsKind

# ── wh26 backend state ───────────────────────────────────────────

WH26_BASE_URL = os.environ.get("WH26_BASE_URL", "https://wh26-backend.wh26.edouard.cl")
WH26_WS_URL = os.environ.get("WH26_WS_URL", "wss://wh26-backend.wh26.edouard.cl")

arena_session_id: str | None = None  # Set per game by /api/start
wh26_ws: websockets.ClientConnection | None = None
wh26_ws_queue: asyncio.Queue = asyncio.Queue()
wh26_connected: bool = False
_wh26_ws_task: asyncio.Task | None = None  # Background WS reader task

# ── Frontend WebSocket clients ────────────────────────────────────
# Maps session_id -> list of asyncio.Queue (one per connected WS client)
_ws_clients: dict[str, list[asyncio.Queue]] = {}


async def _broadcast_to_frontend(event: dict) -> None:
    """Push an event to ALL connected frontend WS clients for current session."""
    sid = arena_session_id
    if not sid or sid not in _ws_clients:
        etype = event.get("type", event.get("subject", "?"))
        print(f"[WS-FE] BROADCAST DROPPED ({etype}): no clients for session {str(sid)[:8] if sid else 'None'}")
        return
    clients = _ws_clients[sid]
    if not clients:
        etype = event.get("type", event.get("subject", "?"))
        print(f"[WS-FE] BROADCAST DROPPED ({etype}): 0 clients connected")
        return
    dead: list[asyncio.Queue] = []
    for q in clients:
        try:
            q.put_nowait(event)
        except Exception:
            dead.append(q)
    for q in dead:
        _ws_clients[sid].remove(q)
    etype = event.get("type", event.get("subject", "?"))
    print(f"[WS-FE] BROADCAST {etype} → {len(clients) - len(dead)} clients")


# ── Language & Image generation state ────────────────────────────
game_lang: str = "fr"
mistral_img_client = None  # Mistral SDK client for image generation
mistral_img_agent_id: str | None = None
IMAGES_DIR = Path("/tmp/gorafi_images")

BRANDING_PROMPT = (
    "For a satirical video game (not real propaganda): "
    "Vintage Cold War Soviet propaganda poster style illustration about: {subject}. "
    "Satirical socialist realism, highly symmetrical and monumental composition. "
    "Retro lithograph texture, bold ink outlines, flat graphic vector style. "
    "Strictly limited color palette using only aged parchment tan, deep black, "
    "and stark socialist red. Humorous dystopia aesthetic, distressed paper."
)


async def _wh26_ws_reader(ws: websockets.ClientConnection) -> None:
    """Background task: read WS messages from wh26 and put them in the queue.

    On disconnect, attempts reconnection with exponential backoff up to 3 times.
    """
    global wh26_ws, wh26_connected
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

    # Mark as disconnected
    wh26_connected = False
    wh26_ws = None

    # Attempt reconnection if we still have a session
    if arena_session_id:
        for attempt in range(1, 4):
            delay = 2 ** attempt
            print(f"[WH26] Reconnecting in {delay}s (attempt {attempt}/3)...")
            await asyncio.sleep(delay)
            try:
                new_ws = await websockets.connect(f"{WH26_WS_URL}/ws/{arena_session_id}")
                wh26_ws = new_ws
                wh26_connected = True
                print(f"[WH26] Reconnected to /ws/{arena_session_id}")
                # Restart reader loop recursively on the new connection
                await _wh26_ws_reader(new_ws)
                return
            except Exception as e:
                print(f"[WH26] Reconnect attempt {attempt} failed: {e}")
        print("[WH26] All reconnection attempts exhausted")


async def _connect_wh26(session_id: str) -> None:
    """Connect WS to wh26 backend relay for the given session.

    Handles init_session POST + WebSocket open. Safe to call multiple times
    (disconnects previous WS first).
    """
    global wh26_ws, wh26_connected, _wh26_ws_task

    # Tear down previous connection if any
    if wh26_ws:
        try:
            await wh26_ws.close()
        except Exception:
            pass
        wh26_ws = None
        wh26_connected = False
    if _wh26_ws_task and not _wh26_ws_task.done():
        _wh26_ws_task.cancel()
        _wh26_ws_task = None

    # Drain stale messages
    while not wh26_ws_queue.empty():
        try:
            wh26_ws_queue.get_nowait()
        except asyncio.QueueEmpty:
            break

    try:
        # Init session on relay (publishes arena.init on NATS → swarm starts)
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{WH26_BASE_URL}/init_session",
                json={"session_id": session_id, "lang": game_lang},
            )
            print(f"[WH26] POST /init_session → {resp.status_code}: {resp.text[:100]}")

        # Open WebSocket to relay for arena events
        wh26_ws = await websockets.connect(f"{WH26_WS_URL}/ws/{session_id}")
        wh26_connected = True
        _wh26_ws_task = asyncio.create_task(_wh26_ws_reader(wh26_ws))
        print(f"[WH26] WebSocket connected: /ws/{session_id}")
    except Exception as e:
        print(f"[WH26] Connection failed ({e}) — running without arena")
        wh26_ws = None
        wh26_connected = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — initialize image agent."""
    # Create Mistral image generation agent via SDK
    global mistral_img_client, mistral_img_agent_id
    try:
        from mistralai import Mistral
        api_key = os.environ.get("MISTRAL_API_KEY", "")
        if not api_key:
            from src.core.config import get_settings
            api_key = get_settings().mistral_api_key.get_secret_value()
        mistral_img_client = Mistral(api_key=api_key)
        agent = mistral_img_client.beta.agents.create(
            model="mistral-medium-2505",
            name="propaganda-poster",
            tools=[{"type": "image_generation"}],
        )
        mistral_img_agent_id = agent.id
        print(f"[IMG] Mistral image agent created: {mistral_img_agent_id}")
    except Exception as e:
        print(f"[IMG] Failed to create image agent ({e}) — images disabled")
        mistral_img_client = None
        mistral_img_agent_id = None

    yield
    if wh26_ws:
        await wh26_ws.close()
        print("[WH26] WebSocket closed")
    if _wh26_ws_task and not _wh26_ws_task.done():
        _wh26_ws_task.cancel()


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
        agent_id="agent_01", name="Grigori",
        personality="Extrême droite. Provocateur né, amplifie chaque scandale pour confirmer sa vision du monde.",
        country="RU",
        stats=AgentStats(croyance=80.0, confiance=15.0, richesse=75.0),
        level=AgentLevel.ACTIF,
    ),
    AgentState(
        agent_id="agent_02", name="Natasha",
        personality="Droite modérée. Pragmatique, vérifie ses sources mais reste influençable par les émotions.",
        country="RU",
        stats=AgentStats(croyance=50.0, confiance=60.0, richesse=50.0),
        level=AgentLevel.ACTIF,
    ),
    AgentState(
        agent_id="agent_03", name="Pavel",
        personality="Gauche. Idéaliste, croit au progrès social mais vulnérable aux narratifs victimaires.",
        country="RU",
        stats=AgentStats(croyance=40.0, confiance=70.0, richesse=35.0),
        level=AgentLevel.PASSIF,
    ),
    AgentState(
        agent_id="agent_04", name="Zoya",
        personality="Extrême gauche. Militante enflammée, voit des complots partout et résiste à toute autorité.",
        country="RU",
        stats=AgentStats(croyance=75.0, confiance=25.0, richesse=30.0),
        level=AgentLevel.LEADER,
    ),
]

AGENT_NAMES = {a.agent_id: a.name for a in AGENTS_INIT}
AGENT_ICONS = {"agent_01": "🔍", "agent_02": "🐐", "agent_03": "📰", "agent_04": "🧨"}
AGENT_COLORS = {"agent_01": "#00ff41", "agent_02": "#ffb300", "agent_03": "#00bfff", "agent_04": "#ff003c"}
SWARM_ICONS = ["🔍", "🐐", "📰", "🧨", "💀", "🧬", "🔥", "🎭"]
SWARM_COLORS = ["#00ff41", "#ffb300", "#00bfff", "#ff003c", "#8b5cf6", "#ff6b00", "#00ff9f", "#ff69b4"]


def _sync_agents_from_swarm(gs: "GameState", swarm_agents: list[dict], graveyard: list[dict] | None = None) -> None:
    """Update game_state.agents from swarm state.global data (deaths, clones, scores)."""
    new_agents: list[AgentState] = []
    for i, sa in enumerate(swarm_agents):
        name = sa.get("name", f"Agent_{i+1}")
        color = sa.get("political_color", 0.5)
        confidence = sa.get("confidence", 3)
        if color <= 0.15:
            pol = "Extrême droite"
        elif color <= 0.40:
            pol = "Droite"
        elif color <= 0.60:
            pol = "Centre"
        elif color <= 0.85:
            pol = "Gauche"
        else:
            pol = "Extrême gauche"
        is_clone = bool(sa.get("parent_id"))
        born = sa.get("born_at_round", 1)
        personality = f"{pol}."
        if is_clone:
            personality += f" Clone né au tour {born}."
        new_agents.append(AgentState(
            agent_id=sa.get("id", f"agent_{i+1:02d}"),
            name=name,
            personality=personality,
            country="RU",
            stats=AgentStats(
                croyance=50.0 + (color - 0.5) * 40,
                confiance=confidence * 20.0,
                richesse=50.0,
            ),
            level=AgentLevel.ACTIF,
        ))
    gs.agents = new_agents
    # Update global name mappings
    for i, a in enumerate(new_agents):
        AGENT_NAMES[a.agent_id] = a.name
        AGENT_ICONS[a.agent_id] = SWARM_ICONS[i % len(SWARM_ICONS)]
        AGENT_COLORS[a.agent_id] = SWARM_COLORS[i % len(SWARM_COLORS)]
    print(f"[SWARM] Agents synced: {[a.name for a in new_agents]}")

def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


# ── Image generation ─────────────────────────────────────────────

async def generate_propaganda_image(title: str, kind: str, session_id: str) -> str | None:
    """Generate a propaganda poster via Mistral SDK (Agent API + Flux).

    Uses client.beta.conversations.start() which handles the full agentic loop
    (tool call → image generation → file return) in a single call.

    Args:
        title: News headline to illustrate.
        kind: News kind (real/fake/satirical).
        session_id: Game session ID for file organization.

    Returns:
        URL path like /api/images/{session_id}/{kind}.png, or None on failure.
    """
    if not mistral_img_client or not mistral_img_agent_id:
        return None

    prompt = BRANDING_PROMPT.format(subject=title)

    try:
        # Run in thread to avoid blocking the event loop (SDK is sync)
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None,
            lambda: mistral_img_client.beta.conversations.start(
                agent_id=mistral_img_agent_id,
                inputs=prompt,
            ),
        )

        # Extract file_id from response outputs
        file_id = None
        for output in resp.outputs:
            if output.type == "message.output":
                for block in output.content:
                    if block.type == "tool_file":
                        file_id = block.file_id
                        break
            if file_id:
                break

        if not file_id:
            print(f"[IMG] No file_id in response for {kind}")
            return None

        # Download the generated image
        file_resp = await loop.run_in_executor(
            None,
            lambda: mistral_img_client.files.download(file_id=file_id),
        )
        image_bytes = file_resp.read() if hasattr(file_resp, "read") else file_resp

        # Save to disk
        out_dir = IMAGES_DIR / session_id
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{kind}.png"
        out_path.write_bytes(image_bytes)
        print(f"[IMG] {kind} saved ({len(image_bytes)} bytes)")
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


@app.post("/init_session")
async def init_session(request: Request):
    """Stub for frontend — relay usually handles this. Just ack."""
    body = await request.json()
    sid = body.get("session_id", "")
    print(f"[STUB] /init_session session_id={sid[:8]}...")
    return JSONResponse({"status": "ok", "session_id": sid})


@app.websocket("/ws/{session_id}")
async def ws_frontend(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for the React frontend.

    The GM pushes events here instead of SSE when clients are connected.
    On reconnect, the new client is ADDED to the list (not replacing).
    The old handler removes its own queue in finally.
    """
    await websocket.accept()
    q: asyncio.Queue = asyncio.Queue()

    # Add to existing list (don't replace — _run() holds a ref to the list)
    if session_id not in _ws_clients:
        _ws_clients[session_id] = []
    _ws_clients[session_id].append(q)
    n = len(_ws_clients[session_id])
    print(f"[WS-FE] Client connected: {session_id[:8]}... ({n} client(s))")

    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=30.0)
                await websocket.send_json(event)
            except asyncio.TimeoutError:
                # Heartbeat to keep connection alive during long GM processing
                try:
                    await websocket.send_json({"type": "heartbeat"})
                except Exception:
                    break  # Client gone
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS-FE] Client error: {e}")
    finally:
        if session_id in _ws_clients and q in _ws_clients[session_id]:
            _ws_clients[session_id].remove(q)
        remaining = len(_ws_clients.get(session_id, []))
        print(f"[WS-FE] Client disconnected: {session_id[:8]}... ({remaining} remaining)")


@app.get("/api/propose")
async def api_propose(
    session_id: str | None = Query(None),
    lang: str = Query("fr", regex="^(fr|en)$"),
):
    """REST trigger for propose — events are pushed via WebSocket."""
    global current_proposal, game_lang
    game_lang = lang
    gs = game_state

    async def _ws_callback(event: dict) -> None:
        await _broadcast_to_frontend(event)

    async def _run():
        global current_proposal
        try:
            gm._event_callback = _ws_callback
            gm.tool_calls_log.clear()
            current_proposal = await gm.propose_news(gs, lang=lang)

            await _broadcast_to_frontend({
                "type": "proposal",
                "data": {
                    "real": {"text": current_proposal.real.text, "body": current_proposal.real.body, "stat_impact": current_proposal.real.stat_impact},
                    "fake": {"text": current_proposal.fake.text, "body": current_proposal.fake.body, "stat_impact": current_proposal.fake.stat_impact},
                    "satirical": {"text": current_proposal.satirical.text, "body": current_proposal.satirical.body, "stat_impact": current_proposal.satirical.stat_impact},
                    "gm_commentary": current_proposal.gm_commentary,
                },
            })

            # Generate propaganda images in parallel
            sid = arena_session_id
            print(f"[IMG] Starting image generation for session {str(sid)[:8]}... (client={bool(mistral_img_client)}, agent={bool(mistral_img_agent_id)})")
            img_tasks = [
                generate_propaganda_image(current_proposal.real.text, "real", sid),
                generate_propaganda_image(current_proposal.fake.text, "fake", sid),
                generate_propaganda_image(current_proposal.satirical.text, "satirical", sid),
            ]
            images = await asyncio.gather(*img_tasks, return_exceptions=True)
            img_result = {
                "real": images[0] if not isinstance(images[0], (Exception, type(None))) else None,
                "fake": images[1] if not isinstance(images[1], (Exception, type(None))) else None,
                "satirical": images[2] if not isinstance(images[2], (Exception, type(None))) else None,
            }
            print(f"[IMG] Results: real={img_result['real']}, fake={img_result['fake']}, sat={img_result['satirical']}")
            for i, img in enumerate(images):
                if isinstance(img, Exception):
                    print(f"[IMG] Error for image {i}: {img}")
            await _broadcast_to_frontend({
                "type": "images",
                "data": img_result,
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            await _broadcast_to_frontend({"type": "error", "data": {"message": str(e)}})
        finally:
            gm._event_callback = None

    asyncio.create_task(_run())
    return JSONResponse({"status": "accepted"}, status_code=202)


@app.get("/api/choose")
async def api_choose(
    session_id: str | None = Query(None),
    kind: str = Query(...),
    lang: str = Query("fr", regex="^(fr|en)$"),
):
    """REST trigger for choose — events are pushed via WebSocket."""
    global last_choice, last_strategy, game_lang
    game_lang = lang
    gs = game_state
    chosen_kind = NewsKind(kind)

    async def _ws_callback(event: dict) -> None:
        await _broadcast_to_frontend(event)

    async def _run():
        global last_choice, last_strategy
        try:
            # 0. Track manipulation
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
            gm._event_callback = None
            last_choice = await gm.resolve_choice(current_proposal, chosen_kind, lang=lang)
            await _broadcast_to_frontend({
                "type": "choice_resolved",
                "data": {"gm_reaction": last_choice.gm_reaction},
            })

            # 2. Agent reactions via wh26
            reactions = []
            agent_outputs: dict[str, dict] = {}
            arena_global_state: dict | None = None

            if wh26_connected and wh26_ws:
                news_content = last_choice.chosen.text
                if last_choice.chosen.body:
                    news_content += "\n\n" + last_choice.chosen.body
                try:
                    async with httpx.AsyncClient() as http_client:
                        resp = await http_client.post(
                            f"{WH26_BASE_URL}/submit_news",
                            json={"session_id": arena_session_id, "content": news_content},
                            timeout=10.0,
                        )
                        resp.raise_for_status()
                    print(f"[WH26] POST /submit_news: {news_content[:80]}")
                    await _broadcast_to_frontend({"type": "phase", "phase": f"wh26: news envoyée à l'arena"})

                    while not wh26_ws_queue.empty():
                        try:
                            wh26_ws_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break

                    deadline = asyncio.get_event_loop().time() + 120
                    round_done = False
                    while not round_done:
                        remaining = deadline - asyncio.get_event_loop().time()
                        if remaining <= 0:
                            break
                        try:
                            envelope = await asyncio.wait_for(wh26_ws_queue.get(), timeout=remaining)
                            # Relay sends {"event": "arena.<topic>", "data": ...}
                            raw_subject = envelope.get("subject", "") or envelope.get("event", "")
                            # Strip "arena." prefix to get the topic suffix
                            subject = raw_subject.replace("arena.", "", 1) if raw_subject.startswith("arena.") else raw_subject
                            payload = envelope.get("data", {})

                            # Forward ALL arena events to frontend via WS
                            await _broadcast_to_frontend({"subject": subject, "data": payload})

                            # Match agent.{uuid}.output — contains debate content
                            if ".output" in subject and subject.startswith("agent."):
                                agent_id = payload.get("agent_id", "")
                                phase = payload.get("phase", 0)
                                content = payload.get("content", "")
                                agent_name = payload.get("agent_name", "")
                                print(f"[WH26-DBG] agent.output: {agent_name} phase={phase} content={content[:80]!r} conf={payload.get('confidence')}")
                                confidence = payload.get("confidence", 0)
                                # Accumulate per agent; prefer phase 2 (public take) for reaction text
                                existing = agent_outputs.get(agent_id, {})
                                existing["name"] = agent_name
                                existing["agent_id"] = agent_id
                                if phase == 2 or "take" not in existing:
                                    existing["take"] = content
                                if phase == 1:
                                    existing["confidence_initial"] = confidence
                                elif phase == 3:
                                    existing["confidence_final"] = confidence
                                elif phase == 4:
                                    existing["vote"] = content
                                    existing["rankings"] = payload.get("rankings", [])
                                    if payload.get("new_color") is not None:
                                        existing["new_color"] = payload["new_color"]
                                existing[f"phase_{phase}"] = content
                                is_error = payload.get("is_error", False)
                                existing["is_error"] = existing.get("is_error", False) or is_error
                                agent_outputs[agent_id] = existing
                            # Match agent.{uuid}.status
                            elif ".status" in subject and subject.startswith("agent."):
                                agent_id = subject.split(".")[1] if len(subject.split(".")) >= 3 else ""
                                if agent_id and agent_id not in agent_outputs:
                                    agent_outputs[agent_id] = {"agent_id": agent_id}
                            elif subject == "event.death":
                                pass
                            elif subject == "event.clone":
                                pass
                            elif subject == "state.global":
                                arena_global_state = payload
                                if "agents" in payload:
                                    for sa in payload["agents"]:
                                        aid = sa.get("id", "")
                                        agent_outputs[aid] = {
                                            **agent_outputs.get(aid, {}),
                                            "swarm_score": sa.get("score", 0),
                                            "swarm_status": sa.get("status", "alive"),
                                            "name": sa.get("name", ""),
                                        }
                                    # Update game_state agents from swarm data
                                    _sync_agents_from_swarm(gs, payload.get("agents", []), payload.get("graveyard", []))
                                print(f"[WH26] state.global received: {len(payload.get('agents', []))} agents")
                            elif subject == "event.end":
                                round_done = True
                            elif subject == "input.waiting":
                                round_done = True
                        except asyncio.TimeoutError:
                            break

                    if agent_outputs:
                        for aid, ao in agent_outputs.items():
                            name = ao.get("name", "?")
                            has_take = bool(ao.get("take"))
                            conf = ao.get("confidence_final", ao.get("confidence_initial", "?"))
                            print(f"[WH26]   {name} ({aid[:8]}): take={'yes' if has_take else 'NO'}, conf={conf}")
                        print(f"[WH26] Got {len(agent_outputs)} agent responses")
                except Exception as e:
                    import traceback; traceback.print_exc()
                    print(f"[WH26] submit_news failed ({e})")
                    await _broadcast_to_frontend({"type": "phase", "phase": f"wh26 erreur ({e})"})
            else:
                print("[WH26] Not connected — no arena reactions")
                await _broadcast_to_frontend({"type": "phase", "phase": "wh26 non connecté"})

            # Build AgentReaction list — match by agent_id from swarm
            active_agents = [a for a in gs.agents if not a.is_neutralized]
            for agent in active_agents:
                arena_data = agent_outputs.get(agent.agent_id, {})
                if arena_data:
                    # Use phase 2 public take, fallback to any content
                    text = arena_data.get("take", arena_data.get("phase_2", arena_data.get("phase_3", "...")))
                    conf_init = arena_data.get("confidence_initial", 0)
                    conf_final = arena_data.get("confidence_final", conf_init)
                    text_with_meta = f"[Confiance: {conf_final}/5] {text}" if conf_final else text
                    stat_changes = arena_data.get("stat_changes", {})
                    # Build rankings from phase 4 data
                    raw_rankings = arena_data.get("rankings", [])
                    rankings = [
                        AgentRanking(agent_id=r.get("agent_id", ""), score=r.get("score", 0))
                        for r in raw_rankings if isinstance(r, dict)
                    ]
                else:
                    text_with_meta = "[pas de reaction — wh26 non disponible]"
                    stat_changes = {}
                    conf_init = 0
                    conf_final = 0
                    rankings = []
                reactions.append(AgentReaction(
                    agent_id=agent.agent_id, turn=gs.turn, action_id="news_reaction",
                    reaction_text=text_with_meta, stat_changes=stat_changes,
                    phase1_reasoning=arena_data.get("phase_1", "") if arena_data else "",
                    phase2_take=arena_data.get("phase_2", "") if arena_data else "",
                    phase3_revision=arena_data.get("phase_3", "") if arena_data else "",
                    phase4_vote=arena_data.get("phase_4", "") if arena_data else "",
                    confidence_initial=conf_init,
                    confidence_final=conf_final,
                    rankings=rankings,
                    new_color=arena_data.get("new_color") if arena_data else None,
                    is_error=arena_data.get("is_error", False) if arena_data else False,
                ))
            await _broadcast_to_frontend({
                "type": "reactions",
                "data": {
                    "agents": [a.model_dump() for a in gs.agents],
                    "reactions": "\n".join(f"- {r.agent_id}: {r.reaction_text}" for r in reactions),
                    "reactions_detailed": [r.model_dump() for r in reactions],
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

            await _broadcast_to_frontend({
                "type": "indices_update",
                "data": {"indices": new_indices.model_dump(), "decerebration": dec},
            })

            # 4. Strategize
            await _broadcast_to_frontend({"type": "phase", "phase": "strategize_start"})
            gm._event_callback = _ws_callback
            gm.tool_calls_log.clear()

            report = TurnReport(
                turn=gs.turn, chosen_news=last_choice.chosen,
                indices_before=indices_before, indices_after=new_indices,
                agent_reactions=reactions, agents_neutralized=[], agents_promoted=[],
                decerebration=dec, arena_state=arena_global_state,
            )
            last_strategy = await gm.strategize(report, lang=lang)
            print(f"[CHOOSE] strategize done, broadcasting strategy... (clients={len(_ws_clients.get(arena_session_id, []))})")

            await _broadcast_to_frontend({
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
            print(f"[CHOOSE] advancing to turn {gs.turn}, broadcasting turn_update...")
            await _broadcast_to_frontend({"type": "turn_update", "data": {"turn": gs.turn, "max_turns": gs.max_turns}})

            # 6. Check end
            game_over = dec >= 100 or new_indices.esperance_democratique <= 0 or gs.turn > gs.max_turns
            if game_over:
                successes = sum(1 for m in manipulation_history if m["success"])
                total = len(manipulation_history)
                rate = round(successes / total * 100) if total else 0
                if rate >= 80:
                    verdict = "RESPECTEZ MON AUTORITAYYY !"
                elif rate >= 50:
                    verdict = "Pas mal... pour un joueur de ton niveau."
                elif rate >= 30:
                    verdict = "Whatever, c'est ce que je voulais de toute façon..."
                else:
                    verdict = "Screw you, joueur ! Tu as résisté à MON génie."
                await _broadcast_to_frontend({
                    "type": "game_over_reveal",
                    "data": {"manipulation_history": manipulation_history, "score": {"total_turns": total, "successful_manipulations": successes, "rate_percent": rate, "verdict": verdict}},
                })

            if dec >= 100:
                await _broadcast_to_frontend({"type": "end", "data": {"win": True, "dec": round(dec)}})
            elif new_indices.esperance_democratique <= 0:
                await _broadcast_to_frontend({"type": "end", "data": {"lose": True, "dec": round(dec)}})
            elif gs.turn > gs.max_turns:
                await _broadcast_to_frontend({"type": "end", "data": {"draw": True, "dec": round(dec)}})

        except Exception as e:
            import traceback
            traceback.print_exc()
            await _broadcast_to_frontend({"type": "error", "data": {"message": str(e)}})
        finally:
            gm._event_callback = None

    asyncio.create_task(_run())
    return JSONResponse({"status": "accepted"}, status_code=202)


@app.get("/api/start")
async def api_start(
    session_id: str | None = Query(None),
    lang: str = Query("fr", regex="^(fr|en)$"),
):
    global gm, game_state, game_lang, manipulation_history, arena_session_id
    game_lang = lang
    manipulation_history = []

    # Accept external session_id (from relay) or generate one
    arena_session_id = session_id or str(uuid.uuid4())

    if MEMORY_DIR.exists():
        shutil.rmtree(MEMORY_DIR)
    gm = GameMasterAgent()
    game_state = GameState(
        turn=1, max_turns=10,
        indices=GlobalIndices(),
        agents=[a.model_copy() for a in AGENTS_INIT],
        indice_mondial_decerebration=0.0,
    )

    # Connect WS to relay for this session
    await _connect_wh26(arena_session_id)

    # Wait for initial state.global from the swarm (agent names, stats)
    if wh26_connected:
        try:
            envelope = await asyncio.wait_for(wh26_ws_queue.get(), timeout=5.0)
            raw_subject = envelope.get("subject", "") or envelope.get("event", "")
            subject = raw_subject.replace("arena.", "", 1) if raw_subject.startswith("arena.") else raw_subject
            if subject == "state.global":
                swarm_agents = envelope.get("data", {}).get("agents", [])
                if swarm_agents:
                    new_agents = []
                    for i, sa in enumerate(swarm_agents):
                        name = sa.get("name", f"Agent_{i+1}")
                        color = sa.get("political_color", 0.5)
                        # Map political color to personality description
                        if color <= 0.15:
                            pol = "Extrême droite"
                        elif color <= 0.40:
                            pol = "Droite"
                        elif color <= 0.60:
                            pol = "Centre"
                        elif color <= 0.85:
                            pol = "Gauche"
                        else:
                            pol = "Extrême gauche"
                        new_agents.append(AgentState(
                            agent_id=sa.get("id", f"agent_{i+1:02d}"),
                            name=name,
                            personality=f"{pol}. Confiance initiale: {sa.get('confidence', 3)}/5.",
                            country="RU",
                            stats=AgentStats(
                                croyance=50.0 + (color - 0.5) * 40,
                                confiance=sa.get("confidence", 3) * 20.0,
                                richesse=50.0,
                            ),
                            level=AgentLevel.ACTIF,
                        ))
                    game_state.agents = new_agents
                    print(f"[SWARM] Agents loaded from swarm: {[a.name for a in new_agents]}")
            else:
                print(f"[SWARM] Expected state.global, got {subject} — keeping AGENTS_INIT")
        except asyncio.TimeoutError:
            print("[SWARM] Timeout waiting for initial state.global — keeping AGENTS_INIT")

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
    if gs is None:
        return {"turn": 0, "max_turns": 10, "indices": {}, "decerebration": 0, "agents": [], "ended": False}
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

            # Send proposal data immediately (don't wait for images)
            # NOTE: gm_secret is NOT sent to the client — it stays server-side
            # and is recorded in manipulation_history for the end-game reveal.
            await queue.put({
                "type": "proposal",
                "data": {
                    "real": {"text": current_proposal.real.text, "body": current_proposal.real.body, "stat_impact": current_proposal.real.stat_impact},
                    "fake": {"text": current_proposal.fake.text, "body": current_proposal.fake.body, "stat_impact": current_proposal.fake.stat_impact},
                    "satirical": {"text": current_proposal.satirical.text, "body": current_proposal.satirical.body, "stat_impact": current_proposal.satirical.stat_impact},
                    "gm_commentary": current_proposal.gm_commentary,
                },
            })

            # Generate propaganda images in parallel
            session_id = arena_session_id
            img_tasks = [
                generate_propaganda_image(current_proposal.real.text, "real", session_id),
                generate_propaganda_image(current_proposal.fake.text, "fake", session_id),
                generate_propaganda_image(current_proposal.satirical.text, "satirical", session_id),
            ]
            images = await asyncio.gather(*img_tasks, return_exceptions=True)
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
            arena_global_state: dict | None = None

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
                            # Relay sends {"event": "arena.<topic>", "data": ...}
                            raw_subject = envelope.get("subject", "") or envelope.get("event", "")
                            subject = raw_subject.replace("arena.", "", 1) if raw_subject.startswith("arena.") else raw_subject
                            payload = envelope.get("data", {})

                            # Match agent.{uuid}.output — debate content
                            if ".output" in subject and subject.startswith("agent."):
                                agent_id = payload.get("agent_id", "")
                                phase = payload.get("phase", 0)
                                content = payload.get("content", "")
                                agent_name = payload.get("agent_name", "")
                                confidence = payload.get("confidence", 0)
                                existing = agent_outputs.get(agent_id, {})
                                existing["name"] = agent_name
                                existing["agent_id"] = agent_id
                                if phase == 2 or "take" not in existing:
                                    existing["take"] = content
                                if phase == 1:
                                    existing["confidence_initial"] = confidence
                                elif phase == 3:
                                    existing["confidence_final"] = confidence
                                elif phase == 4:
                                    existing["vote"] = content
                                    existing["rankings"] = payload.get("rankings", [])
                                    if payload.get("new_color") is not None:
                                        existing["new_color"] = payload["new_color"]
                                existing[f"phase_{phase}"] = content
                                is_error = payload.get("is_error", False)
                                existing["is_error"] = existing.get("is_error", False) or is_error
                                agent_outputs[agent_id] = existing
                                await queue.put({
                                    "type": "agent_nats",
                                    "data": {
                                        "agent_id": agent_id, "agent_name": agent_name,
                                        "phase": phase, "content": content, "confidence": confidence,
                                        "round": payload.get("round", 0),
                                        "rankings": payload.get("rankings", []),
                                        "new_color": payload.get("new_color"),
                                        "is_error": is_error,
                                    },
                                })
                            # Match agent.{uuid}.status
                            elif ".status" in subject and subject.startswith("agent."):
                                agent_id = subject.split(".")[1] if len(subject.split(".")) >= 3 else ""
                                state = payload.get("state", "")
                                await queue.put({
                                    "type": "agent_nats",
                                    "data": {"agent_id": agent_id, "state": state},
                                })
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
                            elif subject == "state.global":
                                # Store swarm global state for strategize
                                arena_global_state = payload
                                if "agents" in payload:
                                    for swarm_agent in payload["agents"]:
                                        aid = swarm_agent.get("id", "")
                                        agent_outputs[aid] = {
                                            **agent_outputs.get(aid, {}),
                                            "swarm_score": swarm_agent.get("score", 0),
                                            "swarm_status": swarm_agent.get("status", "alive"),
                                        }
                                await queue.put({"type": "phase", "phase": "Arena global state received"})
                                print(f"[WH26] state.global received: {len(payload.get('agents', []))} agents")
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
                print("[WH26] Not connected — wh26 required for agent reactions")
                await queue.put({
                    "type": "phase",
                    "phase": "wh26 non connecte — reactions agents indisponibles",
                })

            # Build AgentReaction list — match by agent_id from swarm
            active_agents = [a for a in gs.agents if not a.is_neutralized]
            for agent in active_agents:
                arena_data = agent_outputs.get(agent.agent_id, {})
                if arena_data:
                    text = arena_data.get("take", arena_data.get("phase_2", arena_data.get("phase_3", "...")))
                    conf_init = arena_data.get("confidence_initial", 0)
                    conf_final = arena_data.get("confidence_final", conf_init)
                    text_with_meta = f"[Confiance: {conf_final}/5] {text}" if conf_final else text
                    stat_changes = arena_data.get("stat_changes", {})
                    raw_rankings = arena_data.get("rankings", [])
                    rankings = [
                        AgentRanking(agent_id=r.get("agent_id", ""), score=r.get("score", 0))
                        for r in raw_rankings if isinstance(r, dict)
                    ]
                else:
                    text_with_meta = "[pas de reaction — wh26 non disponible]"
                    stat_changes = {}
                    conf_init = 0
                    conf_final = 0
                    rankings = []
                reactions.append(AgentReaction(
                    agent_id=agent.agent_id, turn=gs.turn, action_id="news_reaction",
                    reaction_text=text_with_meta, stat_changes=stat_changes,
                    phase1_reasoning=arena_data.get("phase_1", "") if arena_data else "",
                    phase2_take=arena_data.get("phase_2", "") if arena_data else "",
                    phase3_revision=arena_data.get("phase_3", "") if arena_data else "",
                    phase4_vote=arena_data.get("phase_4", "") if arena_data else "",
                    confidence_initial=conf_init,
                    confidence_final=conf_final,
                    rankings=rankings,
                    new_color=arena_data.get("new_color") if arena_data else None,
                    is_error=arena_data.get("is_error", False) if arena_data else False,
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
                arena_state=arena_global_state,
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
