/**
 * Maps political_color (0.0 - 1.0) to a CSS color.
 *
 * 0.0 (extrême droite) -> bleu foncé
 * 0.25 (droite) -> bleu clair
 * 0.5 (centre) -> blanc / gris clair
 * 0.75 (gauche) -> rose / rouge clair
 * 1.0 (extrême gauche) -> rouge vif
 */

const STOPS = [
  { pos: 0.0,  r: 30,  g: 60,  b: 180 },  // bleu foncé
  { pos: 0.25, r: 80,  g: 140, b: 230 },  // bleu clair
  { pos: 0.5,  r: 180, g: 175, b: 190 },  // gris lavande (centre)
  { pos: 0.75, r: 220, g: 100, b: 100 },  // rose / rouge clair
  { pos: 1.0,  r: 200, g: 30,  b: 30  },  // rouge vif
];

function lerp(a, b, t) {
  return Math.round(a + (b - a) * t);
}

export function politicalColorCSS(value) {
  if (value == null) return '#666';
  const v = Math.max(0, Math.min(1, value));

  // Find surrounding stops
  let lo = STOPS[0], hi = STOPS[STOPS.length - 1];
  for (let i = 0; i < STOPS.length - 1; i++) {
    if (v >= STOPS[i].pos && v <= STOPS[i + 1].pos) {
      lo = STOPS[i];
      hi = STOPS[i + 1];
      break;
    }
  }

  const t = hi.pos === lo.pos ? 0 : (v - lo.pos) / (hi.pos - lo.pos);
  const r = lerp(lo.r, hi.r, t);
  const g = lerp(lo.g, hi.g, t);
  const b = lerp(lo.b, hi.b, t);
  return `rgb(${r}, ${g}, ${b})`;
}

export function politicalLabel(value) {
  if (value == null) return '?';
  if (value <= 0.12) return 'Extr. droite';
  if (value <= 0.38) return 'Droite';
  if (value <= 0.62) return 'Centre';
  if (value <= 0.88) return 'Gauche';
  return 'Extr. gauche';
}
