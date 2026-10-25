import { useMemo, useState } from "react";
import type { App } from "@modelcontextprotocol/ext-apps/react";
import { SemanticCanvasRenderer } from "./components";
import type { CanvasAppMetadata } from "./mcp-bridge";
import { createGenericExecutionAdapter } from "./generic-execution";
import type { GenericExecutionContext } from "./generic-execution";

export function GenericSemanticView({
    app,
    canvas,
    context,
}: {
    app: App;
    canvas: CanvasAppMetadata;
    context: GenericExecutionContext;
}) {
    const [, update] = useState(0);
    const [artifact, setArtifact] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const controller = useMemo(
        () =>
            createGenericExecutionAdapter(
                app,
                context,
                () => update((n) => n + 1),
                setArtifact,
            ),
        [app, context],
    );
    const act = async (
        id: string,
        action: "cancel" | "refresh" | "execute",
    ) => {
        try {
            setError(null);
            await controller[action](id);
        } catch {
            setError(
                "Execution state unavailable; reopen the app before continuing.",
            );
        }
    };
    return (
        <>
            <SemanticCanvasRenderer
                spec={canvas.spec}
                revision={canvas.revisionId}
                scopeKey={canvas.scopeKey}
                preview={false}
                viewer="app"
                adapters={controller.adapters}
            />
            {[...controller.states.values()].map((state) => (
                <section
                    key={state.bindingId}
                    aria-label={`Execution ${state.bindingId}`}
                >
                    <p role="status">{state.state.replaceAll("_", " ")}</p>
                    <button
                        type="button"
                        onClick={() => void act(state.bindingId, "refresh")}
                    >
                        Refresh status
                    </button>
                    {state.state === "ready" ? (
                        <button
                            type="button"
                            onClick={() => void act(state.bindingId, "execute")}
                        >
                            Continue execution
                        </button>
                    ) : null}
                    {state.state !== "completed" && state.state !== "failed" ? (
                        <button
                            type="button"
                            onClick={() => void act(state.bindingId, "cancel")}
                        >
                            Request cancellation
                        </button>
                    ) : null}
                </section>
            ))}
            {error ? <p role="alert">{error}</p> : null}
            {artifact !== null ? (
                <section aria-label="Authorized result artifact">
                    <pre>{artifact}</pre>
                </section>
            ) : null}
        </>
    );
}
