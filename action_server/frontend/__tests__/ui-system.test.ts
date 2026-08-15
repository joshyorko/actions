import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

const frontendRoot = resolve(__dirname, '..');
const css = readFileSync(resolve(frontendRoot, 'src/index.css'), 'utf8');
const canvasHtml = readFileSync(resolve(frontendRoot, 'apps/canvas-view/index.html'), 'utf8');
const canvasMain = readFileSync(resolve(frontendRoot, 'apps/canvas-view/src/main.tsx'), 'utf8');

function parseHsl(value: string) {
  const [hue, saturation, lightness] = value.split(/\s+/).map(Number.parseFloat);
  const s = saturation / 100;
  const l = lightness / 100;
  const chroma = (1 - Math.abs(2 * l - 1)) * s;
  const x = chroma * (1 - Math.abs(((hue / 60) % 2) - 1));
  const match = hue < 60 ? [chroma, x, 0]
    : hue < 120 ? [x, chroma, 0]
      : hue < 180 ? [0, chroma, x]
        : hue < 240 ? [0, x, chroma]
          : hue < 300 ? [x, 0, chroma]
            : [chroma, 0, x];
  const offset = l - chroma / 2;
  return match.map((channel) => channel + offset);
}

function relativeLuminance(rgb: number[]) {
  return rgb
    .map((channel) => (channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4))
    .reduce((total, channel, index) => total + channel * [0.2126, 0.7152, 0.0722][index], 0);
}

function contrastRatio(first: number[], second: number[]) {
  const firstLuminance = relativeLuminance(first);
  const secondLuminance = relativeLuminance(second);
  return (Math.max(firstLuminance, secondLuminance) + 0.05)
    / (Math.min(firstLuminance, secondLuminance) + 0.05);
}

function darkToken(name: string) {
  const darkBlock = css.match(/\.dark\s*\{([\s\S]*?)\n\s{2}\}/)?.[1] ?? '';
  return darkBlock.match(new RegExp(`--${name}:\\s*([^;]+)`))?.[1] ?? '';
}

function lightToken(name: string) {
  const rootBlock = css.match(/:root\s*\{([\s\S]*?)\n\s{2}\}/)?.[1] ?? '';
  return rootBlock.match(new RegExp(`--${name}:\\s*([^;]+)`))?.[1] ?? '';
}

describe('owned UI system contract', () => {
  it('does not depend on remote fonts or presentation assets', () => {
    expect(css).not.toMatch(/fonts\.googleapis\.com|fonts\.gstatic\.com/);
    expect(css).not.toMatch(/@import\s+url\(/);
  });

  it('defines semantic light and dark theme tokens', () => {
    for (const token of ['background', 'foreground', 'card', 'primary', 'muted', 'border', 'ring']) {
      expect(css).toMatch(new RegExp(`--${token}:`));
      expect(css).toMatch(new RegExp(`\\.dark[\\s\\S]*--${token}:`));
    }
  });

  it('keeps muted text above WCAG AA on light and dark semantic surfaces', () => {
    for (const tokenReader of [lightToken, darkToken]) {
      const mutedForeground = parseHsl(tokenReader('muted-foreground'));
      for (const surface of ['background', 'card', 'muted']) {
        expect(contrastRatio(mutedForeground, parseHsl(tokenReader(surface)))).toBeGreaterThanOrEqual(4.5);
      }
    }
  });

  it('disables motion for reduced-motion users at the system boundary', () => {
    expect(css).toMatch(/@media\s*\(prefers-reduced-motion:\s*reduce\)/);
    expect(css).toMatch(/animation:\s*none/);
    expect(css).toMatch(
      /@media\s*\(prefers-reduced-motion:\s*reduce\)[\s\S]*?\*[\s\S]*?animation:\s*none\s*!important/,
    );
  });

  it('keeps the Canvas entrypoint CSP-safe and offline-capable', () => {
    expect(canvasHtml).not.toMatch(/fonts\.googleapis\.com|fonts\.gstatic\.com/);
    expect(canvasHtml).not.toMatch(/<style|\son[a-z]+=/i);
    expect(canvasMain).not.toMatch(/https?:\/\//);
    expect(canvasMain).not.toMatch(/style={{/);
  });
});
