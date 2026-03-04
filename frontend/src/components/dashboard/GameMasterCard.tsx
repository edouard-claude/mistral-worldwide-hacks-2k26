import { createPortal } from "react-dom";
import type { Agent, GameState } from "@/data/gameData";
import type { TurnPhase, TurnResult, GmAgentVision, GmStrategy } from "@/types/ws-events";
import agentGm from "@/assets/agent_gm.png";
import brainSoviet from "@/assets/brain_soviet.png";
import { useLang } from "@/i18n/LanguageContext";
import { tr } from "@/i18n/translations";
import { renderMarkdown } from "@/utils/terminalMarkdown";

interface GameMasterCardProps {
  agents: Agent[];
  gameState: GameState;
  turnPhase: TurnPhase;
  turnResult: TurnResult | null;
  gmVisions: Record<string, GmAgentVision>;
  gmStrategy: GmStrategy | null;
  onClose: () => void;
}

/** Circular gauge component */
function GaugeCircle({ value, label, color }: { value: number; label: string; color: string }) {
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;

  return (
    <div className="flex flex-col items-center">
      <svg width="68" height="68" className="transform -rotate-90">
        <circle cx="34" cy="34" r={radius} fill="none" stroke="hsl(var(--foreground) / 0.1)" strokeWidth="5" />
        <circle
          cx="34" cy="34" r={radius} fill="none"
          stroke={color} strokeWidth="5"
          strokeDasharray={circumference} strokeDashoffset={offset}
          strokeLinecap="butt"
          className="transition-all duration-1000"
        />
      </svg>
      <div className="absolute mt-4 flex flex-col items-center">
        <span className="font-comic text-lg leading-none" style={{ color }}>{value}</span>
      </div>
      <span className="text-[8px] font-heading tracking-widest text-soviet-black/50 mt-1">{label}</span>
    </div>
  );
}

const GameMasterCard = ({ agents, gameState, turnPhase, turnResult, gmVisions, gmStrategy, onClose }: GameMasterCardProps) => {
  const lang = useLang();
  const alive = agents.filter(a => a.alive);
  const sorted = [...alive].sort((a, b) => b.confidence - a.confidence);
  const dominant = sorted[0];

  const hasVisions = Object.keys(gmVisions).length > 0;
  const hasStrategy = gmStrategy !== null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
      onClick={onClose} style={{ animation: "fade-in-up 0.3s ease-out" }}>
      <div className="max-w-2xl w-full mx-4 border-6 border-foreground bg-card text-card-foreground overflow-y-auto max-h-[90vh] flex flex-col"
        onClick={e => e.stopPropagation()}
        style={{ boxShadow: "10px 10px 0px hsl(var(--black))", animation: "slam-in 0.4s ease-out" }}>

        {/* HEADER */}
        <div className="bg-soviet-black p-4 text-center border-b-4 border-primary relative shrink-0">
          <img src={agentGm} alt="Mistralski" className="w-16 h-16 mx-auto mb-1 border-3 border-foreground/40"
            style={{ imageRendering: "pixelated" }} />
          <h2 className="font-comic text-comic-yellow text-3xl tracking-wider">MISTRALSKI</h2>
          <span className="font-heading text-[10px] tracking-widest text-secondary/70">
            {tr("gm.strategicAnalysis", lang)} — {tr("gm.turn", lang)} {gameState.turn}/{gameState.maxTurns}
          </span>
          <button onClick={onClose}
            className="absolute top-2 right-2 text-foreground/60 hover:text-foreground text-lg font-bold w-8 h-8 flex items-center justify-center border-2 border-foreground/30 bg-soviet-black/80 hover:bg-primary transition-colors">
            ✕
          </button>
        </div>

        {/* SCROLLABLE BODY */}
        <div className="overflow-y-auto flex-1 p-5 space-y-5">

          {/* SITUATION ACTUELLE — Index gauges */}
          <div>
            <h3 className="font-heading text-xs tracking-widest text-soviet-black/50 mb-3 flex items-center gap-1.5">
              <img src={brainSoviet} alt="" className="w-4 h-4" />
              {tr("gm.currentSituation", lang)}
            </h3>
            <div className="flex justify-around items-center">
              <div className="relative">
                <GaugeCircle value={gameState.chaosIndex} label={tr("gm.chaos", lang)} color="hsl(var(--red-soviet))" />
              </div>
              <div className="relative">
                <GaugeCircle value={gameState.creduliteIndex} label={tr("gm.credulity", lang)} color="hsl(var(--comic-yellow))" />
              </div>
              <div className="relative">
                <GaugeCircle value={gameState.indiceMondial} label={tr("gm.global", lang)} color="hsl(var(--matrix-green))" />
              </div>
            </div>
            <div className="text-center mt-2 text-[10px] font-heading text-soviet-black/40">
              {alive.length} {tr("gm.agentsAlive", lang)} {agents.length} {tr("gm.total", lang)}
              {dominant && <> — {tr("gameover.dominantAgent", lang)}: <span className="font-bold text-soviet-red-dark">{dominant.name}</span></>}
            </div>
          </div>

          {/* MEMORY — Last turn recap */}
          {turnResult && (
            <div className="border-l-3 pl-3 py-2" style={{ borderColor: "hsl(var(--red-soviet) / 0.3)" }}>
              <div className="text-[11px] font-heading text-soviet-black/70">
                <span className="text-soviet-red font-bold">{tr("gm.lastTurn", lang)}:</span>{" "}
                {turnResult.winner.name} {tr("gm.eliminated2", lang)} {turnResult.loser.name}. {tr("gm.clone", lang)} {turnResult.clone.name} {tr("gm.created", lang)}.
              </div>
            </div>
          )}

          {/* AGENT VISIONS */}
          <div>
            <h3 className="font-heading text-xs tracking-widest text-soviet-black/50 mb-2 flex items-center gap-1.5">
              👁 {hasVisions ? tr("gm.visionTitle", lang) : tr("gm.intuitionTitle", lang)}
            </h3>
            <div className="space-y-2">
              {hasVisions ? (
                Object.values(gmVisions).map(vision => {
                  const agent = agents.find(a => a.id === vision.agent_id || a.name === vision.agent_id);
                  return (
                    <div key={vision.agent_id} className="border-2 border-soviet-black/15 p-3"
                      style={{ boxShadow: "3px 3px 0px hsl(var(--black) / 0.1)" }}>
                      <div className="font-heading text-[11px] font-bold text-soviet-red-dark mb-1.5 flex items-center gap-1.5">
                        <span className="w-2 h-2 bg-soviet-red/60 inline-block" />
                        {agent?.name || vision.agent_id}
                      </div>
                      <div className="text-[12px] text-soviet-black/75 leading-relaxed">
                        {renderMarkdown(vision.content)}
                      </div>
                    </div>
                  );
                })
              ) : (
                alive.map(agent => {
                  const assessment = agent.confidence <= 1 ? tr("gm.nearElim", lang)
                    : agent.confidence >= 4 ? tr("gm.strongDebate", lang)
                    : agent.temperature > 0.7 ? tr("gm.exhausted", lang)
                    : tr("gm.averageProfile", lang);
                  return (
                    <div key={agent.id} className="flex gap-3 items-center border-2 border-soviet-black/10 p-2.5"
                      style={{ boxShadow: "2px 2px 0px hsl(var(--black) / 0.08)" }}>
                      <div className="font-heading text-[11px] font-bold text-soviet-red-dark shrink-0 w-28 truncate">
                        {agent.name}
                      </div>
                      <div className="text-[11px] text-soviet-black/60 italic">{assessment}</div>
                      <span className="ml-auto text-[10px] font-bold text-comic-yellow">{agent.confidence}/5</span>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* STRATEGY */}
          {hasStrategy ? (
            <div className="space-y-3">
              {/* Analysis */}
              <div className="border-2 border-soviet-ocre/50 bg-soviet-ocre/8 p-4" style={{ boxShadow: "3px 3px 0px hsl(var(--black) / 0.15)" }}>
                <h3 className="font-comic text-soviet-ocre-dark text-sm tracking-wider mb-2 flex items-center gap-1.5">
                  ★ {tr("gm.gmAnalysis", lang)}
                </h3>
                <div className="text-[13px] italic leading-relaxed text-soviet-black/80 font-heading">
                  {renderMarkdown(gmStrategy.analysis)}
                </div>
                {gmStrategy.threat_agents.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5 items-center">
                    <span className="text-[10px] font-heading text-soviet-red font-bold">{tr("gm.threats", lang)}:</span>
                    {gmStrategy.threat_agents.map(a => (
                      <span key={a} className="text-[10px] font-heading bg-soviet-red/15 text-soviet-red px-2 py-0.5 border border-soviet-red/30 font-bold">{a}</span>
                    ))}
                  </div>
                )}
                {gmStrategy.weak_spots.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1.5 items-center">
                    <span className="text-[10px] font-heading text-soviet-ocre-dark font-bold">{tr("gm.weakSpots", lang)}:</span>
                    {gmStrategy.weak_spots.map((w, i) => (
                      <span key={i} className="text-[10px] font-heading bg-soviet-ocre/15 text-soviet-ocre-dark px-2 py-0.5 border border-soviet-ocre/30">{w}</span>
                    ))}
                  </div>
                )}
              </div>

              {/* Next turn plan */}
              <div className="border-2 border-soviet-red/40 bg-soviet-red/5 p-4" style={{ boxShadow: "3px 3px 0px hsl(var(--black) / 0.15)" }}>
                <h3 className="font-comic text-soviet-red text-sm tracking-wider mb-2 flex items-center gap-1.5">
                  ☭ {tr("gm.nextTurnPlan", lang)}
                </h3>
                <div className="text-[13px] italic leading-relaxed text-soviet-black/80 font-heading">
                  {renderMarkdown(gmStrategy.next_turn_plan)}
                </div>
              </div>

              {/* Long term goal */}
              {gmStrategy.long_term_goal && (
                <div className="border-2 border-soviet-black/20 bg-soviet-black/3 p-4" style={{ boxShadow: "3px 3px 0px hsl(var(--black) / 0.1)" }}>
                  <h3 className="font-heading text-[11px] tracking-widest text-soviet-black/40 mb-1.5 flex items-center gap-1.5">
                    ⚑ {tr("gm.longTermGoal", lang)}
                  </h3>
                  <div className="text-[12px] italic leading-relaxed text-soviet-black/70">
                    {renderMarkdown(gmStrategy.long_term_goal)}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-6 opacity-50">
              <div className="text-4xl mb-2">☭</div>
              <div className="font-comic text-soviet-black/40 text-sm">{tr("gm.noStrategy", lang)}</div>
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
};

export default GameMasterCard;
