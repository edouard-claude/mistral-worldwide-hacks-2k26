/**
 * Agent color mapping — each agent gets a distinct Cold War palette color.
 * Uses CSS variables defined in index.css.
 * Keys match backend agent_id OR display name patterns.
 */

export interface AgentColor {
  border: string;   // tailwind border class
  bg: string;       // tailwind bg class (low opacity)
  text: string;     // tailwind text class
  hsl: string;      // raw hsl for inline styles
}

const palette: Record<string, AgentColor> = {
  agent_01: {
    border: "border-[hsl(210,60%,55%)]",
    bg: "bg-[hsl(210,60%,55%,0.15)]",
    text: "text-[hsl(210,60%,55%)]",
    hsl: "hsl(210, 60%, 55%)",
  },
  agent_02: {
    border: "border-[hsl(30,85%,55%)]",
    bg: "bg-[hsl(30,85%,55%,0.15)]",
    text: "text-[hsl(30,85%,55%)]",
    hsl: "hsl(30, 85%, 55%)",
  },
  agent_03: {
    border: "border-[hsl(155,55%,45%)]",
    bg: "bg-[hsl(155,55%,45%,0.15)]",
    text: "text-[hsl(155,55%,45%)]",
    hsl: "hsl(155, 55%, 45%)",
  },
  agent_04: {
    border: "border-[hsl(270,50%,60%)]",
    bg: "bg-[hsl(270,50%,60%,0.15)]",
    text: "text-[hsl(270,50%,60%)]",
    hsl: "hsl(270, 50%, 60%)",
  },
};

// Fallback for unknown agents
const fallback: AgentColor = {
  border: "border-secondary/50",
  bg: "bg-secondary/10",
  text: "text-secondary",
  hsl: "hsl(30, 41%, 68%)",
};

/**
 * Get color for an agent by ID or name.
 * Matches agent_01-04 IDs, or tries to match name patterns.
 */
export function getAgentColor(agentIdOrName: string): AgentColor {
  // Direct ID match
  if (palette[agentIdOrName]) return palette[agentIdOrName];

  // Try matching by name keywords
  const lower = agentIdOrName.toLowerCase();
  if (lower.includes("vérity") || lower.includes("verity") || lower.includes("jean")) return palette.agent_01;
  if (lower.includes("karen") || lower.includes("q-anon") || lower.includes("qanon")) return palette.agent_02;
  if (lower.includes("aisha") || lower.includes("rashid")) return palette.agent_03;
  if (lower.includes("boris") || lower.includes("troll")) return palette.agent_04;

  // Fallback: cycle through palette based on string hash
  const hash = agentIdOrName.split("").reduce((a, c) => a + c.charCodeAt(0), 0);
  const keys = Object.keys(palette);
  return palette[keys[hash % keys.length]];
}
