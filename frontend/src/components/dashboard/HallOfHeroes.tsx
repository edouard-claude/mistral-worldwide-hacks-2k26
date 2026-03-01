import { createPortal } from "react-dom";
import type { FallenAgent } from "@/types/ws-events";
import agentKgb from "@/assets/agent_kgb.png";
import agentSabot from "@/assets/agent_sabot.png";
import agentPropa from "@/assets/agent_propa.png";
import agentMoustache from "@/assets/agent_moustache.png";
import agentGm from "@/assets/agent_gm.png";
import hallHeroesIcon from "@/assets/hall_heroes_icon.png";
import { useLang } from "@/i18n/LanguageContext";
import { tr } from "@/i18n/translations";

const avatarMap: Record<string, string> = {
  ag1: agentKgb, ag2: agentSabot, ag3: agentPropa, ag4: agentMoustache,
};

function getAvatar(agentId: string, agentName: string): string {
  if (avatarMap[agentId]) return avatarMap[agentId];
  if (agentName.includes("KGB_TR0LL")) return agentKgb;
  if (agentName.includes("SABOT_1917")) return agentSabot;
  if (agentName.includes("PROPA_GUERILLA")) return agentPropa;
  if (agentName.includes("MOUSTACHE_BOT")) return agentMoustache;
  const portraits = [agentKgb, agentSabot, agentPropa, agentMoustache];
  return portraits[agentName.length % portraits.length];
}

interface HallOfHeroesProps {
  fallenAgents: FallenAgent[];
  onClose: () => void;
}

const HallOfHeroes = ({ fallenAgents, onClose }: HallOfHeroesProps) => {
  const lang = useLang();

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-background/90" onClick={onClose} />

      <div className="relative z-10 max-w-2xl w-full panel-paper p-0 overflow-hidden max-h-[90vh] flex flex-col"
        style={{ animation: "slam-in 0.5s ease-out" }}>

        <div className="panel-header-dark py-5">
          <div className="flex items-center justify-center gap-3 mb-2">
            <img src={hallHeroesIcon} alt="" className="w-10 h-10" style={{ imageRendering: "pixelated" }} />
            <span className="text-[10px] tracking-[0.3em] uppercase font-bold" style={{ color: "hsl(var(--red-soviet))" }}>
              {tr("hall.memorial", lang)}
            </span>
            <img src={hallHeroesIcon} alt="" className="w-10 h-10 -scale-x-100" style={{ imageRendering: "pixelated" }} />
          </div>
          <h2 className="font-comic text-3xl tracking-wider" style={{ color: "hsl(var(--comic-yellow))" }}>
            {tr("hall.title", lang)}
          </h2>
          <p className="text-[10px] mt-1 tracking-widest uppercase" style={{ color: "hsl(var(--ocre-gulag))" }}>
            {tr("hall.subtitle", lang)}
          </p>
        </div>

        <div className="p-6 overflow-y-auto flex-1 space-y-5">
          {fallenAgents.length === 0 ? (
            <div className="text-center py-8">
              <div className="flex justify-center mb-4">
                <img src={agentGm} alt="Mistralski" className="w-16 h-16"
                  style={{ imageRendering: "pixelated", border: "3px solid hsl(var(--black))" }} />
              </div>
              <div className="speech-bubble inline-block">
                <p className="text-base">{tr("hall.nobodyDead", lang)}</p>
              </div>
            </div>
          ) : (
            <>
              {fallenAgents.map((fallen, i) => (
                <div key={`${fallen.agent.id}-${fallen.turn}`}
                  className="agent-card-ocre p-4 relative"
                  style={{ animation: `fade-in-up 0.4s ease-out ${i * 0.1}s both`, opacity: 0.9 }}>

                  <div className="absolute top-2 right-2 stamp text-[10px]"
                    style={{ animation: "stamp-appear 0.5s ease-out" }}>R.I.P.</div>

                  <div className="flex gap-4 items-start mb-3">
                    <div className="relative shrink-0">
                      <img src={getAvatar(fallen.agent.id, fallen.agent.name)} alt={fallen.agent.name}
                        className="w-16 h-16 object-cover"
                        style={{
                          imageRendering: "pixelated", border: "4px solid hsl(var(--black))",
                          boxShadow: "3px 3px 0px hsl(var(--red-soviet))", filter: "grayscale(0.7) sepia(0.3)",
                        }} />
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-2xl opacity-60">&#9760;</span>
                      </div>
                    </div>

                    <div className="flex-1 min-w-0">
                      <h3 className="font-heading text-base font-bold leading-tight">{fallen.agent.name}</h3>
                      <div className="text-[10px] mt-1 space-y-0.5" style={{ color: "hsl(var(--black) / 0.6)" }}>
                        <div className="font-heading">
                          <span className="font-bold" style={{ color: "hsl(var(--red-soviet))" }}>
                            {tr("hall.eliminatedLabel", lang)}
                          </span>{" "}
                          {tr("hall.eliminatedAt", lang)} {fallen.turn}
                        </div>
                        <div>{tr("hall.executedBy", lang)} <span className="font-bold">{fallen.killedBy}</span></div>
                        <div className="italic text-[9px]">{tr("hall.during", lang)} : « {fallen.newsTitle.slice(0, 60)}... »</div>
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-4 mb-3 text-[9px]">
                    {[
                      { label: tr("swarm.life", lang), value: fallen.agent.health },
                      { label: tr("agent.conviction", lang), value: fallen.agent.conviction },
                      { label: tr("agent.selfishness", lang), value: fallen.agent.selfishness },
                    ].map(s => (
                      <div key={s.label} className="flex items-center gap-1">
                        <span className="font-heading font-bold">{s.label}:</span>
                        <span>{s.value}</span>
                      </div>
                    ))}
                  </div>

                  <div className="font-editorial italic text-sm leading-relaxed"
                    style={{ color: "hsl(var(--black) / 0.8)", borderLeft: "3px solid hsl(var(--red-soviet))", paddingLeft: "12px" }}>
                    {fallen.epitaph}
                  </div>
                </div>
              ))}

              <div className="flex gap-4 items-start pt-2">
                <img src={agentGm} alt="Mistralski" className="w-14 h-14 flex-shrink-0"
                  style={{ imageRendering: "pixelated", border: "3px solid hsl(var(--black))", boxShadow: "3px 3px 0px hsl(var(--red-soviet))" }} />
                <div className="speech-bubble flex-1">
                  <p className="text-sm leading-relaxed">
                    {fallenAgents.length === 1
                      ? tr("hall.comment1", lang)
                      : fallenAgents.length <= 3
                      ? `${fallenAgents.length} ${tr("hall.commentFew", lang)}`
                      : `${fallenAgents.length} ${tr("hall.commentMany", lang)}`
                    }
                  </p>
                </div>
              </div>
            </>
          )}

          <div className="flex justify-center pt-3">
            <button onClick={onClose} className="btn-soviet px-8 py-2 text-sm tracking-widest">
              {tr("hall.close", lang)}
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
};

export default HallOfHeroes;
