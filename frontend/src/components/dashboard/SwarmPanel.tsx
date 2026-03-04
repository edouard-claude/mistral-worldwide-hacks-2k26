import { useState, useMemo } from "react";
import type { Agent, DebateLine } from "@/data/gameData";
import { useGame } from "@/hooks/useGame";
import agentKgb from "@/assets/agent_kgb.png";
import agentSabot from "@/assets/agent_sabot.png";
import agentPropa from "@/assets/agent_propa.png";
import agentMoustache from "@/assets/agent_moustache.png";
import AgentDetailModal from "./AgentDetailModal";
import HallOfHeroes from "./HallOfHeroes";
import hallHeroesIcon from "@/assets/hall_heroes_icon.png";
import { useLang } from "@/i18n/LanguageContext";
import { tr } from "@/i18n/translations";
import { AgentSkeletonGrid } from "@/components/skeletons/AgentSkeleton";
import { getAgentColor } from "@/lib/agentColors";

const avatarMap: Record<string, string> = {
  ag1: agentKgb, ag2: agentSabot, ag3: agentPropa, ag4: agentMoustache,
};

function getAvatar(agent: Agent): string {
  if (avatarMap[agent.id]) return avatarMap[agent.id];
  if (agent.status.includes("KGB_TR0LL")) return agentKgb;
  if (agent.status.includes("SABOT_1917")) return agentSabot;
  if (agent.status.includes("PROPA_GUERILLA")) return agentPropa;
  if (agent.status.includes("MOUSTACHE_BOT")) return agentMoustache;
  const portraits = [agentKgb, agentSabot, agentPropa, agentMoustache];
  return portraits[agent.name.length % portraits.length];
}

/** Conviction blocks: 1-5 scale rendered as filled/empty blocks */
function ConvictionBlocks({ value }: { value: number }) {
  const filled = Math.max(1, Math.min(5, Math.round(value)));
  return (
    <span className="inline-flex items-center gap-px">
      {Array.from({ length: 5 }, (_, i) => (
        <span
          key={i}
          className={`inline-block w-2 h-3 border border-soviet-black/40 ${
            i < filled ? "bg-comic-yellow" : "bg-soviet-black/10"
          }`}
        />
      ))}
    </span>
  );
}

/** Temperature heat bar: 0.0 - 1.0 rendered as gradient bar */
function TemperatureBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  // Cold = blue-ish, hot = red
  const hue = Math.round(240 - value * 240); // 240(blue) → 0(red)
  return (
    <div className="flex items-center gap-1 flex-1">
      <div className="flex-1 h-2 bg-soviet-black/10 border border-soviet-black/30 overflow-hidden">
        <div
          className="h-full transition-all duration-700"
          style={{
            width: `${pct}%`,
            background: `linear-gradient(90deg, hsl(${Math.min(hue + 40, 240)}, 70%, 50%), hsl(${hue}, 80%, 45%))`,
          }}
        />
      </div>
    </div>
  );
}

const SwarmPanel = () => {
  const lang = useLang();
  const { state } = useGame();
  const {
    liveAgents: agents,
    debateLines,
    turnResult,
    turnPhase,
    fallenAgents,
    loading,
  } = state;

  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [showHall, setShowHall] = useState(false);

  // Derive active speaker from last debate line
  const { activeSpeaker, activeSpeakerType } = useMemo(() => {
    if (debateLines.length === 0) return { activeSpeaker: null, activeSpeakerType: null };
    const lastLine = debateLines[debateLines.length - 1];
    return {
      activeSpeaker: lastLine.agent,
      activeSpeakerType: lastLine.type as DebateLine["type"],
    };
  }, [debateLines]);

  // Sort agents by debate ranking when available, otherwise by confidence
  const sortedAgents = turnResult?.ranking
    ? [...agents].sort((a, b) => {
        const aIdx = turnResult.ranking.indexOf(a.id);
        const bIdx = turnResult.ranking.indexOf(b.id);
        return (aIdx === -1 ? 999 : aIdx) - (bIdx === -1 ? 999 : bIdx);
      })
    : [...agents].sort((a, b) => b.confidence - a.confidence);

  const getDefaultRank = (agent: Agent): number => {
    return sortedAgents.indexOf(agent) + 1;
  };

  const getPortraitAnimation = (agentName: string) => {
    if (activeSpeaker !== agentName) return {};
    switch (activeSpeakerType) {
      case "attack":
        return {
          animation: 'shake 0.6s ease-in-out',
          boxShadow: '0 0 25px hsl(0 100% 40% / 0.9), 4px 4px 0px hsl(var(--black))',
          border: '4px solid hsl(0, 100%, 40%)',
        };
      case "defense":
        return {
          animation: 'pulse-glow 0.8s ease-in-out',
          boxShadow: '0 0 15px hsl(30 41% 68% / 0.8), 3px 3px 0px hsl(var(--black))',
          border: '4px solid hsl(30, 41%, 68%)',
        };
      case "reaction":
        return {
          animation: 'fade-in-up 0.4s ease-out',
          boxShadow: '0 0 15px hsl(133 100% 50% / 0.5), 3px 3px 0px hsl(var(--black))',
          border: '4px solid hsl(133, 100%, 40%)',
        };
      default:
        return {
          animation: 'pulse-glow 0.6s ease-in-out',
          boxShadow: '0 0 12px hsl(48 100% 50% / 0.6), 3px 3px 0px hsl(var(--black))',
          border: '4px solid hsl(48, 100%, 50%)',
        };
    }
  };

  const isWinner = (name: string) => turnPhase === "results" && turnResult?.winner.name === name;
  const isLoser = (name: string) => turnPhase === "results" && turnResult?.loser.name === name;
  const isClone = (name: string) => turnPhase === "results" && turnResult?.clone.name === name;

  const getRank = (agent: Agent): number => {
    if (!turnResult?.ranking) return getDefaultRank(agent);
    const idx = turnResult.ranking.indexOf(agent.id);
    return idx >= 0 ? idx + 1 : getDefaultRank(agent);
  };

  // Show skeleton when loading agents
  if (loading.agents && agents.length === 0) {
    return (
      <div className="panel-paper flex flex-col overflow-hidden">
        <div className="panel-header-dark">
          <h2 className="font-comic text-comic-yellow text-base tracking-wider">{tr("swarm.title", lang)}</h2>
          <span className="text-[9px] text-secondary font-heading">{tr("swarm.subtitle", lang)}</span>
        </div>
        <div className="p-3 overflow-y-auto flex-1">
          <AgentSkeletonGrid />
        </div>
      </div>
    );
  }

  return (
    <div className="panel-paper flex flex-col overflow-hidden">
      <div className="panel-header-dark">
        <h2 className="font-comic text-comic-yellow text-base tracking-wider">{tr("swarm.title", lang)}</h2>
        <span className="text-[9px] text-secondary font-heading">{tr("swarm.subtitle", lang)}</span>
      </div>

      <div className="p-3 overflow-y-auto flex-1 space-y-3 text-soviet-black">

        {/* SPECTRE POLITIQUE — Horizontal axis with agent markers */}
        {agents.length > 0 && (
          <div className="border-b-3 border-soviet-black/30 pb-2 mb-1">
            <h3 className="font-comic text-center text-xs mb-2">{tr("swarm.spectrum", lang)}</h3>
            <div className="relative px-2">
              {/* Axis line */}
              <div className="h-1 bg-gradient-to-r from-red-600 via-soviet-black/20 to-blue-700 border border-soviet-black/30" />
              {/* Labels */}
              <div className="flex justify-between text-[7px] font-heading font-bold mt-0.5 text-soviet-black/60">
                <span>{tr("swarm.spectrumLeft", lang)}</span>
                <span>{tr("swarm.spectrumRight", lang)}</span>
              </div>
              {/* Agent markers */}
              <div className="relative h-5 mt-0.5">
                {agents.map((agent) => {
                  const pct = agent.politicalColor * 100; // 0=left, 1=right
                  const color = getAgentColor(agent.name);
                  return (
                    <div
                      key={agent.id}
                      className="absolute -translate-x-1/2 transition-all duration-700 cursor-pointer group"
                      style={{ left: `${pct}%`, top: 0 }}
                      onClick={() => setSelectedAgent(agent)}
                      title={agent.name}
                    >
                      <div
                        className="w-3 h-3 border-2 border-soviet-black/80 transition-transform group-hover:scale-150"
                        style={{ backgroundColor: color.hsl, borderRadius: agent.parentId ? "50%" : "0" }}
                      />
                      <span className="absolute -bottom-3 left-1/2 -translate-x-1/2 text-[6px] font-heading font-bold whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">
                        {agent.name.split(" ")[0]}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {sortedAgents.map((agent, i) => {
          const isSpeaking = activeSpeaker === agent.name;
          const portraitStyle = getPortraitAnimation(agent.name);
          const winner = isWinner(agent.name);
          const loser = isLoser(agent.name);
          const clone = isClone(agent.name);
          const rank = getRank(agent);

          return (
            <div
              key={agent.id || `agent-${i}`}
              onClick={() => setSelectedAgent(agent)}
              className={`agent-card-ocre p-3 transition-all duration-300 cursor-pointer hover:brightness-110 ${
                winner ? "border-comic-yellow animate-victory-glow" : ""
              } ${clone ? "border-soviet-matrix animate-clone-spawn" : ""} ${
                loser ? "animate-death-flash" : ""
              } ${isSpeaking ? 'translate-x-[-2px] translate-y-[-2px]' : ''}`}
              style={{
                animation: clone ? undefined : loser ? undefined : winner ? undefined : `fade-in-up 0.4s ease-out ${i * 0.1}s both`,
                boxShadow: winner
                  ? undefined
                  : isSpeaking
                  ? '6px 6px 0px hsl(var(--black) / 0.5)'
                  : '4px 4px 0px hsl(var(--black) / 0.4)',
              }}
            >
              <div className="flex gap-3 mb-2">
                <div className="relative shrink-0">
                  <img
                    src={getAvatar(agent)}
                    alt={agent.name}
                    className="w-16 h-16 object-cover shrink-0 transition-all duration-300"
                    style={{
                      boxShadow: '3px 3px 0px hsl(var(--black))',
                      border: '4px solid hsl(var(--black))',
                      ...portraitStyle,
                      ...(clone ? { border: '4px solid hsl(133, 100%, 40%)' } : {}),
                      ...(loser ? { filter: 'grayscale(1) brightness(0.5)', border: '4px solid hsl(0, 100%, 30%)' } : {}),
                    }}
                  />
                  {isSpeaking && (
                    <div className="absolute -top-2 -right-2 w-5 h-5 flex items-center justify-center text-xs"
                      style={{ animation: 'stamp-appear 0.3s ease-out' }}>
                      {activeSpeakerType === "attack" ? "⚔️" : activeSpeakerType === "defense" ? "🛡️" : "💭"}
                    </div>
                  )}
                  {winner && (
                    <div className="absolute -top-2 -left-2 text-lg animate-skull-drop">👑</div>
                  )}
                  {loser && (
                    <div className="absolute inset-0 flex items-center justify-center animate-skull-drop">
                      <span className="text-2xl">💀</span>
                    </div>
                  )}
                  {clone && (
                    <div className="absolute -bottom-1 -right-1 text-[8px] bg-soviet-matrix text-soviet-black px-1 font-bold"
                      style={{ animation: 'stamp-appear 0.5s ease-out' }}>
                      CLONE
                    </div>
                  )}
                  {rank !== undefined && (
                    <div className="absolute -top-1 -right-1 bg-comic-yellow text-soviet-black font-comic text-[10px] w-5 h-5 flex items-center justify-center border border-soviet-black">
                      {rank}
                    </div>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-1">
                    <div className={`font-heading text-sm font-bold leading-tight transition-colors duration-300 ${
                      isSpeaking ? 'text-soviet-red-dark' : ''
                    } ${winner ? 'text-soviet-ocre-dark' : ''} ${loser ? 'line-through opacity-50' : ''}`}>
                      {agent.name}
                      {isSpeaking && <span className="ml-1 text-[9px] font-mono font-normal text-soviet-red">{tr("swarm.speaking", lang)}</span>}
                    </div>
                  </div>
                  <div className="text-[9px] text-soviet-black/60 italic mt-0.5">{agent.status}</div>
                  {loser && (
                    <span className="inline-block mt-1 text-[9px] bg-soviet-black text-soviet-red px-1.5 py-0.5 font-bold font-heading animate-slam-in">
                      {tr("swarm.eliminatedLabel", lang)}
                    </span>
                  )}
                </div>
              </div>

              {/* STATS: Conviction (blocks 1-5) + Temperature (heat bar) */}
              <div className="space-y-1">
                <div className="flex items-center gap-1">
                  <span className="text-[8px] w-10 shrink-0 font-heading font-bold">{tr("swarm.conviction", lang)}</span>
                  <ConvictionBlocks value={agent.confidence} />
                  <span className="text-[9px] ml-auto font-bold">{agent.confidence}/5</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="text-[8px] w-10 shrink-0 font-heading font-bold">{tr("swarm.temperature", lang)}</span>
                  <TemperatureBar value={agent.temperature} />
                  <span className="text-[9px] w-8 text-right font-bold">{(agent.temperature * 100).toFixed(0)}%</span>
                </div>
              </div>

              {agent.opinion && (
                <div className={`mt-2 speech-bubble text-[9px] transition-all duration-300 ${
                  isSpeaking ? 'scale-105 origin-left' : ''
                }`}>
                  « {agent.opinion} »
                </div>
              )}
            </div>
          );
        })}

        {fallenAgents.length > 0 && (
          <button
            onClick={() => setShowHall(true)}
            className="mt-4 mb-2 mx-auto flex items-center justify-center gap-2 text-[11px] tracking-widest uppercase font-heading font-bold cursor-pointer transition-all hover:scale-105 px-4 py-2 border-2 border-soviet-red/60 bg-soviet-black/10"
            style={{ color: "hsl(var(--red-soviet))" }}
          >
            <img src={hallHeroesIcon} alt="" className="w-7 h-7" style={{ imageRendering: "pixelated" }} />
            {tr("swarm.hallOfHeroes", lang)} ({fallenAgents.length})
          </button>
        )}
      </div>

      {/* Agent Detail Modal */}
      {selectedAgent && (
        <AgentDetailModal
          agent={selectedAgent}
          rank={getRank(selectedAgent)}
          onClose={() => setSelectedAgent(null)}
        />
      )}

      {/* Hall of Heroes */}
      {showHall && (
        <HallOfHeroes
          fallenAgents={fallenAgents}
          onClose={() => setShowHall(false)}
        />
      )}

    </div>
  );
};

export default SwarmPanel;
