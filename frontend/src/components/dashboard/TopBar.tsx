import type { GameState } from "@/data/gameData";
import type { TurnPhase } from "@/types/ws-events";
import type { Lang } from "@/i18n/translations";
import { useLang } from "@/i18n/LanguageContext";
import { tr } from "@/i18n/translations";

interface TopBarProps {
  gameState: GameState;
  turnPhase: TurnPhase;
  onEndTurn: () => void;
  canEndTurn: boolean;
  gameOver: boolean;
  onChangeLang: (lang: Lang) => void;
}

const TopBar = ({ gameState, turnPhase, onEndTurn, canEndTurn, gameOver, onChangeLang }: TopBarProps) => {
  const lang = useLang();
  const buttonLabel = (() => {
    if (gameOver) return tr("topbar.btn.gameOver", lang);
    switch (turnPhase) {
      case "select_news": return tr("topbar.btn.launchDebate", lang);
      case "debating": return tr("topbar.btn.debating", lang);
      case "resolving": return tr("topbar.btn.resolving", lang);
      case "results": return tr("topbar.btn.nextTurn", lang);
    }
  })();

  return (
    <header className="bg-soviet-red-dark border-b-[6px] border-soviet-black flex items-center px-5 h-[64px] shrink-0 gap-4 relative overflow-hidden">
      <div className="absolute inset-0 opacity-10" style={{
        background: 'repeating-linear-gradient(135deg, transparent, transparent 20px, hsl(var(--black)) 20px, hsl(var(--black)) 22px)'
      }} />

      <div className="shrink-0 flex items-center gap-3 relative z-10">
        <span className="text-4xl" style={{ filter: 'drop-shadow(3px 3px 0px hsl(var(--black)))' }}>☭</span>
        <div>
          <h1 className="font-comic text-comic-yellow text-2xl leading-tight" style={{
            textShadow: "3px 3px 0px hsl(var(--black)), -1px -1px 0px hsl(var(--black))",
            letterSpacing: '0.06em',
          }}>
            GAME OF CLAW
          </h1>
          <p className="text-[9px] text-foreground/60 tracking-[0.3em] leading-none font-heading">
            {tr("topbar.department", lang)}
          </p>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center gap-4 relative z-10">
        <div className="border-4 border-soviet-black bg-soviet-black px-4 py-1.5 flex items-center gap-2" style={{
          boxShadow: '4px 4px 0px hsl(var(--ocre-dark))'
        }}>
          <span className="text-[10px] text-secondary font-heading tracking-wider">{tr("topbar.turn", lang)}</span>
          <span className="font-comic text-comic-yellow text-2xl leading-none">{gameState.turn}</span>
          <span className="text-foreground/40 text-xs">/{gameState.maxTurns}</span>
        </div>

        <div className="flex-1 max-w-sm">
          <div className="text-[9px] text-foreground/70 tracking-wider mb-1 text-center font-heading">
            {tr("topbar.decerebration", lang)}
          </div>
          <div className="w-full h-5 bg-soviet-black border-4 border-soviet-black relative" style={{
            boxShadow: 'inset 0 0 10px hsl(var(--red-soviet) / 0.3)'
          }}>
            <div
              className="h-full transition-all duration-700"
              style={{
                width: `${gameState.indiceMondial}%`,
                background: `linear-gradient(90deg, hsl(var(--ocre-gulag)) 0%, hsl(var(--red-soviet)) 60%, hsl(0 100% 50%) 100%)`,
                animation: 'pulse-glow 2s ease-in-out infinite',
              }}
            />
            <span className="absolute inset-0 flex items-center justify-center font-comic text-foreground text-sm" style={{
              textShadow: '1px 1px 2px hsl(var(--black))'
            }}>
              {gameState.indiceMondial}%
            </span>
          </div>
        </div>
      </div>

      <div className="shrink-0 flex items-center gap-3 relative z-10">
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => onChangeLang("fr")}
            className={`stamp cursor-pointer transition-all text-[9px] px-2 py-0.5 ${lang === "fr" ? "opacity-100 scale-110" : "opacity-40 hover:opacity-70"}`}
            style={{ transform: `rotate(-5deg) ${lang === "fr" ? "scale(1.1)" : ""}`, borderColor: lang === "fr" ? "hsl(var(--red-soviet))" : undefined }}
          >
            FR
          </button>
          <button
            onClick={() => onChangeLang("en")}
            className={`stamp cursor-pointer transition-all text-[9px] px-2 py-0.5 ${lang === "en" ? "opacity-100 scale-110" : "opacity-40 hover:opacity-70"}`}
            style={{ transform: `rotate(4deg) ${lang === "en" ? "scale(1.1)" : ""}`, borderColor: lang === "en" ? "hsl(var(--red-soviet))" : undefined }}
          >
            EN
          </button>
        </div>

        <button
          className={`btn-soviet px-5 py-2.5 tracking-wider font-comic text-lg transition-opacity ${
            !canEndTurn || gameOver ? 'opacity-50 cursor-not-allowed' : ''
          }`}
          style={{ fontSize: '1rem' }}
          onClick={onEndTurn}
          disabled={!canEndTurn || gameOver}
        >
          {buttonLabel}
        </button>
      </div>
    </header>
  );
};

export default TopBar;
