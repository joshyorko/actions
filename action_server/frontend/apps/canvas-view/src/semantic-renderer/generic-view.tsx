import { useMemo, useState } from "react";
import type { App } from "@modelcontextprotocol/ext-apps/react";
import { GenericOutputPanel } from "./generic-output-panel";
import { GenericInputForm } from "./generic-input-form";
import { SemanticCanvasRenderer, SemanticStatus } from "./components";
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
    const [artifact, setArtifact] = useState<{
        bindingId: string;
        text: string;
    } | null>(null);
    const [error, setError] = useState<{
        bindingId: string;
        message: string;
    } | null>(null);
    const controller = useMemo(
        () =>
            createGenericExecutionAdapter(
                app,
                context,
                () => update((n) => n + 1),
                (text, bindingId) => setArtifact({ text, bindingId }),
                canvas.spec.schemaVersion === "actions.canvas-spec/v2",
            ),
        [app, context, canvas.spec.schemaVersion],
    );
    const act = async (
        id: string,
        action: "cancel" | "refresh" | "execute",
    ) => {
        try {
            setError(null);
            await controller[action](id);
        } catch {
            setError({
                bindingId: id,
                message:
                    "Execution state unavailable; reopen the app before continuing.",
            });
        }
    };
    const authorized = new Set(context.bindingIds);
    const forms = new Map(
        (context.inputBindings ?? [])
            .filter((entry) => authorized.has(entry.bindingId))
            .map((entry) => [
                entry.bindingId,
                <GenericInputForm
                    key={entry.bindingId}
                    binding={entry}
                    controller={controller}
                />,
            ]),
    );
    const panels = new Map(
        context.bindingIds.map((bindingId) => {
            const state = controller.states.get(bindingId);
            const output = context.outputBindings?.find(
                (entry) => entry.bindingId === bindingId,
            );
            return [
                bindingId,
                <div className="semantic-stack" key={bindingId}>
                    {state ? (
                        <section
                            className="semantic-panel"
                            aria-label={`Execution ${bindingId}`}
                        >
                            <SemanticStatus
                                state={
                                    state.state === "failed"
                                        ? "error"
                                        : "success"
                                }
                                message={state.state.replaceAll("_", " ")}
                            />
                            <div className="semantic-actions">
                                <button
                                    type="button"
                                    onClick={() =>
                                        void act(bindingId, "refresh")
                                    }
                                >
                                    Refresh status
                                </button>
                                {state.state === "ready" ? (
                                    <button
                                        type="button"
                                        onClick={() =>
                                            void act(bindingId, "execute")
                                        }
                                    >
                                        Continue execution
                                    </button>
                                ) : null}
                                {state.state !== "completed" &&
                                state.state !== "failed" ? (
                                    <button
                                        type="button"
                                        onClick={() =>
                                            void act(bindingId, "cancel")
                                        }
                                    >
                                        Request cancellation
                                    </button>
                                ) : null}
                            </div>
                        </section>
                    ) : null}
                    {output && state?.state === "completed" ? (
                        <GenericOutputPanel
                            key={state.runId}
                            binding={output}
                            controller={controller}
                        />
                    ) : null}
                    {error?.bindingId === bindingId ? (
                        <p role="alert">{error.message}</p>
                    ) : null}
                    {artifact?.bindingId === bindingId ? (
                        <section
                            className="semantic-panel"
                            aria-label="Authorized result artifact"
                        >
                            <h3>Result artifact</h3>
                            <pre>{artifact.text}</pre>
                        </section>
                    ) : null}
                </div>,
            ];
        }),
    );
    return (
        <SemanticCanvasRenderer
            spec={canvas.spec}
            revision={canvas.revisionId}
            scopeKey={canvas.scopeKey}
            preview={canvas.preview}
            viewer="app"
            adapters={controller.adapters}
            appFormOverrides={forms}
            appPanels={panels}
        />
    );
}
