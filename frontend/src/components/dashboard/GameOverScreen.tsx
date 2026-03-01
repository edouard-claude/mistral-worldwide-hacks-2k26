import type { GameState, Agent } from "@/data/gameData";
import { useLang } from "@/i18n/LanguageContext";
import { tr } from "@/i18n/translations";

interface GameOverScreenProps {
  gameState: GameState;
  agents: Agent[];
  onRestart: () => void;
}

const GameOverScreen = ({ gameState, agents, onRestart }: GameOverScreenProps) => {
  const lang = useLang();
  const alive = agents.filter(a => a.alive);
  const topAgent = alive.sort((a, b) => b.conviction - a.conviction)[0];
  const totalScore = gameState.chaosIndex + gameState.creduliteIndex;

  const getVerdict = () => {
    if (totalScore >= 160) return { title: tr("gameover.chaosAbsolute", lang), sub: tr("gameover.chaosAbsoluteSub", lang), icon: "☢️" };
    if (totalScore >= 120) return { title: tr("gameover.totalPropaganda", lang), sub: tr("gameover.totalPropagandaSub", lang), icon: "📡" };
    if (totalScore >= 80) return { title: tr("gameover.majorInstability", lang), sub: tr("gameover.majorInstabilitySub", lang), icon: "⚡" };
    return { title: tr("gameover.partialFailure", lang), sub: tr("gameover.partialFailureSub", lang), icon: "🫤" };
  };

  const verdict = getVerdict();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/95 backdrop-blur-sm"
      style={{ animation: "fade-in-up 0.6s ease-out" }}>
      <div className="max-w-lg w-full mx-4 border-8 border-primary bg-card text-card-foreground"
        style={{ boxShadow: "12px 12px 0px hsl(var(--black))" }}>

        <div className="bg-primary text-primary-foreground p-6 text-center">
          <div className="text-5xl mb-2">{verdict.icon}</div>
          <h1 className="font-comic text-4xl tracking-wider">{verdict.title}</h1>
          <p className="font-heading text-sm mt-1 opacity-80">{verdict.sub}</p>
        </div>

        <div className="p-6 space-y-4">
          <div className="text-center mb-4">
            <span className="font-heading text-xs tracking-widest text-muted-foreground">
              {tr("gameover.finalReport", lang)} — {tr("topbar.turn", lang)} {gameState.turn}/{gameState.maxTurns}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {[
              { label: tr("gameover.chaos", lang), value: gameState.chaosIndex, sub: gameState.chaosLabel, color: "hsl(var(--red-soviet))" },
              { label: tr("gameover.credulity", lang), value: gameState.creduliteIndex, sub: gameState.creduliteLabel, color: "hsl(var(--comic-yellow))" },
            ].map(stat => (
              <div key={stat.label} className="border-4 border-foreground/20 p-3 text-center"
                style={{ boxShadow: "4px 4px 0px hsl(var(--black) / 0.3)" }}>
                <div className="font-heading text-[10px] tracking-widest text-muted-foreground">{stat.label}</div>
                <div className="font-comic text-3xl mt-1" style={{ color: stat.color }}>{stat.value}%</div>
                <div className="font-mono text-[9px] mt-1 italic">{stat.sub}</div>
              </div>
            ))}
          </div>

          <div className="border-4 border-foreground/20 p-3 text-center"
            style={{ boxShadow: "4px 4px 0px hsl(var(--black) / 0.3)" }}>
            <div className="font-heading text-[10px] tracking-widest text-muted-foreground">{tr("gameover.disinfoIndex", lang)}</div>
            <div className="font-comic text-5xl mt-1 text-primary">{gameState.indiceMondial}%</div>
          </div>

          {topAgent && (
            <div className="border-t-4 border-foreground/10 pt-3 text-center">
              <span className="font-heading text-[10px] tracking-widest text-muted-foreground">{tr("gameover.dominantAgent", lang)}</span>
              <div className="font-comic text-lg mt-1">👑 {topAgent.name}</div>
              <div className="font-mono text-[9px] text-muted-foreground">
                {tr("gameover.conviction", lang)} {topAgent.conviction} · {tr("gameover.life", lang)} {topAgent.health} · {alive.length} {tr("gameover.agent", lang)}{alive.length > 1 ? "s" : ""} {tr("gameover.survivors", lang)}{alive.length > 1 ? "s" : ""}
              </div>
            </div>
          )}

          <button onClick={onRestart}
            className="w-full mt-2 py-3 bg-primary text-primary-foreground font-comic text-xl tracking-wider border-4 border-foreground/30 hover:brightness-110 transition-all"
            style={{ boxShadow: "6px 6px 0px hsl(var(--black))" }}>
            {tr("gameover.replay", lang)}
          </button>
        </div>
      </div>
    </div>
  );
};

export default GameOverScreen;
