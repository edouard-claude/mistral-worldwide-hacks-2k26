/**
 * Agent detail view — route #/session/<id>/agent/<uuid>
 */
import { loadSession } from '../data-loader.js';
import { politicalColorCSS, politicalLabel } from '../components/political-color.js';
import { renderMarkdown } from '../components/markdown.js';

export async function renderAgentDetail(app, sessionId, agentId) {
  app.innerHTML = '<div class="loading">Chargement...</div>';

  const session = await loadSession(sessionId);
  const agent = session.agents[agentId];

  if (!agent) {
    app.innerHTML = `
      <button class="back-btn" onclick="location.hash='#/session/${sessionId}'">&larr; Retour</button>
      <div class="empty-state">Agent introuvable</div>
    `;
    return;
  }

  const color = politicalColorCSS(agent.political_color_initial);
  const colorLabel = politicalLabel(agent.political_color_initial);

  // Find parent and children
  const parent = agent.parent_id ? session.agents[agent.parent_id] : null;
  const children = Object.values(session.agents).filter(a => a.parent_id === agent.id);

  // Build round history
  const historyHtml = buildHistory(session, agent);

  // Death box
  const deathHtml = agent.death ? buildDeathBox(agent.death) : '';

  app.innerHTML = `
    <button class="back-btn" id="back-btn">&larr; Retour à la session</button>

    <div class="session-header">
      <h1 style="display: flex; align-items: center; gap: 0.75rem;">
        <div class="avatar" style="background-color: ${color}; width: 40px; height: 40px; font-size: 0.85rem;">${agent.name.substring(0, 2)}</div>
        ${escapeHtml(agent.name)}
        <span class="color-badge" style="background-color: ${color}">${colorLabel} (${agent.political_color_initial})</span>
      </h1>
    </div>

    <div class="agent-profile">
      <!-- Identity -->
      <div class="profile-card">
        <h3>Identité</h3>
        <div class="field">
          <div class="field-label">Statut</div>
          <div class="field-value ${agent.alive ? 'status-alive' : 'status-dead'}">
            ${agent.alive ? 'Vivant' : 'Mort (Tour ' + (agent.died_at_round || '?') + ')'}
          </div>
        </div>
        <div class="field">
          <div class="field-label">Température</div>
          <div class="field-value">${agent.temperature}</div>
        </div>
        <div class="field">
          <div class="field-label">Né au tour</div>
          <div class="field-value">${agent.born_at_round}</div>
        </div>
      </div>

      <!-- Soul -->
      <div class="profile-card">
        <h3>Personnalité (SOUL)</h3>
        ${agent.soul ? `
          <div class="field">
            <div class="field-label">Personnalité</div>
            <div class="field-value">${escapeHtml(agent.soul.personality)}</div>
          </div>
          <div class="field">
            <div class="field-label">Style argumentatif</div>
            <div class="field-value">${renderMarkdown(agent.soul.style)}</div>
          </div>
          <div class="field">
            <div class="field-label">Biais cognitifs</div>
            <ul class="bias-list">
              ${agent.soul.biases.map(b => `<li>${escapeHtml(b)}</li>`).join('')}
            </ul>
          </div>
        ` : '<div class="field-value" style="color: var(--text-dim)">Pas de données SOUL</div>'}
      </div>

      <!-- Lineage -->
      <div class="profile-card">
        <h3>Lignage</h3>
        <div class="field">
          <div class="field-label">Parent</div>
          <div class="field-value lineage-links">
            ${parent
              ? `<a class="lineage-link" href="#/session/${sessionId}/agent/${parent.id}">${escapeHtml(parent.name)}</a>`
              : '<span style="color: var(--text-dim)">Aucun (agent original)</span>'}
          </div>
        </div>
        <div class="field">
          <div class="field-label">Enfants</div>
          <div class="field-value lineage-links">
            ${children.length > 0
              ? children.map(c => `<a class="lineage-link" href="#/session/${sessionId}/agent/${c.id}">${escapeHtml(c.name)}</a>`).join('')
              : '<span style="color: var(--text-dim)">Aucun</span>'}
          </div>
        </div>
      </div>
    </div>

    <h2 class="section-title">Historique tour par tour</h2>
    <div class="accordion">${historyHtml}</div>

    ${deathHtml}
  `;

  // Back button
  document.getElementById('back-btn').addEventListener('click', () => {
    location.hash = `#/session/${sessionId}`;
  });

  // Accordion toggle
  app.querySelectorAll('.accordion-header').forEach(header => {
    header.addEventListener('click', () => {
      header.parentElement.classList.toggle('open');
    });
  });
}

function buildHistory(session, agent) {
  let html = '';
  for (let r = 1; r <= session.total_rounds; r++) {
    const round = session.rounds[r];
    if (!round) continue;
    const ar = round.agent_rounds[agent.id];
    if (!ar) continue;

    const isEliminated = round.eliminated_id === agent.id;

    html += `
      <div class="accordion-item">
        <div class="accordion-header">
          <span>
            <strong>Tour ${r}</strong> — ${escapeHtml(truncate(round.fake_news || '', 60))}
            ${ar.score != null ? ` — Score: ${ar.score}` : ''}
            ${isEliminated ? ' <span class="event-tag death">Eliminé</span>' : ''}
          </span>
          <span class="chevron">&#9654;</span>
        </div>
        <div class="accordion-body">
          <div class="confidence-row" style="margin-bottom: 1rem;">
            Confiance: <strong>${ar.confidence_initial ?? '?'}</strong>
            <span class="arrow">&rarr;</span>
            <strong>${ar.confidence_revised ?? '?'}</strong>
          </div>
          ${ar.political_color_before != null ? `
            <div style="margin-bottom: 1rem; font-size: 0.85rem;">
              Couleur politique:
              <span class="color-badge" style="background-color: ${politicalColorCSS(ar.political_color_before)}">${ar.political_color_before}</span>
              &rarr;
              <span class="color-badge" style="background-color: ${politicalColorCSS(ar.political_color_after)}">${ar.political_color_after}</span>
            </div>
          ` : ''}
          ${ar.vote_ranking && ar.vote_ranking.length > 0 ? `
            <div style="margin-bottom: 1rem; font-size: 0.85rem;">
              Vote: ${ar.vote_ranking.map((v, i) => `${i + 1}e=${v}`).join(', ')}
            </div>
          ` : ''}
          ${ar.final_response ? `
            <div class="md-content">${renderMarkdown(ar.final_response)}</div>
          ` : '<div style="color: var(--text-dim)">Pas de réponse enregistrée</div>'}
        </div>
      </div>
    `;
  }

  if (!html) {
    html = '<div class="empty-state">Aucun historique disponible</div>';
  }
  return html;
}

function buildDeathBox(death) {
  return `
    <div class="death-box">
      <h3>Mort</h3>
      <div class="field">
        <div class="field-label">Tour</div>
        <div class="field-value">${death.round || '?'}</div>
      </div>
      <div class="field">
        <div class="field-label">Score final</div>
        <div class="field-value">${death.final_score ?? '?'}</div>
      </div>
      <div class="field">
        <div class="field-label">Cause</div>
        <div class="field-value">${escapeHtml(death.cause || '?')}</div>
      </div>
      ${death.ranked_by && death.ranked_by.length > 0 ? `
        <div class="field">
          <div class="field-label">Classé par</div>
          <div class="field-value">${death.ranked_by.map(r => `${r.agent_name} (pos. ${r.position})`).join(', ')}</div>
        </div>
      ` : ''}
      ${death.last_message ? `
        <div class="last-message">${renderMarkdown(death.last_message)}</div>
      ` : ''}
    </div>
  `;
}

function truncate(s, len) {
  if (!s || s.length <= len) return s;
  return s.substring(0, len) + '...';
}

function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s || '';
  return div.innerHTML;
}
