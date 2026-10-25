import { render, screen, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import type { App } from "@modelcontextprotocol/ext-apps/react";
import { GenericSemanticView } from "./generic-view";
import { SemanticCanvasRenderer } from "./components";
import type { CanvasAppMetadata } from "./mcp-bridge";
import type { GenericExecutionContext } from "./generic-execution";
import type { CanvasSpecDocumentV1, SemanticRendererAdapters } from "./types";
const id = "11111111-1111-4111-8111-111111111111";
const revision = `sha256:${"1".repeat(64)}`;
const deployment = {
    workspace_id: id,
    deployment_id: id,
    revision_id: revision,
};
const queue = { workspace_id: id, deployment, queue_id: "input" };
const canvas: CanvasAppMetadata & { spec: CanvasSpecDocumentV1 } = {
    applicationId: id,
    revisionId: revision,
    active: true,
    preview: false,
    scopeKey: "owned",
    bindings: [],
    spec: {
        schemaVersion: "actions.canvas-spec/v1",
        title: "Consumer",
        visibility: ["app", "model"],
        bindingIds: ["run"],
        root: {
            type: "form",
            id: "authored-input",
            bindingId: "run",
            submitLabel: "Run",
            fields: [
                {
                    name: "value",
                    label: "Replacement value",
                    type: "text",
                    required: true,
                },
            ],
        },
    },
};
const context = {
    token: "a".repeat(43),
    version: "actions.generic-app/v1",
    bindingIds: ["run"],
    inputBindings: [{ bindingId: "run", queue, inputMode: "claim" }],
    outputBindings: [
        { bindingId: "run", queue: { ...queue, queue_id: "input_output" } },
    ],
    executions: [
        {
            bindingId: "run",
            runId: id,
            attemptId: id,
            state: "completed",
            cancelRequested: false,
        },
    ],
    scope: {
        application: { app_id: id, workspace_id: id, revision_id: revision },
        deployment,
    },
} as GenericExecutionContext;
it("renders declared consumer controls and results within the authored canvas without replacement fields", () => {
    const call = vi.fn();
    render(
        <GenericSemanticView
            app={{ callServerTool: call } as unknown as App}
            canvas={canvas}
            context={context}
        />,
    );
    const main = within(screen.getByRole("main"));
    expect(
        main.getByRole("form", { name: "Work Item input for run" }),
    ).toBeTruthy();
    expect(main.getByRole("button", { name: "Refresh status" })).toBeTruthy();
    expect(
        main.getByRole("button", { name: "Load produced items" }),
    ).toBeTruthy();
    expect(main.queryByText("This action is unavailable.")).toBeNull();
    expect(main.queryByLabelText("Replacement value")).toBeNull();
    expect(main.getByRole("combobox")).toBeTruthy();
    expect(call).not.toHaveBeenCalled();
});
const adapters = {
    resolveFormBinding: vi.fn(),
    resolveStatusBinding: vi.fn(),
    resolveArtifactBinding: vi.fn(),
    dispatch: vi.fn(),
    getStatus: vi.fn(),
    openArtifact: vi.fn(),
} as SemanticRendererAdapters;
it.each(["model", "preview", "undeclared", "invisible"])(
    "suppresses trusted private slots for %s",
    (mode) => {
        const spec = {
            ...canvas.spec,
            bindingIds: mode === "undeclared" ? [] : ["run"],
            visibility:
                mode === "invisible"
                    ? ["model" as const]
                    : canvas.spec.visibility,
        };
        render(
            <SemanticCanvasRenderer
                spec={spec}
                revision={revision}
                scopeKey="owned"
                viewer={mode === "model" ? "model" : "app"}
                preview={mode === "preview"}
                adapters={adapters}
                appFormOverrides={
                    new Map([
                        ["run", <button key="input">Private input</button>],
                    ])
                }
                appPanels={
                    new Map([["run", <p key="panel">Private result</p>]])
                }
            />,
        );
        expect(screen.queryByText("Private input")).toBeNull();
        expect(screen.queryByText("Private result")).toBeNull();
    },
);

it("keeps inspected artifact within the canvas and preserves authored input node identity", async () => {
    const handle = `art_${"A".repeat(22)}`;
    const call = vi.fn(async () => ({
        _meta: {
            "actions.artifact": {
                bindingId: "run",
                runId: id,
                handle,
                text: "Saved result",
            },
        },
    }));
    const active = {
        ...context,
        executions: context.executions!.map((state) => ({
            ...state,
            outputs: [{ handle }],
        })),
    };
    const spec = {
        ...canvas.spec,
        root: {
            type: "stack" as const,
            id: "layout",
            children: [
                canvas.spec.root,
                {
                    type: "artifact" as const,
                    id: "result",
                    bindingId: "run",
                    label: "Inspect result",
                },
            ],
        },
    };
    const { container } = render(
        <GenericSemanticView
            app={{ callServerTool: call } as unknown as App}
            canvas={{ ...canvas, spec }}
            context={active}
        />,
    );
    expect(
        container.querySelector('[data-semantic-node-id="authored-input"]'),
    ).toBeTruthy();
    const { fireEvent } = await import("@testing-library/react");
    fireEvent.click(
        within(screen.getByRole("main")).getByRole("button", {
            name: "Inspect result",
        }),
    );
    expect(
        await within(screen.getByRole("main")).findByText("Saved result"),
    ).toBeTruthy();
    expect(call).toHaveBeenCalledTimes(1);
});

it("does not move a declared private form into an undeclared authored binding", () => {
    const call = vi.fn();
    render(
        <GenericSemanticView
            app={{ callServerTool: call } as unknown as App}
            canvas={{ ...canvas, spec: { ...canvas.spec, bindingIds: [] } }}
            context={context}
        />,
    );
    expect(screen.queryByRole("combobox")).toBeNull();
    expect(screen.queryByRole("button", { name: "Refresh status" })).toBeNull();
    expect(call).not.toHaveBeenCalled();
});
