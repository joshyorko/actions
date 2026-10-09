import fixture from "../../../../../docs/contracts/canvas/fixtures/query-results-v0.1.fixture.json";

interface HarnessFrame {
    contentWindow: {
        postMessage(message: unknown, targetOrigin: string): void;
    } | null;
    src: string;
}

const frame = document.querySelector("#canvas-view") as unknown as HarnessFrame;
const protocol = document.querySelector("#host-protocol")!;
const origin = window.location.origin;
let initialized = false;

function send(method: string, params: unknown): void {
    const target = frame.contentWindow;
    if (!target) throw new Error("Canvas iframe is unavailable.");
    target.postMessage({ jsonrpc: "2.0", method, params }, origin);
}

function sendInput(query: string): void {
    send("ui/notifications/tool-input", {
        arguments: { query, hostOnlySecretSentinel: "must-not-render" },
    });
    send("ui/notifications/tool-result", {
        content: [{ type: "text", text: "Host invocation completed" }],
    });
}

window.addEventListener("message", (event) => {
    if (event.source !== frame.contentWindow || event.origin !== origin) return;
    const message = event.data as Record<string, unknown> | null;
    if (!message || message.jsonrpc !== "2.0") return;
    if (message.method === "ui/initialize" && typeof message.id === "number") {
        const params = message.params as { protocolVersion?: string };
        protocol.textContent = params.protocolVersion ?? "missing";
        frame.contentWindow?.postMessage(
            {
                jsonrpc: "2.0",
                id: message.id,
                result: {
                    protocolVersion: params.protocolVersion,
                    hostCapabilities: { serverTools: {} },
                    hostInfo: { name: "local-fixture-host", version: "0.1.0" },
                    hostContext: { theme: "light", locale: "en-US" },
                },
            },
            origin,
        );
        return;
    }
    if (message.method === "ui/notifications/initialized") {
        initialized = true;
        sendInput("alpha");
        return;
    }
    if (message.method === "tools/call" && typeof message.id === "number") {
        const params = message.params as {
            name?: string;
            arguments?: Record<string, unknown>;
        };
        const query = params.arguments?.query;
        let structuredContent: unknown;
        if (params.name === "canvas_fixture_search") {
            structuredContent =
                query === "alpha" ? fixture.success : fixture.domainError;
        } else if (params.name === "canvas_fixture_artifact_status") {
            structuredContent = { status: "ready" };
        } else {
            frame.contentWindow?.postMessage(
                {
                    jsonrpc: "2.0",
                    id: message.id,
                    error: { code: -32601, message: "Tool not found" },
                },
                origin,
            );
            return;
        }
        frame.contentWindow?.postMessage(
            {
                jsonrpc: "2.0",
                id: message.id,
                result: {
                    content: [{ type: "text", text: "Fixture response" }],
                    structuredContent,
                },
            },
            origin,
        );
    }
});

document.querySelector("#replace-input")?.addEventListener("click", () => {
    if (initialized) sendInput("beta");
});
document.querySelector("#replace-context")?.addEventListener("click", () => {
    if (initialized)
        send("ui/notifications/host-context-changed", {
            theme: "dark",
            locale: "fr-FR",
        });
});
document.querySelector("#remount")?.addEventListener("click", () => {
    initialized = false;
    frame.src = "/index.html?remount=" + Date.now();
});
