import { useState } from "react";
import type { NewsMission, GameState, Agent } from "@/data/gameData";
import type { TurnPhase, TurnResult } from "@/hooks/useBackendEngine";
import { Eye } from "lucide-react";
import agentGm from "@/assets/agent_gm.png";
import news1Img from "@/assets/news1.jpg";
import news2Img from "@/assets/news2.jpg";
import news3Img from "@/assets/news3.jpg";
import news4Img from "@/assets/news4.jpg";
import news5Img from "@/assets/news5.jpg";
import news6Img from "@/assets/news6.jpg";
import news7Img from "@/assets/news7.jpg";
import news8Img from "@/assets/news8.jpg";
import news9Img from "@/assets/news9.jpg";
import GameMasterCard from "./GameMasterCard";
import { useLang } from "@/i18n/LanguageContext";
import { tr } from "@/i18n/translations";

const imageMap: Record<string, string> = {
  news1: news1Img, news2: news2Img, news3: news3Img,
  news4: news4Img, news5: news5Img, news6: news6Img,
  news7: news7Img, news8: news8Img, news9: news9Img,
};

import type { GmAgentVision, GmStrategy } from "@/hooks/useBackendEngine";

interface PropagandaPanelProps {
  missions: NewsMission[];
  gameState: GameState;
  onSelectNews: (id: string) => void;
  turnPhase: TurnPhase;
  agents: Agent[];
  turnResult: TurnResult | null;
  gmVisions: Record<string, GmAgentVision>;
  gmStrategy: GmStrategy | null;
}

const PropagandaPanel = ({ missions, gameState, onSelectNews, turnPhase, agents, turnResult, gmVisions, gmStrategy }: PropagandaPanelProps) => {
  const lang = useLang();
  const canSelect = turnPhase === "select_news";
  const [showGameMaster, setShowGameMaster] = useState(false);

  return (
    <div className="panel-paper flex flex-col overflow-hidden">
      <div className="panel-header-dark">
        <div className="flex items-center justify-center gap-2">
          <span className="text-comic-yellow text-lg">🎖️</span>
          <h2 className="font-comic text-comic-yellow text-lg tracking-wider">{tr("propa.title", lang)}</h2>
        </div>
        <span className="text-[10px] text-secondary font-heading">{tr("propa.subtitle", lang)}</span>
      </div>

      <div className="p-3 overflow-y-auto flex-1 space-y-3">
        {/* GM Card */}
        <div
          onClick={() => setShowGameMaster(true)}
          className="agent-card-ocre p-3 cursor-pointer transition-all duration-200 hover:translate-x-[-2px] hover:translate-y-[-2px] hover:animate-[shake_0.4s_ease-in-out_infinite]"
          style={{ boxShadow: "4px 4px 0px hsl(var(--black) / 0.4)" }}
        >
          <div className="flex gap-3 items-center mb-2">
            <img src={agentGm} alt="Mistralski"
              className="w-16 h-16 object-cover shrink-0"
              style={{ boxShadow: "3px 3px 0px hsl(var(--black))", border: "4px solid hsl(var(--black))" }} />
            <div className="flex-1 min-w-0">
              <div className="font-heading text-sm font-bold leading-tight">MISTRALSKI</div>
              <div className="text-[9px] text-soviet-black/60 italic mt-0.5">{tr("propa.strategicAnalysis", lang)} • {tr("topbar.turn", lang)} {gameState.turn}</div>
              <div className="flex items-center gap-1 mt-1 text-[8px] text-soviet-black/40">
                <Eye size={10} /> {tr("propa.clickStrategy", lang)}
              </div>
            </div>
          </div>

          <div className="space-y-1.5">
            <div>
              <div className="flex justify-between text-[9px]">
                <span className="font-heading font-bold text-soviet-red-dark">{tr("propa.chaos", lang)}</span>
                <span className="font-bold text-soviet-red-dark">{gameState.chaosIndex}%</span>
              </div>
              <div className="h-2.5 bg-soviet-black border border-soviet-black w-full mt-0.5">
                <div className="h-full transition-all duration-700" style={{
                  width: `${gameState.chaosIndex}%`,
                  background: 'linear-gradient(90deg, hsl(0 100% 50%), hsl(0 100% 35%))',
                }} />
              </div>
              <div className="text-[7px] text-soviet-black/50 mt-0.5 font-editorial italic">« {gameState.chaosLabel} »</div>
            </div>
            <div>
              <div className="flex justify-between text-[9px]">
                <span className="font-heading font-bold text-soviet-ocre-dark">{tr("propa.credulity", lang)}</span>
                <span className="font-bold text-soviet-ocre-dark">{gameState.creduliteIndex}%</span>
              </div>
              <div className="h-2.5 bg-soviet-black border border-soviet-black w-full mt-0.5">
                <div className="h-full transition-all duration-700" style={{
                  width: `${gameState.creduliteIndex}%`,
                  background: 'linear-gradient(90deg, hsl(40 85% 45%), hsl(40 85% 29%))',
                }} />
              </div>
              <div className="text-[7px] text-soviet-black/50 mt-0.5 font-editorial italic">« {gameState.creduliteLabel} »</div>
            </div>
          </div>
        </div>

        {/* News */}
        <div className="border-t-3 border-soviet-black/30 pt-2">
          <h3 className="font-comic text-center text-xs mb-2">{tr("propa.news", lang)}</h3>
        </div>

        {missions.map((m, index) => (
          <div
            key={m.id}
            className={`border-[4px] transition-all duration-200 ${
              m.inProgress ? "border-soviet-red bg-white" : "border-soviet-black bg-white hover:border-soviet-red-dark"
            } ${!canSelect ? 'opacity-70' : ''}`}
            style={{
              animation: `news-enter 0.4s ease-out ${index * 0.1}s both`,
              boxShadow: m.inProgress
                ? '5px 5px 0px hsl(var(--red-soviet)), 0 0 20px hsl(var(--red-soviet) / 0.2)'
                : '4px 4px 0px hsl(var(--black) / 0.3)',
              transform: m.inProgress ? 'rotate(-0.5deg)' : 'none',
            }}
          >
            <div className="relative overflow-hidden h-24">
              {m.backendImage ? (
                <img src={m.backendImage} alt={m.title}
                  className="w-full h-full object-cover transition-transform duration-300 hover:scale-105"
                  onError={(e) => { e.currentTarget.src = imageMap[m.image]; }} />
              ) : imageMap[m.image] ? (
                <img src={imageMap[m.image]} alt={m.title}
                  className="w-full h-full object-cover transition-transform duration-300 hover:scale-105" />
              ) : (
                <div className="w-full h-full bg-soviet-black/80 animate-pulse flex items-center justify-center">
                  <span className="text-secondary/30 text-[9px] font-heading tracking-wider">{tr("propa.generating", lang)}</span>
                </div>
              )}
              {m.inProgress && (
                <div className="absolute top-0 right-0 stamp text-[11px]"
                  style={{ animation: 'stamp-appear 0.4s ease-out' }}>
                  {tr("propa.inProgress", lang)}
                </div>
              )}
              {m.recommended && !m.inProgress && (
                <div className="absolute top-1 left-1 bg-soviet-red text-foreground text-[8px] font-heading px-1.5 py-0.5 tracking-wider"
                  style={{ animation: 'stamp-appear 0.4s ease-out', boxShadow: '2px 2px 0px hsl(var(--black))' }}>
                  ★ {lang === "fr" ? "CONSEILLÉ PAR LE POLITBURO" : "RECOMMENDED BY THE POLITBURO"}
                </div>
              )}
            </div>

            <div className="p-2">
              <h3 className="text-soviet-red-dark text-[10px] font-heading font-bold leading-tight mb-1.5">
                {m.title}
              </h3>
              <button
                onClick={() => canSelect && onSelectNews(m.id)}
                className={`btn-select-news w-full text-center px-3 py-1.5 text-[11px] font-bold tracking-wider ${
                  !canSelect ? 'cursor-not-allowed' : ''
                }`}
                disabled={!canSelect}
              >
                {m.inProgress ? tr("propa.selected", lang) : tr("propa.select", lang)}
              </button>
            </div>
          </div>
        ))}
      </div>

      {showGameMaster && (
        <GameMasterCard
          agents={agents} gameState={gameState} turnPhase={turnPhase}
          turnResult={turnResult} gmVisions={gmVisions} gmStrategy={gmStrategy}
          onClose={() => setShowGameMaster(false)}
        />
      )}
    </div>
  );
};

export default PropagandaPanel;
