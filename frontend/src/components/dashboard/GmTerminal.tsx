import { useEffect, useRef, useState } from "react";
import brainSoviet from "@/assets/brain_soviet.png";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useLang } from "@/i18n/LanguageContext";
import { tr } from "@/i18n/translations";
import { useGame } from "@/hooks/useGame";
import { renderMarkdown } from "@/utils/terminalMarkdown";
import type { GmTerminalLine } from "@/types/ws-events";

// Re-export for backwards compatibility
export type { GmTerminalLine } from "@/types/ws-events";

// Level 1 = announcements (shown prominently, modal-style)
const LEVEL1_TYPES = new Set<GmTerminalLine["type"]>(["choice_resolved", "strategy", "separator"]);
// Level 2 = technical journal (foldable, closed by default)
const LEVEL2_TYPES = new Set<GmTerminalLine["type"]>(["llm_text", "vision_update", "phase", "llm_call", "tool_call", "tool_result", "info"]);

// Satirical waiting phrases that rotate while GM thinks
const waitingPhrases: Record<string, string[]> = {
  fr: [
    "Le camarade Mistralski consulte les archives secrètes...",
    "Vérification des dossiers classifiés TOP MOUSTACHE...",
    "Recalibrage de l'indice de crédulité mondiale...",
    "Interrogatoire d'un pigeon suspect en cours...",
    "Le Général ajuste sa moustache et réfléchit...",
    "Écoute clandestine des fréquences wifi subversives...",
    "Analyse des ronronnements codés de Félix-1...",
    "Consultation du Manuel de Désinformation Avancée, 3e édition...",
  ],
  en: [
    "Comrade Mistralski is consulting the secret archives...",
    "Checking files classified TOP MUSTACHE...",
    "Recalibrating global credulity index...",
    "Interrogating a suspicious pigeon...",
    "The General adjusts his mustache and reflects...",
    "Eavesdropping on subversive wifi frequencies...",
    "Analyzing coded purrs from Felix-1 satellite...",
    "Consulting the Manual of Advanced Disinformation, 3rd edition...",
  ],
};

/**
 * Filter article body/JSON from LLM text, keep strategic analysis.
 */
function filterArticleContent(text: string): string | null {
  if (/^\s*\{/.test(text) && /"body"\s*:/.test(text)) {
    try {
      const parsed = JSON.parse(text);
      if (parsed.observations) return formatObservations(parsed.observations);
    } catch { /* fall through */ }
    if (!/"analyse"|"strategie"|"raison"|"theme"|"fiches"|"plan"|"menace"|"objectif"/i.test(text)) {
      return null;
    }
  }

  let cleaned = text.replace(/```json\s*\n?\s*\{[\s\S]*?"body"[\s\S]*?```/g, "").trim();
  const sections = cleaned.split(/\n---\n|\n-{3,}\n/);
  const strategicPart = sections[0] || "";

  cleaned = strategicPart.split("\n").filter(line => {
    const t = line.trim();
    if (/^#{1,4}\s*\d*\.?\s*(REAL|FAKE|SATIRICAL|RÉEL|SATIRIQUE)/i.test(t)) return false;
    if (/^(NEWS OPTIONS|OPTIONS DE NEWS)/i.test(t)) return false;
    if (/^Source:\s/i.test(t)) return false;
    if (/^"(body|source_real|text)"\s*:/.test(t)) return false;
    if (/^"stat_impact"\s*:\s*\{/.test(t)) return false;
    if (/^"(credibilite|rage|complotisme|esperance_democratique)"\s*:/.test(t)) return false;
    if (t === "{" || t === "}" || t === "}," || t === "},") return false;
    if (/^[A-Z]{2,}\s*[—–-]\s/.test(t)) return false;
    return true;
  }).join("\n").trim();

  cleaned = cleaned.replace(/```json/g, "").replace(/```/g, "").trim();
  return cleaned.length > 10 ? cleaned : null;
}

function formatObservations(obs: any): string {
  const parts: string[] = [];
  if (obs.strategie_initiale) {
    const s = obs.strategie_initiale;
    if (s.analyse) parts.push(`## Analyse stratégique\n${s.analyse}`);
    if (s.theme_choisi) parts.push(`## Thème choisi\n**${s.theme_choisi}**`);
    if (s.raison) parts.push(`${s.raison}`);
  }
  if (obs.fiches_agents) {
    parts.push(`## Fiches agents`);
    for (const [key, val] of Object.entries(obs.fiches_agents)) {
      const name = key.replace(/_/g, " ").replace(/agent \d+ /i, "");
      parts.push(`- **${name}** : ${val}`);
    }
  }
  if (obs.adaptation_news) {
    parts.push(`## Adaptation des news`);
    for (const [key, val] of Object.entries(obs.adaptation_news as Record<string, string>)) {
      parts.push(`- **${key}** : ${val}`);
    }
  }
  if (obs.plan_court_terme) parts.push(`## Plan court terme\n${obs.plan_court_terme}`);
  if (obs.plan_long_terme) parts.push(`## Plan long terme\n${obs.plan_long_terme}`);
  if (obs.objectif) parts.push(`## Objectif\n${obs.objectif}`);
  return parts.join("\n\n");
}

/** Render a Level 1 announcement line — modal-quality style */
function renderLevel1Line(line: GmTerminalLine): JSX.Element | null {
  if (line.type === "separator") {
    return (
      <div key={line.id} className="py-2 my-2 border-y-2 border-soviet-red/30 text-center">
        <span className="font-comic tracking-widest text-soviet-red text-sm">
          ☭ {line.text} ☭
        </span>
      </div>
    );
  }
  if (line.type === "choice_resolved") {
    return (
      <div key={line.id} className="my-3 border-l-4 pl-4 py-3"
        style={{ borderColor: "hsl(var(--red-soviet))", background: "linear-gradient(90deg, hsl(0 100% 40% / 0.08), transparent)" }}>
        <div className="flex items-center gap-2 mb-2">
          <img src={brainSoviet} alt="" className="w-5 h-5" />
          <span className="text-[10px] px-2 py-0.5 border-2 border-soviet-red/50 bg-soviet-red/20 text-soviet-red font-heading tracking-widest font-bold">
            MISTRALSKI
          </span>
        </div>
        <div className="text-foreground/90 text-base leading-relaxed italic font-comic">
          {renderMarkdown(line.text)}
        </div>
      </div>
    );
  }
  if (line.type === "strategy") {
    return (
      <div key={line.id} className="my-3 border-l-4 pl-4 py-3"
        style={{ borderColor: "hsl(var(--red-soviet))", background: "linear-gradient(90deg, hsl(0 100% 40% / 0.06), transparent)" }}>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-[10px] px-2 py-0.5 border-2 border-soviet-red/40 bg-soviet-red/15 text-soviet-red font-heading tracking-widest font-bold">
            🎯 STRATÉGIE
          </span>
        </div>
        <div className="text-foreground/80 text-[14px] leading-relaxed font-heading">
          {renderMarkdown(line.text)}
        </div>
      </div>
    );
  }
  return null;
}

/** Render a Level 2 technical journal line */
function renderLevel2Line(line: GmTerminalLine, lang: "fr" | "en"): JSX.Element | null {
  if (line.type === "llm_text") {
    const filtered = filterArticleContent(line.text);
    if (!filtered) return null;
    return (
      <div key={line.id} className="my-1.5 border-l-2 pl-2.5 py-1.5"
        style={{ borderColor: "hsl(var(--red-soviet) / 0.4)", background: "linear-gradient(90deg, hsl(0 100% 40% / 0.03), transparent)" }}>
        <div className="text-foreground/70 text-[11px] leading-relaxed">
          {renderMarkdown(filtered)}
        </div>
      </div>
    );
  }
  if (line.type === "vision_update") {
    return (
      <div key={line.id} className="my-1 border-l-2 pl-2.5 py-1"
        style={{ borderColor: "hsl(var(--ocre-gulag))", background: "linear-gradient(90deg, hsl(30 41% 68% / 0.04), transparent)" }}>
        <span className="text-[8px] px-1 py-0.5 border border-secondary/30 bg-secondary/10 text-secondary font-heading tracking-wider">
          {tr("terminal.vision", lang)}
        </span>
        <div className="text-secondary/70 text-[11px] mt-0.5">
          {renderMarkdown(line.text)}
        </div>
      </div>
    );
  }

  const labelMap: Record<string, string> = {
    phase: tr("terminal.phase", lang),
    llm_call: tr("terminal.llm", lang),
    tool_call: tr("terminal.tool", lang),
    tool_result: tr("terminal.result", lang),
    info: tr("terminal.info", lang),
  };
  const colorMap: Record<string, string> = {
    phase: "text-soviet-red/70",
    llm_call: "text-secondary/40",
    tool_call: "text-secondary/60",
    tool_result: "text-secondary/35",
    info: "text-secondary/40",
  };

  const isInfoLine = line.type === "info";
  const hasMarkdown = /[*«"#\-•]/.test(line.text);

  if (isInfoLine) {
    return (
      <div key={line.id} className="my-1.5 border-l-2 pl-2.5 py-1.5"
        style={{ borderColor: "hsl(var(--red-soviet) / 0.3)", background: "linear-gradient(90deg, hsl(0 100% 40% / 0.02), transparent)" }}>
        <div className="text-foreground/80 text-[12px] leading-relaxed">
          {hasMarkdown ? renderMarkdown(line.text) : <div className="py-0.5">{line.text}</div>}
        </div>
      </div>
    );
  }

  return (
    <div key={line.id} className="flex items-start gap-1.5 py-px">
      <span className="text-[7px] px-1 py-px border border-secondary/15 bg-secondary/5 font-heading tracking-wider shrink-0 mt-px text-secondary/40">
        {labelMap[line.type] || line.type.toUpperCase()}
      </span>
      <span className={`${colorMap[line.type] || "text-secondary/40"} text-[10px] break-all`}>
        {line.text}
      </span>
    </div>
  );
}

const GmTerminal = () => {
  const lang = useLang();
  const { state } = useGame();
  const { gmTerminalLines: lines, isStreaming } = state;

  const scrollRef = useRef<HTMLDivElement>(null);
  const [journalOpen, setJournalOpen] = useState(false); // closed by default
  const [waitingIdx, setWaitingIdx] = useState(0);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [lines.length]);

  // Rotate waiting phrases
  useEffect(() => {
    if (!isStreaming) return;
    const interval = setInterval(() => {
      setWaitingIdx(prev => prev + 1);
    }, 4000);
    return () => clearInterval(interval);
  }, [isStreaming]);

  const level1Lines = lines.filter(l => LEVEL1_TYPES.has(l.type));
  const level2Lines = lines.filter(l => LEVEL2_TYPES.has(l.type));
  const phrases = waitingPhrases[lang] || waitingPhrases.fr;

  return (
    <div className="flex flex-col overflow-hidden"
      style={{ background: "linear-gradient(180deg, hsl(0 0% 6%), hsl(0 0% 3%))" }}>

      <div ref={scrollRef} className="overflow-y-auto p-3 min-h-0 flex-1 space-y-0">

        {lines.length === 0 && !isStreaming && (
          <div className="flex items-center gap-2 justify-center py-3 opacity-30">
            <span className="text-[10px] font-heading tracking-widest text-secondary/50">{tr("terminal.waiting", lang)}</span>
          </div>
        )}

        {/* Announcements — modal-quality style */}
        {level1Lines.length > 0 && (
          <div className="mb-2">
            {level1Lines.map(line => renderLevel1Line(line))}
          </div>
        )}

        {/* Satirical waiting indicator */}
        {isStreaming && (
          <div className="flex items-start gap-2 py-3 border-l-3 pl-3 my-2"
            style={{ borderColor: "hsl(var(--red-soviet) / 0.4)" }}>
            <img src={brainSoviet} alt="" className="w-5 h-5 shrink-0 mt-0.5"
              style={{ animation: "pulse-glow 2s ease-in-out infinite" }} />
            <div>
              <div className="text-foreground/70 text-[13px] italic font-comic leading-relaxed"
                style={{ animation: "fade-in-up 0.5s ease-out" }}
                key={waitingIdx}>
                {phrases[waitingIdx % phrases.length]}
              </div>
              <div className="flex items-center gap-1 mt-1.5 text-soviet-red/40">
                <span className="inline-block w-1.5 h-3 bg-soviet-red/50"
                  style={{ animation: "typewriter-cursor 0.8s step-end infinite" }} />
                <span className="text-[9px] font-heading tracking-wider">
                  {tr("terminal.thinking", lang)}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Technical journal — foldable, closed by default */}
        {level2Lines.length > 0 && (
          <div className="mt-2 border-t border-secondary/10 pt-1">
            <button
              onClick={() => setJournalOpen(!journalOpen)}
              className="flex items-center gap-1.5 w-full text-left py-1 hover:opacity-80 transition-opacity"
            >
              {journalOpen ? <ChevronDown size={12} className="text-secondary/50" /> : <ChevronRight size={12} className="text-secondary/50" />}
              <span className="text-[9px] font-heading text-secondary/50 tracking-[0.15em]">
                {tr("terminal.journal", lang)} ({level2Lines.length})
              </span>
            </button>

            {journalOpen && (
              <div className="space-y-0.5 mt-1" style={{ fontFamily: "'JetBrains Mono', 'Courier New', monospace" }}>
                {level2Lines.map(line => renderLevel2Line(line, lang))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default GmTerminal;
