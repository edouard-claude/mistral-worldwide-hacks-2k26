import { useEffect, useRef } from "react";
import type { ReactNode } from "react";
import { useGame } from "@/hooks/useGame";
import brainSoviet from "@/assets/brain_soviet.png";
import { getAgentColor } from "@/lib/agentColors";
import news1Img from "@/assets/news1.jpg";
import news2Img from "@/assets/news2.jpg";
import news3Img from "@/assets/news3.jpg";
import news4Img from "@/assets/news4.jpg";
import news5Img from "@/assets/news5.jpg";
import news6Img from "@/assets/news6.jpg";
import news7Img from "@/assets/news7.jpg";
import news8Img from "@/assets/news8.jpg";
import news9Img from "@/assets/news9.jpg";
import { useLang } from "@/i18n/LanguageContext";
import { tr } from "@/i18n/translations";

const imageMap: Record<string, string> = {
  news1: news1Img, news2: news2Img, news3: news3Img,
  news4: news4Img, news5: news5Img, news6: news6Img,
  news7: news7Img, news8: news8Img, news9: news9Img,
};

interface CenterPanelProps {
  visibleLines: number;
  activeDebateIndex: number;
  gmTerminal?: ReactNode;
}

const CenterPanel = ({ visibleLines, activeDebateIndex, gmTerminal }: CenterPanelProps) => {
  const lang = useLang();
  const { state } = useGame();
  const {
    debateLines,
    gameState,
    turnPhase,
    turnResult,
    selectedMission,
  } = state;

  const isGmPhase = turnPhase === "proposing" || (turnPhase === "debating" && debateLines.length === 0);
  const debateScrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new debate lines appear
  useEffect(() => {
    if (debateScrollRef.current && visibleLines > 0) {
      debateScrollRef.current.scrollTop = debateScrollRef.current.scrollHeight;
    }
  }, [visibleLines, debateLines.length]);

  return (
    <div className="flex flex-col gap-2 overflow-hidden">
      {/* Top: News article detail OR placeholder */}
      <div className="panel-paper shrink-0 flex flex-col overflow-hidden" style={{ maxHeight: "40%" }}>
        <div className="panel-header-dark flex items-center justify-center gap-2 shrink-0">
          <span className="font-comic text-comic-yellow text-lg">★</span>
          <h2 className="font-comic text-comic-yellow text-base tracking-wider">
            {selectedMission ? tr("center.selectedArticle", lang) : tr("center.specialEdition", lang)}
          </h2>
          <span className="font-comic text-comic-yellow text-lg">★</span>
        </div>

        {selectedMission ? (
          <div className="flex-1 min-h-0 overflow-y-auto">
            <div className="relative">
              {selectedMission.backendImage ? (
                <img src={selectedMission.backendImage} alt={selectedMission.title}
                  className="w-full h-48 object-cover"
                  style={{ animation: 'fade-in-up 0.4s ease-out' }}
                  onError={(e) => { e.currentTarget.src = imageMap[selectedMission.image]; }} />
              ) : (
                <img src={imageMap[selectedMission.image]} alt={selectedMission.title}
                  className="w-full h-48 object-cover"
                  style={{ animation: 'fade-in-up 0.4s ease-out' }} />
              )}
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-soviet-black/90 to-transparent p-4 pt-12">
                <div className="flex items-center gap-2 mb-1">
                  <span className="bg-soviet-red text-foreground text-[9px] font-heading px-2 py-0.5 tracking-wider">
                    {tr("center.exclusive", lang)}
                  </span>
                  <span className="text-comic-yellow font-comic text-[11px]">{selectedMission.chaosImpact}</span>
                </div>
                <h3 className="font-heading text-foreground text-lg font-bold leading-tight" style={{
                  textShadow: '2px 2px 0px hsl(var(--black))'
                }}>
                  {selectedMission.title}
                </h3>
              </div>
            </div>

            <div className="p-4 space-y-3">
              <div className="flex items-center justify-between border-b-2 border-soviet-black/20 pb-2">
                <div className="text-[9px] text-soviet-black/50 font-heading tracking-wider">
                  {tr("center.newsSource", lang)} — {tr("topbar.turn", lang)} {gameState.turn}
                </div>
                <div className="text-[9px] text-soviet-red-dark font-heading">
                  {tr("center.verified", lang)}
                </div>
              </div>

              <p className="font-heading text-soviet-black text-sm italic leading-relaxed border-l-4 border-soviet-red pl-3 tracking-wide">
                {selectedMission.description}
              </p>

              {selectedMission.articleText.split('\n\n').map((paragraph, i) => (
                <p key={i} className="text-soviet-black/85 text-[13px] leading-relaxed tracking-wide"
                  style={{ fontFamily: "'Courier New', Courier, monospace", animation: `fade-in-up 0.3s ease-out ${i * 0.05}s both` }}>
                  {paragraph}
                </p>
              ))}

              <div className="border-t-2 border-soviet-black/15 pt-2 mt-4">
                <p className="text-[8px] text-soviet-black/40 italic text-center">
                  {tr("center.disclaimer", lang)}
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center p-8">
            <div className="text-center space-y-4" style={{ animation: 'fade-in-up 0.5s ease-out' }}>
              <div className="text-6xl">📰</div>
              <div className="font-comic text-soviet-black/40 text-xl">{tr("center.noNewsSelected", lang)}</div>
              <p className="text-soviet-black/30 text-[11px] font-editorial italic max-w-sm">
                {tr("center.noNewsSub", lang)}
              </p>
              <div className="text-8xl opacity-5">☭</div>
            </div>
          </div>
        )}
      </div>

      {/* Unified block: GM reflection OR Agent debate */}
      <div className="panel-feed flex-1 min-h-0 flex flex-col">
        <div className="panel-feed-header py-1.5 px-3 text-left flex items-center justify-between shrink-0">
          <h3 className="font-comic text-comic-yellow text-sm tracking-wider">
            {debateLines.length > 0 && !isGmPhase
              ? tr("center.agentDebate", lang)
              : <><img src={brainSoviet} alt="" className="inline-block w-5 h-5 mr-1 -mt-0.5" /> {tr("center.gmReflection", lang)}</>}
          </h3>
          <span className="text-[10px] text-secondary/80 font-heading">
            {tr("topbar.turn", lang)} {gameState.turn} —
            {turnPhase === "select_news" && ` ${tr("center.selectANews", lang)}`}
            {(turnPhase === "debating" && isGmPhase) && ` ${tr("center.gmThinking", lang)}`}
            {(turnPhase === "debating" && !isGmPhase) && ` ${tr("center.debateOngoing", lang)}`}
            {turnPhase === "resolving" && ` ${tr("center.resolution", lang)}`}
            {turnPhase === "results" && ` ${tr("center.results", lang)}`}
          </span>
        </div>

        <div ref={debateScrollRef} className="flex-1 min-h-0 overflow-y-auto">
          {gmTerminal}

          <div className="p-3 space-y-2 font-mono text-[11px]">
            {turnPhase === "select_news" && debateLines.length === 0 && !isGmPhase && (
              <div className="text-center py-1">
                <span className="text-[9px] font-heading text-soviet-red/30 tracking-[0.1em]">{tr("center.selectNewsPrompt", lang)}</span>
              </div>
            )}

            {debateLines.slice(0, visibleLines).map((line, i) => {
              const isActive = i === activeDebateIndex;
              const isSystem = line.agent === "SYSTÈME";
              const isMistralski = line.agent === "MISTRALSKI";
              const agentColor = (!isSystem && !isMistralski) ? getAgentColor(line.agent) : null;

              return (
                <div
                  key={i}
                  className={`flex gap-2 transition-all duration-300 ${isActive ? 'translate-x-1' : ''} ${
                    isSystem ? 'animate-slam-in' : ''
                  } ${isMistralski ? 'border-l-2 pl-2' : ''}`}
                  style={{
                    borderColor: isMistralski ? "hsl(var(--red-soviet))" : agentColor ? agentColor.hsl : undefined,
                    borderLeftWidth: agentColor ? "2px" : undefined,
                    paddingLeft: agentColor ? "8px" : undefined,
                    animation: isSystem ? undefined
                      : line.type === "attack" ? 'debate-line-attack 0.5s ease-out both'
                      : line.type === "defense" ? 'debate-line-defense 0.4s ease-out both'
                      : 'fade-in-up 0.4s ease-out both',
                  }}
                >
                  <span className={`font-bold shrink-0 px-1.5 border-2 text-[10px] transition-all duration-300 ${
                    isMistralski ? "border-soviet-red bg-soviet-red/20 text-soviet-red"
                    : isSystem ? "border-soviet-red/60 bg-soviet-red/10 text-soviet-red/80"
                    : ""
                  } ${isActive ? 'scale-110' : ''}`}
                    style={agentColor ? {
                      borderColor: agentColor.hsl,
                      backgroundColor: `${agentColor.hsl.replace(')', ' / 0.15)')}`,
                      color: agentColor.hsl,
                    } : undefined}
                  >
                    {isMistralski ? "☭ MISTRALSKI" : line.agent}
                  </span>
                  <span className={`transition-all duration-300 ${
                    isMistralski ? "text-soviet-red/90 font-bold italic"
                    : isSystem ? "text-soviet-red/70 font-bold"
                    : "text-foreground/80"
                  } ${isActive ? 'font-bold' : ''}`}
                    style={agentColor ? { color: `${agentColor.hsl.replace(')', ' / 0.85)')}` } : undefined}
                  >
                    {isMistralski ? <img src={brainSoviet} alt="" className="inline-block w-4 h-4 mr-1 -mt-0.5" /> : isSystem ? "⚠️ " : line.type === "attack" ? "⚔ " : line.type === "defense" ? "◆ " : "▸ "}
                    {line.message}
                  </span>
                </div>
              );
            })}

            {turnPhase === "debating" && (
              <div className="flex items-center gap-1 text-soviet-red/40">
                <span className="inline-block w-1.5 h-4 bg-soviet-red/50" style={{ animation: 'typewriter-cursor 0.8s step-end infinite' }} />
                <span className="text-[9px] italic font-heading tracking-wider">
                  {isGmPhase ? tr("center.gmAnalyzing", lang) : tr("center.agentPreparing", lang)}
                </span>
              </div>
            )}

            {turnPhase === "results" && turnResult && (
              <div className="border-t-2 border-soviet-red/30 pt-2 mt-2 space-y-1">
                <div className="text-soviet-red text-[10px] font-heading">
                  {tr("center.turnResult", lang)} : {turnResult.winner.name} {tr("center.dominates", lang)} — {turnResult.loser.name} {tr("center.eliminated", lang)}
                </div>
                <div className="text-secondary/50 text-[9px]">
                  Chaos +{turnResult.chaosDelta} | {tr("propa.credulity", lang)} +{turnResult.creduliteDelta}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CenterPanel;
