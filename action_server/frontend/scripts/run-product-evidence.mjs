import { execFileSync } from "node:child_process";
import { readdirSync, readFileSync, rmSync } from "node:fs";
import { join, resolve } from "node:path";

const root = process.cwd();
const npm = process.platform === "win32" ? "npm.cmd" : "npm";
const playwright = join(
    root,
    "node_modules",
    ".bin",
    process.platform === "win32" ? "playwright.cmd" : "playwright",
);
const outputDirectories = [
    "reports/product-evidence/first",
    "reports/product-evidence/second",
];

execFileSync(npm, ["run", "build:artifacts"], {
    cwd: root,
    env: process.env,
    stdio: "inherit",
});

for (const outputDirectory of outputDirectories) {
    rmSync(resolve(root, outputDirectory), { force: true, recursive: true });
    execFileSync(
        playwright,
        ["test", "--config=playwright.product-evidence.config.ts"],
        {
            cwd: root,
            env: {
                ...process.env,
                PRODUCT_EVIDENCE_OUTPUT_DIR: outputDirectory,
            },
            stdio: "inherit",
        },
    );
}

const readManifest = (outputDirectory) => {
    const directory = resolve(root, outputDirectory);
    const manifests = readdirSync(directory).filter((file) =>
        file.endsWith(".json"),
    );
    if (manifests.length !== 1)
        throw new Error(
            `Expected one product-evidence manifest in ${directory}`,
        );
    return JSON.parse(readFileSync(join(directory, manifests[0]), "utf8"));
};

const first = JSON.stringify(readManifest(outputDirectories[0]));
const second = JSON.stringify(readManifest(outputDirectories[1]));
if (first !== second)
    throw new Error("Repeated product-evidence output differs");

console.log("Repeated product-evidence output matched exactly");
