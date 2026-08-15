import { readFile } from 'node:fs/promises';
import { gzipSync } from 'node:zlib';
import { join } from 'node:path';

const RAW_BUDGET = 1024 * 1024;
const GZIP_BUDGET = 300 * 1024;

for (const [directory, expectedArtifact, expectedType] of [['dist', 'runtime-admin', 'text/html'], ['dist-canvas', 'canvas-mcp-app', 'text/html;profile=mcp-app']]) {
  const root = join(process.cwd(), directory);
  const manifest = JSON.parse(await readFile(join(root, 'artifact-manifest.json')));
  if (manifest.artifact !== expectedArtifact || manifest.contentType !== expectedType) throw new Error(`${directory}: invalid artifact identity`);
  if (manifest.sourceMaps || manifest.files.some(file => file.path.endsWith('.map'))) throw new Error(`${directory}: source maps are forbidden`);
  const payload = await Promise.all(manifest.files.map(async file => readFile(join(root, file.path))));
  const total = manifest.files.reduce((sum, file) => sum + file.bytes, 0);
  const gzipTotal = payload.reduce((sum, file) => sum + gzipSync(file, { mtime: 0 }).length, 0);
  if (total > RAW_BUDGET || gzipTotal > GZIP_BUDGET) throw new Error(`${directory}: executable payload is ${total} raw / ${gzipTotal} gzip bytes`);
  const html = await readFile(join(root, 'index.html'), 'utf8');
  if (!html.includes(expectedType)) throw new Error(`${directory}: missing content type marker`);
  await readFile(join(root, 'sbom.json'));
  console.log(`${directory}: ${manifest.files.length} files, ${total} raw / ${gzipTotal} gzip bytes, ${manifest.contentType}`);
}
