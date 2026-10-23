import path from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

const canvasViewRoot = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(canvasViewRoot, "../..");

export default defineConfig({
    root: canvasViewRoot,
    test: {
        environment: "jsdom",
        globals: true,
        include: ["src/**/*.test.tsx"],
        setupFiles: [path.join(frontendRoot, "__tests__/a11y/setup.ts")],
    },
});
