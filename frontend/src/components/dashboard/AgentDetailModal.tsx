import { createPortal } from "react-dom";
import type { Agent } from "@/data/gameData";
import agentKgb from "@/assets/agent_kgb.png";
import agentSabot from "@/assets/agent_sabot.png";
import agentPropa from "@/assets/agent_propa.png";
import agentMoustache from "@/assets/agent_moustache.png";
import { useLang } from "@/i18n/LanguageContext";
import { tr } from "@/i18n/translations";

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

const personalities: Record<string, Record<string, { bio: string; trait: string; weakness: string }>> = {
  ag1: {
    fr: {
      bio: "Ancien agent du KGB reconverti en troll professionnel. Maîtrise l'art de la manipulation digitale depuis les années 90.",
      trait: "Charismatique & manipulateur — domine les débats par l'intimidation.",
      weakness: "Excès de confiance. Sous-estime les alliances adverses.",
    },
    en: {
      bio: "Former KGB agent turned professional troll. Master of digital manipulation since the 90s.",
      trait: "Charismatic & manipulative — dominates debates through intimidation.",
      weakness: "Overconfidence. Underestimates opposing alliances.",
    },
  },
  ag2: {
    fr: {
      bio: "Saboteur idéaliste. Croit sincèrement que le chaos mène à un monde meilleur. Végétarien militant.",
      trait: "Prudent & calculateur — optimise sa survie avant tout.",
      weakness: "Manque de conviction. Hésite trop longtemps avant d'agir.",
    },
    en: {
      bio: "Idealistic saboteur. Sincerely believes chaos leads to a better world. Militant vegetarian.",
      trait: "Cautious & calculating — optimizes survival above all.",
      weakness: "Lack of conviction. Hesitates too long before acting.",
    },
  },
  ag3: {
    fr: {
      bio: "Guérillero de la propagande. Prêt à tout pour survivre, même à trahir ses propres principes.",
      trait: "Désespéré & convaincu — sa force vient de son dos au mur.",
      weakness: "Santé fragile. Un mauvais tour et c'est fini.",
    },
    en: {
      bio: "Propaganda guerrilla. Ready to do anything to survive, even betray their own principles.",
      trait: "Desperate & convinced — strength comes from being cornered.",
      weakness: "Fragile health. One bad turn and it's over.",
    },
  },
  ag4: {
    fr: {
      bio: "Bot moustache. Observe, calcule, attend le moment parfait. Ne parle que quand c'est nécessaire.",
      trait: "Observateur & opportuniste — suit le leader pour survivre.",
      weakness: "Pas de loyauté. Change de camp au moindre vent.",
    },
    en: {
      bio: "Mustache bot. Observes, calculates, waits for the perfect moment. Only speaks when necessary.",
      trait: "Observer & opportunist — follows the leader to survive.",
      weakness: "No loyalty. Switches sides at the slightest breeze.",
    },
  },
};

const clonePersonality: Record<string, { bio: string; trait: string; weakness: string }> = {
  fr: {
    bio: "Clone généré à partir d'un agent dominant. Hérite de la personnalité de son créateur mais avec des mutations imprévisibles.",
    trait: "Instable & imprévisible — peut surpasser l'original ou s'effondrer.",
    weakness: "Identité fragile. Cherche encore sa place dans le débat.",
  },
  en: {
    bio: "Clone generated from a dominant agent. Inherits the creator's personality but with unpredictable mutations.",
    trait: "Unstable & unpredictable — may surpass the original or collapse.",
    weakness: "Fragile identity. Still searching for their place in the debate.",
  },
};

function getPersonality(agent: Agent, lang: string) {
  const p = personalities[agent.id];
  if (p) return p[lang] || p["fr"];
  return clonePersonality[lang] || clonePersonality["fr"];
}

interface AgentDetailModalProps {
  agent: Agent;
  rank?: number;
  onClose: () => void;
}

const AgentDetailModal = ({ agent, rank, onClose }: AgentDetailModalProps) => {
  const lang = useLang();
  const personality = getPersonality(agent, lang);
  const isClone = agent.id.startsWith("clone_");

  const dangerLevelKey = agent.health < 30 ? "agent.critical" : agent.health < 50 ? "agent.high" : agent.health < 75 ? "agent.moderate" : "agent.low";
  const dangerLevel = tr(dangerLevelKey as any, lang);
  const dangerColor = agent.health < 30 ? "hsl(var(--red-soviet))" : agent.health < 50 ? "hsl(var(--comic-yellow))" : agent.health < 75 ? "hsl(var(--ocre-dark))" : "hsl(var(--matrix-green))";

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
      onClick={onClose} style={{ animation: "fade-in-up 0.3s ease-out" }}>
      <div className="max-w-2xl w-full mx-4 border-6 border-foreground bg-card text-card-foreground"
        onClick={e => e.stopPropagation()}
        style={{ boxShadow: "10px 10px 0px hsl(var(--black))", animation: "slam-in 0.4s ease-out" }}>

        <div className="relative bg-soviet-black p-4 border-b-4 border-primary">
          <div className="flex gap-4 items-center">
            <img src={getAvatar(agent)} alt={agent.name}
              className="w-20 h-20 object-cover border-4 border-foreground"
              style={{ boxShadow: "4px 4px 0px hsl(var(--black))" }} />
            <div>
              <div className="flex items-center gap-2">
                {rank !== undefined && (
                  <span className="bg-comic-yellow text-soviet-black font-comic text-sm px-2 py-0.5">#{rank}</span>
                )}
                {isClone && (
                  <span className="bg-soviet-matrix text-soviet-black font-heading text-[9px] px-1.5 py-0.5 tracking-wider">CLONE</span>
                )}
              </div>
              <h2 className="font-comic text-comic-yellow text-2xl tracking-wider">{agent.name}</h2>
              <div className="text-[10px] text-secondary/80 italic font-heading">{agent.status}</div>
            </div>
          </div>
          <button onClick={onClose}
            className="absolute top-2 right-2 text-foreground/60 hover:text-foreground text-lg font-bold w-8 h-8 flex items-center justify-center border-2 border-foreground/30 bg-soviet-black/80 hover:bg-primary transition-colors">
            ✕
          </button>
        </div>

        <div className="p-5 space-y-4" style={{ fontFamily: "'Courier New', Courier, monospace" }}>
          <div>
            <h3 className="font-heading text-xs tracking-widest text-muted-foreground mb-1">{tr("agent.biography", lang)}</h3>
            <p className="text-sm italic leading-relaxed">{personality.bio}</p>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="border-2 border-foreground/20 p-2.5" style={{ boxShadow: "3px 3px 0px hsl(var(--black) / 0.2)" }}>
              <div className="font-heading text-[10px] tracking-widest text-comic-yellow">{tr("agent.trait", lang)}</div>
              <p className="text-xs mt-1">{personality.trait}</p>
            </div>
            <div className="border-2 border-foreground/20 p-2.5" style={{ boxShadow: "3px 3px 0px hsl(var(--black) / 0.2)" }}>
              <div className="font-heading text-[10px] tracking-widest text-primary">{tr("agent.weakness", lang)}</div>
              <p className="text-xs mt-1">{personality.weakness}</p>
            </div>
          </div>

          <div>
            <h3 className="font-heading text-xs tracking-widest text-muted-foreground mb-2">{tr("agent.stats", lang)}</h3>
            <div className="space-y-2">
              {[
                { label: tr("agent.life", lang), value: agent.health, color: "hsl(var(--red-soviet))" },
                { label: tr("agent.energy", lang), value: agent.energy, color: "hsl(var(--matrix-green))" },
                { label: tr("agent.conviction", lang), value: agent.conviction, color: "hsl(var(--ocre-dark))" },
                { label: tr("agent.selfishness", lang), value: agent.selfishness, color: "hsl(48, 100%, 40%)" },
              ].map(stat => (
                <div key={stat.label} className="flex items-center gap-2">
                  <span className="text-xs w-24 shrink-0 font-heading font-bold">{stat.label}</span>
                  <div className="flex-1 h-3.5 bg-foreground/10 border border-foreground/20">
                    <div className="h-full transition-all duration-700" style={{ width: `${stat.value}%`, backgroundColor: stat.color }} />
                  </div>
                  <span className="text-xs w-8 text-right font-bold">{stat.value}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between border-t-2 border-foreground/10 pt-3">
            <span className="font-heading text-xs tracking-widest text-muted-foreground">{tr("agent.dangerLevel", lang)}</span>
            <span className="font-comic text-base px-3 py-1 border-2" style={{ color: dangerColor, borderColor: dangerColor }}>
              {dangerLevel}
            </span>
          </div>

          <div className="speech-bubble text-sm">« {agent.opinion} »</div>
        </div>
      </div>
    </div>,
    document.body
  );
};

export default AgentDetailModal;
