import { readdir, readFile } from 'node:fs/promises';
import { gzipSync } from 'node:zlib';
import { join, relative } from 'node:path';
import { createHash } from 'node:crypto';

const RAW_BUDGET = 1024 * 1024;
const GZIP_BUDGET = 300 * 1024;

for (const [directory, expectedArtifact, expectedType] of [['dist', 'runtime-admin', 'text/html'], ['dist-canvas', 'canvas-mcp-app', 'text/html;profile=mcp-app']]) {
  const root = join(process.cwd(), directory);
  const manifest = JSON.parse(await readFile(join(root, 'artifact-manifest.json')));
  async function files(dir) {
    const entries = await readdir(dir, { withFileTypes: true });
    const nested = await Promise.all(entries.map(async entry => {
      const path = join(dir, entry.name);
      return entry.isDirectory() ? files(path) : [path];
    }));
    return nested.flat();
  }
  const actualFiles = (await files(root))
    .map(file => relative(root, file).replaceAll('\\', '/'))
    .filter(file => !['artifact-manifest.json', 'sbom.json'].includes(file))
    .sort();
  const manifestFiles = manifest.files.map(file => file.path);
  if (manifest.artifact !== expectedArtifact || manifest.contentType !== expectedType) throw new Error(`${directory}: invalid artifact identity`);
  if (JSON.stringify(manifestFiles) !== JSON.stringify([...manifestFiles].sort()) || JSON.stringify(manifestFiles) !== JSON.stringify(actualFiles)) throw new Error(`${directory}: manifest inventory is incomplete or unsorted`);
  if (manifest.sourceMaps || manifest.files.some(file => file.path.endsWith('.map'))) throw new Error(`${directory}: source maps are forbidden`);
  const payload = await Promise.all(manifest.files.map(async file => {
    const bytes = await readFile(join(root, file.path));
    const hash = createHash('sha256').update(bytes).digest('hex');
    if (bytes.length !== file.bytes || hash !== file.sha256) throw new Error(`${directory}: manifest metadata mismatch for ${file.path}`);
    return bytes;
  }));
  const total = payload.reduce((sum, file) => sum + file.length, 0);
  const gzipTotal = payload.reduce((sum, file) => sum + gzipSync(file, { mtime: 0 }).length, 0);
  if (total > RAW_BUDGET || gzipTotal > GZIP_BUDGET) throw new Error(`${directory}: executable payload is ${total} raw / ${gzipTotal} gzip bytes`);
  const html = await readFile(join(root, 'index.html'), 'utf8');
  if (!html.includes(expectedType)) throw new Error(`${directory}: missing content type marker`);
  await readFile(join(root, 'sbom.json'));
  console.log(`${directory}: ${manifest.files.length} files, ${total} raw / ${gzipTotal} gzip bytes, ${manifest.contentType}`);
}
