export const PALETTES: Record<string, { label: string; vars: Record<string, string> }> = {
  default: { label: 'Праздничная ночь', vars: {} },
  halloween: {
    label: 'Хеллоуин',
    vars: {
      '--gold': '#ff8c1a',
      '--gold-light': '#ffc27a',
      '--gold-deep': '#d96f08',
      '--accent': '#ff8c1a',
      '--accent-warm': '#ffc27a',
      '--berry': '#e5581f',
      '--bg': '#1d1206',
    },
  },
  newyear: {
    label: 'Новый год',
    vars: {
      '--gold': '#8fd6ff',
      '--gold-light': '#d8f1ff',
      '--gold-deep': '#5db4e8',
      '--accent': '#8fd6ff',
      '--accent-warm': '#d8f1ff',
      '--berry': '#7fb0ff',
      '--bg': '#0d1b2a',
    },
  },
};

const ALL_KEYS = Array.from(new Set(Object.values(PALETTES).flatMap((p) => Object.keys(p.vars))));

export function paletteLabel(key: string | null | undefined): string {
  return PALETTES[key || 'default']?.label ?? PALETTES.default.label;
}

export function applyPalette(key: string | null | undefined) {
  const vars = PALETTES[key || 'default']?.vars ?? {};
  ALL_KEYS.forEach((k) => document.documentElement.style.removeProperty(k));
  Object.entries(vars).forEach(([k, v]) => document.documentElement.style.setProperty(k, v));
}


export function hexToRgbTriple(hex: string | null | undefined): string | null {
  if (!hex) return null;
  const m = hex.trim().match(/^#?([0-9a-f]{6})$/i);
  if (!m) return null;
  const n = parseInt(m[1], 16);
  return `${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}`;
}

export function applySurfaceColor(hex: string | null | undefined) {
  const triple = hexToRgbTriple(hex);
  if (triple) {
    document.documentElement.style.setProperty('--surface-rgb', triple);
  } else {
    document.documentElement.style.removeProperty('--surface-rgb');
  }
}
