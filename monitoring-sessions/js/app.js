/**
 * Hash router + orchestration.
 * Routes:
 *   #/                           -> session list
 *   #/session/<id>               -> session overview
 *   #/session/<id>/round/<N>     -> round detail
 *   #/session/<id>/agent/<uuid>  -> agent detail
 */
import { renderSessionList } from './views/session-list.js';
import { renderSessionOverview } from './views/session-overview.js';
import { renderRoundDetail } from './views/round-detail.js';
import { renderAgentDetail } from './views/agent-detail.js';

const app = document.getElementById('app');
const breadcrumb = document.getElementById('breadcrumb');

function parseHash() {
  const hash = location.hash || '#/';
  const parts = hash.replace('#/', '').split('/').filter(Boolean);

  if (parts.length === 0) return { route: 'list' };
  if (parts[0] === 'session' && parts.length === 2) return { route: 'session', sessionId: parts[1] };
  if (parts[0] === 'session' && parts[2] === 'round' && parts.length === 4) return { route: 'round', sessionId: parts[1], round: parts[3] };
  if (parts[0] === 'session' && parts[2] === 'agent' && parts.length === 4) return { route: 'agent', sessionId: parts[1], agentId: parts[3] };
  return { route: 'list' };
}

function updateBreadcrumb(parsed) {
  let html = '';
  if (parsed.route === 'list') {
    html = '<span>Sessions</span>';
  } else if (parsed.route === 'session') {
    html = `<a href="#/">Sessions</a><span class="sep">/</span><span>${shortId(parsed.sessionId)}</span>`;
  } else if (parsed.route === 'round') {
    html = `<a href="#/">Sessions</a><span class="sep">/</span><a href="#/session/${parsed.sessionId}">${shortId(parsed.sessionId)}</a><span class="sep">/</span><span>Tour ${parsed.round}</span>`;
  } else if (parsed.route === 'agent') {
    html = `<a href="#/">Sessions</a><span class="sep">/</span><a href="#/session/${parsed.sessionId}">${shortId(parsed.sessionId)}</a><span class="sep">/</span><span>Agent</span>`;
  }
  breadcrumb.innerHTML = html;
}

function shortId(id) {
  return id.substring(0, 8);
}

async function route() {
  const parsed = parseHash();
  updateBreadcrumb(parsed);

  try {
    switch (parsed.route) {
      case 'list':
        await renderSessionList(app);
        break;
      case 'session':
        await renderSessionOverview(app, parsed.sessionId);
        break;
      case 'round':
        await renderRoundDetail(app, parsed.sessionId, parsed.round);
        break;
      case 'agent':
        await renderAgentDetail(app, parsed.sessionId, parsed.agentId);
        break;
    }
  } catch (err) {
    console.error(err);
    app.innerHTML = `<div class="empty-state"><div>Erreur de chargement</div><div style="font-size: 0.8rem; margin-top: 0.5rem;">${err.message}</div></div>`;
  }

  window.scrollTo(0, 0);
}

window.addEventListener('hashchange', route);
route();
