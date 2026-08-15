import { readFile, readdir, unlink, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

const root = join(process.cwd(), 'dist');
let html = await readFile(join(root, 'index.html'), 'utf8');
for (const file of await readdir(join(root, 'assets'))) {
  const path = join(root, 'assets', file);
  const source = await readFile(path, 'utf8');
  if (file.endsWith('.js')) html = html.replace(new RegExp(`<script type="module"[^>]+src="/assets/${file}"></script>`), `<script type="module">${source}</script>`);
  if (file.endsWith('.css')) html = html.replace(new RegExp(`<link rel="stylesheet"[^>]+href="/assets/${file}">`), `<style>${source}</style>`);
  await unlink(path);
}
await writeFile(join(root, 'index.html'), html);
