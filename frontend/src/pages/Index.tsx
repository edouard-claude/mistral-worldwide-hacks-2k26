import { useState, useEffect } from "react";
import TopBar from "@/components/dashboard/TopBar";
import PropagandaPanel from "@/components/dashboard/PropagandaPanel";
import CenterPanel from "@/components/dashboard/CenterPanel";
import SwarmPanel from "@/components/dashboard/SwarmPanel";
import NewsTicker from "@/components/dashboard/NewsTicker";
import GameOverScreen from "@/components/dashboard/GameOverScreen";
import ChaosEventModal from "@/components/dashboard/ChaosEventModal";
import WelcomeScreen from "@/components/dashboard/WelcomeScreen";
import GmTerminal from "@/components/dashboard/GmTerminal";
import { GameProvider } from "@/context/GameProvider";
import { useGame } from "@/hooks/useGame";
import { LanguageProvider } from "@/i18n/LanguageContext";
import { tr } from "@/i18n/translations";

// Inner component that uses GameContext
const GameDashboard = () => {
  const { state, actions } = useGame();
  const {
    debateLines,
    turnPhase,
    lang,
    gameState,
    errorMessage,
    pendingChaosEvent,
    gameOver,
    turnTransition,
  } = state;

  const [gameStarted, setGameStarted] = useState(false);
  const [activeDebateIndex, setActiveDebateIndex] = useState(-1);
  const [visibleLines, setVisibleLines] = useState(0);

  const handleStart = (selectedLang: "fr" | "en") => {
    setGameStarted(true);
    actions.startGame(selectedLang);
  };

  // Auto-play debate lines one by one (from WS, lines arrive progressively)
  useEffect(() => {
    if (turnPhase !== "debating" && turnPhase !== "results") return;
    if (visibleLines >= debateLines.length) return;

    const delay = visibleLines === 0 ? 400 : 1200;
    const timer = setTimeout(() => {
      setVisibleLines(prev => prev + 1);
      setActiveDebateIndex(visibleLines);
    }, delay);

    return () => clearTimeout(timer);
  }, [visibleLines, debateLines.length, turnPhase]);

  // Show new lines as they arrive from WS
  useEffect(() => {
    if (debateLines.length > visibleLines) {
      // New line arrived from backend, trigger show
      const timer = setTimeout(() => {
        setVisibleLines(debateLines.length);
        setActiveDebateIndex(debateLines.length - 1);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [debateLines.length, visibleLines]);

  // Reset when new turn starts
  useEffect(() => {
    if (turnPhase === "select_news" || turnPhase === "proposing") {
      setVisibleLines(0);
      setActiveDebateIndex(-1);
    }
  }, [turnPhase]);

  // Clear active speaker highlight
  useEffect(() => {
    if (activeDebateIndex < 0) return;
    const timer = setTimeout(() => setActiveDebateIndex(-1), 1200);
    return () => clearTimeout(timer);
  }, [activeDebateIndex]);

  if (!gameStarted) {
    return <WelcomeScreen onStart={handleStart} />;
  }

  const effectivePhase = turnPhase === "proposing" || turnPhase === "loading" || turnPhase === "error" ? "select_news" as const : turnPhase;

  return (
    <LanguageProvider value={lang}>
      <div className="h-screen flex flex-col overflow-hidden border-8 border-soviet-red box-border">
        <TopBar
          gameState={gameState}
          turnPhase={effectivePhase}
          onEndTurn={() => { if (turnPhase === "results") actions.nextTurn(); }}
          canEndTurn={turnPhase === "results"}
          gameOver={gameOver}
          onChangeLang={actions.changeLang}
        />

        {errorMessage && (
          <div className="bg-soviet-red text-foreground text-center py-2 px-4 text-sm font-heading">
            ⚠ {errorMessage}
            <button onClick={() => actions.startGame()} className="ml-4 underline font-bold">{tr("index.retry", lang)}</button>
          </div>
        )}

        {(turnPhase === "loading" || turnPhase === "proposing") && (
          <div className="bg-soviet-black text-comic-yellow text-center py-2 px-4 text-sm font-heading tracking-wider"
            style={{ animation: "pulse-glow 1.5s ease-in-out infinite" }}>
            {turnPhase === "loading" ? tr("index.connecting", lang) : tr("index.preparingNews", lang)}
          </div>
        )}

        <div className="flex-1 grid grid-cols-[280px_1fr_280px] gap-4 p-4 overflow-hidden bg-stripes">
          <PropagandaPanel />
          <CenterPanel
            visibleLines={visibleLines}
            activeDebateIndex={activeDebateIndex}
            gmTerminal={<GmTerminal />}
          />
          <SwarmPanel />
        </div>

        <NewsTicker />

        {pendingChaosEvent && (
          <ChaosEventModal event={pendingChaosEvent} onClose={actions.dismissChaosEvent} />
        )}

        {gameOver && (
          <GameOverScreen
            gameState={gameState}
            agents={state.liveAgents}
            onRestart={actions.restartGame}
          />
        )}

        {turnTransition && (
          <div className="fixed inset-0 z-[60] flex items-center justify-center pointer-events-none"
            style={{ animation: "turn-transition 2.5s ease-in-out forwards" }}>
            <div className="absolute inset-0" style={{ backgroundColor: "hsl(var(--black) / 0.85)" }} />
            <div className="relative z-10 text-center" style={{ animation: "slam-in 0.4s ease-out both" }}>
              <div className="relative mx-auto mb-4"
                style={{
                  width: 50, height: 50,
                  clipPath: "polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%)",
                  backgroundColor: "hsl(var(--red-soviet))",
                  filter: "drop-shadow(0 0 20px hsl(var(--red-soviet) / 0.8))",
                  animation: "star-spin 2s linear infinite",
                }} />
              <p className="font-comic text-4xl md:text-5xl tracking-wider"
                style={{
                  color: "hsl(var(--comic-yellow))",
                  textShadow: "3px 3px 0px hsl(var(--red-dark)), 5px 5px 0px hsl(var(--black))",
                }}>
                {tr("topbar.turn", lang)} {gameState.turn + 1}
              </p>
              <p className="text-sm mt-2 tracking-[0.2em] uppercase font-bold"
                style={{ color: "hsl(var(--ocre-gulag))" }}>
                {tr("index.turnTransition", lang)}
              </p>
            </div>
          </div>
        )}
      </div>
    </LanguageProvider>
  );
};

// Main component with GameProvider wrapper
const Index = () => {
  return (
    <GameProvider>
      <GameDashboard />
    </GameProvider>
  );
};

export default Index;
