/**
 * Renders an agent presence chart (Gantt-style) as pure SVG.
 * Y-axis: agents sorted by born_at_round then name
 * X-axis: rounds 1..N
 * Each agent gets a horizontal bar from born_at_round to died_at_round (or last round).
 */
import { politicalColorCSS } from './political-color.js';

const ROW_H = 36;
const NAME_W = 110;
const ROUND_W = 80;
const PAD_TOP = 40;
const PAD_LEFT = 16;
const PAD_RIGHT = 16;
const BAR_H = 22;
const BAR_R = 4;
const ICON_SIZE = 16;

export function renderPresenceChart(session, container) {
  const agents = Object.values(session.agents);
  const totalRounds = session.total_rounds;

  if (totalRounds === 0 || agents.length === 0) {
    container.innerHTML = '<div class="empty-state">Pas de données de présence</div>';
    return;
  }

  // Sort: original agents first (born_at_round ascending), then by name
  agents.sort((a, b) => {
    if (a.born_at_round !== b.born_at_round) return a.born_at_round - b.born_at_round;
    return a.name.localeCompare(b.name);
  });

  const chartW = PAD_LEFT + NAME_W + totalRounds * ROUND_W + PAD_RIGHT;
  const chartH = PAD_TOP + agents.length * ROW_H + 12;

  const wrap = document.createElement('div');
  wrap.className = 'presence-container';

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', chartW);
  svg.setAttribute('height', chartH);
  svg.setAttribute('viewBox', `0 0 ${chartW} ${chartH}`);

  // ── Column headers (round numbers) ──
  for (let r = 1; r <= totalRounds; r++) {
    const x = PAD_LEFT + NAME_W + (r - 1) * ROUND_W + ROUND_W / 2;
    const text = svgText(x, 24, `T${r}`, {
      'font-size': '12', 'font-weight': '600',
      'fill': '#7c6bf4', 'text-anchor': 'middle',
    });
    svg.appendChild(text);

    // Vertical grid line
    const line = svgLine(
      PAD_LEFT + NAME_W + (r - 1) * ROUND_W, PAD_TOP - 4,
      PAD_LEFT + NAME_W + (r - 1) * ROUND_W, chartH - 4,
      { 'stroke': '#1e2130', 'stroke-width': '1' }
    );
    svg.appendChild(line);
  }

  // Right edge grid line
  svg.appendChild(svgLine(
    PAD_LEFT + NAME_W + totalRounds * ROUND_W, PAD_TOP - 4,
    PAD_LEFT + NAME_W + totalRounds * ROUND_W, chartH - 4,
    { 'stroke': '#1e2130', 'stroke-width': '1' }
  ));

  // ── Agent rows ──
  agents.forEach((agent, i) => {
    const y = PAD_TOP + i * ROW_H;
    const color = politicalColorCSS(agent.political_color_initial);
    const born = agent.born_at_round;
    const died = agent.died_at_round;
    const lastPresent = died != null ? died : totalRounds;

    // Horizontal row stripe (alternating)
    if (i % 2 === 0) {
      const bg = svgRect(0, y, chartW, ROW_H, {
        fill: 'rgba(255,255,255,0.02)', rx: '0',
      });
      svg.appendChild(bg);
    }

    // Agent name (clickable)
    const nameG = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    nameG.style.cursor = 'pointer';
    nameG.addEventListener('click', () => {
      location.hash = `#/session/${session.session_id}/agent/${agent.id}`;
    });

    // Small color dot
    const dot = svgCircle(PAD_LEFT + 6, y + ROW_H / 2, 5, { fill: color });
    nameG.appendChild(dot);

    const nameLabel = svgText(PAD_LEFT + 18, y + ROW_H / 2 + 4, agent.name, {
      'font-size': '12', 'font-weight': '500', 'fill': '#e4e6ed',
    });
    nameG.appendChild(nameLabel);
    svg.appendChild(nameG);

    // Presence bar — one segment per round, colored by political_color evolution
    const barY = y + (ROW_H - BAR_H) / 2;
    const fullBarX = PAD_LEFT + NAME_W + (born - 1) * ROUND_W + 4;
    const fullBarW = (lastPresent - born + 1) * ROUND_W - 8;

    // Resolve political color for each round this agent was present
    const roundColors = [];
    let lastColor = agent.political_color_initial;
    for (let r = born; r <= lastPresent; r++) {
      const rd = session.rounds[r];
      const ar = rd && rd.agent_rounds[agent.id];
      if (ar) {
        // Use color_before for the start of the round, color_after to carry forward
        const colorVal = ar.political_color_before != null ? ar.political_color_before : lastColor;
        roundColors.push(colorVal);
        if (ar.political_color_after != null) lastColor = ar.political_color_after;
      } else {
        roundColors.push(lastColor);
      }
    }

    // Clip path for rounded corners on the overall bar
    const clipId = `clip-${agent.id.replace(/[^a-z0-9]/gi, '')}`;
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    const clipPath = document.createElementNS('http://www.w3.org/2000/svg', 'clipPath');
    clipPath.setAttribute('id', clipId);
    const clipRect = svgRect(fullBarX, barY, Math.max(fullBarW, 12), BAR_H, { rx: String(BAR_R) });
    clipPath.appendChild(clipRect);
    defs.appendChild(clipPath);
    svg.appendChild(defs);

    // Draw per-round segments inside the clipped group
    const barGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    barGroup.setAttribute('clip-path', `url(#${clipId})`);

    const numSegments = lastPresent - born + 1;
    for (let s = 0; s < numSegments; s++) {
      const segX = PAD_LEFT + NAME_W + (born - 1 + s) * ROUND_W + 4;
      const segW = ROUND_W;
      const segColor = politicalColorCSS(roundColors[s]);
      const seg = svgRect(segX, barY, segW, BAR_H, {
        fill: segColor, opacity: '0.85',
      });
      barGroup.appendChild(seg);
    }
    svg.appendChild(barGroup);

    // Rounds text inside bar
    const roundsLabel = born === lastPresent
      ? `T${born}`
      : `T${born}–T${lastPresent}`;
    if (fullBarW > 30) {
      const label = svgText(fullBarX + fullBarW / 2, barY + BAR_H / 2 + 4, roundsLabel, {
        'font-size': '10', 'font-weight': '600', 'fill': '#fff',
        'text-anchor': 'middle',
      });
      svg.appendChild(label);
    }

    // Death marker (skull icon at end of bar)
    if (died != null) {
      const skullX = fullBarX + fullBarW - 2;
      const skullY = barY - 2;
      const skull = svgText(skullX, skullY + 4, '☠', {
        'font-size': '13', 'text-anchor': 'end', 'fill': '#e5534b',
      });
      svg.appendChild(skull);
    }

    // Clone marker (+ icon at start of bar for agents born > round 1)
    if (born > 1) {
      const plusX = fullBarX + 1;
      const plusY = barY - 2;
      const plus = svgText(plusX, plusY + 4, '+', {
        'font-size': '14', 'font-weight': '700', 'fill': '#3fb950',
      });
      svg.appendChild(plus);
    }

    // Alive indicator (small green arrow at the end)
    if (agent.alive && lastPresent === totalRounds) {
      const arrowX = fullBarX + fullBarW + 6;
      const arrowY = y + ROW_H / 2;
      const arrow = svgText(arrowX, arrowY + 4, '▸', {
        'font-size': '12', 'fill': '#3fb950',
      });
      svg.appendChild(arrow);
    }
  });

  wrap.appendChild(svg);

  // ── Legend: political color gradient scale ──
  const legend = document.createElement('div');
  legend.className = 'presence-legend';

  const LEGEND_W = Math.min(chartW - 40, 500);
  const LEGEND_H = 50;
  const BAR_LH = 14;
  const BAR_LY = 8;
  const LABEL_Y = BAR_LY + BAR_LH + 14;

  const lsvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  lsvg.setAttribute('width', LEGEND_W);
  lsvg.setAttribute('height', LEGEND_H);
  lsvg.setAttribute('viewBox', `0 0 ${LEGEND_W} ${LEGEND_H}`);

  // Gradient definition with the political color stops
  const gradDefs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
  const grad = document.createElementNS('http://www.w3.org/2000/svg', 'linearGradient');
  grad.setAttribute('id', 'pol-gradient');
  const STOPS = [
    { pos: 0.0,  color: politicalColorCSS(0.0)  },
    { pos: 0.25, color: politicalColorCSS(0.25) },
    { pos: 0.5,  color: politicalColorCSS(0.5)  },
    { pos: 0.75, color: politicalColorCSS(0.75) },
    { pos: 1.0,  color: politicalColorCSS(1.0)  },
  ];
  for (const s of STOPS) {
    const stop = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
    stop.setAttribute('offset', `${s.pos * 100}%`);
    stop.setAttribute('stop-color', s.color);
    grad.appendChild(stop);
  }
  gradDefs.appendChild(grad);
  lsvg.appendChild(gradDefs);

  // Gradient bar
  const gradBar = svgRect(0, BAR_LY, LEGEND_W, BAR_LH, {
    fill: 'url(#pol-gradient)', rx: '3',
  });
  lsvg.appendChild(gradBar);

  // Labels
  const labels = [
    { pos: 0.0,  text: '0.0 Extr. droite' },
    { pos: 0.25, text: '0.25 Droite' },
    { pos: 0.5,  text: '0.5 Centre' },
    { pos: 0.75, text: '0.75 Gauche' },
    { pos: 1.0,  text: '1.0 Extr. gauche' },
  ];
  for (const l of labels) {
    const x = l.pos * LEGEND_W;
    // Tick mark
    lsvg.appendChild(svgLine(x, BAR_LY, x, BAR_LY + BAR_LH + 3, {
      stroke: '#e4e6ed', 'stroke-width': '1',
    }));
    // Text
    const anchor = l.pos === 0 ? 'start' : l.pos === 1 ? 'end' : 'middle';
    lsvg.appendChild(svgText(x, LABEL_Y, l.text, {
      'font-size': '10', fill: '#8b8fa3', 'text-anchor': anchor,
    }));
  }

  legend.appendChild(lsvg);
  wrap.appendChild(legend);

  container.appendChild(wrap);
}

// ── SVG helpers ──

function svgText(x, y, content, attrs = {}) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', 'text');
  el.setAttribute('x', x);
  el.setAttribute('y', y);
  el.textContent = content;
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}

function svgRect(x, y, w, h, attrs = {}) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
  el.setAttribute('x', x);
  el.setAttribute('y', y);
  el.setAttribute('width', w);
  el.setAttribute('height', h);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}

function svgLine(x1, y1, x2, y2, attrs = {}) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', 'line');
  el.setAttribute('x1', x1);
  el.setAttribute('y1', y1);
  el.setAttribute('x2', x2);
  el.setAttribute('y2', y2);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}

function svgCircle(cx, cy, r, attrs = {}) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  el.setAttribute('cx', cx);
  el.setAttribute('cy', cy);
  el.setAttribute('r', r);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}
