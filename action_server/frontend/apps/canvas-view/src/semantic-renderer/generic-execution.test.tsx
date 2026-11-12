import { describe, expect, it, vi } from "vitest";
import type { App } from "@modelcontextprotocol/ext-apps/react";
import { createGenericExecutionAdapter } from "./generic-execution";
import type { GenericExecutionContext } from "./generic-execution";
const id = "11111111-1111-4111-8111-111111111111";
const context = {
    token: "a".repeat(43),
    version: "actions.generic-app/v1",
    bindingIds: ["run"],
    scope: {
        application: {
            app_id: id,
            workspace_id: id,
            revision_id: `sha256:${"1".repeat(64)}`,
        },
        deployment: {
            deployment_id: id,
            workspace_id: id,
            revision_id: `sha256:${"2".repeat(64)}`,
        },
    },
} as GenericExecutionContext;
const state = (value: string) => ({
    bindingId: "run",
    runId: id,
    attemptId: id,
    state: value,
    cancelRequested: value === "cancel_requested",
});
describe("generic official bridge adapter", () => {
    it("never runs on mount; submit returns identity before execute and allows cancellation", async () => {
        let resolve!: (v: unknown) => void;
        const executing = new Promise((r) => {
            resolve = r;
        });
        const call = vi.fn(
            async (request: {
                name: string;
                arguments: Record<string, unknown>;
            }) => {
                expect(request.arguments.appSession).toBe(context.token);
                expect(request.arguments.snapshot).toBeUndefined();
                if (request.arguments.action === "submit")
                    return { _meta: { "actions.execution": state("ready") } };
                if (request.arguments.action === "execute") return executing;
                return {
                    _meta: { "actions.execution": state("cancel_requested") },
                };
            },
        );
        const controller = createGenericExecutionAdapter(
            { callServerTool: call } as unknown as App,
            context,
            vi.fn(),
            vi.fn(),
        );
        expect(call).not.toHaveBeenCalled();
        const capability = controller.adapters.resolveFormBinding("run")!;
        const pending = controller.adapters.dispatch(capability, {
            value: "hello",
        });
        await vi.waitFor(() =>
            expect(controller.states.get("run")?.runId).toBe(id),
        );
        await controller.cancel("run");
        expect(controller.states.get("run")?.state).toBe("cancel_requested");
        resolve({ _meta: { "actions.execution": state("cancel_requested") } });
        await pending;
        expect(call.mock.calls.map(([v]) => v.name)).toEqual([
            "canvas_dispatch",
            "canvas_dispatch",
            "canvas_cancel",
        ]);
    });
    it("retains submission identity after uncertainty and rejects replacement input", async () => {
        const call = vi.fn(async () => {
            throw new Error("lost reply");
        });
        const controller = createGenericExecutionAdapter(
            { callServerTool: call } as unknown as App,
            context,
            vi.fn(),
            vi.fn(),
        );
        const capability = controller.adapters.resolveFormBinding("run")!;
        await expect(
            controller.adapters.dispatch(capability, { value: "hello" }),
        ).rejects.toThrow();
        await expect(
            controller.adapters.dispatch(capability, { value: "changed" }),
        ).rejects.toThrow("uncertain");
        await expect(
            controller.adapters.dispatch(capability, { value: "hello" }),
        ).rejects.toThrow();
        const calls = call.mock.calls as unknown as [
            { arguments: { idempotencyKey: string } },
        ][];
        expect(calls[0][0].arguments.idempotencyKey).toBe(
            calls[1][0].arguments.idempotencyKey,
        );
    });
    it("rejects foreign binding in response", async () => {
        const app = {
            callServerTool: async () => ({
                _meta: {
                    "actions.execution": {
                        ...state("ready"),
                        bindingId: "foreign",
                    },
                },
            }),
        } as unknown as App;
        const controller = createGenericExecutionAdapter(
            app,
            context,
            vi.fn(),
            vi.fn(),
        );
        await expect(
            controller.adapters.dispatch(
                controller.adapters.resolveFormBinding("run")!,
                { value: "hello" },
            ),
        ).rejects.toThrow("identity");
        expect(
            controller.adapters.resolveFormBinding("foreign"),
        ).toBeUndefined();
    });
});

it("reopens retained state without admission and continues only unlaunched Run", async () => {
    const call = vi.fn(async () => ({
        _meta: { "actions.execution": state("completed") },
    }));
    const retained = {
        ...context,
        executions: [state("ready")],
    } as GenericExecutionContext;
    const controller = createGenericExecutionAdapter(
        { callServerTool: call } as unknown as App,
        retained,
        vi.fn(),
        vi.fn(),
    );
    expect(call).not.toHaveBeenCalled();
    expect(controller.states.get("run")?.runId).toBe(id);
    await controller.execute("run");
    expect(call.mock.calls).toHaveLength(1);
    await expect(controller.execute("run")).rejects.toThrow("unlaunched");
});
