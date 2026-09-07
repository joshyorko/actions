import { createHash } from 'node:crypto';
import { readdir, readFile, writeFile } from 'node:fs/promises';
import { join, relative } from 'node:path';

const [, , directory, artifact, contentType] = process.argv;
const root = join(process.cwd(), directory);

async function files(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  const nested = await Promise.all(entries.sort((a, b) => a.name.localeCompare(b.name)).map(async entry => {
    const path = join(dir, entry.name);
    return entry.isDirectory() ? files(path) : [path];
  }));
  return nested.flat();
}

const manifestFiles = [];
for (const file of await files(root)) {
  const name = relative(root, file).replaceAll('\\', '/');
  if (name === 'artifact-manifest.json' || name === 'sbom.json') continue;
  const bytes = await readFile(file);
  manifestFiles.push({ path: name, bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') });
}
manifestFiles.sort((a, b) => a.path.localeCompare(b.path));
await writeFile(join(root, 'artifact-manifest.json'), JSON.stringify({ schemaVersion: 1, artifact, contentType, sourceMaps: false, files: manifestFiles }, null, 2) + '\n');
