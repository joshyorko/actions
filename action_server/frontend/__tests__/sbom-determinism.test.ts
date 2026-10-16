// @vitest-environment node
import {
    mkdtempSync,
    mkdirSync,
    readFileSync,
    rmSync,
    writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { delimiter, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { expect, test } from "vitest";

const frontend = resolve(process.cwd());
const scripts = JSON.parse(
    readFileSync(join(frontend, "package.json"), "utf8"),
).scripts;

test("retained SBOM bytes follow the lock graph despite npm cleanup residue", () => {
    const root = mkdtempSync(join(tmpdir(), "actions-sbom-"));
    const write = (path: string, content: object) =>
        writeFileSync(join(root, path), JSON.stringify(content));
    const generate = (name: string) => {
        // Run the actual package script and installed tool, not a serialization mock.
        const result = spawnSync(
            process.execPath,
            [process.env.npm_execpath!, "run", name, "--silent"],
            {
                cwd: root,
                env: {
                    ...process.env,
                    PATH: `${join(frontend, "node_modules", ".bin")}${delimiter}${process.env.PATH}`,
                },
                encoding: "utf8",
                timeout: 20_000,
            },
        );
        expect(result.status, result.stderr).toBe(0);
        return readFileSync(
            join(
                root,
                name === "sbom:runtime"
                    ? "dist/sbom.json"
                    : "dist-canvas/sbom.json",
            ),
            "utf8",
        );
    };
    try {
        mkdirSync(join(root, "dist"));
        mkdirSync(join(root, "dist-canvas"));
        write("package.json", {
            name: "sbom-fixture",
            version: "1.0.0",
            scripts: {
                "sbom:runtime": scripts["sbom:runtime"],
                "sbom:canvas": scripts["sbom:canvas"],
            },
        });
        const lock = {
            name: "sbom-fixture",
            version: "1.0.0",
            lockfileVersion: 3,
            packages: { "": { name: "sbom-fixture", version: "1.0.0" } },
        };
        write("package-lock.json", lock);
        const first = [generate("sbom:runtime"), generate("sbom:canvas")];
        // Windows npm ci reported EPERM retaining this optional native-tool subtree.
        mkdirSync(join(root, "node_modules/node-gyp/node_modules/semver"), {
            recursive: true,
        });
        write("node_modules/node-gyp/node_modules/semver/package.json", {
            name: "semver",
            version: "7.7.3",
        });
        const second = [generate("sbom:runtime"), generate("sbom:canvas")];
        expect(second).toEqual(first);
        for (const document of second) {
            expect(JSON.parse(document).bomFormat).toBe("CycloneDX");
            expect(document).not.toContain('"name": "node-gyp"');
        }
        // Reproducibility must not discard declared dependency-graph changes.
        write("package-lock.json", {
            ...lock,
            packages: {
                ...lock.packages,
                "": {
                    ...lock.packages[""],
                    dependencies: { "declared-library": "1.2.3" },
                },
                "node_modules/declared-library": {
                    version: "1.2.3",
                    resolved:
                        "https://registry.npmjs.org/declared-library/-/declared-library-1.2.3.tgz",
                },
            },
        });
        const manifest = JSON.parse(
            readFileSync(join(root, "package.json"), "utf8"),
        );
        manifest.dependencies = { "declared-library": "1.2.3" };
        write("package.json", manifest);
        expect(generate("sbom:runtime")).toContain(
            '"name": "declared-library"',
        );
    } finally {
        rmSync(root, { recursive: true, force: true });
    }
}, 60_000);
