import { readFile, readdir, unlink, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

const root = join(process.cwd(), 'dist');
let html = await readFile(join(root, 'index.html'), 'utf8');

const escapeInlineJavaScript = (source) =>
  source
    .replace(/<\/script/gi, '\\x3C/script')
    .replace(/<!--/g, '\\x3C!--')
    .replace(/<!doctype/gi, '\\x3C!doctype');

const escapeInlineCss = (source) => source.replace(/<\/style/gi, '\\3C/style');

const replaceAsset = (document, marker, replacement, file) => {
  const firstIndex = document.indexOf(marker);
  if (
    firstIndex === -1 ||
    document.indexOf(marker, firstIndex + marker.length) !== -1
  ) {
    throw new Error(`Expected exactly one HTML marker for ${file}`);
  }
  return document.replace(marker, () => replacement);
};

for (const file of (await readdir(join(root, 'assets'))).sort()) {
  const path = join(root, 'assets', file);
  const source = await readFile(path, 'utf8');
  if (file.endsWith('.js')) {
    const marker = `<script type="module" crossorigin src="/assets/${file}"></script>`;
    html = replaceAsset(
      html,
      marker,
      `<script type="module">${escapeInlineJavaScript(source)}</script>`,
      file,
    );
  }
  if (file.endsWith('.css')) {
    const marker = `<link rel="stylesheet" crossorigin href="/assets/${file}">`;
    html = replaceAsset(
      html,
      marker,
      `<style>${escapeInlineCss(source)}</style>`,
      file,
    );
  }
  await unlink(path);
}
await writeFile(join(root, 'index.html'), html);
