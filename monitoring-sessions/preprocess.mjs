#!/usr/bin/env node
/**
 * Pre-processor: reads examples/ and generates data/sessions.json + data/<id>.json
 * Usage: node preprocess.mjs
 * Zero npm dependencies.
 */
import { readdir, readFile, writeFile, mkdir, access } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = dirname(fileURLToPath(import.meta.url));
const EXAMPLES = join(ROOT, 'examples');
const DATA = join(ROOT, 'data');

// ─── Helpers ────────────────────────────────────────────────────────────────

async function exists(p) {
  try { await access(p); return true; } catch { return false; }
}

async function readText(p) {
  try { return await readFile(p, 'utf-8'); } catch { return null; }
}

async function readJson(p) {
  const t = await readText(p);
  return t ? JSON.parse(t) : null;
}

async function listDirs(p) {
  if (!await exists(p)) return [];
  const entries = await readdir(p, { withFileTypes: true });
  return entries.filter(e => e.isDirectory()).map(e => e.name);
}

async function listFiles(p) {
  if (!await exists(p)) return [];
  const entries = await readdir(p, { withFileTypes: true });
  return entries.filter(e => e.isFile()).map(e => e.name);
}

// ─── SOUL.md parser ─────────────────────────────────────────────────────────

function parseSoul(md) {
  if (!md) return null;
  const sections = {};
  let current = null;
  for (const line of md.split('\n')) {
    const heading = line.match(/^## (.+)/);
    if (heading) {
      current = heading[1].trim();
      sections[current] = [];
    } else if (current) {
      sections[current].push(line);
    }
  }

  const joinSection = key => {
    const lines = sections[key];
    if (!lines) return '';
    return lines.join('\n').trim();
  };

  const biasesRaw = sections['Biais cognitifs dominants'] || [];
  const biases = biasesRaw
    .map(l => l.replace(/^- /, '').trim())
    .filter(l => l.length > 0);

  return {
    personality: joinSection('Personnalité'),
    style: joinSection('Style argumentatif'),
    biases,
  };
}

// ─── DEATH.md parser ────────────────────────────────────────────────────────

function parseDeath(md) {
  if (!md) return null;
  const get = (label) => {
    const re = new RegExp(`\\*\\*${label}\\*\\*:\\s*(.+)`, 'i');
    const m = md.match(re);
    return m ? m[1].trim() : null;
  };

  const round = parseInt(get('Tour'), 10) || null;
  const scoreRaw = get('Score final');
  const final_score = scoreRaw ? parseInt(scoreRaw, 10) : null;
  const cause = get('Cause') || null;

  // Extract last message: everything between "Dernier message (phase 3)**: " and "- **Classé par**:"
  let last_message = null;
  const msgMatch = md.match(/\*\*Dernier message \(phase 3\)\*\*:\s*([\s\S]*?)(?=\n- \*\*Classé par\*\*:)/);
  if (msgMatch) {
    last_message = msgMatch[1].trim();
  }

  // Extract ranked_by
  const ranked_by = [];
  const rankedSection = md.match(/\*\*Classé par\*\*:\s*\n([\s\S]*?)$/);
  if (rankedSection) {
    const lines = rankedSection[1].split('\n');
    for (const line of lines) {
      const m = line.match(/^\s*-\s+(\w+):\s*position\s+(\d+)/);
      if (m) {
        ranked_by.push({ agent_name: m[1], position: parseInt(m[2], 10) });
      }
    }
  }

  return { round, final_score, cause, last_message, ranked_by };
}

// ─── Memory T*.md parser ────────────────────────────────────────────────────

function parseMemory(md) {
  if (!md) return null;

  // Fake news for this round
  const fakeNewsMatch = md.match(/\*\*Fake news débattue\*\*:\s*"?([^"\n]+)"?/);
  const fake_news = fakeNewsMatch ? fakeNewsMatch[1].trim() : null;

  // Phase 1
  const confInitMatch = md.match(/\*\*Confiance initiale\*\*:\s*(\d+)/);
  const confidence_initial = confInitMatch ? parseInt(confInitMatch[1], 10) : null;

  // Phase 2 — public argument (everything between ## Phase 2 and ## Phase 3)
  let public_argument = null;
  const phase2Match = md.match(/## Phase 2 — Mon take public\s*\n([\s\S]*?)(?=\n## Phase 3)/);
  if (phase2Match) {
    public_argument = phase2Match[1].trim();
  }

  // Phase 3
  const confRevMatch = md.match(/\*\*Confiance révisée\*\*:\s*(\d+)/);
  const confidence_revised = confRevMatch ? parseInt(confRevMatch[1], 10) : null;

  let final_response = null;
  const respMatch = md.match(/\*\*Réponse finale\*\*:\s*([\s\S]*?)(?=\n## Phase 4)/);
  if (respMatch) {
    final_response = respMatch[1].trim();
  }

  // Phase 4 — Vote
  let vote_ranking = [];
  const rankMatch = md.match(/\*\*Classement\*\*:\s*(.+)/);
  if (rankMatch) {
    const parts = rankMatch[1].split(',').map(s => s.trim());
    vote_ranking = parts.map(p => {
      const m = p.match(/\d+e=(.+)/);
      return m ? m[1].trim() : p;
    });
  }

  // Political color
  let political_color_before = null;
  let political_color_after = null;
  const colorMatch = md.match(/\*\*Couleur politique\*\*:\s*([\d.]+)\s*→\s*([\d.]+)/);
  if (colorMatch) {
    political_color_before = parseFloat(colorMatch[1]);
    political_color_after = parseFloat(colorMatch[2]);
  }

  // Score
  const scoreMatch = md.match(/\*\*Mon score\*\*:\s*(\d+)/);
  const score = scoreMatch ? parseInt(scoreMatch[1], 10) : null;

  // Eliminated & cloned
  const deathMatch = md.match(/\*\*Mort\*\*:\s*(\w+)/);
  const eliminated_name = deathMatch ? deathMatch[1] : null;

  const cloneMatch = md.match(/\*\*Clone\*\*:\s*(\w+)\s*\(enfant de (\w+)\)/);
  const cloned_name = cloneMatch ? cloneMatch[1] : null;
  const cloned_parent_name = cloneMatch ? cloneMatch[2] : null;

  return {
    fake_news,
    confidence_initial,
    confidence_revised,
    public_argument,
    final_response,
    vote_ranking,
    political_color_before,
    political_color_after,
    score,
    eliminated_name,
    cloned_name,
    cloned_parent_name,
  };
}

// ─── Chat file reader ───────────────────────────────────────────────────────

async function readChat(sessionDir, round, phase) {
  const p = join(sessionDir, 'chat', `T${round}_phase${phase}.md`);
  return await readText(p);
}

// ─── Process a single session ───────────────────────────────────────────────

async function processSession(sessionDir) {
  const global = await readJson(join(sessionDir, 'global.json'));
  if (!global) return null;

  const sessionId = global.session_id;
  const totalRounds = global.round || 0;

  // Build agent map from global.json (living + graveyard)
  const agents = {};
  const nameToId = {};

  for (const a of (global.agents || [])) {
    agents[a.id] = {
      id: a.id,
      name: a.name,
      parent_id: a.parent_id || null,
      born_at_round: a.born_at_round || 1,
      died_at_round: null,
      alive: true,
      political_color_initial: a.political_color,
      temperature: a.temperature,
      soul: null,
      death: null,
    };
    nameToId[a.name] = a.id;
  }

  for (const a of (global.graveyard || [])) {
    agents[a.id] = {
      id: a.id,
      name: a.name,
      parent_id: a.parent_id || null,
      born_at_round: a.born_at_round || 1,
      died_at_round: a.died_at_round || null,
      alive: false,
      political_color_initial: a.political_color,
      temperature: a.temperature,
      soul: null,
      death: null,
    };
    nameToId[a.name] = a.id;
  }

  // Read SOUL.md for all agents (living + graveyard)
  for (const folder of ['agents', 'graveyard']) {
    const dir = join(sessionDir, folder);
    const agentDirs = await listDirs(dir);
    for (const name of agentDirs) {
      const id = nameToId[name];
      if (!id) continue;

      const soulMd = await readText(join(dir, name, 'SOUL.md'));
      if (soulMd) {
        agents[id].soul = parseSoul(soulMd);
      }

      // Read DEATH.md for graveyard agents
      if (folder === 'graveyard') {
        const deathMd = await readText(join(dir, name, 'DEATH.md'));
        if (deathMd) {
          agents[id].death = parseDeath(deathMd);
        }
      }
    }
  }

  // Process rounds
  const rounds = {};
  for (let r = 1; r <= totalRounds; r++) {
    const roundData = {
      round_number: r,
      fake_news: null,
      agents_present: [],
      eliminated_id: null,
      cloned_id: null,
      cloned_parent_id: null,
      agent_rounds: {},
      chat_phase2: null,
      chat_phase3: null,
    };

    // Determine which agents were present in this round
    for (const [id, agent] of Object.entries(agents)) {
      const born = agent.born_at_round || 1;
      const died = agent.died_at_round;
      // Agent is present if born <= round and (still alive or died at this round or later)
      if (born <= r && (died === null || died >= r)) {
        roundData.agents_present.push(id);
      }
    }

    // Read memory files for each present agent
    let eliminatedName = null;
    let clonedName = null;
    let clonedParentName = null;

    for (const id of roundData.agents_present) {
      const agent = agents[id];
      const folder = agent.alive ? 'agents' : 'graveyard';
      const memPath = join(sessionDir, folder, agent.name, 'memory', `T${r}.md`);
      const memMd = await readText(memPath);
      const mem = parseMemory(memMd);

      if (mem) {
        if (!roundData.fake_news && mem.fake_news) {
          roundData.fake_news = mem.fake_news;
        }

        roundData.agent_rounds[id] = {
          confidence_initial: mem.confidence_initial,
          confidence_revised: mem.confidence_revised,
          public_argument: mem.public_argument,
          final_response: mem.final_response,
          vote_ranking: mem.vote_ranking,
          political_color_before: mem.political_color_before,
          political_color_after: mem.political_color_after,
          score: mem.score,
        };

        if (mem.eliminated_name) eliminatedName = mem.eliminated_name;
        if (mem.cloned_name) {
          clonedName = mem.cloned_name;
          clonedParentName = mem.cloned_parent_name;
        }
      }
    }

    // Resolve names to IDs for eliminated/cloned
    if (eliminatedName && nameToId[eliminatedName]) {
      roundData.eliminated_id = nameToId[eliminatedName];
    }
    if (clonedName && nameToId[clonedName]) {
      roundData.cloned_id = nameToId[clonedName];
    }
    if (clonedParentName && nameToId[clonedParentName]) {
      roundData.cloned_parent_id = nameToId[clonedParentName];
    }

    // Use global fake_news as fallback for round 1
    if (!roundData.fake_news && r === 1) {
      roundData.fake_news = global.fake_news;
    }

    // Read chat files
    roundData.chat_phase2 = await readChat(sessionDir, r, 2);
    roundData.chat_phase3 = await readChat(sessionDir, r, 3);

    rounds[r] = roundData;
  }

  // Build genealogy tree
  const genealogy = buildGenealogy(agents);

  // Build timeline
  const timeline = [];
  for (let r = 1; r <= totalRounds; r++) {
    const rd = rounds[r];
    if (!rd) continue;
    const died = rd.eliminated_id ? agents[rd.eliminated_id]?.name : null;
    const born = rd.cloned_id ? agents[rd.cloned_id]?.name : null;
    timeline.push({
      round: r,
      fake_news: rd.fake_news,
      died,
      born,
      agents_present: rd.agents_present.map(id => ({
        id,
        name: agents[id].name,
        political_color: agents[id].political_color_initial,
      })),
    });
  }

  return {
    session_id: sessionId,
    fake_news: global.fake_news,
    total_rounds: totalRounds,
    agents,
    rounds,
    genealogy,
    timeline,
  };
}

// ─── Genealogy tree builder ─────────────────────────────────────────────────

function buildGenealogy(agents) {
  // Build recursive tree: roots = agents with no parent_id
  const agentList = Object.values(agents);
  const childrenMap = {};
  for (const a of agentList) {
    if (a.parent_id) {
      if (!childrenMap[a.parent_id]) childrenMap[a.parent_id] = [];
      childrenMap[a.parent_id].push(a.id);
    }
  }

  function buildNode(id) {
    const a = agents[id];
    if (!a) return null;
    return {
      id: a.id,
      name: a.name,
      alive: a.alive,
      political_color: a.political_color_initial,
      born_at_round: a.born_at_round,
      died_at_round: a.died_at_round,
      children: (childrenMap[id] || []).map(buildNode).filter(Boolean),
    };
  }

  const roots = agentList
    .filter(a => !a.parent_id)
    .map(a => buildNode(a.id))
    .filter(Boolean);

  return roots;
}

// ─── Main ───────────────────────────────────────────────────────────────────

async function main() {
  await mkdir(DATA, { recursive: true });

  const sessionDirs = await listDirs(EXAMPLES);
  const sessionIndex = [];

  for (const dirName of sessionDirs) {
    const sessionDir = join(EXAMPLES, dirName);
    console.log(`Processing ${dirName}...`);

    const session = await processSession(sessionDir);
    if (!session) {
      console.log(`  Skipping (no global.json)`);
      continue;
    }

    // Write individual session JSON
    await writeFile(
      join(DATA, `${session.session_id}.json`),
      JSON.stringify(session, null, 2),
    );

    sessionIndex.push({
      session_id: session.session_id,
      fake_news: session.fake_news,
      total_rounds: session.total_rounds,
      agent_count: Object.keys(session.agents).length,
      alive_count: Object.values(session.agents).filter(a => a.alive).length,
    });

    console.log(`  -> ${session.total_rounds} rounds, ${Object.keys(session.agents).length} agents`);
  }

  // Write sessions index
  await writeFile(
    join(DATA, 'sessions.json'),
    JSON.stringify(sessionIndex, null, 2),
  );

  console.log(`\nDone! Generated ${sessionIndex.length} session files in data/`);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
