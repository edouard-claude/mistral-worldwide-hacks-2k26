/**
 * Render markdown to HTML using marked.js (loaded via CDN).
 */
export function renderMarkdown(md) {
  if (!md) return '';
  if (typeof marked !== 'undefined') {
    return marked.parse(md);
  }
  // Fallback: basic escaping + line breaks
  return md
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>');
}
