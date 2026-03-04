// Shared markdown rendering utilities for terminal-style content
// Extracted from GmTerminal.tsx for reuse in AgentDetailModal

export function renderMarkdown(text: string): JSX.Element[] {
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

export function renderInline(text: string): JSX.Element {
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
