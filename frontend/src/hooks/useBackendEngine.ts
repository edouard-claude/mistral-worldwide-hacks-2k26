import { useState, useCallback, useRef, useEffect } from "react";
import type { Agent, DebateLine, GameState, NewsMission } from "@/data/gameData";
import { politicalSpectrum as initialSpectrum } from "@/data/gameData";
import { checkChaosEvent, type ChaosEvent } from "@/data/chaosEvents";
import { fetchApi, streamSSE, type StartResponse, type NewsProposal, type BackendAgent, type BackendIndices } from "@/services/api";
import type { GmTerminalLine } from "@/components/dashboard/GmTerminal";
import { tr } from "@/i18n/translations";
import type { Lang } from "@/i18n/translations";

export type TurnPhase = "loading" | "select_news" | "proposing" | "debating" | "resolving" | "results" | "error";

export interface GmAgentVision {
  agent_id: string;
  content: string; // full vision text from backend
}

export interface GmStrategy {
  analysis: string;
  threat_agents: string[];
  weak_spots: string[];
  next_turn_plan: string;
  long_term_goal: string;
}

export interface FallenAgent {
  agent: Agent;
  killedBy: string;
  turn: number;
  newsTitle: string;
  epitaph: string;
}

export interface TurnResult {
  winner: Agent;
  loser: Agent;
  clone: Agent;
  chaosDelta: number;
  creduliteDelta: number;
  ranking: string[];
}

const chaosLabels: Record<Lang, { max: number; label: string }[]> = {
  fr: [
    { max: 20, label: "Calme suspect" },
    { max: 40, label: "Rumeurs dans les couloirs" },
    { max: 60, label: "Manifestations sporadiques" },
    { max: 80, label: "Ronds-points en feu" },
    { max: 100, label: "ANARCHIE TOTALE" },
  ],
  en: [
    { max: 20, label: "Suspicious calm" },
    { max: 40, label: "Hallway rumors" },
    { max: 60, label: "Sporadic protests" },
    { max: 80, label: "Roundabouts on fire" },
    { max: 100, label: "TOTAL ANARCHY" },
  ],
};

const creduliteLabels: Record<Lang, { max: number; label: string }[]> = {
  fr: [
    { max: 20, label: "Sceptiques aguerris" },
    { max: 40, label: "Vérifient les sources" },
    { max: 60, label: "Partagent sans lire" },
    { max: 80, label: "Gobent tout" },
    { max: 100, label: "LA VÉRITÉ N'EXISTE PLUS" },
  ],
  en: [
    { max: 20, label: "Hardened skeptics" },
    { max: 40, label: "Check their sources" },
    { max: 60, label: "Share without reading" },
    { max: 80, label: "Swallow everything" },
    { max: 100, label: "TRUTH NO LONGER EXISTS" },
  ],
};

function getLabel(value: number, labels: { max: number; label: string }[]): string {
  return labels.find(l => value <= l.max)?.label ?? labels[labels.length - 1].label;
}

function clamp(v: number, min = 0, max = 100) {
  return Math.max(min, Math.min(max, v));
}

function mapAgent(ba: BackendAgent): Agent {
  return {
    id: ba.id,
    name: ba.name,
    avatar: ba.avatar || "🤖",
    health: ba.health ?? 75,
    energy: ba.energy ?? 60,
    conviction: ba.conviction ?? 70,
    selfishness: ba.selfishness ?? 50,
    status: ba.status || ba.name,
    alive: ba.alive !== false,
    opinion: ba.opinion || "",
  };
}

function mapIndices(indices: BackendIndices, decerebration: number, turn: number, maxTurns: number, lang: Lang): GameState {
  const chaosIndex = clamp(indices.rage ?? 15);
  const creduliteIndex = clamp(100 - (indices.credibilite ?? 80));
  const indiceMondial = clamp(Math.round(decerebration ?? 15));
  return {
    turn, maxTurns, indiceMondial, chaosIndex,
    chaosLabel: getLabel(chaosIndex, chaosLabels[lang]),
    creduliteIndex,
    creduliteLabel: getLabel(creduliteIndex, creduliteLabels[lang]),
  };
}

const newsImages = ["news1", "news2", "news3", "news4", "news5", "news6", "news7", "news8", "news9"];
let newsImageIdx = 0;
function nextNewsImage() {
  const img = newsImages[newsImageIdx % newsImages.length];
  newsImageIdx++;
  return img;
}

export function useGameEngine() {
  const langRef = useRef<Lang>("fr");
  const [lang, setLang] = useState<Lang>("fr");
  const [gameState, setGameState] = useState<GameState>({
    turn: 1, maxTurns: 10, indiceMondial: 0, chaosIndex: 0,
    chaosLabel: "Calme suspect", creduliteIndex: 0, creduliteLabel: "Sceptiques aguerris",
  });
  const [liveAgents, setLiveAgents] = useState<Agent[]>([]);
  const [missions, setMissions] = useState<NewsMission[]>([]);
  const [selectedMission, setSelectedMission] = useState<NewsMission | null>(null);
  const [debateLines, setDebateLines] = useState<DebateLine[]>([]);
  const [turnPhase, setTurnPhase] = useState<TurnPhase>("loading");
  const [turnResult, setTurnResult] = useState<TurnResult | null>(null);
  const [politicalSpectrum, setPoliticalSpectrum] = useState(initialSpectrum.map(p => ({ ...p })));
  const [gameOver, setGameOver] = useState(false);
  const [pendingChaosEvent, setPendingChaosEvent] = useState<ChaosEvent | null>(null);
  const [turnTransition, setTurnTransition] = useState(false);
  const [fallenAgents, setFallenAgents] = useState<FallenAgent[]>([]);
  const [gmCommentary, setGmCommentary] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [needsPropose, setNeedsPropose] = useState(false);
  const [gmTerminalLines, setGmTerminalLines] = useState<GmTerminalLine[]>([]);
  const [gmVisions, setGmVisions] = useState<Record<string, GmAgentVision>>({});
  const [gmStrategy, setGmStrategy] = useState<GmStrategy | null>(null);

  const lineIdRef = useRef(0);
  const addTerminalLine = useCallback((type: GmTerminalLine["type"], text: string) => {
    const id = lineIdRef.current++;
    setGmTerminalLines(prev => [...prev, { id, type, text }]);
  }, []);

  const sessionIdRef = useRef("");
  const proposalRef = useRef<NewsProposal | null>(null);
  const gameStateRef = useRef(gameState);
  gameStateRef.current = gameState;

  // ===== PROPOSE NEWS (SSE) =====
  const doPropose = useCallback(() => {
    setTurnPhase("proposing");
    setMissions([]);
    setSelectedMission(null);
    setDebateLines([]);
    setTurnResult(null);
    setIsStreaming(true);
    proposalRef.current = null;
    addTerminalLine("separator", `══ ${tr("engine.tour", langRef.current)} ${gameStateRef.current.turn} — ${tr("engine.propose", langRef.current)} ══`);

    streamSSE(
      `/api/stream/propose?lang=${langRef.current}`,
      (evt) => {
        // Forward intermediate events to terminal
        switch (evt.type) {
          case "phase":
            addTerminalLine("phase", `>> ${evt.data.phase || evt.data}`);
            break;
          case "llm_call":
            addTerminalLine("llm_call", `${tr("engine.llmCall", langRef.current)} #${(evt.data.turn_idx ?? 0) + 1}`);
            break;
          case "tool_call":
            addTerminalLine("tool_call", `TOOL: ${evt.data.tool || "?"}(${JSON.stringify(evt.data.args || {}).slice(0, 80)})`);
            break;
          case "tool_result":
            addTerminalLine("tool_result", String(evt.data.result || evt.data).slice(0, 200));
            break;
          case "llm_text":
            addTerminalLine("llm_text", String(evt.data.text || evt.data));
            break;
          case "vision_update":
            addTerminalLine("vision_update", `VISION ${evt.data.agent_id || ""}: ${evt.data.content || evt.data}`);
            break;
          case "heartbeat":
            break; // ignore
          case "proposal": {
            const proposal: NewsProposal = evt.data.data || evt.data;
            proposalRef.current = proposal;
            setGmCommentary(proposal.gm_commentary || "");
            addTerminalLine("info", `${tr("engine.proposalReceived", langRef.current)} — ${proposal.gm_commentary || ""}`);

            const kinds: Array<{ key: "real" | "fake" | "satirical" }> = [
              { key: "real" },
              { key: "fake" },
              { key: "satirical" },
            ];

            const newMissions: NewsMission[] = kinds.map((k) => {
              const news = proposal[k.key];
              const impact = news.stat_impact || {};
              // Format impact as a short summary
              const impactParts: string[] = [];
              if (impact.rage) impactParts.push(`Chaos ${impact.rage > 0 ? '+' : ''}${impact.rage}`);
              if (impact.credibilite) impactParts.push(`Créd ${impact.credibilite > 0 ? '+' : ''}${impact.credibilite}`);
              const impactLabel = impactParts.join(" · ") || k.key;

              return {
                id: k.key,
                title: news.text,
                description: news.body.split("\n\n")[0] || news.body.slice(0, 200),
                articleText: news.body,
                image: nextNewsImage(),
                backendImage: undefined,
                chaosImpact: impactLabel,
                statImpact: impact,
                selected: false,
                inProgress: false,
                voiceActive: true,
              };
            });

            // Determine which news the GM "recommends" (highest rage + lowest credibilite = most chaotic)
            let bestIdx = 0;
            let bestScore = -Infinity;
            newMissions.forEach((m, i) => {
              const imp = m.statImpact || {};
              const score = (imp.rage || 0) - (imp.credibilite || 0) + (imp.complotisme || 0);
              if (score > bestScore) { bestScore = score; bestIdx = i; }
            });
            newMissions[bestIdx].recommended = true;

            setMissions(newMissions);
            setTurnPhase("select_news");
            break;
          }
          case "images": {
            // Backend sends generated images for each news kind
            const imgData = evt.data.data || evt.data;
            const BASE = "https://nondeficient-radioluminescent-cherry.ngrok-free.dev";
            const hasAny = imgData.real || imgData.fake || imgData.satirical;
            // silent — no terminal line for images
            setMissions(prev => prev.map(m => {
              const url = imgData[m.id];
              if (url) {
                return { ...m, backendImage: `${BASE}${url}` };
              }
              return m;
            }));
            // Also update selectedMission if already selected
            setSelectedMission(prev => {
              if (!prev) return prev;
              const url = imgData[prev.id];
              if (url) return { ...prev, backendImage: `${BASE}${url}` };
              return prev;
            });
            break;
          }
          default:
            // Log unknown events
            if (evt.type !== "result") {
              addTerminalLine("info", `[${evt.type}] ${JSON.stringify(evt.data).slice(0, 150)}`);
            }
            break;
        }
      },
      () => setIsStreaming(false),
      (err) => {
        setErrorMessage(`${tr("engine.errorPropose", langRef.current)} : ${err.message}`);
        setTurnPhase("error");
        setIsStreaming(false);
      },
    );
  }, [addTerminalLine]);

  // Effect to trigger propose when needed
  useEffect(() => {
    if (needsPropose) {
      setNeedsPropose(false);
      doPropose();
    }
  }, [needsPropose, doPropose]);

  // ===== START GAME =====
  const startGame = useCallback(async (newLang?: Lang) => {
    if (newLang) { langRef.current = newLang; setLang(newLang); }
    setTurnPhase("loading");
    setErrorMessage("");
    try {
      const data = await fetchApi<StartResponse>(`/api/start?lang=${langRef.current}`);
      sessionIdRef.current = data.session_id;
      setLiveAgents(data.agents.map(mapAgent));
      const initialIndices = { ...data.indices, rage: 0, credibilite: 100 };
      setGameState(mapIndices(initialIndices, 0, data.turn, data.max_turns, langRef.current));
      setFallenAgents([]);
      setDebateLines([]);
      setTurnResult(null);
      setSelectedMission(null);
      setGameOver(false);
      setGmCommentary("");
      setGmTerminalLines([]);
      setGmVisions({});
      setGmStrategy(null);
      newsImageIdx = 0;
      setNeedsPropose(true);
    } catch (err: any) {
      setErrorMessage(`${tr("engine.errorServer", langRef.current)} : ${err.message}`);
      setTurnPhase("error");
    }
  }, []);

  // ===== SELECT NEWS & CHOOSE (SSE) =====
  const selectNews = useCallback((missionId: string) => {
    if (turnPhase !== "select_news") return;

    const mission = missions.find(m => m.id === missionId);
    if (!mission) return;

    setMissions(prev => prev.map(m => ({
      ...m, inProgress: m.id === missionId, selected: m.id === missionId,
    })));
    setSelectedMission(mission);

    const kind = missionId as "real" | "fake" | "satirical";
    setTurnPhase("debating");
    setDebateLines([]);
    setIsStreaming(true);
    addTerminalLine("separator", `══ ${tr("engine.tour", langRef.current)} ${gameStateRef.current.turn} — ${tr("engine.resolution", langRef.current)} ══`);

    streamSSE(
      `/api/stream/choose?kind=${kind}&lang=${langRef.current}`,
      (evt) => {
        // Forward intermediate events to terminal
        switch (evt.type) {
          case "phase":
            addTerminalLine("phase", `>> ${evt.data.phase || evt.data}`);
            break;
          case "llm_call":
            addTerminalLine("llm_call", `${tr("engine.llmCall", langRef.current)} #${(evt.data.turn_idx ?? 0) + 1}`);
            break;
          case "tool_call":
            addTerminalLine("tool_call", `TOOL: ${evt.data.tool || "?"}(${JSON.stringify(evt.data.args || {}).slice(0, 80)})`);
            break;
          case "tool_result":
            addTerminalLine("tool_result", String(evt.data.result || evt.data).slice(0, 200));
            break;
          case "llm_text":
            addTerminalLine("llm_text", String(evt.data.text || evt.data));
            break;
          case "vision_update":
            addTerminalLine("vision_update", `VISION ${evt.data.agent_id || ""}: ${evt.data.content || evt.data}`);
            if (evt.data.agent_id) {
              setGmVisions(prev => ({
                ...prev,
                [evt.data.agent_id]: { agent_id: evt.data.agent_id, content: String(evt.data.content || evt.data) },
              }));
            }
            break;
          case "heartbeat":
            break;

          case "choice_resolved":
            addTerminalLine("choice_resolved", `GM: ${evt.data.gm_reaction || tr("engine.choiceMade", langRef.current)}`);
            setDebateLines(prev => [...prev, {
              agent: "MISTRALSKI",
              message: evt.data.gm_reaction || tr("engine.choiceMade", langRef.current),
              type: "argument" as const,
            }]);
            break;

          case "agent_nats":
            setDebateLines(prev => [...prev, {
              agent: evt.data.agent_id || "AGENT",
              message: evt.data.take || "...",
              type: "argument" as const,
            }]);
            break;

          case "agent_death":
            setDebateLines(prev => [...prev, {
              agent: "SYSTÈME",
              message: `☠ ${evt.data.agent_id || (langRef.current === "fr" ? "Un agent" : "An agent")} ${tr("engine.agentEliminated", langRef.current)}`,
              type: "attack" as const,
            }]);
            if (evt.data.agent_id) {
              setFallenAgents(prev => [...prev, {
                agent: {
                  id: evt.data.agent_id, name: evt.data.agent_id, avatar: "💀",
                  health: 0, energy: 0, conviction: 0, selfishness: 0,
                  status: "ÉLIMINÉ", alive: false, opinion: "",
                },
                killedBy: evt.data.killer || "le collectif",
                turn: gameStateRef.current.turn,
                newsTitle: mission?.title ?? "",
                epitaph: evt.data.epitaph || `${evt.data.agent_id} est tombé au combat.`,
              }]);
            }
            break;

          case "agent_clone":
            setDebateLines(prev => [...prev, {
              agent: "SYSTÈME",
              message: `🧬 ${evt.data.agent_id || (langRef.current === "fr" ? "Un clone" : "A clone")} ${tr("engine.joinsDebate", langRef.current)}`,
              type: "reaction" as const,
            }]);
            break;

          case "reactions":
            if (evt.data.reactions) {
              setDebateLines(prev => [...prev, {
                agent: "SYSTÈME",
                message: evt.data.reactions,
                type: "reaction" as const,
              }]);
            }
            break;

          case "indices_update":
            if (evt.data.indices) {
              const newIndices = evt.data.indices as BackendIndices;
              const newDec = evt.data.decerebration ?? gameStateRef.current.indiceMondial;
              setGameState(prev => {
                const newState = mapIndices(newIndices, newDec, prev.turn, prev.maxTurns, langRef.current);
                const chaosEvt = checkChaosEvent(prev.chaosIndex, newState.chaosIndex);
                if (chaosEvt) setPendingChaosEvent(chaosEvt);
                return newState;
              });
            }
            break;

          case "strategy":
            addTerminalLine("strategy", `STRATÉGIE: ${evt.data.analysis || evt.data.next_turn_plan || ""}`);
            setGmCommentary(evt.data.analysis || evt.data.next_turn_plan || "");
            setGmStrategy({
              analysis: evt.data.analysis || "",
              threat_agents: evt.data.threat_agents || [],
              weak_spots: evt.data.weak_spots || [],
              next_turn_plan: evt.data.next_turn_plan || "",
              long_term_goal: evt.data.long_term_goal || "",
            });
            break;

          case "turn_update":
            setGameState(prev => ({
              ...prev,
              turn: evt.data.turn ?? prev.turn,
              maxTurns: evt.data.max_turns ?? prev.maxTurns,
            }));
            break;

          case "end":
            setGameOver(true);
            break;

          case "input.waiting":
            addTerminalLine("info", `${tr("engine.waitingNews", langRef.current)} ${evt.data.round ?? "?"})`);
            setTurnPhase("results");
            setTurnTransition(true);
            setTimeout(() => {
              setTurnTransition(false);
              setNeedsPropose(true);
            }, 2500);
            break;

          case "result":
            setTurnPhase("results");
            setPoliticalSpectrum(prev => prev.map(p => ({
              ...p, value: clamp(p.value + Math.floor(Math.random() * 16) - 8),
            })));
            break;

          default:
            if (evt.type !== "result") {
              addTerminalLine("info", `[${evt.type}] ${JSON.stringify(evt.data).slice(0, 150)}`);
            }
            break;
        }
      },
      () => setIsStreaming(false),
      (err) => {
        setErrorMessage(`${tr("engine.errorDebate", langRef.current)} : ${err.message}`);
        setTurnPhase("error");
        setIsStreaming(false);
      },
    );
  }, [turnPhase, missions, addTerminalLine]);

  const startDebate = useCallback(() => {}, []);
  const resolveTurn = useCallback(() => {}, []);

  const nextTurn = useCallback(() => {
    setNeedsPropose(true);
  }, []);

  const restartGame = useCallback(() => {
    startGame();
  }, [startGame]);

  const dismissChaosEvent = useCallback(() => {
    setPendingChaosEvent(null);
  }, []);

  const changeLang = useCallback((newLang: Lang) => {
    langRef.current = newLang;
    setLang(newLang);
  }, []);

  return {
    gameState, liveAgents, missions, selectedMission, debateLines, turnPhase,
    turnResult, politicalSpectrum, gameOver, pendingChaosEvent, fallenAgents,
    gmCommentary, errorMessage, isStreaming, gmTerminalLines, gmVisions, gmStrategy,
    turnTransition, lang, changeLang,
    selectNews, startDebate, resolveTurn, nextTurn, startGame, restartGame, dismissChaosEvent,
  };
}
