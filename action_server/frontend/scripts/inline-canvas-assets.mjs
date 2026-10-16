import { readFile, readdir, rmdir, unlink, writeFile } from "node:fs/promises";
import { join } from "node:path";

const root = join(process.cwd(), "dist-canvas");
let html = await readFile(join(root, "index.html"), "utf8");
const escapeJs = (source) =>
    source
        .replace(/<\/script/gi, "\\x3C/script")
        .replace(/<!--/g, "\\x3C!--")
        .replace(/<!doctype/gi, "\\x3C!doctype");
const escapeCss = (source) => source.replace(/<\/style/gi, "\\3C/style");

function replaceOnce(document, marker, replacement, file) {
    const first = document.indexOf(marker);
    if (first < 0 || document.indexOf(marker, first + marker.length) >= 0) {
        throw new Error(`Expected one HTML marker for ${file}`);
    }
    return document.replace(marker, () => replacement);
}

for (const file of (await readdir(join(root, "assets"))).sort()) {
    const path = join(root, "assets", file);
    const source = await readFile(path, "utf8");
    if (file.endsWith(".js")) {
        html = replaceOnce(
            html,
            `<script type="module" crossorigin src="/assets/${file}"></script>`,
            `<script type="module">${escapeJs(source)}</script>`,
            file,
        );
    } else if (file.endsWith(".css")) {
        html = replaceOnce(
            html,
            `<link rel="stylesheet" crossorigin href="/assets/${file}">`,
            `<style>${escapeCss(source)}</style>`,
            file,
        );
    } else {
        throw new Error(`Unexpected external Canvas asset: ${file}`);
    }
    await unlink(path);
}
await rmdir(join(root, "assets"));
if (
    /<(?:script|link|img|iframe|audio|video|source)\b[^>]*(?:\bsrc|\bhref)\s*=/iu.test(
        html,
    )
) {
    throw new Error(
        "Canvas MCP resource contains an external or relative asset reference",
    );
}
const styles = [...html.matchAll(/<style>([\s\S]*?)<\/style>/giu)].map(
    (match) => match[1],
);
if (styles.some((style) => /url\(\s*["']?(?:https?:|\/\/|\/)/iu.test(style))) {
    throw new Error(
        "Canvas MCP resource CSS references a network or root-relative asset",
    );
}
await writeFile(join(root, "index.html"), html);
