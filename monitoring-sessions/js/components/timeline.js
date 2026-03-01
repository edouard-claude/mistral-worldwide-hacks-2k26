/**
 * Renders horizontal timeline of rounds.
 */
import { politicalColorCSS } from './political-color.js';

export function renderTimeline(session, container) {
  if (!session.timeline || session.timeline.length === 0) {
    container.innerHTML = '<div class="empty-state">Aucun tour dans cette session</div>';
    return;
  }

  const wrap = document.createElement('div');
  wrap.className = 'timeline';

  for (const t of session.timeline) {
    const el = document.createElement('div');
    el.className = 'timeline-round';
    el.addEventListener('click', () => {
      location.hash = `#/session/${session.session_id}/round/${t.round}`;
    });

    // Round number
    const roundNum = document.createElement('div');
    roundNum.className = 'round-num';
    roundNum.textContent = `Tour ${t.round}`;
    el.appendChild(roundNum);

    // Fake news
    const fn = document.createElement('div');
    fn.className = 'round-fn';
    fn.textContent = t.fake_news || '—';
    el.appendChild(fn);

    // Agent avatars
    const avatars = document.createElement('div');
    avatars.className = 'avatars';
    for (const a of t.agents_present) {
      const av = document.createElement('div');
      av.className = 'avatar';
      av.style.backgroundColor = politicalColorCSS(a.political_color);
      av.textContent = a.name.substring(0, 2);
      av.title = a.name;

      // Mark eliminated agent
      const roundData = session.rounds[t.round];
      if (roundData && roundData.eliminated_id === a.id) {
        av.classList.add('dead');
      }
      // Mark cloned agent
      if (roundData && roundData.cloned_id === a.id) {
        av.classList.add('born');
      }

      avatars.appendChild(av);
    }
    el.appendChild(avatars);

    // Events
    const events = document.createElement('div');
    events.className = 'events';
    if (t.died) {
      const tag = document.createElement('span');
      tag.className = 'event-tag death';
      tag.textContent = `☠ ${t.died}`;
      events.appendChild(tag);
    }
    if (t.born) {
      const tag = document.createElement('span');
      tag.className = 'event-tag clone';
      tag.textContent = `+ ${t.born}`;
      events.appendChild(tag);
    }
    el.appendChild(events);

    wrap.appendChild(el);
  }

  container.appendChild(wrap);
}
