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
          ${s.updated_at ? `<span class="meta-time">${formatTime(s.updated_at)}</span>` : ''}
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

function formatTime(iso) {
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now - d;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'maintenant';
  if (diffMin < 60) return `il y a ${diffMin}min`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `il y a ${diffH}h`;
  const diffD = Math.floor(diffH / 24);
  if (diffD < 7) return `il y a ${diffD}j`;
  return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
}
