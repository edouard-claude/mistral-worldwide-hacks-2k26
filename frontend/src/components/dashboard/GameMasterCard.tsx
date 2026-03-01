import { createPortal } from "react-dom";
import type { Agent, GameState } from "@/data/gameData";
import type { TurnPhase, TurnResult, GmAgentVision, GmStrategy } from "@/hooks/useBackendEngine";
import agentGm from "@/assets/agent_gm.png";
import { useLang } from "@/i18n/LanguageContext";
import { tr } from "@/i18n/translations";

interface GameMasterCardProps {
  agents: Agent[];
  gameState: GameState;
  turnPhase: TurnPhase;
  turnResult: TurnResult | null;
  gmVisions: Record<string, GmAgentVision>;
  gmStrategy: GmStrategy | null;
  onClose: () => void;
}

const GameMasterCard = ({ agents, gameState, turnPhase, turnResult, gmVisions, gmStrategy, onClose }: GameMasterCardProps) => {
  const lang = useLang();
  const alive = agents.filter(a => a.alive);
  const sorted = [...alive].sort((a, b) => b.conviction - a.conviction);
  const dominant = sorted[0];
  const avgHealth = Math.round(alive.reduce((s, a) => s + a.health, 0) / (alive.length || 1));
  const avgConviction = Math.round(alive.reduce((s, a) => s + a.conviction, 0) / (alive.length || 1));

  const memoryNotes = [
    turnResult
      ? `${tr("gm.lastTurn", lang)} : ${turnResult.winner.name} ${tr("gm.eliminated2", lang)} ${turnResult.loser.name}. ${tr("gm.clone", lang)} ${turnResult.clone.name} ${tr("gm.created", lang)}.`
      : tr("gm.noDebate", lang),
    `${alive.length} ${tr("gm.agentsAlive", lang)} ${agents.length} ${tr("gm.total", lang)}. ${agents.filter(a => !a.alive).length} ${tr("gm.eliminatedCount", lang)}.`,
    `${tr("gm.avgHealth", lang)} : ${avgHealth}%. ${tr("gm.avgConviction", lang)} : ${avgConviction}%.`,
    dominant ? `${tr("gameover.dominantAgent", lang)} : ${dominant.name} (${lang === "fr" ? "conviction" : "conviction"} ${dominant.conviction}).` : "",
  ].filter(Boolean);

  const hasVisions = Object.keys(gmVisions).length > 0;
  const hasStrategy = gmStrategy !== null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
      onClick={onClose} style={{ animation: "fade-in-up 0.3s ease-out" }}>
      <div className="max-w-2xl w-full mx-4 border-6 border-primary bg-card text-card-foreground overflow-y-auto max-h-[90vh]"
        onClick={e => e.stopPropagation()}
        style={{ boxShadow: "10px 10px 0px hsl(var(--black))", animation: "slam-in 0.4s ease-out" }}>

        <div className="bg-primary text-primary-foreground p-4 text-center border-b-4 border-foreground relative">
          <img src={agentGm} alt="Mistralski" className="w-14 h-14 mx-auto mb-1 border-3 border-primary-foreground/40" style={{ imageRendering: "pixelated" }} />
          <h2 className="font-comic text-3xl tracking-wider">MISTRALSKI</h2>
          <span className="font-heading text-[10px] tracking-widest opacity-70">{tr("gm.strategicAnalysis", lang)} — {tr("gm.turn", lang)} {gameState.turn}/{gameState.maxTurns}</span>
          <button onClick={onClose}
            className="absolute top-2 right-2 text-primary-foreground/60 hover:text-primary-foreground text-lg font-bold w-8 h-8 flex items-center justify-center border-2 border-primary-foreground/30 hover:bg-primary-foreground/10 transition-colors">
            ✕
          </button>
        </div>

        <div className="p-4 space-y-4" style={{ fontFamily: "'Courier New', Courier, monospace" }}>
          <div>
            <h3 className="font-heading text-xs tracking-widest text-soviet-black/60 mb-2 flex items-center gap-1">
              ● {tr("gm.memory", lang)}
            </h3>
            <div className="space-y-1.5">
              {memoryNotes.map((note, i) => (
                <div key={i} className="text-xs text-soviet-black/80 flex gap-2">
                  <span className="text-soviet-red shrink-0">▸</span>
                  <span>{note}</span>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="font-heading text-xs tracking-widest text-soviet-black/60 mb-2 flex items-center gap-1">
              ● {hasVisions ? tr("gm.visionTitle", lang) : tr("gm.intuitionTitle", lang)}
            </h3>
            <div className="space-y-2">
              {hasVisions ? (
                Object.values(gmVisions).map(vision => (
                  <div key={vision.agent_id} className="border-2 border-soviet-black/20 p-2.5"
                    style={{ boxShadow: "2px 2px 0px hsl(var(--black) / 0.15)" }}>
                    <div className="font-heading text-xs font-bold text-soviet-red-dark mb-1">
                      {vision.agent_id}
                    </div>
                    <div className="text-xs text-soviet-black/70 whitespace-pre-wrap leading-relaxed">
                      {vision.content}
                    </div>
                  </div>
                ))
              ) : (
                alive.map(agent => {
                  const fallback = agent.health < 25 ? tr("gm.nearElim", lang)
                    : agent.conviction > 70 ? tr("gm.strongDebate", lang)
                    : agent.energy < 30 ? tr("gm.exhausted", lang)
                    : tr("gm.averageProfile", lang);
                  return (
                    <div key={agent.id} className="border-2 border-soviet-black/20 p-2.5 flex gap-3 items-start"
                      style={{ boxShadow: "2px 2px 0px hsl(var(--black) / 0.15)" }}>
                      <div className="font-heading text-xs font-bold text-soviet-red-dark shrink-0 w-32 truncate">
                        {agent.name}
                      </div>
                      <div className="text-xs text-soviet-black/70">{fallback}</div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {hasStrategy ? (
            <>
              <div className="border-2 border-soviet-ocre/50 bg-soviet-ocre/10 p-3" style={{ boxShadow: "3px 3px 0px hsl(var(--black) / 0.2)" }}>
                <h3 className="font-heading text-xs tracking-widest text-soviet-ocre-dark mb-1 flex items-center gap-1">
                  ★ {tr("gm.gmAnalysis", lang)}
                </h3>
                <p className="text-sm italic leading-relaxed text-soviet-black/80">{gmStrategy.analysis}</p>
                {gmStrategy.threat_agents.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    <span className="text-[10px] font-heading text-soviet-red">{tr("gm.threats", lang)}:</span>
                    {gmStrategy.threat_agents.map(a => (
                      <span key={a} className="text-[10px] font-heading bg-soviet-red/10 text-soviet-red px-1.5 py-0.5 border border-soviet-red/30">{a}</span>
                    ))}
                  </div>
                )}
                {gmStrategy.weak_spots.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    <span className="text-[10px] font-heading text-soviet-ocre-dark">{tr("gm.weakSpots", lang)}:</span>
                    {gmStrategy.weak_spots.map((w, i) => (
                      <span key={i} className="text-[10px] font-heading bg-soviet-ocre/10 text-soviet-ocre-dark px-1.5 py-0.5 border border-soviet-ocre/30">{w}</span>
                    ))}
                  </div>
                )}
              </div>

              <div className="border-2 border-soviet-red/40 bg-soviet-red/5 p-3" style={{ boxShadow: "3px 3px 0px hsl(var(--black) / 0.2)" }}>
                <h3 className="font-heading text-xs tracking-widest text-soviet-red mb-1 flex items-center gap-1">
                  ☭ {tr("gm.nextTurnPlan", lang)}
                </h3>
                <p className="text-sm italic leading-relaxed text-soviet-black/80">{gmStrategy.next_turn_plan}</p>
              </div>

              {gmStrategy.long_term_goal && (
                <div className="border-2 border-soviet-black/30 bg-soviet-black/5 p-3" style={{ boxShadow: "3px 3px 0px hsl(var(--black) / 0.2)" }}>
                  <h3 className="font-heading text-xs tracking-widest text-soviet-black/50 mb-1 flex items-center gap-1">
                    ⚑ {tr("gm.longTermGoal", lang)}
                  </h3>
                  <p className="text-sm italic leading-relaxed text-soviet-black/80">{gmStrategy.long_term_goal}</p>
                </div>
              )}
            </>
          ) : (
            <>
              <div className="border-2 border-soviet-ocre/50 bg-soviet-ocre/10 p-3" style={{ boxShadow: "3px 3px 0px hsl(var(--black) / 0.2)" }}>
                <h3 className="font-heading text-xs tracking-widest text-soviet-ocre-dark mb-1 flex items-center gap-1">
                  ★ {tr("gm.shortTermStrategy", lang)}
                </h3>
                <p className="text-sm italic leading-relaxed text-soviet-black/80">{tr("gm.waitingBackend", lang)}</p>
              </div>
              <div className="border-2 border-soviet-red/40 bg-soviet-red/5 p-3" style={{ boxShadow: "3px 3px 0px hsl(var(--black) / 0.2)" }}>
                <h3 className="font-heading text-xs tracking-widest text-soviet-red mb-1 flex items-center gap-1">
                  ☭ {tr("gm.longTermStrategy", lang)}
                </h3>
                <p className="text-sm italic leading-relaxed text-soviet-black/80">{tr("gm.waitingBackend", lang)}</p>
              </div>
            </>
          )}

          <div className="grid grid-cols-3 gap-2">
            {[
              { label: tr("gm.chaos", lang), value: gameState.chaosIndex, color: "hsl(var(--red-soviet))" },
              { label: tr("gm.credulity", lang), value: gameState.creduliteIndex, color: "hsl(var(--comic-yellow))" },
              { label: tr("gm.global", lang), value: gameState.indiceMondial, color: "hsl(var(--matrix-green))" },
            ].map(stat => (
              <div key={stat.label} className="text-center border-2 border-soviet-black/20 p-2">
                <div className="font-heading text-[10px] tracking-widest text-soviet-black/50">{stat.label}</div>
                <div className="font-comic text-xl" style={{ color: stat.color }}>{stat.value}%</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
};

export default GameMasterCard;
