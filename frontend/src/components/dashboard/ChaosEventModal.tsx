import type { ChaosEvent } from "@/data/chaosEvents";
import agentGm from "@/assets/agent_gm.png";
import { useLang } from "@/i18n/LanguageContext";
import { tr } from "@/i18n/translations";

interface ChaosEventModalProps {
  event: ChaosEvent;
  onClose: () => void;
}

const ChaosEventModal = ({ event, onClose }: ChaosEventModalProps) => {
  const lang = useLang();
  const isRising = event.direction === "rising";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-background/80"
        onClick={onClose}
        style={{ animation: "fade-in-up 0.3s ease-out" }}
      />

      <div
        className="relative z-10 max-w-2xl w-full panel-paper p-0 overflow-hidden max-h-[90vh] overflow-y-auto"
        style={{ animation: "slam-in 0.5s ease-out" }}
      >
        <div
          className="panel-header-dark py-4 relative"
          style={{
            borderBottomColor: isRising
              ? "hsl(var(--red-soviet))"
              : "hsl(var(--ocre-gulag))",
          }}
        >
          <div className="flex items-center justify-center gap-2 mb-1">
            <div
              className="w-4 h-4"
              style={{
                clipPath:
                  "polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%)",
                backgroundColor: isRising
                  ? "hsl(var(--red-soviet))"
                  : "hsl(var(--ocre-gulag))",
              }}
            />
            <span
              className="text-[10px] tracking-[0.3em] uppercase font-bold"
              style={{
                color: isRising
                  ? "hsl(var(--red-soviet))"
                  : "hsl(var(--ocre-gulag))",
              }}
            >
              {isRising ? tr("chaos.alertChaos", lang) : tr("chaos.situationReport", lang)}
            </span>
            <div
              className="w-4 h-4"
              style={{
                clipPath:
                  "polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%)",
                backgroundColor: isRising
                  ? "hsl(var(--red-soviet))"
                  : "hsl(var(--ocre-gulag))",
              }}
            />
          </div>
          <h2
            className="font-comic text-2xl tracking-wider"
            style={{ color: "hsl(var(--comic-yellow))" }}
          >
            {event.title}
          </h2>
          <p
            className="text-[9px] mt-1 tracking-widest uppercase"
            style={{ color: "hsl(var(--ocre-gulag))" }}
          >
            {event.label}
          </p>
        </div>

        <div className="p-8 space-y-6">
          <div
            className="text-base md:text-lg leading-loose"
            style={{ color: "hsl(var(--black))", fontFamily: "'Courier New', Courier, monospace" }}
          >
            {event.story}
          </div>

          <div className="flex gap-4 items-start">
            <img
              src={agentGm}
              alt="Mistralski"
              className="w-16 h-16 flex-shrink-0"
              style={{
                imageRendering: "pixelated",
                border: "3px solid hsl(var(--black))",
                boxShadow: "3px 3px 0px hsl(var(--red-soviet))",
              }}
            />
            <div className="speech-bubble flex-1">
              <p className="text-base leading-relaxed">
                {event.gmQuote}
              </p>
            </div>
          </div>

          <div className="flex justify-center pt-4">
            <button
              onClick={onClose}
              className="btn-soviet px-10 py-3 text-base tracking-widest"
            >
              {tr("chaos.understood", lang)}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChaosEventModal;
