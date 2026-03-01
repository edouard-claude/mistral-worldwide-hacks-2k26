import { useState, useCallback, useRef } from "react";
import type { Agent, DebateLine, GameState, NewsMission } from "@/data/gameData";
import {
  agents as initialAgents,
  newsMissions as initialMissions,
  politicalSpectrum as initialSpectrum,
  generateMissions,
} from "@/data/gameData";
import { checkChaosEvent, type ChaosEvent } from "@/data/chaosEvents";

// Debate message templates per type
const attackMessages = [
  (attacker: string, target: string) => `${target}, suis-moi ou tu disparais au prochain tour.`,
  (attacker: string, target: string) => `${target} est faible. Il faut l'éliminer.`,
  (attacker: string, target: string) => `Je n'ai pas besoin de ${target}. Qui vote avec moi ?`,
  (attacker: string, target: string) => `${target}, ta conviction ne vaut rien face à mon influence.`,
];

const defenseMessages = [
  (agent: string) => `Je refuse. Cette news est trop risquée pour MA survie.`,
  (agent: string) => `Vous voulez me sacrifier ? Jamais. Je me défends.`,
  (agent: string) => `C'est un piège. Je ne tomberai pas dedans.`,
  (agent: string) => `Mon égoïsme me dit de survivre, pas de vous suivre.`,
];

const argumentMessages = [
  (agent: string, news: string) => `Cette news va amplifier le chaos. Parfait pour nous cacher.`,
  (agent: string, news: string) => `Si on pousse \"${news}\", le risque est calculé.`,
  (agent: string, news: string) => `Stratégiquement, c'est la meilleure option pour survivre.`,
  (agent: string, news: string) => `Le rapport conviction/risque est en notre faveur.`,
];

const reactionMessages = [
  (agent: string, leader: string) => `...je vote avec ${leader}. Désolé pour les autres.`,
  (agent: string, leader: string) => `${leader} a raison. Je suis le mouvement.`,
  (agent: string, leader: string) => `Pas le choix. Je m'aligne sur ${leader}.`,
  (agent: string, leader: string) => `Hmm... ok, ${leader}, je te fais confiance. Cette fois.`,
];

const deathMessages = [
  (agent: string) => `${agent} a été ÉLIMINÉ. Sa conviction n'a pas suffi.`,
  (agent: string) => `${agent} est MORT. Le débat l'a détruit.`,
  (agent: string) => `R.I.P. ${agent}. Le collectif l'a sacrifié.`,
];

const epitaphs = [
  (loser: string, winner: string) => `${loser} pensait pouvoir résister à ${winner}. L'orgueil est un poison lent... mais efficace.`,
  (loser: string, winner: string) => `Trop égoïste pour s'allier, trop faible pour dominer. ${loser} a joué seul et a perdu seul.`,
  (loser: string, winner: string) => `${winner} n'a eu aucune pitié. ${loser} a été broyé par la mécanique du débat.`,
  (loser: string, winner: string) => `${loser} croyait en sa conviction. ${winner} croyait en la victoire. Devinez qui avait raison.`,
  (loser: string, winner: string) => `Le collectif a parlé : ${loser} était le maillon faible. ${winner} a simplement accéléré l'inévitable.`,
  (loser: string, winner: string) => `${loser} est tombé non pas par manque de courage, mais par excès de naïveté face à ${winner}.`,
];

const replicateMessages = [
  (winner: string, clone: string) => `${winner} se RÉPLIQUE → ${clone} rejoint le débat !`,
  (winner: string, clone: string) => `Victoire de ${winner}. Son clone ${clone} prend position.`,
];

const chaosLabels = [
  { max: 20, label: "Calme suspect" },
  { max: 40, label: "Rumeurs dans les couloirs" },
  { max: 60, label: "Manifestations sporadiques" },
  { max: 80, label: "Ronds-points en feu" },
  { max: 100, label: "ANARCHIE TOTALE" },
];

const creduliteLabels = [
  { max: 20, label: "Sceptiques aguerris" },
  { max: 40, label: "Vérifient les sources" },
  { max: 60, label: "Partagent sans lire" },
  { max: 80, label: "Gobent tout" },
  { max: 100, label: "LA VÉRITÉ N'EXISTE PLUS" },
];

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function clamp(v: number, min = 0, max = 100) {
  return Math.max(min, Math.min(max, v));
}

function getLabel(value: number, labels: typeof chaosLabels): string {
  return labels.find(l => value <= l.max)?.label ?? labels[labels.length - 1].label;
}

// Clone names
const cloneNames = [
  "CLONE_ALPHA", "CLONE_BETA", "CLONE_GAMMA", "CLONE_DELTA",
  "REPLICA_01", "REPLICA_02", "GHOST_X", "SHADOW_Y",
  "NEO_TROLL", "CYBER_COMRADE", "RED_GHOST", "IRON_CLONE",
];

export type TurnPhase = "select_news" | "debating" | "resolving" | "results";

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
  ranking: string[]; // agent names sorted by debate score (best first)
}

export function useGameEngine() {
  const [gameState, setGameState] = useState<GameState>({
    turn: 1,
    maxTurns: 10,
    indiceMondial: 15,
    chaosIndex: 15,
    chaosLabel: "Calme suspect",
    creduliteIndex: 20,
    creduliteLabel: "Sceptiques aguerris",
  });

  const [liveAgents, setLiveAgents] = useState<Agent[]>(initialAgents.map(a => ({ ...a, alive: true })));
  const [missions, setMissions] = useState<NewsMission[]>(initialMissions.map(m => ({ ...m })));
  const [selectedMission, setSelectedMission] = useState<NewsMission | null>(null);
  const [debateLines, setDebateLines] = useState<DebateLine[]>([]);
  const [turnPhase, setTurnPhase] = useState<TurnPhase>("select_news");
  const [turnResult, setTurnResult] = useState<TurnResult | null>(null);
  const [politicalSpectrum, setPoliticalSpectrum] = useState(initialSpectrum.map(p => ({ ...p })));
  const [gameOver, setGameOver] = useState(false);
  const [pendingChaosEvent, setPendingChaosEvent] = useState<ChaosEvent | null>(null);
  const [fallenAgents, setFallenAgents] = useState<FallenAgent[]>([]);

  const cloneCounter = useRef(0);
  const usedNewsRef = useRef<Set<number>>(new Set());
  

  const selectNews = useCallback((missionId: string) => {
    if (turnPhase !== "select_news") return;
    const mission = missions.find(m => m.id === missionId);
    if (!mission) return;

    setMissions(prev => prev.map(m => ({
      ...m,
      inProgress: m.id === missionId,
      selected: m.id === missionId,
    })));
    setSelectedMission(mission);
  }, [turnPhase, missions]);

  const startDebate = useCallback(() => {
    if (!selectedMission || turnPhase !== "select_news") return;
    setTurnPhase("debating");
    setDebateLines([]);

    const alive = liveAgents.filter(a => a.alive);
    if (alive.length < 2) return;

    // Calculate each agent's "debate score" = conviction + random + energy bonus
    const scores = alive.map(a => ({
      agent: a,
      score: a.conviction + Math.random() * 40 + (a.energy / 5) - (a.selfishness / 10),
    }));
    scores.sort((a, b) => b.score - a.score);

    const leader = scores[0].agent;
    const loser = scores[scores.length - 1].agent;
    const others = scores.slice(1, -1).map(s => s.agent);

    // Generate debate lines
    const lines: DebateLine[] = [];

    // Leader opens with argument
    lines.push({
      agent: leader.name,
      message: pick(argumentMessages)(leader.name, selectedMission.title.slice(0, 30)),
      type: "argument",
    });

    // Loser defends
    lines.push({
      agent: loser.name,
      message: pick(defenseMessages)(loser.name),
      type: "defense",
    });

    // Others react
    for (const other of others) {
      if (Math.random() > 0.4) {
        lines.push({
          agent: other.name,
          message: pick(reactionMessages)(other.name, leader.name),
          type: "reaction",
        });
      } else {
        lines.push({
          agent: other.name,
          message: pick(argumentMessages)(other.name, selectedMission.title.slice(0, 30)),
          type: "argument",
        });
      }
    }

    // Leader attacks loser
    lines.push({
      agent: leader.name,
      message: pick(attackMessages)(leader.name, loser.name),
      type: "attack",
    });

    // Loser final defense
    lines.push({
      agent: loser.name,
      message: pick(defenseMessages)(loser.name),
      type: "defense",
    });

    setDebateLines(lines);

    // Store result for resolution
    const chaosArrows = (selectedMission.chaosImpact.match(/↑/g) || []).length;
    const chaosDelta = chaosArrows * (5 + Math.floor(Math.random() * 8));
    const creduliteDelta = 3 + Math.floor(Math.random() * 10);

    // Create clone of winner
    const cloneId = `clone_${cloneCounter.current++}`;
    const cloneName = pick(cloneNames.filter(n => !alive.some(a => a.name === n))) || `CLONE_${cloneCounter.current}`;
    const clone: Agent = {
      ...leader,
      id: cloneId,
      name: cloneName,
      health: 50 + Math.floor(Math.random() * 30),
      energy: 40 + Math.floor(Math.random() * 30),
      conviction: leader.conviction - 10 + Math.floor(Math.random() * 20),
      selfishness: leader.selfishness + Math.floor(Math.random() * 15),
      status: `Clone de ${leader.name}`,
      opinion: `Je suis la continuité de ${leader.name}.`,
      alive: true,
    };

    setTurnResult({
      winner: leader,
      loser,
      clone,
      chaosDelta,
      creduliteDelta,
      ranking: scores.map(s => s.agent.id),
    });
  }, [selectedMission, turnPhase, liveAgents]);

  const resolveTurn = useCallback(() => {
    if (!turnResult || turnPhase !== "debating") return;
    setTurnPhase("resolving");

    const { winner, loser, clone, chaosDelta, creduliteDelta } = turnResult;

    // Record fallen agent
    setFallenAgents(prev => [...prev, {
      agent: { ...loser },
      killedBy: winner.name,
      turn: gameState.turn,
      newsTitle: selectedMission?.title ?? "Inconnu",
      epitaph: pick(epitaphs)(loser.name, winner.name),
    }]);

    // Add resolution lines
    setDebateLines(prev => [
      ...prev,
      { agent: "SYSTÈME", message: pick(deathMessages)(loser.name), type: "attack" as const },
      { agent: "SYSTÈME", message: pick(replicateMessages)(winner.name, clone.name), type: "reaction" as const },
    ]);

    // Update agents: kill loser, add clone, update winner stats
    setLiveAgents(prev => {
      const updated = prev.map(a => {
        if (a.id === loser.id) return { ...a, alive: false, status: "ÉLIMINÉ", health: 0 };
        if (a.id === winner.id) return {
          ...a,
          health: clamp(a.health - 5 + Math.floor(Math.random() * 10)),
          energy: clamp(a.energy - 10),
          conviction: clamp(a.conviction + 5),
          status: `Dominant — tour ${gameState.turn}`,
          opinion: `J'ai gagné. ${loser.name} est mort.`,
        };
        // Others lose some energy
        return {
          ...a,
          health: clamp(a.health - Math.floor(Math.random() * 8)),
          energy: clamp(a.energy - 5),
          opinion: a.name === clone.name ? a.opinion : `${loser.name} est tombé... qui sera le prochain ?`,
        };
      });
      // Remove dead, add clone, keep 4 max
      const alive = updated.filter(a => a.alive);
      return [...alive, clone].slice(0, 4);
    });

    // Update game indices
    setGameState(prev => {
      const newChaos = clamp(prev.chaosIndex + chaosDelta);
      const newCredulite = clamp(prev.creduliteIndex + creduliteDelta);
      const newMondial = clamp(Math.round((newChaos + newCredulite) / 2));
      const newTurn = prev.turn + 1;

      // Check for chaos event
      const evt = checkChaosEvent(prev.chaosIndex, newChaos);
      if (evt) {
        setPendingChaosEvent(evt);
      }

      return {
        ...prev,
        turn: newTurn,
        chaosIndex: newChaos,
        chaosLabel: getLabel(newChaos, chaosLabels),
        creduliteIndex: newCredulite,
        creduliteLabel: getLabel(newCredulite, creduliteLabels),
        indiceMondial: newMondial,
      };
    });

    // Shift political spectrum randomly
    setPoliticalSpectrum(prev => prev.map(p => ({
      ...p,
      value: clamp(p.value + Math.floor(Math.random() * 16) - 8),
    })));

    // Check game over
    if (gameState.turn + 1 >= gameState.maxTurns) {
      setGameOver(true);
    }

    setTurnPhase("results");
  }, [turnResult, turnPhase, gameState]);

  const nextTurn = useCallback(() => {
    const { missions: freshMissions, usedIndices } = generateMissions(3, usedNewsRef.current);
    usedNewsRef.current = usedIndices;

    setTurnPhase("select_news");
    setDebateLines([]);
    setTurnResult(null);
    setSelectedMission(null);
    setMissions(freshMissions);
  }, []);

  const restartGame = useCallback(() => {
    setPendingChaosEvent(null);
    setGameState({
      turn: 1,
      maxTurns: 10,
      indiceMondial: 15,
      chaosIndex: 15,
      chaosLabel: "Calme suspect",
      creduliteIndex: 20,
      creduliteLabel: "Sceptiques aguerris",
    });
    setLiveAgents(initialAgents.map(a => ({ ...a, alive: true })));
    usedNewsRef.current = new Set();
    const { missions: freshMissions, usedIndices } = generateMissions(3, usedNewsRef.current);
    usedNewsRef.current = usedIndices;
    setMissions(freshMissions);
    setSelectedMission(null);
    setDebateLines([]);
    setTurnPhase("select_news");
    setTurnResult(null);
    setPoliticalSpectrum(initialSpectrum.map(p => ({ ...p })));
    setGameOver(false);
    setFallenAgents([]);
    cloneCounter.current = 0;
  }, []);

  const dismissChaosEvent = useCallback(() => {
    setPendingChaosEvent(null);
  }, []);

  return {
    gameState,
    liveAgents,
    missions,
    selectedMission,
    debateLines,
    turnPhase,
    turnResult,
    politicalSpectrum,
    gameOver,
    pendingChaosEvent,
    fallenAgents,
    selectNews,
    startDebate,
    resolveTurn,
    nextTurn,
    restartGame,
    dismissChaosEvent,
  };
}
