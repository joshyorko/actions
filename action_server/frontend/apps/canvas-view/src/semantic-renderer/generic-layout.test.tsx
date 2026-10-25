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

it("clears inspected JSON and its success notice before a new failed submission returns", async () => {
    const { fireEvent, waitFor, act } = await import("@testing-library/react");
    const handle = `art_${"A".repeat(22)}`;
    const payload = '{"text":"gamma delta epsilon","count":3}';
    let submissions = 0;
    let fail!: (value: unknown) => void;
    const failure = new Promise((resolve) => {
        fail = resolve;
    });
    const call = vi.fn(async ({ name }: { name: string }) => {
        if (name === "canvas_artifact")
            return {
                _meta: {
                    "actions.artifact": {
                        bindingId: "run",
                        runId: id,
                        handle,
                        text: payload,
                    },
                },
            };
        submissions++;
        if (submissions === 3) return failure;
        return {
            _meta: {
                "actions.execution": {
                    ...context.executions![0],
                    outputs: [{ handle }],
                },
            },
        };
    });
    render(
        <GenericSemanticView
            app={{ callServerTool: call } as unknown as App}
            context={{
                ...context,
                executions: [],
                inputBindings: [],
                outputBindings: [],
            }}
            canvas={{
                ...canvas,
                spec: {
                    ...canvas.spec,
                    root: {
                        type: "stack",
                        id: "layout",
                        children: [
                            canvas.spec.root,
                            {
                                type: "artifact",
                                id: "result",
                                bindingId: "run",
                                label: "Inspect result",
                            },
                        ],
                    },
                },
            }}
        />,
    );
    for (const value of ["alpha beta", "gamma delta epsilon"]) {
        fireEvent.change(screen.getByLabelText("Replacement value"), {
            target: { value },
        });
        fireEvent.click(screen.getByRole("button", { name: "Run" }));
        await waitFor(() =>
            expect(
                (
                    screen.getByRole("button", {
                        name: "Run",
                    }) as HTMLButtonElement
                ).disabled,
            ).toBe(false),
        );
    }
    fireEvent.click(screen.getByRole("button", { name: "Inspect result" }));
    expect(await screen.findByText(payload)).toBeTruthy();
    expect(
        await screen.findByText("Authorized result inspected below."),
    ).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Replacement value"), {
        target: { value: "deliberate failure" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));
    await waitFor(() => {
        expect(screen.queryByText(payload)).toBeNull();
        expect(
            screen.queryByText("Authorized result inspected below."),
        ).toBeNull();
    });
    await act(async () => {
        fail({
            _meta: {
                "actions.execution": {
                    ...context.executions![0],
                    state: "failed",
                },
            },
        });
    });
    expect(await screen.findByText("failed")).toBeTruthy();
    expect(screen.queryByText(payload)).toBeNull();
    expect(screen.queryByText("Authorized result inspected below.")).toBeNull();
});
it("discards an old session's delayed artifact and keeps the replacement session usable", async () => {
    const { fireEvent, act } = await import("@testing-library/react");
    const handle = `art_${"A".repeat(22)}`;
    let finish!: (value: unknown) => void;
    const delayed = new Promise((resolve) => {
        finish = resolve;
    });
    const call = vi.fn(
        async ({ arguments: args }: { arguments: Record<string, unknown> }) =>
            args.appSession === context.token
                ? delayed
                : {
                      _meta: {
                          "actions.artifact": {
                              bindingId: "run",
                              runId: id,
                              handle,
                              text: "New session result",
                          },
                      },
                  },
    );
    const app = { callServerTool: call } as unknown as App;
    const active = {
        ...context,
        executions: context.executions!.map((state) => ({
            ...state,
            outputs: [{ handle }],
        })),
    };
    const selected = {
        ...canvas,
        spec: {
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
        },
    };
    const view = render(
        <GenericSemanticView app={app} context={active} canvas={selected} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Inspect result" }));
    view.rerender(
        <GenericSemanticView
            app={app}
            context={{ ...active, token: "b".repeat(43) }}
            canvas={selected}
        />,
    );
    await act(async () => {
        finish({
            _meta: {
                "actions.artifact": {
                    bindingId: "run",
                    runId: id,
                    handle,
                    text: "Old session result",
                },
            },
        });
    });
    expect(screen.queryByText("Old session result")).toBeNull();
    expect(screen.queryByText("Authorized result inspected below.")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Inspect result" }));
    expect(await screen.findByText("New session result")).toBeTruthy();
});

it("reproduces request error retained after same Run continuation succeeds", async () => {
    const { fireEvent, waitFor } = await import("@testing-library/react");
    let executionCalls = 0;
    const call = vi.fn(
        async ({ arguments: args }: { arguments: Record<string, unknown> }) => {
            if (args.action === "execute" && ++executionCalls === 1)
                throw new Error("synthetic initial transport failure");
            return {
                _meta: {
                    "actions.execution": {
                        ...context.executions![0],
                        state: args.action === "submit" ? "ready" : "completed",
                    },
                },
            };
        },
    );
    render(
        <GenericSemanticView
            app={{ callServerTool: call } as unknown as App}
            canvas={canvas}
            context={{
                ...context,
                executions: [],
                inputBindings: [],
                outputBindings: [],
            }}
        />,
    );
    fireEvent.change(screen.getByLabelText("Replacement value"), {
        target: { value: "alpha beta" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));
    expect(
        await screen.findByText("Unable to complete this action. Try again."),
    ).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Continue execution" }));
    await waitFor(() =>
        expect(
            screen.queryByRole("button", { name: "Continue execution" }),
        ).toBeNull(),
    );
    fireEvent.click(screen.getByRole("button", { name: "Refresh status" }));
    await waitFor(() => expect(call).toHaveBeenCalledTimes(4));
    expect(
        screen.getByText("Unable to complete this action. Try again."),
    ).toBeTruthy();
    expect(
        (screen.getByLabelText("Replacement value") as unknown as { value: string }).value,
    ).toBe("alpha beta");
});

it("disables exposed Continue while automatic execute owns the operation", async () => {
    const { fireEvent, waitFor, act } = await import("@testing-library/react");
    let automatic!: (value: unknown) => void;
    const pendingAutomatic = new Promise((resolve) => {
        automatic = resolve;
    });
    let executes = 0;
    const state = (status: string) => ({
        _meta: {
            "actions.execution": { ...context.executions![0], state: status },
        },
    });
    const call = vi.fn(
        async ({ arguments: args }: { arguments: Record<string, unknown> }) => {
            if (args.action === "submit") return state("ready");
            if (args.action === "execute" && ++executes === 1)
                return pendingAutomatic;
            return state("running");
        },
    );
    render(
        <GenericSemanticView
            app={{ callServerTool: call } as unknown as App}
            canvas={
                {
                    ...canvas,
                    spec: {
                        ...canvas.spec,
                        schemaVersion: "actions.canvas-spec/v2",
                    },
                } as CanvasAppMetadata
            }
            context={{
                ...context,
                executions: [],
                inputBindings: [],
                outputBindings: [],
            }}
        />,
    );
    fireEvent.change(screen.getByLabelText("Replacement value"), {
        target: { value: "alpha beta" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));
    const button = await screen.findByRole("button", {
        name: "Continue execution",
    });
    expect((button as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(button);
    await waitFor(() => expect(executes).toBe(1));
    await act(async () => {
        automatic(state("running"));
        await Promise.resolve();
    });
    expect(
        screen.queryByText("Unable to complete this action. Try again."),
    ).toBeNull();
});
