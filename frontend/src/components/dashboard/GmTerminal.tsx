import { useEffect, useRef, useState } from "react";
import brainSoviet from "@/assets/brain_soviet.png";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useLang } from "@/i18n/LanguageContext";
import { tr } from "@/i18n/translations";

export interface GmTerminalLine {
  id: number;
  type: "separator" | "phase" | "llm_call" | "tool_call" | "tool_result" | "llm_text" | "vision_update" | "choice_resolved" | "strategy" | "info";
  text: string;
}

interface GmTerminalProps {
  lines: GmTerminalLine[];
  isStreaming: boolean;
}

const LEVEL1_TYPES = new Set<GmTerminalLine["type"]>(["choice_resolved", "strategy", "separator"]);
const LEVEL2_TYPES = new Set<GmTerminalLine["type"]>(["llm_text", "vision_update", "phase", "llm_call", "tool_call", "tool_result", "info"]);

/**
 * Filter article body/JSON from LLM text, keep strategic analysis.
 */
function filterArticleContent(text: string): string | null {
  // Pure JSON with body = article content, skip entirely unless it has strategic analysis
  if (/^\s*\{/.test(text) && /"body"\s*:/.test(text)) {
    try {
      const parsed = JSON.parse(text);
      if (parsed.observations) return formatObservations(parsed.observations);
    } catch { /* fall through */ }
    if (!/"analyse"|"strategie"|"raison"|"theme"|"fiches"|"plan"|"menace"|"objectif"/i.test(text)) {
      return null;
    }
  }

  // Remove JSON code blocks containing article bodies
  let cleaned = text.replace(/```json\s*\n?\s*\{[\s\S]*?"body"[\s\S]*?```/g, "").trim();

  // Split into sections and remove NEWS OPTIONS / article content
  const sections = cleaned.split(/\n---\n|\n-{3,}\n/);
  // Keep only the first section (strategic thinking), drop "NEWS OPTIONS" and beyond
  const strategicPart = sections[0] || "";

  // Remove lines that are article headers or content
  cleaned = strategicPart.split("\n").filter(line => {
    const t = line.trim();
    // Filter out news article headers and content
    if (/^#{1,4}\s*\d*\.?\s*(REAL|FAKE|SATIRICAL|RÉEL|SATIRIQUE)/i.test(t)) return false;
    if (/^(NEWS OPTIONS|OPTIONS DE NEWS)/i.test(t)) return false;
    if (/^Source:\s/i.test(t)) return false;
    if (/^"(body|source_real|text)"\s*:/.test(t)) return false;
    if (/^"stat_impact"\s*:\s*\{/.test(t)) return false;
    if (/^"(credibilite|rage|complotisme|esperance_democratique)"\s*:/.test(t)) return false;
    if (t === "{" || t === "}" || t === "}," || t === "},") return false;
    // Filter out lines that look like article body (BRUSSELS —, GENEVA —, etc.)
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

function renderMarkdown(text: string): JSX.Element[] {
  const lines = text.split("\n");
  const elements: JSX.Element[] = [];
  lines.forEach((line, i) => {
    const trimmed = line.trim();
    if (!trimmed) { elements.push(<div key={i} className="h-1" />); return; }
    const headerMatch = trimmed.match(/^(#{1,3})\s+(.+)/);
    if (headerMatch) {
      const level = headerMatch[1].length;
      const content = renderInline(headerMatch[2]);
      const cls = level === 1
        ? "text-soviet-red font-heading text-[13px] font-bold mt-2 mb-1 tracking-wider border-b border-soviet-red/20 pb-0.5"
        : level === 2
        ? "text-soviet-red/90 font-heading text-[12px] font-bold mt-1.5 mb-0.5 tracking-wide"
        : "text-secondary font-heading text-[11px] font-bold mt-1 mb-0.5";
      elements.push(<div key={i} className={cls}>{content}</div>);
      return;
    }
    if (/^[-•]\s/.test(trimmed)) {
      const content = renderInline(trimmed.replace(/^[-•]\s/, ""));
      elements.push(
        <div key={i} className="flex gap-1.5 pl-2 py-0.5">
          <span className="text-soviet-red/60 shrink-0">▪</span>
          <span>{content}</span>
        </div>
      );
      return;
    }
    elements.push(<div key={i} className="py-0.5">{renderInline(trimmed)}</div>);
  });
  return elements;
}

function renderInline(text: string): JSX.Element {
  const parts: (string | JSX.Element)[] = [];
  let remaining = text;
  let key = 0;
  while (remaining.length > 0) {
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
    if (boldMatch && boldMatch.index !== undefined) {
      if (boldMatch.index > 0) parts.push(remaining.slice(0, boldMatch.index));
      parts.push(<strong key={key++} className="text-foreground font-bold">{boldMatch[1]}</strong>);
      remaining = remaining.slice(boldMatch.index + boldMatch[0].length);
      continue;
    }
    const italicMatch = remaining.match(/\*(.+?)\*/);
    if (italicMatch && italicMatch.index !== undefined) {
      if (italicMatch.index > 0) parts.push(remaining.slice(0, italicMatch.index));
      parts.push(<em key={key++} className="italic text-secondary/80">{italicMatch[1]}</em>);
      remaining = remaining.slice(italicMatch.index + italicMatch[0].length);
      continue;
    }
    const quoteMatch = remaining.match(/[«"](.+?)[»"]/);
    if (quoteMatch && quoteMatch.index !== undefined) {
      if (quoteMatch.index > 0) parts.push(remaining.slice(0, quoteMatch.index));
      parts.push(<span key={key++} className="text-soviet-red/80 italic">« {quoteMatch[1]} »</span>);
      remaining = remaining.slice(quoteMatch.index + quoteMatch[0].length);
      continue;
    }
    parts.push(remaining);
    break;
  }
  return <>{parts}</>;
}

function renderLevel1Line(line: GmTerminalLine): JSX.Element | null {
  if (line.type === "separator") {
    return (
      <div key={line.id} className="py-1.5 my-1 border-y border-soviet-red/20 text-center">
        <span className="font-comic tracking-widest text-soviet-red text-[11px]">
          ☭ {line.text} ☭
        </span>
      </div>
    );
  }
  if (line.type === "choice_resolved") {
    return (
      <div key={line.id} className="my-2 border-l-3 pl-3 py-2"
        style={{ borderColor: "hsl(var(--red-soviet))", background: "linear-gradient(90deg, hsl(0 100% 40% / 0.06), transparent)" }}>
        <div className="flex items-center gap-1.5 mb-1">
          <img src={brainSoviet} alt="" className="w-4 h-4" />
          <span className="text-[9px] px-1.5 py-0.5 border border-soviet-red/40 bg-soviet-red/20 text-soviet-red font-heading tracking-wider">
            MISTRALSKI
          </span>
        </div>
        <div className="text-foreground/90 text-[13px] leading-relaxed italic font-heading">
          {renderMarkdown(line.text)}
        </div>
      </div>
    );
  }
  if (line.type === "strategy") {
    return (
      <div key={line.id} className="my-2 border-l-3 pl-3 py-2"
        style={{ borderColor: "hsl(var(--red-soviet))", background: "linear-gradient(90deg, hsl(0 100% 40% / 0.04), transparent)" }}>
        <div className="flex items-center gap-1.5 mb-1">
          <span className="text-[9px] px-1.5 py-0.5 border border-soviet-red/30 bg-soviet-red/15 text-soviet-red font-heading tracking-wider">
            🎯 STRATEGY
          </span>
        </div>
        <div className="text-soviet-red/80 text-[12px] leading-relaxed">
          {renderMarkdown(line.text)}
        </div>
      </div>
    );
  }
  return null;
}

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

  // Info lines: larger font, same style as the rest of the terminal
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

const GmTerminal = ({ lines, isStreaming }: GmTerminalProps) => {
  const lang = useLang();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [journalOpen, setJournalOpen] = useState(true);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [lines.length]);

  const level1Lines = lines.filter(l => LEVEL1_TYPES.has(l.type));
  const level2Lines = lines.filter(l => LEVEL2_TYPES.has(l.type));

  return (
    <div className="flex flex-col overflow-hidden"
      style={{ background: "linear-gradient(180deg, hsl(0 0% 6%), hsl(0 0% 3%))" }}>

      <div ref={scrollRef} className="overflow-y-auto p-3 min-h-0 flex-1 space-y-0"
        style={{ fontFamily: "'JetBrains Mono', 'Courier New', monospace" }}>

        {lines.length === 0 && (
          <div className="flex items-center gap-2 justify-center py-2 opacity-30">
            <span className="text-[9px] font-heading tracking-widest text-secondary/50">{tr("terminal.waiting", lang)}</span>
          </div>
        )}

        {level1Lines.map(line => renderLevel1Line(line))}

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
              <div className="space-y-0.5 mt-1">
                {level2Lines.map(line => renderLevel2Line(line, lang))}
              </div>
            )}
          </div>
        )}

        {isStreaming && (
          <div className="flex items-center gap-1.5 py-1 text-soviet-red/50 mt-1">
            <span className="inline-block w-1.5 h-3 bg-soviet-red/50"
              style={{ animation: "typewriter-cursor 0.8s step-end infinite" }} />
            <span className="text-[9px] italic font-heading tracking-wider">
              {tr("terminal.thinking", lang)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default GmTerminal;
