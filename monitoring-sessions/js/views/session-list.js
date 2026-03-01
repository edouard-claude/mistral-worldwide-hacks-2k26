/**
 * Session list view — route #/
 */
import { loadSessionIndex } from '../data-loader.js';

export async function renderSessionList(app) {
  app.innerHTML = '<div class="loading">Chargement...</div>';

  const sessions = await loadSessionIndex();

  let html = `
    <div class="session-list-header">
      <h1>Sessions de simulation</h1>
      <p>${sessions.length} sessions disponibles</p>
    </div>
    <div class="session-grid">
  `;

  for (const s of sessions) {
    html += `
      <div class="session-card" data-id="${s.session_id}">
        <div class="session-id">${s.session_id}</div>
        <div class="fake-news">${escapeHtml(s.fake_news)}</div>
        <div class="meta">
          <span>${s.total_rounds} tour${s.total_rounds !== 1 ? 's' : ''}</span>
          <span>${s.agent_count} agents</span>
          <span>${s.alive_count} survivants</span>
        </div>
      </div>
    `;
  }

  html += '</div>';
  app.innerHTML = html;

  // Click handlers
  app.querySelectorAll('.session-card').forEach(card => {
    card.addEventListener('click', () => {
      location.hash = `#/session/${card.dataset.id}`;
    });
  });
}

function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}
