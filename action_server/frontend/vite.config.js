/* eslint-disable import/no-extraneous-dependencies */
import { defineConfig } from 'vite';
import path from 'path';
import { fileURLToPath } from 'url';
import react from '@vitejs/plugin-react';

const frontendRoot = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig(({ mode }) => {
  const isCanvas = mode === 'canvas';
  const artifact = isCanvas ? 'canvas-mcp-app' : 'runtime-admin';
  const contentType = isCanvas ? 'text/html;profile=mcp-app' : 'text/html';
  const appRoot = path.join(frontendRoot, 'apps', isCanvas ? 'canvas-view' : 'runtime');

  return {
    root: appRoot,
    server: {
      port: isCanvas ? 8086 : 8085,
      proxy: {
        '/api': 'http://localhost:8080',
        '/openapi.json': 'http://localhost:8080',
        '/config': 'http://localhost:8080',
        '/api/ws': { target: 'ws://localhost:8080', ws: true },
      },
    },
    resolve: {
      alias: {
        '~': path.join(frontendRoot, 'src'),
        '@/core': path.join(frontendRoot, 'src/core'),
        '@/shared': path.join(frontendRoot, 'src/shared'),
        '@/queries': path.join(frontendRoot, 'src/queries'),
      },
      mainFields: ['module', 'main', 'browser'],
    },
    plugins: [react()],
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: path.join(frontendRoot, '__tests__/a11y/setup.ts'),
      include: [path.join(frontendRoot, '__tests__/**/*.test.{ts,tsx}')],
      exclude: ['**/node_modules/**', '**/__tests__/visual/**', '**/*.backup'],
      coverage: { provider: 'v8', reporter: ['text', 'lcov'] },
    },
    build: {
      outDir: path.join(frontendRoot, isCanvas ? 'dist-canvas' : 'dist'),
      emptyOutDir: true,
      sourcemap: false,
      rollupOptions: {
        output: {
          entryFileNames: 'assets/[name]-[hash].js',
          chunkFileNames: 'assets/[name]-[hash].js',
          assetFileNames: 'assets/[name]-[hash].[ext]',
        },
      },
    },
    define: { __ACTIONS_FRONTEND_ARTIFACT__: JSON.stringify(artifact), __ACTIONS_FRONTEND_CONTENT_TYPE__: JSON.stringify(contentType) },
  };
});
