import { useState } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { Agent } from "@/data/gameData";
import type { AgentRoundHistory } from "@/types/ws-events";
import { useGame } from "@/hooks/useGame";
import { useLang } from "@/i18n/LanguageContext";
import { tr } from "@/i18n/translations";
import { renderMarkdown } from "@/utils/terminalMarkdown";
import { getAgentAvatar } from "@/lib/agentAvatars";

const personalities: Record<string, Record<string, { bio: string; trait: string; weakness: string }>> = {
  ag1: {
    fr: {
      bio: "Ancien agent du KGB reconverti en troll professionnel. Maîtrise l'art de la manipulation digitale depuis les années 90.",
      trait: "Charismatique & manipulateur — domine les débats par l'intimidation.",
      weakness: "Excès de confiance. Sous-estime les alliances adverses.",
    },
    en: {
      bio: "Former KGB agent turned professional troll. Master of digital manipulation since the 90s.",
      trait: "Charismatic & manipulative — dominates debates through intimidation.",
      weakness: "Overconfidence. Underestimates opposing alliances.",
    },
  },
  ag2: {
    fr: {
      bio: "Saboteur idéaliste. Croit sincèrement que le chaos mène à un monde meilleur. Végétarien militant.",
      trait: "Prudent & calculateur — optimise sa survie avant tout.",
      weakness: "Manque de conviction. Hésite trop longtemps avant d'agir.",
    },
    en: {
      bio: "Idealistic saboteur. Sincerely believes chaos leads to a better world. Militant vegetarian.",
      trait: "Cautious & calculating — optimizes survival above all.",
      weakness: "Lack of conviction. Hesitates too long before acting.",
    },
  },
  ag3: {
    fr: {
      bio: "Guérillero de la propagande. Prêt à tout pour survivre, même à trahir ses propres principes.",
      trait: "Désespéré & convaincu — sa force vient de son dos au mur.",
      weakness: "Santé fragile. Un mauvais tour et c'est fini.",
    },
    en: {
      bio: "Propaganda guerrilla. Ready to do anything to survive, even betray their own principles.",
      trait: "Desperate & convinced — strength comes from being cornered.",
      weakness: "Fragile health. One bad turn and it's over.",
    },
  },
  ag4: {
    fr: {
      bio: "Bot moustache. Observe, calcule, attend le moment parfait. Ne parle que quand c'est nécessaire.",
      trait: "Observateur & opportuniste — suit le leader pour survivre.",
      weakness: "Pas de loyauté. Change de camp au moindre vent.",
    },
    en: {
      bio: "Mustache bot. Observes, calculates, waits for the perfect moment. Only speaks when necessary.",
      trait: "Observer & opportunist — follows the leader to survive.",
      weakness: "No loyalty. Switches sides at the slightest breeze.",
    },
  },
};

const clonePersonality: Record<string, { bio: string; trait: string; weakness: string }> = {
  fr: {
    bio: "Clone généré à partir d'un agent dominant. Hérite de la personnalité de son créateur mais avec des mutations imprévisibles.",
    trait: "Instable & imprévisible — peut surpasser l'original ou s'effondrer.",
    weakness: "Identité fragile. Cherche encore sa place dans le débat.",
  },
  en: {
    bio: "Clone generated from a dominant agent. Inherits the creator's personality but with unpredictable mutations.",
    trait: "Unstable & unpredictable — may surpass the original or collapse.",
    weakness: "Fragile identity. Still searching for their place in the debate.",
  },
};

function getPersonality(agent: Agent, lang: string) {
  const p = personalities[agent.id];
  if (p) return p[lang] || p["fr"];
  return clonePersonality[lang] || clonePersonality["fr"];
}

// Phase config: icon, color (must contrast on paper bg), label key
const PHASE_CONFIG: Record<number, { icon: string; color: string; labelKey: string }> = {
  1: { icon: "\u{1F9E0}", color: "hsl(133, 60%, 25%)", labelKey: "agent.phase1" },     // brain — dark green
  2: { icon: "\u{1F4E2}", color: "hsl(30, 70%, 35%)", labelKey: "agent.phase2" },      // megaphone — dark amber
  3: { icon: "\u{1F504}", color: "hsl(210, 50%, 40%)", labelKey: "agent.phase3" },      // arrows — steel blue
  4: { icon: "\u{1F5F3}\uFE0F", color: "hsl(0, 60%, 35%)", labelKey: "agent.phase4" }, // ballot box — dark red
};

function ConfidenceBar({ value, max = 5 }: { value: number; max?: number }) {
  const filled = Math.round(value);
  return (
    <span className="inline-flex items-center gap-0.5 ml-1">
      {Array.from({ length: max }, (_, i) => (
        <span key={i} className={`inline-block w-2 h-3.5 border border-soviet-black/20 ${i < filled ? "bg-comic-yellow" : "bg-soviet-black/10"}`} />
      ))}
      <span className="text-[10px] ml-1 text-soviet-black/70 font-bold">{value}/{max}</span>
    </span>
  );
}

function PhaseBlock({
  phaseNum,
  entry,
  pending,
  agentNames,
  lang,
}: {
  phaseNum: number;
  entry?: { content: string; confidence?: number; rankings?: Array<{ agent_id: string; score: number }>; new_color?: number };
  pending: boolean;
  agentNames: Record<string, string>;
  lang: "fr" | "en";
}) {
  const config = PHASE_CONFIG[phaseNum];
  if (!config) return null;

  return (
    <div
      className={`border-l-4 pl-3 py-2.5 my-2 transition-opacity duration-300 ${pending ? "opacity-30" : ""}`}
      style={{ borderColor: config.color, background: `linear-gradient(90deg, ${config.color}08, transparent)` }}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-base">{config.icon}</span>
        <span
          className="text-[10px] px-2 py-0.5 border-2 font-heading tracking-widest font-bold uppercase"
          style={{ borderColor: config.color, color: config.color }}
        >
          {tr(config.labelKey as any, lang)}
        </span>
        {entry?.confidence !== undefined && (
          <span className="text-[10px] text-soviet-black/70 ml-auto flex items-center gap-1 font-bold">
            {tr("agent.confidence", lang)}:
            <ConfidenceBar value={entry.confidence} />
          </span>
        )}
      </div>

      {pending ? (
        <div className="flex items-center gap-1.5 text-soviet-black/40 text-xs italic">
          <span className="inline-block w-1.5 h-3 bg-soviet-black/30" style={{ animation: "typewriter-cursor 0.8s step-end infinite" }} />
          ...
        </div>
      ) : entry ? (
        <div className="text-xs leading-relaxed" style={{ color: "hsl(0 0% 4% / 0.85)" }}>
          {phaseNum === 3 && (
            <span className="text-[9px] px-1.5 py-0.5 border font-heading tracking-wider mr-2 inline-block mb-1"
              style={{ borderColor: "hsl(0 0% 4% / 0.3)", background: "hsl(0 0% 4% / 0.05)", color: "hsl(0 0% 4% / 0.7)" }}>
              REVISED
            </span>
          )}
          {phaseNum === 4 && entry.rankings ? (
            <div className="space-y-1.5">
              <div className="flex gap-3 flex-wrap">
                {entry.rankings
                  .sort((a, b) => a.score - b.score)
                  .map((r) => (
                    <span key={r.agent_id} className="text-xs flex items-center gap-1">
                      <span className="font-comic text-sm" style={{ color: "hsl(0 0% 4%)" }}>#{r.score}</span>
                      <span className="font-heading" style={{ color: "hsl(0 0% 4% / 0.8)" }}>{agentNames[r.agent_id] || r.agent_id}</span>
                    </span>
                  ))}
              </div>
              {entry.new_color !== undefined && (
                <div className="text-[10px] mt-1" style={{ color: "hsl(0 0% 4% / 0.6)" }}>
                  {tr("agent.politicalShift", lang)}: <span className="font-bold" style={{ color: "hsl(0 0% 4% / 0.8)" }}>{entry.new_color.toFixed(2)}</span>
                </div>
              )}
            </div>
          ) : (
            renderMarkdown(entry.content)
          )}
        </div>
      ) : null}
    </div>
  );
}

function RoundBlock({
  roundHistory,
  isCurrent,
  agentNames,
  lang,
}: {
  roundHistory: AgentRoundHistory;
  isCurrent: boolean;
  agentNames: Record<string, string>;
  lang: "fr" | "en";
}) {
  const [open, setOpen] = useState(isCurrent);

  return (
    <div className={`${isCurrent ? "" : "mt-1"}`}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full text-left py-2 hover:opacity-80 transition-opacity"
      >
        {open ? <ChevronDown size={14} className="text-soviet-red/60" /> : <ChevronRight size={14} className="text-soviet-red/60" />}
        <span className="text-xs font-heading tracking-widest text-soviet-red/80 font-bold uppercase">
          {isCurrent ? tr("agent.currentRound", lang) : tr("agent.round", lang)} {roundHistory.round}
        </span>
        <span className="text-[9px] text-soviet-black/40 ml-auto font-heading">
          {Object.keys(roundHistory.phases).length}/4
        </span>
      </button>

      {open && (
        <div className="ml-1">
          {[1, 2, 3, 4].map(phaseNum => {
            const entry = roundHistory.phases[phaseNum];
            const pending = isCurrent && !entry;
            // Only show pending indicator for phases that haven't arrived yet
            // but are expected (i.e., a previous phase exists for this round)
            const hasAnyPhase = Object.keys(roundHistory.phases).length > 0;
            if (!entry && !pending) return null;
            if (!entry && !hasAnyPhase) return null;
            return (
              <PhaseBlock
                key={phaseNum}
                phaseNum={phaseNum}
                entry={entry}
                pending={pending && hasAnyPhase}
                agentNames={agentNames}
                lang={lang}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

interface AgentDetailModalProps {
  agent: Agent;
  rank?: number;
  onClose: () => void;
}

const AgentDetailModal = ({ agent, rank, onClose }: AgentDetailModalProps) => {
  const lang = useLang();
  const { state } = useGame();
  const personality = getPersonality(agent, lang);
  const isClone = agent.id.startsWith("clone_");

  // Get debate history for this agent
  const agentRounds = state.agentHistory[agent.id] || [];
  const hasHistory = agentRounds.length > 0;
  const currentTurn = state.gameState.turn;

  // Sort rounds: current first, then descending
  const sortedRounds = [...agentRounds].sort((a, b) => b.round - a.round);

  // Build agent name lookup for rankings display
  const agentNames: Record<string, string> = {};
  for (const a of state.liveAgents) {
    agentNames[a.id] = a.name;
  }
  for (const f of state.fallenAgents) {
    agentNames[f.agent.id] = f.agent.name;
  }

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
      onClick={onClose} style={{ animation: "fade-in-up 0.3s ease-out" }}>
      <div className="max-w-2xl w-full mx-4 border-6 border-foreground bg-card text-card-foreground max-h-[85vh] flex flex-col"
        onClick={e => e.stopPropagation()}
        style={{ boxShadow: "10px 10px 0px hsl(var(--black))", animation: "slam-in 0.4s ease-out" }}>

        {/* HEADER */}
        <div className="relative bg-soviet-black p-4 border-b-4 border-primary shrink-0">
          <div className="flex gap-4 items-center">
            <img src={getAgentAvatar(agent.name)} alt={agent.name}
              className="w-20 h-20 object-cover border-4 border-foreground"
              style={{ boxShadow: "4px 4px 0px hsl(var(--black))" }} />
            <div>
              <div className="flex items-center gap-2">
                {rank !== undefined && (
                  <span className="bg-comic-yellow text-soviet-black font-comic text-sm px-2 py-0.5">#{rank}</span>
                )}
                {isClone && (
                  <span className="bg-soviet-matrix text-soviet-black font-heading text-[9px] px-1.5 py-0.5 tracking-wider">CLONE</span>
                )}
              </div>
              <h2 className="font-comic text-comic-yellow text-2xl tracking-wider">{agent.name}</h2>
              <div className="text-[10px] text-secondary/80 italic font-heading">{agent.status}</div>
            </div>
          </div>
          <button onClick={onClose}
            className="absolute top-2 right-2 text-foreground/60 hover:text-foreground text-lg font-bold w-8 h-8 flex items-center justify-center border-2 border-foreground/30 bg-soviet-black/80 hover:bg-primary transition-colors">
            ✕
          </button>
        </div>

        {/* SCROLLABLE BODY */}
        <div className="overflow-y-auto flex-1 p-5 space-y-4">

          {/* STATS */}
          <div className="space-y-3">
            {/* Conviction: 1-5 blocks */}
            <div className="flex items-center gap-3">
              <span className="text-xs w-28 shrink-0 font-heading font-bold tracking-wider uppercase text-soviet-black">{tr("agent.confidence", lang)}</span>
              <span className="inline-flex items-center gap-1">
                {Array.from({ length: 5 }, (_, i) => (
                  <span key={i} className={`inline-block w-4 h-5 border-2 border-soviet-black/30 ${
                    i < Math.round(agent.confidence) ? "bg-comic-yellow" : "bg-soviet-black/10"
                  }`} />
                ))}
              </span>
              <span className="text-sm ml-1 font-bold font-heading text-soviet-black">{agent.confidence}/5</span>
            </div>
            {/* Political position: marker on axis */}
            <div className="flex items-center gap-3">
              <span className="text-xs w-28 shrink-0 font-heading font-bold tracking-wider uppercase text-soviet-black">{tr("agent.politicalShift", lang)}</span>
              <div className="flex-1 relative h-4 border-2 border-soviet-black/20 overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-r from-red-600/30 via-soviet-black/5 to-blue-700/30" />
                <div
                  className="absolute top-0 w-1.5 h-full bg-comic-yellow border-x border-soviet-black/50 transition-all duration-700"
                  style={{ left: `${agent.politicalColor * 100}%` }}
                />
              </div>
              <span className="text-sm w-12 text-right font-bold font-heading text-soviet-black">{agent.politicalColor.toFixed(2)}</span>
            </div>
            {/* Temperature: heat bar */}
            <div className="flex items-center gap-3">
              <span className="text-xs w-28 shrink-0 font-heading font-bold tracking-wider uppercase text-soviet-black">{tr("swarm.temperature", lang)}</span>
              <div className="flex-1 h-4 border-2 border-soviet-black/20 overflow-hidden">
                <div
                  className="h-full transition-all duration-700"
                  style={{
                    width: `${agent.temperature * 100}%`,
                    background: `linear-gradient(90deg, hsl(240, 70%, 50%), hsl(${Math.round(240 - agent.temperature * 240)}, 80%, 45%))`,
                  }}
                />
              </div>
              <span className="text-sm w-12 text-right font-bold font-heading text-soviet-black">{(agent.temperature * 100).toFixed(0)}%</span>
            </div>
          </div>

          {/* BIO — always visible */}
          <div className="border-t-2 border-soviet-black/15 pt-3">
            <div className="mb-3">
              <h3 className="font-heading text-sm tracking-widest text-soviet-black/60 mb-1.5 uppercase">{tr("agent.biography", lang)}</h3>
              <p className="text-sm italic leading-relaxed text-soviet-black/80">{personality.bio}</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="border-3 border-soviet-black/20 p-3" style={{ boxShadow: "4px 4px 0px hsl(var(--black) / 0.2)" }}>
                <div className="font-heading text-xs tracking-widest uppercase mb-1" style={{ color: "hsl(30, 70%, 35%)" }}>{tr("agent.trait", lang)}</div>
                <p className="text-sm leading-relaxed text-soviet-black/80">{personality.trait}</p>
              </div>
              <div className="border-3 border-soviet-black/20 p-3" style={{ boxShadow: "4px 4px 0px hsl(var(--black) / 0.2)" }}>
                <div className="font-heading text-xs tracking-widest uppercase mb-1" style={{ color: "hsl(0, 60%, 35%)" }}>{tr("agent.weakness", lang)}</div>
                <p className="text-sm leading-relaxed text-soviet-black/80">{personality.weakness}</p>
              </div>
            </div>
          </div>

          {/* DEBATE HISTORY */}
          {hasHistory ? (
            <div className="border-t-2 border-soviet-black/15 pt-3">
              <h3 className="font-heading text-sm tracking-widest text-soviet-black/60 mb-2 uppercase">
                {tr("agent.debateHistory", lang)}
              </h3>
              {sortedRounds.map(roundH => (
                <RoundBlock
                  key={roundH.round}
                  roundHistory={roundH}
                  isCurrent={roundH.round === currentTurn}
                  agentNames={agentNames}
                  lang={lang}
                />
              ))}
            </div>
          ) : (
            <div className="text-xs text-soviet-black/40 italic text-center py-2">
              {tr("agent.noHistory", lang)}
            </div>
          )}

          {/* CURRENT OPINION */}
          {agent.opinion && (
            <div className="speech-bubble text-[11px]">
              « {agent.opinion} »
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
};

export default AgentDetailModal;
