/**
 * Round detail view — route #/session/<id>/round/<N>
 */
import { loadSession } from '../data-loader.js';
import { politicalColorCSS, politicalLabel } from '../components/political-color.js';
import { renderMarkdown } from '../components/markdown.js';

export async function renderRoundDetail(app, sessionId, roundNum) {
  app.innerHTML = '<div class="loading">Chargement...</div>';

  const session = await loadSession(sessionId);
  const round = session.rounds[roundNum];

  if (!round) {
    app.innerHTML = `
      <button class="back-btn" onclick="location.hash='#/session/${sessionId}'">&larr; Retour</button>
      <div class="empty-state">Tour ${roundNum} introuvable</div>
    `;
    return;
  }

  // Build agent cards HTML
  const agentCards = buildAgentCards(session, round);
  const voteBar = buildVoteBar(session, round);

  app.innerHTML = `
    <button class="back-btn" id="back-btn">&larr; Retour à la session</button>
    <div class="round-header">
      <h1>Tour ${round.round_number}</h1>
      <div class="fn-full">${escapeHtml(round.fake_news || '—')}</div>
    </div>

    <h2 class="section-title">Agents</h2>
    <div class="agent-grid">${agentCards}</div>

    ${voteBar}

    <h2 class="section-title">Transcriptions</h2>
    <div class="tabs" id="chat-tabs">
      <button class="tab active" data-phase="2">Phase 2 — Débat</button>
      <button class="tab" data-phase="3">Phase 3 — Réponses finales</button>
    </div>
    <div class="chat-transcript" id="chat-content">
      <div class="md-content">${renderMarkdown(round.chat_phase2 || '*Pas de transcription*')}</div>
    </div>
  `;

  // Back button
  document.getElementById('back-btn').addEventListener('click', () => {
    location.hash = `#/session/${sessionId}`;
  });

  // Tab switching
  const tabs = document.querySelectorAll('#chat-tabs .tab');
  const chatContent = document.getElementById('chat-content');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const phase = tab.dataset.phase;
      const md = phase === '2' ? round.chat_phase2 : round.chat_phase3;
      chatContent.innerHTML = `<div class="md-content">${renderMarkdown(md || '*Pas de transcription*')}</div>`;
    });
  });
}

function buildAgentCards(session, round) {
  let html = '';
  for (const agentId of round.agents_present) {
    const agent = session.agents[agentId];
    if (!agent) continue;
    const ar = round.agent_rounds[agentId] || {};

    const isEliminated = round.eliminated_id === agentId;
    const isCloned = round.cloned_id === agentId;
    let cardClass = 'agent-card';
    if (isEliminated) cardClass += ' eliminated';
    if (isCloned) cardClass += ' cloned';

    const color = politicalColorCSS(ar.political_color_before ?? agent.political_color_initial);
    const colorLabel = politicalLabel(ar.political_color_before ?? agent.political_color_initial);

    html += `
      <div class="${cardClass}">
        <div class="agent-top">
          <div class="avatar" style="background-color: ${color}">${agent.name.substring(0, 2)}</div>
          <div>
            <div class="agent-name"><a href="#/session/${session.session_id}/agent/${agent.id}">${escapeHtml(agent.name)}</a></div>
            <span class="color-badge" style="background-color: ${color}">${colorLabel}</span>
          </div>
        </div>
        <div class="confidence-row">
          Confiance: <strong>${ar.confidence_initial ?? '?'}</strong>
          <span class="arrow">&rarr;</span>
          <strong>${ar.confidence_revised ?? '?'}</strong>
        </div>
        ${ar.final_response ? `<div class="message-preview">${renderMarkdown(truncate(ar.final_response, 200))}</div>` : ''}
        ${ar.score != null ? `<span class="score-badge">Score: ${ar.score}</span>` : ''}
        ${isEliminated ? '<span class="event-tag death" style="margin-left: 0.5rem">Eliminé</span>' : ''}
        ${isCloned ? '<span class="event-tag clone" style="margin-left: 0.5rem">Clone</span>' : ''}
      </div>
    `;
  }
  return html;
}

function buildVoteBar(session, round) {
  const entries = [];
  for (const agentId of round.agents_present) {
    const agent = session.agents[agentId];
    const ar = round.agent_rounds[agentId];
    if (!agent || !ar || ar.score == null) continue;
    entries.push({
      name: agent.name,
      score: ar.score,
      color: politicalColorCSS(ar.political_color_before ?? agent.political_color_initial),
    });
  }

  if (entries.length === 0) return '';

  entries.sort((a, b) => b.score - a.score);
  const maxScore = Math.max(...entries.map(e => e.score), 1);

  let barHtml = '';
  let labelsHtml = '';
  for (const e of entries) {
    barHtml += `<div class="bar-segment" style="flex: ${e.score}; background-color: ${e.color}">${e.name} (${e.score})</div>`;
    labelsHtml += `<div class="vbl"><div class="vbl-dot" style="background-color: ${e.color}"></div>${e.name}: ${e.score}</div>`;
  }

  return `
    <div class="vote-bar-section">
      <h2 class="section-title">Résultats du vote</h2>
      <div class="vote-bar">${barHtml}</div>
      <div class="vote-bar-labels">${labelsHtml}</div>
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
