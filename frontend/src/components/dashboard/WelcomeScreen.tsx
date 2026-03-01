import { useState, useRef, useEffect } from "react";
import agentGm from "@/assets/agent_gm.png";
import agentKgb from "@/assets/agent_kgb.png";
import agentMoustache from "@/assets/agent_moustache.png";
import agentPropa from "@/assets/agent_propa.png";
import agentSabot from "@/assets/agent_sabot.png";

interface WelcomeScreenProps {
  onStart: (lang: "fr" | "en") => void;
}

const agentPortraits = [agentKgb, agentMoustache, agentPropa, agentSabot];

const rulesData = {
  fr: [
    { n: "I", text: <><strong>Choisis une Fake News</strong> parmi 3 — chaque mensonge a ses conséquences, camarade.</> },
    { n: "II", text: <><strong>Les agents débattent.</strong> Le plus convaincant survit. Le plus faible ? <strong>LIQUIDÉ.</strong></> },
    { n: "III", text: <><strong>Le vainqueur se CLONE</strong> — la médiocrité est remplacée par l'excellence idéologique.</> },
    { n: "IV", text: <><strong>10 tours</strong> pour plonger le monde dans le chaos. Ou mourir en essayant.</> },
  ],
  en: [
    { n: "I", text: <><strong>Pick a Fake News</strong> from 3 — every lie has consequences, comrade.</> },
    { n: "II", text: <><strong>Agents debate.</strong> The most convincing survives. The weakest? <strong>LIQUIDATED.</strong></> },
    { n: "III", text: <><strong>The winner CLONES</strong> — mediocrity is replaced by ideological excellence.</> },
    { n: "IV", text: <><strong>10 rounds</strong> to plunge the world into chaos. Or die trying.</> },
  ],
};

const introText = {
  fr: <>Camarade ! Bienvenue dans le<strong> Politburo des Fake News</strong>. Ici, des agents IA s'affrontent dans des débats acharnés pour dominer l'opinion publique.</>,
  en: <>Comrade! Welcome to the<strong> Politburo of Fake News</strong>. Here, AI agents clash in fierce debates to dominate public opinion.</>,
};

const ctaText = {
  fr: "ENTRER AU POLITBURO",
  en: "ENTER THE POLITBURO",
};

const ctaSub = {
  fr: "Le Parti compte sur vous. Ne le décevez pas.",
  en: "The Party is counting on you. Do not disappoint.",
};

const rulesTitle = {
  fr: "PROTOCOLE OPÉRATIONNEL",
  en: "OPERATIONAL PROTOCOL",
};

const agentsTitle = {
  fr: "VOS PIONS",
  en: "YOUR PAWNS",
};

const WelcomeScreen = ({ onStart }: WelcomeScreenProps) => {
  const [showContent, setShowContent] = useState(false);
  const [musicPlaying, setMusicPlaying] = useState(false);
  const [lang, setLang] = useState<"fr" | "en">("fr");
  
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => setShowContent(true), 300);
    return () => clearTimeout(timer);
  }, []);

  const handleStart = () => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    onStart(lang);
  };

  const toggleMusic = () => {
    if (!audioRef.current) {
      audioRef.current = new Audio("/soviet-march.ogg");
      audioRef.current.loop = true;
      audioRef.current.volume = 0.4;
    }
    if (musicPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play().catch(() => {});
    }
    setMusicPlaying(!musicPlaying);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background overflow-hidden">
      <div className="absolute inset-0 bg-stripes opacity-60" />
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: "radial-gradient(ellipse at center, transparent 30%, hsl(var(--red-dark) / 0.4) 100%)",
        }}
      />

      <div
        className={`relative z-10 max-w-3xl w-full mx-4 transition-all duration-1000 ${
          showContent ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
        }`}
      >
        <div className="panel-paper p-0 overflow-hidden">
          {/* Header */}
          <div className="panel-header-dark py-8 relative overflow-hidden">
            <div className="flex justify-center mb-3">
              <div
                className="relative"
                style={{
                  width: 60, height: 60,
                  clipPath: "polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%)",
                  backgroundColor: "hsl(var(--red-soviet))",
                  filter: "drop-shadow(0 0 12px hsl(var(--red-soviet) / 0.6))",
                  animation: "star-spin 12s linear infinite, pulse-glow 3s ease-in-out infinite",
                }}
              />
            </div>
            <h1
              className="font-comic text-5xl md:text-7xl tracking-wider leading-none"
              style={{
                color: "hsl(var(--comic-yellow))",
                textShadow: "4px 4px 0px hsl(var(--red-dark)), 6px 6px 0px hsl(var(--black))",
              }}
            >
              GAME OF CLAW
            </h1>
            <div className="mt-2 mx-auto max-w-xs h-[3px]" style={{ backgroundColor: "hsl(var(--red-soviet))" }} />
            <p className="text-sm mt-2 tracking-[0.3em] uppercase font-bold" style={{ color: "hsl(var(--ocre-gulag))" }}>
              {lang === "fr" ? "PROPAGANDE — DÉBATS — TRAHISONS" : "PROPAGANDA — DEBATES — BETRAYALS"}
            </p>
          </div>

          <div className="p-6 md:p-8 space-y-5">
            {/* GM Portrait + Intro */}
            <div className="flex gap-5 items-start">
              <img
                src={agentGm}
                alt="Mistralski"
                className="w-24 h-24 border-4 border-black flex-shrink-0"
                style={{ imageRendering: "pixelated", boxShadow: "4px 4px 0px hsl(var(--red-soviet))" }}
              />
              <div className="speech-bubble flex-1">
                <p className="text-base md:text-lg leading-relaxed">{introText[lang]}</p>
              </div>
            </div>

            {/* Language stamps — right after intro */}
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={() => setLang("fr")}
                className={`stamp cursor-pointer transition-all text-[11px] px-3 py-1 ${lang === "fr" ? "opacity-100 scale-110" : "opacity-50 hover:opacity-80"}`}
                style={{ transform: `rotate(-6deg) ${lang === "fr" ? "scale(1.1)" : ""}`, borderColor: lang === "fr" ? "hsl(var(--red-soviet))" : undefined }}
              >
                FRANÇAIS
              </button>
              <span className="text-[8px]" style={{ color: "hsl(var(--ocre-gulag))" }}>///</span>
              <button
                onClick={() => setLang("en")}
                className={`stamp cursor-pointer transition-all text-[11px] px-3 py-1 ${lang === "en" ? "opacity-100 scale-110" : "opacity-50 hover:opacity-80"}`}
                style={{ transform: `rotate(4deg) ${lang === "en" ? "scale(1.1)" : ""}`, borderColor: lang === "en" ? "hsl(var(--red-soviet))" : undefined }}
              >
                ENGLISH
              </button>
            </div>

            {/* Rules — rewritten satirical */}
            <div className="space-y-2">
              <h2 className="text-base font-bold tracking-wide" style={{ color: "hsl(var(--red-soviet))" }}>
                {rulesTitle[lang]}
              </h2>
              <div className="grid gap-2 text-sm">
                {rulesData[lang].map(r => (
                  <div key={r.n} className="flex gap-2 items-start">
                    <span className="stamp text-[10px] px-1 py-0 flex-shrink-0" style={{ transform: "none" }}>{r.n}</span>
                    <p>{r.text}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Agent preview */}
            <div className="space-y-2">
              <h2 className="text-base font-bold tracking-wide" style={{ color: "hsl(var(--red-soviet))" }}>
                {agentsTitle[lang]}
              </h2>
              <div className="flex gap-3 justify-center">
                {agentPortraits.map((portrait, i) => (
                  <img
                    key={i}
                    src={portrait}
                    alt={`Agent ${i + 1}`}
                    className="w-14 h-14 border-3 border-black"
                    style={{
                      imageRendering: "pixelated",
                      boxShadow: "3px 3px 0px hsl(var(--black) / 0.4)",
                      animation: `fade-in-up 0.5s ease-out ${0.5 + i * 0.15}s both`,
                    }}
                  />
                ))}
              </div>
            </div>

            {/* CTA + music */}
            <div className="space-y-3 pt-1">
              <button
                onClick={handleStart}
                className="btn-soviet w-full py-3 text-lg tracking-wider flex flex-col items-center gap-1"
              >
                <span className="font-comic text-xl">{ctaText[lang]}</span>
              </button>
              <p className="text-center text-[8px] italic" style={{ color: "hsl(var(--ocre-gulag))" }}>
                {ctaSub[lang]}
              </p>
              <div className="flex justify-center">
                <button onClick={toggleMusic} className="btn-select-news text-xs px-4 py-2">
                  {musicPlaying
                    ? (lang === "fr" ? "/// Couper la musique" : "/// Mute the music")
                    : (lang === "fr" ? "/// Activer la musique soviétique" : "/// Play Soviet music")}
                </button>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div
            className="text-center py-3 text-xs tracking-widest uppercase"
            style={{ backgroundColor: "hsl(var(--black))", color: "hsl(var(--ocre-gulag))" }}
          >
            {lang === "fr" ? "★ Approuvé par le Politburo de la Désinformation ★" : "★ Approved by the Disinformation Politburo ★"}
          </div>
        </div>
      </div>
    </div>
  );
};

export default WelcomeScreen;
