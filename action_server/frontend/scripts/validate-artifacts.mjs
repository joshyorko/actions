import { readFile } from 'node:fs/promises';
import { join } from 'node:path';

for (const [directory, expectedArtifact, expectedType] of [['dist', 'runtime-admin', 'text/html'], ['dist-canvas', 'canvas-mcp-app', 'text/html;profile=mcp-app']]) {
  const root = join(process.cwd(), directory);
  const manifest = JSON.parse(await readFile(join(root, 'artifact-manifest.json')));
  if (manifest.artifact !== expectedArtifact || manifest.contentType !== expectedType) throw new Error(`${directory}: invalid artifact identity`);
  if (manifest.sourceMaps || manifest.files.some(file => file.path.endsWith('.map'))) throw new Error(`${directory}: source maps are forbidden`);
  const total = manifest.files.reduce((sum, file) => sum + file.bytes, 0);
  if (total > 1024 * 1024) throw new Error(`${directory}: ${total} bytes exceeds 1 MiB budget`);
  const html = await readFile(join(root, 'index.html'), 'utf8');
  if (!html.includes(expectedType)) throw new Error(`${directory}: missing content type marker`);
  await readFile(join(root, 'sbom.json'));
  console.log(`${directory}: ${manifest.files.length} files, ${total} bytes, ${manifest.contentType}`);
}
