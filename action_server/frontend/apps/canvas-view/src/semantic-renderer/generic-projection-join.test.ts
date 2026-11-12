import { describe, expect, it, vi } from "vitest";
import type { App } from "@modelcontextprotocol/ext-apps/react";
import { createGenericExecutionAdapter } from "./generic-execution";
import type { GenericExecutionContext } from "./generic-execution";

const id = "11111111-1111-4111-8111-111111111111";
const other = "22222222-2222-4222-8222-222222222222";
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
const state = (runId = id, status = "completed") => ({
    bindingId: "run",
    runId,
    attemptId: runId,
    state: status,
    cancelRequested: false,
});
const projection = (runId = id, value = 3) => ({
    bindingId: "run",
    runId,
    attemptId: runId,
    canonicalJson: `{"value":${value}}`,
    data: { value },
});
function setup(call: ReturnType<typeof vi.fn>) {
    return createGenericExecutionAdapter(
        { callServerTool: call } as unknown as App,
        context,
        vi.fn(),
        vi.fn(),
        true,
    );
}
describe("generated projection real adapter join", () => {
    it("does not fetch on creation and uses separate authorized data after success", async () => {
        const call = vi.fn(async ({ name }: { name: string }) => ({
            _meta:
                name === "canvas_projection"
                    ? { "actions.projection": projection() }
                    : { "actions.execution": state() },
        }));
        const c = setup(call);
        expect(call).not.toHaveBeenCalled();
        expect(c.adapters.getProjection!("run").state).toBe("not-run");
        await c.adapters.dispatch(c.adapters.resolveFormBinding("run")!, {
            value: "x",
        });
        expect(call.mock.calls.map(([r]) => r.name)).toEqual([
            "canvas_dispatch",
            "canvas_projection",
        ]);
        expect(c.adapters.getProjection!("run")).toMatchObject({
            state: "ready",
            data: { value: 3 },
            execution: { runId: id, attemptId: id },
        });
    });
    it.each(["running", "failed", "cancel_requested"])(
        "never projects %s metadata",
        async (status) => {
            const call = vi.fn(async () => ({
                _meta: { "actions.execution": state(id, status) },
            }));
            const c = setup(call);
            await c.adapters.dispatch(
                c.adapters.resolveFormBinding("run")!,
                {},
            );
            expect(call).toHaveBeenCalledTimes(1);
            expect(c.adapters.getProjection!("run").state).toBe(
                status === "running" ? "loading" : "error",
            );
        },
    );
    it("clears prior data when a later authenticated call is denied", async () => {
        let denied = false;
        const call = vi.fn(async ({ name }: { name: string }) =>
            denied
                ? { isError: true }
                : {
                      _meta:
                          name === "canvas_projection"
                              ? { "actions.projection": projection() }
                              : { "actions.execution": state() },
                  },
        );
        const c = setup(call);
        await c.adapters.dispatch(c.adapters.resolveFormBinding("run")!, {});
        denied = true;
        await expect(c.refresh("run")).rejects.toThrow();
        expect(c.adapters.getProjection!("run")).toMatchObject({
            state: "error",
        });
        expect(c.adapters.getProjection!("run")).not.toHaveProperty("data");
    });
    it.each([false, true])(
        "ignores an old projection or denial after a new successful request (denied=%s)",
        async (denied) => {
            let resolve!: (v: unknown) => void;
            let submits = 0;
            const delayed = new Promise((r) => {
                resolve = r;
            });
            const call = vi.fn(
                async ({
                    name,
                    arguments: args,
                }: {
                    name: string;
                    arguments: Record<string, unknown>;
                }) => {
                    if (name === "canvas_projection")
                        return args.runId === id
                            ? delayed
                            : {
                                  _meta: {
                                      "actions.projection": projection(
                                          other,
                                          4,
                                      ),
                                  },
                              };
                    return {
                        _meta: {
                            "actions.execution": state(
                                ++submits === 1 ? id : other,
                            ),
                        },
                    };
                },
            );
            const c = setup(call);
            const cap = c.adapters.resolveFormBinding("run")!;
            const old = c.adapters.dispatch(cap, { value: "old" });
            await vi.waitFor(() => expect(call).toHaveBeenCalledTimes(2));
            await c.adapters.dispatch(cap, { value: "new" });
            resolve(
                denied
                    ? { isError: true }
                    : { _meta: { "actions.projection": projection() } },
            );
            await old;
            expect(c.adapters.getProjection!("run")).toMatchObject({
                state: "ready",
                data: { value: 4 },
                execution: { runId: other },
            });
        },
    );
});
