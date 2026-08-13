import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const frontendRoot = resolve(process.cwd());
const read = (relativePath: string) => readFileSync(resolve(frontendRoot, relativePath), 'utf8');

describe('Actions frontend topology', () => {
  it('uses one Actions-owned manifest without inherited tier contracts', () => {
    const manifest = JSON.parse(read('package.json')) as {
      name?: string;
      author?: { name?: string };
      dependencies?: Record<string, string>;
    };

    expect(manifest.name).toBe('actions-runtime-frontend');
    expect(manifest.author?.name).toBe('Josh Yorko');
    expect(JSON.stringify(manifest)).not.toMatch(/sema4ai|community|enterprise/i);
    expect(existsSync(resolve(frontendRoot, 'package.json.community'))).toBe(false);
    expect(existsSync(resolve(frontendRoot, 'package.json.enterprise'))).toBe(false);
    expect(existsSync(resolve(frontendRoot, 'feature-boundaries.json'))).toBe(false);
    expect(existsSync(resolve(frontendRoot, 'src/enterprise'))).toBe(false);
  });

  it('defines independent Runtime and Canvas View application entries', () => {
    expect(existsSync(resolve(frontendRoot, 'apps/runtime/index.html'))).toBe(true);
    expect(existsSync(resolve(frontendRoot, 'apps/runtime/src/main.tsx'))).toBe(true);
    expect(existsSync(resolve(frontendRoot, 'apps/canvas-view/index.html'))).toBe(true);
    expect(existsSync(resolve(frontendRoot, 'apps/canvas-view/src/main.tsx'))).toBe(true);

    const runtimeEntry = read('apps/runtime/src/main.tsx');
    const canvasEntry = read('apps/canvas-view/src/main.tsx');
    expect(runtimeEntry).toContain("from '../../../src/App'");
    expect(canvasEntry).not.toContain("from '../../../src/App'");
    expect(canvasEntry).toContain('Canvas View');
  });

  it('keeps App.tsx as composition while feature boundaries own shell and routes', () => {
    const app = read('src/App.tsx');

    expect(app.split('\n').length).toBeLessThan(120);
    expect(app).toContain('RuntimeShell');
    expect(app).toContain('RuntimeRoutes');
    expect(existsSync(resolve(frontendRoot, 'src/app/RuntimeShell.tsx'))).toBe(true);
    expect(existsSync(resolve(frontendRoot, 'src/app/RuntimeRoutes.tsx'))).toBe(true);
  });
});
