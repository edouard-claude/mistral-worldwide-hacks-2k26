/**
 * Renders a top-down genealogy tree as pure SVG.
 */
import { politicalColorCSS } from './political-color.js';

const NODE_R = 24;
const H_SPACING = 100;
const V_SPACING = 90;
const LABEL_OFFSET = 38;

/**
 * Layout tree nodes using a simple recursive algorithm.
 * Returns { nodes, edges, width, height }
 */
function layoutTree(roots) {
  const nodes = [];
  const edges = [];
  let nextX = 0;

  function layout(node, depth) {
    if (!node.children || node.children.length === 0) {
      const x = nextX * H_SPACING;
      nextX++;
      const y = depth * V_SPACING;
      const placed = { ...node, x, y };
      nodes.push(placed);
      return placed;
    }

    const childPlacements = node.children.map(c => layout(c, depth + 1));
    const minX = Math.min(...childPlacements.map(c => c.x));
    const maxX = Math.max(...childPlacements.map(c => c.x));
    const x = (minX + maxX) / 2;
    const y = depth * V_SPACING;
    const placed = { ...node, x, y };
    nodes.push(placed);

    for (const child of childPlacements) {
      edges.push({ from: placed, to: child });
    }

    return placed;
  }

  for (const root of roots) {
    layout(root, 0);
  }

  const allX = nodes.map(n => n.x);
  const allY = nodes.map(n => n.y);
  const width = (Math.max(...allX) - Math.min(...allX)) + H_SPACING * 2;
  const height = (Math.max(...allY) - Math.min(...allY)) + V_SPACING + LABEL_OFFSET + 20;

  // Offset so everything starts from a margin
  const offsetX = -Math.min(...allX) + H_SPACING / 2;
  const offsetY = NODE_R + 10;
  for (const n of nodes) {
    n.x += offsetX;
    n.y += offsetY;
  }

  return { nodes, edges, width, height };
}

export function renderGenealogy(session, container) {
  const roots = session.genealogy || [];
  if (roots.length === 0) {
    container.innerHTML = '<div class="empty-state">Pas de données de lignage</div>';
    return;
  }

  const wrap = document.createElement('div');
  wrap.className = 'genealogy-container';

  const { nodes, edges, width, height } = layoutTree(roots);

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', Math.max(width, 200));
  svg.setAttribute('height', Math.max(height, 100));
  svg.setAttribute('viewBox', `0 0 ${Math.max(width, 200)} ${Math.max(height, 100)}`);

  // Edges
  for (const e of edges) {
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', e.from.x);
    line.setAttribute('y1', e.from.y);
    line.setAttribute('x2', e.to.x);
    line.setAttribute('y2', e.to.y);
    line.setAttribute('stroke', '#2a2e3d');
    line.setAttribute('stroke-width', '2');
    svg.appendChild(line);
  }

  // Nodes
  for (const n of nodes) {
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.classList.add('node-circle');
    g.addEventListener('click', () => {
      location.hash = `#/session/${session.session_id}/agent/${n.id}`;
    });

    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', n.x);
    circle.setAttribute('cy', n.y);
    circle.setAttribute('r', NODE_R);
    circle.setAttribute('fill', politicalColorCSS(n.political_color));
    circle.setAttribute('stroke', n.alive ? '#3fb950' : '#e5534b');
    circle.setAttribute('stroke-width', '3');
    if (!n.alive) {
      circle.setAttribute('stroke-dasharray', '5,3');
    }
    g.appendChild(circle);

    // Initial letters inside circle
    const initials = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    initials.setAttribute('x', n.x);
    initials.setAttribute('y', n.y + 5);
    initials.setAttribute('text-anchor', 'middle');
    initials.setAttribute('font-size', '12');
    initials.setAttribute('font-weight', '700');
    initials.setAttribute('fill', '#fff');
    initials.textContent = n.name.substring(0, 2);
    g.appendChild(initials);

    // Name label below
    const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    label.setAttribute('x', n.x);
    label.setAttribute('y', n.y + LABEL_OFFSET);
    label.setAttribute('text-anchor', 'middle');
    label.setAttribute('font-size', '11');
    label.setAttribute('fill', '#8b8fa3');

    let roundsText = `T${n.born_at_round}`;
    if (n.died_at_round) roundsText += `–T${n.died_at_round}`;
    else roundsText += '+';
    label.textContent = `${n.name} (${roundsText})`;
    g.appendChild(label);

    svg.appendChild(g);
  }

  wrap.appendChild(svg);
  container.appendChild(wrap);
}
