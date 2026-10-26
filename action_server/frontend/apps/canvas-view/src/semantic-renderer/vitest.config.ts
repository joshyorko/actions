import path from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

const semanticRendererRoot = path.dirname(fileURLToPath(import.meta.url));
const canvasViewRoot = path.resolve(semanticRendererRoot, "../..");
const frontendRoot = path.resolve(canvasViewRoot, "../..");

export default defineConfig({
    root: canvasViewRoot,
    test: {
        environment: "jsdom",
        globals: true,
        include: ["src/semantic-renderer/**/*.test.tsx"],
        setupFiles: [path.join(frontendRoot, "__tests__/a11y/setup.ts")],
    },
});
