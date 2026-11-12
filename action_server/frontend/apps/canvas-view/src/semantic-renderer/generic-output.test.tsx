import { expect, it, vi } from "vitest";
import type { App } from "@modelcontextprotocol/ext-apps/react";
import {
    createGenericExecutionAdapter,
    type GenericExecutionContext,
} from "./generic-execution";
const id = "11111111-1111-4111-8111-111111111111";
const revision = `sha256:${"1".repeat(64)}`;
const queue = {
    workspace_id: id,
    deployment: { workspace_id: id, deployment_id: id, revision_id: revision },
    queue_id: "produced",
};
const context = {
    token: "a".repeat(43),
    version: "actions.generic-app/v1",
    bindingIds: ["run"],
    inputBindings: [],
    outputBindings: [{ bindingId: "run", queue }],
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
        deployment: queue.deployment,
    },
} as GenericExecutionContext;
const page = {
    bindingId: "run",
    runId: id,
    attemptId: id,
    queue,
    items: [
        {
            itemId: id,
            parentId: null,
            queueState: "PENDING",
            cancelRequested: false,
            preview: '{"value":"child"}',
            previewTruncated: false,
        },
    ],
    nextCursor: null,
};
it("loads only explicit associated Run children without claim or adoption", async () => {
    const call = vi.fn(async () => ({ _meta: { "actions.execution": page } }));
    const controller = createGenericExecutionAdapter(
        { callServerTool: call } as unknown as App,
        context,
        vi.fn(),
        vi.fn(),
    );
    expect(call).not.toHaveBeenCalled();
    await controller.loadOutputs("run");
    expect(controller.outputPages.get("run")?.items[0].preview).toContain(
        "child",
    );
    expect(call).toHaveBeenCalledTimes(1);
});

it.each(["run", "attempt", "queue"])(
    "rejects changed output %s identity",
    async (part) => {
        const foreign = "22222222-2222-4222-8222-222222222222";
        const altered = {
            ...page,
            ...(part === "run"
                ? { runId: foreign }
                : part === "attempt"
                  ? { attemptId: foreign }
                  : { queue: { ...queue, queue_id: "foreign" } }),
        };
        const controller = createGenericExecutionAdapter(
            {
                callServerTool: async () => ({
                    _meta: { "actions.execution": altered },
                }),
            } as unknown as App,
            context,
            vi.fn(),
            vi.fn(),
        );
        await expect(controller.loadOutputs("run")).rejects.toThrow("identity");
        expect(controller.outputPages.size).toBe(0);
    },
);

it("renders read-only produced items with explicit load and no adoption controls", async () => {
    const { render, screen, fireEvent, waitFor } =
        await import("@testing-library/react");
    const { GenericOutputPanel } = await import("./generic-output-panel");
    const call = vi.fn(
        async (request: {
            name: string;
            arguments: Record<string, unknown>;
        }) => {
            expect(request.name).toBe("canvas_get_state");
            expect(request.arguments.action).toBe("outputs");
            expect(request.arguments.runId).toBe(id);
            expect(request.arguments.itemId).toBeUndefined();
            return { _meta: { "actions.execution": page } };
        },
    );
    const controller = createGenericExecutionAdapter(
        { callServerTool: call } as unknown as App,
        context,
        vi.fn(),
        vi.fn(),
    );
    const view = render(
        <GenericOutputPanel
            binding={context.outputBindings[0]}
            controller={controller}
        />,
    );
    expect(call).not.toHaveBeenCalled();
    fireEvent.click(
        screen.getByRole("button", { name: "Load produced items" }),
    );
    await waitFor(() =>
        expect(controller.outputPages.get("run")?.items).toHaveLength(1),
    );
    view.rerender(
        <GenericOutputPanel
            binding={context.outputBindings[0]}
            controller={controller}
        />,
    );
    expect(screen.getByText('{"value":"child"}')).toBeTruthy();
    expect(screen.queryByRole("button", { name: /claim|adopt/iu })).toBeNull();
    expect(call).toHaveBeenCalledTimes(1);
});

it("drops the cached child page when a later authorized read is denied", async () => {
    let denied = false;
    const app = {
        callServerTool: async () =>
            denied
                ? { isError: true }
                : { _meta: { "actions.execution": page } },
    } as unknown as App;
    const controller = createGenericExecutionAdapter(
        app,
        context,
        vi.fn(),
        vi.fn(),
    );
    await controller.loadOutputs("run");
    expect(controller.outputPages.size).toBe(1);
    denied = true;
    await expect(controller.loadOutputs("run")).rejects.toThrow();
    expect(controller.outputPages.size).toBe(0);
});
