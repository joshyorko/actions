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
    expect(runtimeEntry).toContain("../../../src/App");
    expect(canvasEntry).not.toContain("from '../../../src/App'");
    expect(canvasEntry).toContain('Canvas View');
    expect(read('apps/runtime/index.html')).toContain('/src/main.tsx');
    expect(read('apps/canvas-view/index.html')).toContain('/src/main.tsx');
  });

  it('keeps App.tsx as composition while feature boundaries own shell and routes', () => {
    const app = read('src/App.tsx');
    const shell = read('src/app/RuntimeShell.tsx');

    expect(app.split('\n').length).toBeLessThan(120);
    expect(app).toContain('RuntimeShell');
    expect(app).toContain('RuntimeRoutes');
    expect(existsSync(resolve(frontendRoot, 'src/app/RuntimeShell.tsx'))).toBe(true);
    expect(existsSync(resolve(frontendRoot, 'src/app/RuntimeRoutes.tsx'))).toBe(true);
    expect(existsSync(resolve(frontendRoot, 'src/app/RuntimeNavigation.tsx'))).toBe(true);
    expect(existsSync(resolve(frontendRoot, 'src/app/RuntimeLayout.tsx'))).toBe(true);
    expect(existsSync(resolve(frontendRoot, 'src/app/RuntimeProviders.tsx'))).toBe(true);
    expect(shell).not.toMatch(/<Route\b|<Routes\b|<Navigation\b|createContext/);
  });

  it('keeps the shipping Runtime route set and excludes removed enterprise routes', () => {
    const routes = read('src/app/RuntimeRoutes.tsx');

    for (const path of ['/actions', '/runs', '/schedules', '/robots', '/work-items', '/analytics', '/logs/:runId', '/artifacts/:runId']) {
      expect(routes).toContain(`path="${path}"`);
    }
    for (const removedRoute of ['/knowledge-base', '/org-management', '/sso']) {
      expect(routes).not.toContain(removedRoute);
    }
  });

  it('defines the calm workbench route and object-to-run context contract', () => {
    const routes = read('src/app/RuntimeRoutes.tsx');
    const navigation = read('src/app/RuntimeNavigation.tsx');
    const layout = read('src/app/RuntimeLayout.tsx');

    expect(routes).toContain('path="/"');
    expect(routes).toContain('Overview');
    expect(routes).toContain('path="/actions/:actionId"');
    expect(routes).toContain('path="/runs/:runId"');
    expect(navigation).toContain('Actions Runtime');
    expect(navigation).toContain('aria-label="Close Runtime menu"');
    expect(navigation).toContain('Primary');
    expect(navigation).toContain('Reference');
    expect(layout).toContain('aria-label="Breadcrumb"');
    expect(layout).toContain('aria-label="Open Runtime menu"');
    expect(navigation).toContain('data-testid="mobile-menu-backdrop"');
  });

  it('defines the visual contract as a calm, offline-safe workbench', () => {
    const css = read('src/index.css');

    expect(css).toContain('--execution-accent');
    expect(css).toContain('--workbench-rule');
    expect(css).toContain('--radius-panel');
    expect(css).toContain('--radius-control');
    expect(css).not.toMatch(/https?:\/\//);
    expect(css).not.toMatch(/gradient|glow/i);
    expect(css).toContain('prefers-reduced-motion: reduce');
  });

  it('keeps persisted sidebar and theme controls in Runtime navigation', () => {
    const navigation = read('src/app/RuntimeNavigation.tsx');

    expect(navigation).toContain('sidebar-collapsed');
    expect(navigation).toContain('useTheme');
    expect(navigation).toContain('cycleTheme');
  });

  it('defines a bounded fail-fast quality gate', () => {
    const manifest = JSON.parse(read('package.json')) as {
      scripts: Record<string, string>;
    };

    expect(manifest.scripts['test:quality']).toContain('test:lint');
    expect(manifest.scripts['test:quality']).not.toContain('||');
    expect(manifest.scripts['test:lint']).toContain('src/app');
    expect(manifest.scripts['test:lint']).not.toMatch(/\s\.\s*$/);
  });
});
