import { lstat, readdir, readFile } from 'node:fs/promises';
import { gzipSync } from 'node:zlib';
import { join, relative } from 'node:path';
import { createHash } from 'node:crypto';

const RAW_BUDGET = 1024 * 1024;
const GZIP_BUDGET = 300 * 1024;

for (const [directory, expectedArtifact, expectedType] of [['dist', 'runtime-admin', 'text/html'], ['dist-canvas', 'canvas-mcp-app', 'text/html;profile=mcp-app']]) {
  const root = join(process.cwd(), directory);
  if ((await lstat(root)).isSymbolicLink()) throw new Error(`${directory}: symlink root is forbidden`);
  async function metadataFile(name) {
    const path = join(root, name);
    const entry = await lstat(path);
    if (entry.isSymbolicLink()) throw new Error(`${directory}: symlink metadata is forbidden: ${path}`);
    if (!entry.isFile()) throw new Error(`${directory}: non-regular metadata entry is forbidden: ${path}`);
    return path;
  }
  const manifestPath = await metadataFile('artifact-manifest.json');
  const sbomPath = await metadataFile('sbom.json');
  const manifest = JSON.parse(await readFile(manifestPath));
  if (manifest.schemaVersion !== 1) throw new Error(`${directory}: unsupported manifest schema`);
  const sbom = JSON.parse(await readFile(sbomPath));
  if (sbom.bomFormat !== 'CycloneDX' || !sbom.specVersion) throw new Error(`${directory}: invalid CycloneDX SBOM`);
  async function files(dir) {
    const entries = await readdir(dir, { withFileTypes: true });
    const nested = await Promise.all(entries.map(async entry => {
      const path = join(dir, entry.name);
      if (entry.isSymbolicLink()) throw new Error(`${directory}: symlink entry is forbidden: ${path}`);
      if (entry.isDirectory()) return files(path);
      if (!entry.isFile()) throw new Error(`${directory}: non-regular file entry is forbidden: ${path}`);
      return [path];
    }));
    return nested.flat();
  }
  const actualFiles = (await files(root))
    .map(file => relative(root, file).replaceAll('\\', '/'))
    .filter(file => !['artifact-manifest.json', 'sbom.json'].includes(file))
    .sort();
  const actualDirectories = [];
  async function directories(dir) {
    const entries = await readdir(dir, { withFileTypes: true });
    for (const entry of entries) {
      const path = join(dir, entry.name);
      if (entry.isDirectory()) {
        actualDirectories.push(relative(root, path).replaceAll('\\', '/'));
        await directories(path);
      }
    }
  }
  await directories(root);
  const manifestFiles = manifest.files.map(file => file.path);
  const expectedDirectories = [...new Set(manifestFiles.flatMap(file => {
    const parts = file.split('/');
    return parts.slice(0, -1).map((_, index) => parts.slice(0, index + 1).join('/'));
  }))].sort();
  if (manifest.artifact !== expectedArtifact || manifest.contentType !== expectedType) throw new Error(`${directory}: invalid artifact identity`);
  if (JSON.stringify(manifestFiles) !== JSON.stringify([...manifestFiles].sort()) || JSON.stringify(manifestFiles) !== JSON.stringify(actualFiles)) throw new Error(`${directory}: manifest inventory is incomplete or unsorted`);
  if (JSON.stringify(actualDirectories.sort()) !== JSON.stringify(expectedDirectories)) throw new Error(`${directory}: undeclared structural path`);
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
  console.log(`${directory}: ${manifest.files.length} files, ${total} raw / ${gzipTotal} gzip bytes, ${manifest.contentType}`);
}
