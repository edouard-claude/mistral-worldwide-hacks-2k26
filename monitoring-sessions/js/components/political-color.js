/**
 * Maps political_color (0.0 - 1.0) to a CSS color.
 *
 * 0.0 (extrême droite) -> rouge foncé
 * 0.3 (droite) -> orange
 * 0.5 (centre) -> violet
 * 0.75 (gauche) -> bleu
 * 1.0 (extrême gauche) -> rouge profond
 */

const STOPS = [
  { pos: 0.0,  r: 180, g: 30,  b: 30  },  // rouge foncé
  { pos: 0.3,  r: 220, g: 140, b: 30  },  // orange
  { pos: 0.5,  r: 140, g: 90,  b: 210 },  // violet
  { pos: 0.75, r: 50,  g: 120, b: 220 },  // bleu
  { pos: 1.0,  r: 160, g: 20,  b: 50  },  // rouge profond
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
  if (value <= 0.1) return 'Extr. droite';
  if (value <= 0.35) return 'Droite';
  if (value <= 0.65) return 'Centre';
  if (value <= 0.9) return 'Gauche';
  return 'Extr. gauche';
}
