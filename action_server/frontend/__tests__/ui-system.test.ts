import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

const frontendRoot = resolve(__dirname, '..');
const css = readFileSync(resolve(frontendRoot, 'src/index.css'), 'utf8');
const canvasHtml = readFileSync(resolve(frontendRoot, 'apps/canvas-view/index.html'), 'utf8');
const canvasMain = readFileSync(resolve(frontendRoot, 'apps/canvas-view/src/main.tsx'), 'utf8');

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

  it('disables motion for reduced-motion users at the system boundary', () => {
    expect(css).toMatch(/@media\s*\(prefers-reduced-motion:\s*reduce\)/);
    expect(css).toMatch(/animation:\s*none/);
  });

  it('keeps the Canvas entrypoint CSP-safe and offline-capable', () => {
    expect(canvasHtml).not.toMatch(/fonts\.googleapis\.com|fonts\.gstatic\.com/);
    expect(canvasHtml).not.toMatch(/<style|\son[a-z]+=/i);
    expect(canvasMain).not.toMatch(/https?:\/\//);
    expect(canvasMain).not.toMatch(/style={{/);
  });
});
