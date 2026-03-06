// Centralized agent avatar mapping — by name, gender-aware

import agentHomme1 from "@/assets/agent_homme1.png";
import agentHomme2 from "@/assets/agent_homme2.png";
import agentHomme3 from "@/assets/agent_homme3.png";
import agentHomme4 from "@/assets/agent_homme4.png";
import agentHomme5 from "@/assets/agent_homme5.png";
import agentFemme1 from "@/assets/agent_femme1.png";
import agentFemme2 from "@/assets/agent_femme2.png";
import agentFemme3 from "@/assets/agent_femme3.png";
import agentFemme4 from "@/assets/agent_femme4.png";
import agentFemme5 from "@/assets/agent_femme5.png";

const maleAvatars = [agentHomme1, agentHomme2, agentHomme3, agentHomme4, agentHomme5];
const femaleAvatars = [agentFemme1, agentFemme2, agentFemme3, agentFemme4, agentFemme5];

// All portraits for generic use (welcome screen, etc.)
export const allPortraits = [...maleAvatars, ...femaleAvatars];

// Known agent names from swarm/agent.go — mapped to specific avatars
const nameMap: Record<string, string> = {
  Grigori: agentHomme1,
  Pavel: agentHomme2,
  Dmitri: agentHomme3,
  Alexei: agentHomme4,
  Sergei: agentHomme5,
  Nikolai: agentHomme1,
  Natasha: agentFemme1,
  Zoya: agentFemme2,
  Aria: agentFemme3,
  Vera: agentFemme4,
  Nadia: agentFemme5,
  Olga: agentFemme1,
};

// Female names for gender detection on unknown/clone names
const femaleNames = new Set(["Natasha", "Zoya", "Aria", "Vera", "Nadia", "Olga"]);

function simpleHash(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) - h + s.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

/**
 * Get avatar for an agent by name.
 * Handles clones (e.g. "Clone_Grigori_2") by extracting parent name.
 */
export function getAgentAvatar(name: string): string {
  // Direct match
  if (nameMap[name]) return nameMap[name];

  // Clone pattern: "Clone_ParentName_N" or just contains a known name
  for (const knownName of Object.keys(nameMap)) {
    if (name.includes(knownName)) return nameMap[knownName];
  }

  // Unknown name — pick by hash, use female pool for female-sounding names
  const isFemale = femaleNames.has(name) || name.endsWith("a") || name.endsWith("ya");
  const pool = isFemale ? femaleAvatars : maleAvatars;
  return pool[simpleHash(name) % pool.length];
}
