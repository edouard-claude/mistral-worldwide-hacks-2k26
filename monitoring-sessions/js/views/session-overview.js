/**
 * Session overview view — route #/session/<id>
 */
import { loadSession } from '../data-loader.js';
import { renderTimeline } from '../components/timeline.js';
import { renderGenealogy } from '../components/genealogy-tree.js';

export async function renderSessionOverview(app, sessionId) {
  app.innerHTML = '<div class="loading">Chargement...</div>';

  const session = await loadSession(sessionId);
  const agents = Object.values(session.agents);
  const alive = agents.filter(a => a.alive).length;
  const dead = agents.length - alive;

  app.innerHTML = `
    <div class="session-header">
      <h1>${escapeHtml(session.fake_news)}</h1>
      <div class="sub">
        ${session.total_rounds} tour${session.total_rounds !== 1 ? 's' : ''} &middot;
        ${agents.length} agents (${alive} vivants, ${dead} morts) &middot;
        <span style="font-family: var(--mono); font-size: 0.8rem;">${session.session_id}</span>
      </div>
    </div>
    <h2 class="section-title">Chronologie</h2>
    <div id="timeline-container"></div>
    <h2 class="section-title">Arbre de lignage</h2>
    <div id="genealogy-container"></div>
  `;

  renderTimeline(session, document.getElementById('timeline-container'));
  renderGenealogy(session, document.getElementById('genealogy-container'));
}

function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}
